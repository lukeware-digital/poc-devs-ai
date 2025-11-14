import json
from pathlib import Path

import yaml

_CONFIG_DIR = Path(__file__).parent
_DEFAULT_CONFIG_PATH = _CONFIG_DIR / "hardware_profiles" / "default.yaml"


def _validate_config(config: dict) -> None:
    """
    Valida se a configuração contém todos os campos obrigatórios.
    
    Raises:
        ValueError: Se campos obrigatórios estiverem faltando ou inválidos.
    """
    required_fields = [
        "primary_model",
        "agent_models",
        "agents",
        "orchestrator",
        "performance",
        "security",
    ]
    
    missing_fields = [field for field in required_fields if field not in config]
    if missing_fields:
        raise ValueError(
            f"Campos obrigatórios faltando na configuração: {', '.join(missing_fields)}"
        )
    
    if not isinstance(config.get("agent_models"), dict):
        raise ValueError("'agent_models' deve ser um dicionário")
    
    required_agents = [f"agent{i}" for i in range(1, 9)]
    agent_models = config.get("agent_models", {})
    missing_agents = [agent for agent in required_agents if agent not in agent_models]
    if missing_agents:
        raise ValueError(
            f"Agentes faltando em 'agent_models': {', '.join(missing_agents)}"
        )
    
    agents_config = config.get("agents", {})
    missing_agent_configs = [agent for agent in required_agents if agent not in agents_config]
    if missing_agent_configs:
        raise ValueError(
            f"Configurações faltando em 'agents': {', '.join(missing_agent_configs)}"
        )
    
    for agent_id in required_agents:
        agent_config = agents_config.get(agent_id, {})
        if "temperature" not in agent_config:
            raise ValueError(f"Campo 'temperature' faltando para {agent_id}")
        if "max_retries" not in agent_config:
            raise ValueError(f"Campo 'max_retries' faltando para {agent_id}")
        
        temp = agent_config["temperature"]
        if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
            raise ValueError(f"Temperature inválida para {agent_id}: {temp} (deve estar entre 0 e 2)")
        
        max_retries = agent_config["max_retries"]
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError(f"max_retries inválido para {agent_id}: {max_retries} (deve ser >= 0)")


def load_configuration(config_path: str = None) -> dict:
    """
    Carrega a configuração do sistema a partir de arquivo YAML.
    
    Se config_path não for fornecido, usa config/hardware_profiles/default.yaml como padrão.
    Se o arquivo especificado não existir, usa default.yaml como fallback.
    
    Args:
        config_path: Caminho para o arquivo de configuração (YAML ou JSON)
    
    Returns:
        Dicionário com a configuração carregada
    
    Raises:
        FileNotFoundError: Se nem o arquivo especificado nem default.yaml existirem
        ValueError: Se o formato for inválido ou campos obrigatórios estiverem faltando
    """
    if not config_path:
        config_file = _DEFAULT_CONFIG_PATH
    else:
        config_file = Path(config_path)
        if not config_file.is_absolute():
            current_dir_file = Path.cwd() / config_path
            if current_dir_file.exists():
                config_file = current_dir_file
            else:
                project_root = _CONFIG_DIR.parent
                config_file = project_root / config_path
    
    original_config_file = config_file
    
    if not config_file.exists():
        if config_path and config_file != _DEFAULT_CONFIG_PATH:
            import logging
            logger = logging.getLogger("DEVs_AI")
            logger.warning(
                f"Arquivo de configuração não encontrado: {config_file}. "
                f"Usando fallback: {_DEFAULT_CONFIG_PATH}"
            )
            config_file = _DEFAULT_CONFIG_PATH
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"Arquivo de configuração não encontrado: {original_config_file}. "
                f"Fallback default.yaml também não encontrado: {_DEFAULT_CONFIG_PATH}. "
                f"Certifique-se de que pelo menos um dos arquivos existe."
            )
    
    with open(config_file) as f:
        config_path_str = str(config_file)
        if config_path_str.endswith(".yaml") or config_path_str.endswith(".yml"):
            config = yaml.safe_load(f)
        elif config_path_str.endswith(".json"):
            config = json.load(f)
        else:
            raise ValueError(
                f"Formato de configuração não suportado: {config_path_str}. "
                f"Use YAML (.yaml, .yml) ou JSON (.json)."
            )
    
    if config is None:
        raise ValueError(f"Arquivo de configuração vazio ou inválido: {config_file}")
    
    _validate_config(config)
    
    return config


def merge_dicts(dict1, dict2):
    """Mescla dois dicionários de forma recursiva."""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result
