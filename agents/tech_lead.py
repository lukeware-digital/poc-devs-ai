import json
import logging

from agents.base_agent import BaseAgent

logger = logging.getLogger("DEVs_AI")


class Agent4_TechLead(BaseAgent):
    """Agent-4: Tech Lead - Define tasks técnicas e stack detalhada"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
        spec = task["specification"]
        architecture = task["architecture"]
        user_stories = task["user_stories"]

        # Carrega template especializado
        template_base = self._build_prompt("tech_lead", {})
        
        prompt = f"""
{template_base}

Crie tasks técnicas detalhadas baseado em:
ESPECIFICAÇÃO: {json.dumps(spec, indent=2)}
ARQUITETURA: {json.dumps(architecture, indent=2)}
HISTÓRIAS DE USUÁRIO: {json.dumps(user_stories, indent=2)}

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
            technical_plan = json.loads(response)

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

            return {
                "status": "success",
                "technical_tasks": technical_plan,
                "capability_token": token.token_id,
            }
        except Exception as e:
            logger.error(f"Erro no parsing da resposta do Tech Lead: {str(e)}")
            raise
