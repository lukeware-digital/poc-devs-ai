import json
import logging

from agents.base_agent import BaseAgent
from utils.markdown_parser import extract_structured_data_from_markdown

logger = logging.getLogger("devs-ai")


class Agent4_TechLead(BaseAgent):
    """Agent-4: Tech Lead - Define tasks técnicas e stack detalhada"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:  # noqa: C901
        spec = task["specification"]
        architecture = task["architecture"]
        user_stories = task["user_stories"]

        # Analisa código existente do projeto
        project_path = self._get_project_path()
        project_analysis = {}
        if project_path:
            try:
                from services.project_analyzer import ProjectAnalyzer

                analyzer = ProjectAnalyzer()
                project_type = await analyzer.detect_project_type(project_path)
                code_exists = await analyzer.validate_code_exists(project_path)
                directories = await analyzer.analyze_directories(project_path)

                project_analysis = {
                    "project_type": project_type,
                    "code_exists": code_exists,
                    "directories": directories,
                }
                logger.info(f"Projeto analisado: tipo={project_type}, código_existe={code_exists}")
            except Exception as e:
                logger.warning(f"Erro ao analisar projeto: {str(e)}")

        # Carrega template especializado
        template_base = self._build_prompt("tech_lead", {})

        project_context = ""
        if project_analysis:
            project_context = f"""
ANÁLISE DO PROJETO EXISTENTE:
- Tipo de Projeto: {project_analysis.get("project_type", "unknown")}
- Código Existe: {project_analysis.get("code_exists", False)}
- Diretórios: {json.dumps(project_analysis.get("directories", []), indent=2)}

IMPORTANTE: Se o projeto já existe, analise a linguagem de programação detectada e defina a stack
tecnológica baseada nela. Se o projeto é novo, defina a stack baseada nos requisitos.
"""

        prompt = f"""
{template_base}

Crie tasks técnicas detalhadas baseado em:
ESPECIFICAÇÃO: {json.dumps(spec, indent=2)}
ARQUITETURA: {json.dumps(architecture, indent=2)}
HISTÓRIAS DE USUÁRIO: {json.dumps(user_stories, indent=2)}
{project_context}

Suas responsabilidades:
1. Decompor histórias em tasks técnicas implementáveis
2. Definir stack tecnológica específica (versões, bibliotecas)
3. Estimar esforço para cada task (horas/pontos)
4. Definir dependências entre tasks
5. Especificar critérios de qualidade para cada task
6. Identificar riscos técnicos e mitigações

Formato Markdown:

## Technical Tasks

### TECH-1
**Description:** Implementar modelo de dados para Task
**Type:** backend|frontend|database|infra|test
**Complexity:** low|medium|high
**Estimated Hours:** [número]
**Dependencies:**
- [dependência 1]

**Acceptance Criteria:**
- [critério 1]
- [critério 2]

**Technology Specifics:**
**Libraries:**
- [biblioteca 1]

**Frameworks:**
- [framework 1]

**Tools:**
- [ferramenta 1]

**Quality Requirements:**
**Test Coverage:** [porcentagem]
**Performance Targets:**
- [target 1]

**Security Requirements:**
- [requisito 1]

**Risk Assessment:**
**Level:** low|medium|high
**Mitigation Strategy:** [estratégia]

---

## Technology Stack Detailed
**Backend:**
- [tecnologia 1]

**Frontend:**
- [tecnologia 1]

**Database:**
- [tecnologia 1]

**Infrastructure:**
- [tecnologia 1]

**DevOps:**
- [tecnologia 1]

## Development Workflow
**Branch Strategy:** git-flow|trunk-based
**Code Review Process:**
- [processo 1]

**Testing Strategy:**
- [estratégia 1]

**Deployment Process:**
- [processo 1]

## Technical Risks

### [Nome do Risco]
**Probability:** low|medium|high
**Impact:** low|medium|high
**Mitigation:** [mitigação]
"""

        # Obtém temperatura do config para este agente
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent4", {}).get("temperature", 0.3)

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            technical_plan = extract_structured_data_from_markdown(response, model_name=self.agent_id)

            # Atualiza contexto compartilhado
            await self.shared_context.update_decision(
                self.agent_id, "technical", "technical_tasks", technical_plan, 0.9
            )

            # Gera capability token para operações técnicas
            token = self.guardrails.token_manager.generate_token(
                self.agent_id,
                "technical_planning",
                ["task_creation", "stack_definition"],
            )

            # Lê arquivo do agente anterior
            previous_content = self._read_previous_agent_md(4)

            # Gera nova seção de tasks técnicas
            new_section = "# TASKS TÉCNICAS DETALHADAS\n\n"
            new_section += "## TASKS TÉCNICAS\n\n"
            for task in technical_plan.get("technical_tasks", []):
                task_id = task.get("task_id", "N/A")
                description = task.get("description", "N/A")
                task_type = task.get("type", "N/A")
                complexity = task.get("complexity", "N/A")
                estimated_hours = task.get("estimated_hours", 0)

                new_section += f"### {task_id}\n\n"
                new_section += f"**Descrição:** {description}\n\n"
                new_section += f"- **Complexidade:** {complexity}\n"
                new_section += f"- **Tempo Estimado:** {estimated_hours} horas\n"
                new_section += f"- **Tipo:** {task_type}\n"
                if task.get("dependencies"):
                    new_section += f"- **Dependências:** {', '.join(task.get('dependencies', []))}\n"
                new_section += "\n**Critérios de Conclusão:**\n\n"
                for criterion in task.get("acceptance_criteria", []):
                    new_section += f"- [ ] {criterion}\n"
                new_section += "\n"
                if task.get("technology_specifics"):
                    tech_specs = task.get("technology_specifics", {})
                    new_section += "**Especificações Técnicas:**\n"
                    if tech_specs.get("libraries"):
                        new_section += f"- Bibliotecas: {', '.join(tech_specs.get('libraries', []))}\n"
                    if tech_specs.get("frameworks"):
                        new_section += f"- Frameworks: {', '.join(tech_specs.get('frameworks', []))}\n"
                    if tech_specs.get("tools"):
                        new_section += f"- Ferramentas: {', '.join(tech_specs.get('tools', []))}\n"
                    new_section += "\n"
                if task.get("risk_assessment"):
                    risk = task.get("risk_assessment", {})
                    new_section += (
                        f"**Risco:** {risk.get('level', 'N/A')} - {risk.get('mitigation_strategy', 'N/A')}\n\n"
                    )
                new_section += "---\n\n"

            if technical_plan.get("technology_stack_detailed"):
                new_section += "## Stack Tecnológica Detalhada\n\n"
                tech_stack = technical_plan.get("technology_stack_detailed", {})
                for category, techs in tech_stack.items():
                    category_name = category.replace("_", " ").title()
                    new_section += f"- **{category_name}:** {', '.join(techs) if techs else 'N/A'}\n"
                new_section += "\n"

            if technical_plan.get("development_workflow"):
                workflow = technical_plan.get("development_workflow", {})
                new_section += "## Workflow de Desenvolvimento\n\n"
                if workflow.get("branch_strategy"):
                    new_section += f"- **Branch Strategy:** {workflow.get('branch_strategy')}\n"
                if workflow.get("code_review_process"):
                    new_section += "- **Code Review Process:**\n"
                    for item in workflow.get("code_review_process", []):
                        new_section += f"  - {item}\n"
                if workflow.get("testing_strategy"):
                    new_section += "- **Testing Strategy:**\n"
                    for item in workflow.get("testing_strategy", []):
                        new_section += f"  - {item}\n"
                new_section += "\n"

            if technical_plan.get("technical_risks"):
                new_section += "## Riscos Técnicos\n\n"
                for risk in technical_plan.get("technical_risks", []):
                    new_section += f"### {risk.get('risk', 'N/A')}\n\n"
                    new_section += f"- **Probabilidade:** {risk.get('probability', 'N/A')}\n"
                    new_section += f"- **Impacto:** {risk.get('impact', 'N/A')}\n"
                    new_section += f"- **Mitigação:** {risk.get('mitigation', 'N/A')}\n\n"

            md_content = self._build_accumulative_md(
                previous_content, new_section, "TASKS TÉCNICAS DETALHADAS", 4, "Agent 3"
            )
            await self._save_markdown_file("agent4_tasks.md", md_content)

            return {
                "status": "success",
                "technical_tasks": technical_plan,
                "capability_token": token.token_id,
            }
        except Exception as e:
            logger.error(f"Erro no parsing da resposta do Tech Lead: {str(e)}")
            raise
