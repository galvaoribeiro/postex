.PHONY: up down build logs migrate seed test-backend lint-frontend build-frontend

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f api worker

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m scripts.seed

test-backend:
	cd backend && pytest -q

lint-frontend:
	cd frontend && npm run lint && npx tsc --noEmit

build-frontend:
	cd frontend && npm run build
