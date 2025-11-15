import asyncio
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from database.step_repository import StepRepository
from main import DEVsAISystem
from models.job_model import JobRequest
from services.git_service import AuthenticationError, GitService
from services.job_manager import JobManager
from services.project_analyzer import ProjectAnalyzer
from utils.git_utils import ensure_temp_directory

logger = logging.getLogger("devs-ai")


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

            project_path = f"./temp/local/{job_id}"
            ensure_temp_directory(project_path)

            await self.job_manager.update_job_project_path(job_id, project_path)
            await self.job_manager.update_job_status(
                job_id, current_step="Preparando diretório do projeto", progress=5.0
            )

            if job_request.repository_url:
                await self.job_manager.update_job_status(job_id, current_step="Clonando repositório", progress=10.0)
                try:
                    await self.git_service.clone_repository(
                        job_request.repository_url, job_request.access_token, project_path
                    )
                except AuthenticationError as e:
                    error_msg = "Erro de autenticação: Token inválido ou sem permissão para acessar o repositório"
                    logger.error(f"Erro de autenticação ao clonar repositório: {str(e)}")
                    await self.job_manager.update_job_status(
                        job_id,
                        status="failed",
                        error_message=error_msg,
                        current_step="Erro de autenticação",
                        progress=0.0,
                    )
                    return {"success": False, "error": error_msg}
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

            from database.job_request_repository import JobRequestRepository

            job_request_data = await JobRequestRepository.get_job_request(job_id)
            if not job_request_data:
                raise ValueError(f"Dados da requisição não encontrados para job {job_id}")

            result = await self.system.process_request(
                job_request_data["user_input"],
                project_path,
                job_id=str(job_id),
                repository_url=job_request_data["repository_url"],
                access_token=job_request_data["access_token"],
            )

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

    def _log_job_start_with_steps(self, job_id: UUID, steps: list[dict[str, Any]]):
        """
        Gera log grande e decorativo mostrando o job iniciado e os steps executados pelos agentes.

        Args:
            job_id: ID do job
            steps: Lista de steps executados
        """
        border = "═" * 70

        agent_icons = {
            "agent1": "🔍",
            "agent2": "📋",
            "agent3": "🏗️",
            "agent4": "👨‍💼",
            "agent5": "📁",
            "agent6": "💻",
            "agent7": "🔎",
            "agent8": "✅",
        }

        status_icons = {
            "pending": "⏳",
            "running": "⚙️",
            "completed": "✅",
            "failed": "❌",
        }

        agent_names = {
            "agent1": "Clarificador",
            "agent2": "Product Manager",
            "agent3": "Arquiteto",
            "agent4": "Tech Lead",
            "agent5": "Scaffolder",
            "agent6": "Desenvolvedor",
            "agent7": "Code Reviewer",
            "agent8": "Finalizador",
        }

        log_message = f"""
{border}
🚀  JOB INICIADO - Desenvolvimento do Software
{border}
Job ID: {job_id}
Total de Steps: {len(steps)}
{border}
"""

        if steps:
            log_message += "Steps Executados pelos Agentes:\n"
            log_message += f"{border}\n"

            for step in steps:
                agent_id = step.get("agent_id", "unknown")
                step_name = step.get("step_name", "N/A")
                status = step.get("status", "unknown")

                agent_icon = agent_icons.get(agent_id, "🤖")
                status_icon = status_icons.get(status, "❓")
                agent_name = agent_names.get(agent_id, agent_id)

                started_at = step.get("started_at")
                completed_at = step.get("completed_at")

                time_info = ""
                if started_at:
                    time_info = f" | Iniciado: {started_at}"
                if completed_at:
                    time_info += f" | Concluído: {completed_at}"

                log_message += f"{agent_icon} {agent_name} ({agent_id})\n"
                log_message += f"   {status_icon} Status: {status.upper()}\n"
                log_message += f"   📝 Step: {step_name}{time_info}\n"

                if step.get("error_message"):
                    log_message += f"   ⚠️  Erro: {step.get('error_message')}\n"

                log_message += f"{border}\n"
        else:
            log_message += "Nenhum step encontrado para este job.\n"
            log_message += f"{border}\n"

        logger.info(log_message)

    async def approve_commit(self, job_id: UUID, approved: bool, commit_message: str) -> dict[str, Any]:
        from database.job_request_repository import JobRequestRepository

        job = await self.job_manager.get_job(job_id)
        if not job:
            raise ValueError("Job não encontrado")

        project_path = job.get("project_path")
        if not project_path:
            raise ValueError("Project path não encontrado para o job")

        job_request_data = await JobRequestRepository.get_job_request(job_id)
        if not job_request_data:
            raise ValueError("Dados da requisição não encontrados para o job")

        if not approved:
            await self.job_manager.update_job_status(
                job_id, status="completed", current_step="Commit rejeitado", progress=100.0
            )
            del self.approval_requests[job_id]
            return {"success": True, "message": "Commit rejeitado"}

        try:
            await self.job_manager.update_job_status(job_id, current_step="Criando commit", progress=97.0)

            await self.git_service.create_commit(project_path, commit_message, agent_id="agent8")

            if job_request_data.get("repository_url"):
                await self.job_manager.update_job_status(job_id, current_step="Fazendo push", progress=99.0)
                await self.git_service.push_changes(
                    project_path,
                    job_request_data["repository_url"],
                    job_request_data["access_token"],
                    agent_id="agent8",
                )

            await self.job_manager.update_job_status(
                job_id, status="completed", current_step="Concluído", progress=100.0
            )

            steps = await StepRepository.get_steps_by_job(job_id)
            self._log_job_start_with_steps(job_id, steps)

            if job_id in self.approval_requests:
                del self.approval_requests[job_id]
            return {"success": True, "message": "Commit e push realizados com sucesso"}

        except Exception as e:
            logger.error(f"Erro ao fazer commit/push: {str(e)}")
            await self.job_manager.update_job_status(
                job_id, status="failed", error_message=str(e), current_step="Erro no commit"
            )
            return {"success": False, "error": str(e)}
