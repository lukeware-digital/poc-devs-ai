import logging
from uuid import UUID
from typing import Optional, Dict, Any
from database.job_repository import JobRepository

logger = logging.getLogger("DEVs_AI")


class JobManager:
    def __init__(self):
        self.repository = JobRepository()
        self.active_jobs: Dict[UUID, Any] = {}

    async def create_job(self, job_data: Dict[str, Any]) -> UUID:
        job_id = await self.repository.create_job(job_data)
        logger.info(f"Job criado: {job_id}")
        return job_id

    async def get_job(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        return await self.repository.get_job(job_id)

    async def update_job_status(
        self,
        job_id: UUID,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        await self.repository.update_job_status(
            job_id, status, progress, current_step, error_message
        )

    async def list_jobs(
        self, status: Optional[str] = None, limit: int = 100, offset: int = 0
    ):
        return await self.repository.list_jobs(status, limit, offset)

    async def cancel_job(self, job_id: UUID) -> bool:
        if job_id in self.active_jobs:
            task = self.active_jobs[job_id]
            if not task.done():
                task.cancel()
            del self.active_jobs[job_id]

        await self.repository.cancel_job(job_id)
        logger.info(f"Job cancelado: {job_id}")
        return True

    def register_active_job(self, job_id: UUID, task):
        self.active_jobs[job_id] = task

    def unregister_active_job(self, job_id: UUID):
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]

