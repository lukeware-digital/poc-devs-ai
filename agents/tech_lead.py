import json
import logging

from agents.base_agent import BaseAgent
from utils.json_parser import extract_json_from_response

logger = logging.getLogger("devs-ai")


class Agent4_TechLead(BaseAgent):
    """Agent-4: Tech Lead - Define tasks técnicas e stack detalhada"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
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

Formato JSON:
{{
    "technical_tasks": [
        {{
            "task_id": "TECH-1",
            "description": "Implementar modelo de dados para Task",
            "type": "backend|frontend|database|infra|test",
            "complexity": "low|medium|high",
            "estimated_hours": 0,
            "dependencies": [],
            "acceptance_criteria": [],
            "technology_specifics": {{
                "libraries": [],
                "frameworks": [],
                "tools": []
            }},
            "quality_requirements": {{
                "test_coverage": 0,
                "performance_targets": [],
                "security_requirements": []
            }},
            "risk_assessment": {{
                "level": "low|medium|high",
                "mitigation_strategy": ""
            }}
        }}
    ],
    "technology_stack_detailed": {{
        "backend": [],
        "frontend": [],
        "database": [],
        "infrastructure": [],
        "devops": []
    }},
    "development_workflow": {{
        "branch_strategy": "git-flow|trunk-based",
        "code_review_process": [],
        "testing_strategy": [],
        "deployment_process": []
    }},
    "technical_risks": [
        {{
            "risk": "",
            "probability": "low|medium|high",
            "impact": "low|medium|high",
            "mitigation": ""
        }}
    ]
}}
"""

        # Obtém temperatura do config para este agente
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent4", {}).get("temperature", 0.3)

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            technical_plan = extract_json_from_response(response, model_name=self.agent_id)

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

            # Salva technical_tasks.md
            md_content = "# Technical Tasks\n\n"
            for task in technical_plan.get("technical_tasks", []):
                md_content += f"## {task.get('task_id', 'N/A')}\n\n"
                md_content += f"**Description:** {task.get('description', 'N/A')}\n\n"
                md_content += f"**Type:** {task.get('type', 'N/A')}\n\n"
                md_content += f"**Complexity:** {task.get('complexity', 'N/A')}\n\n"
                md_content += f"**Estimated Hours:** {task.get('estimated_hours', 0)}\n\n"
                md_content += "**Acceptance Criteria:**\n"
                for criterion in task.get("acceptance_criteria", []):
                    md_content += f"- {criterion}\n"
                md_content += "\n---\n\n"
            await self._save_markdown_file("technical_tasks.md", md_content)

            return {
                "status": "success",
                "technical_tasks": technical_plan,
                "capability_token": token.token_id,
            }
        except Exception as e:
            logger.error(f"Erro no parsing da resposta do Tech Lead: {str(e)}")
            raise
