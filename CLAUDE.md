# LegalLens — Claude Code Instructions

## Project

LegalLens is an open-source, AI-powered contract risk analyzer. Users upload a PDF/DOCX contract and a multi-agent system extracts clauses, classifies risk levels, retrieves legal precedents, and generates plain-language recommendations with suggested alternative clause language.

**100% free stack — no paid APIs.** LLMs run locally via Ollama or via Groq free tier.

**Backend**: Python 3.11+, FastAPI, LangChain + LangGraph, Ollama (Llama 3.1 / Mistral), sentence-transformers, ChromaDB, Celery + Redis
**Frontend**: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui

## Commands

```bash
make install        # Install all Python + frontend dependencies
make setup-ollama   # Pull required Ollama models
make dev            # Start backend + Redis + ChromaDB (docker-compose up, then uvicorn)
make test           # Run all unit + integration tests with coverage
make lint           # Run ruff + mypy
make format         # Run black + ruff --fix
make eval           # Run LLM evaluation suite
make docker-build   # Build all Docker images
make index          # Index legal corpus into ChromaDB
```

## LLM Provider Strategy (all free)

The system supports three free LLM backends, configured via `LLM_PROVIDER` env var:

### Option 1: Ollama (fully local, no internet needed)
```bash
# Install: https://ollama.ai
ollama pull llama3.1:8b        # Main model for extraction + classification
ollama pull mistral:7b         # Alternative / fallback
```
Set: `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://localhost:11434`

### Option 2: Groq (free tier — 30 req/min, very fast)
```bash
# Get free API key: https://console.groq.com
```
Set: `LLM_PROVIDER=groq`, `GROQ_API_KEY=gsk_...`
Models: `llama-3.1-8b-instant` (extraction), `llama-3.1-70b-versatile` (classification)

### Option 3: HuggingFace Inference API (free tier)
```bash
# Get free token: https://huggingface.co/settings/tokens
```
Set: `LLM_PROVIDER=huggingface`, `HF_API_TOKEN=hf_...`

**Embeddings always run locally** via sentence-transformers (`all-MiniLM-L6-v2`), no API needed.

## Repo Structure

```
legallens/
├── CLAUDE.md
├── README.md
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── .gitignore
├── .github/workflows/ci.yml
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings via pydantic-settings
│   ├── celery_app.py            # Celery configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── contracts.py     # POST /api/v1/contracts/analyze
│   │   │   ├── tasks.py         # GET /api/v1/tasks/{task_id}
│   │   │   └── health.py        # GET /api/v1/health
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── contracts.py
│   │   │   ├── clauses.py
│   │   │   └── tasks.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── llm.py               # LLM provider factory (Ollama/Groq/HF)
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── pdf_parser.py
│   │   │   └── docx_parser.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── clause_extractor.py
│   │   │   ├── risk_classifier.py
│   │   │   ├── precedent_retriever.py
│   │   │   ├── recommendation_generator.py
│   │   │   └── report_assembler.py
│   │   ├── orchestrator.py
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── clause_extraction.py
│   │       ├── risk_classification.py
│   │       └── recommendation.py
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── embeddings.py        # sentence-transformers (local)
│   │   ├── vector_store.py
│   │   ├── indexer.py
│   │   └── retriever.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analysis_service.py
│   │   ├── report_service.py
│   │   └── chat_service.py
│   └── tasks/
│       ├── __init__.py
│       └── analysis_tasks.py
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── analysis/[taskId]/page.tsx
│   ├── components/
│   │   ├── upload/
│   │   ├── analysis/
│   │   ├── chat/
│   │   └── ui/
│   └── lib/
│       ├── api.ts
│       └── types.ts
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── eval/
├── data/
│   ├── sample_contracts/
│   └── eval/
├── scripts/
│   ├── index_corpus.py
│   ├── run_eval.py
│   └── seed_data.py
└── docs/
    ├── architecture.md
    ├── api.md
    └── evaluation.md
```

## Conventions

### Python
- **Formatter**: black (line length 100)
- **Linter**: ruff (select = ["E", "F", "I", "N", "UP", "B", "SIM"])
- **Type checker**: mypy (--ignore-missing-imports)
- **Python version**: 3.11+ (use modern syntax: `X | None`, `list[str]`, match statements)
- **Imports**: isort-compatible via ruff, stdlib → third-party → local
- **Docstrings**: Google style on every public function and class
- **Type hints**: Required on every function signature

### API
- All routes return: `{ "status": str, "data": T | null, "errors": list[str] | null, "metadata": dict | null }`
- Pydantic v2 for all schemas
- Async everywhere in route handlers
- File uploads via `UploadFile` with validation (≤ 20MB, .pdf/.docx only)

### LLM Provider Abstraction (CRITICAL)
- **All LLM calls go through `backend/core/llm.py`** — never import provider-specific modules in agents
- `llm.py` exposes: `get_llm() -> BaseChatModel` and `get_embeddings() -> Embeddings`
- Provider selected via `LLM_PROVIDER` env var: "ollama" | "groq" | "huggingface"
- Agents receive an LLM instance, never construct one
- Use `PydanticOutputParser` + `OutputFixingParser` for structured output (works with all providers, unlike `with_structured_output` which is provider-specific)

### Agents
- Each agent: class with `async def run(self, input) -> output`
- All inputs/outputs are Pydantic models
- Prompts in `backend/core/prompts/` as constants
- PydanticOutputParser for structured output
- Retry on malformed output: max 2 retries with error feedback
- Log input/output at DEBUG, errors at ERROR

### Testing
- Unit tests mock all LLM calls — no real LLM calls in `make test`
- Eval tests call real LLMs — run via `make eval` only
- pytest fixtures for test data
- Target ≥80% coverage

### Git
- Commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `ci:` prefixes
- One logical change per commit

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
│  │  (chain-of-     │ │  Retriever  │  │
│  │   thought)      │ │  (hybrid    │  │
│  └───────┬────────┘ │   RAG)      │  │
│          │          └──────┬──────┘  │
│          ▼                 ▼         │
│  ┌───────────────────────────────┐   │
│  │  Recommendation Generator     │   │
│  └───────────────────────────────┘   │
└──────────────────┬───────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │ Report Assembler│
          └────────────────┘
                   │
                   ▼
            AnalysisResult
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | No | `ollama` | `ollama`, `groq`, or `huggingface` |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `llama3.1:8b` | Ollama model |
| `GROQ_API_KEY` | If groq | — | Groq free tier key |
| `GROQ_MODEL` | No | `llama-3.1-8b-instant` | Groq model |
| `HF_API_TOKEN` | If hf | — | HuggingFace token |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Local embedding model |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection |
| `CHROMA_HOST` | No | `localhost` | ChromaDB host |
| `CHROMA_PORT` | No | `8000` | ChromaDB port |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `MAX_FILE_SIZE_MB` | No | `20` | Max upload size |

## Key Design Decisions

1. **100% free**: Ollama (local) or Groq (free tier). Embeddings via sentence-transformers (local).
2. **Provider-agnostic**: `llm.py` abstracts everything. Switch provider = change one env var.
3. **PydanticOutputParser**: Works with any LLM. No provider-specific structured output.
4. **Async-first**: FastAPI + async agents + Celery.
5. **Fail gracefully**: One clause fails → rest continue. Errors collected.
6. **No data persistence**: Privacy by design.
7. **Evaluation as code**: Metrics computed by scripts, thresholds enforced.
