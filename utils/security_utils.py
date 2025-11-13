"""
Utilitários de Segurança - Funções auxiliares para segurança do sistema
"""

import re
import logging
import json
from typing import Dict, Any, List, Optional
import hashlib
import base64
import os

logger = logging.getLogger("DEVs_AI")

def sanitize_input(input_str: str, max_length: int = 10000) -> str:
    """
    Sanitiza entrada de usuário removendo caracteres potencialmente perigosos
    
    Args:
        input_str: String de entrada
        max_length: Comprimento máximo permitido
        
    Returns:
        String sanitizada
    """
    if not input_str:
        return ""
    
    # Limita comprimento
    if len(input_str) > max_length:
        input_str = input_str[:max_length]
        logger.warning(f"Entrada truncada para {max_length} caracteres")
    
    # Remove caracteres de controle e NUL
    sanitized = ''.join(c for c in input_str if ord(c) >= 32 or c in '\n\r\t')
    
    # Remove padrões perigosos conhecidos (básico)
    dangerous_patterns = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC|DECLARE)\b)',  # SQL injection básico
        r'(<script.*?>.*?</script>)',  # XSS básico
        r'(\b__import__\b)',  # Import dinâmico perigoso
        r'(\bos\.[a-z_]+\(|\bsubprocess\.[a-z_]+\(|\bsystem\(|\bpopen\()',  # Comandos de sistema
        r'(\bchmod\b|\bchown\b|\brm\s+-\w+\b)',  # Comandos de sistema Unix
        r'(\bjavascript:\b|\bdata:\b)'  # URLs perigosas
    ]
    
    for pattern in dangerous_patterns:
        try:
            sanitized = re.sub(pattern, '[SANITIZED]', sanitized, flags=re.IGNORECASE)
        except re.error as e:
            logger.warning(f"Erro em padrão de sanitização: {str(e)}")
    
    return sanitized

def validate_json_structure(json_data: Dict[str, Any], 
                          schema: Dict[str, Any]) -> bool:
    """
    Valida estrutura JSON contra esquema
    
    Args:
        json_data: Dados JSON para validar
        schema: Esquema de validação
        
    Returns:
        True se válido, False caso contrário
    """
    try:
        from jsonschema import validate
        validate(instance=json_data, schema=schema)
        return True
    except ImportError:
        logger.warning("jsonschema não instalado, usando validação básica")
        return _basic_json_validation(json_data, schema)
    except Exception as e:
        logger.error(f"Erro na validação JSON: {str(e)}")
        return False

def _basic_json_validation(json_data: Dict[str, Any], 
                         schema: Dict[str, Any]) -> bool:
    """
    Validação JSON básica sem dependências externas
    """
    if not isinstance(json_data, dict) or not isinstance(schema, dict):
        return False
    
    # Verifica campos obrigatórios
    required = schema.get('required', [])
    for field in required:
        if field not in json_data:
            logger.warning(f"Campo obrigatório ausente: {field}")
            return False
    
    # Verifica tipos se especificados
    properties = schema.get('properties', {})
    for field, field_schema in properties.items():
        if field in json_data:
            expected_type = field_schema.get('type')
            if expected_type:
                actual_value = json_data[field]
                if expected_type == 'string' and not isinstance(actual_value, str):
                    logger.warning(f"Campo {field} esperava string, recebeu {type(actual_value)}")
                    return False
                elif expected_type == 'number' and not isinstance(actual_value, (int, float)):
                    logger.warning(f"Campo {field} esperava número, recebeu {type(actual_value)}")
                    return False
                elif expected_type == 'integer' and not isinstance(actual_value, int):
                    logger.warning(f"Campo {field} esperava inteiro, recebeu {type(actual_value)}")
                    return False
                elif expected_type == 'boolean' and not isinstance(actual_value, bool):
                    logger.warning(f"Campo {field} esperava booleano, recebeu {type(actual_value)}")
                    return False
                elif expected_type == 'object' and not isinstance(actual_value, dict):
                    logger.warning(f"Campo {field} esperava objeto, recebeu {type(actual_value)}")
                    return False
                elif expected_type == 'array' and not isinstance(actual_value, list):
                    logger.warning(f"Campo {field} esperava array, recebeu {type(actual_value)}")
                    return False
    
    return True

def generate_secure_token(length: int = 32) -> str:
    """
    Gera token seguro aleatório
    
    Args:
        length: Comprimento do token em bytes
        
    Returns:
        Token seguro em formato base64
    """
    random_bytes = os.urandom(length)
    return base64.urlsafe_b64encode(random_bytes).decode().rstrip('=')

def hash_sensitive_data(data: str, algorithm: str = 'sha256') -> str:
    """
    Hash de dados sensíveis para armazenamento seguro
    
    Args:
        data: Dados para fazer hash
        algorithm: Algoritmo de hash
        
    Returns:
        Hash dos dados
    """
    try:
        hash_func = getattr(hashlib, algorithm)()
        hash_func.update(data.encode('utf-8'))
        return hash_func.hexdigest()
    except (AttributeError, TypeError) as e:
        logger.error(f"Erro ao gerar hash: {str(e)}")
        raise ValueError(f"Algoritmo de hash inválido: {algorithm}")

def mask_sensitive_info(text: str, patterns: List[str] = None) -> str:
    """
    Mascara informações sensíveis em texto
    
    Args:
        text: Texto para mascarar
        patterns: Padrões de informações sensíveis (None para padrões padrão)
        
    Returns:
        Texto com informações sensíveis mascaradas
    """
    if not text:
        return text
    
    if patterns is None:
        patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Telefones
            r'\b(?:\d[ -]*?){13,16}\b',  # Cartões de crédito
            r'\b[A-Z0-9]{15,30}\b',  # IDs longos
            r'password\s*[=:]\s*["\'][^"\']+["\']',  # Senhas em configurações
            r'api[_-]?key\s*[=:]\s*["\'][^"\']+["\']',  # Chaves de API
            r'token\s*[=:]\s*["\'][^"\']+["\']',  # Tokens
        ]
    
    masked_text = text
    for pattern in patterns:
        try:
            matches = re.findall(pattern, masked_text, re.IGNORECASE)
            for match in set(matches):  # Remove duplicados
                masked = '*' * (len(match) - 4) + match[-4:] if len(match) > 4 else '*' * len(match)
                masked_text = masked_text.replace(match, masked)
        except re.error as e:
            logger.warning(f"Erro no padrão de mascaramento: {str(e)}")
    
    return masked_text

def is_safe_directory_path(path: str, base_dir: str) -> bool:
    """
    Verifica se caminho está dentro do diretório base (proteção contra path traversal)
    
    Args:
        path: Caminho para verificar
        base_dir: Diretório base permitido
        
    Returns:
        True se o caminho é seguro, False caso contrário
    """
    try:
        # Resolve paths
        base_path = os.path.realpath(base_dir)
        target_path = os.path.realpath(os.path.join(base_dir, path))
        
        # Verifica se target_path está dentro de base_path
        return os.path.commonpath([base_path]) == os.path.commonpath([base_path, target_path])
    except Exception as e:
        logger.error(f"Erro ao verificar caminho seguro: {str(e)}")
        return False

def validate_capability_token(token: str, expected_operation: str, 
                             context: Dict[str, Any]) -> bool:
    """
    Valida token de capacidade para operações críticas
    
    Args:
        token: Token a ser validado
        expected_operation: Operação esperada
        context: Contexto da operação
        
    Returns:
        True se token é válido, False caso contrário
    """
    # Em implementação real, isso validaria contra um serviço de tokens
    # Esta é uma implementação simplificada para demonstração
    if not token or not token.startswith('cap_'):
        return False
    
    # Validação básica de estrutura
    parts = token.split('_')
    if len(parts) != 4:
        return False
    
    # Verifica operação esperada
    if parts[1] != expected_operation:
        return False
    
    # Verifica contexto (simplificado)
    context_hash = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()
    if parts[2] != context_hash[:8]:
        return False
    
    return True

def generate_capability_token(operation: str, context: Dict[str, Any], 
                             ttl: int = 300) -> str:
    """
    Gera token de capacidade para operações críticas
    
    Args:
        operation: Operação que o token autoriza
        context: Contexto da operação
        ttl: Tempo de vida do token em segundos
        
    Returns:
        Token de capacidade
    """
    # Gera hash do contexto
    context_hash = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()
    
    # Gera timestamp
    timestamp = str(int(time.time()))
    
    # Cria token
    token_data = f"{operation}_{context_hash[:8]}_{timestamp}"
    token_hash = hashlib.sha256(token_data.encode()).hexdigest()[:16]
    
    return f"cap_{operation}_{context_hash[:8]}_{token_hash}"

def secure_json_dump(data: Dict[str, Any], include_sensitive: bool = False) -> str:
    """
    Serializa JSON removendo campos sensíveis
    
    Args:
        data: Dados para serializar
        include_sensitive: Incluir campos sensíveis (para debugging)
        
    Returns:
        String JSON segura
    """
    if not include_sensitive:
        # Remove campos sensíveis
        sensitive_fields = ['password', 'token', 'api_key', 'secret', 'credential']
        cleaned_data = {}
        
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                continue
            
            if isinstance(value, dict):
                cleaned_data[key] = secure_json_dump(value, include_sensitive)
            elif isinstance(value, str):
                cleaned_data[key] = mask_sensitive_info(value)
            else:
                cleaned_data[key] = value
        
        data = cleaned_data
    
    return json.dumps(data, ensure_ascii=False)