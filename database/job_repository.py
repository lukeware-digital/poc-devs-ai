import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from database.connection import DatabaseConnection

logger = logging.getLogger("devs-ai")


class JobRepository:
    @staticmethod
    async def create_job(job_data: dict[str, Any]) -> UUID:
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO jobs (
                    status, repository_url, project_path, user_input,
                    progress, current_step, access_token
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                job_data.get("status", "pending"),
                job_data.get("repository_url"),
                job_data.get("project_path"),
                job_data.get("user_input"),
                job_data.get("progress", 0.0),
                job_data.get("current_step"),
                job_data.get("access_token"),
            )
            return row["id"]

    @staticmethod
    async def get_job(job_id: UUID) -> dict[str, Any] | None:
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, status, repository_url, project_path, progress, current_step,
                       user_input, error_message, access_token, created_at, updated_at
                FROM jobs
                WHERE id = $1
                """,
                job_id,
            )
            if row:
                return dict(row)
            return None

    @staticmethod
    async def update_job_status(
        job_id: UUID,
        status: str | None = None,
        progress: float | None = None,
        current_step: str | None = None,
        error_message: str | None = None,
    ):
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            updates = []
            params = []
            param_idx = 1

            if status is not None:
                updates.append(f"status = ${param_idx}")
                params.append(status)
                param_idx += 1

            if progress is not None:
                updates.append(f"progress = ${param_idx}")
                params.append(progress)
                param_idx += 1

            if current_step is not None:
                updates.append(f"current_step = ${param_idx}")
                params.append(current_step)
                param_idx += 1

            if error_message is not None:
                updates.append(f"error_message = ${param_idx}")
                params.append(error_message)
                param_idx += 1

            updates.append(f"updated_at = ${param_idx}")
            params.append(datetime.now(timezone.utc))
            param_idx += 1

            params.append(job_id)

            query = f"""
                UPDATE jobs
                SET {", ".join(updates)}
                WHERE id = ${param_idx}
            """
            await conn.execute(query, *params)

    @staticmethod
    async def list_jobs(
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    """
                    SELECT id, status, repository_url, project_path, progress, current_step,
                           user_input, error_message, access_token, created_at, updated_at
                    FROM jobs
                    WHERE status = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    status,
                    limit,
                    offset,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, status, repository_url, project_path, progress, current_step,
                           user_input, error_message, access_token, created_at, updated_at
                    FROM jobs
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )
            return [dict(row) for row in rows]

    @staticmethod
    async def update_job_project_path(job_id: UUID, project_path: str):
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET project_path = $1, updated_at = CURRENT_TIMESTAMP
                WHERE id = $2
                """,
                project_path,
                job_id,
            )

    @staticmethod
    async def cancel_job(job_id: UUID):
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND status IN ('pending', 'running')
                """,
                job_id,
            )

    @staticmethod
    async def update_job_failure_info(
        job_id: UUID,
        failed_step_id: UUID | None = None,
        failed_agent_id: str | None = None,
    ):
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            updates = []
            params = []
            param_idx = 1

            if failed_step_id is not None:
                updates.append(f"failed_step_id = ${param_idx}")
                params.append(failed_step_id)
                param_idx += 1

            if failed_agent_id is not None:
                updates.append(f"failed_agent_id = ${param_idx}")
                params.append(failed_agent_id)
                param_idx += 1

            if not updates:
                return

            updates.append(f"updated_at = ${param_idx}")
            params.append(datetime.now(timezone.utc))
            param_idx += 1

            params.append(job_id)

            query = f"""
                UPDATE jobs
                SET {", ".join(updates)}
                WHERE id = ${param_idx}
            """
            await conn.execute(query, *params)
