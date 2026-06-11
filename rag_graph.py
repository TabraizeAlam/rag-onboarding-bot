"""
LangGraph-based RAG pipeline.

Graph nodes:
  retrieve  →  grade_relevance  →  generate  (if relevant docs found)
                                →  refuse    (if no relevant docs)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict, Annotated
import operator

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain.schema import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

load_dotenv()

CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "onboarding_kb"
TOP_K = 5
RELEVANCE_THRESHOLD = 0.25  # cosine similarity floor (0–1)


# ── State ────────────────────────────────────────────────────────────────────

class RAGState(TypedDict):
    question: str
    documents: list[Document]
    relevance_scores: list[float]
    answer: str
    sources: list[str]
    refused: bool


# ── Retriever setup ──────────────────────────────────────────────────────────

def build_retriever():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    # Dense retriever
    dense = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": TOP_K, "score_threshold": 0.0},
    )

    # Sparse BM25 retriever — built from all stored docs
    all_docs = vectorstore.get()
    bm25_docs = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(all_docs["documents"], all_docs["metadatas"])
    ]
    sparse = BM25Retriever.from_documents(bm25_docs, k=TOP_K)

    # Hybrid: 60% dense, 40% sparse
    return EnsembleRetriever(retrievers=[dense, sparse], weights=[0.6, 0.4])


_retriever = None

def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = build_retriever()
    return _retriever


# ── LLM (Nebius Token Factory — required by course) ──────────────────────────

def get_llm():
    return ChatOpenAI(
        model="meta-llama/Meta-Llama-3.1-70B-Instruct-fast",
        openai_api_key=os.environ["NEBIUS_API_KEY"],
        openai_api_base="https://api.studio.nebius.ai/v1/",
        temperature=0.1,
        max_tokens=1024,
    )


# ── Graph nodes ───────────────────────────────────────────────────────────────

def retrieve(state: RAGState) -> dict:
    retriever = get_retriever()
    docs = retriever.invoke(state["question"])
    return {"documents": docs}


def grade_relevance(state: RAGState) -> dict:
    """
    Score each retrieved doc against the question via embedding cosine similarity.
    Keep docs above threshold; if none survive, signal refusal.
    """
    from langchain_openai import OpenAIEmbeddings
    import numpy as np

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    q_vec = embeddings.embed_query(state["question"])
    q_arr = np.array(q_vec)

    scored = []
    for doc in state["documents"]:
        d_arr = np.array(embeddings.embed_query(doc.page_content))
        score = float(np.dot(q_arr, d_arr) / (np.linalg.norm(q_arr) * np.linalg.norm(d_arr) + 1e-10))
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    relevant = [(s, d) for s, d in scored if s >= RELEVANCE_THRESHOLD]

    scores = [s for s, _ in relevant]
    docs = [d for _, d in relevant]
    refused = len(docs) == 0
    return {"documents": docs, "relevance_scores": scores, "refused": refused}


def generate(state: RAGState) -> dict:
    llm = get_llm()
    context_parts = []
    sources = []
    for i, doc in enumerate(state["documents"][:5]):
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
    user = f"Knowledge base excerpts:\n\n{context}\n\nQuestion: {state['question']}"

    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
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
    graph.add_node("grade_relevance", grade_relevance)
    graph.add_node("generate", generate)
    graph.add_node("refuse", refuse)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "grade_relevance")
    graph.add_conditional_edges("grade_relevance", route_after_grading, {
        "generate": "generate",
        "refuse": "refuse",
    })
    graph.add_edge("generate", END)
    graph.add_edge("refuse", END)

    return graph.compile()


_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def ask(question: str) -> dict:
    """Public API: ask a question, get back answer + sources."""
    initial = RAGState(
        question=question,
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
    }
