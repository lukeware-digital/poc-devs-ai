import os
import json
import yaml
from pathlib import Path


def load_configuration(config_path: str = None) -> dict:
    """
    Carrega a configuração do sistema com valores padrão e sobrescreve com configuração específica.
    """
    # Configuração padrão
    default_config = {
        'primary_model': 'llama3:8b-instruct-q4_0',
        'fallback_models': [
            'mistral:7b-instruct-v0.2-q4_0', 
            'phi3:medium-4k-instruct-q4_0',
            'codegemma:7b-instruct-q4_0'
        ],
        'redis_host': 'localhost',
        'redis_port': 6379,
        'chroma_host': 'localhost',
        'chroma_port': 8000,
        'ollama_host': 'localhost:11434',
        'agents': {
            'agent1': {'temperature': 0.3, 'max_retries': 2},
            'agent2': {'temperature': 0.8, 'max_retries': 3},
            'agent3': {'temperature': 0.2, 'max_retries': 2},
            'agent4': {'temperature': 0.3, 'max_retries': 2},
            'agent5': {'temperature': 0.2, 'max_retries': 3},
            'agent6': {'temperature': 0.3, 'max_retries': 2},
            'agent7': {'temperature': 0.1, 'max_retries': 1},
            'agent8': {'temperature': 0.4, 'max_retries': 2},
        },
        'orchestrator': {
            'concurrent_agents': 3,
            'max_auto_retries': 2,
            'state_checkpoint_interval': 60,
            'circuit_breaker': {
                'failure_threshold': 3,
                'reset_timeout': 300
            }
        },
        'performance': {
            'batch_processing': True,
            'gpu_offloading': True,
            'max_startup_time': 120,
            'memory_management': {
                'swap_usage_limit': 0.5,
                'gc_interval': 300
            }
        },
        'security': {
            'enable_guardrails': True,
            'capability_token_ttl': 300,
            'sandbox_enabled': True,
            'network_isolation': True
        }
    }
    
    # Sobrescreve com configuração do arquivo se existir
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                user_config = yaml.safe_load(f)
            elif config_path.endswith('.json'):
                user_config = json.load(f)
            else:
                raise ValueError("Formato de configuração não suportado. Use YAML ou JSON.")
                
            # Mescla configurações de forma recursiva
            default_config = merge_dicts(default_config, user_config)
            
    return default_config


def merge_dicts(dict1, dict2):
    """Mescla dois dicionários de forma recursiva."""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result