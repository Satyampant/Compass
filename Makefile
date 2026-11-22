.PHONY: dev test lint

dev:
	uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .
