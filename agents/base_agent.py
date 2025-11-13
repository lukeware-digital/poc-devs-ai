import logging
from datetime import datetime
from typing import any

logger = logging.getLogger("DEVs_AI")


class BaseAgent:
    """
    Classe base para todos os agentes do sistema DEVs AI.
    Fornece funcionalidades comuns como execução de tarefas, métricas e tratamento de erros.
    """

    def __init__(
        self,
        agent_id: str,
        llm_layer: any,
        shared_context: any,
        rag_retriever: any,
        guardrails: any,
    ):
        self.agent_id = agent_id
        self.llm = llm_layer
        self.shared_context = shared_context
        self.rag = rag_retriever
        self.guardrails = guardrails
        self.metrics = {
            "success_count": 0,
            "failure_count": 0,
            "total_response_time": 0.0,
            "last_execution": None,
        }

    async def execute(self, task: dict[str, any]) -> dict[str, any]:
        """
        Executa uma tarefa com o agente, incluindo verificação de permissões e tratamento de erros.
        """
        start_time = datetime.utcnow()
        try:
            # Verifica permissões
            operation = task.get("operation", "default")
            allowed, reason = await self.guardrails.check_permission(self.agent_id, operation, task.get("context", {}))
            if not allowed:
                raise PermissionError(f"Operação não permitida: {reason}")

            # Executa a tarefa específica do agente
            result = await self._execute_task(task)

            # Atualiza métricas
            self.metrics["success_count"] += 1
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics["total_response_time"] += execution_time
            self.metrics["last_execution"] = datetime.utcnow()
            logger.info(f"Agente {self.agent_id} executado com sucesso em {execution_time:.2f}s")
            return result

        except Exception as e:
            self.metrics["failure_count"] += 1
            logger.error(f"Erro no agente {self.agent_id}: {str(e)}")
            raise

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
        """
        Método abstrato para ser implementado por cada agente específico.
        """
        raise NotImplementedError("Método deve ser implementado pela subclasse") from e

    def get_metrics(self) -> dict[str, any]:
        """
        Retorna métricas de performance do agente.
        """
        total_operations = self.metrics["success_count"] + self.metrics["failure_count"]
        success_rate = (self.metrics["success_count"] / total_operations * 100) if total_operations > 0 else 0
        avg_response_time = (
            (self.metrics["total_response_time"] / self.metrics["success_count"])
            if self.metrics["success_count"] > 0
            else 0
        )

        return {
            "agent_id": self.agent_id,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "total_operations": total_operations,
            "last_execution": self.metrics["last_execution"],
        }
