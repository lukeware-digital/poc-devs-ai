import asyncio
import logging
from pathlib import Path
from typing import Any

from git import Repo

logger = logging.getLogger("DEVs_AI")


class ProjectAnalyzer:
    def __init__(self):
        pass

    async def validate_code_exists(self, path: str) -> bool:
        def _validate():
            project_path = Path(path)
            if not project_path.exists():
                return False

            code_extensions = {
                ".py",
                ".js",
                ".ts",
                ".java",
                ".cpp",
                ".c",
                ".h",
                ".cs",
                ".go",
                ".rs",
                ".rb",
                ".php",
                ".swift",
                ".kt",
                ".scala",
                ".clj",
                ".hs",
                ".ml",
                ".sh",
                ".bat",
                ".ps1",
                ".sql",
                ".html",
                ".css",
                ".vue",
                ".jsx",
                ".tsx",
                ".dart",
                ".lua",
                ".r",
                ".m",
                ".mm",
            }

            for item in project_path.rglob("*"):
                if item.is_file() and item.suffix in code_extensions:
                    if not item.name.startswith(".") and ".git" not in str(item):
                        return True
            return False

        return await asyncio.to_thread(_validate)

    async def analyze_directories(self, path: str) -> list[str]:
        def _analyze():
            project_path = Path(path)
            if not project_path.exists():
                return []

            directories = []
            for item in project_path.rglob("*"):
                if item.is_dir():
                    if item.name not in (".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"):
                        rel_path = str(item.relative_to(project_path))
                        if rel_path not in directories:
                            directories.append(rel_path)

            return sorted(directories)

        return await asyncio.to_thread(_analyze)

    async def detect_project_type(self, path: str) -> str:
        def _detect():
            project_path = Path(path)
            if not project_path.exists():
                return "unknown"

            indicators = {
                "python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile", "poetry.lock"],
                "nodejs": ["package.json", "yarn.lock", "package-lock.json"],
                "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
                "go": ["go.mod", "go.sum"],
                "rust": ["Cargo.toml", "Cargo.lock"],
                "ruby": ["Gemfile", "Rakefile"],
                "php": ["composer.json", "composer.lock"],
                "csharp": [".csproj", ".sln"],
                "cpp": ["CMakeLists.txt", "Makefile"],
            }

            for project_type, files in indicators.items():
                for file_name in files:
                    if (project_path / file_name).exists():
                        return project_type

            if any(project_path.glob("*.py")):
                return "python"
            elif any(project_path.glob("*.js")):
                return "nodejs"
            elif any(project_path.glob("*.java")):
                return "java"

            return "unknown"

        return await asyncio.to_thread(_detect)

    async def check_git_status(self, path: str) -> dict[str, Any]:
        def _check():
            repo_path = Path(path)
            if not repo_path.exists():
                return {"is_git_repo": False, "has_commits": False, "has_changes": False}

            try:
                repo = Repo(str(repo_path))
                is_git_repo = True
                has_commits = len(list(repo.iter_commits())) > 0
                has_changes = repo.is_dirty() or len(repo.untracked_files) > 0

                return {
                    "is_git_repo": is_git_repo,
                    "has_commits": has_commits,
                    "has_changes": has_changes,
                    "untracked_files": repo.untracked_files,
                    "modified_files": [item.a_path for item in repo.index.diff(None)],
                }
            except Exception as e:
                logger.warning(f"Erro ao verificar status Git: {str(e)}")
                return {"is_git_repo": False, "has_commits": False, "has_changes": False}

        return await asyncio.to_thread(_check)
