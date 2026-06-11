"""
Ingest markdown docs into a persistent Chroma vector store.
Run once (or whenever docs change): python ingest.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

DOCS_DIR = Path(__file__).parent / "docs"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "onboarding_kb"


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
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=64,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(docs)
    return [clean_doc(c) for c in chunks]


def build_vector_store(chunks):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
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

    print("Building vector store...")
    vs = build_vector_store(chunks)
    print(f"  Stored in {CHROMA_DIR}")
    print("Done. Run app.py to start the chatbot.")
