import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path
import numpy as np

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
    
    def __init__(self, config_path: str = None):
        from config.system_config import load_configuration
        from orchestrator.workflow import DEVsAIOrchestrator
        from monitoring.metrics_collector import MetricsCollector
        
        self.config = load_configuration(config_path)
        self.orchestrator = None
        self.metrics_collector = None
        self.is_initialized = False
        
    async def initialize(self):
        """Inicializa o sistema DEVs AI"""
        logger.info("Inicializando sistema DEVs AI...")
        try:
            from orchestrator.workflow import DEVsAIOrchestrator
            
            # Inicializa orquestrador
            self.orchestrator = DEVsAIOrchestrator(self.config)
            
            # Inicializa coletor de métricas
            from monitoring.metrics_collector import MetricsCollector
            self.metrics_collector = MetricsCollector(self.config)
            
            # Pré-carrega modelos e índices
            await self._warmup_system()
            self.is_initialized = True
            logger.info("Sistema DEVs AI inicializado com sucesso!")
        except Exception as e:
            logger.error(f"Falha na inicialização do sistema: {str(e)}")
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
        services = ['Redis', 'ChromaDB', 'Ollama']
        for service in services:
            try:
                if service == 'Redis':
                    import redis
                    redis_client = redis.Redis(
                        host=self.config['redis_host'], 
                        port=self.config['redis_port']
                    )
                    redis_client.ping()
                elif service == 'ChromaDB':
                    import chromadb
                    chromadb.HttpClient(
                        host=self.config['chroma_host'], 
                        port=self.config['chroma_port']
                    )
                elif service == 'Ollama':
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"http://{self.config['ollama_host']}/api/tags") as response:
                            if response.status != 200:
                                raise Exception(f"Ollama retornou status {response.status}")
                logger.info(f"✅ {service} conectado com sucesso")
            except Exception as e:
                logger.error(f"❌ Falha na conexão com {service}: {str(e)}")
                raise
                
    async def _preload_common_prompts(self):
        """Pré-carrega prompts comuns no cache"""
        common_prompts = [
            "Analise os seguintes requisitos e identifique...",
            "Crie histórias de usuário para...",
            "Defina a arquitetura para um sistema que..."
        ]
        for prompt in common_prompts:
            await self.orchestrator.llm_layer.generate_response(prompt, 0.3)
            
    async def process_request(self, user_input: str) -> dict[str, any]:
        """Processa uma solicitação do usuário"""
        if not self.is_initialized:
            raise RuntimeError("Sistema não inicializado")
        logger.info(f"Processando solicitação: {user_input[:100]}...")
        start_time = datetime.utcnow()
        try:
            result = await self.orchestrator.execute_workflow(user_input)
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            # Coleta métricas
            self.metrics_collector.record_agent_metrics('system', {
                'success_rate': 100 if result['success'] else 0,
                'avg_response_time': execution_time,
                'total_requests': 1
            })
            result['execution_time'] = execution_time
            result['timestamp'] = datetime.utcnow().isoformat()
            return result
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Erro no processamento: {str(e)}")
            self.metrics_collector.record_agent_metrics('system', {
                'success_rate': 0,
                'avg_response_time': execution_time,
                'total_requests': 1,
                'error': str(e)
            })
            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time,
                'timestamp': datetime.utcnow().isoformat()
            }
            
    def get_system_status(self) -> dict[str, any]:
        """Retorna status atual do sistema"""
        status = {
            'initialized': self.is_initialized,
            'config': {k: v for k, v in self.config.items() if 'password' not in k.lower()},
            'agents_ready': list(self.orchestrator.agents.keys()) if self.orchestrator else [],
            'services': {
                'redis': 'unknown',
                'chromadb': 'unknown',
                'ollama': 'unknown'
            }
        }
        # Verifica status dos serviços
        try:
            import redis
            redis_client = redis.Redis(host=self.config['redis_host'], port=self.config['redis_port'])
            redis_client.ping()
            status['services']['redis'] = 'healthy'
        except:
            status['services']['redis'] = 'unhealthy'
        return status


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
        start_time = datetime.utcnow()
        result = await system.process_request(user_request)
        execution_time = (datetime.utcnow() - start_time).total_seconds()
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