.PHONY: help build up down logs shell migrate makemigrations test lint

help:
	@echo "make build  — build docker images"
	@echo "make up     — start with docker-compose"
	@echo "make down   — stop"
	@echo "make shell  — open a shell in the web container"
	@echo "make migrate"

build:
	docker-compose build

up:
	docker-compose up -d --build

down:
	docker-compose down

logs:
	docker-compose logs -f

shell:
	docker-compose exec web bash

migrate:
	docker-compose exec web python manage.py migrate

makemigrations:
	docker-compose exec web python manage.py makemigrations

collectstatic:
	docker-compose exec web python manage.py collectstatic --noinput

test:
	pytest

lint:
	black --check .
	isort --check-only .
	flake8
