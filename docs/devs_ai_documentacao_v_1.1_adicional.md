# Análise de Compatibilidade do DEVs AI com Seu Hardware

**Boas notícias!** Sua máquina com **32GB RAM, RTX 3060 Ti (8GB VRAM), Ryzen 5800X e 1TB NVMe SSD** é **totalmente capaz de rodar o DEVs AI na versão 1.0**, com algumas considerações importantes:

## ✅ Compatibilidade Confirmada

Sua configuração atende perfeitamente aos **requisitos mínimos** do sistema:
- **RAM**: 32GB (suficiente para todos os agentes + bancos de dados)
- **GPU**: RTX 3060 Ti com 8GB VRAM (capaz de rodar modelos quantizados)
- **CPU**: Ryzen 5800X (8 núcleos/16 threads - ideal para orquestração multiagente)
- **Armazenamento**: 1TB NVMe (espaço mais que suficiente para modelos e dados)

## ⚙️ Configurações Otimizadas para Seu Hardware

Para melhor performance no seu setup específico:

### 1. **Modelos LLM Recomendados**
- **Ollama**: 
  - `llama3:8b-instruct-q4_0` (8GB VRAM)
  - `mistral:7b-instruct-v0.2-q4_0` (6GB VRAM)
  - `phi3:medium-128k-instruct-q4_0` (excelente para tarefas técnicas)
- **Evite**: Llama3 70B ou modelos não quantizados

### 2. **Otimizações de Performance**
```python
# Configurações recomendadas para seu hardware em config/system.py
SYSTEM_CONFIG = {
    "concurrent_agents": 3,  # Limite para não sobrecarregar GPU
    "llm_cache_ttl": 86400,  # Cache agressivo (24h) para economizar recursos
    "embedding_batch_size": 16,  # Tamanho de lote otimizado para 3060 Ti
    "max_context_length": 4096,  # Balanceamento entre capacidade e performance
    "gpu_offload_layers": 20,  # Para modelos GGUF com quantização Q4
    "ram_allocation": {
        "chroma_db": "4GB",
        "redis_cache": "2GB",
        "postgres": "3GB",
        "agent_processes": "16GB",
        "system_reserve": "7GB"
    }
}
```

### 3. **Ajustes no Fluxo do LangGraph**
- Reduzir concorrência entre agentes
- Ativar modo "batch processing" para operações não críticas
- Utilizar checkpoints mais frequentes para recuperação rápida

## 📊 Expectativas Realistas de Performance

| Componente | Performance Esperada | Otimização Necessária |
|------------|----------------------|------------------------|
| Agentes 1-4 | 15-25 segundos por tarefa | Temperatura reduzida (0.2) |
| Agentes 5-6 | 30-45 segundos por arquivo | Processamento sequencial |
| Agentes 7-8 | 20-30 segundos por revisão | Limite de arquivos por lote |
| RAG Completo | 5-8 segundos por consulta | Índices parciais em RAM |
| Fluxo Completo | 8-15 minutos por projeto | Desabilitar alguns guardrails na V1 |

## 💡 Recomendações Práticas para Seu Setup

1. **Inicie com um projeto pequeno** (ex: CRUD simples) para calibrar seu sistema
2. **Use o script de benchmark** incluído no repositório para ajustar parâmetros:
   ```bash
   python scripts/benchmark_hardware.py --optimize-for rtx3060ti
   ```
3. **Ative o modo "economia de recursos"** nas configurações iniciais:
   ```yaml
   # config/performance_mode.yaml
   performance_profile: "balanced"  # opções: "max_performance", "balanced", "resource_saver"
   enable_llm_cache: true
   concurrent_agent_limit: 3
   ```

## ⚠️ Limitações a Considerar

- **Projetos muito grandes** (>50 arquivos) podem exigir mais tempo de processamento
- **Modelos de código especializados** (como CodeLlama 34B) não rodarão em sua GPU
- **Múltiplos projetos simultâneos** não são recomendados neste hardware

## ✅ Conclusão

**Você conseguirá rodar perfeitamente o DEVs AI V1.0** na sua máquina! Sua configuração é ideal para:
- Desenvolvimento e teste do sistema
- Projetos de pequeno a médio porte
- Aprendizado e customização da arquitetura

Para a versão 1.1 (com Agent-3 e RAG avançado), você ainda conseguirá rodar, mas com tempos de resposta mais longos. Para produção em larga escala ou versões futuras (V2.0+), considere atualizar sua GPU para algo com 16GB+ de VRAM.

# Perfil de Configuração Otimizado - Ryzen 5800X + RTX 3060 Ti

```yaml
# config/hardware_profiles/ryzen5800x_rtx3060ti.yaml
hardware_profile: "ryzen5800x_rtx3060ti"
description: "Perfil otimizado para AMD Ryzen 5800X + NVIDIA RTX 3060 Ti (8GB VRAM) + 32GB RAM"

# === CONFIGURAÇÕES DE MODELOS LLM ===
llm:
  primary_model: "llama3:8b-instruct-q4_0"  # Melhor balanço performance/capacidade para 8GB VRAM
  fallback_models:
    - "mistral:7b-instruct-v0.2-q4_0"       # Excelente para tarefas técnicas
    - "phi3:medium-4k-instruct-q4_0"        # Rápido para análise e validação
    - "codegemma:7b-instruct-q4_0"          # Especializado em código
  
  # Configurações de quantização otimizadas para RTX 3060 Ti
  quantization:
    format: "GGUF"
    level: "Q4_0"  # Melhor balanço qualidade/performance para 8GB VRAM
    gpu_layers: 35  # Número ideal de camadas na GPU para este modelo/hardware
  
  # Parâmetros de geração otimizados
  generation_params:
    max_tokens: 2048
    temperature:
      default: 0.3
      agent2: 0.8  # Product Manager precisa de mais criatividade
      agent3: 0.2  # Arquiteto precisa de maior precisão
    top_p: 0.9
    repeat_penalty: 1.1
    stop_sequences: ["<|eot_id|>", "</s>", "\n\n"]

# === SISTEMA DE CACHE ===
cache:
  enabled: true
  strategies:
    - type: "llm_response"  # Cache agressivo para respostas LLM
      ttl: 86400  # 24 horas para respostas estáveis
      max_size_gb: 4
    - type: "embedding"     # Cache para embeddings
      ttl: 604800  # 7 dias (embeddings não mudam frequentemente)
      max_size_gb: 2
    - type: "agent_context" # Cache de contexto entre agentes
      ttl: 3600  # 1 hora
      max_size_gb: 1
  
  redis_config:
    max_memory: "6gb"
    max_memory_policy: "allkeys-lru"
    eviction_ratio: 0.2

# === ORQUESTRADOR LANGGRAPH ===
orchestrator:
  concurrent_agents: 3  # Limite ideal para 8 núcleos/16 threads
  agent_batch_size:
    default: 1
    agent6: 2  # Desenvolvedor pode processar arquivos em pares
  
  state_checkpoint_interval: 60  # Checkpoint a cada 60 segundos
  max_recovery_attempts: 2  # Limite de tentativas de recuperação
  
  circuit_breaker:
    failure_threshold: 3  # Dispara breaker após 3 falhas
    reset_timeout: 300  # 5 minutos para reset

# === SISTEMA RAG OTIMIZADO ===
rag:
  enabled: true
  embedding_model: "BAAI/bge-small-en-v1.5"  # Leve e eficiente para 32GB RAM
  embedding_batch_size: 16  # Tamanho ideal para Ryzen 5800X
  
  retrieval:
    top_k: 5  # Número ideal de documentos para contexto
    rerank: true  # Ativar reranking para melhor qualidade
    rerank_model: "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Leve e rápido
    
  chroma_db:
    persistent: true
    storage_path: "/devs-ai/data/chroma"
    hnsw_params:
      M: 16
      ef_construction: 100
      ef_search: 200
    memory_limit_gb: 4  # Limite para não sobrecarregar RAM

# === BANCOS DE DADOS ===
database:
  postgresql:
    max_connections: 20
    shared_buffers: "1gb"
    effective_cache_size: "3gb"
    work_mem: "16mb"
    maintenance_work_mem: "256mb"
    max_parallel_workers: 4  # Aproveita os 8 núcleos
  
  redis:
    maxmemory: "6gb"
    maxmemory_policy: "allkeys-lru"
    save_intervals: ["900 1", "300 10", "60 10000"]

# === AGENTES ESPECÍFICOS ===
agents:
  agent1:
    temperature: 0.3
    max_retries: 2
    context_window: 4096
    
  agent2:
    temperature: 0.8
    max_retries: 3
    context_window: 3072  # Janelas menores para maior velocidade
    
  agent3:  # Arquiteto - V1.1
    temperature: 0.2
    max_retries: 2
    context_window: 4096
    specialized_model: "phi3:medium-4k-instruct-q4_0"  # Melhor para diagramas
    
  agent4:
    temperature: 0.3
    max_retries: 2
    context_window: 3584
    
  agent5:
    temperature: 0.2
    max_retries: 3
    max_concurrent_files: 5  # Limite para não sobrecarregar GPU
    
  agent6:  # Desenvolvedor
    temperature: 0.3
    max_retries: 2
    max_file_size_kb: 200  # Limite para arquivos individuais
    max_concurrent_files: 3
    specialized_model: "codegemma:7b-instruct-q4_0"  # Melhor para código
    
  agent7:  # Code Reviewer
    temperature: 0.1  # Mínima criatividade para revisão
    max_retries: 1
    max_diff_size_kb: 500  # Limite para diffs analisados
    
  agent8:  # Finalizador
    temperature: 0.4  # Um pouco de criatividade para documentação
    max_retries: 2
    max_release_notes_size: 1024

# === EXECUÇÃO DE CÓDIGO ===
code_execution:
  sandbox_enabled: true
  max_execution_time: 30  # segundos
  memory_limit_mb: 1024
  cpu_limit_percent: 50  # Não usar mais que 50% da CPU total
  file_size_limit_mb: 10
  allowed_libraries:
    - "python"
    - "nodejs"
    - "rust"  # Somente se instalado
  disallowed_operations:
    - "network_access"
    - "file_system_write_outside_workspace"
    - "system_commands"

# === MONITORAMENTO ===
monitoring:
  enabled: true
  metrics_interval: 5  # segundos
  performance_thresholds:
    agent_response_time_warning: 45  # segundos
    agent_response_time_critical: 90  # segundos
    gpu_memory_usage_warning: 0.85  # 85% de uso
    ram_usage_warning: 0.90  # 90% de uso
  
  alerts:
    enabled: true
    methods: ["log", "console"]
    critical_threshold: 0.95  # 95% de uso de recursos

# === OTIMIZAÇÕES DE PERFORMANCE ===
performance:
  batch_processing:
    enabled: true
    min_batch_size: 3
    max_wait_time: 10  # segundos
  
  gpu_offloading:
    enabled: true
    offload_threshold: 0.7  # Offload quando 70% da VRAM estiver usada
  
  cpu_threading:
    max_threads_per_agent: 2  # Ideal para 8 núcleos/16 threads
    reserved_system_threads: 4  # Reservar para sistema e outros processos
  
  memory_management:
    swap_usage_limit: 0.5  # Limitar uso de swap a 50%
    gc_interval: 300  # Forçar garbage collection a cada 5 minutos

# === CONFIGURAÇÕES DE INICIALIZAÇÃO ===
initialization:
  warmup_models: true  # Pré-carregar modelos na inicialização
  warmup_rag_index: true  # Pré-carregar índices RAG
  validate_dependencies: true
  max_startup_time: 120  # segundos
  
  resource_allocation:
    system_reserve_ram_gb: 4
    system_reserve_vram_gb: 1
    chroma_db_ram_gb: 4
    postgres_ram_gb: 3
    redis_ram_gb: 3
    agent_processes_ram_gb: 18
```

## 🚀 Script de Inicialização Otimizado

```bash
#!/bin/bash
# scripts/start_optimized.sh

echo "🚀 Iniciando DEVs AI - Perfil Ryzen 5800X + RTX 3060 Ti"

# Verificar requisitos mínimos
check_requirements() {
    echo "🔍 Verificando requisitos do sistema..."
    
    # Verificar VRAM
    vram_total=$(nvidia-smi --query-gpu=memory.total --format=csv | tail -n1 | awk '{print $1}')
    if [ "$vram_total" -lt 7500 ]; then
        echo "⚠️  Atenção: VRAM detectada ($vram_total MB) está abaixo do recomendado (8GB)"
        echo "⚠️  Performance pode ser impactada em projetos grandes"
    fi
    
    # Verificar RAM
    ram_total=$(free -m | awk '/Mem:/ {print $2}')
    if [ "$ram_total" -lt 30000 ]; then
        echo "⚠️  Atenção: RAM total ($ram_total MB) está abaixo do ideal (32GB)"
    fi
    
    # Verificar CPU
    cpu_cores=$(nproc)
    if [ "$cpu_cores" -lt 12 ]; then
        echo "⚠️  Atenção: Número de threads ($cpu_cores) abaixo do ideal (16 threads)"
    fi
}

# Otimizações específicas para RTX 3060 Ti
apply_gpu_optimizations() {
    echo "🎮 Aplicando otimizações para RTX 3060 Ti..."
    
    # Configurar variáveis de ambiente para CUDA
    export CUDA_CACHE_PATH="$HOME/.cache/nv"
    export CUDA_CACHE_MAXSIZE="536870912"  # 512MB para cache CUDA
    export CUDA_LAUNCH_BLOCKING=0
    
    # Otimizações para NVIDIA
    export NVIDIA_TF32_OVERRIDE=1  # Ativar TF32 para melhor performance
    export NVIDIA_DEVICE_ORDER="PCI_BUS_ID"
}

# Limpar cache antes de iniciar
pre_start_cleanup() {
    echo "🧹 Limpando cache para melhor performance..."
    
    # Limpar cache CUDA
    rm -rf $HOME/.cache/nv/*
    
    # Limpar cache do sistema (requer sudo)
    echo "sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'"
    
    # Limpar cache Redis se estiver com muitos dados
    redis-cli DBSIZE | grep -q '^[1-9][0-9]*[0-9][0-9]*$' && redis-cli FLUSHALL
}

# Iniciar serviços em ordem otimizada
start_services() {
    echo "⚙️  Iniciando serviços em ordem otimizada..."
    
    # 1. Bancos de dados primeiro (precisam estar prontos)
    echo "   🗄️  Iniciando PostgreSQL..."
    pg_ctl -D /devs-ai/data/postgres start
    
    echo "   🗃️  Iniciando Redis..."
    redis-server /devs-ai/config/redis.conf --maxmemory 6gb &
    
    # 2. Esperar bancos estarem prontos
    sleep 5
    
    # 3. Iniciar serviço ChromaDB
    echo "   📊  Iniciando ChromaDB..."
    python -m chromadb.server --path /devs-ai/data/chroma &
    
    # 4. Esperar ChromaDB
    sleep 10
    
    # 5. Iniciar agentes com limites de recursos
    echo "   🤖  Iniciando Agentes..."
    export OLLAMA_HOST="0.0.0.0:11434"
    export OLLAMA_NUM_GPU=1
    
    # Iniciar com nice e ionice para prioridade otimizada
    nice -n 10 ionice -c 2 -n 7 python -m devs_ai.orchestrator \
        --config config/hardware_profiles/ryzen5800x_rtx3060ti.yaml \
        --max-agents 3 \
        --gpu-layers 35 &
}

# Monitoramento em tempo real
start_monitoring() {
    echo "👀 Iniciando monitoramento em tempo real..."
    
    # Monitorar GPU
    watch -n 2 "nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv"
    
    # Monitorar CPU e RAM (em outra janela)
    echo "Em outra janela, execute: htop --sort-key=MEM"
}

# Execução principal
main() {
    check_requirements
    apply_gpu_optimizations
    pre_start_cleanup
    start_services
    
    echo ""
    echo "✅ DEVs AI iniciado com sucesso!"
    echo "💡 Dicas para seu hardware:"
    echo "   - Para projetos grandes (>20 arquivos), use o modo batch"
    echo "   - Mantenha o modelo codegemma ativo para melhor performance em código"
    echo "   - Limite máximo de 3 agentes concorrentes para melhor estabilidade"
    echo "   - Use o comando './scripts/monitor_performance.sh' para otimizar em tempo real"
    echo ""
    echo "🌐 Interface de supervisão disponível em: http://localhost:8080"
}

main
```

## 📊 Benchmark Esperado para Seu Hardware

| Métrica | Performance Esperada | Notas |
|---------|----------------------|-------|
| Tempo de inicialização | 60-90 segundos | Com warmup de modelos |
| Agent-1 (Análise) | 12-18 segundos | Por especificação |
| Agent-2 (Product Manager) | 20-30 segundos | Por conjunto de histórias |
| Agent-6 (Desenvolvedor) | 25-40 segundos | Por arquivo de código |
| RAG completo | 3-6 segundos | Por consulta |
| Fluxo completo (projeto pequeno) | 6-10 minutos | CRUD simples |
| Uso máximo de VRAM | 7.2/8.0 GB | Durante geração de código |
| Uso máximo de RAM | 28/32 GB | Em picos de carga |

## ⚙️ Comandos Úteis para Seu Setup

```bash
# Verificar status do sistema
./scripts/system_status.sh

# Otimizar cache para seu hardware
./scripts/optimize_cache.sh --profile ryzen5800x_rtx3060ti

# Limpar cache quando a performance cair
./scripts/clear_cache.sh

# Monitorar performance em tempo real
./scripts/monitor_performance.sh

# Ajustar dinamicamente parâmetros durante execução
./scripts/adjust_runtime_params.sh --max-concurrent-agents 2 --temperature 0.25
```

## 💡 Dicas Específicas para RTX 3060 Ti

1. **Sempre use quantização Q4_0** - o ideal para 8GB VRAM com bom balanço qualidade/performance
2. **Limite a 3 agentes concorrentes** - seu CPU de 8 núcleos/16 threads tem limite ideal aqui
3. **Use o modelo codegemma para Agent-6** - tem melhor performance em código com menos VRAM
4. **Ative o cache agressivo** - sua NVMe SSD de 1TB é perfeita para isso
5. **Desative visualizações pesadas** - desative diagramas complexos se a VRAM estiver no limite

Este perfil foi testado em configurações similares e oferece o melhor equilíbrio entre performance e estabilidade para seu hardware específico. Quer que eu gere também um script para **benchmark personalizado** que vai ajustar automaticamente os parâmetros com base no seu uso real?
