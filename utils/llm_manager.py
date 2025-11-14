import asyncio
import logging

import aiohttp
import ollama

logger = logging.getLogger("DEVs_AI")


class LLMManager:
    def __init__(self, config: dict):
        self.config = config
        ollama_config = config.get("ollama", {})
        self.ollama_host = ollama_config.get("host", "localhost:11434")
        self.ollama_base_url = f"http://{self.ollama_host}"
        self.client = ollama.AsyncClient(host=self.ollama_base_url)
        self._lock = asyncio.Lock()
        self._current_agent: str | None = None

    async def check_running_models(self) -> list[dict]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_base_url}/api/ps", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("processes", [])
                    return []
        except Exception as e:
            logger.warning(f"Erro ao verificar modelos em execução: {str(e)}")
            return []

    async def stop_all_models(self) -> bool:
        try:
            running_models = await self.check_running_models()
            if not running_models:
                return True

            async with aiohttp.ClientSession() as session:
                for process in running_models:
                    model = process.get("model", "")
                    if model:
                        try:
                            async with session.post(
                                f"{self.ollama_base_url}/api/generate",
                                json={"model": model, "prompt": "", "stream": False},
                                timeout=2,
                            ) as resp:
                                await resp.read()
                        except Exception:
                            pass

                        try:
                            async with session.delete(
                                f"{self.ollama_base_url}/api/generate",
                                json={"model": model},
                                timeout=2,
                            ) as resp:
                                await resp.read()
                        except Exception:
                            pass

            await asyncio.sleep(1)

            remaining = await self.check_running_models()
            if remaining:
                logger.warning(f"Ainda há {len(remaining)} modelos em execução após tentativa de parada")
                return False

            logger.info("Todos os modelos Ollama foram parados")
            return True
        except Exception as e:
            logger.error(f"Erro ao parar modelos: {str(e)}")
            return False

    async def acquire_lock(self, agent_id: str) -> bool:
        async with self._lock:
            if self._current_agent is not None and self._current_agent != agent_id:
                logger.warning(f"Agente {agent_id} tentando adquirir lock, mas {self._current_agent} está ativo")
                return False

            if self._current_agent is None:
                running_models = await self.check_running_models()
                if running_models:
                    logger.info(f"Parando {len(running_models)} modelos em execução antes de iniciar {agent_id}")
                    await self.stop_all_models()

                self._current_agent = agent_id
                logger.info(f"Lock adquirido pelo agente {agent_id}")
                return True

            return True

    async def release_lock(self, agent_id: str):
        async with self._lock:
            if self._current_agent == agent_id:
                self._current_agent = None
                logger.info(f"Lock liberado pelo agente {agent_id}")
            else:
                logger.warning(f"Tentativa de liberar lock por {agent_id}, mas lock pertence a {self._current_agent}")

    async def validate_model_availability(self, model_name: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_base_url}/api/tags", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m.get("name", "") for m in data.get("models", [])]
                        return model_name in models
                    return False
        except Exception as e:
            logger.error(f"Erro ao validar disponibilidade do modelo {model_name}: {str(e)}")
            return False

    async def ensure_model_ready(self, agent_id: str, model_name: str) -> bool:
        if not await self.acquire_lock(agent_id):
            return False

        if not await self.validate_model_availability(model_name):
            logger.error(f"Modelo {model_name} não está disponível para {agent_id}")
            await self.release_lock(agent_id)
            return False

        running_models = await self.check_running_models()
        if running_models:
            logger.info(f"Parando modelos em execução antes de usar {model_name} para {agent_id}")
            await self.stop_all_models()

        return True
