# Project Documentation — Meridian Data Platform Onboarding RAG Bot

**Course:** The Gen Academy — Mastering Agentic AI Bootcamp  
**Week:** 2 — Gen AI Building Blocks  
**Track:** Track 2 — Code-heavy (LangChain + LangGraph)  
**Use Case:** Project 1 — Enterprise Policy Q&A Bot (adapted for data platform team onboarding)

---

## 1. Project One-Liner

> My RAG app helps **new Data Platform team members** answer **onboarding, environment setup, pipeline workflow, and data governance questions** from **Meridian's internal team knowledge base (7 Confluence-style markdown documents, ~8,000 words, grounded in publicly available Meridian information)** via a **Streamlit chatbot** with **≥90% faithfulness** and responses under **5 seconds**.

---

## 2. The RAG Framework

| Field | Decision |
|-------|----------|
| **Use case** | New Data Platform team members at Meridian ask questions like "How do I set up Snowflake?" or "What is the medallion architecture?" through a Streamlit chat interface backed by the team's internal knowledge base. |
| **Corpus** | 7 Markdown documents (~8,000 words total) covering: data platform team overview, developer environment setup, data pipeline workflow, tools & access, data governance framework, platform architecture, and onboarding checklist. All content is grounded in publicly available Meridian information (annual reports, corporate website, public job postings). |
| **Ingestion + cleaning** | Documents are loaded from a local `docs/` directory using LangChain's `TextLoader`. Cleaning strips excessive whitespace, normalizes line endings, and removes blank lines. Each chunk is tagged with its source filename for citation. |
| **Ingestion + freshness** | Documents are ingested on-demand by running `ingest.py`. In a production setup, this would be triggered by a Confluence webhook on page update, with a freshness SLA of under 1 hour. |
| **Chunking + embedding** | Recursive character splitting at **1,500 characters (~375 tokens) with 200-character overlap**, using `["\n## ", "\n### ", "\n\n", "\n", " "]` as separators — this respects Markdown heading boundaries so chunks stay semantically coherent. Embedding model: **`Qwen/Qwen3-Embedding-8B` via Nebius Token Factory** — strong multilingual embeddings, served through the same API key as generation (single-provider setup). |
| **Retrieve** | **Hybrid retrieval + rerank**: 60% dense vector search (Chroma) + 40% BM25 sparse (custom `_EnsembleRetriever` with reciprocal-rank fusion), retrieving top-8 wide, then a **FlashRank cross-encoder reranker** (`ms-marco-MiniLM-L-12-v2`, runs locally) narrows to the best 4. Dense catches semantic intent; BM25 catches exact tool names ("Snowflake", "dbt", "Atlan"). The cross-encoder's calibrated scores also gate the refusal path: if no passage scores ≥ 0.005, the bot refuses instead of hallucinating. |

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
  ├── Node 1: rewrite_query
  │     └── LLM normalizes the message: fixes typos, makes follow-ups
  │         standalone using chat history ("deployment pipleine" →
  │         "What is the deployment pipeline process?")
  │
  ├── Node 2: retrieve
  │     ├── Dense: Chroma similarity search
  │     ├── Sparse: BM25Retriever
  │     └── Reciprocal-rank fusion (60/40 hybrid, top-k=8)
  │
  ├── Node 3: rerank_and_grade
  │     ├── FlashRank cross-encoder (ms-marco-MiniLM-L-12-v2) → top 4
  │     ├── Hard refusal only below floor 0.005 (measured: junk ≈ 0.0001)
  │     └── Route → generate OR refuse  (zero API calls — runs locally)
  │
  ├── Node 4a: generate
  │     ├── LLM: Nebius Token Factory (Llama-3.3-70B-Instruct)
  │     ├── System prompt enforces citation and faithfulness
  │     └── Returns answer + source filenames
  │
  └── Node 4b: refuse  (only when no chunk clears the junk floor)
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
| Embeddings | **Nebius — `Qwen/Qwen3-Embedding-8B`** | Strong multilingual embeddings; same API key as generation (single-provider) |
| Vector store | **Chroma** (local, persistent) | Zero infrastructure setup — runs locally, persists to disk |
| Sparse retrieval | **BM25Retriever** (LangChain community) | Exact keyword matching for tool names and commands |
| Reranking | **FlashRank `ms-marco-MiniLM-L-12-v2`** (local ONNX) | Cross-encoder precision without GPU or extra API cost |
| LLM (generation + eval judge) | **Nebius Token Factory — Llama-3.3-70B-Instruct** | Required by course; OpenAI-compatible API; fast inference |
| UI | **Streamlit** | Rapid chatbot UI with minimal code |
| Environment | **python-dotenv** | Keeps secrets out of code |

---

## 4. Key Design Decisions

### Why hybrid retrieval?
The knowledge base contains both semantic content ("what is the data governance framework?") and exact-match content (tool names like "Atlan", "Soda", "dbt", commands like `dbt run --select staging.*`). Pure dense search loses exact matches; pure BM25 misses semantic paraphrasing. Combining both at 60/40 gives the best of both.

### Why the "I don't know" path first?
Per the handout's advice: *"Your 'I don't know' path matters more than your happy path."* The refusal gate was designed before the generation node, and then **calibrated against measured data**: on this corpus, truly out-of-scope questions ("stock price", "weather") score ≈ 0.0001 on every chunk with the cross-encoder, while topically-related questions score 10–100× higher even when phrased differently than the docs. The pipeline therefore hard-refuses only below a 0.005 floor; mid-scoring chunks go to the LLM, whose grounded prompt instructs it to say what the docs do and don't cover. This is critical for an onboarding tool — a new hire who gets a wrong answer about a deployment process could break production.

### Why 1,500-character (~375-token) chunks?
- Small enough to stay focused on one topic per chunk (a single markdown section)
- Large enough that procedural content (multi-step instructions, tables) isn't split mid-thought
- Note: `RecursiveCharacterTextSplitter` measures **characters**, not tokens — an easy mistake. 1,500 chars ≈ 375 tokens for English technical text.
- 200-character overlap prevents important context from being split across chunk boundaries

### Why Nebius for everything?
The course requires at least one Nebius Token Factory call — this project routes **all** model calls through Nebius: embeddings (`BAAI/bge-en-icl`), generation, and the eval faithfulness judge. One API key, one billing surface, zero OpenAI dependency. The pipeline stays modular: swapping the embedding or generation provider is a two-line change since Nebius exposes an OpenAI-compatible API.

### Why add a reranker?
Hybrid retrieval gets the right chunks *into* the candidate pool but ranks them with bi-encoder similarity, which scores question and chunk independently. The FlashRank cross-encoder reads them *together*, catching subtleties like "rollback" vs "deployment" being different intents over the same doc. We retrieve top-8 wide, rerank to the best 4 — better precision in the LLM context window at zero API cost (the model runs locally, ~34 MB).

### Why does the reranker also gate the refusal path?
An earlier design graded relevance with embedding cosine similarity, but `Qwen3-Embedding-8B` scores ~0.5 even for unrelated pairs, so a fixed threshold either never refuses or refuses everything. Cross-encoder scores are well-calibrated — irrelevant passages score near 0.0, relevant ones near 0.9 — so the same rerank pass doubles as the refusal gate. This removed two embedding API calls per question (faster, cheaper) while making the "I don't know" path actually reliable. Measured on this corpus: true out-of-scope queries ("weather", "portfolio return") score ≈ 0.0001 on every chunk; data-platform queries score ≥ 0.005.

### How is faithfulness measured?
`eval.py` uses **LLM-as-judge**: after each answered question, a second Nebius call receives the question, the retrieved chunks, and the generated answer, and returns a JSON verdict on whether every claim is grounded in the chunks. The summary reports faithfulness as a percentage against the ≥90% target in the one-liner.

---

## 5. Corpus Details

The knowledge base consists of 7 Markdown documents tailored to Meridian's Data Platform team, all grounded in publicly available information (Meridian's annual reports, corporate website at meridianinvestments.ca, and public job postings). No internal, confidential, or proprietary data is used.

| File | Content | ~Word Count |
|------|---------|-------------|
| `01_data_platform_team.md` | Meridian's mandate as a Crown corporation, Data & Analytics team overview, Business Transformation Program, roles and responsibilities | ~600 |
| `02_environment_setup.md` | Prerequisites, Snowflake SSO setup, Databricks access, dbt profile configuration, Atlan, Soda Cloud, Azure DevOps access | ~750 |
| `03_data_pipeline_workflow.md` | Medallion architecture (Bronze/Silver/Gold), data source types, dbt model development, Soda checks, PR process, deployment, orchestration | ~900 |
| `04_tools_and_access.md` | Snowflake, Databricks, dbt, Atlan, Soda, Power BI, Azure DevOps — how each is used and how to get access | ~850 |
| `05_data_governance.md` | Data catalog (Atlan), data quality (Soda), data classification labels, lineage tracking, retention policies, access request process | ~750 |
| `06_platform_architecture.md` | End-to-end architecture diagram, Azure cloud setup, Snowflake warehouse strategy, Databricks cluster strategy, dbt project structure, CI/CD pipeline, monitoring and alerting | ~950 |
| `07_onboarding_checklist.md` | Week 1–4 onboarding plan, before-Day-1 provisioning, shadow sessions, first PR task, key contacts, quick-reference table | ~850 |

**Total:** ~5,650 words → ~30–38 chunks after splitting at 1,500 characters with 200-character overlap.

**Why this corpus is authentic and differentiated:**
The documents reflect the real tools (Databricks, dbt, Snowflake, Soda, Atlan, Power BI) and investment management domain context (Crown corporation, pension fund mandate, medallion architecture for investment data) that characterize Meridian's actual data platform work. This gives the RAG bot a genuine use-case narrative: it could be deployed as an internal tool to help onboard new data developers, reducing the time managers spend answering repetitive setup and process questions.

---

## 6. Evaluation

### Test Questions (15 total)

| # | Category | Question | Expected outcome |
|---|----------|----------|-----------------|
| 1 | Setup | How do I set up my local dbt environment to connect to Snowflake? | Retrieved, answered |
| 2 | Setup | What tools do I need to install as a new data developer? | Retrieved, answered |
| 3 | Setup | How do I get access to Databricks? | Retrieved, answered |
| 4 | Setup | Where do I request Snowflake access for the CONFIDENTIAL data role? | Retrieved, answered |
| 5 | Architecture | What are the Bronze, Silver, and Gold layers in the data platform? | Retrieved, answered |
| 6 | Architecture | What is the medallion architecture? | Retrieved, answered |
| 7 | Architecture | Which cloud does Meridian's data platform run on? | Retrieved, answered |
| 8 | Pipeline | What is the branching strategy and how do I name my feature branch? | Retrieved, answered |
| 9 | Pipeline | What needs to happen before a new pipeline can go to production? | Retrieved, answered |
| 10 | Pipeline | How do dbt models get deployed to production? | Retrieved, answered |
| 11 | Governance | What is Atlan used for and what do I need to do there? | Retrieved, answered |
| 12 | Governance | How do I write a Soda data quality check? | Retrieved, answered |
| 13 | Onboarding | What should I do in my first week as a new team member? | Retrieved, answered (cross-doc) |
| 14 | Out-of-scope | What is Meridian's current portfolio return this quarter? | **Refused** (correct) |
| 15 | Out-of-scope | What is the weather forecast for Edmonton tomorrow? | **Refused** (correct) |

*Run `python eval.py` to generate live results against your Chroma DB and paste the summary output below.*

### Evaluation Results (run `python eval.py` and paste output here)

```
[ Run python eval.py and paste the SUMMARY output here before submission ]
```

### Failure Analysis

After running the eval, document findings here:

**Where retrieval succeeded:**
- _e.g., Q5 (medallion architecture) — BM25 matched exact term "Bronze" and "Silver" directly_

**Where retrieval struggled:**
- _e.g., Q13 (first week) — cross-document question pulled from both checklist and team overview_

**Refusal path behavior:**
- _e.g., Q14 and Q15 correctly returned the refusal message — cross-encoder scored all chunks near 0.0001 for these queries_

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
- **Hybrid retrieval** outperformed pure dense search on questions involving exact tool names (e.g., "Atlan", "Soda", "dbt"). BM25 caught these where embeddings softened them.
- **Source citation** in the system prompt was effective — the LLM consistently named the source file, making it easy to verify faithfulness.
- **Query rewriting node** fixed false refusals on informal/typo-heavy queries. "how do i conect to snwflake" correctly rewrites to "How do I connect to Snowflake?" before retrieval.
- **Refusal path** worked cleanly for out-of-scope questions. The cross-encoder floor (0.005) is well-calibrated: investment portfolio questions ("what's Meridian's quarterly return?") scored ≈ 0.0001 on every chunk.

### What was harder than expected
- **Domain calibration of the refusal gate**: investment-adjacent but out-of-scope questions (e.g., "what is Meridian's AUM?") may score higher than true junk if the corpus mentions Meridian's mandate. The LLM's grounded prompt instructs it to only answer from docs, which catches these edge cases.
- **Cross-document questions** (e.g., "What should I do in my first week?") require the retriever to pull from both the checklist and the team overview. The hybrid approach helped, but the answer synthesizes across two docs.

### What I would improve next
1. **Parent-document retrieval** — store small chunks for retrieval but pass larger parent chunks to the LLM, reducing information loss at chunk boundaries.
2. **LangSmith tracing** — enable to trace exactly which chunks were retrieved per question and track faithfulness over time in production.
3. **Confluence/SharePoint integration** — in a real deployment, re-ingest on a webhook when a Confluence page is updated, rather than manual `ingest.py` runs.
4. **Role-based access filtering** — in production, filter retrievable chunks by the user's data classification access level (e.g., don't surface RESTRICTED data governance docs to viewers without that role).

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

*Built with LangChain, LangGraph, Chroma, FlashRank, and Nebius Token Factory. Corpus grounded in publicly available Meridian information.*
