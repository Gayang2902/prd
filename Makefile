.PHONY: setup setup-backend setup-frontend setup-schemas lint lint-backend lint-frontend test test-backend test-frontend build build-frontend dev migrate seed openapi worker

# ──────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────
setup: setup-schemas setup-backend setup-frontend

setup-schemas:
	cd packages/shared-schemas && pip install -e .

setup-backend:
	cd apps/backend && pip install -e ".[dev]"

setup-frontend:
	cd apps/frontend && npm install

# ──────────────────────────────────────────────
# Lint
# ──────────────────────────────────────────────
lint: lint-backend lint-frontend

lint-backend:
	cd apps/backend && .venv/bin/black --check . && .venv/bin/ruff check . && .venv/bin/mypy app

lint-frontend:
	cd apps/frontend && npm run lint && npm run typecheck && npm run format

# ──────────────────────────────────────────────
# Test
# ──────────────────────────────────────────────
test: test-backend test-frontend

test-backend:
	cd apps/backend && .venv/bin/pytest --cov=app --cov-report=term-missing

test-frontend:
	cd apps/frontend && npm test

# ──────────────────────────────────────────────
# Build
# ──────────────────────────────────────────────
build: build-frontend

build-frontend:
	cd apps/frontend && npx next build

# ──────────────────────────────────────────────
# Dev
# ──────────────────────────────────────────────
dev:
	docker compose up -d

# ──────────────────────────────────────────────
# DB
# ──────────────────────────────────────────────
migrate:
	cd apps/backend && .venv/bin/alembic upgrade head

seed:
	cd apps/backend && python scripts/seed.py

# ──────────────────────────────────────────────
# Temporal worker
# ──────────────────────────────────────────────
worker:
	cd apps && python -m worker

# ──────────────────────────────────────────────
# OpenAPI → Frontend types
# ──────────────────────────────────────────────
openapi:
	cd apps/backend && .venv/bin/python -c "from app.main import app; import json; print(json.dumps(app.openapi()))" > ../frontend/lib/openapi.json
