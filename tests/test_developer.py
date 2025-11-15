import asyncio
import logging
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.developer import Agent6_Desenvolvedor
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


async def test_developer_integration():
    """Testa o Agent6_Desenvolvedor com todas as integrações reais"""
    logger.info(BORDER)
    logger.info("TESTE ISOLADO DO AGENT6_DESENVOLVEDOR")
    logger.info("Testando com integrações reais (sem mocks)")
    logger.info(BORDER)

    try:
        logger.info("\n📋 Carregando configuração...")
        config = load_configuration()
        logger.info("   ✅ Configuração carregada")

        logger.info("\n🔧 Configurando componentes...")
        llm_layer, shared_context, rag_retriever, guardrails = await setup_real_components(config)

        logger.info("\n🤖 Criando Agent6_Desenvolvedor...")
        agent = Agent6_Desenvolvedor(
            "agent6",
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
                "technical_tasks": {
                    "technical_tasks": [
                        {
                            "task_id": "TECH-1",
                            "description": "Implementar modelo de dados para Task",
                            "type": "backend",
                            "complexity": "medium",
                            "acceptance_criteria": [
                                "Modelo deve ter campos: id, title, description, status",
                                "Modelo deve usar SQLAlchemy",
                            ],
                        }
                    ],
                },
                "project_structure": {
                    "project_structure": [
                        {
                            "type": "directory",
                            "path": "src",
                            "name": "",
                        }
                    ],
                },
                "architecture": {
                    "architecture_decision": {
                        "pattern": "REST API",
                    },
                    "technology_stack": {
                        "backend": ["Python", "FastAPI"],
                    },
                },
            }

            logger.info("\n📝 Input de teste:")
            logger.info(f"   Task: {test_task['technical_tasks']['technical_tasks'][0]['description']}")
            logger.info("\n🚀 Executando agente...")
            logger.info("-" * 80)

            result = await agent.execute(test_task)

            logger.info("-" * 80)
            logger.info("\n✅ Teste concluído com sucesso!")
            logger.info("\n📊 Resultado:")
            logger.info(f"   Status: {result.get('status')}")
            logger.info(f"   Tasks implementadas: {len(result.get('implemented_tasks', []))}")
            logger.info(f"   Arquivos modificados: {len(result.get('files_modified', []))}")

            if result.get("code_results"):
                logger.info("\n📋 Resultados do código:")
                for task_id, code_result in list(result["code_results"].items())[:2]:
                    logger.info(f"\n   Task {task_id}:")
                    files = code_result.get("files_created_modified", [])
                    logger.info(f"      Arquivos: {len(files)}")
                    for file_info in files[:2]:
                        logger.info(f"         - {file_info.get('file_path')} ({file_info.get('action')})")

            logger.info(f"\n📁 Código criado em: {temp_dir}")

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
        result = asyncio.run(test_developer_integration())
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Falha crítica: {str(e)}")
        sys.exit(1)

