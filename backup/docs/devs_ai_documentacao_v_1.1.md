# DEVs AI — Documentação Técnica Completa
## Versão 1.1 (Melhorada)

## 1. Visão Geral
O DEVs AI é uma plataforma multiagente projetada para automatizar o ciclo completo de desenvolvimento de software utilizando agentes de IA especializados, comunicação estruturada, execução local com modelos open-source e ferramentas modernas como LangGraph, ChromaDB e Python.

A arquitetura foi construída para ser totalmente local, modular, expansível e segura, permitindo evolução incremental dos agentes, das capacidades e dos fluxos de execução. **Novidade na V1.1**: Sistema de contexto compartilhado e mecanismos avançados de recuperação de falhas.

---

## 2. Objetivo do Sistema
Fornecer uma equipe de desenvolvimento totalmente automatizada composta por agentes inteligentes que assumem papéis tradicionais de engenharia de software: análise, arquitetura, product management, desenvolvimento, revisão e refatoração. O sistema recebe uma instrução humana e gera um software completo, versionado, revisado e documentado em repositório Git, com capacidade de recuperação automática de falhas.

---

## 3. Fundamentos da Arquitetura
A arquitetura emprega múltiplos agentes autônomos que cooperam entre si, seguindo um fluxo ordenado, seguro e auditável. Todos os agentes rodam de maneira isolada, comunicando-se via mensagens JSON validadas e utilizando LLMs locais.

### Stack Principal (Atualizado)
- **Linguagem:** Python 3.10+
- **Orquestração Multiagente:** LangGraph (com circuit breakers)
- **Modelos LLM:** Ollama, LLMStudio ou via HuggingFace (todos locais)
- **Banco vetorial:** ChromaDB
- **Banco vetorial alternativo:** VectorDB (compatível)
- **Banco relacional:** PostgreSQL
- **Cache e fila:** Redis (Streams) + Sistema de cache para LLM
- **Validação:** PydanticAI
- **Guardrails:** Sistema próprio com capability tokens
- **RAG:** Sistema interno de recuperação semântica
- **Execução do código gerado:** via ambiente sandboxizado duplo
- **Monitoramento:** Métricas em tempo real por agente
- **Interface:** Painel de supervisão humana

---

## 4. Modelos de LLM Local (Open-Source)
O sistema usa exclusivamente modelos locais para garantir privacidade e autonomia:

### Opções Suportadas
- **Ollama** com modelos como Llama3, Mistral e Qwen
- **LLMStudio** (treinamento e execução local)
- **HuggingFace Transformers** (offline, via download manual)

### Otimizações de Performance (Novo)
- **Caching agressivo**: Sistema de cache hierárquico para respostas LLM
- **Modelos especializados por agente**: Cada agente utiliza o modelo mais adequado para sua função
- **Quantização adaptativa**: Nível de quantização ajustado dinamicamente conforme carga do sistema
- **Batch processing**: Processamento em lote para operações não críticas

### Camada de Abstração LLM (Melhorada)
Todos os agentes acessam LLMs através de uma camada de abstração que gerencia:
- temperatura adaptativa
- top_p dinâmico
- prevenção de repetição
- contexto RAG enriquecido
- cache de respostas com TTL inteligente
- fallback automático em caso de falha

```python
# Exemplo da camada de abstração LLM com cache
class LLMAbstractLayer:
    def __init__(self):
        self.cache = LLMLocalCache()
        self.fallback_models = ["llama3:8b", "mistral:7b", "phi3:3.8b"]
    
    def generate_response(self, prompt: str, temperature: float, context: dict = None):
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        
        # Verifica cache primeiro
        cached = self.cache.get_cached_response(prompt_hash, temperature)
        if cached:
            return cached
        
        # Tenta modelo primário com fallback
        for model in [config.primary_model] + self.fallback_models:
            try:
                response = self._call_model(model, prompt, temperature, context)
                # Armazena no cache com TTL baseado na criticidade
                ttl = 86400 if "critical" not in context else 3600
                self.cache.set_cached_response(prompt_hash, temperature, response, ttl)
                return response
            except Exception as e:
                logger.warning(f"Falha no modelo {model}: {str(e)}")
                continue
        
        raise LLMException("Todos os modelos falharam")
```

---

## 5. RAG — Retrieval-Augmented Generation (Aprimorado)
O RAG é parte central do sistema com melhorias significativas na V1.1.

### Componentes RAG Avançados
- **ChromaDB** como principal armazenamento vetorial
- **VectorDB alternativo** opcional para failover
- **Mecanismo de embedding especializado**:
  - Modelos genéricos (bge-small, all-MiniLM) para documentos
  - **Modelos fine-tunados em código-fonte** para recuperação técnica
- **Pipeline RAG híbrido** (busca semântica + keyword matching)

### Fluxo RAG Aprimorado
1. Usuário envia tarefa
2. Sistema determina tipo de consulta (técnica/não técnica)
3. RAG especializado seleciona modelo de embedding adequado
4. Recupera documentos relevantes com reranking adaptativo
5. Aplica filtro de contexto para remover informações irrelevantes
6. Injeta documentos no prompt com marcação estruturada
7. LLM gera resposta contextualizada com referências explícitas
8. Resposta é validada contra fontes recuperadas

### Estratégias de Indexação (Novo)
```python
class RAGIndexer:
    def index_technical_document(self, doc_type: str, content: str):
        """Indexação com processamento especializado por tipo de documento"""
        processors = {
            'code': self._process_code_document,
            'architecture': self._process_arch_document,
            'requirement': self._process_req_document,
            'commit': self._process_commit_document
        }
        
        processor = processors.get(doc_type, self._process_generic_document)
        structured_content = processor(content)
        
        # Gera múltiplos embeddings para diferentes aspectos
        embeddings = {
            'semantic': self.semantic_embedder.embed(structured_content['main_text']),
            'technical': self.technical_embedder.embed(structured_content['code_blocks']),
            'contextual': self.context_embedder.embed(structured_content['context'])
        }
        
        self.chroma_db.add_document(
            content=structured_content,
            embeddings=embeddings,
            metadata={'type': doc_type, 'indexed_at': datetime.utcnow()}
        )
```

---

## 6. PydanticAI (Validação Estruturada com Fallback)
Todos os dados trafegados pelo sistema passam por modelos definidos em Pydantic, com mecanismos de recuperação inteligentes.

### Sistema de Fallback para Validação (Novo)
- **Primeira tentativa**: Validação estrita com Pydantic
- **Segunda tentativa**: Correção automática com LLM especializado
- **Terceira tentativa**: Simplificação do payload para campos essenciais
- **Quarta tentativa**: Solicitação de intervenção humana via painel de supervisão

### Exemplo de Schema com Mecanismo de Fallback
```python
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, Dict, any

class TaskSpecification(BaseModel):
    task_id: str
    description: str
    acceptance_criteria: list[str]
    estimated_complexity: int  # 1-10
    technical_constraints: Optional[list[str]] = None
    fallback_attempts: int = 0
    
    @field_validator('estimated_complexity')
    @classmethod
    def validate_complexity(cls, v):
        if not 1 <= v <= 10:
            raise ValueError('Complexidade deve estar entre 1 e 10')
        return v
    
    @model_validator(mode='after')
    def handle_validation_failure(self) -> 'TaskSpecification':
        """Mecanismo de fallback integrado ao modelo"""
        try:
            # Tenta validação completa
            return self
        except Exception as e:
            self.fallback_attempts += 1
            
            if self.fallback_attempts > 2:
                # Solicita intervenção humana
                supervisor_alert(
                    f"Falha repetida de validação para task {self.task_id}",
                    context=self.model_dump(),
                    error=str(e)
                )
            
            # Tenta correção automática
            corrected = auto_correct_task_spec(self.model_dump(), str(e))
            return TaskSpecification(**corrected)
```

---

## 7. Guardrails (Regras de Segurança com Capability Tokens)
Os guardrails garantem que nenhum agente execute ações indesejadas ou inseguras, com sistema aprimorado de capability tokens.

### Capability Tokens (Novo)
- **Mecanismo**: Tokens temporários e específicos para operações sensíveis
- **Validação**: Cada operação crítica requer token válido gerado pelo MCP
- **Escopo**: Tokens são limitados a operações específicas e tempos de vida curtos
- **Auditoria**: Todos os tokens são registrados com contexto de uso

### Fluxo de Capability Tokens
1. Agente solicita permissão para operação crítica (ex: git commit)
2. MCP avalia solicitação com base em contexto e histórico
3. MCP gera capability token com escopo específico e TTL curto
4. Agente executa operação usando o token
5. Token é invalidado após uso ou expiração
6. Operação é registrada no log de auditoria com referência ao token

### Guardrails Aprimorados
- **Níveis de Autonomia com Supervisão Dinâmica**:
  - Autonomia Baixa: Agents 1, 2, 4 (sempre supervisionados)
  - Autonomia Média: Agents 5, 6 (supervisão em operações críticas)
  - Autonomia Alta: Agents 7, 8 (supervisão por amostragem e em caso de anomalias)
- **Sandboxing Duplo**: Ambiente de execução isolado dentro de container Docker adicional
- **Network Isolation**: Nenhuma interface de rede disponível nos containers dos agentes

---

## 8. Sistema de Contexto Compartilhado (Novo - V1.1)
### Visão Geral
Sistema centralizado que mantém estado compartilhado entre todos os agentes, garantindo coerência e consistência nas decisões.

### Componentes Principais
- **Shared Context Manager**: Gerencia acesso concorrente ao contexto
- **Decision Registry**: Armazena decisões críticas com metadados
- **Context Versioning**: Versionamento do estado compartilhado para rollback
- **Conflict Resolution**: Mecanismo para resolver conflitos de contexto

### Estrutura do Contexto Compartilhado
```python
class SharedContext:
    def __init__(self):
        # Decisões arquiteturais (Agent-3)
        self.architecture_decisions = VersionedStore()
        
        # Restrições técnicas (Agent-4)
        self.tech_constraints = VersionedStore()
        
        # Métricas de qualidade (Agent-7)
        self.quality_metrics = VersionedStore()
        
        # Estado do projeto
        self.project_state = {
            'current_phase': 'requirements',
            'completion_percentage': 0,
            'blockers': [],
            'last_successful_agent': None
        }
    
    def update_decision(self, agent_id: str, decision_type: str, key: str, value: any, confidence: float):
        """Atualiza uma decisão com metadados completos"""
        decision_record = {
            'value': value,
            'agent_id': agent_id,
            'timestamp': datetime.utcnow(),
            'confidence': confidence,
            'dependencies': self._get_current_dependencies(),
            'version': self._generate_version_hash()
        }
        
        if decision_type == 'architecture':
            self.architecture_decisions.set(key, decision_record)
        elif decision_type == 'technical':
            self.tech_constraints.set(key, decision_record)
        # ... outros tipos
    
    def get_context_for_agent(self, agent_id: str, required_context: list[str]) -> dict:
        """Retorna contexto relevante para um agente específico"""
        agent_context = {}
        
        for context_key in required_context:
            # Busca no contexto compartilhado com fallback para defaults
            value = self._retrieve_context_value(context_key, agent_id)
            agent_context[context_key] = value
        
        return agent_context
```

---

## 9. Mecanismo de Recuperação de Falhas (Novo - V1.1)
### Visão Geral
Sistema robusto para detectar, isolar e recuperar-se de falhas em qualquer ponto do fluxo de execução.

### Estratégias de Recuperação
- **Circuit Breakers no LangGraph**: Detecta padrões de falha e pausa execução
- **Fallback Agents**: Agentes especializados em recuperação para cada tipo de agente principal
- **Rollback Versionado**: Retorna estado do projeto para último ponto consistente
- **Degradação Graciosa**: Continua operação com funcionalidade reduzida em caso de falha parcial

### Implementação no LangGraph
```python
from langgraph.graph import StateGraph, END

def create_recovery_aware_graph():
    workflow = StateGraph(ProjectState)
    
    # Nós principais do fluxo
    workflow.add_node("agent1", agent1_node)
    workflow.add_node("agent2", agent2_node)
    # ... outros agentes
    
    # Nós de recuperação
    workflow.add_node("fallback_agent1", fallback_agent1_node)
    workflow.add_node("rollback_state", rollback_state_node)
    workflow.add_node("human_supervisor", human_supervisor_node)
    
    # Condições de falha
    def check_failure(state):
        if state.last_operation.success:
            return "continue"
        elif state.failure_count < MAX_AUTO_RETRIES:
            return "auto_recovery"
        else:
            return "human_intervention"
    
    # Conexões com lógica de recuperação
    workflow.add_conditional_edges(
        "agent1",
        check_failure,
        {
            "continue": "agent2",
            "auto_recovery": "fallback_agent1",
            "human_intervention": "human_supervisor"
        }
    )
    
    workflow.add_edge("fallback_agent1", "agent1")
    workflow.add_edge("rollback_state", "agent1")
    
    workflow.set_entry_point("agent1")
    return workflow.compile()
```

### Estratégias por Tipo de Falha
| Tipo de Falha | Estratégia de Recuperação | Agentes Afetados |
|---------------|---------------------------|------------------|
| Falha de Validação | Reexecução com temperatura ajustada + simplificação do payload | 1, 2, 4 |
| Falha de Geração de Código | Rollback para última versão estável + geração incremental | 5, 6 |
| Falha de Revisão | Revisão por agente alternativo + redução de complexidade | 7 |
| Falha de Finalização | Separação de tarefas + finalização parcial | 8 |
| Falha de Sistema | Isolamento do agente + realocação de recursos | Todos |

---

## 10. Interface de Supervisão Humana (Novo - V1.1)
### Visão Geral
Painel web para intervenção humana em pontos críticos, monitoramento do sistema e ajustes de parâmetros em tempo real.

### Funcionalidades Principais
- **Visão em Tempo Real**: Estado atual de cada agente e progresso do projeto
- **Intervenção Manual**: Capacidade de aprovar/rejeitar decisões críticas
- **Ajuste de Parâmetros**: Modificação de temperatura, top_p e outros parâmetros por agente
- **Forçar Rollback**: Reverter estado do projeto para versões anteriores
- **Modo Pausa**: Suspender execução para análise detalhada
- **Alertas Inteligentes**: Notificações para padrões incomuns ou decisões de alta criticidade

### Integração com o Fluxo Principal
```python
class HumanSupervisor:
    def __init__(self):
        self.alert_queue = deque()
        self.pending_approvals = {}
    
    def requires_supervision(self, agent_id: str, operation: str, context: dict) -> bool:
        """Determina se uma operação requer supervisão humana"""
        # Regras baseadas em criticidade, histórico e confiança
        critical_operations = ['git_push', 'database_schema_change', 'api_breaking_change']
        
        if operation in critical_operations:
            return True
        
        if context.get('confidence', 1.0) < 0.7:
            return True
        
        # Verifica histórico de falhas do agente
        failure_rate = self._get_agent_failure_rate(agent_id)
        if failure_rate > 0.3:
            return True
        
        return False
    
    def request_approval(self, agent_id: str, operation: str, context: dict, timeout=300):
        """Solicita aprovação humana para operação crítica"""
        approval_id = str(uuid.uuid4())
        self.pending_approvals[approval_id] = {
            'agent_id': agent_id,
            'operation': operation,
            'context': context,
            'requested_at': datetime.utcnow(),
            'timeout': timeout,
            'status': 'pending'
        }
        
        # Envia notificação para interface web
        self._notify_supervisor_interface(approval_id, context)
        
        return approval_id
```

---

## 11. Monitoramento e Métricas (Novo - V1.1)
### Sistema de Métricas em Tempo Real
- **Performance por Agente**: Tempo de resposta, taxa de sucesso/falha
- **Qualidade de Saída**: Validação Pydantic, consistência lógica
- **Recursos do Sistema**: Uso de CPU, memória, GPU
- **Progresso do Projeto**: Percentual concluído, bloqueadores
- **Evolução do Contexto**: Mudanças significativas no shared context

### Painel de Monitoramento
```python
class MetricsCollector:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=1)
        self.metrics_history = {}
    
    def record_agent_metrics(self, agent_id: str, metrics: dict):
        """Registra métricas para um agente específico"""
        timestamp = datetime.utcnow().isoformat()
        key = f"metrics:{agent_id}:{timestamp}"
        
        # Armazena no Redis para análise em tempo real
        self.redis.hset(key, mapping={
            'timestamp': timestamp,
            'success_rate': metrics.get('success_rate', 0),
            'avg_response_time': metrics.get('avg_response_time', 0),
            'validation_failures': metrics.get('validation_failures', 0),
            'context_switches': metrics.get('context_switches', 0)
        })
        
        # Mantém histórico em memória para anomalias
        if agent_id not in self.metrics_history:
            self.metrics_history[agent_id] = deque(maxlen=100)
        
        self.metrics_history[agent_id].append({
            'timestamp': timestamp,
            **metrics
        })
        
        # Detecta anomalias
        self._detect_anomalies(agent_id)
    
    def _detect_anomalies(self, agent_id: str):
        """Detecta padrões anômalos nas métricas"""
        if len(self.metrics_history[agent_id]) < 10:
            return
        
        # Calcula métricas de tendência
        recent_metrics = list(self.metrics_history[agent_id])[-10:]
        success_rates = [m['success_rate'] for m in recent_metrics]
        
        if np.mean(success_rates) < 0.5 and np.std(success_rates) > 0.2:
            # Anomalia detectada - alerta supervisor
            anomaly_score = 1 - np.mean(success_rates)
            self._alert_anomaly(agent_id, "falling_success_rate", anomaly_score)
```

---

## 12. Atualização das Seções Existentes

### 8. Tipos de Agentes e Suas Funções (Atualizado)
**Agent-3 — Arquiteto (V1.1) - AGORA IMPLEMENTADO**
- Entrada: spec + histórias do usuário
- Saída: 
  - Documento de arquitetura (`architecture.json`)
  - Diagrama de componentes (PlantUML)
  - Escolha de protocolos e fluxos de dados
  - Decisões não funcionais (escalabilidade, segurança)
- Integração: Grava decisões no Shared Context para uso dos demais agentes
- Temperatura: 0.2 (alta precisão)

**Todos os agentes atualizados com:**
- Integração com Shared Context
- Suporte a Capability Tokens para operações críticas
- Mecanismos de fallback nativos
- Registro de métricas para monitoramento

### 9. Orquestração com LangGraph (Atualizado)
**Fluxo Geral Aprimorado no LangGraph**
```
User → Agent-1 → Agent-2 → Agent-3 → Agent-4 → Agent-5 → Agent-6 → Agent-7 → Agent-8 → User
          ↑         ↑         ↑         ↑         ↑         ↑         ↑         ↑
          └─── Recovery System & Human Supervision Interface ────────────────────┘
```

**Estados Mantidos Aprimorados**
- mensagens com histórico completo
- shared context versionado
- logs estruturados com níveis de criticidade
- validações com histórico de tentativas
- estado entre agentes com checkpoint automático
- métricas de performance em tempo real

### 12. Fluxo Completo Aprimorado (V1.1)
1. Usuário envia descrição através da interface
2. System avalia necessidade de supervisão inicial
3. Agent-1 gera spec com validação Pydantic
4. Agent-2 gera histórias com critérios de aceite
5. Agent-3 define arquitetura e padrões
6. Agent-4 cria tasks técnicas e define stack
7. Agent-5 gera estrutura do projeto inicial
8. Agent-6 implementa código com testes
9. Agent-7 revisa código e sugere melhorias
10. Agent-8 aplica correções e finaliza entrega
11. Sistema gera relatório de qualidade e deploy recommendation
12. Interface notifica usuário com link para repositório final

**Em qualquer etapa**:
- Falhas disparam circuit breakers
- Sistema tenta recuperação automática (até 3 tentativas)
- Persistência de checkpoint a cada etapa bem-sucedida
- Interface de supervisão permite intervenção humana

---

## 13. Estrutura de Pastas do Repositório (Atualizada)
```
/devs-ai
 ├── agents/
 │    ├── core/               # Componentes compartilhados pelos agentes
 │    ├── agent1/             # Clarificador e Analista
 │    ├── agent2/             # Product Manager
 │    ├── agent3/             # Arquiteto (V1.1)
 │    ├── agent4/             # Tech Lead
 │    ├── agent5/             # Scaffolder
 │    ├── agent6/             # Desenvolvedor
 │    ├── agent7/             # Code Reviewer
 │    ├── agent8/             # Refatorador e Finalizador
 │    └── fallback/           # Agentes especializados em recuperação
 ├── orchestrator/
 │    ├── langgraph_flow.py   # Definição do fluxo principal
 │    ├── recovery_system.py  # Sistema de recuperação de falhas
 │    └── state_manager.py    # Gerenciamento de estado compartilhado
 ├── shared_context/          # Sistema de contexto compartilhado
 ├── supervision/             # Interface de supervisão humana
 │    ├── web_dashboard/      # Painel web React
 │    └── api_endpoints.py    # API para integração
 ├── rag/
 │    ├── indexers/           # Indexadores especializados
 │    ├── retrievers/         # Recuperadores por tipo de documento
 │    └── rerankers/          # Re-rankeadores especializados
 ├── db/
 │    ├── chroma/             # Configuração ChromaDB
 │    ├── postgres/           # Schema e migrações
 │    └── redis/              # Configuração de cache e streams
 ├── guardrails/
 │    ├── capability_tokens/  # Sistema de tokens de capacidade
 │    ├── sandbox/            # Implementação de sandbox duplo
 │    └── validators/         # Validadores especializados
 ├── monitoring/              # Sistema de métricas e monitoramento
 ├── schemas/                 # Modelos Pydantic com fallback
 ├── prompts/                 # Templates de prompts otimizados
 ├── models/                  # Modelos de ML especializados
 ├── tests/
 │    ├── unit/               # Testes unitários
 │    ├── integration/        # Testes de integração
 │    └── failure_scenarios/  # Cenários de falha e recuperação
 ├── docs/
 ├── diagrams/
 ├── scripts/                 # Scripts de utilidade e inicialização
 ├── config/                  # Configurações por ambiente
 ├── docker-compose.yml
 ├── requirements.txt
 ├── .env.example
 ├── SECURITY.md              # Política de segurança detalhada
 └── README.md
```

---

## 14. Regras de Segurança e Guardrails (Atualizadas)
- **Princípio do Mínimo Privilégio**: Cada agente tem apenas as permissões necessárias
- **Isolamento Completo**: Nenhum agente acessa internet externa ou recursos fora do workspace
- **Sandboxing Duplo**: Execução em container Docker dentro de ambiente virtualizado
- **Capability Tokens**: Operações críticas requerem tokens específicos e temporários
- **Git somente via MCP**: Todas as operações Git passam pelo Machine Control Protocol
- **Auditoria Completa**: Todo acesso e operação registrados com contexto detalhado
- **Network Isolation**: Nenhuma interface de rede nos containers dos agentes
- **Criptografia de Dados**: Dados sensíveis criptografados em repouso
- **Intervenção Humana Obrigatória**: Para operações de alto impacto (deploy produção, schema changes)

---

## 15. Roteiro de Desenvolvimento (Roadmap) - Atualizado
### Versão 1.0 (Concluída)
- Stack definida
- Agentes principais funcionando
- RAG básico completo
- Git local via MCP

### Versão 1.1 (Em Desenvolvimento)
- ✅ Adicionar Agent-3 (Arquiteto)
- ✅ Sistema de Contexto Compartilhado
- ✅ Mecanismo de Recuperação de Falhas
- ✅ Capability Tokens para segurança
- ✅ Interface de Supervisão Humana (MVP)
- ✅ Sistema de Monitoramento de Métricas
- ✅ RAG especializado em código-fonte
- ⏳ Testes automatizados para cenários de falha

### Versão 1.2 (Planejado)
- Fine-tuning de embeddings em repositórios técnicos
- Sistema de aprendizado contínuo com feedback humano
- Integração com CI/CD para testes automatizados
- Otimizações de performance para hardware modesto

### Versão 2.0
- Deploy automático para ambientes de staging
- Testes avançados (security scanning, performance testing)
- Suporte a múltiplos projetos simultâneos
- Interface de configuração por projeto
- Sistema de custo computacional e otimização

---

## 16. Critérios de Sucesso Aprimorados
- **Confiança**:
  - 95% de fluxos completos sem intervenção humana
  - Tempo médio de recuperação de falhas < 2 minutos
- **Qualidade**:
  - JSON 100% válido em todas as comunicações
  - Código com 85%+ de cobertura de testes
  - Zero vulnerabilidades críticas identificadas
- **Performance**:
  - Tempo de resposta por agente < 30 segundos (hardware recomendado)
  - Taxa de sucesso de validação Pydantic > 90%
- **Segurança**:
  - Auditoria completa de todas as operações
  - Zero vazamentos de dados em testes de penetração
- **Usabilidade**:
  - Interface de supervisão intuitiva
  - Documentação completa para customização

---

## 17. Licença
Licença: MIT com cláusula de segurança adicional (ver SECURITY.md para detalhes).

---

## 18. Considerações de Hardware e Performance (Novo)
### Requisitos Mínimos
- CPU: 8 núcleos
- RAM: 32GB
- GPU: 8GB VRAM (para modelos quantizados)
- Armazenamento: 100GB SSD

### Configuração Recomendada
- CPU: 16+ núcleos
- RAM: 64GB+
- GPU: 24GB VRAM (RTX 4090 ou similar)
- Armazenamento: 1TB NVMe SSD
- Rede: 1Gbps+ (para downloads iniciais de modelos)

### Otimizações para Hardware Limitado
- **Modelos especializados menores**: Phi-3 para agentes de análise, CodeLlama-7b para desenvolvimento
- **Processamento sequencial**: Limitar concorrência entre agentes
- **Cache agressivo**: TTL expandido para respostas comuns
- **Offloading de GPU**: Processamento em CPU para operações não críticas
- **Modelos especializados por domínio**: Um modelo pequeno por tipo de tarefa

---

## 19. Conclusão
Esta documentação atualizada reflete uma arquitetura significativamente mais robusta e madura para o DEVs AI. As melhorias introduzidas na V1.1 - particularmente o Sistema de Contexto Compartilhado, o Mecanismo de Recuperação de Falhas e as Guardrails Aprimoradas - transformam o sistema de um protótipo interessante para uma plataforma pronta para uso em cenários reais de desenvolvimento de software.

A ênfase em segurança, recuperação de falhas e supervisão humana garante que o sistema possa operar de forma confiável mesmo em ambientes críticos, enquanto as otimizações de performance tornam viável sua execução em hardware acessível.

O roadmap claro e os critérios de sucesso mensuráveis fornecem uma base sólida para o desenvolvimento contínuo, com a V2.0 prometendo capacidades ainda mais avançadas de automação completa do ciclo de desenvolvimento.
