"""
Sistema Avançado de Recuperação de Falhas
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from shared_context.context_manager import SharedContext
from .workflow import ProjectState

logger = logging.getLogger("DEVs_AI")

class RecoveryStrategy(Enum):
    """Estratégias de recuperação disponíveis"""
    RETRY_WITH_ADJUSTED_PARAMS = "retry_with_adjusted_params"
    ROLLBACK_AND_INCREMENTAL_GENERATION = "rollback_and_incremental_generation"
    ALTERNATE_REVIEWER = "alternate_reviewer"
    ISOLATE_AND_RESTART = "isolate_and_restart"
    GENERIC_RECOVERY = "generic_recovery"
    HUMAN_INTERVENTION = "human_intervention"

class FailureType(Enum):
    """Tipos de falhas identificáveis"""
    VALIDATION_FAILURE = "validation_failure"
    CODE_GENERATION_FAILURE = "code_generation_failure"
    REVIEW_FAILURE = "review_failure"
    SYSTEM_FAILURE = "system_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_FAILURE = "network_failure"
    PERMISSION_FAILURE = "permission_failure"
    UNKNOWN_FAILURE = "unknown_failure"

class AdvancedRecoverySystem:
    """
    Sistema avançado de recuperação de falhas com estratégias específicas para diferentes cenários
    """
    
    def __init__(self, orchestrator: Any, shared_context: SharedContext):
        self.orchestrator = orchestrator
        self.shared_context = shared_context
        self.recovery_strategies = {
            FailureType.VALIDATION_FAILURE: self._handle_validation_failure,
            FailureType.CODE_GENERATION_FAILURE: self._handle_code_generation_failure,
            FailureType.REVIEW_FAILURE: self._handle_review_failure,
            FailureType.SYSTEM_FAILURE: self._handle_system_failure,
            FailureType.RESOURCE_EXHAUSTION: self._handle_resource_exhaustion,
            FailureType.NETWORK_FAILURE: self._handle_network_failure,
            FailureType.PERMISSION_FAILURE: self._handle_permission_failure,
            FailureType.UNKNOWN_FAILURE: self._handle_generic_failure
        }
        self.recovery_history = []
        
    async def handle_failure(self, failure_type: FailureType, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gerencia uma falha usando a estratégia apropriada
        
        Args:
            failure_type: Tipo de falha identificada
            context: Contexto da falha com detalhes relevantes
            
        Returns:
            Dicionário com a estratégia de recuperação e parâmetros
        """
        try:
            strategy_func = self.recovery_strategies.get(failure_type, self._handle_generic_failure)
            recovery_plan = await strategy_func(context)
            
            # Registra histórico de recuperação
            self._record_recovery_attempt(failure_type, context, recovery_plan)
            
            return recovery_plan
            
        except Exception as e:
            logger.error(f"Erro ao executar estratégia de recuperação: {str(e)}")
            # Estratégia de fallback
            return await self._handle_generic_failure(context)
    
    async def _handle_validation_failure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lida com falhas de validação (ex: parsing de JSON, validação de schema)
        """
        agent_id = context.get('agent_id')
        error = context.get('error', '')
        failed_payload = context.get('payload', '')
        
        # Estratégia: Reexecutar com temperatura ajustada + simplificação
        recovery_params = {
            'strategy': RecoveryStrategy.RETRY_WITH_ADJUSTED_PARAMS,
            'new_temperature': 0.1,
            'simplify_payload': True,
            'max_retries': 3,
            'fallback_format': 'simplified_json'
        }
        
        # Ajustes específicos por agente
        if agent_id in ['agent1', 'agent2', 'agent4']:
            recovery_params['prompt_template'] = 'simplified_validation'
        elif agent_id in ['agent6', 'agent7']:
            recovery_params['code_format'] = 'minimal'
            
        logger.info(f"Recuperando falha de validação para {agent_id} com estratégia: {recovery_params['strategy']}")
        return recovery_params
    
    async def _handle_code_generation_failure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lida com falhas na geração de código
        """
        task_id = context.get('task_id')
        file_path = context.get('file_path')
        error = context.get('error', '')
        
        # Estratégia: Rollback para última versão estável + geração incremental
        recovery_params = {
            'strategy': RecoveryStrategy.ROLLBACK_AND_INCREMENTAL_GENERATION,
            'rollback_target': 'last_stable_commit',
            'incremental_steps': True,
            'max_file_size': 200,  # KB
            'focus_critical_path': True
        }
        
        # Se o erro indica um problema de sintaxe específico
        if 'syntax error' in error.lower() or 'indentation' in error.lower():
            recovery_params['fix_strategy'] = 'syntax_correction'
            recovery_params['new_temperature'] = 0.05
            
        # Se o erro indica um problema de lógica
        elif 'logic error' in error.lower() or 'bug' in error.lower():
            recovery_params['fix_strategy'] = 'logic_verification'
            recovery_params['add_tests'] = True
            
        logger.info(f"Recuperando falha de geração de código para task {task_id} com estratégia: {recovery_params['strategy']}")
        return recovery_params
    
    async def _handle_review_failure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lida com falhas na revisão de código
        """
        task_id = context.get('task_id')
        review_result = context.get('review_result', {})
        error = context.get('error', '')
        
        # Estratégia: Revisão por agente alternativo + redução de complexidade
        recovery_params = {
            'strategy': RecoveryStrategy.ALTERNATE_REVIEWER,
            'fallback_reviewer': 'agent7_backup',
            'complexity_reduction': True,
            'focus_critical_issues_only': True,
            'max_issues_per_review': 5
        }
        
        # Se a revisão falhou devido a muitos problemas
        if review_result.get('total_issues', 0) > 10:
            recovery_params['batch_review'] = True
            recovery_params['issues_per_batch'] = 3
            
        logger.info(f"Recuperando falha de revisão para task {task_id} com estratégia: {recovery_params['strategy']}")
        return recovery_params
    
    async def _handle_system_failure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lida com falhas de sistema (ex: crashes, deadlocks)
        """
        component = context.get('component', 'unknown')
        error = context.get('error', '')
        failing_agents = context.get('failing_agents', [])
        
        # Estratégia: Isolamento do agente + realocação de recursos
        recovery_params = {
            'strategy': RecoveryStrategy.ISOLATE_AND_RESTART,
            'isolated_agents': failing_agents,
            'resource_reallocation': True,
            'graceful_degradation': True,
            'max_restart_attempts': 2
        }
        
        # Se é uma falha crítica no sistema
        if 'critical' in error.lower() or 'fatal' in error.lower():
            recovery_params['emergency_mode'] = True
            recovery_params['preserve_state'] = True
            
        logger.warning(f"Recuperando falha de sistema no componente {component} com estratégia: {recovery_params['strategy']}")
        return recovery_params
    
    async def _handle_resource_exhaustion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lida com esgotamento de recursos (memória, CPU, etc.)
        """
        resource_type = context.get('resource_type', 'unknown')
        usage_percent = context.get('usage_percent', 0)
        
        # Estratégia: Redução de carga + liberação de recursos
        recovery_params = {
            'strategy': RecoveryStrategy.GENERIC_RECOVERY,
            'actions': [
                'reduce_batch_size',
                'release_cached_resources',
                'pause_non_critical_agents',
                'enable_streaming_processing'
            ],
            'resource_limits': {
                'memory_usage_percent': 70,
                'cpu_usage_percent': 80,
                'concurrent_tasks': max(1, self.orchestrator.config.get('orchestrator', {}).get('concurrent_agents', 3) // 2)
            }
        }
        
        # Ajustes específicos por tipo de recurso
        if resource_type == 'memory':
            recovery_params['actions'].extend(['clear_llm_cache', 'optimize_context_window'])
        elif resource_type == 'gpu':
            recovery_params['actions'].append('reduce_model_parallelism')
            
        logger.warning(f"Recuperando esgotamento de {resource_type} ({usage_percent}%) com estratégia: {recovery_params['strategy']}")
        return recovery_params
    
    async def _handle_network_failure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lida com falhas de rede (conectividade com serviços externos)
        """
        service = context.get('service', 'unknown')
        error = context.get('error', '')
        
        # Estratégia: Retentativas progressivas + fallback para cache
        recovery_params = {
            'strategy': RecoveryStrategy.GENERIC_RECOVERY,
            'actions': [
                'enable_offline_mode',
                'use_cached_responses',
                'reduce_retry_backoff',
                'notify_service_disruption'
            ],
            'retry_config': {
                'max_attempts': 5,
                'initial_delay': 1,
                'backoff_factor': 2,
                'max_delay': 30
            },
            'fallback_to_cache': True
        }
        
        # Serviços críticos requerem estratégias mais robustas
        if service in ['ollama', 'chromadb', 'redis']:
            recovery_params['actions'].append('activate_emergency_cache')
            recovery_params['timeout_extension'] = 60
            
        logger.warning(f"Recuperando falha de rede no serviço {service} com estratégia: {recovery_params['strategy']}")
        return recovery_params
    
    async def _handle_permission_failure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lida com falhas de permissão (capability tokens, acesso a arquivos)
        """
        operation = context.get('operation', 'unknown')
        resource = context.get('resource', 'unknown')
        error = context.get('error', '')
        
        # Estratégia: Revalidação de permissões + solicitação de novos tokens
        recovery_params = {
            'strategy': RecoveryStrategy.GENERIC_RECOVERY,
            'actions': [
                'regenerate_capability_token',
                'verify_resource_permissions',
                'request_permission_elevation'
            ],
            'token_regeneration': {
                'force_refresh': True,
                'extended_scope': True,
                'extended_ttl': 600  # 10 minutos
            }
        }
        
        # Operações críticas requerem supervisão humana
        if operation in ['file_deletion', 'system_command', 'network_request']:
            recovery_params['actions'].append('request_human_approval')
            recovery_params['strategy'] = RecoveryStrategy.HUMAN_INTERVENTION
            
        logger.warning(f"Recuperando falha de permissão na operação {operation} para recurso {resource} com estratégia: {recovery_params['strategy']}")
        return recovery_params
    
    async def _handle_generic_failure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estratégia genérica para falhas não especificadas
        """
        error = context.get('error', 'Erro não especificado')
        agent_id = context.get('agent_id', 'unknown')
        
        # Estratégia genérica com múltiplas ações
        recovery_params = {
            'strategy': RecoveryStrategy.GENERIC_RECOVERY,
            'actions': [
                'log_failure_details',
                'notify_supervisor',
                'pause_affected_workflow',
                'suggest_manual_intervention'
            ],
            'timeout': 300,  # 5 minutos
            'max_attempts': 3,
            'fallback_to_human': True
        }
        
        logger.error(f"Falha não categorizada no agente {agent_id}: {error}. Usando estratégia genérica.")
        return recovery_params
    
    def _record_recovery_attempt(self, failure_type: FailureType, context: Dict[str, Any], recovery_plan: Dict[str, Any]):
        """Registra uma tentativa de recuperação no histórico"""
        record = {
            'timestamp': datetime.utcnow().isoformat(),
            'failure_type': failure_type.value,
            'context': context,
            'recovery_plan': recovery_plan,
            'agent_id': context.get('agent_id', 'unknown')
        }
        self.recovery_history.append(record)
        
        # Mantém apenas os últimos 100 registros para evitar crescimento excessivo
        if len(self.recovery_history) > 100:
            self.recovery_history.pop(0)
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas sobre recuperações de falhas"""
        if not self.recovery_history:
            return {
                'total_attempts': 0,
                'success_rate': 0,
                'most_common_failures': [],
                'average_recovery_time': 0
            }
            
        # Contagem de tipos de falha
        failure_counts = {}
        for record in self.recovery_history:
            failure_type = record['failure_type']
            failure_counts[failure_type] = failure_counts.get(failure_type, 0) + 1
            
        # Ordena por frequência
        most_common_failures = sorted(
            failure_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return {
            'total_attempts': len(self.recovery_history),
            'most_common_failures': most_common_failures,
            'last_recovery_timestamp': self.recovery_history[-1]['timestamp']
        }
    
    async def suggest_preventive_measures(self) -> List[str]:
        """
        Sugere medidas preventivas baseadas no histórico de falhas
        """
        stats = self.get_recovery_statistics()
        suggestions = []
        
        # Analisa padrões no histórico
        failure_patterns = {}
        for record in self.recovery_history:
            failure_type = record['failure_type']
            agent_id = record['agent_id']
            key = (failure_type, agent_id)
            failure_patterns[key] = failure_patterns.get(key, 0) + 1
        
        # Gera sugestões baseadas nos padrões
        for (failure_type, agent_id), count in failure_patterns.items():
            if count > 3:  # Mais de 3 ocorrências
                if failure_type == FailureType.VALIDATION_FAILURE.value:
                    suggestions.append(f"Revisar prompts do {agent_id} para melhorar validação de JSON")
                elif failure_type == FailureType.CODE_GENERATION_FAILURE.value:
                    suggestions.append(f"Ajustar temperatura do {agent_id} para gerar código mais estável")
                elif failure_type == FailureType.REVIEW_FAILURE.value:
                    suggestions.append(f"Aumentar critérios de qualidade para revisões do {agent_id}")
                elif failure_type == FailureType.NETWORK_FAILURE.value:
                    suggestions.append(f"Melhorar tolerância a falhas de rede para serviços utilizados pelo {agent_id}")
        
        # Sugestões genéricas se necessário
        if not suggestions:
            suggestions = [
                "Monitorar uso de recursos do sistema regularmente",
                "Manter backups frequentes do estado do projeto",
                "Configurar alertas para detecção precoce de falhas",
                "Realizar testes de estresse periódicos no sistema"
            ]
            
        return suggestions