from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class JobRequest(BaseModel):
    repository_url: str = Field(..., description="URL do repositório Git")
    access_token: str = Field(..., description="Token de acesso ao repositório")
    user_input: str = Field(..., description="Solicitação do usuário para desenvolvimento")
    project_path: Optional[str] = Field(None, description="Caminho opcional do projeto")


class JobStatus(BaseModel):
    job_id: UUID
    status: str = Field(..., description="Status: pending, running, completed, failed, cancelled")
    progress: float = Field(0.0, ge=0.0, le=100.0, description="Progresso de 0 a 100")
    current_step: Optional[str] = Field(None, description="Etapa atual do processamento")
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = Field(None, description="Mensagem de erro se houver")
    repository_url: Optional[str] = None
    project_path: Optional[str] = None
    user_input: Optional[str] = None


class JobResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


class CommitApprovalRequest(BaseModel):
    approved: bool = Field(..., description="Se o commit foi aprovado")
    commit_message: str = Field(..., description="Mensagem do commit")

