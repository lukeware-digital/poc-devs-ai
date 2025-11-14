"""
Sistema de orquestração do fluxo de trabalho usando LangGraph
"""

import logging
from datetime import datetime

from agents.architect import Agent3_Arquiteto
from agents.clarifier import Agent1_Clarificador
from agents.code_reviewer import Agent7_CodeReviewer
from agents.developer import Agent6_Desenvolvedor
from agents.finalizer import Agent8_Finalizador
from agents.product_manager import Agent2_ProductManager
from agents.scaffolder import Agent5_Scaffolder
from agents.tech_lead import Agent4_TechLead
from config.logging_config import AgentAdapter
from database.job_repository import JobRepository
from database.step_repository import StepRepository
from guardrails.security_system import GuardrailSystem
from monitoring.metrics_collector import MetricsCollector
from orchestrator.fallback_handler import FallbackHandler
from orchestrator.models import ProjectState
from rag.retriever import RAGRetriever
from shared_context.context_manager import SharedContext
from utils.llm_manager import LLMManager

logger = logging.getLogger("DEVs_AI")
workflow_logger = AgentAdapter(logger, {"agent_id": "workflow"})


class DEVsAIOrchestrator:
    """
    Orquestrador principal do sistema DEVs AI usando LangGraph
    """

    def __init__(self, config: dict[str, any]):
        self.config = config
        self.shared_context = SharedContext(config)
        self.metrics_collector = MetricsCollector(config)
        self.fallback_handler = FallbackHandler(self.shared_context)
        self.llm_manager = LLMManager(config)
        self.single_agent_mode = config.get("orchestrator", {}).get("single_agent_mode", True)
        self.setup_components()
        self.workflow = self.create_complete_workflow()

    def setup_components(self):
        """Configura todos os componentes necessários para o orquestrador"""
        from utils.embedders import SimpleEmbedder

        # Configura LLM Layer
        from utils.llm_abstraction import LLMAbstractLayer

        self.llm_layer = LLMAbstractLayer(self.config)

        # Configura RAG
        from chromadb import HttpClient

        self.chroma_client = HttpClient(
            host=self.config.get("chroma_host", "localhost"),
            port=self.config.get("chroma_port", 8000),
        )

        # Configura embedders
        embedders = {
            "semantic": SimpleEmbedder(dimensions=384),
            "technical": SimpleEmbedder(dimensions=384),
            "contextual": SimpleEmbedder(dimensions=384),
        }

        self.rag_retriever = RAGRetriever(self.chroma_client, embedders)

        # Configura Guardrails
        from guardrails.capability_tokens import CapabilityTokenManager

        token_manager = CapabilityTokenManager()
        self.guardrails = GuardrailSystem(token_manager)

        # Inicializa todos os agentes
        self.agents = {
            "agent1": Agent1_Clarificador(
                "agent1",
                self.llm_layer,
                self.shared_context,
                self.rag_retriever,
                self.guardrails,
            ),
            "agent2": Agent2_ProductManager(
                "agent2",
                self.llm_layer,
                self.shared_context,
                self.rag_retriever,
                self.guardrails,
            ),
            "agent3": Agent3_Arquiteto(
                "agent3",
                self.llm_layer,
                self.shared_context,
                self.rag_retriever,
                self.guardrails,
            ),
            "agent4": Agent4_TechLead(
                "agent4",
                self.llm_layer,
                self.shared_context,
                self.rag_retriever,
                self.guardrails,
            ),
            "agent5": Agent5_Scaffolder(
                "agent5",
                self.llm_layer,
                self.shared_context,
                self.rag_retriever,
                self.guardrails,
            ),
            "agent6": Agent6_Desenvolvedor(
                "agent6",
                self.llm_layer,
                self.shared_context,
                self.rag_retriever,
                self.guardrails,
            ),
            "agent7": Agent7_CodeReviewer(
                "agent7",
                self.llm_layer,
                self.shared_context,
                self.rag_retriever,
                self.guardrails,
            ),
            "agent8": Agent8_Finalizador(
                "agent8",
                self.llm_layer,
                self.shared_context,
                self.rag_retriever,
                self.guardrails,
            ),
        }

        logger.info(f"✅ Todos os {len(self.agents)} agentes inicializados com sucesso")

    def create_complete_workflow(self):
        """Cria o workflow completo usando LangGraph"""
        from langgraph.graph import END, StateGraph

        workflow = StateGraph(ProjectState)

        # Adiciona todos os nós principais (um para cada agente)
        workflow.add_node("agent1", self.agent1_node)
        workflow.add_node("agent2", self.agent2_node)
        workflow.add_node("agent3", self.agent3_node)
        workflow.add_node("agent4", self.agent4_node)
        workflow.add_node("agent5", self.agent5_node)
        workflow.add_node("agent6", self.agent6_node)
        workflow.add_node("agent7", self.agent7_node)
        workflow.add_node("agent8", self.agent8_node)

        # Adiciona nós de recuperação
        workflow.add_node("fallback_agent", self.fallback_agent_node)
        workflow.add_node("fallback_agent1", self.fallback_agent1_node)
        workflow.add_node("rollback_state", self.rollback_state_node)
        workflow.add_node("human_supervisor", self.human_supervisor_node)

        # Define condições de falha
        def check_failure(state: ProjectState) -> str:
            if state.last_operation.get("success", True):
                return "continue"
            elif state.failure_count < self.config.get("orchestrator", {}).get("max_auto_retries", 3):
                return "auto_recovery"
            else:
                return "human_intervention"

        # Conecta os nós com lógica condicional
        workflow.add_conditional_edges(
            "agent1",
            check_failure,
            {
                "continue": "agent2",
                "auto_recovery": "fallback_agent",
                "human_intervention": "human_supervisor",
            },
        )
        workflow.add_conditional_edges(
            "agent2",
            check_failure,
            {
                "continue": "agent3",
                "auto_recovery": "fallback_agent",
                "human_intervention": "human_supervisor",
            },
        )
        workflow.add_conditional_edges(
            "agent3",
            check_failure,
            {
                "continue": "agent4",
                "auto_recovery": "fallback_agent",
                "human_intervention": "human_supervisor",
            },
        )
        workflow.add_conditional_edges(
            "agent4",
            check_failure,
            {
                "continue": "agent5",
                "auto_recovery": "fallback_agent",
                "human_intervention": "human_supervisor",
            },
        )
        workflow.add_conditional_edges(
            "agent5",
            check_failure,
            {
                "continue": "agent6",
                "auto_recovery": "fallback_agent",
                "human_intervention": "human_supervisor",
            },
        )
        workflow.add_conditional_edges(
            "agent6",
            check_failure,
            {
                "continue": "agent7",
                "auto_recovery": "fallback_agent",
                "human_intervention": "human_supervisor",
            },
        )
        workflow.add_conditional_edges(
            "agent7",
            check_failure,
            {
                "continue": "agent8",
                "auto_recovery": "fallback_agent",
                "human_intervention": "human_supervisor",
            },
        )

        def check_agent8_next(state: ProjectState) -> str:
            if not state.last_operation.get("success", True):
                return "human_intervention"
            if state.current_phase == "review_loop":
                return "continue_review"
            if state.current_phase == "project_complete":
                return "end"
            return "human_intervention"

        workflow.add_conditional_edges(
            "agent8",
            check_agent8_next,
            {
                "end": END,
                "continue_review": "agent7",
                "human_intervention": "human_supervisor",
            },
        )

        # Conexões de recuperação
        workflow.add_edge("fallback_agent", "rollback_state")
        workflow.add_edge("rollback_state", "agent1")  # Reinicia do início após rollback

        workflow.set_entry_point("agent1")
        return workflow.compile()

    async def _prepare_agent_execution(self, agent_id: str, state: ProjectState) -> bool:
        if not self.single_agent_mode:
            return True

        model_name = self.config.get("agent_models", {}).get(agent_id, self.config.get("primary_model", ""))
        ready = await self.llm_manager.ensure_model_ready(agent_id, model_name)

        if ready and state.job_id:
            if state.current_step_id:
                previous_step = await StepRepository.get_step(state.current_step_id)
                if previous_step and previous_step.get("status") == "running":
                    await StepRepository.update_step_status(state.current_step_id, "completed")

            step_name = f"{agent_id}_{state.current_phase}"
            step_id = await StepRepository.create_step(
                job_id=state.job_id,
                agent_id=agent_id,
                step_name=step_name,
                metadata={"phase": state.current_phase},
            )
            state.current_step_id = step_id
            await StepRepository.update_step_status(step_id, "running")

        return ready

    async def _cleanup_agent_execution(
        self, agent_id: str, state: ProjectState, success: bool = True, error: str | None = None
    ):
        if self.single_agent_mode:
            await self.llm_manager.release_lock(agent_id)

        if state.current_step_id:
            if success:
                await StepRepository.update_step_status(state.current_step_id, "completed")
            else:
                await StepRepository.record_step_failure(
                    state.current_step_id,
                    error_message=error or "Erro desconhecido",
                    error_cause=f"Falha na execução do {agent_id}",
                )

        import gc

        gc.collect()

    async def agent1_node(self, state: ProjectState) -> ProjectState:
        """Executa o nó do Agent-1 (Clarificador)"""
        workflow_logger.info("Iniciando execução do Agent-1 (Clarificador)")
        start_time = datetime.utcnow()

        agent_id = "agent1"

        try:
            if not await self._prepare_agent_execution(agent_id, state):
                raise Exception(f"Não foi possível garantir disponibilidade do modelo para {agent_id}")

            workflow_logger.debug(f"Fase atual: {state.current_phase}")
            result = await self.agents["agent1"].execute(
                {
                    "user_input": state.last_operation.get("user_input", ""),
                    "operation": "requirements_analysis",
                }
            )

            state.task_specification = result.get("specification")
            state.last_operation = {
                "success": True,
                "agent": "agent1",
                "result": result,
                "timestamp": datetime.utcnow(),
            }
            state.current_phase = "specification_complete"

            execution_time = (datetime.utcnow() - start_time).total_seconds()
            workflow_logger.info(f"Agent-1 concluído com sucesso em {execution_time:.2f}s")
            workflow_logger.info("Transição: Agent-1 -> Agent-2")

            await self._cleanup_agent_execution(agent_id, state, success=True)

            self.metrics_collector.record_agent_metrics(
                "agent1",
                {
                    "success": True,
                    "execution_time": execution_time,
                    "tasks_processed": 1,
                },
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            workflow_logger.error(f"Agent-1 falhou após {execution_time:.2f}s: {str(e)}")

            await self._cleanup_agent_execution(agent_id, state, success=False, error=str(e))

            if state.job_id:
                await JobRepository.update_job_failure_info(
                    job_id=state.job_id,
                    failed_step_id=state.current_step_id,
                    failed_agent_id=agent_id,
                )

            state.last_operation = {
                "success": False,
                "agent": "agent1",
                "error": str(e),
                "timestamp": datetime.utcnow(),
            }
            state.failure_count += 1

            self.metrics_collector.record_agent_metrics(
                "agent1",
                {
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time,
                },
            )

        return state

    async def agent2_node(self, state: ProjectState) -> ProjectState:
        """Executa o nó do Agent-2 (Product Manager)"""
        workflow_logger.info("Iniciando execução do Agent-2 (Product Manager)")
        start_time = datetime.utcnow()
        agent_id = "agent2"

        try:
            if not await self._prepare_agent_execution(agent_id, state):
                raise Exception(f"Não foi possível garantir disponibilidade do modelo para {agent_id}")

            workflow_logger.debug(f"Fase atual: {state.current_phase}")
            result = await self.agents["agent2"].execute(
                {
                    "specification": state.task_specification,
                    "operation": "user_stories_creation",
                }
            )

            state.user_stories = result.get("user_stories")
            state.last_operation = {
                "success": True,
                "agent": "agent2",
                "result": result,
                "timestamp": datetime.utcnow(),
            }
            state.current_phase = "user_stories_complete"

            execution_time = (datetime.utcnow() - start_time).total_seconds()
            stories_count = len(result.get("user_stories", {}).get("user_stories", []))
            workflow_logger.info(
                f"Agent-2 concluído com sucesso em {execution_time:.2f}s ({stories_count} stories criadas)"
            )
            workflow_logger.info("Transição: Agent-2 -> Agent-3")

            await self._cleanup_agent_execution(agent_id, state, success=True)

            self.metrics_collector.record_agent_metrics(
                "agent2",
                {
                    "success": True,
                    "execution_time": execution_time,
                    "stories_created": stories_count,
                },
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            workflow_logger.error(f"Agent-2 falhou após {execution_time:.2f}s: {str(e)}")

            await self._cleanup_agent_execution(agent_id, state, success=False, error=str(e))

            if state.job_id:
                await JobRepository.update_job_failure_info(
                    job_id=state.job_id,
                    failed_step_id=state.current_step_id,
                    failed_agent_id=agent_id,
                )

            state.last_operation = {
                "success": False,
                "agent": "agent2",
                "error": str(e),
                "timestamp": datetime.utcnow(),
            }
            state.failure_count += 1

            self.metrics_collector.record_agent_metrics(
                "agent2",
                {
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time,
                },
            )

        return state

    async def agent3_node(self, state: ProjectState) -> ProjectState:
        """Executa o nó do Agent-3 (Arquiteto)"""
        workflow_logger.info("Iniciando execução do Agent-3 (Arquiteto)")
        start_time = datetime.utcnow()
        agent_id = "agent3"

        try:
            if not await self._prepare_agent_execution(agent_id, state):
                raise Exception(f"Não foi possível garantir disponibilidade do modelo para {agent_id}")

            workflow_logger.debug(f"Fase atual: {state.current_phase}")
            result = await self.agents["agent3"].execute(
                {
                    "specification": state.task_specification,
                    "user_stories": state.user_stories,
                    "operation": "architecture_definition",
                }
            )

            state.architecture = result.get("architecture")
            state.last_operation = {
                "success": True,
                "agent": "agent3",
                "result": result,
                "timestamp": datetime.utcnow(),
            }
            state.current_phase = "architecture_complete"

            execution_time = (datetime.utcnow() - start_time).total_seconds()
            components_count = len(result.get("architecture", {}).get("components", []))
            workflow_logger.info(
                f"Agent-3 concluído com sucesso em {execution_time:.2f}s ({components_count} componentes)"
            )
            workflow_logger.info("Transição: Agent-3 -> Agent-4")

            await self._cleanup_agent_execution(agent_id, state, success=True)

            self.metrics_collector.record_agent_metrics(
                "agent3",
                {
                    "success": True,
                    "execution_time": execution_time,
                    "components_defined": components_count,
                },
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            workflow_logger.error(f"Agent-3 falhou após {execution_time:.2f}s: {str(e)}")

            await self._cleanup_agent_execution(agent_id, state, success=False, error=str(e))

            if state.job_id:
                await JobRepository.update_job_failure_info(
                    job_id=state.job_id,
                    failed_step_id=state.current_step_id,
                    failed_agent_id=agent_id,
                )

            state.last_operation = {
                "success": False,
                "agent": "agent3",
                "error": str(e),
                "timestamp": datetime.utcnow(),
            }
            state.failure_count += 1

            self.metrics_collector.record_agent_metrics(
                "agent3",
                {
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time,
                },
            )

        return state

    async def agent4_node(self, state: ProjectState) -> ProjectState:
        """Executa o nó do Agent-4 (Tech Lead)"""
        workflow_logger.info("Iniciando execução do Agent-4 (Tech Lead)")
        start_time = datetime.utcnow()
        agent_id = "agent4"

        try:
            if not await self._prepare_agent_execution(agent_id, state):
                raise Exception(f"Não foi possível garantir disponibilidade do modelo para {agent_id}")

            workflow_logger.debug(f"Fase atual: {state.current_phase}")
            result = await self.agents["agent4"].execute(
                {
                    "specification": state.task_specification,
                    "architecture": state.architecture,
                    "user_stories": state.user_stories,
                    "operation": "technical_planning",
                }
            )

            state.technical_tasks = result.get("technical_tasks")
            state.last_operation = {
                "success": True,
                "agent": "agent4",
                "result": result,
                "timestamp": datetime.utcnow(),
            }
            state.current_phase = "technical_planning_complete"

            execution_time = (datetime.utcnow() - start_time).total_seconds()
            tasks_count = len(result.get("technical_tasks", {}).get("technical_tasks", []))
            workflow_logger.info(
                f"Agent-4 concluído com sucesso em {execution_time:.2f}s ({tasks_count} tarefas criadas)"
            )
            workflow_logger.info("Transição: Agent-4 -> Agent-5")

            await self._cleanup_agent_execution(agent_id, state, success=True)

            self.metrics_collector.record_agent_metrics(
                "agent4",
                {
                    "success": True,
                    "execution_time": execution_time,
                    "tasks_created": tasks_count,
                },
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            workflow_logger.error(f"Agent-4 falhou após {execution_time:.2f}s: {str(e)}")

            await self._cleanup_agent_execution(agent_id, state, success=False, error=str(e))

            if state.job_id:
                await JobRepository.update_job_failure_info(
                    job_id=state.job_id,
                    failed_step_id=state.current_step_id,
                    failed_agent_id=agent_id,
                )

            state.last_operation = {
                "success": False,
                "agent": "agent4",
                "error": str(e),
                "timestamp": datetime.utcnow(),
            }
            state.failure_count += 1

            self.metrics_collector.record_agent_metrics(
                "agent4",
                {
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time,
                },
            )

        return state

    async def agent5_node(self, state: ProjectState) -> ProjectState:
        """Executa o nó do Agent-5 (Scaffolder)"""
        workflow_logger.info("Iniciando execução do Agent-5 (Scaffolder)")
        start_time = datetime.utcnow()
        agent_id = "agent5"

        try:
            if not await self._prepare_agent_execution(agent_id, state):
                raise Exception(f"Não foi possível garantir disponibilidade do modelo para {agent_id}")

            workflow_logger.debug(f"Fase atual: {state.current_phase}")
            result = await self.agents["agent5"].execute(
                {
                    "architecture": state.architecture,
                    "technical_tasks": state.technical_tasks,
                    "operation": "project_scaffolding",
                }
            )

            state.project_structure = result.get("project_structure")
            state.last_operation = {
                "success": True,
                "agent": "agent5",
                "result": result,
                "timestamp": datetime.utcnow(),
            }
            state.current_phase = "scaffolding_complete"

            execution_time = (datetime.utcnow() - start_time).total_seconds()
            files_count = len(result.get("files_created", []))
            workflow_logger.info(
                f"Agent-5 concluído com sucesso em {execution_time:.2f}s ({files_count} arquivos criados)"
            )
            workflow_logger.info("Transição: Agent-5 -> Agent-6")

            await self._cleanup_agent_execution(agent_id, state, success=True)

            self.metrics_collector.record_agent_metrics(
                "agent5",
                {
                    "success": True,
                    "execution_time": execution_time,
                    "files_created": files_count,
                },
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            workflow_logger.error(f"Agent-5 falhou após {execution_time:.2f}s: {str(e)}")

            await self._cleanup_agent_execution(agent_id, state, success=False, error=str(e))

            if state.job_id:
                await JobRepository.update_job_failure_info(
                    job_id=state.job_id,
                    failed_step_id=state.current_step_id,
                    failed_agent_id=agent_id,
                )

            state.last_operation = {
                "success": False,
                "agent": "agent5",
                "error": str(e),
                "timestamp": datetime.utcnow(),
            }
            state.failure_count += 1

            self.metrics_collector.record_agent_metrics(
                "agent5",
                {
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time,
                },
            )

        return state

    async def agent6_node(self, state: ProjectState) -> ProjectState:
        """Executa o nó do Agent-6 (Desenvolvedor)"""
        workflow_logger.info("Iniciando execução do Agent-6 (Desenvolvedor)")
        start_time = datetime.utcnow()
        agent_id = "agent6"

        try:
            if not await self._prepare_agent_execution(agent_id, state):
                raise Exception(f"Não foi possível garantir disponibilidade do modelo para {agent_id}")

            workflow_logger.debug(f"Fase atual: {state.current_phase}")
            result = await self.agents["agent6"].execute(
                {
                    "technical_tasks": state.technical_tasks,
                    "project_structure": state.project_structure,
                    "architecture": state.architecture,
                    "operation": "code_implementation",
                }
            )

            state.implemented_code = result.get("code_results")
            state.last_operation = {
                "success": True,
                "agent": "agent6",
                "result": result,
                "timestamp": datetime.utcnow(),
            }
            state.current_phase = "implementation_complete"

            execution_time = (datetime.utcnow() - start_time).total_seconds()
            tasks_impl = len(result.get("implemented_tasks", []))
            files_mod = len(result.get("files_modified", []))
            workflow_logger.info(
                f"Agent-6 concluído com sucesso em {execution_time:.2f}s ({tasks_impl} tarefas, {files_mod} arquivos)"
            )
            workflow_logger.info("Transição: Agent-6 -> Agent-7")

            await self._cleanup_agent_execution(agent_id, state, success=True)

            self.metrics_collector.record_agent_metrics(
                "agent6",
                {
                    "success": True,
                    "execution_time": execution_time,
                    "tasks_implemented": tasks_impl,
                    "files_modified": files_mod,
                },
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            workflow_logger.error(f"Agent-6 falhou após {execution_time:.2f}s: {str(e)}")

            await self._cleanup_agent_execution(agent_id, state, success=False, error=str(e))

            if state.job_id:
                await JobRepository.update_job_failure_info(
                    job_id=state.job_id,
                    failed_step_id=state.current_step_id,
                    failed_agent_id=agent_id,
                )

            state.last_operation = {
                "success": False,
                "agent": "agent6",
                "error": str(e),
                "timestamp": datetime.utcnow(),
            }
            state.failure_count += 1

            self.metrics_collector.record_agent_metrics(
                "agent6",
                {
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time,
                },
            )

        return state

    async def agent7_node(self, state: ProjectState) -> ProjectState:
        """Executa o nó do Agent-7 (Code Reviewer)"""
        workflow_logger.info("Iniciando execução do Agent-7 (Code Reviewer)")
        start_time = datetime.utcnow()
        agent_id = "agent7"

        try:
            if not await self._prepare_agent_execution(agent_id, state):
                raise Exception(f"Não foi possível garantir disponibilidade do modelo para {agent_id}")

            workflow_logger.debug(f"Fase atual: {state.current_phase}")
            result = await self.agents["agent7"].execute(
                {
                    "implemented_code": state.implemented_code,
                    "technical_tasks": state.technical_tasks,
                    "architecture": state.architecture,
                    "operation": "code_review",
                }
            )

            state.code_review = result.get("reviews")
            state.last_operation = {
                "success": True,
                "agent": "agent7",
                "result": result,
                "timestamp": datetime.utcnow(),
            }
            state.current_phase = "review_complete"

            execution_time = (datetime.utcnow() - start_time).total_seconds()
            reviews_count = len(result.get("reviews", {}))
            approved = result.get("overall_approval", False)
            quality_score = result.get("quality_metrics", {}).get("average_score", 0)

            if not approved:
                state.failure_count += 1
                workflow_logger.warning(f"Agent-7 concluído mas código não aprovado (score: {quality_score})")
            else:
                workflow_logger.info(
                    f"Agent-7 concluído com sucesso em {execution_time:.2f}s "
                    f"({reviews_count} revisões, score: {quality_score})"
                )

            workflow_logger.info("Transição: Agent-7 -> Agent-8")

            await self._cleanup_agent_execution(agent_id, state, success=True)

            self.metrics_collector.record_agent_metrics(
                "agent7",
                {
                    "success": True,
                    "execution_time": execution_time,
                    "reviews_performed": reviews_count,
                    "overall_approval": approved,
                    "quality_score": quality_score,
                },
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            workflow_logger.error(f"Agent-7 falhou após {execution_time:.2f}s: {str(e)}")

            await self._cleanup_agent_execution(agent_id, state, success=False, error=str(e))

            if state.job_id:
                await JobRepository.update_job_failure_info(
                    job_id=state.job_id,
                    failed_step_id=state.current_step_id,
                    failed_agent_id=agent_id,
                )

            state.last_operation = {
                "success": False,
                "agent": "agent7",
                "error": str(e),
                "timestamp": datetime.utcnow(),
            }
            state.failure_count += 1

            self.metrics_collector.record_agent_metrics(
                "agent7",
                {
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time,
                },
            )

        return state

    async def agent8_node(self, state: ProjectState) -> ProjectState:
        """Executa o nó do Agent-8 (Finalizador)"""
        workflow_logger.info("Iniciando execução do Agent-8 (Finalizador)")
        start_time = datetime.utcnow()
        agent_id = "agent8"

        try:
            if not await self._prepare_agent_execution(agent_id, state):
                raise Exception(f"Não foi possível garantir disponibilidade do modelo para {agent_id}")

            workflow_logger.debug(f"Fase atual: {state.current_phase}")
            result = await self.agents["agent8"].execute(
                {
                    "implemented_code": state.implemented_code,
                    "code_review": state.code_review,
                    "project_structure": state.project_structure,
                    "technical_tasks": state.technical_tasks,
                    "repository_url": state.repository_url,
                    "access_token": state.access_token,
                    "operation": "final_delivery",
                }
            )

            if result.get("should_loop_back", False):
                state.code_review_count += 1
                max_reviews = self.config.get("orchestrator", {}).get("max_code_reviews_per_job", 5)
                if state.code_review_count >= max_reviews:
                    workflow_logger.warning(f"Limite de code reviews atingido ({max_reviews}). Finalizando job.")
                    state.current_phase = "project_complete"
                else:
                    workflow_logger.info(
                        f"Voltando para code review (tentativa {state.code_review_count}/{max_reviews})"
                    )
                    state.current_phase = "review_loop"
            else:
                state.final_delivery = result.get("final_delivery")
                state.current_phase = "project_complete"

            state.last_operation = {
                "success": True,
                "agent": "agent8",
                "result": result,
                "timestamp": datetime.utcnow(),
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()
            docs_count = len(result.get("documentation_generated", {}))
            corrections_count = len(result.get("corrections_applied", {}))
            workflow_logger.info(
                f"Agent-8 concluído com sucesso em {execution_time:.2f}s "
                f"({docs_count} docs, {corrections_count} correções)"
            )
            workflow_logger.info("Workflow completo! Projeto finalizado.")

            await self._cleanup_agent_execution(agent_id, state, success=True)

            self.metrics_collector.record_agent_metrics(
                "agent8",
                {
                    "success": True,
                    "execution_time": execution_time,
                    "documentation_files": docs_count,
                    "corrections_applied": corrections_count,
                },
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            workflow_logger.error(f"Agent-8 falhou após {execution_time:.2f}s: {str(e)}")

            await self._cleanup_agent_execution(agent_id, state, success=False, error=str(e))

            if state.job_id:
                await JobRepository.update_job_failure_info(
                    job_id=state.job_id,
                    failed_step_id=state.current_step_id,
                    failed_agent_id=agent_id,
                )

            state.last_operation = {
                "success": False,
                "agent": "agent8",
                "error": str(e),
                "timestamp": datetime.utcnow(),
            }
            state.failure_count += 1

            self.metrics_collector.record_agent_metrics(
                "agent8",
                {
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time,
                },
            )

        return state

    async def fallback_agent_node(self, state: ProjectState) -> ProjectState:
        """Nó de fallback genérico usando FallbackHandler"""
        failing_agent = state.last_operation.get("agent", "unknown")

        # Detecta loops: verifica se o mesmo agente falhou muitas vezes
        max_retry_attempts = self.config.get("orchestrator", {}).get("max_retry_attempts", 3)
        if state.recovery_attempts >= max_retry_attempts:
            logger.error(
                f"Loop detectado! Agente {failing_agent} falhou após {state.recovery_attempts} tentativas. "
                f"Parando workflow para evitar loop infinito."
            )
            state.last_operation = {
                "success": False,
                "agent": f"fallback_{failing_agent}",
                "error": f"Loop infinito detectado: agente {failing_agent} falhou {state.recovery_attempts} vezes",
                "timestamp": datetime.utcnow(),
            }
            return state

        return await self.fallback_handler.apply_fallback(state, failing_agent)

    async def fallback_agent1_node(self, state: ProjectState) -> ProjectState:
        """Fallback específico para Agent-1"""
        state.task_specification = {
            "task_id": "fallback_spec",
            "description": state.last_operation.get("user_input", ""),
            "acceptance_criteria": ["Funcionalidade básica operacional"],
            "estimated_complexity": 5,
            "technical_constraints": [],
            "fallback_used": True,
        }

        state.last_operation = {
            "success": True,
            "agent": "fallback_agent1",
            "result": {"status": "fallback_applied"},
            "timestamp": datetime.utcnow(),
        }
        state.recovery_attempts += 1

        # Atualiza contexto compartilhado
        await self.shared_context.update_decision(
            "fallback_agent1",
            "technical",
            "initial_spec",
            state.task_specification,
            0.5,
        )

        return state

    async def _fallback_agent2(self, state: ProjectState) -> ProjectState:
        """Fallback genérico para User Stories"""
        state.user_stories = {
            "user_stories": [
                {
                    "id": "US-FALLBACK-1",
                    "description": "Como usuário, eu quero uma funcionalidade básica que funcione",
                    "acceptance_criteria": ["O sistema deve responder a requisições básicas"],
                    "priority": "high",
                    "definition_of_done": ["Código implementado e testado"],
                    "estimated_story_points": 3,
                }
            ],
            "product_backlog": ["US-FALLBACK-1"],
            "release_planning": {
                "mvp_scope": ["US-FALLBACK-1"],
                "future_enhancements": [],
            },
        }

        state.last_operation = {
            "success": True,
            "agent": "fallback_agent2",
            "result": {"status": "fallback_applied"},
            "timestamp": datetime.utcnow(),
        }
        state.recovery_attempts += 1

        await self.shared_context.update_decision(
            "fallback_agent2", "technical", "user_stories", state.user_stories, 0.5
        )

        return state

    async def _fallback_agent3(self, state: ProjectState) -> ProjectState:
        """Fallback para arquitetura simples"""
        state.architecture = {
            "architecture_decision": {
                "pattern": "monolithic",
                "rationale": "Fallback para arquitetura monolítica simples devido a falha na análise",
                "alternatives_considered": ["microservices", "serverless"],
            },
            "components": [
                {
                    "name": "main_app",
                    "responsibility": "Aplicação principal",
                    "technology": "Python/FastAPI",
                    "dependencies": [],
                }
            ],
            "technology_stack": {
                "frontend": ["HTML", "CSS", "JavaScript"],
                "backend": ["Python", "FastAPI"],
                "database": ["SQLite"],
                "infrastructure": ["Docker"],
            },
        }

        state.last_operation = {
            "success": True,
            "agent": "fallback_agent3",
            "result": {"status": "fallback_applied"},
            "timestamp": datetime.utcnow(),
        }
        state.recovery_attempts += 1

        await self.shared_context.update_decision(
            "fallback_agent3",
            "architecture",
            "main_architecture",
            state.architecture,
            0.5,
        )

        return state

    async def _fallback_agent4(self, state: ProjectState) -> ProjectState:
        """Fallback para tarefas técnicas simples"""
        state.technical_tasks = {
            "technical_tasks": [
                {
                    "task_id": "TECH-FALLBACK-1",
                    "description": "Implementar funcionalidade básica",
                    "type": "backend",
                    "complexity": "medium",
                    "estimated_hours": 8,
                    "dependencies": [],
                    "acceptance_criteria": ["Sistema funcional básico"],
                    "technology_specifics": {
                        "libraries": ["fastapi", "uvicorn"],
                        "frameworks": [],
                        "tools": [],
                    },
                    "quality_requirements": {
                        "test_coverage": 0.5,
                        "performance_targets": [],
                        "security_requirements": [],
                    },
                    "risk_assessment": {
                        "level": "low",
                        "mitigation_strategy": "Fallback simples",
                    },
                }
            ]
        }

        state.last_operation = {
            "success": True,
            "agent": "fallback_agent4",
            "result": {"status": "fallback_applied"},
            "timestamp": datetime.utcnow(),
        }
        state.recovery_attempts += 1

        await self.shared_context.update_decision(
            "fallback_agent4",
            "technical",
            "technical_tasks",
            state.technical_tasks,
            0.5,
        )

        return state

    async def _fallback_agent5(self, state: ProjectState) -> ProjectState:
        """Fallback para estrutura de projeto mínima"""
        state.project_structure = {
            "project_structure": [
                {
                    "type": "directory",
                    "path": "src/",
                    "name": "",
                    "content": None,
                    "template_type": "python_package",
                    "permissions": "755",
                    "description": "Source code directory",
                },
                {
                    "type": "file",
                    "path": "src/main.py",
                    "name": "main.py",
                    "content": '# Basic application structure\nprint("Hello World")',
                    "template_type": "python_script",
                    "permissions": "644",
                    "description": "Main application file",
                },
                {
                    "type": "file",
                    "path": "requirements.txt",
                    "name": "requirements.txt",
                    "content": "fastapi\nuvicorn",
                    "template_type": "config_file",
                    "permissions": "644",
                    "description": "Python dependencies",
                },
            ]
        }

        state.last_operation = {
            "success": True,
            "agent": "fallback_agent5",
            "result": {"status": "fallback_applied"},
            "timestamp": datetime.utcnow(),
        }
        state.recovery_attempts += 1

        await self.shared_context.update_decision(
            "fallback_agent5",
            "technical",
            "project_structure",
            state.project_structure,
            0.5,
        )

        return state

    async def _fallback_agent6(self, state: ProjectState) -> ProjectState:
        """Fallback para implementação de código mínima"""
        state.implemented_code = {
            "FALLBACK-1": {
                "task_id": "FALLBACK-1",
                "files_created_modified": [
                    {
                        "file_path": "src/app.py",
                        "content": (
                            "from fastapi import FastAPI\n\napp = FastAPI()\n\n"
                            '@app.get("/")\ndef read_root():\n    return {"Hello": "World"}'
                        ),
                        "action": "create",
                        "description": "Basic FastAPI application",
                    }
                ],
                "dependencies_added": ["fastapi", "uvicorn"],
                "tests_suggested": [],
                "implementation_notes": "Fallback implementation with basic functionality",
                "quality_metrics": {
                    "complexity": "low",
                    "maintainability": "medium",
                    "security_considerations": ["Basic implementation - needs security review"],
                },
            }
        }

        state.last_operation = {
            "success": True,
            "agent": "fallback_agent6",
            "result": {"status": "fallback_applied"},
            "timestamp": datetime.utcnow(),
        }
        state.recovery_attempts += 1

        await self.shared_context.update_decision(
            "fallback_agent6",
            "technical",
            "implemented_code",
            state.implemented_code,
            0.5,
        )

        return state

    async def _fallback_agent7(self, state: ProjectState) -> ProjectState:
        """Fallback para revisão de código simplificada"""
        state.code_review = {
            "FALLBACK-1": {
                "task_id": "FALLBACK-1",
                "overall_score": 0.7,
                "approved": True,
                "issues_found": [
                    {
                        "type": "maintainability",
                        "severity": "low",
                        "file": "src/app.py",
                        "line": 1,
                        "description": "Implementação mínima - necessita expansão",
                        "suggestion": "Expandir funcionalidade conforme requisitos originais",
                        "priority": "could_fix",
                    }
                ],
                "suggested_improvements": [
                    {
                        "type": "enhance",
                        "description": "Adicionar testes unitários",
                        "benefit": "Melhor cobertura de testes",
                        "effort": "medium",
                    }
                ],
                "positive_feedback": ["Estrutura básica correta"],
                "test_recommendations": [{"test_type": "unit", "scope": "Endpoint /", "priority": "high"}],
                "security_assessment": {
                    "vulnerabilities_found": [],
                    "data_handling": "needs_improvement",
                    "authentication_authorization": "insufficient",
                },
                "performance_assessment": {
                    "efficiency": "moderate",
                    "bottlenecks_identified": [],
                    "optimization_suggestions": [],
                },
            }
        }

        state.last_operation = {
            "success": True,
            "agent": "fallback_agent7",
            "result": {"status": "fallback_applied"},
            "timestamp": datetime.utcnow(),
        }
        state.recovery_attempts += 1

        await self.shared_context.update_decision("fallback_agent7", "quality", "code_review", state.code_review, 0.5)

        return state

    async def _fallback_agent8(self, state: ProjectState) -> ProjectState:
        """Fallback para entrega final simplificada"""
        state.final_delivery = {
            "delivery_timestamp": datetime.utcnow().isoformat(),
            "project_summary": {
                "total_tasks": 1,
                "corrections_applied": 0,
                "documentation_files": 1,
                "project_structure": 2,
            },
            "quality_metrics": {
                "approval_rate": 100,
                "average_score": 0.7,
                "total_issues": 1,
                "critical_issues": 0,
                "quality_grade": "B",
            },
            "next_steps_recommendations": [
                "Expandir funcionalidade básica para atender requisitos originais",
                "Adicionar sistema de autenticação",
                "Implementar persistência de dados",
                "Adicionar testes unitários e de integração",
            ],
            "maintenance_considerations": [
                "Monitorar uso em produção",
                "Planejar expansão gradual das funcionalidades",
            ],
        }

        state.last_operation = {
            "success": True,
            "agent": "fallback_agent8",
            "result": {"status": "fallback_applied"},
            "timestamp": datetime.utcnow(),
        }
        state.recovery_attempts += 1

        await self.shared_context.update_decision(
            "fallback_agent8", "quality", "final_delivery", state.final_delivery, 0.5
        )
        await self.shared_context.update_decision(
            "fallback_agent8",
            "project",
            "completion_status",
            {"status": "completed_with_fallback", "timestamp": datetime.utcnow()},
            0.5,
        )

        return state

    async def _fallback_generic(self, state: ProjectState) -> ProjectState:
        """Fallback genérico para agentes não especificados"""
        state.last_operation = {
            "success": True,
            "agent": "fallback_generic",
            "result": {"status": "generic_fallback_applied"},
            "timestamp": datetime.utcnow(),
        }
        state.recovery_attempts += 1
        return state

    async def rollback_state_node(self, state: ProjectState) -> ProjectState:
        """Executa rollback de estado"""
        logger.warning("Executando rollback de estado")

        # Detecta loops: se recovery_attempts for muito alto, pode indicar loop
        max_recovery_attempts = self.config.get("orchestrator", {}).get("max_retry_attempts", 3)
        if state.recovery_attempts >= max_recovery_attempts:
            logger.error(
                f"Loop detectado! Número de tentativas de recuperação ({state.recovery_attempts}) "
                f"excedeu o limite ({max_recovery_attempts}). Parando workflow."
            )
            state.last_operation = {
                "success": False,
                "agent": "rollback",
                "error": f"Loop infinito detectado após {state.recovery_attempts} tentativas de recuperação",
                "timestamp": datetime.utcnow(),
            }
            return state

        # Reverte para o último estado bom conhecido
        state.failure_count = 0
        state.recovery_attempts += 1

        # Limpa o último resultado problemático
        failing_agent = state.last_operation.get("agent", "")
        if failing_agent == "agent1":
            state.task_specification = None
        elif failing_agent == "agent2":
            state.user_stories = None
        elif failing_agent == "agent3":
            state.architecture = None
        elif failing_agent == "agent4":
            state.technical_tasks = None
        elif failing_agent == "agent5":
            state.project_structure = None
        elif failing_agent == "agent6":
            state.implemented_code = None
        elif failing_agent == "agent7":
            state.code_review = None

        state.last_operation = {
            "success": True,
            "agent": "rollback",
            "result": {"status": "state_rolled_back"},
            "timestamp": datetime.utcnow(),
        }

        return state

    async def human_supervisor_node(self, state: ProjectState) -> ProjectState:
        """Solicita intervenção humana"""
        logger.error("Solicitando intervenção humana")

        # Em uma implementação real, isso enviaria uma notificação
        # para a interface de supervisão

        error_details = state.last_operation.get("error", "Erro não especificado")
        failing_agent = state.last_operation.get("agent", "unknown")

        # Registra alerta no sistema de monitoramento
        self.metrics_collector.record_alert(
            "human_intervention_required",
            {
                "agent": failing_agent,
                "error": error_details,
                "failure_count": state.failure_count,
                "recovery_attempts": state.recovery_attempts,
                "current_phase": state.current_phase,
            },
        )

        state.last_operation = {
            "success": False,
            "agent": "human_supervisor",
            "error": f"Intervenção humana requerida após {state.failure_count} falhas",
            "details": error_details,
            "timestamp": datetime.utcnow(),
        }

        return state

    async def execute_workflow(
        self,
        user_input: str,
        project_path: str | None = None,
        job_id: str | None = None,
        repository_url: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, any]:
        """Executa o fluxo completo do DEVs AI"""
        workflow_logger.info("=== Iniciando execução do workflow DEVs AI ===")
        workflow_logger.info(f"Input do usuário: {user_input[:200] if len(user_input) > 200 else user_input}")
        workflow_logger.info(f"Caminho do projeto: {project_path or 'N/A'}")

        from uuid import UUID

        job_uuid = UUID(job_id) if job_id else None

        if project_path:
            self.shared_context.project_state.set("project_path", project_path)

        initial_state = ProjectState(
            last_operation={"user_input": user_input, "success": True},
            project_path=project_path,
            job_id=job_uuid,
            repository_url=repository_url,
            access_token=access_token,
            code_review_count=0,
            timestamp=datetime.utcnow(),
        )

        recursion_limit = self.config.get("orchestrator", {}).get("recursion_limit", 15)

        try:
            config = {"recursion_limit": recursion_limit}

            if recursion_limit <= 20:
                workflow_logger.warning(f"Limite de recursão baixo: {recursion_limit}")

            workflow_logger.info("Executando workflow...")
            final_state = await self.workflow.ainvoke(initial_state, config=config)

            execution_time = (datetime.utcnow() - initial_state.timestamp).total_seconds()
            phases_completed = self._get_completed_phases(final_state)

            workflow_logger.info(f"=== Workflow concluído em {execution_time:.2f}s ===")
            workflow_logger.info(f"Fases completadas: {', '.join(phases_completed)}")
            workflow_logger.info(f"Status final: {final_state.current_phase}")

            return {
                "success": True,
                "execution_time": execution_time,
                "phases_completed": phases_completed,
                "final_state": final_state.dict(),
                "project_status": final_state.current_phase,
            }

        except Exception as e:
            execution_time = (datetime.utcnow() - initial_state.timestamp).total_seconds()
            workflow_logger.error(f"=== Erro no workflow após {execution_time:.2f}s ===")
            workflow_logger.error(f"Erro: {str(e)}", exc_info=True)

            # Coleta métricas de falha
            self.metrics_collector.record_system_error(str(e))

            # Gera sugestões de recuperação
            recovery_suggestions = self._generate_recovery_suggestions(e)

            return {
                "success": False,
                "error": str(e),
                "execution_time": (datetime.utcnow() - initial_state.timestamp).total_seconds(),
                "recovery_suggestions": recovery_suggestions,
                "failed_phase": initial_state.current_phase,
            }

    def _get_completed_phases(self, state: ProjectState) -> list[str]:
        """Identifica quais fases foram completadas com sucesso"""
        phases = []
        if state.task_specification:
            phases.append("requirements_analysis")
        if state.user_stories:
            phases.append("user_stories_creation")
        if state.architecture:
            phases.append("architecture_design")
        if state.technical_tasks:
            phases.append("technical_planning")
        if state.project_structure:
            phases.append("project_scaffolding")
        if state.implemented_code:
            phases.append("code_implementation")
        if state.code_review:
            phases.append("code_review")
        if state.final_delivery:
            phases.append("final_delivery")
        return phases

    def _generate_recovery_suggestions(self, error: Exception) -> list[str]:
        """Gera sugestões para recuperação de falhas"""
        error_str = str(error).lower()
        suggestions = []

        # Sugestões baseadas no tipo de erro
        if "connection" in error_str or "network" in error_str:
            suggestions.extend(
                [
                    "Verificar conectividade com serviços (Redis, ChromaDB, Ollama)",
                    "Validar configurações de rede e firewalls",
                    "Testar serviços manualmente antes de reiniciar o sistema",
                ]
            )
        elif "memory" in error_str or "ram" in error_str or "oom" in error_str:
            suggestions.extend(
                [
                    "Reduzir tamanho do contexto para LLM",
                    "Aumentar limite de memória ou usar máquina com mais RAM",
                    "Processar tarefas menores e em lotes",
                ]
            )
        elif "timeout" in error_str:
            suggestions.extend(
                [
                    "Aumentar timeout de configuração",
                    "Reduzir complexidade da tarefa solicitada",
                    "Verificar carga do sistema e serviços dependentes",
                ]
            )
        elif "validation" in error_str or "json" in error_str:
            suggestions.extend(
                [
                    "Simplificar solicitação do usuário",
                    "Fornecer mais contexto ou exemplos",
                    "Dividir tarefa complexa em subtarefas menores",
                ]
            )
        elif "permission" in error_str or "access" in error_str:
            suggestions.extend(
                [
                    "Verificar permissões de sistema de arquivos",
                    "Rodar sistema com privilégios adequados",
                    "Verificar capability tokens e configurações de segurança",
                ]
            )

        # Sugestões genéricas se nenhuma específica foi adicionada
        if not suggestions:
            suggestions.extend(
                [
                    "Verificar logs detalhados para diagnóstico",
                    "Tentar novamente com uma descrição mais simples do projeto",
                    "Dividir o projeto em partes menores e processar separadamente",
                ]
            )

        return suggestions
