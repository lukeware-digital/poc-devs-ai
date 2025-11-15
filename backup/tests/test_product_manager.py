import asyncio
import logging
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.clarifier import Agent1_Clarificador
from agents.product_manager import Agent2_ProductManager
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


async def test_agent1_to_agent2_integration():
    """Testa o fluxo completo Agent1 → Agent2"""
    logger.info(BORDER)
    logger.info("TESTE DE INTEGRAÇÃO AGENT1 → AGENT2")
    logger.info("Testando fluxo completo com integrações reais")
    logger.info(BORDER)

    try:
        logger.info("\n📋 Carregando configuração...")
        config = load_configuration()
        logger.info("   ✅ Configuração carregada")

        logger.info("\n🔧 Configurando componentes...")
        llm_layer, shared_context, rag_retriever, guardrails = await setup_real_components(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"\n📁 Usando diretório temporário: {temp_dir}")
            shared_context.project_state.set("project_path", temp_dir)

            user_input = (
                "Criar uma API REST para gerenciar tarefas com autenticação JWT e banco de dados PostgreSQL"
            )

            logger.info("\n" + "=" * 80)
            logger.info("ETAPA 1: AGENT1 - CLARIFICADOR")
            logger.info("=" * 80)

            logger.info("\n🤖 Criando Agent1_Clarificador...")
            agent1 = Agent1_Clarificador(
                "agent1",
                llm_layer,
                shared_context,
                rag_retriever,
                guardrails,
            )
            logger.info("   ✅ Agent1 criado")

            test_task_agent1 = {
                "user_input": user_input,
                "operation": "requirements_analysis",
            }

            logger.info("\n📝 Input de teste (Agent1):")
            logger.info(f"   {user_input}")
            logger.info("\n🚀 Executando Agent1...")
            logger.info("-" * 80)

            result_agent1 = await agent1.execute(test_task_agent1)

            logger.info("-" * 80)
            logger.info("\n✅ Agent1 concluído!")
            logger.info(f"   Status: {result_agent1.get('status')}")

            if not result_agent1.get("specification"):
                raise ValueError("Agent1 não retornou specification")

            specification = result_agent1["specification"]
            logger.info("\n📋 Especificação gerada pelo Agent1:")
            logger.info(f"   Task ID: {specification.get('task_id')}")
            logger.info(f"   Complexidade: {specification.get('estimated_complexity')}/10")
            logger.info(f"   Critérios de aceitação: {len(specification.get('acceptance_criteria', []))} itens")
            func_reqs = specification.get("requirements_breakdown", {}).get("functional", [])
            logger.info(f"   Requisitos funcionais: {len(func_reqs)} itens")
            non_func_reqs = specification.get("requirements_breakdown", {}).get("non_functional", [])
            logger.info(f"   Requisitos não-funcionais: {len(non_func_reqs)} itens")

            logger.info("\n" + "=" * 80)
            logger.info("ETAPA 2: AGENT2 - PRODUCT MANAGER")
            logger.info("=" * 80)

            logger.info("\n🤖 Criando Agent2_ProductManager...")
            agent2 = Agent2_ProductManager(
                "agent2",
                llm_layer,
                shared_context,
                rag_retriever,
                guardrails,
            )
            logger.info("   ✅ Agent2 criado")

            test_task_agent2 = {
                "specification": specification,
            }

            logger.info("\n📝 Input de teste (Agent2):")
            logger.info(f"   Specification ID: {specification.get('task_id')}")
            logger.info(f"   Description: {specification.get('description', '')[:80]}...")
            logger.info("\n🚀 Executando Agent2...")
            logger.info("-" * 80)

            result_agent2 = await agent2.execute(test_task_agent2)

            logger.info("-" * 80)
            logger.info("\n✅ Agent2 concluído!")
            logger.info(f"   Status: {result_agent2.get('status')}")

            if result_agent2.get("user_stories"):
                stories = result_agent2["user_stories"]
                logger.info("\n📋 Histórias de usuário geradas:")
                logger.info(f"   Total de histórias: {len(stories.get('user_stories', []))}")

                if stories.get("user_stories"):
                    for i, story in enumerate(stories["user_stories"][:3], 1):
                        logger.info(f"\n   História {i}:")
                        logger.info(f"      ID: {story.get('id')}")
                        logger.info(f"      Descrição: {story.get('description', '')[:80]}...")
                        logger.info(f"      Prioridade: {story.get('priority')}")
                        logger.info(f"      Story Points: {story.get('estimated_story_points', 0)}")
                    if len(stories["user_stories"]) > 3:
                        logger.info(f"   ... e mais {len(stories['user_stories']) - 3} histórias")

            logger.info("\n📄 Arquivos gerados:")
            logger.info(f"   Agent1: {temp_dir}/agent1_corrigido.md")
            logger.info(f"   Agent2: {temp_dir}/agent2_historias.md")

            logger.info("\n" + BORDER)
            logger.info("TESTE CONCLUÍDO COM SUCESSO")
            logger.info(BORDER)

            return {
                "agent1_result": result_agent1,
                "agent2_result": result_agent2,
            }

    except Exception as e:
        logger.error("\n" + BORDER)
        logger.error("❌ ERRO NO TESTE")
        logger.error(BORDER)
        logger.error(f"Erro: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        result = asyncio.run(test_agent1_to_agent2_integration())
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Falha crítica: {str(e)}")
        sys.exit(1)
