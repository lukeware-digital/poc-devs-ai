import json
import logging
import os

from agents.base_agent import BaseAgent
from utils.json_parser import extract_json_from_response

logger = logging.getLogger("devs-ai")


class Agent6_Desenvolvedor(BaseAgent):
    """Agent-6: Desenvolvedor - Implementa código seguindo tasks técnicas"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
        technical_tasks = task["technical_tasks"]
        project_structure = task["project_structure"]
        architecture = task["architecture"]

        # Lê todos os arquivos .md do projeto
        project_path = self._get_project_path()
        md_files_content = {}
        if project_path:
            md_files = ["specification.md", "user_stories.md", "architecture.md", "technical_tasks.md"]
            for md_file in md_files:
                md_path = os.path.join(project_path, md_file)
                if os.path.exists(md_path):
                    try:
                        with open(md_path, encoding="utf-8") as f:
                            md_files_content[md_file] = f.read()
                        logger.info(f"Arquivo {md_file} lido com sucesso")
                    except Exception as e:
                        logger.warning(f"Erro ao ler {md_file}: {str(e)}")

        # Obtém temperatura do config para este agente
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent6", {}).get("temperature", 0.3)

        # Filtra tasks de desenvolvimento
        dev_tasks = [
            t
            for t in technical_tasks.get("technical_tasks", [])
            if t.get("type") in ["backend", "frontend", "database"]
        ]

        # Limita o número de tasks para processamento simultâneo
        max_tasks = agent_config.get("orchestrator", {}).get("concurrent_agents", 3)
        dev_tasks = dev_tasks[:max_tasks]

        implemented_code = {}
        for dev_task in dev_tasks:
            task_result = await self._implement_single_task(dev_task, project_structure, architecture, temperature)
            implemented_code[dev_task["task_id"]] = task_result

        # Atualiza contexto compartilhado
        await self.shared_context.update_decision(
            self.agent_id, "technical", "implemented_code", implemented_code, 0.85
        )

        # Lê arquivo do agente anterior
        previous_content = self._read_previous_agent_md(6)

        # Gera nova seção de desenvolvimento
        new_section = "# RESUMO DO DESENVOLVIMENTO\n\n"
        new_section += "## CÓDIGO IMPLEMENTADO\n\n"
        new_section += "### Arquivos Criados/Modificados\n\n"
        files_modified = self._get_modified_files(implemented_code)
        total_files = len(files_modified)
        for idx, file_info in enumerate(files_modified, 1):
            file_path = file_info.get("file_path", "N/A")
            action = file_info.get("action", "modify")
            task_id = file_info.get("task_id", "N/A")
            new_section += f"{idx}. **{file_path}**\n"
            new_section += f"   - Ação: {action}\n"
            new_section += f"   - Task: {task_id}\n"
            new_section += "   - Status: ✅ Concluído\n\n"
        new_section += "\n### Resumo das Implementações\n\n"
        new_section += f"- **Total de Arquivos:** {total_files}\n"
        new_section += f"- **Tasks Implementadas:** {len(implemented_code)}\n"
        new_section += "- **Funcionalidades Implementadas:**\n"
        for task_id in implemented_code.keys():
            new_section += f"  - {task_id}\n"
        project_path = self._get_project_path()
        if project_path:
            new_section += f"\n**Endereço Pasta Projeto:** {project_path}\n"

        md_content = self._build_accumulative_md(
            previous_content, new_section, "RESUMO DO DESENVOLVIMENTO", 6, "Agent 5"
        )
        await self._save_markdown_file("agent6_desenvolvimento.md", md_content)

        return {
            "status": "success",
            "implemented_tasks": list(implemented_code.keys()),
            "code_results": implemented_code,
            "files_modified": files_modified,
        }

    async def _implement_single_task(
        self,
        task: dict[str, any],
        project_structure: dict[str, any],
        architecture: dict[str, any],
        temperature: float,
    ) -> dict[str, any]:
        """Implementa uma única task técnica"""
        template_base = self._build_prompt("developer", {})
        project_path = self._get_project_path()

        md_context = self._read_md_files(project_path) if project_path else ""
        existing_code_context = self._analyze_existing_code(project_path) if project_path else ""

        prompt = self._build_implementation_prompt(
            template_base, task, project_structure, architecture, md_context, existing_code_context
        )

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            implementation = extract_json_from_response(response, model_name=self.agent_id)
            await self._apply_code_changes(implementation)
            return implementation
        except Exception as e:
            logger.error(f"Erro no parsing da implementação para task {task['task_id']}: {str(e)}")
            return self._create_fallback_implementation(task)

    def _read_md_files(self, project_path: str) -> str:
        """Lê arquivo markdown do agente anterior (agent5_estrutura.md)"""
        previous_content = self._read_previous_agent_md(6)
        return previous_content

    def _analyze_existing_code(self, project_path: str) -> str:
        """Analisa arquivos de código existentes no projeto"""
        try:
            from pathlib import Path

            project_path_obj = Path(project_path)
            existing_files = self._collect_code_files(project_path_obj)

            if existing_files:
                return self._format_code_context(existing_files)
        except Exception as e:
            logger.warning(f"Erro ao analisar arquivos existentes: {str(e)}")
        return ""

    def _collect_code_files(self, project_path_obj) -> list[dict[str, str]]:
        """Coleta arquivos de código do projeto"""
        code_extensions = {".py", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".php", ".cpp", ".c", ".cs"}
        existing_files = []

        for ext in code_extensions:
            for code_file in project_path_obj.rglob(f"*{ext}"):
                if code_file.is_file() and not any(part.startswith(".") for part in code_file.parts):
                    file_info = self._read_code_file(code_file, project_path_obj)
                    if file_info:
                        existing_files.append(file_info)
                        if len(existing_files) >= 10:
                            break
            if len(existing_files) >= 10:
                break
        return existing_files

    def _read_code_file(self, code_file, project_path_obj) -> dict[str, str] | None:
        """Lê um arquivo de código e retorna informações"""
        try:
            with open(code_file, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if len(content) > 0:
                    rel_path = str(code_file.relative_to(project_path_obj))
                    return {"path": rel_path, "content": content[:2000]}
        except Exception:
            pass
        return None

    def _format_code_context(self, existing_files: list[dict[str, str]]) -> str:
        """Formata o contexto dos arquivos de código"""
        existing_code_context = "\n\n## Arquivos de Código Existentes no Projeto:\n\n"
        for file_info in existing_files[:10]:
            existing_code_context += f"### {file_info['path']}\n```\n{file_info['content']}\n```\n\n"
        logger.info(f"Analisados {len(existing_files)} arquivos de código existentes")
        return existing_code_context

    def _build_implementation_prompt(
        self,
        template_base: str,
        task: dict[str, any],
        project_structure: dict[str, any],
        architecture: dict[str, any],
        md_context: str,
        existing_code_context: str,
    ) -> str:
        """Constrói o prompt para implementação"""
        return f"""
{template_base}

Implemente a seguinte task:
TASK: {json.dumps(task, indent=2)}
ESTRUTURA DO PROJETO: {json.dumps(project_structure, indent=2)}
ARQUITETURA: {json.dumps(architecture, indent=2)}
CONTEXTO DOS ARQUIVOS .MD DO PROJETO:{md_context}
{existing_code_context}

IMPORTANTE: Se arquivos de código já existem, analise-os e modifique apenas o necessário.
Não recrie arquivos que já existem, apenas adicione ou modifique funcionalidades conforme a task.

Requisitos:
1. Gere código limpo e bem estruturado
2. Siga padrões da arquitetura definida
3. Inclua tratamentos de erro adequados
4. Adicione comentários quando necessário
5. Considere os critérios de aceitação
6. Siga as convenções da linguagem/stack

RESPOSTA EM JSON:
{{
    "task_id": "{task["task_id"]}",
    "files_created_modified": [
        {{
            "file_path": "src/main.py",
            "content": "código completo aqui",
            "action": "create|modify",
            "description": "Descrição das mudanças"
        }}
    ],
    "dependencies_added": [],
    "tests_suggested": [
        {{
            "test_file": "test_main.py",
            "test_cases": []
        }}
    ],
    "implementation_notes": "Notas sobre decisões de implementação",
    "quality_metrics": {{
        "complexity": "low|medium|high",
        "maintainability": "high",
        "security_considerations": []
    }}
}}
"""

    async def _apply_code_changes(self, implementation: dict[str, any]):
        """Aplica as mudanças de código no sistema de arquivos"""
        # Verifica permissões para modificações de código
        context = {"modified_files": [f["file_path"] for f in implementation.get("files_created_modified", [])]}
        allowed, reason = await self.guardrails.check_permission(self.agent_id, "file_modification", context)
        if not allowed:
            logger.warning(f"Permissão negada para modificar arquivos: {reason}")
            return

        project_path = self._get_project_path()
        if not project_path:
            project_path = "."

        for file_change in implementation.get("files_created_modified", []):
            try:
                file_path = file_change["file_path"]
                full_path = os.path.join(project_path, file_path) if not os.path.isabs(file_path) else file_path

                # Verifica se arquivo já existe
                file_exists = os.path.exists(full_path)
                if file_exists and file_change.get("action") == "create":
                    logger.info(f"Arquivo já existe, alterando ação para 'modify': {file_path}")
                    file_change["action"] = "modify"

                if not file_path.startswith(("src/", "app/", "lib/", "tests/", "./")):
                    # Permite arquivos na raiz do projeto também
                    if "/" not in file_path or file_path.startswith("."):
                        pass
                    else:
                        logger.warning(f"Tentativa de modificar arquivo fora do diretório de código: {file_path}")
                        continue

                content = file_change["content"]
                action = file_change.get("action", "create")

                if action == "create":
                    # Cria diretório pai se não existir
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"Arquivo {file_path} {action} com sucesso")
            except Exception as e:
                logger.error(f"Erro aplicando mudança em {file_change.get('file_path', '')}: {str(e)}")

    def _get_modified_files(self, implemented_code: dict[str, any]) -> list[str]:
        """Extrai lista de arquivos modificados do resultado da implementação"""
        files = []
        for task_id, result in implemented_code.items():
            for file_change in result.get("files_created_modified", []):
                files.append(
                    {
                        "file_path": file_change["file_path"],
                        "action": file_change.get("action", "modify"),
                        "task_id": task_id,
                    }
                )
        return files

    def _create_fallback_implementation(self, task: dict[str, any]) -> dict[str, any]:
        """Cria uma implementação simples de fallback quando o parsing falha"""
        return {
            "task_id": task["task_id"],
            "files_created_modified": [
                {
                    "file_path": f"src/fallback_{task['task_id'].lower().replace('-', '_')}.py",
                    "content": '# Implementação de fallback - necessita revisão humana\nprint("Hello World")',
                    "action": "create",
                    "description": "Implementação simples de fallback",
                }
            ],
            "implementation_notes": "Esta é uma implementação de fallback. Necessita revisão e complementação.",
            "quality_metrics": {
                "complexity": "low",
                "maintainability": "medium",
                "security_considerations": ["Necessita revisão de segurança"],
            },
        }
