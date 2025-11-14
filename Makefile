.PHONY: format lint build-local run

format:
	@ruff format .

lint:
	@ruff check . --fix

build-local:
	@docker compose build --no-cache app && docker compose up -d app

run:
	python main.py