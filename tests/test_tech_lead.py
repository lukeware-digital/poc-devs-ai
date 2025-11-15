import asyncio
import logging
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.tech_lead import Agent4_TechLead
from config.system_config import load_configuration
from guardrails.capability_tokens import CapabilityTokenManager
from guardrails.security_system import GuardrailSystem
from rag.retriever import RAGRetriever
from shared_context.context_manager import SharedContext
from utils.embedders import SimpleEmbedder
from utils.llm_abstraction import LLMAbstractLayer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("devs-ai")

BORDER = "═" * 80

async def setup_real_components(config: dict):
    """Configura todos os componentes reais necessários"""
    logger.info("=== Configurando componentes reais ===")

    logger.info("1. Inicializando LLMAbstractLayer...")
    llm_layer = LLMAbstractLayer(config)
    logger.info(f"   ✅ LLMAbstractLayer inicializado com {len(llm_layer.providers)} provedores")

    logger.info("2. Inicializando SharedContext...")
    shared_context = SharedContext(config)
    logger.info("   ✅ SharedContext inicializado")

    logger.info("3. Inicializando ChromaDB client...")
    from chromadb import HttpClient

    chroma_client = HttpClient(
        host=config.get("chroma_host", "localhost"),
        port=config.get("chroma_port", 8000),
    )
    logger.info("   ✅ ChromaDB client conectado")

    logger.info("4. Inicializando embedders...")
    embedders = {
        "semantic": SimpleEmbedder(dimensions=384),
        "technical": SimpleEmbedder(dimensions=384),
        "contextual": SimpleEmbedder(dimensions=384),
    }
    logger.info("   ✅ Embedders inicializados")

    logger.info("5. Inicializando RAGRetriever...")
    rag_retriever = RAGRetriever(chroma_client, embedders)
    logger.info("   ✅ RAGRetriever inicializado")

    logger.info("6. Inicializando GuardrailSystem...")
    token_manager = CapabilityTokenManager()
    guardrails = GuardrailSystem(token_manager)
    logger.info("   ✅ GuardrailSystem inicializado")

    return llm_layer, shared_context, rag_retriever, guardrails


async def test_tech_lead_integration():
    """Testa o Agent4_TechLead com todas as integrações reais"""
    logger.info(BORDER)
    logger.info("TESTE ISOLADO DO AGENT4_TECH_LEAD")
    logger.info("Testando com integrações reais (sem mocks)")
    logger.info(BORDER)

    try:
        logger.info("\n📋 Carregando configuração...")
        config = load_configuration()
        logger.info("   ✅ Configuração carregada")

        logger.info("\n🔧 Configurando componentes...")
        llm_layer, shared_context, rag_retriever, guardrails = await setup_real_components(config)

        logger.info("\n🤖 Criando Agent4_TechLead...")
        agent = Agent4_TechLead(
            "agent4",
            llm_layer,
            shared_context,
            rag_retriever,
            guardrails,
        )
        logger.info("   ✅ Agente criado")

        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"\n📁 Usando diretório temporário: {temp_dir}")
            shared_context.project_state.set("project_path", temp_dir)

            test_task = {
                "specification": {
                    "task_id": "test_task_001",
                    "description": "Criar uma API REST para gerenciar tarefas com autenticação JWT e banco de dados PostgreSQL",
                    "acceptance_criteria": [
                        "API deve suportar CRUD completo de tarefas",
                        "Autenticação JWT deve ser implementada",
                    ],
                    "estimated_complexity": 7,
                },
                "architecture": {
                    "architecture_decision": {
                        "pattern": "REST API",
                        "rationale": "Padrão adequado para APIs web",
                    },
                    "components": [
                        {
                            "name": "API Server",
                            "responsibility": "Servir requisições HTTP",
                            "technology": "FastAPI",
                        }
                    ],
                    "technology_stack": {
                        "backend": ["Python", "FastAPI"],
                        "database": ["PostgreSQL"],
                    },
                },
                "user_stories": {
                    "user_stories": [
                        {
                            "id": "US-1",
                            "description": "Como usuário, eu quero criar tarefas para organizar meu trabalho",
                            "priority": "high",
                        }
                    ],
                },
            }

            logger.info("\n📝 Input de teste:")
            logger.info(f"   Specification: {test_task['specification']['description']}")
            logger.info("\n🚀 Executando agente...")
            logger.info("-" * 80)

            result = await agent.execute(test_task)

            logger.info("-" * 80)
            logger.info("\n✅ Teste concluído com sucesso!")
            logger.info("\n📊 Resultado:")
            logger.info(f"   Status: {result.get('status')}")

            if result.get("technical_tasks"):
                tasks = result["technical_tasks"]
                logger.info("\n📋 Tasks técnicas geradas:")
                logger.info(f"   Total de tasks: {len(tasks.get('technical_tasks', []))}")
                
                if tasks.get("technical_tasks"):
                    for i, task in enumerate(tasks["technical_tasks"][:3], 1):
                        logger.info(f"\n   Task {i}:")
                        logger.info(f"      ID: {task.get('task_id')}")
                        logger.info(f"      Tipo: {task.get('type')}")
                        logger.info(f"      Complexidade: {task.get('complexity')}")
                        logger.info(f"      Horas estimadas: {task.get('estimated_hours', 0)}")
                    if len(tasks["technical_tasks"]) > 3:
                        logger.info(f"   ... e mais {len(tasks['technical_tasks']) - 3} tasks")

            logger.info(f"\n📄 Arquivo technical_tasks.md criado em: {temp_dir}/technical_tasks.md")

            logger.info("\n" + BORDER)
            logger.info("TESTE CONCLUÍDO COM SUCESSO")
            logger.info(BORDER)

            return result

    except Exception as e:
        logger.error("\n" + BORDER)
        logger.error("❌ ERRO NO TESTE")
        logger.error(BORDER)
        logger.error(f"Erro: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        result = asyncio.run(test_tech_lead_integration())
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Falha crítica: {str(e)}")
        sys.exit(1)

