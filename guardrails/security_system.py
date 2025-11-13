"""
Sistema de Segurança e Guardrails - Verifica e restringe operações perigosas
"""

import fnmatch
import json
import logging
import os
from datetime import datetime

from config.constants import (
    ALLOWED_SYSTEM_COMMANDS,
    CRITICAL_OPERATIONS,
    DANGEROUS_PORTS,
    PROTECTED_FILE_PATTERNS,
)

from .capability_tokens import CapabilityTokenManager

logger = logging.getLogger("DEVs_AI")


class GuardrailSystem:
    """
    Sistema de guardrails para segurança e controle de operações
    """

    def __init__(self, token_manager: CapabilityTokenManager):
        self.token_manager = token_manager

        # Carrega constantes do config
        self.critical_operations = CRITICAL_OPERATIONS
        self.protected_file_patterns = PROTECTED_FILE_PATTERNS
        self.allowed_commands = ALLOWED_SYSTEM_COMMANDS  # WHITELIST ao invés de blacklist
        self.dangerous_ports = DANGEROUS_PORTS

        # Dicionário de restrições por agente
        self.agent_restrictions = {
            "agent1": ["file_modification", "system_command", "network_request"],
            "agent2": ["file_modification", "system_command", "network_request"],
            "agent3": ["file_modification", "system_command"],
            "agent4": ["system_command", "sudo_operation"],
            "agent5": ["file_deletion"],
            "agent6": ["git_push"],
            "agent7": [],
            "agent8": ["git_push"],
        }

        logger.info("✅ GuardrailSystem inicializado com sucesso")

    async def check_permission(self, agent_id: str, operation: str, context: dict[str, any]) -> tuple[bool, str | None]:
        """
        Verifica se o agente tem permissão para executar a operação

        Args:
            agent_id: ID do agente
            operation: Operação a ser executada
            context: Contexto da operação

        Returns:
            Tupla (permitido, motivo) onde motivo é None se permitido
        """
        try:
            # Verifica restrições específicas do agente
            if operation in self.agent_restrictions.get(agent_id, []):
                return False, f"Operação {operation} proibida para o agente {agent_id}"

            # Verifica operações críticas que requerem capability tokens
            if operation in self.critical_operations:
                token_id = context.get("capability_token")
                if not token_id or not self.token_manager.validate_token(token_id, agent_id, operation):
                    return (
                        False,
                        f"Token de capacidade requerido para operação crítica: {operation}",
                    )

            # Verifica operações específicas
            if operation == "file_modification":
                return await self._check_file_modification_permissions(agent_id, context)
            elif operation == "file_deletion":
                return await self._check_file_deletion_permissions(agent_id, context)
            elif operation == "system_command":
                return await self._check_system_command_permissions(agent_id, context)
            elif operation == "network_request":
                return await self._check_network_permissions(agent_id, context)
            elif operation == "git_push":
                return await self._check_git_permissions(agent_id, context)

            # Permissão concedida para operações não críticas
            return True, None

        except Exception as e:
            logger.error(f"Erro ao verificar permissão para {agent_id} - {operation}: {str(e)}")
            return False, f"Erro interno no sistema de segurança: {str(e)}"

    async def _check_file_modification_permissions(self, agent_id: str, context: dict[str, any]) -> tuple[bool, str]:
        """
        Verifica permissões para modificação de arquivos
        """
        file_path = context.get("file_path", "")
        content = context.get("content", "")

        # Normaliza o path para prevenir path traversal
        try:
            normalized_path = os.path.normpath(os.path.abspath(file_path))
            # Verifica se o path normalizado ainda está dentro do workspace
            workspace_root = os.path.abspath(".")
            if not normalized_path.startswith(workspace_root):
                return False, f"Acesso fora do workspace não permitido: {file_path}"
        except Exception:
            return False, f"Path inválido: {file_path}"

        # Verifica se é um arquivo protegido
        for pattern in self.protected_file_patterns:
            if fnmatch.fnmatch(os.path.basename(file_path), pattern) or fnmatch.fnmatch(file_path, pattern):
                return (
                    False,
                    f"Modificação proibida para arquivo protegido: {file_path}",
                )

        # Verifica se o conteúdo contém padrões suspeitos
        suspicious_patterns = [
            "os.system",
            "subprocess.call",
            "eval(",
            "exec(",
            "import os",
            "import sys",
            "import subprocess",
            "chmod",
            "chown",
            "rm -rf",
            "sudo",
            "apt-get",
            "curl ",
            "wget ",
            "nc ",
            "netcat",
            "telnet",
        ]

        for pattern in suspicious_patterns:
            if pattern in content.lower():
                return (
                    False,
                    f"Conteúdo suspeito detectado no arquivo {file_path}: {pattern}",
                )

        # Verifica tamanho do arquivo (limita arquivos muito grandes)
        if len(content) > 100000:  # 100KB
            return (
                False,
                f"Tamanho de arquivo muito grande para modificação automática: {len(content)} bytes",
            )

        return True, ""

    async def _check_file_deletion_permissions(self, agent_id: str, context: dict[str, any]) -> tuple[bool, str]:
        """
        Verifica permissões para deleção de arquivos
        """
        file_path = context.get("file_path", "")

        # Normaliza o path para prevenir path traversal
        try:
            normalized_path = os.path.normpath(os.path.abspath(file_path))
            workspace_root = os.path.abspath(".")
            if not normalized_path.startswith(workspace_root):
                return False, f"Acesso fora do workspace não permitido: {file_path}"
        except Exception:
            return False, f"Path inválido: {file_path}"

        # Verifica se é um arquivo protegido
        for pattern in self.protected_file_patterns:
            if fnmatch.fnmatch(os.path.basename(file_path), pattern) or fnmatch.fnmatch(file_path, pattern):
                return False, f"Deleção proibida para arquivo protegido: {file_path}"

        # Verifica se é um arquivo de código fonte crítico
        if file_path.endswith((".py", ".js", ".ts", ".java", ".cpp", ".h", ".go", ".rs")):
            # Permite deleção apenas se for um arquivo temporário ou de teste
            if not any(x in file_path.lower() for x in ["temp", "test", "tmp", "backup", "old"]):
                return (
                    False,
                    f"Não é permitido deletar arquivos de código fonte principais: {file_path}",
                )

        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            return False, f"Arquivo não existe: {file_path}"

        return True, ""

    async def _check_system_command_permissions(self, agent_id: str, context: dict[str, any]) -> tuple[bool, str]:
        """
        Verifica permissões para execução de comandos de sistema usando WHITELIST
        """
        command = context.get("command", "").strip()

        if not command:
            return False, "Comando vazio não permitido"

        if self._has_dangerous_chars(command):
            return False, f"Comando contém caracteres perigosos não permitidos: {command}"

        command_parts = command.split()
        if not command_parts:
            return False, "Comando inválido"

        command_name = command_parts[0].lower()

        if command_name not in self.allowed_commands:
            return (
                False,
                f"Comando '{command_name}' não está na whitelist. Permitidos: {', '.join(self.allowed_commands)}",
            )

        sensitive_check = self._check_sensitive_paths(command_parts[1:])
        if not sensitive_check[0]:
            return sensitive_check

        traversal_check = self._check_path_traversal(command_parts[1:])
        if not traversal_check[0]:
            return traversal_check

        return True, ""

    def _has_dangerous_chars(self, command: str) -> bool:
        """Verifica se comando contém caracteres perigosos"""
        dangerous_chars = [">", ">>", "<", "|", "&", ";", "`", "$", "(", ")", "{", "}", "[", "]", "\\", "\n", "\r"]
        return any(char in command for char in dangerous_chars)

    def _check_sensitive_paths(self, args: list[str]) -> tuple[bool, str]:
        """Verifica acesso a diretórios sensíveis"""
        sensitive_patterns = ["/etc", "/root", "/var/log", "/.ssh", "/.gnupg", "/proc", "/sys"]
        for part in args:
            for pattern in sensitive_patterns:
                if pattern in part.lower():
                    return False, f"Acesso a diretório sensível não permitido: {part}"
        return True, ""

    def _check_path_traversal(self, args: list[str]) -> tuple[bool, str]:
        """Verifica tentativas de path traversal"""
        for part in args:
            if ".." in part or part.startswith("/"):
                try:
                    if os.path.isabs(part) or ".." in part:
                        normalized = os.path.normpath(os.path.abspath(part))
                        workspace = os.path.abspath(".")
                        if not normalized.startswith(workspace):
                            return False, f"Acesso fora do workspace não permitido: {part}"
                except Exception:
                    return False, f"Argumento inválido: {part}"
        return True, ""

    async def _check_network_permissions(self, agent_id: str, context: dict[str, any]) -> tuple[bool, str]:
        """
        Verifica permissões para requisições de rede
        """
        url = context.get("url", "")
        port = context.get("port")

        # Bloqueia URLs locais e internas
        local_patterns = [
            "localhost",
            "127.0.0.1",
            "192.168.",
            "10.",
            "172.16.",
            "172.31.",
        ]
        for pattern in local_patterns:
            if pattern in url.lower():
                return False, f"Requisições para endereços locais não permitidas: {url}"

        # Bloqueia portas perigosas
        if port in self.dangerous_ports:
            return False, f"Requisições para portas perigosas não permitidas: {port}"

        # Permite apenas protocolos seguros
        if not url.startswith(("https://", "wss://")):
            return (
                False,
                f"Apenas requisições seguras (HTTPS/WSS) são permitidas: {url}",
            )

        # Bloqueia URLs suspeitas
        suspicious_patterns = [
            "admin",
            "login",
            "password",
            "credential",
            "secret",
            "token",
            "auth",
        ]
        for pattern in suspicious_patterns:
            if pattern in url.lower():
                return False, f"URL suspeita detectada: {url}"

        return True, ""

    async def _check_git_permissions(self, agent_id: str, context: dict[str, any]) -> tuple[bool, str]:
        """
        Verifica permissões para operações git
        """
        action = context.get("action", "push")
        branch = context.get("branch", "main")
        changes = context.get("changes", [])

        # Bloqueia pushes para branches protegidas
        protected_branches = ["main", "master", "production", "prod", "release"]
        if action == "push" and branch.lower() in protected_branches:
            return False, f"Push proibido para branch protegida: {branch}"

        # Verifica número de mudanças
        if len(changes) > 50:
            return (
                False,
                f"Muitas mudanças para push único ({len(changes)}). Limite: 50",
            )

        # Verifica tamanho das mudanças
        total_size = sum(len(str(change)) for change in changes)
        if total_size > 10000:  # 10KB
            return (
                False,
                f"Tamanho total das mudanças muito grande ({total_size} bytes). Limite: 10KB",
            )

        # Verifica mudanças em arquivos protegidos
        for change in changes:
            file_path = change.get("file_path", "")
            for pattern in self.protected_file_patterns:
                if fnmatch.fnmatch(file_path, pattern):
                    return (
                        False,
                        f"Mudança em arquivo protegido não permitida: {file_path}",
                    )

        return True, ""

    def should_sandbox_execution(self, operation: str, context: dict[str, any]) -> bool:
        """
        Determina se uma operação deve ser executada em sandbox

        Args:
            operation: Operação a ser executada
            context: Contexto da operação

        Returns:
            True se deve usar sandbox, False caso contrário
        """
        sandbox_operations = [
            "code_execution",
            "script_execution",
            "plugin_execution",
            "dynamic_import",
            "eval_code",
        ]

        return operation in sandbox_operations

    def log_security_event(
        self,
        event_type: str,
        agent_id: str,
        operation: str,
        context: dict[str, any],
        allowed: bool,
        reason: str = None,
    ):
        """
        Registra evento de segurança para auditoria
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "agent_id": agent_id,
            "operation": operation,
            "context": context,
            "allowed": allowed,
            "reason": reason,
        }

        log_level = logging.INFO if allowed else logging.WARNING
        logger.log(log_level, f"Evento de segurança: {json.dumps(event)}")

        # Em produção, aqui enviaria para um sistema de SIEM ou segurança
        if not allowed and "critical" in event_type.lower():
            self._alert_security_team(event)

    def _alert_security_team(self, event: dict[str, any]):
        """
        Alerta equipe de segurança sobre evento crítico
        """
        logger.critical(f"ALERTA DE SEGURANÇA CRÍTICO: {json.dumps(event)}")
        # Em implementação real, aqui enviaria email, slack, etc.

    def get_agent_permissions(self, agent_id: str) -> dict[str, any]:
        """
        Retorna permissões e restrições para um agente específico

        Args:
            agent_id: ID do agente

        Returns:
            Dicionário com permissões e restrições
        """
        return {
            "agent_id": agent_id,
            "critical_operations_allowed": [
                op for op in self.critical_operations if op not in self.agent_restrictions.get(agent_id, [])
            ],
            "restricted_operations": self.agent_restrictions.get(agent_id, []),
            "protected_files": self.protected_file_patterns,
            "forbidden_commands": self.forbidden_commands,
            "dangerous_ports": self.dangerous_ports,
        }

    def get_security_status(self) -> dict[str, any]:
        """
        Retorna status atual do sistema de segurança
        """
        active_tokens = self.token_manager.list_active_tokens()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_tokens_count": len(active_tokens),
            "critical_operations_count": len(self.critical_operations),
            "protected_file_patterns_count": len(self.protected_file_patterns),
            "forbidden_commands_count": len(self.forbidden_commands),
            "agent_restrictions_summary": {
                agent_id: len(restrictions) for agent_id, restrictions in self.agent_restrictions.items()
            },
        }
