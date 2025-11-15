"""
Sistema de Capability Tokens - Tokens de capacidade para operações críticas
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta

import redis

logger = logging.getLogger("devs-ai")


class CapabilityToken:
    """
    Token de capacidade que autoriza uma operação específica para um agente
    """

    def __init__(
        self,
        token_id: str,
        agent_id: str,
        operation: str,
        scope: list[str],
        expires_at: datetime,
    ):
        self.token_id = token_id
        self.agent_id = agent_id
        self.operation = operation
        self.scope = scope
        self.expires_at = expires_at
        self.used = False
        self.created_at = datetime.utcnow()
        self.metadata = {}

    def is_valid(self) -> bool:
        """
        Verifica se o token é válido (não usado e não expirado)
        """
        return not self.used and datetime.utcnow() < self.expires_at

    def mark_used(self):
        """
        Marca o token como usado
        """
        self.used = True

    def to_dict(self) -> dict[str, any]:
        """
        Converte token para dicionário
        """
        return {
            "token_id": self.token_id,
            "agent_id": self.agent_id,
            "operation": self.operation,
            "scope": self.scope,
            "expires_at": self.expires_at.isoformat(),
            "used": self.used,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, any]) -> "CapabilityToken":
        """
        Cria token a partir de dicionário
        """
        token = cls(
            token_id=data["token_id"],
            agent_id=data["agent_id"],
            operation=data["operation"],
            scope=data["scope"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
        )
        token.used = data["used"]
        token.created_at = datetime.fromisoformat(data["created_at"])
        token.metadata = data.get("metadata", {})
        return token


class CapabilityTokenManager:
    """
    Gerenciador de tokens de capacidade com persistência em Redis
    """

    def __init__(self, redis_client: redis.Redis | None = None, token_ttl: int = 300):
        self.redis = redis_client
        self.token_ttl = token_ttl  # TTL padrão em segundos (5 minutos)
        self.memory_cache = {}

    def generate_token(
        self,
        agent_id: str,
        operation: str,
        scope: list[str],
        ttl: int | None = None,
        metadata: dict[str, any] = None,
    ) -> CapabilityToken:
        """
        Gera um novo token de capacidade

        Args:
            agent_id: ID do agente que receberá o token
            operation: Operação autorizada
            scope: Escopo da operação (ex: ['file:create', 'file:read'])
            ttl: Tempo de vida do token em segundos (None para usar padrão)
            metadata: Metadados adicionais

        Returns:
            CapabilityToken gerado
        """
        # Gera ID único para o token
        token_id = hashlib.sha256(f"{agent_id}{operation}{datetime.utcnow().isoformat()}{scope}".encode()).hexdigest()[
            :16
        ]

        # Define TTL
        token_ttl = ttl if ttl is not None else self.token_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=token_ttl)

        # Cria token
        token = CapabilityToken(token_id, agent_id, operation, scope, expires_at)
        if metadata:
            token.metadata = metadata

        # Armazena token
        self._store_token(token, token_ttl)

        logger.info(f"Token de capacidade gerado: {token_id} para agente {agent_id} - operação {operation}")
        return token

    def _store_token(self, token: CapabilityToken, ttl: int):
        """
        Armazena token no Redis e cache em memória
        """
        token_data = token.to_dict()
        token_key = f"capability_token:{token.token_id}"

        # Armazena em cache em memória
        self.memory_cache[token.token_id] = token

        # Armazena no Redis se disponível
        if self.redis:
            try:
                self.redis.setex(token_key, ttl, json.dumps(token_data))
            except Exception as e:
                logger.warning(f"Falha ao armazenar token no Redis: {str(e)}")

    def validate_token(self, token_id: str, agent_id: str, operation: str) -> bool:
        """
        Valida um token de capacidade

        Args:
            token_id: ID do token
            agent_id: ID do agente que está usando o token
            operation: Operação que está sendo executada

        Returns:
            True se o token é válido, False caso contrário
        """
        # Verifica cache em memória primeiro
        if token_id in self.memory_cache:
            token = self.memory_cache[token_id]
            return self._validate_token_object(token, agent_id, operation)

        # Verifica Redis se disponível
        if self.redis:
            try:
                token_key = f"capability_token:{token_id}"
                token_data = self.redis.get(token_key)

                if token_data:
                    token_dict = json.loads(token_data)
                    token = CapabilityToken.from_dict(token_dict)

                    # Armazena em cache para futuro uso
                    self.memory_cache[token_id] = token

                    return self._validate_token_object(token, agent_id, operation)

            except Exception as e:
                logger.warning(f"Falha ao validar token no Redis: {str(e)}")

        logger.warning(f"Token não encontrado ou inválido: {token_id}")
        return False

    def _validate_token_object(self, token: CapabilityToken, agent_id: str, operation: str) -> bool:
        """
        Valida um objeto de token
        """
        # Verifica se o token é válido
        if not token.is_valid():
            logger.warning(f"Token inválido: {token.token_id} - {'usado' if token.used else 'expirado'}")
            return False

        # Verifica se o agente e operação correspondem
        if token.agent_id != agent_id:
            logger.warning(f"Token {token.token_id} inválido para agente {agent_id} (esperado {token.agent_id})")
            return False

        if token.operation != operation:
            logger.warning(f"Token {token.token_id} inválido para operação {operation} (esperado {token.operation})")
            return False

        # Marca token como usado
        token.mark_used()

        # Atualiza token no armazenamento
        self._update_token(token)

        logger.info(f"Token validado com sucesso: {token.token_id} para {agent_id} - {operation}")
        return True

    def _update_token(self, token: CapabilityToken):
        """
        Atualiza token no armazenamento após uso
        """
        # Atualiza cache em memória
        self.memory_cache[token.token_id] = token

        # Atualiza Redis se disponível
        if self.redis:
            try:
                token_key = f"capability_token:{token.token_id}"
                ttl = max(0, int((token.expires_at - datetime.utcnow()).total_seconds()))

                if ttl > 0:
                    self.redis.setex(token_key, ttl, json.dumps(token.to_dict()))
                else:
                    # Token expirado, remove do Redis
                    self.redis.delete(token_key)

            except Exception as e:
                logger.warning(f"Falha ao atualizar token no Redis: {str(e)}")

    def revoke_token(self, token_id: str):
        """
        Revoga um token de capacidade

        Args:
            token_id: ID do token a ser revogado
        """
        # Remove do cache em memória
        if token_id in self.memory_cache:
            del self.memory_cache[token_id]

        # Remove do Redis se disponível
        if self.redis:
            try:
                token_key = f"capability_token:{token_id}"
                self.redis.delete(token_key)
                logger.info(f"Token revogado: {token_id}")
            except Exception as e:
                logger.warning(f"Falha ao revogar token no Redis: {str(e)}")

    def list_active_tokens(self, agent_id: str | None = None) -> list[dict[str, any]]:
        """
        Lista tokens ativos

        Args:
            agent_id: Filtra por ID do agente (None para todos)

        Returns:
            Lista de tokens ativos
        """
        active_tokens = []

        # Verifica cache em memória
        for _token_id, token in self.memory_cache.items():
            if token.is_valid() and (agent_id is None or token.agent_id == agent_id):
                active_tokens.append(token.to_dict())

        # Se tivermos muitos tokens, também verifica Redis
        if self.redis and len(active_tokens) < 100:  # Limite para evitar sobrecarga
            try:
                pattern = "capability_token:*" if agent_id is None else f"capability_token:*_{agent_id}_*"
                keys = self.redis.keys(pattern)

                for key in keys:
                    try:
                        token_data = self.redis.get(key)
                        if token_data:
                            token_dict = json.loads(token_data)
                            token = CapabilityToken.from_dict(token_dict)
                            if token.is_valid() and (agent_id is None or token.agent_id == agent_id):
                                if not any(t["token_id"] == token.token_id for t in active_tokens):
                                    active_tokens.append(token.to_dict())
                    except Exception:
                        continue

            except Exception as e:
                logger.warning(f"Falha ao listar tokens no Redis: {str(e)}")

        return active_tokens

    def cleanup_expired_tokens(self):
        """
        Limpa tokens expirados do cache em memória
        """
        datetime.utcnow()
        expired_tokens = []

        for token_id, token in self.memory_cache.items():
            if not token.is_valid():
                expired_tokens.append(token_id)

        for token_id in expired_tokens:
            del self.memory_cache[token_id]

        if expired_tokens:
            logger.info(f"Tokens expirados removidos do cache: {len(expired_tokens)}")
