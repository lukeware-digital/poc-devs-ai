import json
import logging
import os

from agents.base_agent import BaseAgent

logger = logging.getLogger("DEVs_AI")


class Agent5_Scaffolder(BaseAgent):
    """Agent-5: Scaffolder - Cria estrutura do projeto"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
        architecture = task["architecture"]
        technical_tasks = task["technical_tasks"]

        # Solicita token de capacidade para criação de arquivos
        capability_token = task.get("capability_token")
        if not capability_token:
            token = self.guardrails.token_manager.generate_token(
                self.agent_id, "file_creation", ["create_directories", "create_files"]
            )
            capability_token = token.token_id

        # Carrega template especializado
        template_base = self._build_prompt("scaffolder", {})

        prompt = f"""
{template_base}

Crie a estrutura completa do projeto baseado em:
ARQUITETURA: {json.dumps(architecture, indent=2)}
TASKS TÉCNICAS: {json.dumps(technical_tasks, indent=2)}

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
            project_structure = json.loads(response)

            # Cria estrutura real no sistema de arquivos
            created_files = await self._create_project_structure(project_structure, capability_token)

            # Atualiza contexto compartilhado
            await self.shared_context.update_decision(
                self.agent_id, "technical", "project_structure", project_structure, 0.95
            )

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
        # Verifica se o token é válido
        if not self.guardrails.token_manager.validate_token(token, self.agent_id, "file_creation"):
            raise PermissionError("Token de capacidade inválido para criação de arquivos")

        created_files = []
        base_dir = structure.get("base_directory", "project")

        # Cria estrutura de diretórios e arquivos
        for item in structure.get("project_structure", []):
            try:
                # Combina path e name para obter o caminho completo
                path = os.path.join(base_dir, item.get("path", ""))
                name = item.get("name", "")
                full_path = os.path.join(path, name) if name else path

                if item["type"] == "directory":
                    # Cria diretório
                    os.makedirs(full_path, exist_ok=True)
                    created_files.append(f"DIR: {full_path}")
                elif item["type"] == "file":
                    # Cria diretório pai se não existir
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)

                    # Cria arquivo
                    content = item.get("content", "")
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    created_files.append(f"FILE: {full_path}")

                    # Define permissões se especificado
                    if "permissions" in item:
                        os.chmod(full_path, int(item["permissions"], 8))

            except Exception as e:
                logger.error(f"Erro criando {item.get('path', '')}/{item.get('name', '')}: {str(e)}")
                continue

        # Cria arquivos de configuração
        for config_file in structure.get("configuration_files", []):
            try:
                file_path = os.path.join(base_dir, config_file["file_path"])
                # Cria diretório pai se não existir
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                content = config_file["content"]
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                created_files.append(f"CONFIG: {file_path}")
            except Exception as e:
                logger.error(f"Erro criando config {config_file.get('file_path', '')}: {str(e)}")

        return created_files
