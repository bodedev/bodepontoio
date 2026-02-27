.DEFAULT_GOAL := help
SETTINGS := tests.test_settings
MANAGE    := uv run django-admin

.PHONY: help install test test-v lint migrate makemigrations shell runserver build clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install package and dev dependencies
	uv pip install -e ".[dev]"

test: ## Run test suite
	uv run python -m pytest

test-v: ## Run test suite with verbose output
	uv run python -m pytest -v

test-x: ## Run tests, stop on first failure
	uv run python -m pytest -x

makemigrations: ## Generate migrations for bodepontoio
	$(MANAGE) makemigrations bodepontoio --settings=$(SETTINGS)

migrate: ## Apply migrations (test DB)
	$(MANAGE) migrate --settings=$(SETTINGS)

shell: ## Open Django shell (test settings)
	$(MANAGE) shell --settings=$(SETTINGS)

runserver: ## Start dev server on localhost:8000 (test settings)
	$(MANAGE) runserver --settings=$(SETTINGS)

build: ## Build the distribution packages
	uv build

clean: ## Remove build artefacts and caches
	rm -rf dist/ build/ *.egg-info .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
