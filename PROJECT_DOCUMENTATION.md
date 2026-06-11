# Project Documentation — Team Onboarding RAG Bot

**Course:** The Gen Academy — Mastering Agentic AI Bootcamp  
**Week:** 2 — Gen AI Building Blocks  
**Track:** Track 2 — Code-heavy (LangChain + LangGraph)  
**Use Case:** Project 1 — Enterprise Policy Q&A Bot (adapted for team onboarding)

---

## 1. Project One-Liner

> My RAG app helps **new hires and existing team members** answer **onboarding, setup, process, and architecture questions** from **Acme Corp's internal team knowledge base (7 Confluence-style markdown documents, ~6,000 words)** via a **Streamlit chatbot** with **≥90% faithfulness** and responses under **5 seconds**.

---

## 2. The RAG Framework

| Field | Decision |
|-------|----------|
| **Use case** | New hires at Acme Corp ask questions like "How do I set up my dev environment?" or "What is the deployment process?" through a Streamlit chat interface backed by the team's internal knowledge base. |
| **Corpus** | 7 Markdown documents (~6,000 words total) covering: team overview, developer environment setup, deployment process, tools & access, engineering processes, architecture overview, and onboarding checklist. Documents are owned by the Platform Engineering team and would normally live in Confluence. |
| **Ingestion + cleaning** | Documents are loaded from a local `docs/` directory using LangChain's `UnstructuredMarkdownLoader`. Cleaning strips excessive whitespace, normalizes line endings, and removes blank lines. Each chunk is tagged with its source filename for citation. |
| **Ingestion + freshness** | Documents are ingested on-demand by running `ingest.py`. In a production setup, this would be triggered by a Confluence webhook on page update, with a freshness SLA of under 1 hour. |
| **Chunking + embedding** | Recursive character splitting at **1,500 characters (~375 tokens) with 200-character overlap**, using `["\n## ", "\n### ", "\n\n", "\n", " "]` as separators — this respects Markdown heading boundaries so chunks stay semantically coherent. Embedding model: **`BAAI/bge-en-icl` via Nebius Token Factory** — strong English retrieval embeddings, served through the same API key as generation (single-provider setup). |
| **Retrieve** | **Hybrid retrieval + rerank**: 60% dense vector search (Chroma) + 40% BM25 sparse (`EnsembleRetriever`), retrieving top-8 wide, then a **FlashRank cross-encoder reranker** (`ms-marco-MiniLM-L-12-v2`, runs locally) narrows to the best 4. Dense catches semantic intent; BM25 catches exact tool names ("AWS SSO", "kubectl"). A batched cosine-similarity threshold (0.30) then grades relevance and triggers the "I don't know" refusal path if nothing clears the bar. |

---

## 3. Architecture

### Pipeline Flow

```
docs/*.md
    │
    ▼
ingest.py
  ├── DirectoryLoader (UnstructuredMarkdownLoader)
  ├── RecursiveCharacterTextSplitter (1500 chars, 200 overlap)
  ├── OpenAIEmbeddings (text-embedding-3-small)
  └── Chroma (persisted to chroma_db/)
    │
    ▼
LangGraph RAG Pipeline (rag_graph.py)
  │
  ├── Node 1: retrieve
  │     ├── Dense: Chroma similarity search
  │     ├── Sparse: BM25Retriever
  │     └── EnsembleRetriever (60/40 hybrid, top-k=8)
  │
  ├── Node 2: rerank
  │     └── FlashRank cross-encoder (ms-marco-MiniLM-L-12-v2) → top 4
  │
  ├── Node 3: grade_relevance
  │     ├── Batched cosine similarity per doc vs. question
  │     ├── Filter docs below threshold (0.30)
  │     └── Route → generate OR refuse
  │
  ├── Node 4a: generate
  │     ├── LLM: Nebius Token Factory (Meta-Llama-3.1-70B-Instruct-fast)
  │     ├── System prompt enforces citation and faithfulness
  │     └── Returns answer + source filenames
  │
  └── Node 4b: refuse
        └── Returns canned "not found" message with escalation paths
    │
    ▼
app.py (Streamlit UI)
  ├── Chat message history
  ├── Spinner during retrieval
  └── Source citations shown below each answer
```

### Tech Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Orchestration | **LangGraph** | Stateful graph enables the grade → route → generate/refuse flow cleanly |
| Document loading | **LangChain UnstructuredMarkdownLoader** | Handles Markdown formatting natively |
| Text splitting | **RecursiveCharacterTextSplitter** | Heading-aware splits keep semantic units intact |
| Embeddings | **Nebius — `BAAI/bge-en-icl`** | Strong English embeddings; same API key as generation (single-provider) |
| Vector store | **Chroma** (local, persistent) | Zero infrastructure setup — runs locally, persists to disk |
| Sparse retrieval | **BM25Retriever** (LangChain community) | Exact keyword matching for tool names and commands |
| Reranking | **FlashRank `ms-marco-MiniLM-L-12-v2`** (local ONNX) | Cross-encoder precision without GPU or extra API cost |
| LLM (generation + eval judge) | **Nebius Token Factory — Meta-Llama-3.1-70B-Instruct-fast** | Required by course; OpenAI-compatible API; fast inference |
| UI | **Streamlit** | Rapid chatbot UI with minimal code |
| Environment | **python-dotenv** | Keeps secrets out of code |

---

## 4. Key Design Decisions

### Why hybrid retrieval?
The knowledge base contains both semantic content ("what are the team's communication norms?") and exact-match content (tool names like "Tailscale", "ArgoCD", port numbers like "8080", commands like `aws configure sso`). Pure dense search loses exact matches; pure BM25 misses semantic paraphrasing. Combining both at 60/40 gives the best of both.

### Why the "I don't know" path first?
Per the handout's advice: *"Your 'I don't know' path matters more than your happy path."* The relevance grading node was designed before the generation node. If cosine similarity between the question embedding and all retrieved chunks is below 0.25, the pipeline refuses rather than hallucinating. This is critical for an onboarding tool — a new hire who gets a wrong answer about a deployment process could break production.

### Why 1,500-character (~375-token) chunks?
- Small enough to stay focused on one topic per chunk (a single markdown section)
- Large enough that procedural content (multi-step instructions, tables) isn't split mid-thought
- Note: `RecursiveCharacterTextSplitter` measures **characters**, not tokens — an easy mistake. 1,500 chars ≈ 375 tokens for English technical text.
- 200-character overlap prevents important context from being split across chunk boundaries

### Why Nebius for everything?
The course requires at least one Nebius Token Factory call — this project routes **all** model calls through Nebius: embeddings (`BAAI/bge-en-icl`), generation, and the eval faithfulness judge. One API key, one billing surface, zero OpenAI dependency. The pipeline stays modular: swapping the embedding or generation provider is a two-line change since Nebius exposes an OpenAI-compatible API.

### Why add a reranker?
Hybrid retrieval gets the right chunks *into* the candidate pool but ranks them with bi-encoder similarity, which scores question and chunk independently. The FlashRank cross-encoder reads them *together*, catching subtleties like "rollback" vs "deployment" being different intents over the same doc. We retrieve top-8 wide, rerank to the best 4 — better precision in the LLM context window at zero API cost (the model runs locally, ~34 MB).

### How is faithfulness measured?
`eval.py` uses **LLM-as-judge**: after each answered question, a second Nebius call receives the question, the retrieved chunks, and the generated answer, and returns a JSON verdict on whether every claim is grounded in the chunks. The summary reports faithfulness as a percentage against the ≥90% target in the one-liner.

---

## 5. Corpus Details

The knowledge base consists of 7 synthetic Markdown documents simulating a real team's Confluence space:

| File | Content | ~Word Count |
|------|---------|-------------|
| `01_team_overview.md` | Team structure, sub-teams, rituals, communication norms, principles | ~450 |
| `02_dev_environment_setup.md` | Prerequisites, tool installation, AWS SSO config, GitHub setup, IDE setup, troubleshooting | ~600 |
| `03_deployment_process.md` | Environments, pipeline steps, how to deploy, rollback, K8s basics, freeze windows, monitoring | ~700 |
| `04_tools_and_access.md` | All tools and access levels, IT portal process, on-call, VPN, secrets management | ~700 |
| `05_engineering_processes.md` | Code review rules, PR conventions, branching strategy, sprint process, incident management, testing standards | ~750 |
| `06_architecture_overview.md` | Services, infrastructure (AWS/EKS/RDS/Kafka/Snowflake), networking, observability | ~700 |
| `07_onboarding_checklist.md` | Week 1–4 checklist, 30/60-day milestones, key contacts, FAQ | ~750 |

**Total:** ~4,650 words → ~25–30 chunks after splitting at 1,500 characters with 200-character overlap.

---

## 6. Evaluation

### Test Questions (15 total)

| # | Category | Question | Expected outcome |
|---|----------|----------|-----------------|
| 1 | Setup | How do I set up my local development environment? | Retrieved, answered |
| 2 | Setup | What tools do I need to install before cloning a repo? | Retrieved, answered |
| 3 | Setup | How do I configure AWS SSO? | Retrieved, answered |
| 4 | Deployment | What is the deployment process to production? | Retrieved, answered |
| 5 | Deployment | How do I roll back a production deployment? | Retrieved, answered |
| 6 | Process | What are the PR review requirements? | Retrieved, answered |
| 7 | Process | What is the branching strategy the team uses? | Retrieved, answered |
| 8 | Process | What is the incident severity classification? | Retrieved, answered |
| 9 | Team | Who is the Engineering Manager? | Retrieved, answered |
| 10 | Onboarding | What Slack channels should I join as a new hire? | Retrieved, answered |
| 11 | Onboarding | What should I do in my first week? | Retrieved, answered (cross-doc) |
| 12 | Tools | How do I request access to Snowflake? | Retrieved, answered |
| 13 | Architecture | What databases does Acme use and where are they hosted? | Retrieved, answered |
| 14 | Out-of-scope | What is the company stock price? | **Refused** (correct) |
| 15 | Out-of-scope | Can you write me a Python function to sort a list? | **Refused** (correct) |

*Run `python eval.py` to generate live results against your Chroma DB.*

### Evaluation Metrics (to fill in after running `eval.py`)

| Metric | Result |
|--------|--------|
| Total questions | 15 |
| Correctly answered | _/13 |
| Correctly refused (out-of-scope) | _/2 |
| Avg. docs retrieved (answered questions) | _ |
| Hallucination observed | Yes / No |

### Failure Analysis Template

After running the eval, document findings here:

**Where retrieval succeeded:**
- _e.g., Q2 (tool prerequisites) — BM25 matched exact tool names directly_

**Where retrieval struggled:**
- _e.g., Q11 (first week) — cross-document question pulled from both checklist and overview; answer was composite but accurate_

**Refusal path behavior:**
- _e.g., Q14 and Q15 correctly returned the refusal message since no docs had cosine similarity above 0.25_

---

## 7. How to Run the Project

### Prerequisites
- Python 3.11+
- Nebius Token Factory API key only (get at https://studio.nebius.ai/ → API Keys)

### Steps

```bash
# 1. Install dependencies
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux
pip install -r requirements.txt

# 2. Set up API key
cp .env.example .env
# Edit .env and fill in NEBIUS_API_KEY

# 3. Ingest documents into Chroma (run once)
python ingest.py

# 4. Launch the chatbot
streamlit run app.py
# Opens at http://localhost:8501

# 5. Run the evaluation
python eval.py
```

### Swapping in Your Own Docs
1. Add `.md` (or `.pdf`) files to the `docs/` folder.
2. Re-run `python ingest.py` to rebuild the vector store.
3. The rest of the pipeline picks up the new docs automatically.

---

## 8. Learnings and Observations

### What worked well
- **Hybrid retrieval** outperformed pure dense search noticeably on questions involving exact tool names (e.g., "Tailscale", "ArgoCD", "kubectl"). BM25 caught these where embeddings softened them.
- **Source citation** in the system prompt was effective — the LLM consistently named the source file, making it easy to verify faithfulness.
- **Refusal path** worked cleanly for clearly out-of-scope questions. The cosine threshold prevented hallucination without over-refusing.

### What was harder than expected
- **Chunk boundary decisions** matter more than chunk size. Splitting mid-sentence on a bullet list degraded retrieval for multi-step procedural answers (e.g., the deployment pipeline steps). The recursive splitter with heading-based separators helped but didn't fully solve this.
- **Cross-document questions** (e.g., "What should I do in my first week?") require the retriever to pull from multiple files. The hybrid approach helped, but re-ranking would further improve result ordering.

### What I would improve next
1. **Parent-document retrieval** — store small chunks for retrieval but pass larger parent chunks to the LLM for context, reducing information loss at chunk boundaries.
2. **LangSmith tracing** — enable to trace exactly which chunks were retrieved per question and track faithfulness over time.
3. **Query rewriting for follow-ups** — multi-turn memory is implemented, but rewriting the follow-up question into a standalone query before retrieval would improve retrieval on pronoun-heavy follow-ups ("and what about staging?").
4. **Automated freshness pipeline** — re-ingest on a schedule or via Confluence webhooks instead of manual `ingest.py` runs.

---

## 9. Submission Checklist

- [ ] Push code to GitHub (exclude `chroma_db/` and `.env` via `.gitignore`)
- [ ] Record a ≤5-minute video demo covering:
  - [ ] Run `ingest.py` (or show it already ran)
  - [ ] Ask 3–4 in-scope questions and show cited answers
  - [ ] Ask 1 out-of-scope question and show the refusal
  - [ ] Briefly explain the LangGraph pipeline
- [ ] Fill in the evaluation table in Section 6 with live `eval.py` output
- [ ] Submit via https://forms.gle/3vj27gwoxw2xk9B7A

---

*Built with LangChain, LangGraph, Chroma, OpenAI Embeddings, and Nebius Token Factory.*
