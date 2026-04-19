#!/usr/bin/env python3
"""Run the full LegalLens evaluation suite and print a results table.

Usage:
    python scripts/run_eval.py

Requires a running LLM provider (Ollama or Groq key set via env).
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Thresholds from the implementation plan
THRESHOLDS = {
    "extraction_f1": 0.80,
    "classification_accuracy": 0.75,
    "retrieval_mrr": 0.65,
}


def _print_table(results: dict[str, float]) -> None:
    print("\n" + "=" * 60)
    print(f"{'Metric':<35} {'Score':>8}  {'Threshold':>10}  {'Pass?':>6}")
    print("-" * 60)
    all_pass = True
    for key, score in results.items():
        threshold = THRESHOLDS.get(key, 0.0)
        passed = score >= threshold
        if not passed:
            all_pass = False
        status = "✅" if passed else "❌"
        label = key.replace("_", " ").title()
        print(f"  {label:<33} {score:>8.3f}  {threshold:>10.2f}  {status:>6}")
    print("=" * 60)
    print(f"Overall: {'PASS' if all_pass else 'FAIL'}")
    print()
    return all_pass


async def run_extraction_eval(limit: int) -> float:
    """Run extraction F1 evaluation on sample contracts."""
    from backend.core.agents.clause_extractor import ClauseExtractor
    from backend.core.llm import get_llm
    from backend.core.parsers.base import ParsedDocument

    eval_dir = Path("data/eval")
    samples = list(eval_dir.glob("*.json")) if eval_dir.exists() else []

    if not samples:
        logger.warning("No eval samples found in data/eval/ — skipping extraction eval")
        return 0.0

    llm = get_llm(temperature=0.0)
    extractor = ClauseExtractor(llm)

    tp = fp = fn = 0
    import json

    for sample_path in samples[:limit]:
        sample = json.loads(sample_path.read_text())
        doc = ParsedDocument(
            filename=sample["filename"],
            file_type="txt",
            full_text=sample["text"],
            sections=[],
            page_count=1,
        )
        predicted = await extractor.run(doc)
        expected_types = set(sample.get("expected_clause_types", []))
        predicted_types = {c.clause_type.value for c in predicted}

        tp += len(expected_types & predicted_types)
        fp += len(predicted_types - expected_types)
        fn += len(expected_types - predicted_types)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    logger.info("Extraction: P=%.3f R=%.3f F1=%.3f", precision, recall, f1)
    return f1


async def run_retrieval_eval(limit: int) -> float:
    """Compute MRR@5 over retrieval queries."""
    from backend.knowledge.retriever import hybrid_search

    eval_dir = Path("data/eval")
    queries_path = eval_dir / "retrieval_queries.json"

    if not queries_path.exists():
        logger.warning("No retrieval eval file found — skipping retrieval eval")
        return 0.0

    import json

    queries = json.loads(queries_path.read_text())[:limit]
    reciprocal_ranks = []

    for q in queries:
        hits = hybrid_search(q["query"], top_k=5)
        hit_ids = [h["id"] for h in hits]
        relevant = set(q.get("relevant_ids", []))
        rr = 0.0
        for rank, doc_id in enumerate(hit_ids, 1):
            if doc_id in relevant:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    logger.info("Retrieval MRR@5=%.3f over %d queries", mrr, len(reciprocal_ranks))
    return mrr


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LegalLens evaluation suite")
    parser.add_argument("--limit", type=int, default=10, help="Max samples per eval")
    args = parser.parse_args()

    results = {}
    loop = asyncio.get_event_loop()

    logger.info("Running extraction eval…")
    results["extraction_f1"] = loop.run_until_complete(
        run_extraction_eval(args.limit)
    )

    logger.info("Running retrieval eval…")
    results["retrieval_mrr"] = loop.run_until_complete(
        run_retrieval_eval(args.limit)
    )

    passed = _print_table(results)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
