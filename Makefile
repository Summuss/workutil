.PHONY: install dev-backend dev-frontend build run test check

## First-time setup
install:
	cd backend && uv sync
	cd frontend && pnpm install

## Development: run both, then reach :5173 over an SSH tunnel (docs/design.md §7)
dev-backend:
	cd backend && uv run uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8765

dev-frontend:
	cd frontend && pnpm dev

## Production: build the UI, then serve everything from Python alone
build:
	cd frontend && pnpm build

run:
	cd backend && uv run workutil

test:
	cd backend && uv run pytest

check:
	cd backend && uv run ruff check .
	cd backend && uv run mypy app tests
	cd frontend && pnpm typecheck
