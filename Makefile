.PHONY: help lint lint-backend lint-frontend typecheck format format-backend format-frontend dev prod build

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  lint              Lint + format-check both backend and frontend"
	@echo "  lint-backend      ruff check + black --check on backend/app/"
	@echo "  lint-frontend     tsc --noEmit + prettier --check on frontend/src/"
	@echo "  typecheck         Alias for lint"
	@echo "  format            Auto-format both backend (black) and frontend (prettier)"
	@echo "  format-backend    black on backend/app/"
	@echo "  format-frontend   prettier on frontend/src/"
	@echo "  dev               Start dev stack with hot-reload"
	@echo "  prod              Start production stack"
	@echo "  build             Build Docker images locally"

lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check app/ && black --check app/

lint-frontend:
	cd frontend && npm run typecheck && npm run format:check

typecheck: lint

format: format-backend format-frontend

format-backend:
	cd backend && black app/ && ruff check --fix app/

format-frontend:
	cd frontend && npm run format

dev:
	docker compose up

prod:
	docker compose -f docker-compose.prod.yml up -d

build:
	docker compose build
