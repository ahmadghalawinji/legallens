.PHONY: install setup-ollama dev test lint format eval docker-build index

install:
	pip install -e ".[dev]"

setup-ollama:
	ollama pull llama3.1:8b
	ollama pull mistral:7b

dev:
	docker-compose up -d redis chromadb
	uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload

test:
	pytest tests/unit -v --cov=backend --cov-report=term-missing

lint:
	ruff check backend/ tests/
	mypy backend/ --ignore-missing-imports

format:
	black backend/ tests/
	ruff check --fix backend/ tests/

eval:
	pytest tests/eval -v

docker-build:
	docker-compose build

index:
	python scripts/index_corpus.py
