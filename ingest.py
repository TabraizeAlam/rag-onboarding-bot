"""
Ingest markdown docs into a persistent Chroma vector store.
Uses Nebius Token Factory for embeddings (no OpenAI key needed).

Run once (or whenever docs change): python ingest.py
"""

import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

DOCS_DIR = Path(__file__).parent / "docs"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "onboarding_kb"

# Nebius serves embeddings through an OpenAI-compatible API
NEBIUS_BASE_URL = "https://api.studio.nebius.ai/v1/"
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"


def get_embeddings():
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=os.environ["NEBIUS_API_KEY"],
        openai_api_base=NEBIUS_BASE_URL,
        # Nebius does not support OpenAI's dimension/tokenization params
        tiktoken_enabled=False,
        check_embedding_ctx_length=False,
    )


def load_docs():
    docs = []
    for md_file in sorted(DOCS_DIR.glob("**/*.md")):
        loader = TextLoader(str(md_file), encoding="utf-8")
        loaded = loader.load()
        for doc in loaded:
            doc.metadata["source"] = str(md_file)
        docs.extend(loaded)
        print(f"  Loaded: {md_file.name}")
    return docs


def clean_doc(doc):
    # Strip excessive whitespace and normalize line endings
    doc.page_content = "\n".join(
        line.rstrip() for line in doc.page_content.splitlines() if line.strip()
    )
    # Tag each chunk with its source filename for citations
    doc.metadata["source_file"] = Path(doc.metadata.get("source", "")).name
    return doc


def chunk_docs(docs):
    # chunk_size is in CHARACTERS for RecursiveCharacterTextSplitter.
    # 1500 chars ≈ 375 tokens — keeps a full markdown section per chunk.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(docs)
    return [clean_doc(c) for c in chunks]


def build_vector_store(chunks):
    # Chroma.from_documents APPENDS to an existing collection — wipe first
    # so re-running ingest never creates duplicate chunks.
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
    )
    return vectorstore


if __name__ == "__main__":
    print("Loading documents...")
    docs = load_docs()
    print(f"  Loaded {len(docs)} documents")

    print("Chunking...")
    chunks = chunk_docs(docs)
    print(f"  Created {len(chunks)} chunks")

    print(f"Embedding with Nebius ({EMBEDDING_MODEL}) and building vector store...")
    vs = build_vector_store(chunks)
    print(f"  Stored in {CHROMA_DIR}")
    print("Done. Run 'streamlit run app.py' to start the chatbot.")
