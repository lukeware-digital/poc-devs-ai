"""
Constantes do sistema DEVs AI - Valores padrão para configurações
"""

# === CONFIGURAÇÕES DE LLM ===
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TOP_P = 0.9
DEFAULT_REPEAT_PENALTY = 1.1

# Temperaturas específicas por agente
AGENT_TEMPERATURES = {
    'agent1': 0.3,  # Clarificador - preciso
    'agent2': 0.8,  # Product Manager - criativo
    'agent3': 0.2,  # Arquiteto - muito preciso
    'agent4': 0.3,  # Tech Lead - preciso
    'agent5': 0.2,  # Scaffolder - muito preciso
    'agent6': 0.3,  # Desenvolvedor - preciso
    'agent7': 0.1,  # Code Reviewer - extremamente preciso
    'agent8': 0.4,  # Finalizador - moderadamente criativo
}

# === CONFIGURAÇÕES DE CACHE ===
DEFAULT_CACHE_TTL = 3600  # 1 hora em segundos
CACHE_TTL_24H = 86400  # 24 horas
CACHE_TTL_7D = 604800  # 7 dias
CACHE_CLEANUP_INTERVAL = 300  # 5 minutos
MAX_CACHE_ENTRIES = 1000

# === CONFIGURAÇÕES DE RETRY E TIMEOUT ===
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 300  # 5 minutos em segundos
DEFAULT_RETRY_BACKOFF_FACTOR = 2
MAX_RETRY_DELAY = 30  # segundos

# Retries específicas por agente
AGENT_MAX_RETRIES = {
    'agent1': 2,
    'agent2': 3,
    'agent3': 2,
    'agent4': 2,
    'agent5': 3,
    'agent6': 2,
    'agent7': 1,
    'agent8': 2,
}

# === CONFIGURAÇÕES DE CAPABILITY TOKENS ===
DEFAULT_TOKEN_TTL = 300  # 5 minutos
EXTENDED_TOKEN_TTL = 600  # 10 minutos
CRITICAL_TOKEN_TTL = 900  # 15 minutos

# === CONFIGURAÇÕES DE CONCORRÊNCIA ===
DEFAULT_CONCURRENT_AGENTS = 3
MAX_CONCURRENT_AGENTS = 8
DEFAULT_BATCH_SIZE = 16

# === CONFIGURAÇÕES DE CIRCUIT BREAKER ===
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
CIRCUIT_BREAKER_RESET_TIMEOUT = 300  # 5 minutos
CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT = 60  # 1 minuto

# === CONFIGURAÇÕES DE ESTADO E CHECKPOINT ===
STATE_CHECKPOINT_INTERVAL = 60  # 1 minuto
MAX_STATE_VERSIONS = 10
ROLLBACK_MAX_ATTEMPTS = 3

# === CONFIGURAÇÕES DE MÉTRICAS ===
METRICS_COLLECTION_INTERVAL = 5  # segundos
MAX_METRICS_HISTORY_SIZE = 1000
MAX_ALERTS_IN_MEMORY = 1000
ALERTS_CLEANUP_INTERVAL = 3600  # 1 hora
ALERTS_RETENTION_DAYS = 7

# Thresholds de performance
AGENT_RESPONSE_TIME_WARNING = 30  # segundos
AGENT_RESPONSE_TIME_CRITICAL = 60  # segundos
SYSTEM_CPU_WARNING_PERCENT = 80
SYSTEM_MEMORY_WARNING_PERCENT = 80
SYSTEM_DISK_WARNING_PERCENT = 90

# === CONFIGURAÇÕES DE RECURSOS ===
# GPU
DEFAULT_GPU_LAYERS = 35
MIN_VRAM_GB = 4
RECOMMENDED_VRAM_GB = 8

# RAM
MIN_RAM_GB = 16
RECOMMENDED_RAM_GB = 32
SYSTEM_RESERVE_RAM_GB = 4

# CPU
MIN_CPU_CORES = 8
RECOMMENDED_CPU_CORES = 16

# === CONFIGURAÇÕES DE EMBEDDING ===
DEFAULT_EMBEDDING_DIMENSIONS = 384
EMBEDDING_BATCH_SIZE = 16
SEMANTIC_WEIGHT = 0.5
TECHNICAL_WEIGHT = 0.3
CONTEXTUAL_WEIGHT = 0.2

# === CONFIGURAÇÕES DE RAG ===
RAG_TOP_K_RESULTS = 5
RAG_MIN_SIMILARITY = 0.3
RAG_RERANK_ENABLED = True
RAG_MAX_CONTEXT_TOKENS = 500

# === CONFIGURAÇÕES DE SEGURANÇA ===
# File size limits
MAX_FILE_SIZE_KB = 200
MAX_FILE_SIZE_BYTES = 100_000  # 100KB
MAX_DIFF_SIZE_KB = 500

# Network
DANGEROUS_PORTS = [22, 23, 25, 53, 80, 443, 3306, 5432, 6379, 27017]
NETWORK_TIMEOUT_SECONDS = 30

# Git
MAX_GIT_CHANGES_PER_PUSH = 50
MAX_GIT_PUSH_SIZE_KB = 10_000  # 10MB

# === CONFIGURAÇÕES DE BANCO DE DADOS ===
# Redis
REDIS_DEFAULT_PORT = 6379
REDIS_MAX_MEMORY_GB = 6
REDIS_MAX_CONNECTIONS = 50

# PostgreSQL
POSTGRES_DEFAULT_PORT = 5432
POSTGRES_MAX_CONNECTIONS = 20
POSTGRES_SHARED_BUFFERS_GB = 1
POSTGRES_EFFECTIVE_CACHE_SIZE_GB = 3

# ChromaDB
CHROMA_DEFAULT_PORT = 8000
CHROMA_MEMORY_LIMIT_GB = 4

# === CONFIGURAÇÕES DE RECOVERY SYSTEM ===
RECOVERY_MAX_AUTO_RETRIES = 3
RECOVERY_TIMEOUT = 120  # 2 minutos
RECOVERY_STATS_HISTORY_SIZE = 100

# === CONFIGURAÇÕES DE FALLBACK ===
FALLBACK_TEMPERATURE = 0.1
FALLBACK_MAX_ATTEMPTS = 3
FALLBACK_CONFIDENCE_THRESHOLD = 0.5

# === FORMATOS E CONSTANTES DE VALIDAÇÃO ===
VALID_PROGRAMMING_LANGUAGES = [
    'python', 'javascript', 'typescript', 'java', 'cpp', 'c',
    'csharp', 'go', 'rust', 'ruby', 'php', 'swift', 'kotlin'
]

VALID_DOC_TYPES = ['code', 'architecture', 'requirement', 'commit', 'generic']

COMPLEXITY_MIN = 1
COMPLEXITY_MAX = 10

# === MENSAGENS DE STATUS ===
STATUS_SUCCESS = 'success'
STATUS_FAILURE = 'failure'
STATUS_FALLBACK_APPLIED = 'success_with_fallback'
STATUS_PENDING = 'pending'
STATUS_IN_PROGRESS = 'in_progress'
STATUS_COMPLETED = 'completed'
STATUS_CANCELLED = 'cancelled'

# === TIPOS DE OPERAÇÕES ===
OPERATION_DEFAULT = 'default'
OPERATION_REQUIREMENTS_ANALYSIS = 'requirements_analysis'
OPERATION_USER_STORIES_CREATION = 'user_stories_creation'
OPERATION_ARCHITECTURE_DEFINITION = 'architecture_definition'
OPERATION_TECHNICAL_PLANNING = 'technical_planning'
OPERATION_PROJECT_SCAFFOLDING = 'project_scaffolding'
OPERATION_CODE_IMPLEMENTATION = 'code_implementation'
OPERATION_CODE_REVIEW = 'code_review'
OPERATION_FINAL_DELIVERY = 'final_delivery'

# === OPERAÇÕES CRÍTICAS (requerem capability tokens) ===
CRITICAL_OPERATIONS = [
    'git_push',
    'file_deletion',
    'database_modification',
    'system_command',
    'network_request',
    'file_execution',
    'environment_modification',
    'sudo_operation'
]

# === COMANDOS PERMITIDOS (whitelist) ===
ALLOWED_SYSTEM_COMMANDS = [
    'ls', 'pwd', 'cat', 'echo', 'mkdir', 'touch', 'cp', 'mv', 'grep', 'find'
]

# === PADRÕES DE ARQUIVOS PROTEGIDOS ===
PROTECTED_FILE_PATTERNS = [
    '*.pyc', '*.pyo', '__pycache__/*', '.git/*', '.env',
    'config/*', 'secrets/*', 'credentials/*', '*password*',
    '*secret*', '*key*', '*token*', '*.key', '*.pem'
]

