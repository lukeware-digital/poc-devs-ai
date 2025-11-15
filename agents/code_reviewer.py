import json
import logging

import numpy as np

from agents.base_agent import BaseAgent
from utils.markdown_parser import extract_structured_data_from_markdown

logger = logging.getLogger("devs-ai")


class Agent7_CodeReviewer(BaseAgent):
    """Agent-7: Code Reviewer - Revisa código gerado"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:  # noqa: C901
        implemented_code = task["implemented_code"]
        technical_tasks = task["technical_tasks"]
        architecture = task["architecture"]

        # Obtém temperatura do config para este agente
        agent_config = getattr(self.shared_context, "config", {})
        temperature = agent_config.get("agents", {}).get("agent7", {}).get("temperature", 0.1)

        review_results = {}
        for task_id, implementation in implemented_code.items():
            review = await self._review_single_implementation(
                task_id, implementation, technical_tasks, architecture, temperature
            )
            review_results[task_id] = review

        # Calcula métricas gerais de qualidade
        quality_metrics = self._calculate_quality_metrics(review_results)

        # Atualiza contexto compartilhado
        await self.shared_context.update_decision(self.agent_id, "quality", "code_review", review_results, 0.9)
        await self.shared_context.update_decision(self.agent_id, "quality", "quality_metrics", quality_metrics, 0.95)

        # Lê arquivo do agente anterior
        previous_content = self._read_previous_agent_md(7)

        # Gera nova seção de code review
        new_section = "# CODE REVIEW\n\n"
        new_section += "## ANÁLISE GIT\n\n"
        new_section += "### Arquivos Modificados\n\n"
        project_path = self._get_project_path()
        if project_path:
            try:
                import subprocess

                result = subprocess.run(
                    ["git", "diff", "--stat"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    new_section += "```\n"
                    new_section += result.stdout
                    new_section += "```\n\n"
                else:
                    new_section += "*Git diff não disponível*\n\n"
            except Exception:
                new_section += "*Git diff não disponível*\n\n"
        else:
            new_section += "*Git diff não disponível*\n\n"

        approval_status = "✅ Approved" if self._determine_overall_approval(review_results) else "❌ Not Approved"
        new_section += f"## Overall Approval: {approval_status}\n\n"
        new_section += "## Quality Metrics\n\n"
        new_section += f"- **Approval Rate:** {quality_metrics.get('approval_rate', 0):.1f}%\n"
        new_section += f"- **Average Score:** {quality_metrics.get('average_score', 0):.2f}\n"
        new_section += f"- **Total Issues:** {quality_metrics.get('total_issues', 0)}\n"
        new_section += f"- **Critical Issues:** {quality_metrics.get('critical_issues', 0)}\n"
        new_section += f"- **Quality Grade:** {quality_metrics.get('quality_grade', 'N/A')}\n\n"

        new_section += "## Issues Identificados\n\n"
        critical_issues = []
        improvement_issues = []
        for task_id, review in review_results.items():
            for issue in review.get("issues_found", []):
                if issue.get("severity") == "critical":
                    critical_issues.append((task_id, issue))
                else:
                    improvement_issues.append((task_id, issue))

        if critical_issues:
            new_section += "**CRÍTICO:**\n\n"
            for task_id, issue in critical_issues:
                new_section += f"- [ ] {issue.get('description', 'N/A')} ({task_id})\n"
            new_section += "\n"

        if improvement_issues:
            new_section += "**MELHORIA:**\n\n"
            for task_id, issue in improvement_issues[:10]:
                new_section += f"- [ ] {issue.get('description', 'N/A')} ({task_id})\n"
            if len(improvement_issues) > 10:
                new_section += f"- ... e mais {len(improvement_issues) - 10} melhorias\n"
            new_section += "\n"

        new_section += "## RECOMENDAÇÕES\n\n"
        refactorings = []
        optimizations = []
        bugs = []
        for _task_id, review in review_results.items():
            for improvement in review.get("suggested_improvements", []):
                imp_type = improvement.get("type", "")
                if imp_type == "refactor":
                    refactorings.append(improvement.get("description", "N/A"))
                elif imp_type == "optimize":
                    optimizations.append(improvement.get("description", "N/A"))
            for issue in review.get("issues_found", []):
                if issue.get("type") == "bug":
                    bugs.append(issue.get("description", "N/A"))

        if refactorings:
            new_section += "1. **Refatoração Necessária:**\n"
            for ref in refactorings[:5]:
                new_section += f"   - {ref}\n"
            new_section += "\n"

        if optimizations:
            new_section += "2. **Otimizações:**\n"
            for opt in optimizations[:5]:
                new_section += f"   - {opt}\n"
            new_section += "\n"

        if bugs:
            new_section += "3. **Bugs a Corrigir:**\n"
            for bug in bugs[:5]:
                new_section += f"   - {bug}\n"
            new_section += "\n"

        md_content = self._build_accumulative_md(previous_content, new_section, "CODE REVIEW", 7, "Agent 6")
        await self._save_markdown_file("agent7_review.md", md_content)

        return {
            "status": "success",
            "reviews": review_results,
            "quality_metrics": quality_metrics,
            "overall_approval": self._determine_overall_approval(review_results),
        }

    async def _review_single_implementation(
        self,
        task_id: str,
        implementation: dict[str, any],
        technical_tasks: dict[str, any],
        architecture: dict[str, any],
        temperature: float,
    ) -> dict[str, any]:
        """Revisa uma única implementação"""
        # Encontra a task técnica correspondente
        task_spec = {}
        for t in technical_tasks.get("technical_tasks", []):
            if t.get("task_id") == task_id:
                task_spec = t
                break

        # Carrega template especializado
        template_base = self._build_prompt("code_reviewer", {})

        prompt = f"""
{template_base}

Analise a implementação:
TASK ESPECIFICAÇÃO: {json.dumps(task_spec, indent=2)}
IMPLEMENTAÇÃO: {json.dumps(implementation, indent=2)}
PADRÕES ARQUITETURAIS: {json.dumps(architecture, indent=2)}

Análise a ser realizada:
1. QUALIDADE DE CÓDIGO:
   - Legibilidade e clareza
   - Complexidade ciclomática
   - Duplicação de código
   - Convenções de nomenclatura
2. ADERÊNCIA AOS REQUISITOS:
   - Critérios de aceitação atendidos
   - Funcionalidade completa
   - Comportamento esperado
3. SEGURANÇA:
   - Vulnerabilidades potenciais
   - Tratamento de dados sensíveis
   - Validação de entrada
4. PERFORMANCE:
   - Algoritmos eficientes
   - Uso adequado de recursos
   - Possíveis gargalos
5. MANTENABILIDADE:
   - Modularidade
   - Testabilidade
   - Documentação
6. PADRÕES ARQUITETURAIS:
   - Seguimento dos padrões definidos
   - Acoplamento e coesão
   - Separação de responsabilidades

RESPOSTA EM MARKDOWN:

## Task ID
{task_id}

## Overall Score
[0.0 a 10.0]

## Approved
true|false

## Issues Found

### Issue 1
**Type:** bug|security|performance|maintainability|style
**Severity:** low|medium|high|critical
**File:** src/main.py
**Line:** 10
**Description:** Descrição detalhada do problema
**Suggestion:** Sugestão de correção
**Priority:** must_fix|should_fix|could_fix

---

## Suggested Improvements

### Improvement 1
**Type:** refactor|optimize|enhance
**Description:** Descrição da melhoria
**Benefit:** Benefício esperado
**Effort:** low|medium|high

---

## Positive Feedback
- Aspectos bem implementados

## Test Recommendations

### Recommendation 1
**Test Type:** unit|integration|e2e
**Scope:** O que testar
**Priority:** high|medium|low

## Security Assessment
**Vulnerabilities Found:**
- [vulnerabilidade 1]

**Data Handling:** secure|needs_improvement
**Authentication Authorization:** adequate|insufficient

## Performance Assessment
**Efficiency:** efficient|moderate|inefficient
**Bottlenecks Identified:**
- [gargalo 1]

**Optimization Suggestions:**
- [sugestão 1]
"""

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            review = extract_structured_data_from_markdown(response, model_name=self.agent_id)
            return review
        except Exception as e:
            logger.error(f"Erro no parsing da revisão para task {task_id}: {str(e)}")
            # Retorna uma revisão de fallback
            return self._create_fallback_review(task_id)

    def _calculate_quality_metrics(self, review_results: dict[str, any]) -> dict[str, any]:
        """Calcula métricas de qualidade agregadas"""
        total_tasks = len(review_results)
        if total_tasks == 0:
            return {}

        approved_tasks = sum(1 for review in review_results.values() if review.get("approved", False))
        total_issues = sum(len(review.get("issues_found", [])) for review in review_results.values())
        critical_issues = sum(
            1
            for review in review_results.values()
            for issue in review.get("issues_found", [])
            if issue.get("severity") == "critical"
        )
        avg_score = np.mean(
            [
                review.get("overall_score", 0)
                for review in review_results.values()
                if isinstance(review.get("overall_score"), (int, float))
            ]
        )

        return {
            "approval_rate": approved_tasks / total_tasks * 100,
            "average_score": avg_score,
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "issues_per_task": total_issues / total_tasks if total_tasks > 0 else 0,
            "quality_grade": self._assign_quality_grade(avg_score, critical_issues),
        }

    def _assign_quality_grade(self, avg_score: float, critical_issues: int) -> str:
        """Atribui nota de qualidade baseada no score e issues críticas"""
        if critical_issues > 0:
            return "F"
        elif avg_score >= 0.9:
            return "A"
        elif avg_score >= 0.8:
            return "B"
        elif avg_score >= 0.7:
            return "C"
        elif avg_score >= 0.6:
            return "D"
        else:
            return "F"

    def _determine_overall_approval(self, review_results: dict[str, any]) -> bool:
        """Determina se o código geral é aprovado"""
        if not review_results:
            return False

        # Rejeita se houver qualquer task não aprovada
        for review in review_results.values():
            if not review.get("approved", False):
                return False

        # Rejeita se houver issues críticas não tratadas
        for review in review_results.values():
            for issue in review.get("issues_found", []):
                if issue.get("severity") == "critical" and issue.get("priority") == "must_fix":
                    return False

        return True

    def _create_fallback_review(self, task_id: str) -> dict[str, any]:
        """Cria uma revisão simples de fallback quando o parsing falha"""
        return {
            "task_id": task_id,
            "overall_score": 0.5,
            "approved": False,
            "issues_found": [
                {
                    "type": "maintainability",
                    "severity": "medium",
                    "file": "unknown",
                    "line": 0,
                    "description": "Revisão automatizada não foi possível. Necessita revisão humana.",
                    "suggestion": "Realizar revisão manual completa do código.",
                    "priority": "must_fix",
                }
            ],
            "suggested_improvements": [
                {
                    "type": "enhance",
                    "description": "Necessita revisão humana completa",
                    "benefit": "Garantir qualidade do código",
                    "effort": "high",
                }
            ],
            "positive_feedback": ["N/A - Revisão automática falhou"],
            "test_recommendations": [
                {
                    "test_type": "all",
                    "scope": "Todo o código implementado",
                    "priority": "high",
                }
            ],
            "security_assessment": {
                "vulnerabilities_found": ["Necessita revisão de segurança manual"],
                "data_handling": "needs_improvement",
                "authentication_authorization": "insufficient",
            },
            "performance_assessment": {
                "efficiency": "moderate",
                "bottlenecks_identified": ["Não avaliado - necessita revisão humana"],
                "optimization_suggestions": ["Realizar análise de performance manual"],
            },
        }
