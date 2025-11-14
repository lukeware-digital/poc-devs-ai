import logging
import traceback
from datetime import datetime

from config.logging_config import AgentAdapter

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
        self._prompt_loader = None
        self._logger = AgentAdapter(logger, {"agent_id": agent_id})

    async def execute(self, task: dict[str, any]) -> dict[str, any]:
        """
        Executa uma tarefa com o agente, incluindo verificação de permissões e tratamento de erros.
        """
        start_time = datetime.utcnow()
        operation = task.get("operation", "default")

        self._logger.info(f"Iniciando tarefa: {operation}")
        self._logger.debug(f"Detalhes da tarefa: {self._sanitize_task_for_log(task)}")

        try:
            self._logger.debug("Verificando permissões...")
            allowed, reason = await self.guardrails.check_permission(self.agent_id, operation, task.get("context", {}))
            if not allowed:
                self._logger.error(f"Permissão negada: {reason}")
                raise PermissionError(f"Operação não permitida: {reason}")

            self._logger.info("Permissão concedida, executando tarefa...")

            result = await self._execute_task(task)

            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics["success_count"] += 1
            self.metrics["total_response_time"] += execution_time
            self.metrics["last_execution"] = datetime.utcnow()

            self._logger.info(f"Tarefa concluída com sucesso em {execution_time:.2f}s")
            self._logger.debug(f"Resultado: {self._sanitize_result_for_log(result)}")

            return result

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics["failure_count"] += 1

            error_trace = traceback.format_exc()
            self._logger.error(f"Erro na execução da tarefa após {execution_time:.2f}s: {str(e)}")
            self._logger.debug(f"Stack trace: {error_trace}")

            raise

    def _sanitize_task_for_log(self, task: dict[str, any]) -> dict[str, any]:
        sanitized = task.copy()
        if "user_input" in sanitized and len(str(sanitized["user_input"])) > 200:
            sanitized["user_input"] = str(sanitized["user_input"])[:200] + "..."
        return sanitized

    def _sanitize_result_for_log(self, result: dict[str, any]) -> dict[str, any]:
        sanitized = result.copy()
        for key, value in sanitized.items():
            if isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "..."
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_result_for_log(value)
        return sanitized

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
        """
        Método abstrato para ser implementado por cada agente específico.
        """
        raise NotImplementedError("Método deve ser implementado pela subclasse")

    async def _generate_llm_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop_sequences: list[str] = None,
    ) -> str:
        """
        Helper method para gerar resposta LLM com agent_id automaticamente.
        """
        return await self.llm.generate_response(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            agent_id=self.agent_id,
        )

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

    def _get_language_config(self) -> dict:
        """
        Obtém a configuração de especialização de linguagem.
        """
        config = getattr(self.shared_context, "config", {})
        return config.get("language_specialization", {})

    def _get_prompt_loader(self):
        """
        Obtém ou cria o carregador de prompts.
        """
        if self._prompt_loader is None:
            from utils.prompt_loader import PromptLoader

            config = getattr(self.shared_context, "config", {})
            self._prompt_loader = PromptLoader(config)
        return self._prompt_loader

    def _build_prompt(self, template_name: str, context: dict) -> str:
        """
        Constrói um prompt usando templates parametrizados.

        Args:
            template_name: Nome da seção do template (ex: 'developer', 'architect')
            context: Dicionário com valores adicionais para substituição no template

        Returns:
            Prompt formatado com placeholders substituídos
        """
        prompt_loader = self._get_prompt_loader()
        return prompt_loader.build_prompt(template_name, context)
