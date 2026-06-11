"""
LangGraph-based RAG pipeline — Nebius-only (embeddings + generation).

Graph nodes:
  retrieve  →  rerank_and_grade  →  generate  (if relevant docs found)
                                 →  refuse    (if no relevant docs)

The FlashRank cross-encoder does double duty: it reorders the hybrid
retrieval candidates AND its calibrated scores gate the refusal path.
(Embedding cosine similarity is a poor refusal signal for BGE-family
models — unrelated pairs still score ~0.5 — while cross-encoder scores
sit near 0 for irrelevant passages and near 1 for relevant ones.)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain.schema import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

load_dotenv()

CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "onboarding_kb"
TOP_K = 8            # retrieve wide...
RERANK_TOP_N = 4     # ...then rerank down to the best few
RELEVANCE_THRESHOLD = 0.30  # cross-encoder score floor (0–1); irrelevant ≈ 0.0x

NEBIUS_BASE_URL = "https://api.studio.nebius.ai/v1/"
EMBEDDING_MODEL = "BAAI/bge-en-icl"
GENERATION_MODEL = "meta-llama/Meta-Llama-3.1-70B-Instruct-fast"


# ── State ────────────────────────────────────────────────────────────────────

class RAGState(TypedDict):
    question: str
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
    return EnsembleRetriever(retrievers=[dense, sparse], weights=[0.6, 0.4])


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

def retrieve(state: RAGState) -> dict:
    docs = get_retriever().invoke(state["question"])
    return {"documents": docs}


def rerank_and_grade(state: RAGState) -> dict:
    """
    Cross-encoder rerank: reads question + chunk together for precise
    relevance ordering. The same calibrated scores gate the refusal path —
    if no passage clears RELEVANCE_THRESHOLD, route to refuse.
    Runs locally; zero API calls.
    """
    from flashrank import RerankRequest

    docs = state["documents"]
    if not docs:
        return {"documents": [], "relevance_scores": [], "refused": True}

    request = RerankRequest(
        query=state["question"],
        passages=[{"id": i, "text": d.page_content} for i, d in enumerate(docs)],
    )
    results = get_reranker().rerank(request)

    keep = [
        (float(r["score"]), docs[r["id"]])
        for r in results[:RERANK_TOP_N]
        if r["score"] >= RELEVANCE_THRESHOLD
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
        "You are an onboarding assistant for new team members at Acme Corp. "
        "Answer questions using ONLY the provided knowledge base excerpts. "
        "Cite the source file name in your answer (e.g. 'According to 02_dev_environment_setup.md...'). "
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
            "I couldn't find relevant information in the team knowledge base to answer your question. "
            "Please check the Confluence wiki, ask in the appropriate Slack channel (#devex-team, "
            "#infra-team, #data-platform), or reach out to your onboarding buddy."
        ),
        "sources": [],
    }


def route_after_grading(state: RAGState) -> str:
    return "refuse" if state.get("refused") else "generate"


# ── Build graph ───────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("rerank_and_grade", rerank_and_grade)
    graph.add_node("generate", generate)
    graph.add_node("refuse", refuse)

    graph.set_entry_point("retrieve")
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
        "num_docs_retrieved": len(result["documents"]),
        "relevance_scores": result.get("relevance_scores", []),
        "context": [d.page_content for d in result["documents"]],
    }
