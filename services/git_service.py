import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from git import Repo

logger = logging.getLogger("DEVs_AI")


class GitService:
    def __init__(self):
        pass

    async def clone_repository(self, repo_url: str, token: str, target_path: str) -> str:
        def _clone():
            target = Path(target_path)
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)

            parsed_url = urlparse(repo_url)
            if parsed_url.scheme in ("http", "https"):
                auth_url = f"{parsed_url.scheme}://{token}@{parsed_url.netloc}{parsed_url.path}"
            else:
                auth_url = repo_url

            Repo.clone_from(auth_url, str(target))
            logger.info(f"Repositório clonado com sucesso: {target_path}")
            return str(target)

        try:
            return await asyncio.to_thread(_clone)
        except Exception as e:
            logger.error(f"Erro ao clonar repositório: {str(e)}")
            raise

    async def validate_repository(self, path: str) -> bool:
        def _validate():
            repo_path = Path(path)
            if not repo_path.exists():
                return False
            try:
                repo = Repo(str(repo_path))
                return not repo.bare
            except Exception:
                return False

        return await asyncio.to_thread(_validate)

    async def analyze_project_structure(self, path: str) -> dict[str, Any]:
        def _analyze():
            project_path = Path(path)
            if not project_path.exists():
                return {"exists": False, "directories": [], "files": []}

            directories = []
            files = []

            for item in project_path.rglob("*"):
                if item.is_dir():
                    if item.name not in (".git", "__pycache__", ".pytest_cache", "node_modules"):
                        rel_path = str(item.relative_to(project_path))
                        directories.append(rel_path)
                elif item.is_file():
                    rel_path = str(item.relative_to(project_path))
                    if not rel_path.startswith(".git/"):
                        files.append(rel_path)

            return {
                "exists": True,
                "directories": sorted(directories),
                "files": sorted(files),
                "total_files": len(files),
                "total_directories": len(directories),
            }

        return await asyncio.to_thread(_analyze)

    async def init_git_repository(self, path: str) -> bool:
        def _init():
            repo_path = Path(path)
            if not repo_path.exists():
                repo_path.mkdir(parents=True, exist_ok=True)

            try:
                if (repo_path / ".git").exists():
                    return True

                Repo.init(str(repo_path))
                logger.info(f"Repositório Git inicializado: {path}")
                return True
            except Exception as e:
                logger.error(f"Erro ao inicializar repositório Git: {str(e)}")
                return False

        return await asyncio.to_thread(_init)

    async def create_commit(self, repo_path: str, message: str, files: list | None = None) -> bool:
        def _commit():
            try:
                repo = Repo(str(repo_path))
                if files:
                    for file_path in files:
                        repo.index.add([file_path])
                else:
                    repo.index.add(["*"])

                repo.index.commit(message)
                logger.info(f"Commit criado: {message}")
                return True
            except Exception as e:
                logger.error(f"Erro ao criar commit: {str(e)}")
                return False

        return await asyncio.to_thread(_commit)

    async def push_changes(self, repo_path: str, repo_url: str, token: str) -> bool:
        def _push():
            try:
                repo = Repo(str(repo_path))
                origin = repo.remote(name="origin")
                if not origin:
                    parsed_url = urlparse(repo_url)
                    if parsed_url.scheme in ("http", "https"):
                        auth_url = f"{parsed_url.scheme}://{token}@{parsed_url.netloc}{parsed_url.path}"
                    else:
                        auth_url = repo_url
                    origin = repo.create_remote("origin", auth_url)

                origin.push()
                logger.info("Push realizado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao fazer push: {str(e)}")
                return False

        return await asyncio.to_thread(_push)
