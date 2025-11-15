import json
import logging

from agents.base_agent import BaseAgent
from utils.markdown_parser import extract_structured_data_from_markdown

logger = logging.getLogger("devs-ai")


class Agent3_Arquiteto(BaseAgent):
    """Agent-3: Arquiteto - Define arquitetura do sistema"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:  # noqa: C901
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

Formato Markdown:

## Architecture Decision
**Pattern:** [padrão arquitetural]
**Rationale:** [justificativa]
**Alternatives Considered:**
- [alternativa 1]
- [alternativa 2]

## Components

### [Nome do Componente]
**Responsibility:** [responsabilidade]
**Technology:** [tecnologia]
**Dependencies:**
- [dependência 1]
- [dependência 2]

## Technology Stack
**Frontend:**
- [tecnologia 1]
- [tecnologia 2]

**Backend:**
- [tecnologia 1]
- [tecnologia 2]

**Database:**
- [tecnologia 1]

**Infrastructure:**
- [tecnologia 1]

## Communication Protocols
- [protocolo 1]
- [protocolo 2]

## Quality Attributes
**Scalability:** [descrição]
**Security:** [descrição]
**Maintainability:** [descrição]

## PlantUML Diagram
```
[código do diagrama PlantUML aqui]
```
"""

        # Obtém temperatura do config para este agente
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent3", {}).get("temperature", 0.2)

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            architecture = extract_structured_data_from_markdown(response, model_name=self.agent_id)

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

            # Lê arquivo do agente anterior
            previous_content = self._read_previous_agent_md(3)

            # Gera nova seção de arquitetura
            new_section = "# ARQUITETURA DO SISTEMA\n\n"
            arch_decision = architecture.get("architecture_decision", {})
            new_section += "## ARQUITETURA DEFINIDA\n\n"
            new_section += "### Diagrama de Componentes\n\n"
            plantuml = architecture.get("plantuml_diagram", "")
            if plantuml:
                new_section += f"```\n{plantuml}\n```\n\n"
            else:
                new_section += "*Diagrama não disponível*\n\n"
            new_section += "### Tecnologias e Frameworks\n\n"
            tech_stack = architecture.get("technology_stack", {})
            for category, techs in tech_stack.items():
                category_name = category.replace("_", " ").title()
                new_section += f"- **{category_name}:** {', '.join(techs) if techs else 'N/A'}\n"
            new_section += "\n### Padrões Arquiteturais\n\n"
            pattern = arch_decision.get("pattern", "N/A")
            rationale = arch_decision.get("rationale", "N/A")
            new_section += f"- **{pattern}** - {rationale}\n"
            if arch_decision.get("alternatives_considered"):
                new_section += "\n**Alternativas Consideradas:**\n"
                for alt in arch_decision.get("alternatives_considered", []):
                    new_section += f"- {alt}\n"
            new_section += "\n### Componentes\n\n"
            for component in architecture.get("components", []):
                new_section += f"#### {component.get('name', 'N/A')}\n\n"
                new_section += f"**Responsabilidade:** {component.get('responsibility', 'N/A')}\n\n"
                new_section += f"**Tecnologia:** {component.get('technology', 'N/A')}\n\n"
                if component.get("dependencies"):
                    new_section += "**Dependências:**\n"
                    for dep in component.get("dependencies", []):
                        new_section += f"- {dep}\n"
                new_section += "\n"
            if architecture.get("communication_protocols"):
                new_section += "### Protocolos de Comunicação\n\n"
                for protocol in architecture.get("communication_protocols", []):
                    new_section += f"- {protocol}\n"
                new_section += "\n"
            if architecture.get("quality_attributes"):
                quality_attrs = architecture.get("quality_attributes", {})
                new_section += "### Atributos de Qualidade\n\n"
                for attr, value in quality_attrs.items():
                    new_section += f"- **{attr.replace('_', ' ').title()}:** {value}\n"
                new_section += "\n"

            md_content = self._build_accumulative_md(
                previous_content, new_section, "ARQUITETURA DO SISTEMA", 3, "Agent 2"
            )
            await self._save_markdown_file("agent3_arquitetura.md", md_content)

            return {"status": "success", "architecture": architecture}
        except Exception as e:
            logger.error(f"Erro no parsing da resposta do Arquiteto: {str(e)}")
            raise
