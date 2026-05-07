.PHONY: setup setup-backend setup-frontend lint lint-backend lint-frontend test test-backend test-frontend dev migrate openapi worker

# ──────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────
setup: setup-backend setup-frontend

setup-backend:
	cd apps/backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"

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
	cd apps/frontend && npm test 2>/dev/null || true

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

# ──────────────────────────────────────────────
# Temporal worker
# ──────────────────────────────────────────────
worker:
	cd apps/worker && python -m worker

# ──────────────────────────────────────────────
# OpenAPI → Frontend types
# ──────────────────────────────────────────────
openapi:
	cd apps/backend && .venv/bin/python -c "from app.main import app; import json; print(json.dumps(app.openapi()))" > ../frontend/lib/openapi.json
