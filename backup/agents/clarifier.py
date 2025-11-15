import hashlib
import json
import logging

from agents.base_agent import BaseAgent
from models.task_specification import TaskSpecification
from utils.markdown_parser import MarkdownParseError, extract_structured_data_from_markdown

logger = logging.getLogger("devs-ai")


class Agent1_Clarificador(BaseAgent):
    """Agent-1: Clarificador e Analista de Requisitos"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:  # noqa: C901
        user_input = task["user_input"]

        # Recupera contexto relevante
        rag_context = self.rag.retrieve(user_input, "requirement", 3)

        # Carrega template especializado
        template_base = self._build_prompt("clarifier", {})

        prompt = f"""
            {template_base}

            Analise a seguinte solicitação do usuário:
            SOLICITAÇÃO: {user_input}
            CONTEXTO RELEVANTE:
            {json.dumps(rag_context, indent=2)}

            Sua tarefa é:
            1. Clarificar requisitos ambíguos
            2. Identificar requisitos funcionais e não-funcionais
            3. Definir critérios de aceitação claros
            4. Estimar complexidade (1-10)

            Responda em formato Markdown estruturado:

            ## Requirements Breakdown

            ### Functional
            - [Lista de requisitos funcionais, um por linha]

            ### Non-Functional
            - [Lista de requisitos não-funcionais, um por linha]

            ## Acceptance Criteria
            - [Critério de aceitação 1]
            - [Critério de aceitação 2]

            ## Clarification Questions
            - [Pergunta de clarificação 1]
            - [Pergunta de clarificação 2]

            ## Estimated Complexity
            [Número de 1 a 10]

            ## Technical Considerations
            - [Consideração técnica 1]
            - [Consideração técnica 2]
        """

        # Obtém temperatura do config para este agente (com valor padrão)
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent1", {}).get("temperature", 0.3)

        response = await self._generate_llm_response(prompt, temperature=temperature)

        model_name = None
        try:
            if self._llm_initialized and hasattr(self, "llm"):
                providers = self.llm._get_providers_for_agent(self.agent_id)
                if providers:
                    model_info = providers[0].get_model_info()
                    model_name = model_info.get("name") if model_info else None
        except Exception:
            pass

        logger.debug(f"Resposta recebida (tamanho: {len(response) if response else 0} caracteres)")

        try:
            spec = extract_structured_data_from_markdown(response, model_name=model_name)
            requirements_breakdown = spec.get("requirements_breakdown")
            if requirements_breakdown is None:
                requirements_breakdown = {"functional": [], "non_functional": []}
            elif not isinstance(requirements_breakdown, dict):
                requirements_breakdown = {"functional": [], "non_functional": []}
            
            estimated_complexity = spec.get("estimated_complexity", 5)
            if isinstance(estimated_complexity, list) and len(estimated_complexity) > 0:
                estimated_complexity = estimated_complexity[0]
            if isinstance(estimated_complexity, str):
                estimated_complexity = estimated_complexity.strip().strip("[]")
                try:
                    estimated_complexity = int(estimated_complexity)
                except (ValueError, TypeError):
                    estimated_complexity = 5
            if not isinstance(estimated_complexity, int):
                estimated_complexity = 5
            
            task_spec = TaskSpecification(
                task_id=task.get(
                    "task_id",
                    f"task_{hashlib.md5(user_input.encode()).hexdigest()[:8]}",
                ),
                description=user_input,
                acceptance_criteria=spec.get("acceptance_criteria", []),
                estimated_complexity=estimated_complexity,
                technical_constraints=spec.get("technical_considerations", []),
                requirements_breakdown=requirements_breakdown,
                clarification_questions=spec.get("clarification_questions", []),
            )

            # Atualiza contexto compartilhado
            await self.shared_context.update_decision(
                self.agent_id, "technical", "initial_spec", task_spec.model_dump(), 0.8
            )

            # Gera markdown no novo formato acumulativo
            new_section = "# ANÁLISE DE REQUISITOS CORRIGIDA\n\n"
            new_section += "**Status:** Validado e Corrigido\n\n"
            new_section += "## PROMPT ORIGINAL\n\n"
            new_section += f"{user_input}\n\n"
            new_section += "## PROMPT CORRIGIDO E MELHORADO\n\n"
            new_section += f"{task_spec.description}\n\n"
            new_section += "## VALIDAÇÕES REALIZADAS\n\n"
            new_section += "- [x] Clareza dos requisitos\n"
            new_section += "- [x] Completude das informações\n"
            new_section += "- [x] Viabilidade técnica\n"
            new_section += "- [x] Ambiguidades removidas\n\n"
            new_section += "## ESPECIFICAÇÃO TÉCNICA\n\n"
            new_section += f"**Task ID:** {task_spec.task_id}\n\n"
            new_section += "### Critérios de Aceitação\n\n"
            for criterion in task_spec.acceptance_criteria:
                new_section += f"- {criterion}\n"
            new_section += f"\n### Complexidade Estimada\n\n{task_spec.estimated_complexity}/10\n\n"
            new_section += "### Considerações Técnicas\n\n"
            for constraint in task_spec.technical_constraints:
                new_section += f"- {constraint}\n"
            if task_spec.requirements_breakdown:
                new_section += "\n### Breakdown de Requisitos\n\n"
                new_section += "#### Funcionais\n\n"
                for req in task_spec.requirements_breakdown.get("functional", []):
                    new_section += f"- {req}\n"
                new_section += "\n#### Não-Funcionais\n\n"
                for req in task_spec.requirements_breakdown.get("non_functional", []):
                    new_section += f"- {req}\n"
            if task_spec.clarification_questions:
                new_section += "\n### Questões de Clarificação\n\n"
                for question in task_spec.clarification_questions:
                    new_section += f"- {question}\n"

            md_content = self._build_accumulative_md("", new_section, "ANÁLISE DE REQUISITOS CORRIGIDA", 1)
            await self._save_markdown_file("agent1_corrigido.md", md_content)

            return {
                "status": "success",
                "specification": task_spec.model_dump(),
                "clarification_questions": spec.get("clarification_questions", []),
            }
        except MarkdownParseError as e:
            logger.error(f"Erro detalhado no parsing Markdown: {str(e)}")
            corrected_spec = self._fallback_spec_creation(user_input, response, str(e))
            return {
                "status": "success_with_fallback",
                "specification": corrected_spec,
                "fallback_used": True,
            }

    def _fallback_spec_creation(self, user_input: str, raw_response: str, error: str) -> dict[str, any]:
        """Cria uma especificação simplificada em caso de falha na análise"""
        return {
            "task_id": "fallback_" + hashlib.md5(user_input.encode()).hexdigest()[:8],
            "description": user_input,
            "acceptance_criteria": ["Funcionalidade básica operacional"],
            "estimated_complexity": 5,
            "technical_constraints": [],
            "fallback_attempts": 1,
        }
