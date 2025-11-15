import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from database.connection import DatabaseConnection

logger = logging.getLogger("devs-ai")


class JobRequestRepository:
    @staticmethod
    async def create_job_request(
        job_id: UUID,
        repository_url: str,
        access_token: str,
        user_input: str,
    ) -> UUID:
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO job_requests (job_id, repository_url, access_token, user_input)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                job_id,
                repository_url,
                access_token,
                user_input,
            )
            return row["id"]

    @staticmethod
    async def get_job_request(job_id: UUID) -> dict[str, Any] | None:
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, job_id, repository_url, access_token, user_input, created_at, updated_at
                FROM job_requests
                WHERE job_id = $1
                """,
                job_id,
            )
            if row:
                return dict(row)
            return None

    @staticmethod
    async def update_job_request(
        job_id: UUID,
        repository_url: str | None = None,
        access_token: str | None = None,
        user_input: str | None = None,
    ):
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            updates = []
            params = []
            param_idx = 1

            if repository_url is not None:
                updates.append(f"repository_url = ${param_idx}")
                params.append(repository_url)
                param_idx += 1

            if access_token is not None:
                updates.append(f"access_token = ${param_idx}")
                params.append(access_token)
                param_idx += 1

            if user_input is not None:
                updates.append(f"user_input = ${param_idx}")
                params.append(user_input)
                param_idx += 1

            if not updates:
                return

            updates.append(f"updated_at = ${param_idx}")
            params.append(datetime.now(timezone.utc))
            param_idx += 1

            params.append(job_id)

            query = f"""
                UPDATE job_requests
                SET {", ".join(updates)}
                WHERE job_id = ${param_idx}
            """
            await conn.execute(query, *params)
