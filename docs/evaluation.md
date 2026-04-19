# LegalLens — Evaluation

## Overview

The evaluation suite (`scripts/run_eval.py`) measures LLM quality against labeled samples. It calls real LLMs and is **not** part of the unit test suite (`make test`). Run it separately:

```bash
make eval
# or
python scripts/run_eval.py --limit 20
```

## Metrics

### Extraction F1

Measures how accurately the clause extractor identifies clause types present in a contract.

- **Precision**: fraction of predicted clause types that are correct
- **Recall**: fraction of expected clause types that were found
- **F1**: harmonic mean of precision and recall

**Threshold**: F1 ≥ 0.80

### Retrieval MRR@5

Measures retrieval quality for the RAG knowledge base.

- For each query, hybrid_search returns up to 5 results
- Reciprocal rank = 1/rank of the first relevant result (0 if none in top 5)
- MRR = mean reciprocal rank over all queries

**Threshold**: MRR@5 ≥ 0.65

## Eval Data Format

### Extraction samples — `data/eval/*.json`

```json
{
  "filename": "sample_nda.txt",
  "text": "... full contract text ...",
  "expected_clause_types": ["confidentiality", "termination", "governing_law"]
}
```

### Retrieval queries — `data/eval/retrieval_queries.json`

```json
[
  {
    "query": "unilateral termination without cause",
    "relevant_ids": ["doc_id_1", "doc_id_2"]
  }
]
```

Use `scripts/seed_data.py` to generate sample eval data.

## Results Table

The script prints a table and exits with code 0 (all pass) or 1 (any fail):

```
============================================================
Metric                              Score   Threshold   Pass?
------------------------------------------------------------
  Extraction F1                     0.847        0.80      ✅
  Retrieval Mrr                     0.712        0.65      ✅
============================================================
Overall: PASS
```

## Adding New Metrics

1. Add a `run_<metric>_eval(limit: int) -> float` async function in `scripts/run_eval.py`
2. Add the threshold to `THRESHOLDS`
3. Call it in `main()` and add the result to `results`
