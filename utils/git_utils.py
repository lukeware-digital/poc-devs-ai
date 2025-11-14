import os
import re
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DEVs_AI")


def sanitize_path(path: str) -> str:
    path = re.sub(r'[^\w\-_./\\]', '', path)
    path = os.path.normpath(path)
    if path.startswith('..'):
        raise ValueError("Caminho não pode conter '..'")
    return path


def ensure_temp_directory(base_path: str) -> Path:
    base = Path(base_path)
    base.mkdir(parents=True, exist_ok=True)
    return base


def create_archive(project_path: str, output_path: Optional[str] = None) -> str:
    project = Path(project_path)
    if not project.exists():
        raise ValueError(f"Caminho do projeto não existe: {project_path}")

    if output_path is None:
        output_path = str(project.parent / f"{project.name}.zip")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    shutil.make_archive(
        str(output.with_suffix('')),
        'zip',
        str(project.parent),
        project.name
    )

    logger.info(f"Arquivo criado: {output_path}")
    return output_path

