"""
Camada de Abstração LLM - Interface unificada para diferentes provedores de LLM
"""

import asyncio
import hashlib
import inspect
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime

import aiohttp
import ollama

logger = logging.getLogger("devs-ai")


class LLMProvider(ABC):
    """
    Interface abstrata para provedores de LLM
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop_sequences: list[str] = None,
    ) -> str:
        """
        Gera resposta para prompt

        Args:
            prompt: Texto do prompt
            temperature: Temperatura para sampling
            max_tokens: Número máximo de tokens na resposta
            stop_sequences: Sequências de parada

        Returns:
            Resposta gerada
        """
        pass

    @abstractmethod
    async def batch_generate(self, prompts: list[str], temperature: float = 0.7, max_tokens: int = 2048) -> list[str]:
        """
        Gera respostas para múltiplos prompts

        Args:
            prompts: Lista de prompts
            temperature: Temperatura para sampling
            max_tokens: Número máximo de tokens por resposta

        Returns:
            Lista de respostas
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, any]:
        """
        Retorna informações sobre o modelo

        Returns:
            Dicionário com informações do modelo
        """
        pass


class OllamaProvider(LLMProvider):
    """
    Provedor Ollama para modelos locais
    """

    def __init__(self, model_name: str, host: str = "localhost:11434", stream: bool = False):
        self.model_name = model_name
        self.host = host
        self.stream = stream
        self.client = ollama.AsyncClient(host=f"http://{host}")
        logger.info(f"OllamaProvider inicializado com modelo {model_name} em {host} (stream: {stream})")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop_sequences: list[str] = None,
    ) -> str:
        try:
            if self.stream:
                response_text = ""
                stream_response = self.client.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "stop": stop_sequences or [],
                        "top_p": 0.9,
                        "repeat_penalty": 1.1,
                    },
                    stream=True,
                )
                if inspect.iscoroutine(stream_response):
                    stream_response = await stream_response
                async for chunk in stream_response:
                    chunk_text = ""
                    if hasattr(chunk, "response"):
                        chunk_text = chunk.response or ""
                    elif isinstance(chunk, dict):
                        chunk_text = chunk.get("response", "")
                    else:
                        chunk_text = str(chunk) if chunk else ""
                    
                    if chunk_text:
                        response_text += chunk_text
                        logger.info(f"[OLLAMA STREAM] {chunk_text}")
                
                response_text = response_text.strip()
            else:
                response = await self.client.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "stop": stop_sequences or [],
                        "top_p": 0.9,
                        "repeat_penalty": 1.1,
                    },
                    stream=False,
                )

                if hasattr(response, "response"):
                    response_text = response.response.strip() if response.response else ""
                elif isinstance(response, dict):
                    response_text = response.get("response", "").strip() if response else ""
                else:
                    response_text = str(response).strip() if response else ""

            if not response_text:
                logger.warning(f"Ollama retornou resposta vazia (modelo: {self.model_name}, host: {self.host})")
            elif len(response_text) < 10:
                logger.warning(
                    f"Ollama retornou resposta muito curta ({len(response_text)} caracteres) "
                    f"(modelo: {self.model_name}, host: {self.host}). "
                    f"Primeiros caracteres: {response_text[:100]}"
                )

            return response_text
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com Ollama (modelo: {self.model_name}, host: {self.host}): {str(e)}")
            raise

    async def batch_generate(self, prompts: list[str], temperature: float = 0.7, max_tokens: int = 2048) -> list[str]:
        tasks = [self.generate(prompt, temperature, max_tokens) for prompt in prompts]
        return await asyncio.gather(*tasks)

    def get_model_info(self) -> dict[str, any]:
        try:
            info = ollama.show(self.model_name)
            if hasattr(info, "size"):
                size = info.size
                details = info.details if hasattr(info, "details") else {}
            elif isinstance(info, dict):
                size = info.get("size", 0)
                details = info.get("details", {})
            else:
                size = 0
                details = {}

            return {
                "name": self.model_name,
                "size": size,
                "parameters": details.get("parameter_size", "unknown") if isinstance(details, dict) else "unknown",
                "family": details.get("family", "unknown") if isinstance(details, dict) else "unknown",
            }
        except Exception as e:
            logger.error(f"Erro ao obter informações do modelo: {str(e)}")
            return {
                "name": self.model_name,
                "size": 0,
                "parameters": "unknown",
                "family": "unknown",
            }

    async def stop_model(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                base_url = f"http://{self.host}"
                async with session.get(f"{base_url}/api/ps", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        processes = data.get("processes", [])
                        for process in processes:
                            if process.get("model") == self.model_name:
                                try:
                                    async with session.delete(
                                        f"{base_url}/api/generate",
                                        json={"model": self.model_name},
                                        timeout=2,
                                    ) as resp:
                                        await resp.read()
                                    logger.info(f"Modelo Ollama {self.model_name} parado com sucesso")
                                    return True
                                except Exception as e:
                                    logger.warning(f"Erro ao parar modelo {self.model_name}: {str(e)}")
            return False
        except Exception as e:
            logger.warning(f"Erro ao parar modelo Ollama {self.model_name}: {str(e)}")
            return False


class OpenAIProvider(LLMProvider):
    """
    Provedor OpenAI para modelos GPT
    """

    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://api.openai.com/v1"
        logger.info(f"OpenAIProvider inicializado com modelo {model_name}")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop_sequences: list[str] = None,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop": stop_sequences,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/chat/completions", headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Erro OpenAI {response.status}: {error_text}")

                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com OpenAI: {str(e)}")
            raise

    async def batch_generate(self, prompts: list[str], temperature: float = 0.7, max_tokens: int = 2048) -> list[str]:
        return await asyncio.gather(*[self.generate(prompt, temperature, max_tokens) for prompt in prompts])

    def get_model_info(self) -> dict[str, any]:
        return {
            "name": self.model_name,
            "provider": "openai",
            "max_context": 128000 if "gpt-4" in self.model_name else 32000,
        }


class ResponseCache:
    """
    Cache de respostas LLM com TTL e versionamento
    """

    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 1000):
        self.cache = {}
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self.hits = 0
        self.misses = 0
        self.last_cleanup = time.time()

    def _get_cache_key(self, prompt: str, temperature: float, max_tokens: int, model_name: str) -> str:
        """Gera chave de cache única"""
        key_data = f"{prompt}|{temperature}|{max_tokens}|{model_name}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, prompt: str, temperature: float, max_tokens: int, model_name: str) -> str | None:
        """Obtém resposta do cache"""
        key = self._get_cache_key(prompt, temperature, max_tokens, model_name)

        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry["expires_at"]:
                self.hits += 1
                return entry["response"]
            else:
                del self.cache[key]

        self.misses += 1
        return None

    def set(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        model_name: str,
        response: str,
    ):
        """Armazena resposta no cache"""
        # Limpa cache expirado periodicamente (a cada 5 minutos)
        current_time = time.time()
        if current_time - self.last_cleanup > 300:  # 5 minutos
            self._cleanup_expired()
            self.last_cleanup = current_time

        # Limita tamanho do cache
        if len(self.cache) >= self.max_entries:
            self._evict_oldest()

        key = self._get_cache_key(prompt, temperature, max_tokens, model_name)
        self.cache[key] = {
            "response": response,
            "expires_at": time.time() + self.ttl,
            "cached_at": datetime.utcnow().isoformat(),
        }

    def _cleanup_expired(self):
        """Remove entradas expiradas do cache"""
        current_time = time.time()
        expired_keys = [key for key, value in self.cache.items() if current_time >= value["expires_at"]]
        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.info(f"Cache cleanup: removidas {len(expired_keys)} entradas expiradas")

    def _evict_oldest(self):
        """Remove as 10% entradas mais antigas quando o cache está cheio"""
        if not self.cache:
            return

        # Ordena por tempo de criação
        sorted_items = sorted(self.cache.items(), key=lambda x: x[1]["cached_at"])

        # Remove os 10% mais antigos
        num_to_remove = max(1, len(sorted_items) // 10)
        for key, _ in sorted_items[:num_to_remove]:
            del self.cache[key]

        logger.info(f"Cache eviction: removidas {num_to_remove} entradas antigas")

    def get_stats(self) -> dict[str, any]:
        """Retorna estatísticas do cache"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache),
        }


class LLMAbstractLayer:
    """
    Camada de abstração unificada para LLM com fallback e cache
    """

    def __init__(self, config: dict[str, any]):
        self.config = config
        self.providers = []
        cache_ttl = config.get("performance", {}).get("cache_ttl", 3600)
        single_agent_mode = config.get("orchestrator", {}).get("single_agent_mode", True)

        if single_agent_mode:
            max_entries = 100
        else:
            max_entries = 1000

        self.cache = ResponseCache(ttl_seconds=cache_ttl, max_entries=max_entries)
        self.current_provider_idx = 0
        self.agent_providers = {}
        self.single_agent_mode = single_agent_mode
        self._providers_initialized = False

        self.capability_tokens = config.get("capability_tokens", {})

        logger.info(f"LLMAbstractLayer inicializado (single_agent_mode: {single_agent_mode})")

    def _get_ollama_config(self) -> dict:
        """Obtém configuração do Ollama com suporte a formatos antigo e novo"""
        ollama_config = self.config.get("ollama", {})
        if isinstance(ollama_config, dict) and ollama_config:
            return ollama_config
        ollama_host = self.config.get("ollama_host", "localhost:11434")
        return {"host": ollama_host, "enabled": True, "stream": False}

    def _initialize_providers(self) -> list[LLMProvider]:
        """Inicializa provedores de LLM baseado na configuração"""
        providers = []

        # Provedor Ollama (padrão)
        ollama_config = self._get_ollama_config()
        if ollama_config.get("enabled", True):
            primary_model = self.config.get("primary_model", "llama3:8b-instruct-q4_0")
            stream_enabled = ollama_config.get("stream", False)
            providers.append(
                OllamaProvider(
                    model_name=primary_model,
                    host=ollama_config.get("host", "localhost:11434"),
                    stream=stream_enabled,
                )
            )

        # Provedores fallback
        fallback_models = self.config.get("fallback_models", [])
        stream_enabled = ollama_config.get("stream", False)
        for model in fallback_models:
            providers.append(OllamaProvider(model_name=model, host=ollama_config.get("host", "localhost:11434"), stream=stream_enabled))

        # Provedor OpenAI (se configurado)
        openai_config = self.config.get("openai", {})
        if openai_config.get("enabled", False) and openai_config.get("api_key"):
            providers.append(
                OpenAIProvider(
                    api_key=openai_config["api_key"],
                    model_name=openai_config.get("model", "gpt-4"),
                )
            )

        return providers

    def _get_providers_for_agent(self, agent_id: str = None) -> list[LLMProvider]:
        """Retorna providers específicos para um agente ou providers padrão"""
        if not agent_id:
            if not self._providers_initialized:
                self.providers = self._initialize_providers()
                self._providers_initialized = True
            return self.providers

        if agent_id in self.agent_providers:
            return self.agent_providers[agent_id]

        agent_models = self.config.get("agent_models", {})
        if agent_id in agent_models:
            model_name = agent_models[agent_id]
            ollama_config = self._get_ollama_config()
            host = ollama_config.get("host", "localhost:11434")
            stream_enabled = ollama_config.get("stream", False)

            providers = [OllamaProvider(model_name=model_name, host=host, stream=stream_enabled)]

            fallback_models = self.config.get("fallback_models", [])
            for fallback_model in fallback_models:
                if fallback_model != model_name:
                    providers.append(OllamaProvider(model_name=fallback_model, host=host, stream=stream_enabled))

            self.agent_providers[agent_id] = providers
            logger.info(f"Providers específicos criados para {agent_id}: {model_name}")
            return providers

        if not self._providers_initialized:
            self.providers = self._initialize_providers()
            self._providers_initialized = True
        return self.providers

    def _is_valid_response(self, response: str) -> bool:
        """
        Valida se a resposta é válida antes de armazenar no cache.
        Não cacheia respostas vazias ou muito curtas.
        """
        if not response or not response.strip():
            return False

        response_stripped = response.strip()

        if len(response_stripped) < 3:
            return False

        return True

    async def generate_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop_sequences: list[str] = None,
        context: dict[str, any] = None,
        agent_id: str = None,
    ) -> str:
        """
        Gera resposta usando o provedor atual com fallback automático

        Args:
            prompt: Texto do prompt
            temperature: Temperatura para sampling
            max_tokens: Número máximo de tokens na resposta
            stop_sequences: Sequências de parada
            context: Contexto adicional para cache e logging
            agent_id: ID do agente para usar modelo específico

        Returns:
            Resposta gerada
        """
        providers = self._get_providers_for_agent(agent_id)

        if agent_id and agent_id in self.config.get("performance", {}).get("max_tokens", {}):
            max_tokens = self.config["performance"]["max_tokens"][agent_id]

        # Verifica cache primeiro
        model_name = providers[0].get_model_info()["name"]
        cached_response = self.cache.get(prompt, temperature, max_tokens, model_name)
        if cached_response:
            logger.info("Cache hit para resposta LLM")
            return cached_response

        # Tenta com provedores em ordem
        last_error = None
        for i in range(len(providers)):
            provider = providers[i]

            try:
                start_time = time.time()
                response = await provider.generate(
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop_sequences=stop_sequences,
                )
                generation_time = time.time() - start_time

                # Valida resposta antes de armazenar no cache
                model_info = provider.get_model_info()
                if self._is_valid_response(response):
                    self.cache.set(prompt, temperature, max_tokens, model_info["name"], response)
                else:
                    logger.warning(
                        f"Resposta inválida não será armazenada no cache: {response[:100] if response else 'vazia'}"
                    )

                agent_name = agent_id or "default"
                logger.info(f"Resposta gerada com {model_info['name']} (agent: {agent_name}) em {generation_time:.2f}s")

                if self.single_agent_mode:
                    import gc

                    gc.collect()

                return response

            except Exception as e:
                last_error = e
                logger.warning(f"Falha com provedor {provider.get_model_info()['name']}: {str(e)}")
                continue

        # Se todos os provedores falharem
        logger.error(f"Todos os provedores de LLM falharam. Último erro: {str(last_error)}")
        raise Exception(f"Falha crítica nos provedores de LLM: {str(last_error)}")

    async def batch_generate_responses(
        self, prompts: list[str], temperature: float = 0.7, max_tokens: int = 2048, agent_id: str = None
    ) -> list[str]:
        """
        Gera respostas para múltiplos prompts em paralelo

        Args:
            prompts: Lista de prompts
            temperature: Temperatura para sampling
            max_tokens: Número máximo de tokens por resposta
            agent_id: ID do agente para usar modelo específico

        Returns:
            Lista de respostas
        """
        tasks = [self.generate_response(prompt, temperature, max_tokens, agent_id=agent_id) for prompt in prompts]
        return await asyncio.gather(*tasks)

    async def stop_agent_providers(self, agent_id: str = None):
        """Para os providers Ollama de um agente específico"""
        providers = []

        if agent_id and agent_id in self.agent_providers:
            providers = self.agent_providers[agent_id]
        elif not agent_id and self._providers_initialized:
            providers = self.providers

        for provider in providers:
            if isinstance(provider, OllamaProvider):
                await provider.stop_model()

        if agent_id and agent_id in self.agent_providers:
            del self.agent_providers[agent_id]
            logger.info(f"Providers do agente {agent_id} removidos após parada")

    def get_system_status(self) -> dict[str, any]:
        """
        Retorna status do sistema LLM
        """
        if not self._providers_initialized:
            self.providers = self._initialize_providers()
            self._providers_initialized = True

        provider_statuses = []
        for provider in self.providers:
            try:
                info = provider.get_model_info()
                provider_statuses.append(
                    {
                        "name": info["name"],
                        "status": "online",
                        "type": type(provider).__name__,
                    }
                )
            except Exception as e:
                provider_statuses.append(
                    {
                        "name": getattr(provider, "model_name", "unknown"),
                        "status": "offline",
                        "error": str(e),
                    }
                )

        current_provider_name = "unknown"
        if self.providers and self.current_provider_idx < len(self.providers):
            try:
                current_provider_name = self.providers[self.current_provider_idx].get_model_info()["name"]
            except Exception:
                pass

        return {
            "current_provider": current_provider_name,
            "providers": provider_statuses,
            "cache_stats": self.cache.get_stats(),
            "capability_tokens": len(self.capability_tokens),
            "timestamp": datetime.utcnow().isoformat(),
        }
