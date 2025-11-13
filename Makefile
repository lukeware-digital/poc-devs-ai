.PHONY: format lint up-redis up-chroma pull-ollama

format:
	@ruff format .

lint:
	@ruff check . --fix

pull-ollama:
	@docker exec -it ollama ollama pull llama3:8b-instruct-q4_0
	@docker exec -it ollama ollama pull mistral:7b-instruct-v0.2-q4_0
	@docker exec -it ollama ollama pull phi3:medium-4k-instruct-q4_0
	@docker exec -it ollama ollama pull codegemma:7b-instruct-q4_0
