import logging
import os

import asyncpg

logger = logging.getLogger("devs-ai")


class DatabaseConnection:
    _pool: asyncpg.Pool | None = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            await cls.initialize()
        return cls._pool

    @classmethod
    async def initialize(cls):
        if cls._pool is not None:
            return

        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        database = os.getenv("POSTGRES_DB", "minha_base")
        user = os.getenv("POSTGRES_USER", "usuario")
        password = os.getenv("POSTGRES_PASSWORD", "senha")

        try:
            cls._pool = await asyncpg.create_pool(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                min_size=2,
                max_size=10,
            )
            logger.info("Pool de conexões PostgreSQL criado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao criar pool de conexões PostgreSQL: {str(e)}")
            raise

    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("Pool de conexões PostgreSQL fechado")
