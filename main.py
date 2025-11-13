import sys
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('devs_ai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DEVs_AI")


class DEVsAISystem:
    """Sistema principal do DEVs AI"""
    
    def __init__(self, config_path: Optional[str] = None):
        from config.system_config import load_configuration
        
        self.config = load_configuration(config_path)
        self.orchestrator = None
        self.metrics_collector = None
        self.is_initialized = False
        
    async def initialize(self):
        """Inicializa o sistema DEVs AI"""
        logger.info("Inicializando sistema DEVs AI...")
        try:
            from orchestrator.workflow import DEVsAIOrchestrator
            from monitoring.metrics_collector import MetricsCollector
            
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
            'Redis': {
                'host_key': 'redis_host',
                'port_key': 'redis_port',
                'test': self._test_redis
            },
            'ChromaDB': {
                'host_key': 'chroma_host',
                'port_key': 'chroma_port',
                'test': self._test_chromadb
            },
            'Ollama': {
                'host_key': 'ollama_host',
                'port_key': None,
                'test': self._test_ollama
            }
        }
        
        for service_name, config in services_config.items():
            try:
                await config['test'](service_name, config)
                logger.info(f"✅ {service_name} conectado com sucesso")
            except KeyError as e:
                logger.warning(f"⚠️ Configuração faltando para {service_name}: {e}")
                # Continua mesmo se a configuração estiver faltando
            except Exception as e:
                logger.error(f"❌ Falha na conexão com {service_name}: {str(e)}")
                raise
    
    async def _test_redis(self, service_name: str, config: Dict[str, Any]) -> None:
        """Testa conectividade com Redis"""
        import redis
        host = self.config.get(config['host_key'], 'localhost')
        port = self.config.get(config['port_key'], 6379)
        redis_client = redis.Redis(host=host, port=port, socket_timeout=2)
        redis_client.ping()
    
    async def _test_chromadb(self, service_name: str, config: Dict[str, Any]) -> None:
        """Testa conectividade com ChromaDB"""
        import chromadb
        host = self.config.get(config['host_key'], 'localhost')
        port = self.config.get(config['port_key'], 8000)
        # Apenas cria o cliente, não testa conexão real (ChromaDB não tem ping)
        chromadb.HttpClient(host=host, port=port)
    
    async def _test_ollama(self, service_name: str, config: Dict[str, Any]) -> None:
        """Testa conectividade com Ollama"""
        import aiohttp
        host = self.config.get(config['host_key'], 'localhost:11434')
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{host}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status != 200:
                    raise Exception(f"Ollama retornou status {response.status}")
                
    async def _preload_common_prompts(self):
        """Pré-carrega prompts comuns no cache"""
        if not self.orchestrator or not hasattr(self.orchestrator, 'llm_layer'):
            logger.warning("Orquestrador ou llm_layer não disponível para pré-carregamento")
            return
        
        common_prompts = [
            "Analise os seguintes requisitos e identifique...",
            "Crie histórias de usuário para...",
            "Defina a arquitetura para um sistema que..."
        ]
        for prompt in common_prompts:
            try:
                await self.orchestrator.llm_layer.generate_response(prompt, 0.3)
            except Exception as e:
                logger.warning(f"Falha ao pré-carregar prompt: {str(e)}")
                # Não interrompe a inicialização se o pré-carregamento falhar
            
    async def process_request(self, user_input: str) -> Dict[str, Any]:
        """Processa uma solicitação do usuário"""
        if not self.is_initialized:
            raise RuntimeError("Sistema não inicializado")
        if not self.orchestrator:
            raise RuntimeError("Orquestrador não inicializado")
        if not user_input or not user_input.strip():
            raise ValueError("Solicitação do usuário não pode estar vazia")
        
        logger.info(f"Processando solicitação: {user_input[:100]}...")
        start_time = datetime.now(timezone.utc)
        try:
            result = await self.orchestrator.execute_workflow(user_input)
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Coleta métricas (se disponível)
            if self.metrics_collector:
                try:
                    self.metrics_collector.record_agent_metrics('system', {
                        'success_rate': 100 if result.get('success', False) else 0,
                        'avg_response_time': execution_time,
                        'total_requests': 1
                    })
                except Exception as metrics_error:
                    logger.warning(f"Erro ao registrar métricas: {str(metrics_error)}")
            
            result['execution_time'] = execution_time
            result['timestamp'] = datetime.now(timezone.utc).isoformat()
            return result
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Erro no processamento: {str(e)}", exc_info=True)
            
            # Coleta métricas de erro (se disponível)
            if self.metrics_collector:
                try:
                    self.metrics_collector.record_agent_metrics('system', {
                        'success_rate': 0,
                        'avg_response_time': execution_time,
                        'total_requests': 1,
                        'error': str(e)
                    })
                except Exception as metrics_error:
                    logger.warning(f"Erro ao registrar métricas de erro: {str(metrics_error)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
    def get_system_status(self) -> Dict[str, Any]:
        """Retorna status atual do sistema"""
        status = {
            'initialized': self.is_initialized,
            'config': {k: v for k, v in self.config.items() if 'password' not in k.lower() and 'api_key' not in k.lower()},
            'agents_ready': list(self.orchestrator.agents.keys()) if self.orchestrator and hasattr(self.orchestrator, 'agents') else [],
            'services': {
                'redis': 'unknown',
                'chromadb': 'unknown',
                'ollama': 'unknown'
            }
        }
        
        # Verifica status dos serviços
        status['services']['redis'] = self._check_redis_status()
        status['services']['chromadb'] = self._check_chromadb_status()
        status['services']['ollama'] = self._check_ollama_status()
        
        return status
    
    def _check_redis_status(self) -> str:
        """Verifica status do Redis"""
        try:
            import redis
            host = self.config.get('redis_host', 'localhost')
            port = self.config.get('redis_port', 6379)
            redis_client = redis.Redis(host=host, port=port, socket_timeout=2)
            redis_client.ping()
            return 'healthy'
        except KeyError:
            return 'not_configured'
        except Exception:
            return 'unhealthy'
    
    def _check_chromadb_status(self) -> str:
        """Verifica status do ChromaDB"""
        try:
            import chromadb
            host = self.config.get('chroma_host', 'localhost')
            port = self.config.get('chroma_port', 8000)
            # ChromaDB não tem método ping, então apenas tenta criar o cliente
            chromadb.HttpClient(host=host, port=port)
            return 'healthy'
        except KeyError:
            return 'not_configured'
        except Exception:
            return 'unhealthy'
    
    def _check_ollama_status(self) -> str:
        """Verifica status do Ollama (versão síncrona usando requests)"""
        try:
            import requests
            host = self.config.get('ollama_host', 'localhost:11434')
            response = requests.get(f"http://{host}/api/tags", timeout=2)
            return 'healthy' if response.status_code == 200 else 'unhealthy'
        except KeyError:
            return 'not_configured'
        except ImportError:
            # Se requests não estiver disponível, tenta com aiohttp de forma segura
            try:
                import aiohttp
                import asyncio
                host = self.config.get('ollama_host', 'localhost:11434')
                
                async def check():
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"http://{host}/api/tags",
                            timeout=aiohttp.ClientTimeout(total=2)
                        ) as response:
                            return response.status == 200
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        return 'unknown'  # Não pode fazer sync call dentro de loop ativo
                    if asyncio.run(check()):
                        return 'healthy'
                    return 'unhealthy'
                except RuntimeError:
                    # Sem loop de evento, cria um novo
                    if asyncio.run(check()):
                        return 'healthy'
                    return 'unhealthy'
            except Exception:
                return 'unknown'
        except Exception:
            return 'unhealthy'


async def main():
    """Função principal de inicialização do sistema"""
    from utils.hardware_detection import detect_hardware_profile
    
    # Detecta perfil de hardware automaticamente
    hardware_profile = detect_hardware_profile()
    config_path = f"config/hardware_profiles/{hardware_profile}.yaml"
    
    system = DEVsAISystem(config_path)
    try:
        await system.initialize()
        print("🚀 DEVs AI Sistema Completo Inicializado!")
        print(f"📊 Agentes Carregados: {len(system.orchestrator.agents)}")
        print(f"⚙️  Perfil de Hardware: {hardware_profile}")
        print("=" * 50)
        
        # Testa com uma solicitação de exemplo
        user_request = """
        Desenvolva um sistema de gerenciamento de tarefas (To-Do List) com:
        - API REST para CRUD de tarefas
        - Interface web moderna
        - Autenticação de usuários
        - Categorização de tarefas
        - Busca e filtros
        - Deploy em Docker
        """
        print("📝 Processando solicitação...")
        start_time = datetime.now(timezone.utc)
        result = await system.process_request(user_request)
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        print(f"⏱️  Tempo de execução: {execution_time:.2f} segundos")
        
        if result['success']:
            print("✅ Projeto concluído com sucesso!")
            final_state = result['final_state']
            print(f"📈 Fases completadas: {final_state['current_phase']}")
            print(f"📁 Estrutura criada: {len(final_state.get('project_structure', {}).get('project_structure', []))} itens")
            print(f"👨‍💻 Tasks implementadas: {len(final_state.get('implemented_code', {}))}")
            print(f"🔍 Revisões realizadas: {len(final_state.get('code_review', {}))}")
            if final_state.get('final_delivery'):
                print("🎉 Entrega final preparada!")
        else:
            print("❌ Erro no processamento:")
            print(f"   Erro: {result.get('error')}")
            print(f"   Sugestões: {result.get('recovery_suggestions', [])}")
    except Exception as e:
        logger.error(f"Erro na execução: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
