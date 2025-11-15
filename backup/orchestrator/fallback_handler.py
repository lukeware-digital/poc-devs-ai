"""
FallbackHandler - Sistema centralizado de fallback para todos os agentes
"""

import logging
from datetime import datetime

from orchestrator.models import ProjectState

logger = logging.getLogger("devs-ai")


class FallbackHandler:
    """Handler centralizado para fallback de todos os agentes"""

    def __init__(self, shared_context):
        self.shared_context = shared_context
        self.fallback_templates = self._init_fallback_templates()

    def _init_fallback_templates(self) -> dict[str, dict[str, object]]:
        """Define templates de fallback para cada tipo de agente"""
        return {
            "agent1": {
                "key": "initial_spec",
                "decision_type": "technical",
                "template": {
                    "task_id": "fallback_spec",
                    "description": "",
                    "acceptance_criteria": ["Funcionalidade básica operacional"],
                    "estimated_complexity": 5,
                    "technical_constraints": [],
                    "fallback_used": True,
                },
            },
            "agent2": {
                "key": "user_stories",
                "decision_type": "technical",
                "template": {
                    "user_stories": [
                        {
                            "id": "US-FALLBACK-1",
                            "description": "Como usuário, eu quero uma funcionalidade básica que funcione",
                            "acceptance_criteria": ["O sistema deve responder a requisições básicas"],
                            "priority": "high",
                            "definition_of_done": ["Código implementado e testado"],
                            "estimated_story_points": 3,
                        }
                    ],
                    "product_backlog": ["US-FALLBACK-1"],
                    "release_planning": {
                        "mvp_scope": ["US-FALLBACK-1"],
                        "future_enhancements": [],
                    },
                },
            },
            "agent3": {
                "key": "main_architecture",
                "decision_type": "architecture",
                "template": {
                    "architecture_decision": {
                        "pattern": "monolithic",
                        "rationale": "Fallback para arquitetura monolítica simples",
                        "alternatives_considered": ["microservices", "serverless"],
                    },
                    "components": [
                        {
                            "name": "main_app",
                            "responsibility": "Aplicação principal",
                            "technology": "Python/FastAPI",
                            "dependencies": [],
                        }
                    ],
                    "technology_stack": {
                        "frontend": ["HTML", "CSS", "JavaScript"],
                        "backend": ["Python", "FastAPI"],
                        "database": ["SQLite"],
                        "infrastructure": ["Docker"],
                    },
                },
            },
            "agent4": {
                "key": "technical_tasks",
                "decision_type": "technical",
                "template": {
                    "technical_tasks": [
                        {
                            "task_id": "TECH-FALLBACK-1",
                            "description": "Implementar funcionalidade básica",
                            "type": "backend",
                            "complexity": "medium",
                            "estimated_hours": 8,
                            "dependencies": [],
                            "acceptance_criteria": ["Sistema funcional básico"],
                            "technology_specifics": {
                                "libraries": ["fastapi", "uvicorn"],
                                "frameworks": [],
                                "tools": [],
                            },
                            "quality_requirements": {
                                "test_coverage": 0.5,
                                "performance_targets": [],
                                "security_requirements": [],
                            },
                            "risk_assessment": {
                                "level": "low",
                                "mitigation_strategy": "Fallback simples",
                            },
                        }
                    ]
                },
            },
            "agent5": {
                "key": "project_structure",
                "decision_type": "technical",
                "template": {
                    "project_structure": [
                        {
                            "type": "directory",
                            "path": "src/",
                            "name": "",
                            "content": None,
                            "template_type": "python_package",
                            "permissions": "755",
                            "description": "Source code directory",
                        },
                        {
                            "type": "file",
                            "path": "src/main.py",
                            "name": "main.py",
                            "content": '# Basic application structure\nprint("Hello World")',
                            "template_type": "python_script",
                            "permissions": "644",
                            "description": "Main application file",
                        },
                        {
                            "type": "file",
                            "path": "requirements.txt",
                            "name": "requirements.txt",
                            "content": "fastapi\nuvicorn",
                            "template_type": "config_file",
                            "permissions": "644",
                            "description": "Python dependencies",
                        },
                    ]
                },
            },
            "agent6": {
                "key": "implemented_code",
                "decision_type": "technical",
                "template": {
                    "FALLBACK-1": {
                        "task_id": "FALLBACK-1",
                        "files_created_modified": [
                            {
                                "file_path": "src/app.py",
                                "content": (
                                    "from fastapi import FastAPI\n\napp = FastAPI()\n\n"
                                    '@app.get("/")\ndef read_root():\n    return {"Hello": "World"}'
                                ),
                                "action": "create",
                                "description": "Basic FastAPI application",
                            }
                        ],
                        "dependencies_added": ["fastapi", "uvicorn"],
                        "tests_suggested": [],
                        "implementation_notes": "Fallback implementation with basic functionality",
                        "quality_metrics": {
                            "complexity": "low",
                            "maintainability": "medium",
                            "security_considerations": ["Basic implementation - needs security review"],
                        },
                    }
                },
            },
            "agent7": {
                "key": "code_review",
                "decision_type": "quality",
                "template": {
                    "FALLBACK-1": {
                        "task_id": "FALLBACK-1",
                        "overall_score": 0.7,
                        "approved": True,
                        "issues_found": [
                            {
                                "type": "maintainability",
                                "severity": "low",
                                "file": "src/app.py",
                                "line": 1,
                                "description": "Implementação mínima - necessita expansão",
                                "suggestion": "Expandir funcionalidade conforme requisitos originais",
                                "priority": "could_fix",
                            }
                        ],
                        "suggested_improvements": [
                            {
                                "type": "enhance",
                                "description": "Adicionar testes unitários",
                                "benefit": "Melhor cobertura de testes",
                                "effort": "medium",
                            }
                        ],
                        "positive_feedback": ["Estrutura básica correta"],
                        "test_recommendations": [
                            {
                                "test_type": "unit",
                                "scope": "Endpoint /",
                                "priority": "high",
                            }
                        ],
                        "security_assessment": {
                            "vulnerabilities_found": [],
                            "data_handling": "needs_improvement",
                            "authentication_authorization": "insufficient",
                        },
                        "performance_assessment": {
                            "efficiency": "moderate",
                            "bottlenecks_identified": [],
                            "optimization_suggestions": [],
                        },
                    }
                },
            },
            "agent8": {
                "key": "final_delivery",
                "decision_type": "quality",
                "template": {
                    "delivery_timestamp": "",
                    "project_summary": {
                        "total_tasks": 1,
                        "corrections_applied": 0,
                        "documentation_files": 1,
                        "project_structure": 2,
                    },
                    "quality_metrics": {
                        "approval_rate": 100,
                        "average_score": 0.7,
                        "total_issues": 1,
                        "critical_issues": 0,
                        "quality_grade": "B",
                    },
                    "next_steps_recommendations": [
                        "Expandir funcionalidade básica para atender requisitos originais",
                        "Adicionar sistema de autenticação",
                        "Implementar persistência de dados",
                        "Adicionar testes unitários e de integração",
                    ],
                    "maintenance_considerations": [
                        "Monitorar uso em produção",
                        "Planejar expansão gradual das funcionalidades",
                    ],
                },
            },
        }

    async def apply_fallback(self, state: ProjectState, agent_id: str) -> ProjectState:
        """Aplica fallback genérico para qualquer agente"""
        logger.warning(f"Executando fallback para {agent_id}")

        if agent_id not in self.fallback_templates:
            logger.error(f"Template de fallback não encontrado para {agent_id}")
            return state

        template_config = self.fallback_templates[agent_id]
        fallback_data = template_config["template"].copy()

        # Customiza com dados do estado atual
        fallback_data = self._customize_fallback(state, agent_id, fallback_data)

        # Atualiza estado do projeto
        self._update_project_state(state, agent_id, fallback_data)

        # Atualiza contexto compartilhado
        await self.shared_context.update_decision(
            f"fallback_{agent_id}",
            template_config["decision_type"],
            template_config["key"],
            fallback_data,
            0.5,  # Baixa confiança para fallback
        )

        state.last_operation = {
            "success": True,
            "agent": f"fallback_{agent_id}",
            "result": {"status": "fallback_applied"},
            "timestamp": datetime.utcnow(),
        }
        state.recovery_attempts += 1

        return state

    def _customize_fallback(
        self, state: ProjectState, agent_id: str, fallback_data: dict[str, object]
    ) -> dict[str, object]:
        """Customiza dados de fallback com informações do estado"""
        if agent_id == "agent1" and state.last_operation.get("user_input"):
            fallback_data["description"] = state.last_operation["user_input"]
        elif agent_id == "agent8":
            fallback_data["delivery_timestamp"] = datetime.utcnow().isoformat()

        return fallback_data

    def _update_project_state(self, state: ProjectState, agent_id: str, fallback_data: dict[str, object]):
        """Atualiza o estado do projeto com dados de fallback"""
        if agent_id == "agent1":
            state.task_specification = fallback_data
        elif agent_id == "agent2":
            state.user_stories = fallback_data
        elif agent_id == "agent3":
            state.architecture = fallback_data
        elif agent_id == "agent4":
            state.technical_tasks = fallback_data
        elif agent_id == "agent5":
            state.project_structure = fallback_data
        elif agent_id == "agent6":
            state.implemented_code = fallback_data
        elif agent_id == "agent7":
            state.code_review = fallback_data
        elif agent_id == "agent8":
            state.final_delivery = fallback_data
