import json
import os
import logging
from datetime import datetime
from typing import Dict, Any

from agents.base_agent import BaseAgent

logger = logging.getLogger("DEVs_AI")


class Agent8_Finalizador(BaseAgent):
    """Agent-8: Finalizador - Refatora, documenta e entrega"""
    
    async def _execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        implemented_code = task.get('implemented_code', {})
        code_review = task.get('code_review', {})
        project_structure = task.get('project_structure', {})
        technical_tasks = task.get('technical_tasks', {})
        
        # Obtém temperatura do config para este agente
        agent_config = getattr(self.shared_context, 'config', {})
        temperature = agent_config.get('agents', {}).get('agent8', {}).get('temperature', 0.4)
        
        # Aplica correções baseadas na revisão
        corrections_applied = await self._apply_review_corrections(
            implemented_code, code_review, temperature
        )
        
        # Gera documentação final
        documentation = await self._generate_comprehensive_documentation(
            implemented_code, project_structure, technical_tasks, temperature
        )
        
        # Prepara entrega final
        delivery_package = await self._prepare_final_delivery(
            corrections_applied, documentation, project_structure
        )
        
        # Atualiza contexto compartilhado
        await self.shared_context.update_decision(
            self.agent_id, 'quality', 'final_delivery', 
            delivery_package, 0.95
        )
        
        # Atualiza estado do projeto para completo
        await self.shared_context.update_decision(
            self.agent_id, 'project', 'completion_status',
            {'status': 'completed', 'timestamp': datetime.utcnow()}, 1.0
        )
        
        return {
            'status': 'success',
            'corrections_applied': corrections_applied,
            'documentation_generated': documentation,
            'final_delivery': delivery_package,
            'project_complete': True
        }
        
    async def _apply_review_corrections(self, implemented_code: Dict[str, Any], 
                                      code_review: Dict[str, Any], temperature: float) -> Dict[str, Any]:
        """Aplica correções baseadas nas revisões de código"""
        corrections = {}
        for task_id, review in code_review.items():
            if not review.get('approved', False) or len(review.get('issues_found', [])) > 0:
                # Aplica correções para tasks não aprovadas ou com issues
                task_corrections = await self._correct_single_task(
                    task_id, implemented_code.get(task_id, {}), review, temperature
                )
                corrections[task_id] = task_corrections
        return corrections
        
    async def _correct_single_task(self, task_id: str, implementation: Dict[str, Any],
                                 review: Dict[str, Any], temperature: float) -> Dict[str, Any]:
        """Corrige uma única task baseada na revisão"""
        # Filtra apenas issues que precisam ser corrigidas
        issues_to_fix = [
            issue for issue in review.get('issues_found', []) 
            if issue.get('priority') in ['must_fix', 'should_fix']
        ]
        
        if not issues_to_fix:
            return {'no_corrections_needed': True}
            
        prompt = f"""
        Como Desenvolvedor Sênior, corrija os problemas identificados na revisão:
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
        
        RESPOSTA EM JSON (mesmo formato da implementação original):
        {{
            "task_id": "{task_id}",
            "files_created_modified": [
                {{
                    "file_path": "src/main.py",
                    "content": "código corrigido aqui",
                    "action": "modify",
                    "description": "Correções aplicadas baseadas na revisão"
                }}
            ],
            "corrections_applied": [
                {{
                    "issue_description": "Descrição do issue corrigido",
                    "correction_description": "Como foi corrigido",
                    "file_affected": "src/main.py"
                }}
            ],
            "improvements_made": [
                "Lista de melhorias aplicadas"
            ]
        }}
        """
        
        response = await self.llm.generate_response(prompt, temperature=temperature)
        
        try:
            correction = json.loads(response)
            
            # Aplica as correções
            await self._apply_code_changes(correction)
            
            return correction
        except Exception as e:
            logger.error(f"Erro aplicando correções para task {task_id}: {str(e)}")
            return {'error_applying_corrections': str(e)}
            
    async def _generate_comprehensive_documentation(self, implemented_code: Dict[str, Any],
                                                  project_structure: Dict[str, Any],
                                                  technical_tasks: Dict[str, Any],
                                                  temperature: float) -> Dict[str, Any]:
        """Gera documentação abrangente do projeto"""
        prompt = f"""
        Como Documentador Técnico, crie documentação completa para:
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
        
        FORMATO JSON:
        {{
            "readme_main": {{
                "file_path": "README.md",
                "content": "# Conteúdo completo do README"
            }},
            "installation_guide": {{
                "file_path": "docs/INSTALLATION.md",
                "content": "Guia de instalação"
            }},
            "development_guide": {{
                "file_path": "docs/DEVELOPMENT.md",
                "content": "Guia para desenvolvedores"
            }},
            "api_documentation": {{
                "file_path": "docs/API.md",
                "content": "Documentação da API"
            }},
            "deployment_guide": {{
                "file_path": "docs/DEPLOYMENT.md",
                "content": "Guia de deploy"
            }},
            "architecture_documentation": {{
                "file_path": "docs/ARCHITECTURE.md",
                "content": "Documentação arquitetural"
            }},
            "troubleshooting_guide": {{
                "file_path": "docs/TROUBLESHOOTING.md",
                "content": "Guia de troubleshooting"
            }},
            "code_comments_summary": {{
                "file_path": "docs/CODE_OVERVIEW.md",
                "content": "Visão geral do código"
            }}
        }}
        """
        
        response = await self.llm.generate_response(prompt, temperature=temperature)
        
        try:
            documentation = json.loads(response)
            # Cria os arquivos de documentação
            for doc_type, doc_info in documentation.items():
                if isinstance(doc_info, dict) and 'file_path' in doc_info:
                    file_path = doc_info['file_path']
                    content = doc_info['content']
                    try:
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.info(f"Documentação criada: {file_path}")
                    except Exception as e:
                        logger.error(f"Erro criando documentação {file_path}: {str(e)}")
            return documentation
        except Exception as e:
            logger.error(f"Erro gerando documentação: {str(e)}")
            return {'error_generating_documentation': str(e)}
            
    async def _prepare_final_delivery(self, corrections_applied: Dict[str, Any],
                                    documentation: Dict[str, Any],
                                    project_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara o pacote final de entrega"""
        # Gera relatório final
        final_report = {
            'delivery_timestamp': datetime.utcnow().isoformat(),
            'project_summary': {
                'total_tasks': len(corrections_applied) + len([k for k in corrections_applied if k]),
                'corrections_applied': len(corrections_applied),
                'documentation_files': len(documentation),
                'project_structure': len(project_structure.get('project_structure', []))
            },
            'quality_metrics': await self._get_latest_quality_metrics(),
            'next_steps_recommendations': [
                "Executar suite de testes completa",
                "Revisão final por desenvolvedor humano",
                "Deploy em ambiente de staging",
                "Testes de integração e carga"
            ],
            'maintenance_considerations': [
                "Monitorar performance em produção",
                "Plano de escalabilidade",
                "Backup e recovery procedures",
                "Atualizações de segurança"
            ]
        }
        
        # Cria arquivo de relatório final
        report_path = "delivery/FINAL_REPORT.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(final_report, f, indent=2, ensure_ascii=False)
            logger.info(f"Relatório final criado: {report_path}")
        except Exception as e:
            logger.error(f"Erro criando relatório final: {str(e)}")
            
        return final_report
        
    async def _get_latest_quality_metrics(self) -> Dict[str, Any]:
        """Obtém as métricas de qualidade mais recentes do contexto compartilhado"""
        try:
            return await self.shared_context.get_context_for_agent(
                self.agent_id, ['quality.quality_metrics']
            ).get('quality.quality_metrics', {})
        except:
            return {
                'approval_rate': 0,
                'average_score': 0,
                'total_issues': 0,
                'critical_issues': 0,
                'quality_grade': 'F'
            }
            
    async def _apply_code_changes(self, implementation: Dict[str, Any]):
        """Aplica mudanças de código (reutilizado do Agent6)"""
        for file_change in implementation.get('files_created_modified', []):
            try:
                file_path = file_change['file_path']
                content = file_change['content']
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                logger.error(f"Erro aplicando correção em {file_change.get('file_path', '')}: {str(e)}")