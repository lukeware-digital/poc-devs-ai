import json
import logging

from agents.base_agent import BaseAgent
from utils.json_parser import extract_json_from_response

logger = logging.getLogger("devs-ai")


class Agent3_Arquiteto(BaseAgent):
    """Agent-3: Arquiteto - Define arquitetura do sistema"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
        spec = task["specification"]
        user_stories = task["user_stories"]

        # Recupera padrões arquiteturais relevantes
        arch_context = self.rag.retrieve(spec["description"], "architecture", 5)

        # Carrega template especializado
        template_base = self._build_prompt("architect", {})

        prompt = f"""
{template_base}

Defina a arquitetura para:
ESPECIFICAÇÃO: {json.dumps(spec, indent=2)}
HISTÓRIAS: {json.dumps(user_stories, indent=2)}
CONTEXTO ARQUITETURAL:
{json.dumps(arch_context, indent=2)}

Defina:
1. Padrão arquitetural principal (microservices, monolith, serverless, etc.)
2. Componentes principais e suas responsabilidades
3. Tecnologias recomendadas (frontend, backend, database, etc.)
4. Protocolos de comunicação entre componentes
5. Considerações de escalabilidade, segurança e manutenção
6. Diagrama de componentes em texto (para PlantUML)

Formato JSON:
{{
    "architecture_decision": {{
        "pattern": "",
        "rationale": "",
        "alternatives_considered": []
    }},
    "components": [
        {{
            "name": "",
            "responsibility": "",
            "technology": "",
            "dependencies": []
        }}
    ],
    "technology_stack": {{
        "frontend": [],
        "backend": [],
        "database": [],
        "infrastructure": []
    }},
    "communication_protocols": [],
    "quality_attributes": {{
        "scalability": "",
        "security": "",
        "maintainability": ""
    }},
    "plantuml_diagram": ""
}}
"""

        # Obtém temperatura do config para este agente
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent3", {}).get("temperature", 0.2)

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            architecture = extract_json_from_response(response, model_name=self.agent_id)

            # Atualiza contexto compartilhado
            await self.shared_context.update_decision(
                self.agent_id, "architecture", "main_architecture", architecture, 0.85
            )
            await self.shared_context.update_decision(
                self.agent_id,
                "technical",
                "technology_stack",
                architecture.get("technology_stack", {}),
                0.9,
            )

            # Salva architecture.md
            md_content = "# Architecture\n\n"
            arch_decision = architecture.get("architecture_decision", {})
            md_content += "## Architecture Decision\n\n"
            md_content += f"**Pattern:** {arch_decision.get('pattern', 'N/A')}\n\n"
            md_content += f"**Rationale:** {arch_decision.get('rationale', 'N/A')}\n\n"
            md_content += "**Alternatives Considered:**\n"
            for alt in arch_decision.get("alternatives_considered", []):
                md_content += f"- {alt}\n"
            md_content += "\n## Components\n\n"
            for component in architecture.get("components", []):
                md_content += f"### {component.get('name', 'N/A')}\n\n"
                md_content += f"**Responsibility:** {component.get('responsibility', 'N/A')}\n\n"
                md_content += f"**Technology:** {component.get('technology', 'N/A')}\n\n"
            md_content += "\n## Technology Stack\n\n"
            tech_stack = architecture.get("technology_stack", {})
            for category, techs in tech_stack.items():
                md_content += f"### {category.title()}\n"
                for tech in techs:
                    md_content += f"- {tech}\n"
                md_content += "\n"
            await self._save_markdown_file("architecture.md", md_content)

            return {"status": "success", "architecture": architecture}
        except Exception as e:
            logger.error(f"Erro no parsing da resposta do Arquiteto: {str(e)}")
            raise
