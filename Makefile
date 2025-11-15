.PHONY: format lint build-local run

format:
	@ruff format .

lint:
	@ruff check . --fix