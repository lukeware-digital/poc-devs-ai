import asyncio
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from git import Repo
from git.exc import GitCommandError

logger = logging.getLogger("devs-ai")

AGENT_CONFIG = {
    "agent1": {
        "name": "Clarificador DEVs AI",
        "email": "clarificador@devs-ai.local",
    },
    "agent2": {
        "name": "Product Manager DEVs AI",
        "email": "product-manager@devs-ai.local",
    },
    "agent3": {
        "name": "Arquiteto DEVs AI",
        "email": "arquiteto@devs-ai.local",
    },
    "agent4": {
        "name": "Tech Lead DEVs AI",
        "email": "tech-lead@devs-ai.local",
    },
    "agent5": {
        "name": "Scaffolder DEVs AI",
        "email": "scaffolder@devs-ai.local",
    },
    "agent6": {
        "name": "Desenvolvedor DEVs AI",
        "email": "desenvolvedor@devs-ai.local",
    },
    "agent7": {
        "name": "Code Reviewer DEVs AI",
        "email": "code-reviewer@devs-ai.local",
    },
    "agent8": {
        "name": "Finalizador DEVs AI",
        "email": "finalizador@devs-ai.local",
    },
}


class AuthenticationError(Exception):
    pass


class GitService:
    def __init__(self):
        pass

    def _configure_git_no_prompt(self, repo_path: str | None = None):
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
        try:
            if repo_path:
                subprocess.run(
                    ["git", "config", "core.askPass", ""],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )
            else:
                subprocess.run(
                    ["git", "config", "core.askPass", ""],
                    check=True,
                    capture_output=True,
                )
        except subprocess.CalledProcessError:
            pass

    def _configure_agent_git_identity(self, repo_path: str, agent_id: str):
        agent_config = AGENT_CONFIG.get(agent_id, AGENT_CONFIG["agent8"])
        try:
            subprocess.run(
                ["git", "config", "user.name", agent_config["name"]],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", agent_config["email"]],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            logger.info(f"Git configurado para agente {agent_id}: {agent_config['name']}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Erro ao configurar git para agente {agent_id}: {str(e)}")

    async def clone_repository(self, repo_url: str, token: str, target_path: str) -> str:
        def _clone():
            target = Path(target_path)
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)

            self._configure_git_no_prompt()

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
        except GitCommandError as e:
            error_str = str(e).lower()
            if e.status == 128 and (
                "authentication failed" in error_str
                or "invalid username or token" in error_str
                or "password authentication is not supported" in error_str
            ):
                logger.error(f"Erro de autenticação ao clonar repositório: {str(e)}")
                raise AuthenticationError(f"Token de autenticação inválido: {str(e)}") from e
            logger.error(f"Erro ao clonar repositório: {str(e)}")
            raise
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

    async def create_commit(
        self, repo_path: str, message: str, files: list | None = None, agent_id: str | None = None
    ) -> bool:
        def _commit():
            try:
                self._configure_agent_git_identity(repo_path, agent_id or "agent8")

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

    async def push_changes(self, repo_path: str, repo_url: str, token: str, agent_id: str | None = None) -> bool:
        def _push():
            try:
                self._configure_git_no_prompt(repo_path)

                self._configure_agent_git_identity(repo_path, agent_id or "agent8")

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
