.PHONY: up down logs migrate superuser test test-frontend lint format shell

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec backend python manage.py migrate

superuser:
	docker compose exec backend python manage.py createsuperuser

test:
	docker compose exec backend pytest

test-frontend:
	docker compose exec frontend npm test

lint:
	docker compose exec backend sh -c "ruff check . && ruff format --check ."
	docker compose exec frontend sh -c "npm run lint && npm run format:check"

format:
	docker compose exec backend sh -c "ruff check --fix . && ruff format ."

shell:
	docker compose exec backend python manage.py shell
