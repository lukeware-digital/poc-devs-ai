import hashlib
import json
import logging

from agents.base_agent import BaseAgent
from models.task_specification import TaskSpecification

logger = logging.getLogger("DEVs_AI")


class Agent1_Clarificador(BaseAgent):
    """Agent-1: Clarificador e Analista de Requisitos"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
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

Responda em formato JSON estruturado:
{{
    "requirements_breakdown": {{
        "functional": [],
        "non_functional": []
    }},
    "acceptance_criteria": [],
    "clarification_questions": [],
    "estimated_complexity": 0,
    "technical_considerations": []
}}
"""

        # Obtém temperatura do config para este agente (com valor padrão)
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent1", {}).get("temperature", 0.3)

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            spec = json.loads(response)
            task_spec = TaskSpecification(
                task_id=task.get(
                    "task_id",
                    f"task_{hashlib.md5(user_input.encode()).hexdigest()[:8]}",
                ),
                description=user_input,
                acceptance_criteria=spec.get("acceptance_criteria", []),
                estimated_complexity=spec.get("estimated_complexity", 5),
                technical_constraints=spec.get("technical_considerations", []),
                requirements_breakdown=spec.get("requirements_breakdown"),
                clarification_questions=spec.get("clarification_questions", []),
            )

            # Atualiza contexto compartilhado
            await self.shared_context.update_decision(
                self.agent_id, "technical", "initial_spec", task_spec.model_dump(), 0.8
            )

            # Salva specification.md
            md_content = (
                f"# Specification\n\n## Task ID\n{task_spec.task_id}\n\n"
                f"## Description\n{task_spec.description}\n\n## Acceptance Criteria\n"
            )
            for criterion in task_spec.acceptance_criteria:
                md_content += f"- {criterion}\n"
            md_content += f"\n## Estimated Complexity\n{task_spec.estimated_complexity}\n\n## Technical Constraints\n"
            for constraint in task_spec.technical_constraints:
                md_content += f"- {constraint}\n"
            if task_spec.requirements_breakdown:
                md_content += "\n## Requirements Breakdown\n\n### Functional\n"
                for req in task_spec.requirements_breakdown.get("functional", []):
                    md_content += f"- {req}\n"
                md_content += "\n### Non-Functional\n"
                for req in task_spec.requirements_breakdown.get("non_functional", []):
                    md_content += f"- {req}\n"
            await self._save_markdown_file("specification.md", md_content)

            return {
                "status": "success",
                "specification": task_spec.model_dump(),
                "clarification_questions": spec.get("clarification_questions", []),
            }
        except Exception as e:
            # Fallback para validação
            logger.warning(f"Falha no parsing da resposta. Erro: {str(e)}")
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
