import json
import logging
import os
from datetime import datetime

from agents.base_agent import BaseAgent
from utils.markdown_parser import extract_structured_data_from_markdown

logger = logging.getLogger("devs-ai")


class Agent8_Finalizador(BaseAgent):
    """Agent-8: Finalizador - Refatora, documenta e entrega"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
        implemented_code = task.get("implemented_code", {})
        code_review = task.get("code_review", {})
        project_structure = task.get("project_structure", {})
        technical_tasks = task.get("technical_tasks", {})
        repository_url = task.get("repository_url")
        access_token = task.get("access_token")

        # Verifica se existe code_review.md
        project_path = self._get_project_path()
        code_review_file = os.path.join(project_path, "code_review.md") if project_path else None
        has_code_review = code_review_file and os.path.exists(code_review_file)

        # Obtém temperatura do config para este agente
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent8", {}).get("temperature", 0.4)

        if has_code_review:
            return await self._handle_code_review_loop(code_review_file, implemented_code, code_review, temperature)
        else:
            return await self._handle_final_delivery(
                implemented_code,
                project_structure,
                technical_tasks,
                temperature,
                project_path,
                repository_url,
                access_token,
            )

    async def _handle_code_review_loop(
        self, code_review_file: str, implemented_code: dict[str, any], code_review: dict[str, any], temperature: float
    ) -> dict[str, any]:
        """Lida com o loop de code review"""
        corrections_applied = await self._apply_review_corrections(implemented_code, code_review, temperature)

        # Lê arquivo do agente anterior para atualizar com correções
        previous_content = self._read_previous_agent_md(8)

        # Gera seção de correções aplicadas
        new_section = "# CORREÇÕES APLICADAS\n\n"
        new_section += "## Ajustes Realizados\n\n"
        for task_id, correction in corrections_applied.items():
            if correction.get("no_corrections_needed"):
                new_section += f"- [x] {task_id} - Nenhuma correção necessária - Status: ✅\n"
            else:
                corrections = correction.get("corrections_applied", [])
                new_section += f"- [x] {task_id} - {len(corrections)} correções aplicadas - Status: ✅\n"
        new_section += "\n**Status:** Correções aplicadas, retornando para code review.\n"

        md_content = self._build_accumulative_md(previous_content, new_section, "CORREÇÕES APLICADAS", 8, "Agent 7")
        await self._save_markdown_file("agent8_correcoes.md", md_content)

        try:
            os.remove(code_review_file)
            logger.info(f"Arquivo code_review.md deletado: {code_review_file}")
        except Exception as e:
            logger.error(f"Erro ao deletar code_review.md: {str(e)}")

        return {
            "status": "success",
            "corrections_applied": corrections_applied,
            "code_review_deleted": True,
            "should_loop_back": True,
        }

    async def _handle_final_delivery(
        self,
        implemented_code: dict[str, any],
        project_structure: dict[str, any],
        technical_tasks: dict[str, any],
        temperature: float,
        project_path: str | None,
        repository_url: str | None,
        access_token: str | None,
    ) -> dict[str, any]:
        """Lida com a entrega final do projeto"""
        documentation = await self._generate_comprehensive_documentation(
            implemented_code, project_structure, technical_tasks, temperature
        )

        delivery_package = await self._prepare_final_delivery({}, documentation, project_structure)

        if project_path and repository_url and access_token:
            await self._commit_and_push_changes(project_path, repository_url, access_token)

        await self.shared_context.update_decision(self.agent_id, "quality", "final_delivery", delivery_package, 0.95)

        await self.shared_context.update_decision(
            self.agent_id,
            "project",
            "completion_status",
            {"status": "completed", "timestamp": datetime.utcnow()},
            1.0,
        )

        # Lê arquivo do agente anterior
        previous_content = self._read_previous_agent_md(8)

        # Gera nova seção de entrega final
        new_section = "# ENTREGA FINAL\n\n"
        new_section += "## CORREÇÕES APLICADAS\n\n"
        corrections_count = len(delivery_package.get("project_summary", {}).get("corrections_applied", 0))
        new_section += "### Ajustes Realizados\n\n"
        if corrections_count > 0:
            new_section += f"- [x] {corrections_count} correções aplicadas - Status: ✅\n"
        else:
            new_section += "- [x] Nenhuma correção necessária - Status: ✅\n"
        new_section += "\n"

        new_section += "## DOCUMENTAÇÃO FINAL\n\n"
        new_section += "### Arquivos Entregues\n\n"
        if documentation:
            for _doc_type, doc_info in documentation.items():
                if isinstance(doc_info, dict) and "file_path" in doc_info:
                    new_section += f"- {doc_info.get('file_path', 'N/A')}\n"
        new_section += "\n"

        project_summary = delivery_package.get("project_summary", {})
        new_section += "### Resumo do Projeto\n\n"
        new_section += f"- **Total de Tasks:** {project_summary.get('total_tasks', 0)}\n"
        new_section += f"- **Correções Aplicadas:** {project_summary.get('corrections_applied', 0)}\n"
        new_section += f"- **Arquivos de Documentação:** {project_summary.get('documentation_files', 0)}\n"
        new_section += f"- **Estrutura do Projeto:** {project_summary.get('project_structure', 0)} itens\n"
        new_section += "\n"

        quality_metrics = delivery_package.get("quality_metrics", {})
        new_section += "### Métricas de Qualidade\n\n"
        new_section += f"- **Taxa de Aprovação:** {quality_metrics.get('approval_rate', 0):.1f}%\n"
        new_section += f"- **Score Médio:** {quality_metrics.get('average_score', 0):.2f}\n"
        new_section += f"- **Total de Issues:** {quality_metrics.get('total_issues', 0)}\n"
        new_section += f"- **Issues Críticas:** {quality_metrics.get('critical_issues', 0)}\n"
        new_section += f"- **Nota de Qualidade:** {quality_metrics.get('quality_grade', 'N/A')}\n"
        new_section += "\n"

        new_section += "### Instruções de Uso\n\n"
        if project_path:
            new_section += f"**Endereço Pasta Projeto:** {project_path}\n\n"
        new_section += "Para executar o projeto, siga as instruções no README.md gerado.\n\n"

        new_section += "### Próximos Passos\n\n"
        next_steps = delivery_package.get("next_steps_recommendations", [])
        for step in next_steps[:5]:
            new_section += f"- {step}\n"
        new_section += "\n"

        maintenance = delivery_package.get("maintenance_considerations", [])
        if maintenance:
            new_section += "### Considerações de Manutenção\n\n"
            for item in maintenance[:5]:
                new_section += f"- {item}\n"
            new_section += "\n"

        new_section += "**Status do Projeto:** ✅ CONCLUÍDO\n"

        md_content = self._build_accumulative_md(previous_content, new_section, "ENTREGA FINAL", 8, "Agent 7")
        await self._save_markdown_file("agent8_final.md", md_content)

        return {
            "status": "success",
            "corrections_applied": {},
            "documentation_generated": documentation,
            "final_delivery": delivery_package,
            "project_complete": True,
            "git_committed": True,
        }

    async def _commit_and_push_changes(self, project_path: str, repository_url: str, access_token: str):
        """Faz commit e push das mudanças"""
        try:
            from services.git_service import GitService

            git_service = GitService()

            await git_service.create_commit(project_path, "Development completed by DEVs AI", agent_id="agent8")
            logger.info("Git commit criado com sucesso")

            await git_service.push_changes(project_path, repository_url, access_token, agent_id="agent8")
            logger.info("Git push realizado com sucesso")

            await self._update_job_status_completed()
        except Exception as e:
            logger.error(f"Erro ao fazer git commit/push: {str(e)}")

    async def _update_job_status_completed(self):
        """Atualiza status do job para concluído"""
        if not hasattr(self.shared_context, "config"):
            return

        from uuid import UUID

        from database.job_repository import JobRepository

        job_id_value = self.shared_context.project_state.get("job_id")
        if not job_id_value:
            return

        if isinstance(job_id_value, dict):
            job_id_value = job_id_value.get("value")

        if isinstance(job_id_value, str):
            job_id = UUID(job_id_value)
        elif isinstance(job_id_value, UUID):
            job_id = job_id_value
        else:
            return

        if job_id:
            await JobRepository.update_job_status(job_id, status="completed", current_step="Concluído", progress=100.0)

    async def _apply_review_corrections(
        self,
        implemented_code: dict[str, any],
        code_review: dict[str, any],
        temperature: float,
    ) -> dict[str, any]:
        """Aplica correções baseadas nas revisões de código"""
        corrections = {}
        if not code_review:
            return corrections
        for task_id, review in code_review.items():
            if not review.get("approved", False) or len(review.get("issues_found", [])) > 0:
                # Aplica correções para tasks não aprovadas ou com issues
                task_corrections = await self._correct_single_task(
                    task_id, implemented_code.get(task_id, {}), review, temperature
                )
                corrections[task_id] = task_corrections
        return corrections

    async def _correct_single_task(
        self,
        task_id: str,
        implementation: dict[str, any],
        review: dict[str, any],
        temperature: float,
    ) -> dict[str, any]:
        """Corrige uma única task baseada na revisão"""
        # Filtra apenas issues que precisam ser corrigidas
        issues_to_fix = [
            issue for issue in review.get("issues_found", []) if issue.get("priority") in ["must_fix", "should_fix"]
        ]

        if not issues_to_fix:
            return {"no_corrections_needed": True}

        # Carrega template especializado
        template_base = self._build_prompt("developer", {})

        prompt = f"""
{template_base}

Corrija os problemas identificados na revisão:
TASK: {task_id}
IMPLEMENTAÇÃO ORIGINAL: {json.dumps(implementation, indent=2)}
REVISÃO: {json.dumps(review, indent=2)}

Correções necessárias:
{json.dumps(issues_to_fix, indent=2)}

Gere a versão corrigida seguindo:
1. Corrija todos os issues de prioridade 'must_fix'
2. Considere as sugestões de melhoria
3. Mantenha a funcionalidade existente
4. Melhore a qualidade sem quebrar funcionalidades

RESPOSTA EM MARKDOWN (mesmo formato da implementação original):

## Task ID
{task_id}

## Files Created/Modified

### src/main.py
**File Path:** src/main.py
**Action:** modify
**Description:** Correções aplicadas baseadas na revisão
**Content:**
```python
código corrigido aqui
```

---

## Corrections Applied

### Correction 1
**Issue Description:** Descrição do issue corrigido
**Correction Description:** Como foi corrigido
**File Affected:** src/main.py

---

## Improvements Made
- Lista de melhorias aplicadas
"""

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            correction = extract_structured_data_from_markdown(response, model_name=self.agent_id)

            # Aplica as correções
            await self._apply_code_changes(correction)

            return correction
        except Exception as e:
            logger.error(f"Erro aplicando correções para task {task_id}: {str(e)}")
            return {"error_applying_corrections": str(e)}

    async def _generate_comprehensive_documentation(
        self,
        implemented_code: dict[str, any],
        project_structure: dict[str, any],
        technical_tasks: dict[str, any],
        temperature: float,
    ) -> dict[str, any]:
        """Gera documentação abrangente do projeto"""
        # Carrega template especializado
        template_base = self._build_prompt("finalizer", {})

        prompt = f"""
{template_base}

Crie documentação completa para:
CÓDIGO IMPLEMENTADO: {json.dumps(implemented_code, indent=2)}
ESTRUTURA DO PROJETO: {json.dumps(project_structure, indent=2)}
TASKS TÉCNICAS: {json.dumps(technical_tasks, indent=2)}

Gere a seguinte documentação:
1. README principal
2. Guia de instalação e setup
3. Guia de desenvolvimento
4. Documentação da API (se aplicável)
5. Guia de deploy
6. Documentação de arquitetura
7. Troubleshooting comum

FORMATO MARKDOWN:

## Readme Main
**File Path:** README.md
**Content:**
```
# Conteúdo completo do README
```

---

## Installation Guide
**File Path:** docs/INSTALLATION.md
**Content:**
```
Guia de instalação
```

---

## Development Guide
**File Path:** docs/DEVELOPMENT.md
**Content:**
```
Guia para desenvolvedores
```

---

## API Documentation
**File Path:** docs/API.md
**Content:**
```
Documentação da API
```

---

## Deployment Guide
**File Path:** docs/DEPLOYMENT.md
**Content:**
```
Guia de deploy
```

---

## Architecture Documentation
**File Path:** docs/ARCHITECTURE.md
**Content:**
```
Documentação arquitetural
```

---

## Troubleshooting Guide
**File Path:** docs/TROUBLESHOOTING.md
**Content:**
```
Guia de troubleshooting
```

---

## Code Comments Summary
**File Path:** docs/CODE_OVERVIEW.md
**Content:**
```
Visão geral do código
```
"""

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            documentation = extract_structured_data_from_markdown(response, model_name=self.agent_id)
            # Cria os arquivos de documentação
            for _doc_type, doc_info in documentation.items():
                if isinstance(doc_info, dict) and "file_path" in doc_info:
                    file_path = doc_info["file_path"]
                    content = doc_info["content"]
                    try:
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        logger.info(f"Documentação criada: {file_path}")
                    except Exception as e:
                        logger.error(f"Erro criando documentação {file_path}: {str(e)}")
            return documentation
        except Exception as e:
            logger.error(f"Erro gerando documentação: {str(e)}")
            return {"error_generating_documentation": str(e)}

    async def _prepare_final_delivery(
        self,
        corrections_applied: dict[str, any],
        documentation: dict[str, any],
        project_structure: dict[str, any],
    ) -> dict[str, any]:
        """Prepara o pacote final de entrega"""
        # Gera relatório final
        final_report = {
            "delivery_timestamp": datetime.utcnow().isoformat(),
            "project_summary": {
                "total_tasks": len(corrections_applied) + len([k for k in corrections_applied if k]),
                "corrections_applied": len(corrections_applied),
                "documentation_files": len(documentation),
                "project_structure": len(project_structure.get("project_structure", [])),
            },
            "quality_metrics": await self._get_latest_quality_metrics(),
            "next_steps_recommendations": [
                "Executar suite de testes completa",
                "Revisão final por desenvolvedor humano",
                "Deploy em ambiente de staging",
                "Testes de integração e carga",
            ],
            "maintenance_considerations": [
                "Monitorar performance em produção",
                "Plano de escalabilidade",
                "Backup e recovery procedures",
                "Atualizações de segurança",
            ],
        }

        # Cria arquivo de relatório final
        report_path = "delivery/FINAL_REPORT.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(final_report, f, indent=2, ensure_ascii=False)
            logger.info(f"Relatório final criado: {report_path}")
        except Exception as e:
            logger.error(f"Erro criando relatório final: {str(e)}")

        return final_report

    async def _get_latest_quality_metrics(self) -> dict[str, any]:
        """Obtém as métricas de qualidade mais recentes do contexto compartilhado"""
        try:
            return await self.shared_context.get_context_for_agent(self.agent_id, ["quality.quality_metrics"]).get(
                "quality.quality_metrics", {}
            )
        except Exception:
            return {
                "approval_rate": 0,
                "average_score": 0,
                "total_issues": 0,
                "critical_issues": 0,
                "quality_grade": "F",
            }

    async def _apply_code_changes(self, implementation: dict[str, any]):
        """Aplica mudanças de código (reutilizado do Agent6)"""
        for file_change in implementation.get("files_created_modified", []):
            try:
                file_path = file_change["file_path"]
                content = file_change["content"]
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                logger.error(f"Erro aplicando correção em {file_change.get('file_path', '')}: {str(e)}")
