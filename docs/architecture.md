# LegalLens — Architecture

## Overview

LegalLens is an async, multi-agent pipeline that analyzes legal contracts for risk. A document is parsed, clauses are extracted by an LLM, each clause is classified for risk (in parallel), legal precedents are retrieved via hybrid RAG, recommendations are generated, and an HTML/PDF report is assembled.

## Component Diagram

```
User (Browser)
      │  POST /api/v1/contracts/analyze
      ▼
┌─────────────────────────────────────────────────────────┐
│                      FastAPI (main.py)                  │
│   /health   /contracts/analyze   /tasks/{id}[/report]   │
└──────────────────────┬──────────────────────────────────┘
                       │ Celery task (Redis broker)
                       ▼
┌─────────────────────────────────────────────────────────┐
│               LangGraph Orchestrator                    │
│                                                         │
│  parse_document → extract_clauses                       │
│       → classify_and_retrieve (asyncio.gather)          │
│       → generate_summary → compute_score                │
└──────────────────────┬──────────────────────────────────┘
                       │ AnalysisResult
                       ▼
              Redis (task state store)
```

## Agent Pipeline

### 1. Document Parser (`backend/core/parsers/`)

- `pdf_parser.py` — PyMuPDF; detects headers/footers, splits into sections by blank lines + heading patterns
- `docx_parser.py` — python-docx; uses Heading styles as section boundaries, extracts metadata
- Output: `ParsedDocument` with `full_text` and a list of `DocumentSection`

### 2. Clause Extractor (`backend/core/agents/clause_extractor.py`)

- Chunked input (≤ 3000 chars, 200-char overlap)
- 3-shot prompt → LLM → `PydanticOutputParser[ExtractionResult]`
- Manual retry (up to 2) with error feedback on malformed JSON
- Deduplicates by (type, text prefix)
- Output: `list[ExtractedClause]`

### 3. Risk Classifier (`backend/core/agents/risk_classifier.py`)

- Chain-of-thought prompt with HIGH/MEDIUM/LOW rubric
- All clauses classified in parallel via `asyncio.gather`
- Risk score clamped to [0, 1]; MEDIUM fallback on failure
- Output: `list[ClassifiedClause]`

### 4. Precedent Retriever (`backend/core/agents/precedent_retriever.py`)

- Skips LOW-risk clauses
- Calls `hybrid_search(clause.text, top_k=3)` from `backend/knowledge/retriever.py`
- Returns top-3 relevant legal precedent snippets

### 5. Recommendation Generator (`backend/core/agents/recommendation_generator.py`)

- Receives clause + risk classification + precedents
- Generates: `summary`, `issues`, `alternative_language`
- Graceful fallback on LLM failure

### 6. Report Assembler / Report Service

- `report_assembler.py` — combines classified clauses + recommendations into `AnalysisResult`
- `report_service.py` — renders HTML string template; optional PDF via WeasyPrint

## Knowledge Base (RAG)

```
Legal corpus (LEDGAR / plain text)
          │
          ▼
  sentence-transformers (all-MiniLM-L6-v2) — local, no API
          │
     dense vectors
          ▼
       ChromaDB                BM25 (rank-bm25, in-memory)
          │                          │
          └──────────┬───────────────┘
                     ▼
        Reciprocal Rank Fusion (k=60)
                     │
              top-K provisions
```

- `embeddings.py` — lazy singleton, embed_text / embed_batch
- `vector_store.py` — ChromaDB HttpClient wrapper, cosine similarity
- `retriever.py` — hybrid_search() merges dense + sparse results

## LLM Provider Abstraction

All agents receive a `BaseChatModel` from `backend/core/llm.py`. Switch provider with `LLM_PROVIDER` env var:

| Provider | Variable | Notes |
|----------|----------|-------|
| `ollama` | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Fully local |
| `groq` | `GROQ_API_KEY`, `GROQ_MODEL` | Free tier, fast |
| `huggingface` | `HF_API_TOKEN` | Free inference API |

Embeddings always use sentence-transformers locally.

## Async / Concurrency Model

- FastAPI routes are `async`
- Clause extraction + classification are `async`
- Per-clause classify + retrieve run with `asyncio.gather` for parallelism
- Heavy pipeline dispatched to Celery worker (separate process) to avoid blocking the API
- Task state (progress, result, error) serialized as JSON in Redis

## Data Flow Types

```
UploadFile
  → ParsedDocument
    → list[ExtractedClause]
      → list[ClassifiedClause]  (+ precedents + recommendations)
        → AnalysisResult
          → TaskResponse (API)  /  HTML or PDF (report)
```
