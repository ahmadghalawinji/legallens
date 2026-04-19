#!/usr/bin/env python3
"""CLI script to index the legal corpus into ChromaDB.

Usage:
    python scripts/index_corpus.py --source ledgar --limit 5000
"""
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Index legal corpus into ChromaDB")
    parser.add_argument("--source", default="ledgar", help="Corpus source (default: ledgar)")
    parser.add_argument("--limit", type=int, default=5000, help="Max provisions to index")
    args = parser.parse_args()

    from backend.knowledge.indexer import index_corpus

    total = index_corpus(source=args.source, limit=args.limit)
    print(f"Indexed {total} provisions from '{args.source}'.")


if __name__ == "__main__":
    main()
