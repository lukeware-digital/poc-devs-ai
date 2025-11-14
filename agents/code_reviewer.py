import json
import logging

import numpy as np

from agents.base_agent import BaseAgent

logger = logging.getLogger("DEVs_AI")


class Agent7_CodeReviewer(BaseAgent):
    """Agent-7: Code Reviewer - Revisa código gerado"""

    async def _execute_task(self, task: dict[str, any]) -> dict[str, any]:
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

RESPOSTA EM JSON:
{{
    "task_id": "{task_id}",
    "overall_score": 0.0,
    "approved": false,
    "issues_found": [
        {{
            "type": "bug|security|performance|maintainability|style",
            "severity": "low|medium|high|critical",
            "file": "src/main.py",
            "line": 10,
            "description": "Descrição detalhada do problema",
            "suggestion": "Sugestão de correção",
            "priority": "must_fix|should_fix|could_fix"
        }}
    ],
    "suggested_improvements": [
        {{
            "type": "refactor|optimize|enhance",
            "description": "Descrição da melhoria",
            "benefit": "Benefício esperado",
            "effort": "low|medium|high"
        }}
    ],
    "positive_feedback": [
        "Aspectos bem implementados"
    ],
    "test_recommendations": [
        {{
            "test_type": "unit|integration|e2e",
            "scope": "O que testar",
            "priority": "high|medium|low"
        }}
    ],
    "security_assessment": {{
        "vulnerabilities_found": [],
        "data_handling": "secure|needs_improvement",
        "authentication_authorization": "adequate|insufficient"
    }},
    "performance_assessment": {{
        "efficiency": "efficient|moderate|inefficient",
        "bottlenecks_identified": [],
        "optimization_suggestions": []
    }}
}}
"""

        response = await self._generate_llm_response(prompt, temperature=temperature)

        try:
            review = json.loads(response)
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
