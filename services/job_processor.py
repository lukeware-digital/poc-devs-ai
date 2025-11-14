import asyncio
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from main import DEVsAISystem
from models.job_model import JobRequest
from services.git_service import GitService
from services.job_manager import JobManager
from services.project_analyzer import ProjectAnalyzer
from utils.git_utils import ensure_temp_directory, sanitize_path

logger = logging.getLogger("DEVs_AI")


class JobProcessor:
    def __init__(self, system: DEVsAISystem):
        self.system = system
        self.job_manager = JobManager()
        self.git_service = GitService()
        self.project_analyzer = ProjectAnalyzer()
        self.approval_requests: dict[UUID, dict[str, Any]] = {}

    async def process_job(self, job_id: UUID, job_request: JobRequest) -> dict[str, Any]:
        try:
            await self.job_manager.update_job_status(job_id, status="running", current_step="Iniciando processamento")

            project_path = job_request.project_path
            if not project_path:
                project_path = f"./temp/local/{job_id}"
                ensure_temp_directory(project_path)

            project_path = sanitize_path(project_path)
            await self.job_manager.update_job_status(
                job_id, current_step="Preparando diretório do projeto", progress=5.0
            )

            if job_request.repository_url:
                await self.job_manager.update_job_status(job_id, current_step="Clonando repositório", progress=10.0)
                try:
                    await self.git_service.clone_repository(
                        job_request.repository_url, job_request.access_token, project_path
                    )
                except Exception as e:
                    logger.error(f"Erro ao clonar repositório: {str(e)}")
                    if not await self.git_service.validate_repository(project_path):
                        raise
            else:
                if not Path(project_path).exists():
                    Path(project_path).mkdir(parents=True, exist_ok=True)

            await self.job_manager.update_job_status(job_id, current_step="Validando projeto", progress=20.0)

            code_exists = await self.project_analyzer.validate_code_exists(project_path)
            await self.git_service.analyze_project_structure(project_path)
            await self.project_analyzer.analyze_directories(project_path)
            await self.project_analyzer.detect_project_type(project_path)
            git_status = await self.project_analyzer.check_git_status(project_path)

            await self.job_manager.update_job_status(job_id, current_step="Analisando estrutura", progress=30.0)

            if not code_exists and not git_status.get("is_git_repo"):
                await self.job_manager.update_job_status(
                    job_id, current_step="Inicializando projeto do zero", progress=35.0
                )
                await self.git_service.init_git_repository(project_path)

            await self.job_manager.update_job_status(job_id, current_step="Executando workflow DEVs AI", progress=40.0)

            result = await self.system.process_request(job_request.user_input, project_path)

            await self.job_manager.update_job_status(
                job_id, current_step="Aguardando aprovação para commit", progress=90.0
            )

            self.approval_requests[job_id] = {
                "project_path": project_path,
                "repository_url": job_request.repository_url,
                "access_token": job_request.access_token,
                "result": result,
            }

            await self.job_manager.update_job_status(
                job_id, status="pending_approval", current_step="Aguardando aprovação", progress=95.0
            )

            return {"success": True, "job_id": str(job_id), "status": "pending_approval"}

        except asyncio.CancelledError:
            await self.job_manager.update_job_status(job_id, status="cancelled", current_step="Cancelado", progress=0.0)
            raise
        except Exception as e:
            logger.error(f"Erro ao processar job {job_id}: {str(e)}", exc_info=True)
            await self.job_manager.update_job_status(
                job_id,
                status="failed",
                error_message=str(e),
                current_step="Erro no processamento",
                progress=0.0,
            )
            return {"success": False, "error": str(e)}

    async def approve_commit(self, job_id: UUID, approved: bool, commit_message: str) -> dict[str, Any]:
        if job_id not in self.approval_requests:
            raise ValueError("Job não encontrado ou não está aguardando aprovação")

        request_data = self.approval_requests[job_id]
        project_path = request_data["project_path"]

        if not approved:
            await self.job_manager.update_job_status(
                job_id, status="completed", current_step="Commit rejeitado", progress=100.0
            )
            del self.approval_requests[job_id]
            return {"success": True, "message": "Commit rejeitado"}

        try:
            await self.job_manager.update_job_status(job_id, current_step="Criando commit", progress=97.0)

            await self.git_service.create_commit(project_path, commit_message)

            if request_data.get("repository_url"):
                await self.job_manager.update_job_status(job_id, current_step="Fazendo push", progress=99.0)
                await self.git_service.push_changes(
                    project_path,
                    request_data["repository_url"],
                    request_data["access_token"],
                )

            await self.job_manager.update_job_status(
                job_id, status="completed", current_step="Concluído", progress=100.0
            )

            del self.approval_requests[job_id]
            return {"success": True, "message": "Commit e push realizados com sucesso"}

        except Exception as e:
            logger.error(f"Erro ao fazer commit/push: {str(e)}")
            await self.job_manager.update_job_status(
                job_id, status="failed", error_message=str(e), current_step="Erro no commit"
            )
            return {"success": False, "error": str(e)}
