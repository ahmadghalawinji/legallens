# LegalLens

AI-powered contract risk analyzer. Upload a PDF or DOCX contract and a multi-agent system extracts clauses, classifies risk levels, retrieves legal precedents, and generates plain-language recommendations with suggested alternative clause language.

**100% free stack** — LLMs run locally via Ollama or on the Groq free tier. No paid APIs.

---

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project scaffold, infrastructure, LLM factory | ✅ Done |
| 2 | Document parsing (PDF + DOCX) | ✅ Done |
| 3 | Core agents — clause extraction + risk classification | ✅ Done |
| 4 | API endpoints & async pipeline (Celery) | ✅ Done |
| 5 | Knowledge base — RAG with ChromaDB | ✅ Done |
| 6 | Recommendation generator + report assembler | ✅ Done |
| 7 | LangGraph orchestration | ✅ Done |
| 8 | Frontend (Next.js) | ✅ Done |
| 9 | Evaluation harness, PDF reports, API docs | ✅ Done |

---

## Stack

**Backend:** Python 3.11+, FastAPI, LangChain + LangGraph, Celery + Redis, ChromaDB, sentence-transformers

**Frontend:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui

**LLMs (all free):**
- [Ollama](https://ollama.ai) — fully local, no internet needed (`llama3.1:8b`, `qwen2.5:1.5b`)
- [Groq](https://console.groq.com) — free tier, 30 req/min, very fast
- [Gemini](https://aistudio.google.com) — free daily quota, `gemini-2.0-flash`
- [HuggingFace](https://huggingface.co/settings/tokens) — free inference API

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/ahmadghalawinji/legallens.git
cd legallens
make install
```

### 2. Configure LLM provider

```bash
cp .env.example .env
```

Edit `.env` and choose a provider:

**Option A — Ollama (fully local, recommended):**
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:1.5b   # or llama3.1:8b, mistral:7b
LLM_REQUEST_DELAY=0          # no delay needed for local
```
Then pull the model:
```bash
make setup-ollama
# or manually: ollama pull qwen2.5:1.5b
```

**Option B — Groq (free tier, fastest cloud option):**
```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...         # from https://console.groq.com
LLM_REQUEST_DELAY=2.0        # required — Groq free tier is 6,000 TPM
```

**Option C — Gemini (free daily quota):**
```env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=AIza...       # from https://aistudio.google.com
GEMINI_MODEL=gemini-2.0-flash
LLM_REQUEST_DELAY=2.0        # recommended to stay within free quota
```

**Option D — HuggingFace (free tier):**
```env
LLM_PROVIDER=huggingface
HF_API_TOKEN=hf_...          # from https://huggingface.co/settings/tokens
```

### 3. Start infrastructure (Redis + ChromaDB)

```bash
docker-compose up -d redis chromadb
```

### 4. Start the backend API

```bash
# Terminal 1 — FastAPI server
uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```

### 5. Start the Celery worker

```bash
# Terminal 2 — async task worker (required for contract analysis)
celery -A backend.celery_app worker --loglevel=info
```

### 6. Start the frontend

```bash
# Terminal 3 — Next.js dev server
cd frontend
npm install       # first time only
npm run dev
```

Frontend runs at `http://localhost:3000`, backend API at `http://localhost:8080`.

> **One-command alternative:** `make dev` runs steps 3–4 together (Docker + uvicorn).  
> You still need to start the Celery worker and frontend separately.

### 7. Verify

```bash
curl http://localhost:8080/api/v1/health
# {"status": "ok", ...}
```

---

## API

All responses follow the shape:
```json
{
  "status": "string",
  "data": null,
  "errors": null,
  "metadata": null
}
```

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/contracts/analyze` | Upload and analyze a contract |
| `GET` | `/api/v1/tasks/{task_id}` | Poll async analysis task |

Full API docs at `http://localhost:8080/docs` when the server is running.

---

## Development

```bash
make test       # Run unit tests with coverage
make lint       # ruff + mypy
make format     # black + ruff --fix
make eval       # Run LLM evaluation suite (calls real LLMs)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama` \| `groq` \| `gemini` \| `huggingface` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | Ollama model name (e.g. `qwen2.5:1.5b`) |
| `GROQ_API_KEY` | — | Groq free tier key |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model name |
| `GOOGLE_API_KEY` | — | Gemini API key (Google AI Studio) |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model name (use `gemini-2.0-flash`) |
| `HF_API_TOKEN` | — | HuggingFace token |
| `LLM_REQUEST_DELAY` | `0.0` | Seconds between LLM calls — set `2.0` for cloud free tiers |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Local embedding model (sentence-transformers) |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `CHROMA_HOST` | `localhost` | ChromaDB host |
| `CHROMA_PORT` | `8000` | ChromaDB port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_FILE_SIZE_MB` | `20` | Max upload size |

---

## Architecture

```
Upload (PDF/DOCX)
       │
       ▼
┌─────────────┐
│  Doc Parser  │  ← PyMuPDF / python-docx
└──────┬──────┘
       │ ParsedDocument
       ▼
┌─────────────────┐
│ Clause Extractor │  ← Llama 3.1 via Ollama/Groq, PydanticOutputParser
└──────┬──────────┘
       │ list[ExtractedClause]
       ▼
┌──────────────────────────────────────┐
│  PER CLAUSE (parallel via asyncio):  │
│  ┌────────────────┐ ┌─────────────┐  │
│  │ Risk Classifier │ │  Precedent  │  │
│  │ (chain-of-     │ │  Retriever  │  │
│  │  thought)      │ │  (RAG)      │  │
│  └───────┬────────┘ └──────┬──────┘  │
│          └────────┬────────┘         │
│          ▼                           │
│  ┌───────────────────────────────┐   │
│  │  Recommendation Generator     │   │
│  └───────────────────────────────┘   │
└──────────────────┬───────────────────┘
                   ▼
          ┌────────────────┐
          │ Report Assembler│
          └────────────────┘
```

---

## Project Structure

```
legallens/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings (pydantic-settings)
│   ├── celery_app.py        # Celery configuration
│   ├── api/routes/          # health, contracts, tasks
│   ├── core/
│   │   ├── llm.py           # LLM provider factory ← all agents use this
│   │   ├── agents/          # clause_extractor, risk_classifier, ...
│   │   ├── parsers/         # pdf_parser, docx_parser
│   │   └── prompts/         # prompt templates
│   ├── knowledge/           # embeddings, vector store, retriever
│   ├── services/            # analysis, report, chat
│   └── tasks/               # Celery tasks
├── frontend/                # Next.js app
├── tests/
│   ├── unit/                # mocked — runs in CI
│   ├── integration/         # requires running services
│   └── eval/                # LLM quality evaluation
├── scripts/                 # index_corpus, run_eval, seed_data
└── docs/                    # architecture, api, evaluation
```

---

## License

MIT
