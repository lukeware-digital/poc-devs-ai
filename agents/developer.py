import json
import logging
import os

from agents.base_agent import BaseAgent

logger = logging.getLogger("DEVs_AI")


class Agent6_Desenvolvedor(BaseAgent):
    """Agent-6: Desenvolvedor - Implementa código seguindo tasks técnicas"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
        technical_tasks = task["technical_tasks"]
        project_structure = task["project_structure"]
        architecture = task["architecture"]

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

        return {
            "status": "success",
            "implemented_tasks": list(implemented_code.keys()),
            "code_results": implemented_code,
            "files_modified": self._get_modified_files(implemented_code),
        }

    async def _implement_single_task(
        self,
        task: dict[str, any],
        project_structure: dict[str, any],
        architecture: dict[str, any],
        temperature: float,
    ) -> dict[str, any]:
        """Implementa uma única task técnica"""
        prompt = f"""
        Como Desenvolvedor Sênior, implemente a seguinte task:
        TASK: {json.dumps(task, indent=2)}
        ESTRUTURA DO PROJETO: {json.dumps(project_structure, indent=2)}
        ARQUITETURA: {json.dumps(architecture, indent=2)}

        Requisitos:
        1. Gere código limpo e bem estruturado
        2. Siga padrões da arquitetura definida
        3. Inclua tratamentos de erro adequados
        4. Adicione comentários quando necessário
        5. Considere os critérios de aceitação
        6. Siga as convenções da linguagem/stack

        Para tasks de backend (Python):
        - Use type hints
        - Siga PEP8
        - Inclua docstrings
        - Trate exceções adequadamente

        Para tasks de frontend:
        - Use componentes reutilizáveis
        - Trate estados de loading/error
        - Siga padrões de acessibilidade

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

        response = await self.llm.generate_response(prompt, temperature=temperature)

        try:
            implementation = json.loads(response)

            # Aplica as mudanças no sistema de arquivos
            await self._apply_code_changes(implementation)

            return implementation
        except Exception as e:
            logger.error(f"Erro no parsing da implementação para task {task['task_id']}: {str(e)}")
            # Cria implementação de fallback
            return self._create_fallback_implementation(task)

    async def _apply_code_changes(self, implementation: dict[str, any]):
        """Aplica as mudanças de código no sistema de arquivos"""
        # Verifica permissões para modificações de código
        context = {"modified_files": [f["file_path"] for f in implementation.get("files_created_modified", [])]}
        allowed, reason = await self.guardrails.check_permission(self.agent_id, "file_modification", context)
        if not allowed:
            logger.warning(f"Permissão negada para modificar arquivos: {reason}")
            return

        for file_change in implementation.get("files_created_modified", []):
            try:
                file_path = file_change["file_path"]
                if not file_path.startswith(("src/", "app/", "lib/", "tests/")):
                    logger.warning(f"Tentativa de modificar arquivo fora do diretório de código: {file_path}")
                    continue

                content = file_change["content"]
                action = file_change.get("action", "create")

                if action == "create":
                    # Cria diretório pai se não existir
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, "w", encoding="utf-8") as f:
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
