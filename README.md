# Acme Corp Onboarding RAG Bot

**One-liner:** This RAG app helps new hires answer onboarding and setup questions from the team's Confluence-style knowledge base via a Streamlit chatbot with ≥90% faithfulness.

Built for The Gen Academy — Week 2 Project (Track 2: LangChain + LangGraph).

## Architecture

```
docs/*.md  →  ingest.py  →  Chroma (vector store)
                               ↓
User question  →  LangGraph pipeline:
                    retrieve (hybrid BM25 + dense)
                    → grade_relevance (cosine threshold)
                    → generate (Nebius LLM) or refuse
                    → Streamlit UI
```

**Key decisions:**
| Layer | Choice | Why |
|-------|--------|-----|
| Chunking | Recursive, 512 tokens, 64 overlap | Matches heading-based markdown structure |
| Embedding | OpenAI text-embedding-3-small | Fast, cheap, high quality for English text |
| Retrieval | Hybrid BM25 + dense (60/40) | Dense catches semantic intent; BM25 catches exact tool names / acronyms |
| Generation | Nebius Meta-Llama-3.1-70B-Instruct-fast | Required by course; fast inference |
| "I don't know" path | Cosine similarity threshold (0.25) | Prevents hallucination when no relevant docs retrieved |

## Setup

### 1. Clone / unzip and install dependencies
```bash
cd rag-onboarding-bot
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure API keys
```bash
cp .env.example .env
# Edit .env and fill in OPENAI_API_KEY and NEBIUS_API_KEY
```

Get your Nebius key at: https://studio.nebius.ai/

### 3. Ingest documents
```bash
python ingest.py
```
This loads the 7 markdown docs from `docs/`, chunks them, embeds them with OpenAI, and stores them in a local Chroma DB (`chroma_db/`). Takes ~30 seconds.

### 4. Run the chatbot
```bash
streamlit run app.py
```
Opens at http://localhost:8501

### 5. Run the evaluation
```bash
python eval.py
```
Runs 15 questions (13 in-scope + 2 out-of-scope) and prints a summary with retrieval stats.

## Replacing the Sample Docs

To use your own Confluence/team docs:
1. Export your pages as Markdown or PDF (Confluence: Space Settings → Export).
2. Place `.md` files in the `docs/` folder (or add PDF support by changing the loader in `ingest.py`).
3. Re-run `python ingest.py`.

## Project Structure

```
rag-onboarding-bot/
├── docs/                    # Knowledge base (7 markdown files)
│   ├── 01_team_overview.md
│   ├── 02_dev_environment_setup.md
│   ├── 03_deployment_process.md
│   ├── 04_tools_and_access.md
│   ├── 05_engineering_processes.md
│   ├── 06_architecture_overview.md
│   └── 07_onboarding_checklist.md
├── chroma_db/               # Created by ingest.py (gitignored)
├── ingest.py                # Load → clean → chunk → embed → store
├── rag_graph.py             # LangGraph RAG pipeline
├── app.py                   # Streamlit chatbot UI
├── eval.py                  # 15-question evaluation script
├── requirements.txt
├── .env.example
└── README.md
```

## Submission Checklist

- [ ] GitHub repo with all code pushed
- [ ] `chroma_db/` added to `.gitignore` (not committed — rebuilt by ingest.py)
- [ ] `.env` added to `.gitignore` (secrets never committed)
- [ ] Video demo recorded (≤5 min): show ingest, ask 3–4 questions, show refusal case
- [ ] Evaluation report: run `python eval.py`, screenshot/copy output
- [ ] Google Doc with: project overview, corpus description, chunking decisions, eval results, learnings
