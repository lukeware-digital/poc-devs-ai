"""
Gerenciador de Contexto Compartilhado - Armazena e gerencia o estado compartilhado entre agentes
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import hashlib
import redis

logger = logging.getLogger("DEVs_AI")

class VersionedStore:
    """
    Armazenamento versionado de dados com histórico de versões
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.memory_store = {}
        self.versions = {}
        self.current_version = 0
        
    def set(self, key: str, value: Any, version: Optional[int] = None) -> int:
        """
        Armazena um valor com versionamento
        
        Args:
            key: Chave de identificação
            value: Valor a ser armazenado
            version: Versão específica (None para nova versão)
            
        Returns:
            Número da versão armazenada
        """
        if version is None:
            version = self.current_version + 1
            self.current_version = version
            
        if key not in self.versions:
            self.versions[key] = []
            
        # Adiciona nova versão
        self.versions[key].append({
            'value': value,
            'version': version,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Mantém apenas as últimas 10 versões em memória
        if len(self.versions[key]) > 10:
            self.versions[key] = self.versions[key][-10:]
            
        # Atualiza valor atual
        self.memory_store[key] = value
        
        # Armazena no Redis se disponível
        if self.redis:
            try:
                redis_key = f"versioned:{key}"
                redis_value = json.dumps({
                    'current_version': version,
                    'value': value,
                    'timestamp': datetime.utcnow().isoformat()
                })
                self.redis.setex(redis_key, 3600, redis_value)  # Expira em 1 hora
                
                # Armazena histórico de versões
                history_key = f"versioned_history:{key}"
                history_value = json.dumps(self.versions[key])
                self.redis.setex(history_key, 86400, history_value)  # Expira em 24 horas
                
            except Exception as e:
                logger.warning(f"Falha ao armazenar no Redis: {str(e)}")
                
        return version
        
    def get(self, key: str, version: Optional[int] = None) -> Optional[Any]:
        """
        Recupera um valor pelo key e versão
        
        Args:
            key: Chave de identificação
            version: Versão específica (None para versão mais recente)
            
        Returns:
            Valor armazenado ou None se não encontrado
        """
        # Primeiro tenta recuperar do Redis
        if self.redis:
            try:
                redis_key = f"versioned:{key}"
                cached_data = self.redis.get(redis_key)
                if cached_data:
                    data = json.loads(cached_data)
                    if version is None or data.get('current_version') == version:
                        return data.get('value')
            except Exception as e:
                logger.warning(f"Falha ao recuperar do Redis: {str(e)}")
        
        # Fallback para memória
        if key not in self.versions or not self.versions[key]:
            return None
            
        if version is None:
            # Retorna a versão mais recente
            return self.versions[key][-1]['value']
            
        # Procura versão específica
        for item in reversed(self.versions[key]):
            if item['version'] == version:
                return item['value']
                
        return None
        
    def get_history(self, key: str, max_versions: int = 5) -> List[Dict[str, Any]]:
        """
        Retorna o histórico de versões para uma chave
        
        Args:
            key: Chave de identificação
            max_versions: Número máximo de versões a retornar
            
        Returns:
            Lista de versões ordenada da mais recente para a mais antiga
        """
        if key not in self.versions:
            return []
            
        # Tenta recuperar do Redis primeiro
        if self.redis:
            try:
                history_key = f"versioned_history:{key}"
                cached_history = self.redis.get(history_key)
                if cached_history:
                    history = json.loads(cached_history)
                    return history[-max_versions:][::-1]  # Ordena da mais recente para mais antiga
            except Exception as e:
                logger.warning(f"Falha ao recuperar histórico do Redis: {str(e)}")
        
        # Fallback para memória
        history = self.versions[key][-max_versions:][::-1]  # Ordena da mais recente para mais antiga
        return history
        
    def delete(self, key: str):
        """
        Remove uma chave e todo seu histórico
        
        Args:
            key: Chave de identificação
        """
        if key in self.versions:
            del self.versions[key]
        if key in self.memory_store:
            del self.memory_store[key]
            
        # Remove do Redis se disponível
        if self.redis:
            try:
                self.redis.delete(f"versioned:{key}")
                self.redis.delete(f"versioned_history:{key}")
            except Exception as e:
                logger.warning(f"Falha ao deletar do Redis: {str(e)}")

class SharedContext:
    """
    Contexto compartilhado entre agentes com versionamento e concorrência controlada
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._updating_completion = False  # Flag para evitar recursão
        
        # Inicializa conexão com Redis se configurado
        self.redis = None
        redis_config = self.config.get('redis', {})
        if redis_config.get('enabled', False):
            try:
                self.redis = redis.Redis(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    db=redis_config.get('db', 1),
                    decode_responses=True,
                    socket_timeout=2,
                    socket_connect_timeout=2
                )
                # Testa conexão
                self.redis.ping()
                logger.info("✅ Conexão com Redis estabelecida para shared context")
            except Exception as e:
                logger.warning(f"⚠️ Falha ao conectar ao Redis: {str(e)}")
                self.redis = None
        
        # Inicializa armazenamentos versionados
        self.architecture_decisions = VersionedStore(self.redis)
        self.tech_constraints = VersionedStore(self.redis)
        self.quality_metrics = VersionedStore(self.redis)
        self.project_state = VersionedStore(self.redis)
        
        # Estado do projeto
        self.project_state.set('current_phase', 'initial')
        self.project_state.set('completion_percentage', 0)
        self.project_state.set('blockers', [])
        self.project_state.set('last_successful_agent', None)
        self.project_state.set('start_time', datetime.utcnow().isoformat())
        
        # Lock para operações concorrentes
        self._lock = asyncio.Lock()
        self._update_counter = 0
        
    async def update_decision(self, agent_id: str, decision_type: str, key: str, 
                            value: Any, confidence: float) -> Dict[str, Any]:
        """
        Atualiza uma decisão no contexto compartilhado
        
        Args:
            agent_id: ID do agente que fez a decisão
            decision_type: Tipo de decisão (architecture, technical, quality)
            key: Chave de identificação
            value: Valor da decisão
            confidence: Nível de confiança (0.0 a 1.0)
            
        Returns:
            Dicionário com detalhes da atualização
        """
        async with self._lock:
            self._update_counter += 1
            
            # Cria registro de decisão
            decision_record = {
                'value': value,
                'agent_id': agent_id,
                'timestamp': datetime.utcnow().isoformat(),
                'confidence': confidence,
                'dependencies': await self._get_current_dependencies(),
                'version_hash': self._generate_version_hash(),
                'update_id': self._update_counter
            }
            
            # Armazena no repositório apropriado
            if decision_type == 'architecture':
                version = self.architecture_decisions.set(key, decision_record)
            elif decision_type == 'technical':
                version = self.tech_constraints.set(key, decision_record)
            elif decision_type == 'quality':
                version = self.quality_metrics.set(key, decision_record)
            elif decision_type == 'project':
                version = self.project_state.set(key, decision_record)
            else:
                raise ValueError(f"Tipo de decisão desconhecido: {decision_type}")
                
            # Atualiza estado do projeto se necessário
            if key == 'completion_status':
                await self._update_completion_percentage(value)
                
            # Registra métricas
            logger.info(f"Decisão atualizada: {decision_type}.{key} (v{version}) por {agent_id} com confiança {confidence:.2f}")
            
            return {
                'status': 'success',
                'decision_type': decision_type,
                'key': key,
                'version': version,
                'agent_id': agent_id,
                'confidence': confidence,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def get_context_for_agent(self, agent_id: str, required_context: List[str]) -> Dict[str, Any]:
        """
        Recupera contexto específico para um agente
        
        Args:
            agent_id: ID do agente
            required_context: Lista de chaves de contexto necessárias
            
        Returns:
            Dicionário com o contexto solicitado
        """
        context = {}
        async with self._lock:
            for context_key in required_context:
                try:
                    if context_key.startswith('architecture.'):
                        key = context_key.split('.', 1)[1]
                        context[context_key] = self.architecture_decisions.get(key)
                    elif context_key.startswith('technical.'):
                        key = context_key.split('.', 1)[1]
                        context[context_key] = self.tech_constraints.get(key)
                    elif context_key.startswith('quality.'):
                        key = context_key.split('.', 1)[1]
                        context[context_key] = self.quality_metrics.get(key)
                    elif context_key.startswith('project.'):
                        key = context_key.split('.', 1)[1]
                        context[context_key] = self.project_state.get(key)
                    else:
                        # Tenta nos diferentes armazenamentos
                        value = (self.architecture_decisions.get(context_key) or
                                self.tech_constraints.get(context_key) or
                                self.quality_metrics.get(context_key) or
                                self.project_state.get(context_key))
                        if value is not None:
                            context[context_key] = value
                except Exception as e:
                    logger.warning(f"Erro ao recuperar contexto {context_key} para {agent_id}: {str(e)}")
                    context[context_key] = None
                    
        return context
    
    async def _get_current_dependencies(self) -> List[str]:
        """
        Obtém dependências atuais do contexto
        
        Returns:
            Lista de dependências no formato "tipo:chave"
        """
        dependencies = []
        
        # Adiciona dependências de arquitetura
        for key in self.architecture_decisions.memory_store:
            if self.architecture_decisions.get(key):
                dependencies.append(f"architecture:{key}")
                
        # Adiciona dependências técnicas
        for key in self.tech_constraints.memory_store:
            if self.tech_constraints.get(key):
                dependencies.append(f"technical:{key}")
                
        return dependencies
    
    def _generate_version_hash(self) -> str:
        """
        Gera um hash único para o estado atual do contexto
        """
        state_str = (
            str(self.project_state.memory_store) +
            str(self.architecture_decisions.memory_store) +
            str(self.tech_constraints.memory_store) +
            str(self.quality_metrics.memory_store) +
            str(self._update_counter)
        )
        return hashlib.sha256(state_str.encode()).hexdigest()[:16]
    
    async def _update_completion_percentage(self, status: Any):
        """
        Atualiza a porcentagem de conclusão do projeto com base no estado atual
        """
        # Evita recursão infinita
        if self._updating_completion:
            return
            
        self._updating_completion = True
        try:
            # Obtém estado atual das fases
            phases = {
                'specification': self.tech_constraints.get('initial_spec') is not None,
                'user_stories': self.tech_constraints.get('user_stories') is not None,
                'architecture': self.architecture_decisions.get('main_architecture') is not None,
                'technical_tasks': self.tech_constraints.get('technical_tasks') is not None,
                'scaffolding': self.tech_constraints.get('project_structure') is not None,
                'implementation': self.tech_constraints.get('implemented_code') is not None,
                'review': self.quality_metrics.get('code_review') is not None,
                'delivery': self.quality_metrics.get('final_delivery') is not None
            }
            
            # Calcula porcentagem com base nas fases completadas
            total_phases = len(phases)
            completed_phases = sum(1 for phase in phases.values() if phase)
            completion_percentage = int((completed_phases / total_phases) * 100)
            
            # Atualiza diretamente no armazenamento sem chamar update_decision
            decision_record = {
                'value': completion_percentage,
                'agent_id': 'system',
                'timestamp': datetime.utcnow().isoformat(),
                'confidence': 1.0,
                'dependencies': [],
                'version_hash': self._generate_version_hash(),
                'update_id': self._update_counter
            }
            self.project_state.set('completion_percentage', decision_record)
            
            # Atualiza fase atual
            current_phase = next((phase for phase, completed in phases.items() 
                                if not completed), 'completed')
            phase_record = {
                'value': current_phase,
                'agent_id': 'system',
                'timestamp': datetime.utcnow().isoformat(),
                'confidence': 1.0,
                'dependencies': [],
                'version_hash': self._generate_version_hash(),
                'update_id': self._update_counter
            }
            self.project_state.set('current_phase', phase_record)
            
        except Exception as e:
            logger.error(f"Erro ao atualizar porcentagem de conclusão: {str(e)}")
        finally:
            self._updating_completion = False
    
    def get_project_status(self) -> Dict[str, Any]:
        """
        Retorna o status atual do projeto
        """
        try:
            return {
                'current_phase': self.project_state.get('current_phase'),
                'completion_percentage': self.project_state.get('completion_percentage'),
                'blockers': self.project_state.get('blockers'),
                'last_successful_agent': self.project_state.get('last_successful_agent'),
                'start_time': self.project_state.get('start_time'),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Erro ao obter status do projeto: {str(e)}")
            return {
                'current_phase': 'error',
                'completion_percentage': 0,
                'blockers': [f'Erro interno: {str(e)}'],
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_context_snapshot(self) -> Dict[str, Any]:
        """
        Retorna um snapshot completo do contexto atual
        """
        return {
            'architecture_decisions': self.architecture_decisions.memory_store,
            'tech_constraints': self.tech_constraints.memory_store,
            'quality_metrics': self.quality_metrics.memory_store,
            'project_state': self.project_state.memory_store,
            'snapshot_timestamp': datetime.utcnow().isoformat()
        }
    
    async def rollback_to_version(self, decision_type: str, key: str, target_version: int) -> bool:
        """
        Reverte uma decisão para uma versão anterior
        
        Args:
            decision_type: Tipo de decisão (architecture, technical, quality, project)
            key: Chave de identificação
            target_version: Versão alvo para rollback
            
        Returns:
            True se o rollback foi bem-sucedido, False caso contrário
        """
        async with self._lock:
            try:
                # Obtém o histórico da decisão
                if decision_type == 'architecture':
                    history = self.architecture_decisions.get_history(key)
                elif decision_type == 'technical':
                    history = self.tech_constraints.get_history(key)
                elif decision_type == 'quality':
                    history = self.quality_metrics.get_history(key)
                elif decision_type == 'project':
                    history = self.project_state.get_history(key)
                else:
                    return False
                    
                # Procura a versão alvo
                target_record = None
                for record in history:
                    if record.get('version') == target_version:
                        target_record = record
                        break
                        
                if not target_record:
                    return False
                    
                # Realiza o rollback
                value = target_record.get('value')
                if decision_type == 'architecture':
                    self.architecture_decisions.set(key, value, target_version)
                elif decision_type == 'technical':
                    self.tech_constraints.set(key, value, target_version)
                elif decision_type == 'quality':
                    self.quality_metrics.set(key, value, target_version)
                elif decision_type == 'project':
                    self.project_state.set(key, value, target_version)
                    
                logger.info(f"Rollback bem-sucedido para {decision_type}.{key} versão {target_version}")
                return True
                
            except Exception as e:
                logger.error(f"Falha no rollback para {decision_type}.{key} versão {target_version}: {str(e)}")
                return False