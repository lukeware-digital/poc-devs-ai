import json
import logging
import os

from agents.base_agent import BaseAgent
from utils.json_parser import extract_json_from_response

logger = logging.getLogger("devs-ai")


class Agent5_Scaffolder(BaseAgent):
    """Agent-5: Scaffolder - Cria estrutura do projeto"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:  # noqa: C901
        architecture = task["architecture"]
        technical_tasks = task["technical_tasks"]

        # Verifica se projeto já existe
        project_path = self._get_project_path()
        project_exists = False
        existing_structure = {}
        if project_path:
            try:
                from services.project_analyzer import ProjectAnalyzer

                analyzer = ProjectAnalyzer()
                code_exists = await analyzer.validate_code_exists(project_path)
                directories = await analyzer.analyze_directories(project_path)
                project_type = await analyzer.detect_project_type(project_path)

                if code_exists or len(directories) > 0:
                    project_exists = True
                    existing_structure = {
                        "code_exists": code_exists,
                        "directories": directories,
                        "project_type": project_type,
                    }
                    logger.info(f"Projeto já existe: tipo={project_type}, diretórios={len(directories)}")
            except Exception as e:
                logger.warning(f"Erro ao verificar projeto existente: {str(e)}")

        # Solicita token de capacidade para criação de arquivos
        capability_token = task.get("capability_token")
        if not capability_token:
            token = self.guardrails.token_manager.generate_token(
                self.agent_id, "file_creation", ["create_directories", "create_files"]
            )
            capability_token = token.token_id

        # Carrega template especializado
        template_base = self._build_prompt("scaffolder", {})

        project_context = ""
        if project_exists:
            project_context = f"""
PROJETO JÁ EXISTE:
- Tipo: {existing_structure.get("project_type", "unknown")}
- Código Existe: {existing_structure.get("code_exists", False)}
- Diretórios Existentes: {json.dumps(existing_structure.get("directories", []), indent=2)}

IMPORTANTE: O projeto já possui estrutura. Apenas complemente com arquivos e diretórios faltantes.
NÃO sobrescreva arquivos existentes. Crie apenas o que está faltando.
"""
        else:
            project_context = "\nIMPORTANTE: Este é um projeto novo. Crie a estrutura completa do zero.\n"

        prompt = f"""
{template_base}

Crie a estrutura completa do projeto baseado em:
ARQUITETURA: {json.dumps(architecture, indent=2)}
TASKS TÉCNICAS: {json.dumps(technical_tasks, indent=2)}
{project_context}

Suas responsabilidades:
1. Criar estrutura de diretórios completa
2. Gerar arquivos de configuração básicos
3. Configurar ambiente de desenvolvimento
4. Setup de ferramentas (linting, testing, build)
5. Documentação inicial do projeto
6. Scripts de inicialização

ESTRUTURA ESPERADA (formato JSON):
{{
    "project_structure": [
        {{
            "type": "directory|file",
            "path": "src/models/",
            "name": "__init__.py",
            "content": "# File content or null for directories",
            "template_type": "python_package|config_file|readme|dockerfile",
            "permissions": "644|755",
            "description": "Purpose of this file/directory"
        }}
    ],
    "configuration_files": [
        {{
            "file_path": "requirements.txt",
            "content": "fastapi\\nuvicorn\\nsqlalchemy",
            "description": "Python dependencies"
        }}
    ],
    "setup_scripts": [
        {{
            "name": "setup.sh",
            "content": "#!/bin/bash\\n pip install -r requirements.txt",
            "description": "Initial setup script"
        }}
    ],
    "development_tools": {{
        "linter_config": {{}},
        "formatter_config": {{}},
        "test_runner_config": {{}},
        "build_tools": []
    }},
    "documentation": {{
        "readme_content": "# Project Name\\n## Description",
        "api_docs_structure": [],
        "deployment_guide": ""
    }}
}}
"""

        # Obtém temperatura do config para este agente
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent5", {}).get("temperature", 0.2)

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            project_structure = extract_json_from_response(response, model_name=self.agent_id)

            # Cria estrutura real no sistema de arquivos
            created_files = await self._create_project_structure(project_structure, capability_token)

            # Atualiza contexto compartilhado
            await self.shared_context.update_decision(
                self.agent_id, "technical", "project_structure", project_structure, 0.95
            )

            # Lê arquivo do agente anterior
            previous_content = self._read_previous_agent_md(5)

            # Gera nova seção de estrutura do projeto
            new_section = "# ESTRUTURA DO PROJETO\n\n"
            new_section += "## ESTRUTURA CRIADA\n\n"
            new_section += "```\n"
            project_path = self._get_project_path() or "."
            structure_items = project_structure.get("project_structure", [])
            for item in structure_items:
                item_path = item.get("path", "")
                item_name = item.get("name", "")
                if item.get("type") == "directory":
                    new_section += f"{item_path}{item_name}/\n"
                elif item.get("type") == "file":
                    new_section += f"{item_path}{item_name}\n"
            new_section += "```\n\n"
            new_section += "### Ações Realizadas\n\n"
            new_section += "- [x] Estrutura validada\n"
            new_section += "- [x] Novos diretórios criados\n"
            if created_files:
                new_section += f"- [x] {len(created_files)} arquivos/diretórios criados\n"
            if project_structure.get("configuration_files"):
                new_section += (
                    f"- [x] {len(project_structure.get('configuration_files', []))} arquivos de configuração criados\n"
                )
            new_section += "\n"
            if project_path:
                new_section += f"**Endereço Pasta Projeto:** {project_path}\n\n"
            if created_files:
                new_section += "### Arquivos Criados\n\n"
                for file_info in created_files[:20]:
                    new_section += f"- {file_info}\n"
                if len(created_files) > 20:
                    new_section += f"- ... e mais {len(created_files) - 20} arquivos\n"
                new_section += "\n"

            md_content = self._build_accumulative_md(
                previous_content, new_section, "ESTRUTURA DO PROJETO", 5, "Agent 4"
            )
            await self._save_markdown_file("agent5_estrutura.md", md_content)

            return {
                "status": "success",
                "project_structure": project_structure,
                "files_created": created_files,
                "capability_token": capability_token,
            }
        except Exception as e:
            logger.error(f"Erro no parsing da resposta do Scaffolder: {str(e)}")
            raise

    async def _create_project_structure(self, structure: dict[str, any], token: str) -> list[str]:
        """Cria a estrutura de arquivos e diretórios"""
        if not self.guardrails.token_manager.validate_token(token, self.agent_id, "file_creation"):
            raise PermissionError("Token de capacidade inválido para criação de arquivos")

        project_path = self._get_project_path()
        if not project_path:
            project_path = "."

        created_files = []
        base_dir = structure.get("base_directory", project_path)

        for item in structure.get("project_structure", []):
            file_created = self._create_structure_item(item, base_dir)
            if file_created:
                created_files.append(file_created)

        for config_file in structure.get("configuration_files", []):
            file_created = self._create_config_file(config_file, base_dir)
            if file_created:
                created_files.append(file_created)

        return created_files

    def _create_structure_item(self, item: dict[str, any], base_dir: str) -> str | None:
        """Cria um item da estrutura (diretório ou arquivo)"""
        try:
            path = os.path.join(base_dir, item.get("path", ""))
            name = item.get("name", "")
            full_path = os.path.join(path, name) if name else path

            if item["type"] == "directory":
                os.makedirs(full_path, exist_ok=True)
                return f"DIR: {full_path}"
            elif item["type"] == "file":
                if os.path.exists(full_path):
                    logger.info(f"Arquivo já existe, pulando: {full_path}")
                    return None

                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                content = item.get("content", "")
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)

                if "permissions" in item:
                    os.chmod(full_path, int(item["permissions"], 8))

                return f"FILE: {full_path}"
        except Exception as e:
            logger.error(f"Erro criando {item.get('path', '')}/{item.get('name', '')}: {str(e)}")
        return None

    def _create_config_file(self, config_file: dict[str, any], base_dir: str) -> str | None:
        """Cria um arquivo de configuração"""
        try:
            file_path = os.path.join(base_dir, config_file["file_path"])
            if os.path.exists(file_path):
                logger.info(f"Arquivo de configuração já existe, pulando: {file_path}")
                return None

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            content = config_file["content"]
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"CONFIG: {file_path}"
        except Exception as e:
            logger.error(f"Erro criando config {config_file.get('file_path', '')}: {str(e)}")
        return None
