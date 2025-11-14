"""
Modelos de dados para o orchestrator
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectState(BaseModel):
    """
    Estado do projeto durante o workflow
    """

    current_phase: str = "initial"
    task_specification: dict[str, object | None] = None
    user_stories: dict[str, object | None] = None
    architecture: dict[str, object | None] = None
    technical_tasks: dict[str, object | None] = None
    project_structure: dict[str, object | None] = None
    implemented_code: dict[str, object | None] = None
    code_review: dict[str, object | None] = None
    final_delivery: dict[str, object | None] = None
    last_operation: dict[str, object] = {}
    failure_count: int = 0
    recovery_attempts: int = 0
    project_path: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
