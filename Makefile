up-redis:
	@docker run -d --name redis -p 6379:6379 redis

up-chroma:
	@docker run -d --name chromadb -p 8000:8000 chromadb/chroma

pull-ollama:
	@ollama pull llama3:8b-instruct-q4_0
	@ollama pull mistral:7b-instruct-v0.2-q4_0
	@ollama pull phi3:medium-4k-instruct-q4_0
	@ollama pull codegemma:7b-instruct-q4_0