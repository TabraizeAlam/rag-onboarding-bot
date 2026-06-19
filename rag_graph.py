"""
LangGraph-based RAG pipeline — Nebius-only (embeddings + generation).

Graph nodes:
  rewrite_query  →  retrieve  →  rerank_and_grade  →  generate  (docs found)
                                                   →  refuse    (true junk)

Design notes (measured on this corpus):
- Users type informally with typos ("deployment pipleine"). The rewrite
  node turns the message into a clean standalone search query first —
  this also folds in chat history so follow-ups retrieve correctly.
- The FlashRank cross-encoder reorders candidates AND gates refusal.
  Its scores are bimodal at the extremes: true junk ("stock price",
  "weather") scores ~0.0001 across ALL chunks, while topically-related
  text scores 10–100x higher even when phrased differently than the
  docs (e.g. "development process" vs "engineering processes" ≈ 0.013).
  So the gate hard-refuses only below REFUSAL_FLOOR; mid-scoring docs
  are passed to the LLM, whose grounded prompt makes the final call.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document


class _EnsembleRetriever:
    """Reciprocal-rank fusion over multiple retrievers (replaces langchain EnsembleRetriever)."""
    def __init__(self, retrievers, weights):
        self.retrievers = retrievers
        self.weights = weights

    def invoke(self, query: str) -> list[Document]:
        scores: dict[str, float] = {}
        docs_map: dict[str, Document] = {}
        for retriever, weight in zip(self.retrievers, self.weights):
            for rank, doc in enumerate(retriever.invoke(query)):
                key = doc.page_content[:200]
                scores[key] = scores.get(key, 0.0) + weight / (rank + 1)
                docs_map[key] = doc
        return [docs_map[k] for k in sorted(scores, key=lambda k: scores[k], reverse=True)]
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

load_dotenv()

CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "onboarding_kb"
TOP_K = 8            # retrieve wide...
RERANK_TOP_N = 4     # ...then rerank down to the best few
REFUSAL_FLOOR = 0.005  # cross-encoder score; true junk ≈ 0.0001, related text ≥ 0.005

NEBIUS_BASE_URL = "https://api.studio.nebius.ai/v1/"
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"
GENERATION_MODEL = "meta-llama/Llama-3.3-70B-Instruct"


# ── State ────────────────────────────────────────────────────────────────────

class RAGState(TypedDict):
    question: str
    search_query: str  # cleaned/rewritten version of question used for retrieval
    chat_history: list[tuple[str, str]]  # (role, content) pairs for multi-turn
    documents: list[Document]
    relevance_scores: list[float]
    answer: str
    sources: list[str]
    refused: bool


# ── Shared clients ───────────────────────────────────────────────────────────

def get_embeddings():
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=os.environ["NEBIUS_API_KEY"],
        openai_api_base=NEBIUS_BASE_URL,
        tiktoken_enabled=False,
        check_embedding_ctx_length=False,
    )


def get_llm(temperature: float = 0.1):
    return ChatOpenAI(
        model=GENERATION_MODEL,
        openai_api_key=os.environ["NEBIUS_API_KEY"],
        openai_api_base=NEBIUS_BASE_URL,
        temperature=temperature,
        max_tokens=1024,
    )


# ── Retriever setup ──────────────────────────────────────────────────────────

def build_retriever():
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )

    dense = vectorstore.as_retriever(search_kwargs={"k": TOP_K})

    # Sparse BM25 retriever — built from all stored docs
    all_docs = vectorstore.get()
    if not all_docs["documents"]:
        raise RuntimeError(
            "Vector store is empty. Run 'python ingest.py' first to build the knowledge base."
        )
    bm25_docs = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(all_docs["documents"], all_docs["metadatas"])
    ]
    sparse = BM25Retriever.from_documents(bm25_docs, k=TOP_K)

    # Hybrid: 60% dense, 40% sparse
    return _EnsembleRetriever(retrievers=[dense, sparse], weights=[0.6, 0.4])


_retriever = None
_reranker = None
_graph = None


def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = build_retriever()
    return _retriever


def get_reranker():
    """Local cross-encoder reranker (FlashRank, small ONNX model, no GPU needed)."""
    global _reranker
    if _reranker is None:
        from flashrank import Ranker
        _reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir=str(Path(__file__).parent / ".flashrank"))
    return _reranker


# ── Graph nodes ───────────────────────────────────────────────────────────────

def rewrite_query(state: RAGState) -> dict:
    """
    Normalize the user's message into a clean standalone search query:
    fixes typos, expands informal phrasing, and resolves follow-up
    references ("and how do I roll that back?") using recent history.
    Falls back to the raw question if the rewrite fails.
    """
    question = state["question"]
    history = state.get("chat_history", [])

    ctx = ""
    if history:
        recent = "\n".join(f"{role}: {content[:200]}" for role, content in history[-4:])
        ctx = f"Recent conversation for context:\n{recent}\n\n"

    prompt = (
        f"{ctx}"
        "Rewrite the user message below as ONE clear, standalone question for "
        "searching team documentation. Fix any typos. Keep specific tool and "
        "system names. Output ONLY the rewritten question, nothing else.\n\n"
        f"User message: {question}"
    )
    try:
        rewritten = get_llm(temperature=0.0).invoke(prompt).content.strip().strip('"')
        if not rewritten or len(rewritten) > 300:
            rewritten = question
    except Exception:
        rewritten = question
    return {"search_query": rewritten}


def retrieve(state: RAGState) -> dict:
    query = state.get("search_query") or state["question"]
    docs = get_retriever().invoke(query)
    return {"documents": docs}


def rerank_and_grade(state: RAGState) -> dict:
    """
    Cross-encoder rerank: reads query + chunk together for precise relevance
    ordering. Hard-refuse only when even the best passage scores below
    REFUSAL_FLOOR (true junk territory, ~0.0001). Mid-scoring passages are
    kept and passed to the LLM, whose grounded prompt makes the final call.
    Runs locally; zero API calls.
    """
    from flashrank import RerankRequest

    docs = state["documents"]
    if not docs:
        return {"documents": [], "relevance_scores": [], "refused": True}

    query = state.get("search_query") or state["question"]
    request = RerankRequest(
        query=query,
        passages=[{"id": i, "text": d.page_content} for i, d in enumerate(docs)],
    )
    results = get_reranker().rerank(request)

    keep = [
        (float(r["score"]), docs[r["id"]])
        for r in results[:RERANK_TOP_N]
        if r["score"] >= REFUSAL_FLOOR
    ]

    return {
        "documents": [d for _, d in keep],
        "relevance_scores": [s for s, _ in keep],
        "refused": len(keep) == 0,
    }


def generate(state: RAGState) -> dict:
    llm = get_llm()
    context_parts = []
    sources = []
    for i, doc in enumerate(state["documents"]):
        src = doc.metadata.get("source_file", f"doc_{i}")
        context_parts.append(f"[{src}]\n{doc.page_content}")
        if src not in sources:
            sources.append(src)

    context = "\n\n---\n\n".join(context_parts)

    system = (
        "You are an onboarding assistant for new Data Platform team members at AIMCo "
        "(Alberta Investment Management Corporation). "
        "Answer questions using ONLY the provided knowledge base excerpts. "
        "Cite the source file name in your answer (e.g. 'According to 02_environment_setup.md...'). "
        "If the excerpts do not contain enough information, say so clearly rather than guessing."
    )

    messages = [SystemMessage(content=system)]
    # Multi-turn: include recent history so follow-up questions keep context
    for role, content in state.get("chat_history", [])[-6:]:
        messages.append(HumanMessage(content=content) if role == "user" else AIMessage(content=content))
    messages.append(HumanMessage(content=f"Knowledge base excerpts:\n\n{context}\n\nQuestion: {state['question']}"))

    response = llm.invoke(messages)
    return {"answer": response.content, "sources": sources}


def refuse(state: RAGState) -> dict:
    return {
        "answer": (
            "I couldn't find relevant information in the Data Platform knowledge base to answer your question. "
            "Please check with your onboarding buddy, post in the #data-platform-team Teams channel, "
            "or search the Atlan data catalog for data-related questions."
        ),
        "sources": [],
    }


def route_after_grading(state: RAGState) -> str:
    return "refuse" if state.get("refused") else "generate"


# ── Build graph ───────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(RAGState)
    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("rerank_and_grade", rerank_and_grade)
    graph.add_node("generate", generate)
    graph.add_node("refuse", refuse)

    graph.set_entry_point("rewrite_query")
    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("retrieve", "rerank_and_grade")
    graph.add_conditional_edges("rerank_and_grade", route_after_grading, {
        "generate": "generate",
        "refuse": "refuse",
    })
    graph.add_edge("generate", END)
    graph.add_edge("refuse", END)

    return graph.compile()


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def ask(question: str, chat_history: list[tuple[str, str]] | None = None) -> dict:
    """Public API: ask a question, get back answer + sources + retrieved context."""
    initial = RAGState(
        question=question,
        search_query="",
        chat_history=chat_history or [],
        documents=[],
        relevance_scores=[],
        answer="",
        sources=[],
        refused=False,
    )
    result = get_graph().invoke(initial)
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "refused": result.get("refused", False),
        "search_query": result.get("search_query", ""),
        "num_docs_retrieved": len(result["documents"]),
        "relevance_scores": result.get("relevance_scores", []),
        "context": [d.page_content for d in result["documents"]],
    }
