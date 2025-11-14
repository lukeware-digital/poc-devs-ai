import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from config.logging_config import setup_logging

logger = setup_logging(logging.INFO)


class DEVsAISystem:
    """Sistema principal do DEVs AI"""

    def __init__(self, config_path: str | None = None):
        from config.system_config import load_configuration

        self.config = load_configuration(config_path)
        self.orchestrator = None
        self.metrics_collector = None
        self.is_initialized = False

    async def initialize(self):
        """Inicializa o sistema DEVs AI"""
        logger.info("Inicializando sistema DEVs AI...")
        try:
            from monitoring.metrics_collector import MetricsCollector
            from orchestrator.workflow import DEVsAIOrchestrator

            # Inicializa orquestrador
            self.orchestrator = DEVsAIOrchestrator(self.config)

            # Inicializa coletor de métricas
            self.metrics_collector = MetricsCollector(self.config)

            # Pré-carrega modelos e índices
            await self._warmup_system()
            self.is_initialized = True
            logger.info("Sistema DEVs AI inicializado com sucesso!")
        except Exception as e:
            logger.error(f"Falha na inicialização do sistema: {str(e)}", exc_info=True)
            raise

    async def _warmup_system(self):
        """Pré-aquece o sistema carregando componentes essenciais"""
        logger.info("Pré-aquecendo sistema...")
        # Testa conectividade com serviços
        await self._test_service_connectivity()
        # Pré-carrega alguns prompts comuns
        await self._preload_common_prompts()
        logger.info("Pré-aquecimento concluído")

    async def _test_service_connectivity(self):
        """Testa conectividade com todos os serviços"""
        services_config = {
            "Redis": {"host_key": "redis_host", "port_key": "redis_port", "test": self._test_redis, "required": True},
            "ChromaDB": {
                "host_key": "chroma_host",
                "port_key": "chroma_port",
                "test": self._test_chromadb,
                "required": True,
            },
            "Ollama": {"host_key": "ollama_host", "port_key": None, "test": self._test_ollama, "required": False},
        }

        for service_name, config in services_config.items():
            try:
                await config["test"](service_name, config)
                logger.info(f"✅ {service_name} conectado com sucesso")
            except KeyError as e:
                logger.warning(f"⚠️ Configuração faltando para {service_name}: {e}")
                # Continua mesmo se a configuração estiver faltando
            except Exception as e:
                if config.get("required", True):
                    logger.error(f"❌ Falha na conexão com {service_name}: {str(e)}")
                    raise
                else:
                    msg = (
                        f"⚠️ {service_name} não está disponível: {str(e)}. "
                        "O sistema continuará, mas funcionalidades que dependem deste serviço podem não funcionar."
                    )
                    logger.warning(msg)

    async def _test_redis(self, service_name: str, config: dict[str, Any]) -> None:
        """Testa conectividade com Redis"""
        import redis

        host = self.config.get(config["host_key"], "localhost")
        port = self.config.get(config["port_key"], 6379)
        redis_client = redis.Redis(host=host, port=port, socket_timeout=2)
        redis_client.ping()

    async def _test_chromadb(self, service_name: str, config: dict[str, Any]) -> None:
        """Testa conectividade com ChromaDB"""
        import chromadb

        host = self.config.get(config["host_key"], "localhost")
        port = self.config.get(config["port_key"], 8000)
        # Apenas cria o cliente, não testa conexão real (ChromaDB não tem ping)
        chromadb.HttpClient(host=host, port=port)

    async def _test_ollama(self, service_name: str, config: dict[str, Any]) -> None:
        """Testa conectividade com Ollama"""
        import aiohttp
        from aiohttp import ClientConnectorError, ClientError

        host = self.config.get(config["host_key"], "localhost:11434")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{host}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status != 200:
                        raise Exception(f"Ollama retornou status {response.status}")
        except (ClientConnectorError, ClientError, asyncio.TimeoutError) as e:
            raise ConnectionError(f"Não foi possível conectar ao Ollama em {host}: {str(e)}")

    async def _preload_common_prompts(self):
        """Pré-carrega prompts comuns no cache"""
        if not self.orchestrator or not hasattr(self.orchestrator, "llm_layer"):
            logger.warning("Orquestrador ou llm_layer não disponível para pré-carregamento")
            return

        common_prompts = [
            "Analise os seguintes requisitos e identifique...",
            "Crie histórias de usuário para...",
            "Defina a arquitetura para um sistema que...",
        ]
        for prompt in common_prompts:
            try:
                await asyncio.wait_for(self.orchestrator.llm_layer.generate_response(prompt, 0.3), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Timeout ao pré-carregar prompt (limite: 5s)")
            except Exception as e:
                logger.warning(f"Falha ao pré-carregar prompt: {str(e)}")

    def _record_metrics(self, success: bool, execution_time: float, error: str | None = None):
        if not self.metrics_collector:
            return
        try:
            metrics = {
                "success_rate": 100 if success else 0,
                "avg_response_time": execution_time,
                "total_requests": 1,
            }
            if error:
                metrics["error"] = error
            self.metrics_collector.record_agent_metrics("system", metrics)
        except Exception as metrics_error:
            logger.warning(f"Erro ao registrar métricas: {str(metrics_error)}")

    def _build_error_response(
        self, error_msg: str, execution_time: float, include_suggestions: bool = False
    ) -> dict[str, Any]:
        response = {
            "success": False,
            "error": error_msg,
            "execution_time": execution_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if include_suggestions:
            response["recovery_suggestions"] = [
                "A solicitação pode ser muito complexa",
                "Tente dividir em solicitações menores",
                "Verifique se os serviços estão respondendo corretamente",
            ]
        return response

    async def process_request(
        self,
        user_input: str,
        project_path: str | None = None,
        job_id: str | None = None,
        repository_url: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        """Processa uma solicitação do usuário"""
        if not self.is_initialized:
            raise RuntimeError("Sistema não inicializado")
        if not self.orchestrator:
            raise RuntimeError("Orquestrador não inicializado")
        if not user_input or not user_input.strip():
            raise ValueError("Solicitação do usuário não pode estar vazia")

        logger.info(f"Processando solicitação: {user_input[:100]}...")
        start_time = datetime.now(timezone.utc)
        timeout = self.config.get("orchestrator", {}).get("request_timeout", 600)

        try:
            result = await asyncio.wait_for(
                self.orchestrator.execute_workflow(user_input, project_path, job_id, repository_url, access_token),
                timeout=timeout,
            )
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_metrics(result.get("success", False), execution_time)
            result["execution_time"] = execution_time
            result["timestamp"] = datetime.now(timezone.utc).isoformat()
            return result
        except asyncio.TimeoutError:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            error_msg = f"Processamento excedeu o tempo limite de {timeout} segundos"
            logger.error(error_msg)
            self._record_metrics(False, execution_time, "timeout")
            return self._build_error_response(error_msg, execution_time, include_suggestions=True)
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Erro no processamento: {str(e)}", exc_info=True)
            self._record_metrics(False, execution_time, str(e))
            return self._build_error_response(str(e), execution_time)

    async def get_system_status(self) -> dict[str, Any]:
        """Retorna status atual do sistema"""
        status = {
            "initialized": self.is_initialized,
            "config": {
                k: v for k, v in self.config.items() if "password" not in k.lower() and "api_key" not in k.lower()
            },
            "agents_ready": list(self.orchestrator.agents.keys())
            if self.orchestrator and hasattr(self.orchestrator, "agents")
            else [],
            "services": {"redis": "unknown", "chromadb": "unknown", "ollama": "unknown"},
        }

        # Verifica status dos serviços
        status["services"]["redis"] = await self._check_redis_status()
        status["services"]["chromadb"] = await self._check_chromadb_status()
        status["services"]["ollama"] = await self._check_ollama_status()

        return status

    async def _check_redis_status(self) -> str:
        """Verifica status do Redis"""

        def _check():
            try:
                import redis

                host = self.config.get("redis_host", "localhost")
                port = self.config.get("redis_port", 6379)
                redis_client = redis.Redis(host=host, port=port, socket_timeout=2)
                redis_client.ping()
                return "healthy"
            except KeyError:
                return "not_configured"
            except Exception:
                return "unhealthy"

        return await asyncio.to_thread(_check)

    async def _check_chromadb_status(self) -> str:
        """Verifica status do ChromaDB"""

        def _check():
            try:
                import chromadb

                host = self.config.get("chroma_host", "localhost")
                port = self.config.get("chroma_port", 8000)
                # ChromaDB não tem método ping, então apenas tenta criar o cliente
                chromadb.HttpClient(host=host, port=port)
                return "healthy"
            except KeyError:
                return "not_configured"
            except Exception:
                return "unhealthy"

        return await asyncio.to_thread(_check)

    async def _check_ollama_status(self) -> str:
        """Verifica status do Ollama"""

        def _check():
            try:
                import requests

                host = self.config.get("ollama_host", "localhost:11434")
                response = requests.get(f"http://{host}/api/tags", timeout=2)
                return "healthy" if response.status_code == 200 else "unhealthy"
            except KeyError:
                return "not_configured"
            except ImportError:
                return "unknown"
            except Exception:
                return "unhealthy"

        return await asyncio.to_thread(_check)


async def main():
    """Função principal de inicialização do sistema"""
    import os

    import uvicorn

    from api.server import app

    port = int(os.getenv("PORT", 8181))
    logger.info("Iniciando servidor API...")
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
