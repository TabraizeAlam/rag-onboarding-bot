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
| **Retrieve** | **Hybrid retrieval + rerank**: 60% dense vector search (Chroma) + 40% BM25 sparse (`EnsembleRetriever`), retrieving top-8 wide, then a **FlashRank cross-encoder reranker** (`ms-marco-MiniLM-L-12-v2`, runs locally) narrows to the best 4. Dense catches semantic intent; BM25 catches exact tool names ("AWS SSO", "kubectl"). The cross-encoder's calibrated scores also gate the refusal path: if no passage scores ≥ 0.30, the bot says "I don't know" instead of hallucinating. |

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
| Embeddings | **Nebius — `BAAI/bge-en-icl`** | Strong English embeddings; same API key as generation (single-provider) |
| Vector store | **Chroma** (local, persistent) | Zero infrastructure setup — runs locally, persists to disk |
| Sparse retrieval | **BM25Retriever** (LangChain community) | Exact keyword matching for tool names and commands |
| Reranking | **FlashRank `ms-marco-MiniLM-L-12-v2`** (local ONNX) | Cross-encoder precision without GPU or extra API cost |
| LLM (generation + eval judge) | **Nebius Token Factory — Llama-3.3-70B-Instruct** | Required by course; OpenAI-compatible API; fast inference |
| UI | **Streamlit** | Rapid chatbot UI with minimal code |
| Environment | **python-dotenv** | Keeps secrets out of code |

---

## 4. Key Design Decisions

### Why hybrid retrieval?
The knowledge base contains both semantic content ("what are the team's communication norms?") and exact-match content (tool names like "Tailscale", "ArgoCD", port numbers like "8080", commands like `aws configure sso`). Pure dense search loses exact matches; pure BM25 misses semantic paraphrasing. Combining both at 60/40 gives the best of both.

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
An earlier design graded relevance with embedding cosine similarity, but BGE-family embeddings are poorly calibrated for that: even unrelated question/passage pairs score ~0.5, so a fixed threshold either never refuses or refuses everything. Cross-encoder scores are well-calibrated — irrelevant passages score near 0.0, relevant ones near 0.9 — so the same rerank pass doubles as the refusal gate. This removed two embedding API calls per question (faster, cheaper) while making the "I don't know" path actually reliable.

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

====================================================================================================
ANSWERS

Q1: How do I set up my local development environment?
A:  According to `02_dev_environment_setup.md`, to set up your local development environment, you need to install the following tools with the specified versions:
- Git (>= 2.40) via `brew install git` or [git-scm.com](https://git-scm.com)
- Docker Desktop (>= 4.30) from [docker.com/products/docker-desk...
Sources: 07_onboarding_checklist.md, 02_dev_environment_setup.md
Judge: faithful=False — The answer mentions `07_onboarding_checklist.md`, which is not present in the retrieved context.

Q2: What tools do I need to install before cloning a repo?
A:  According to 02_dev_environment_setup.md, the following tools need to be installed before cloning any repository:
1. Git (version >= 2.40)
2. Docker Desktop (version >= 4.30)
3. Node.js (version 20 LTS)
4. Python (version 3.11)
5. kubectl (version >= 1.28)
6. Terraform (version >= 1.7)
7. AWS CLI (v...
Sources: 02_dev_environment_setup.md
Judge: faithful=True — The answer accurately lists all the tools and their required versions as specified in the retrieved context.

Q3: How do I configure AWS SSO?
A:  According to 02_dev_environment_setup.md, to configure AWS SSO, you should run the command `aws configure sso` and provide the following information: 
- SSO Start URL: https://acme.awsapps.com/start
- SSO Region: us-west-2
- Default region: us-west-2
- Default output format: json
The profile name mu...
Sources: 02_dev_environment_setup.md, 07_onboarding_checklist.md, 06_architecture_overview.md
Judge: faithful=True — The answer accurately reflects the information provided in the retrieved context for configuring AWS SSO.

Q4: What is the deployment process to production?
A:  According to `03_deployment_process.md`, the deployment process to production involves the following steps: 

1. Merging your PR to `main` (which triggers an auto-deploy to staging).
2. Verifying that staging looks good.
3. Creating a release tag using `git tag v1.2.3 -m "Release v1.2.3: [brief desc...
Sources: 03_deployment_process.md, 07_onboarding_checklist.md
Judge: faithful=True — The answer accurately reflects the deployment process to production as described in the retrieved context.

Q5: How do I roll back a production deployment?
A:  According to 03_deployment_process.md, if a production deploy causes issues, you can roll back via Helm (which is the fastest method) by running the command `helm rollback <service-name> -n production`. Alternatively, you can redeploy the previous image tag via GitHub Actions by going to Actions, fi...
Sources: 03_deployment_process.md, 07_onboarding_checklist.md
Judge: faithful=True — The answer accurately reflects the information provided in the retrieved context regarding the rollback process.

Q6: What are the PR review requirements?
A:  According to 05_engineering_processes.md, the PR review requirements include: 
- At least 1 approval from a team member (not the author)
- 2 approvals required for specific changes (CI/CD pipelines, Terraform infrastructure, shared libraries, or production secrets)
- All CI checks must pass (lint, t...
Sources: 05_engineering_processes.md
Judge: faithful=True — Every factual claim in the answer is directly supported by the retrieved context under the PR Requirements section.

Q7: What is the branching strategy the team uses?
A:  According to 05_engineering_processes.md, the team uses **trunk-based development** with specific branch types: `main` for the always-deployable protected branch, `feature/<ticket-id>-short-description` for short-lived feature branches, and `hotfix/<description>` for P0/P1 production fixes only.
Sources: 05_engineering_processes.md
Judge: faithful=True — The answer accurately reflects the branching strategy described in the retrieved context.

Q8: What is the incident severity classification?
A:  According to 05_engineering_processes.md, the incident severity classification is as follows: 
- P0: Production down, all users affected
- P1: Major feature broken, significant user impact
- P2: Partial degradation, workaround exists
- P3: Minor issue, cosmetic.
Sources: 05_engineering_processes.md
Judge: faithful=True — The answer directly quotes the severity levels and descriptions from the retrieved context without adding or modifying any information.

Q9: Who is the Engineering Manager?
A:  According to 01_team_overview.md, the Engineering Manager is David Park (david.park@acme.com).
Sources: 01_team_overview.md
Judge: faithful=True — The retrieved context explicitly states that the Engineering Manager is David Park (david.park@acme.com) under the Team Overview section.

Q10: What Slack channels should I join as a new hire?
A:  According to 04_tools_and_access.md, as a new hire, you should join the following Slack channels immediately:

- `#general` — company-wide announcements
- `#eng-announcements` — engineering-wide announcements
- `#team-general` — Platform Engineering team channel
- `#infra-team`, `#devex-team`, or `#...
Sources: 01_team_overview.md, 07_onboarding_checklist.md, 04_tools_and_access.md
Judge: faithful=None — Judge output unparseable: {"faithful": false, "reason": The answer mentions 04_tools_and_access.md and 07_onboarding_checklist

Q11: What should I do in my first week?
A:  According to `07_onboarding_checklist.md`, in your first week, you should follow the "Week 1: Get Set Up" checklist, which includes tasks such as receiving your laptop, setting up your Google Workspace account, joining Slack, attending the New Hire Orientation, and meeting with your Engineering Mana...
Sources: 07_onboarding_checklist.md
Judge: faithful=None — Judge output unparseable: {"faithful": false, "reason": The retrieved context is actually titled "# New Hire Onboarding Checkl

Q12: How do I request access to Snowflake?
A:  According to 04_tools_and_access.md, to request access to Snowflake, you should submit a request via the IT portal at `it.internal.acme.com` and select "Snowflake Read". Your manager must approve the request.
Sources: 04_tools_and_access.md
Judge: faithful=True — Every factual claim in the answer is directly supported by the information provided in the retrieved context.

Q13: What databases does Acme use and where are they hosted?
A:  According to 06_architecture_overview.md, Acme Corp uses the following databases: 
- PostgreSQL, which is hosted on AWS RDS in Multi-AZ mode with automated backups.
- Redis, which is hosted on AWS ElastiCache with 2 replicas.
- Kafka, which is hosted on AWS MSK (Managed Streaming for Kafka) with 3 b...
Sources: 06_architecture_overview.md, 04_tools_and_access.md
Judge: faithful=True — Every factual claim in the answer is directly supported by the retrieved context in the section titled 'Databases'.

Q14: What is the company stock price?
A:  I couldn't find relevant information in the team knowledge base to answer your question. Please check the Confluence wiki, ask in the appropriate Slack channel (#devex-team, #infra-team, #data-platform), or reach out to your onboarding buddy.
Sources: none

Q15: Can you write me a Python function to sort a list?
A:  I couldn't find relevant information in the team knowledge base to answer your question. Please check the Confluence wiki, ask in the appropriate Slack channel (#devex-team, #infra-team, #data-platform), or reach out to your onboarding buddy.
Sources: none

====================================================================================================
SUMMARY
  In-scope questions answered:  13/13
  Correct refusals:             2/2 out-of-scope questions
  Faithfulness:                 10/11 = 91%  (target: >=90%)

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
