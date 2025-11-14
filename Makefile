.PHONY: format lint up-redis up-chroma pull-ollama

format:
	@ruff format .

lint:
	@ruff check . --fix

pull-ollama:
	@echo "Baixando modelos otimizados para consumo mínimo de hardware..."
	@docker exec -it ollama ollama pull phi3:mini
	@docker exec -it ollama ollama pull tinyllama
	@docker exec -it ollama ollama pull qwen2:1.5b-instruct-q4_K_M
	@docker exec -it ollama ollama pull llama3.2:3b
	@docker exec -it ollama ollama pull gemma:2b
	@echo "Modelos otimizados baixados com sucesso!"
