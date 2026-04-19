# LegalLens — API Reference

Base URL: `http://localhost:8080`

All JSON responses follow the envelope:

```json
{
  "status": "ok" | "error",
  "data": <payload> | null,
  "errors": ["..."] | null,
  "metadata": {} | null
}
```

Interactive docs available at `http://localhost:8080/docs` (Swagger UI).

---

## GET /api/v1/health

Health check. Verifies Redis and ChromaDB connectivity.

**Response 200**
```json
{
  "status": "ok",
  "data": {
    "redis": "ok",
    "chromadb": "ok",
    "version": "0.1.0"
  },
  "errors": null,
  "metadata": null
}
```

---

## POST /api/v1/contracts/analyze

Upload a contract file for analysis. Returns a task ID for polling.

**Request** — `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | yes | PDF or DOCX, max 20 MB |

**Response 202**
```json
{
  "status": "ok",
  "data": {
    "task_id": "abc123",
    "status": "pending",
    "message": "Analysis started."
  },
  "errors": null,
  "metadata": null
}
```

**Errors**

| Code | Reason |
|------|--------|
| 400 | Unsupported file type (only .pdf / .docx) |
| 413 | File exceeds MAX_FILE_SIZE_MB (default 20 MB) |
| 422 | Missing file field |

---

## GET /api/v1/tasks/{task_id}

Poll analysis status and retrieve results when complete.

**Path params**

| Param | Description |
|-------|-------------|
| `task_id` | ID returned by POST /contracts/analyze |

**Response 200 — pending / in_progress**
```json
{
  "status": "ok",
  "data": {
    "task_id": "abc123",
    "status": "in_progress",
    "progress": 45,
    "result": null,
    "error": null
  },
  "errors": null,
  "metadata": null
}
```

**Response 200 — success**
```json
{
  "status": "ok",
  "data": {
    "task_id": "abc123",
    "status": "success",
    "progress": 100,
    "result": {
      "task_id": "abc123",
      "filename": "contract.pdf",
      "status": "success",
      "clauses": [
        {
          "clause_type": "termination",
          "text": "Either party may terminate...",
          "risk_level": "high",
          "risk_score": 0.82,
          "risk_explanation": "Unilateral termination with no notice period.",
          "reasoning": "...",
          "recommendations": {
            "summary": "Add minimum notice period.",
            "issues": ["No notice period specified"],
            "alternative_language": "Either party may terminate with 30 days written notice..."
          },
          "precedents": ["..."]
        }
      ],
      "overall_risk_score": 0.61,
      "high_risk_count": 3,
      "medium_risk_count": 2,
      "low_risk_count": 1,
      "processing_time_seconds": 12.4,
      "errors": []
    },
    "error": null
  },
  "errors": null,
  "metadata": null
}
```

**Errors**

| Code | Reason |
|------|--------|
| 404 | Task not found |

---

## GET /api/v1/tasks/{task_id}/report

Download the analysis as an HTML report.

**Response 200** — `text/html`

Full HTML document rendered with risk-colored clauses, executive summary stats, and legal disclaimer.

**Errors**

| Code | Reason |
|------|--------|
| 404 | Task not found |
| 409 | Analysis not yet complete |

---

## GET /api/v1/tasks/{task_id}/report.pdf

Download the analysis as a PDF report (requires WeasyPrint).

**Response 200** — `application/pdf`

`Content-Disposition: attachment; filename="legallens_{task_id}.pdf"`

**Errors**

| Code | Reason |
|------|--------|
| 404 | Task not found |
| 409 | Analysis not yet complete |
| 500 | WeasyPrint not installed |

---

## Clause Types

| Value | Description |
|-------|-------------|
| `termination` | Termination conditions |
| `liability` | Liability and indemnification |
| `intellectual_property` | IP ownership / licensing |
| `payment` | Payment terms |
| `confidentiality` | NDA / confidentiality obligations |
| `dispute_resolution` | Dispute resolution / arbitration |
| `force_majeure` | Force majeure events |
| `non_compete` | Non-compete restrictions |
| `warranty` | Warranties and representations |
| `governing_law` | Governing law / jurisdiction |
| `other` | Miscellaneous |

## Risk Levels

| Value | Meaning |
|-------|---------|
| `high` | Significant legal risk; review with attorney |
| `medium` | Moderate concern; consider negotiating |
| `low` | Standard clause; low risk |
