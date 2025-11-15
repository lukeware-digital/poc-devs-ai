import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from database.connection import DatabaseConnection

logger = logging.getLogger("devs-ai")


class StepRepository:
    @staticmethod
    async def create_step(
        job_id: UUID,
        agent_id: str,
        step_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO steps (job_id, agent_id, step_name, status, started_at, metadata)
                VALUES ($1, $2, $3, 'pending', CURRENT_TIMESTAMP, $4)
                RETURNING id
                """,
                job_id,
                agent_id,
                step_name,
                metadata or {},
            )
            return row["id"]

    @staticmethod
    async def update_step_status(
        step_id: UUID,
        status: str,
        error_message: str | None = None,
        error_cause: str | None = None,
    ):
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            updates = []
            params = []
            param_idx = 1

            updates.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1

            if status == "running":
                updates.append(f"started_at = ${param_idx}")
                params.append(datetime.now(timezone.utc))
                param_idx += 1
            elif status in ("completed", "failed"):
                updates.append(f"completed_at = ${param_idx}")
                params.append(datetime.now(timezone.utc))
                param_idx += 1

            if error_message is not None:
                updates.append(f"error_message = ${param_idx}")
                params.append(error_message)
                param_idx += 1

            if error_cause is not None:
                updates.append(f"error_cause = ${param_idx}")
                params.append(error_cause)
                param_idx += 1

            updates.append(f"updated_at = ${param_idx}")
            params.append(datetime.now(timezone.utc))
            param_idx += 1

            params.append(step_id)

            query = f"""
                UPDATE steps
                SET {", ".join(updates)}
                WHERE id = ${param_idx}
            """
            await conn.execute(query, *params)

    @staticmethod
    async def record_step_failure(
        step_id: UUID,
        error_message: str,
        error_cause: str,
    ):
        await StepRepository.update_step_status(
            step_id,
            status="failed",
            error_message=error_message,
            error_cause=error_cause,
        )

    @staticmethod
    async def get_steps_by_job(job_id: UUID) -> list[dict[str, Any]]:
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, job_id, agent_id, step_name, status, started_at, completed_at,
                       error_message, error_cause, metadata, created_at, updated_at
                FROM steps
                WHERE job_id = $1
                ORDER BY created_at ASC
                """,
                job_id,
            )
            return [dict(row) for row in rows]

    @staticmethod
    async def get_step(step_id: UUID) -> dict[str, Any] | None:
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, job_id, agent_id, step_name, status, started_at, completed_at,
                       error_message, error_cause, metadata, created_at, updated_at
                FROM steps
                WHERE id = $1
                """,
                step_id,
            )
            if row:
                return dict(row)
            return None
