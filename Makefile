.PHONY: up down logs migrate superuser test lint format shell

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

lint:
	docker compose exec backend sh -c "ruff check . && ruff format --check ."

format:
	docker compose exec backend sh -c "ruff check --fix . && ruff format ."

shell:
	docker compose exec backend python manage.py shell
