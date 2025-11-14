import json
import logging

from agents.base_agent import BaseAgent

logger = logging.getLogger("DEVs_AI")


class Agent2_ProductManager(BaseAgent):
    """Agent-2: Product Manager - Gera histórias de usuário"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
        specification = task["specification"]

        # Carrega template especializado
        template_base = self._build_prompt("product_manager", {})

        prompt = f"""
{template_base}

Crie histórias de usuário baseado na especificação:
ESPECIFICAÇÃO: {json.dumps(specification, indent=2)}

Crie:
1. Histórias de usuário no formato "Como [persona], eu quero [ação] para [benefício]"
2. Critérios de aceitação para cada história
3. Priorização baseada no valor e complexidade
4. Definição de pronto para cada história

Formato de resposta JSON:
{{
    "user_stories": [
        {{
            "id": "US-1",
            "description": "Como usuário, eu quero...",
            "acceptance_criteria": [],
            "priority": "high|medium|low",
            "definition_of_done": [],
            "estimated_story_points": 0
        }}
    ],
    "product_backlog": [],
    "release_planning": {{
        "mvp_scope": [],
        "future_enhancements": []
    }}
}}
"""

        # Obtém temperatura do config para este agente
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent2", {}).get("temperature", 0.8)

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            user_stories = json.loads(response)

            # Atualiza contexto compartilhado
            await self.shared_context.update_decision(self.agent_id, "technical", "user_stories", user_stories, 0.9)

            # Salva user_stories.md
            md_content = "# User Stories\n\n"
            for story in user_stories.get("user_stories", []):
                md_content += f"## {story.get('id', 'N/A')}\n\n"
                md_content += f"**Description:** {story.get('description', 'N/A')}\n\n"
                md_content += f"**Priority:** {story.get('priority', 'N/A')}\n\n"
                md_content += f"**Story Points:** {story.get('estimated_story_points', 0)}\n\n"
                md_content += "**Acceptance Criteria:**\n"
                for criterion in story.get("acceptance_criteria", []):
                    md_content += f"- {criterion}\n"
                md_content += "\n**Definition of Done:**\n"
                for item in story.get("definition_of_done", []):
                    md_content += f"- {item}\n"
                md_content += "\n---\n\n"
            await self._save_markdown_file("user_stories.md", md_content)

            return {"status": "success", "user_stories": user_stories}
        except Exception as e:
            logger.error(f"Erro no parsing da resposta do Product Manager: {str(e)}")
            raise
