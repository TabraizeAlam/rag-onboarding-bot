# Acme Corp Onboarding RAG Bot

**One-liner:** This RAG app helps new hires answer onboarding and setup questions from the team's Confluence-style knowledge base via a Streamlit chatbot with ≥90% faithfulness.

Built for The Gen Academy — Week 2 Project (Track 2: LangChain + LangGraph).

## Architecture

```
docs/*.md  →  ingest.py  →  Chroma (vector store)
                               ↓
User question  →  LangGraph pipeline:
                    rewrite_query (LLM fixes typos/phrasing, resolves follow-ups)
                    → retrieve (hybrid BM25 + dense, top-8)
                    → rerank_and_grade (FlashRank cross-encoder:
                        reorders to top-4; hard-refuses only true junk)
                    → generate (Nebius Llama-70B) or refuse
                    → Streamlit UI (multi-turn + context inspector)
```

**Key decisions:**
| Layer | Choice | Why |
|-------|--------|-----|
| Chunking | Recursive, 1,500 chars (~375 tokens), 200 overlap | Keeps a full markdown section per chunk |
| Embedding | Nebius `BAAI/bge-en-icl` | Single API key for whole project; strong English embeddings |
| Retrieval | Hybrid BM25 + dense (60/40), top-8 | Dense catches semantic intent; BM25 catches exact tool names / acronyms |
| Reranking | FlashRank `ms-marco-MiniLM-L-12-v2` (local) | Cross-encoder reads question+chunk together; free, no GPU |
| Generation | Nebius Llama-3.3-70B-Instruct | Required by course; fast inference |
| Query rewriting | LLM pre-step before retrieval | Real users type typos and informal phrasing; rewrite also makes follow-up questions standalone |
| "I don't know" path | Two-tier: cross-encoder floor (0.005) + grounded LLM judgment | Measured: true junk scores ≈ 0.0001 on every chunk; related-but-differently-phrased text scores 10–100× higher and deserves the LLM's call |
| Eval | LLM-as-judge faithfulness scoring | Measures grounding, not just retrieval — per the handout |

**Only one API key needed: Nebius.** Both embeddings and generation run through Nebius Token Factory's OpenAI-compatible API.

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

### 2. Configure API key (only Nebius needed)
```bash
cp .env.example .env
# Edit .env and fill in NEBIUS_API_KEY
```

Get Nebius key at: https://studio.nebius.ai/ → API Keys

### 3. Ingest documents
```bash
python ingest.py
```
This loads the 7 markdown docs from `docs/`, chunks them, embeds them via Nebius (`BAAI/bge-en-icl`), and stores them in a local Chroma DB (`chroma_db/`). Takes ~30 seconds.

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
