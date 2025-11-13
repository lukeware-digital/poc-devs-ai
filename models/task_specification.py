"""
Modelo Pydantic para especificação de tarefas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class TaskSpecification(BaseModel):
    """
    Especificação formal de uma tarefa gerada pelo Agent-1
    """
    task_id: str = Field(..., description="Identificador único da tarefa")
    description: str = Field(..., description="Descrição completa da tarefa")
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Critérios de aceitação para considerar a tarefa completa"
    )
    estimated_complexity: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Complexidade estimada de 1 (simples) a 10 (muito complexo)"
    )
    technical_constraints: Optional[List[str]] = Field(
        default_factory=list,
        description="Restrições técnicas identificadas"
    )
    fallback_attempts: int = Field(
        default=0,
        ge=0,
        description="Número de tentativas de fallback realizadas"
    )
    requirements_breakdown: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Breakdown de requisitos funcionais e não-funcionais"
    )
    clarification_questions: Optional[List[str]] = Field(
        default_factory=list,
        description="Questões de clarificação para o usuário"
    )
    
    @field_validator('estimated_complexity')
    @classmethod
    def validate_complexity(cls, v: int) -> int:
        """Valida que a complexidade está no intervalo correto"""
        if not 1 <= v <= 10:
            raise ValueError('Complexidade deve estar entre 1 e 10')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Valida que a descrição não está vazia"""
        if not v or not v.strip():
            raise ValueError('Descrição não pode estar vazia')
        return v.strip()
    
    @field_validator('acceptance_criteria')
    @classmethod
    def validate_criteria(cls, v: List[str]) -> List[str]:
        """Valida que há pelo menos um critério de aceitação"""
        if not v:
            return ['Funcionalidade básica implementada e testada']
        return [criterion.strip() for criterion in v if criterion.strip()]
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_abc12345",
                "description": "Criar API REST para gerenciamento de usuários",
                "acceptance_criteria": [
                    "Endpoint POST /users para criar usuário",
                    "Endpoint GET /users/:id para buscar usuário",
                    "Validação de dados de entrada",
                    "Testes unitários com cobertura > 80%"
                ],
                "estimated_complexity": 7,
                "technical_constraints": [
                    "Usar FastAPI",
                    "Banco de dados PostgreSQL",
                    "Autenticação JWT"
                ],
                "fallback_attempts": 0,
                "requirements_breakdown": {
                    "functional": [
                        "CRUD de usuários",
                        "Autenticação"
                    ],
                    "non_functional": [
                        "Performance < 200ms",
                        "Segurança: senha hash bcrypt"
                    ]
                },
                "clarification_questions": []
            }
        }

