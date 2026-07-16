.PHONY: install run test lint format compose-up compose-down migrate shell help

PYTHON_RUN := poetry run

help:
	@echo "AI SRE Makefile Commands:"
	@echo "  install        Install dependencies"
	@echo "  run            Run the FastAPI dev server"
	@echo "  test           Run pytest suite"
	@echo "  lint           Run code linter checks"
	@echo "  format         Auto-format code with black & isort"
	@echo "  compose-up     Start development docker containers"
	@echo "  compose-down   Stop development docker containers"
	@echo "  migrate        Run database migrations"

install:
	poetry install

run:
	$(PYTHON_RUN) uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON_RUN) pytest

lint:
	$(PYTHON_RUN) black --check src tests
	$(PYTHON_RUN) isort --check-only src tests
	$(PYTHON_RUN) flake8 src tests
	$(PYTHON_RUN) mypy src

format:
	$(PYTHON_RUN) black src tests
	$(PYTHON_RUN) isort src tests

compose-up:
	docker compose up -d

compose-down:
	docker compose down

migrate:
	$(PYTHON_RUN) alembic upgrade head
