import logging
import re
from pathlib import Path

import asyncpg

logger = logging.getLogger("devs-ai")


class MigrationManager:
    def __init__(self, migrations_dir: Path):
        self.migrations_dir = migrations_dir
        self.schema_version_table = "schema_version"

    async def initialize_schema_table(self, conn: asyncpg.Connection):
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version VARCHAR(50) PRIMARY KEY,
                description TEXT,
                checksum VARCHAR(64),
                executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER,
                success BOOLEAN DEFAULT TRUE
            )
            """
        )
        logger.info("Tabela schema_version verificada/criada no PostgreSQL")

    async def get_applied_migrations(self, conn: asyncpg.Connection) -> list[str]:
        rows = await conn.fetch("SELECT version FROM schema_version WHERE success = TRUE ORDER BY version")
        return [row["version"] for row in rows]

    def get_migration_files(self) -> list[tuple[str, Path]]:
        pattern = re.compile(r"^(\d+)_(.+)\.sql$")
        migrations = []

        if not self.migrations_dir.exists():
            logger.warning(f"Diretório de migrações não encontrado: {self.migrations_dir}")
            return migrations

        for file_path in self.migrations_dir.glob("*.sql"):
            match = pattern.match(file_path.name)
            if match:
                version = match.group(1)
                migrations.append((int(version), version, file_path))
            else:
                logger.warning(f"Arquivo de migração com nome inválido ignorado: {file_path.name}")

        migrations.sort(key=lambda x: x[0])
        return [(v, p) for _, v, p in migrations]

    def calculate_checksum(self, content: str) -> str:
        import hashlib

        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def apply_migration(self, conn: asyncpg.Connection, version: str, file_path: Path) -> bool:
        try:
            content = file_path.read_text()
            checksum = self.calculate_checksum(content)
            description = file_path.stem.replace(f"{version}_", "").replace("_", " ")

            existing = await conn.fetchrow("SELECT * FROM schema_version WHERE version = $1", version)

            if existing and existing["success"]:
                if existing["checksum"] != checksum:
                    logger.warning(
                        f"Migração {version} já aplicada, mas checksum diferente. "
                        f"Esperado: {existing['checksum']}, Atual: {checksum}"
                    )
                return False

            import time

            start_time = time.time()

            async with conn.transaction():
                await conn.execute(content)
                execution_time_ms = int((time.time() - start_time) * 1000)

                if existing:
                    await conn.execute(
                        """
                        UPDATE schema_version
                        SET description = $1, checksum = $2, executed_at = CURRENT_TIMESTAMP,
                            execution_time_ms = $3, success = TRUE
                        WHERE version = $4
                        """,
                        description,
                        checksum,
                        execution_time_ms,
                        version,
                    )
                    logger.info(f"Migração {version} atualizada no registro do PostgreSQL")
                else:
                    await conn.execute(
                        """
                        INSERT INTO schema_version
                        (version, description, checksum, execution_time_ms, success)
                        VALUES ($1, $2, $3, $4, TRUE)
                        """,
                        version,
                        description,
                        checksum,
                        execution_time_ms,
                    )
                    logger.info(f"Migração {version} registrada no PostgreSQL")

            logger.info(f"Migração {version} aplicada com sucesso ({execution_time_ms}ms)")
            return True

        except Exception as e:
            logger.error(f"Erro ao aplicar migração {version}: {str(e)}", exc_info=True)
            try:
                await conn.execute(
                    """
                    INSERT INTO schema_version
                    (version, description, checksum, success)
                    VALUES ($1, $2, $3, FALSE)
                    ON CONFLICT (version) DO UPDATE SET success = FALSE
                    """,
                    version,
                    file_path.stem,
                    self.calculate_checksum(content),
                )
                logger.error(f"Falha da migração {version} registrada no PostgreSQL")
            except Exception as log_error:
                logger.error(f"Erro ao registrar falha da migração: {str(log_error)}")
            raise

    async def run_migrations(self, pool: asyncpg.Pool):
        async with pool.acquire() as conn:
            await self.initialize_schema_table(conn)

            applied = await self.get_applied_migrations(conn)
            logger.info(f"Migrações já aplicadas no PostgreSQL: {applied if applied else 'nenhuma'}")

            migrations = self.get_migration_files()
            logger.info(f"Migrações encontradas no diretório: {[v for v, _ in migrations]}")

            pending = [(v, p) for v, p in migrations if v not in applied]

            if not pending:
                logger.info("Nenhuma migração pendente - banco de dados está atualizado")
                return

            logger.info(f"Aplicando {len(pending)} migração(ões) pendente(s) e registrando no PostgreSQL...")

            for version, file_path in pending:
                await self.apply_migration(conn, version, file_path)

            final_applied = await self.get_applied_migrations(conn)
            logger.info(f"Todas as migrações foram aplicadas e registradas no PostgreSQL. Total: {len(final_applied)}")
