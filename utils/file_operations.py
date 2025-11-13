"""
Operações de Arquivo - Utilitários seguros para manipulação de arquivos e diretórios
"""

import os
import logging
import json
import yaml
import shutil
import re
import fnmatch
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import datetime
import hashlib
from contextlib import contextmanager
import tempfile
import filelock

logger = logging.getLogger("DEVs_AI")

class FileAccessError(Exception):
    """Exceção personalizada para erros de acesso a arquivos"""
    pass

class FileIntegrityError(Exception):
    """Exceção para erros de integridade de arquivos"""
    pass

class SafeFileOperations:
    """
    Operações seguras de arquivos com validações e fallbacks
    """
    
    def __init__(self, base_dir: str = None, max_file_size_mb: int = 50):
        """
        Inicializa operações seguras de arquivos
        
        Args:
            base_dir: Diretório base para operações (None para diretório atual)
            max_file_size_mb: Tamanho máximo de arquivo em MB
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.max_file_size_mb = max_file_size_mb
        self.backup_dir = self.base_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.lock_dir = self.base_dir / ".locks"
        self.lock_dir.mkdir(exist_ok=True)
        
        # Padrões de arquivos protegidos
        self.protected_patterns = [
            '*.pyc', '*.pyo', '__pycache__/*', '.git/*', '.env',
            'config/*', 'secrets/*', 'credentials/*', '*password*',
            '*secret*', '*key*', '*token*', '.ssh/*', '.gnupg/*'
        ]
        
        logger.info(f"SafeFileOperations inicializado com base_dir: {self.base_dir}")
    
    def is_file_protected(self, file_path: Union[str, Path]) -> bool:
        """
        Verifica se um arquivo é protegido e não deve ser modificado
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            True se o arquivo é protegido, False caso contrário
        """
        file_path = Path(file_path).as_posix()
        rel_path = Path(file_path).relative_to(self.base_dir).as_posix() if self.base_dir in Path(file_path).parents else file_path
        
        for pattern in self.protected_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(Path(file_path).name, pattern):
                return True
        
        # Verifica conteúdo do arquivo para dados sensíveis
        try:
            if self._contains_sensitive_data(file_path):
                return True
        except Exception as e:
            logger.warning(f"Erro ao verificar conteúdo sensível em {file_path}: {str(e)}")
        
        return False
    
    def _contains_sensitive_data(self, file_path: str) -> bool:
        """
        Verifica se arquivo contém dados sensíveis
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            True se contém dados sensíveis, False caso contrário
        """
        try:
            if not Path(file_path).exists() or Path(file_path).stat().st_size == 0:
                return False
            
            # Lê apenas as primeiras 100 linhas para verificar dados sensíveis
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i > 100:
                        break
                    
                    line_lower = line.lower()
                    sensitive_patterns = [
                        'password', 'passphrase', 'secret', 'api_key', 'api-key',
                        'access_token', 'refresh_token', 'auth_token', 'credential',
                        'private_key', 'ssh-rsa', 'BEGIN PRIVATE KEY', 'BEGIN RSA PRIVATE KEY'
                    ]
                    
                    for pattern in sensitive_patterns:
                        if pattern in line_lower:
                            # Verifica se não é um comentário ou string de documentação
                            if not (line.strip().startswith(('#', '//', '/*', '*')) or
                                    'example' in line_lower or
                                    'test' in line_lower):
                                return True
        
        except Exception as e:
            logger.warning(f"Erro ao verificar conteúdo sensível: {str(e)}")
        
        return False
    
    @contextmanager
    def safe_file_lock(self, file_path: Union[str, Path]):
        """
        Context manager para lock seguro de arquivo
        
        Args:
            file_path: Caminho do arquivo para lock
        """
        file_path = Path(file_path)
        lock_path = self.lock_dir / f"{file_path.name}.lock"
        lock = filelock.FileLock(lock_path)
        
        try:
            lock.acquire(timeout=10)
            yield
        finally:
            lock.release()
            # Remove lock file se não estiver sendo usado
            if lock_path.exists() and not lock.is_locked:
                try:
                    lock_path.unlink()
                except:
                    pass
    
    def create_backup(self, file_path: Union[str, Path], max_backups: int = 5) -> Path:
        """
        Cria backup de arquivo com versionamento
        
        Args:
            file_path: Caminho do arquivo para backup
            max_backups: Número máximo de backups a manter
            
        Returns:
            Caminho do arquivo de backup criado
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado para backup: {file_path}")
        
        # Cria nome do backup com timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        # Cria backup
        with self.safe_file_lock(file_path):
            shutil.copy2(file_path, backup_path)
        
        logger.info(f"Backup criado: {backup_path}")
        
        # Limpa backups antigos
        self._cleanup_old_backups(file_path.stem, max_backups)
        
        return backup_path
    
    def _cleanup_old_backups(self, file_stem: str, max_backups: int):
        """
        Limpa backups antigos mantendo apenas os mais recentes
        
        Args:
            file_stem: Nome base do arquivo
            max_backups: Número máximo de backups a manter
        """
        try:
            # Encontra todos os backups do arquivo
            backup_pattern = f"{file_stem}_*.*"
            backups = list(self.backup_dir.glob(backup_pattern))
            
            # Ordena por data de modificação (mais recente primeiro)
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove backups excedentes
            for backup in backups[max_backups:]:
                try:
                    backup.unlink()
                    logger.info(f"Backup antigo removido: {backup}")
                except Exception as e:
                    logger.warning(f"Erro ao remover backup {backup}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Erro ao limpar backups antigos: {str(e)}")
    
    def read_file(self, file_path: Union[str, Path], 
                 binary: bool = False, max_size_mb: int = None) -> Union[str, bytes]:
        """
        Lê arquivo com validações de segurança
        
        Args:
            file_path: Caminho do arquivo
            binary: True para leitura binária, False para texto
            max_size_mb: Tamanho máximo permitido em MB (None usa configuração padrão)
            
        Returns:
            Conteúdo do arquivo como string ou bytes
        """
        file_path = Path(file_path)
        max_size = max_size_mb if max_size_mb is not None else self.max_file_size_mb
        
        # Validações de segurança
        self._validate_file_access(file_path, 'read')
        
        # Verifica tamanho do arquivo
        if file_path.exists():
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > max_size:
                raise FileAccessError(f"Arquivo muito grande ({file_size_mb:.1f}MB > {max_size}MB): {file_path}")
        
        # Lê arquivo
        try:
            if binary:
                with open(file_path, 'rb') as f:
                    return f.read()
            else:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
        except Exception as e:
            raise FileAccessError(f"Erro ao ler arquivo {file_path}: {str(e)}")
    
    def write_file(self, file_path: Union[str, Path], content: Union[str, bytes], 
                  create_backup: bool = True, binary: bool = False) -> bool:
        """
        Escreve arquivo com validações de segurança e backup
        
        Args:
            file_path: Caminho do arquivo
            content: Conteúdo a ser escrito
            create_backup: True para criar backup antes de escrever
            binary: True para escrita binária, False para texto
            
        Returns:
            True se operação foi bem-sucedida
        """
        file_path = Path(file_path)
        
        # Validações de segurança
        self._validate_file_access(file_path, 'write')
        
        # Cria diretório pai se não existir
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Cria backup se necessário e arquivo existe
        if create_backup and file_path.exists():
            self.create_backup(file_path)
        
        # Escreve arquivo
        try:
            with self.safe_file_lock(file_path):
                mode = 'wb' if binary else 'w'
                encoding = None if binary else 'utf-8'
                
                with open(file_path, mode, encoding=encoding) as f:
                    f.write(content)
            
            logger.info(f"Arquivo escrito com sucesso: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao escrever arquivo {file_path}: {str(e)}")
            # Tenta restaurar do backup mais recente
            self._restore_from_latest_backup(file_path)
            raise FileAccessError(f"Erro ao escrever arquivo {file_path}: {str(e)}")
    
    def _validate_file_access(self, file_path: Path, operation: str):
        """
        Valida acesso a arquivo com verificações de segurança
        
        Args:
            file_path: Caminho do arquivo
            operation: Operação ('read', 'write', 'delete')
        """
        # Valida caminho absoluto
        if not file_path.is_absolute():
            file_path = self.base_dir / file_path
        
        # Verifica se está dentro do diretório base
        try:
            file_path.relative_to(self.base_dir)
        except ValueError:
            raise FileAccessError(f"Acesso fora do diretório base não permitido: {file_path}")
        
        # Verifica arquivo protegido
        if self.is_file_protected(file_path):
            raise FileAccessError(f"Acesso negado a arquivo protegido: {file_path}")
        
        # Verifica existência para operações de leitura
        if operation == 'read' and not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    
    def _restore_from_latest_backup(self, file_path: Path):
        """
        Restaura arquivo do backup mais recente
        
        Args:
            file_path: Caminho do arquivo para restaurar
        """
        try:
            # Encontra backups do arquivo
            file_stem = file_path.stem
            backup_pattern = f"{file_stem}_*{file_path.suffix}"
            backups = list(self.backup_dir.glob(backup_pattern))
            
            if not backups:
                return
            
            # Ordena por data de modificação (mais recente primeiro)
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Restaura do backup mais recente
            latest_backup = backups[0]
            with self.safe_file_lock(file_path):
                shutil.copy2(latest_backup, file_path)
            
            logger.info(f"Arquivo restaurado do backup: {file_path} <- {latest_backup}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao restaurar arquivo do backup: {str(e)}")
            return False
    
    def delete_file(self, file_path: Union[str, Path], create_backup: bool = True) -> bool:
        """
        Deleta arquivo com segurança e backup
        
        Args:
            file_path: Caminho do arquivo
            create_backup: True para criar backup antes de deletar
            
        Returns:
            True se operação foi bem-sucedida
        """
        file_path = Path(file_path)
        
        # Validações de segurança
        self._validate_file_access(file_path, 'delete')
        
        # Cria backup
        if create_backup and file_path.exists():
            self.create_backup(file_path)
        
        # Deleta arquivo
        try:
            with self.safe_file_lock(file_path):
                file_path.unlink()
            
            logger.info(f"Arquivo deletado com sucesso: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao deletar arquivo {file_path}: {str(e)}")
            raise FileAccessError(f"Erro ao deletar arquivo {file_path}: {str(e)}")
    
    def safe_directory_listing(self, dir_path: Union[str, Path], 
                              max_depth: int = 3, max_items: int = 1000) -> List[Dict[str, Any]]:
        """
        Lista diretório de forma segura com limites
        
        Args:
            dir_path: Caminho do diretório
            max_depth: Profundidade máxima de listagem
            max_items: Número máximo de itens a listar
            
        Returns:
            Lista de informações sobre arquivos e diretórios
        """
        dir_path = Path(dir_path)
        if not dir_path.is_absolute():
            dir_path = self.base_dir / dir_path
        
        # Validações de segurança
        try:
            dir_path.relative_to(self.base_dir)
        except ValueError:
            raise FileAccessError(f"Acesso fora do diretório base não permitido: {dir_path}")
        
        if not dir_path.exists() or not dir_path.is_dir():
            raise FileNotFoundError(f"Diretório não encontrado ou inválido: {dir_path}")
        
        # Lista itens com limites
        items = []
        count = 0
        
        for root, dirs, files in os.walk(dir_path):
            # Verifica profundidade
            depth = len(Path(root).relative_to(dir_path).parts) if root != str(dir_path) else 0
            if depth > max_depth:
                continue
            
            # Processa arquivos
            for file_name in files:
                if count >= max_items:
                    break
                
                file_path = Path(root) / file_name
                try:
                    stat = file_path.stat()
                    items.append({
                        'type': 'file',
                        'path': file_path.relative_to(self.base_dir).as_posix(),
                        'name': file_name,
                        'size': stat.st_size,
                        'mtime': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'protected': self.is_file_protected(file_path)
                    })
                    count += 1
                except Exception as e:
                    logger.warning(f"Erro ao obter informações de {file_path}: {str(e)}")
            
            # Processa diretórios
            for dir_name in dirs:
                if count >= max_items:
                    break
                
                dir_path_item = Path(root) / dir_name
                try:
                    stat = dir_path_item.stat()
                    items.append({
                        'type': 'directory',
                        'path': dir_path_item.relative_to(self.base_dir).as_posix(),
                        'name': dir_name,
                        'size': 0,  # Diretórios não têm tamanho direto
                        'mtime': datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'protected': self.is_file_protected(dir_path_item)
                    })
                    count += 1
                except Exception as e:
                    logger.warning(f"Erro ao obter informações de {dir_path_item}: {str(e)}")
            
            if count >= max_items:
                break
        
        return items
    
    def get_file_hash(self, file_path: Union[str, Path], algorithm: str = 'sha256') -> str:
        """
        Calcula hash de arquivo para verificação de integridade
        
        Args:
            file_path: Caminho do arquivo
            algorithm: Algoritmo de hash ('md5', 'sha1', 'sha256', 'sha512')
            
        Returns:
            Hash do arquivo como string hexadecimal
        """
        file_path = Path(file_path)
        self._validate_file_access(file_path, 'read')
        
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        hash_func = getattr(hashlib, algorithm)()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
            
        except Exception as e:
            raise FileIntegrityError(f"Erro ao calcular hash de {file_path}: {str(e)}")
    
    def verify_file_integrity(self, file_path: Union[str, Path], 
                             expected_hash: str, algorithm: str = 'sha256') -> bool:
        """
        Verifica integridade de arquivo comparando hash
        
        Args:
            file_path: Caminho do arquivo
            expected_hash: Hash esperado
            algorithm: Algoritmo de hash
            
        Returns:
            True se hash corresponde, False caso contrário
        """
        actual_hash = self.get_file_hash(file_path, algorithm)
        return actual_hash.lower() == expected_hash.lower()
    
    def safe_json_read(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Lê arquivo JSON com tratamento de erros
        
        Args:
            file_path: Caminho do arquivo JSON
            
        Returns:
            Dicionário com conteúdo do JSON
        """
        content = self.read_file(file_path)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise FileIntegrityError(f"Erro ao decodificar JSON em {file_path}: {str(e)}")
    
    def safe_json_write(self, file_path: Union[str, Path], data: Dict[str, Any], 
                       indent: int = 2, create_backup: bool = True) -> bool:
        """
        Escreve arquivo JSON com tratamento de erros
        
        Args:
            file_path: Caminho do arquivo JSON
            data: Dados para escrever
            indent: Número de espaços para indentação
            create_backup: True para criar backup antes de escrever
            
        Returns:
            True se operação foi bem-sucedida
        """
        try:
            content = json.dumps(data, indent=indent, ensure_ascii=False)
            return self.write_file(file_path, content, create_backup=create_backup)
        except (TypeError, ValueError) as e:
            raise FileIntegrityError(f"Erro ao serializar JSON: {str(e)}")
    
    def safe_yaml_read(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Lê arquivo YAML com tratamento de erros
        
        Args:
            file_path: Caminho do arquivo YAML
            
        Returns:
            Dicionário com conteúdo do YAML
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("Biblioteca PyYAML não instalada")
        
        content = self.read_file(file_path)
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise FileIntegrityError(f"Erro ao decodificar YAML em {file_path}: {str(e)}")
    
    def safe_yaml_write(self, file_path: Union[str, Path], data: Dict[str, Any], 
                       create_backup: bool = True) -> bool:
        """
        Escreve arquivo YAML com tratamento de erros
        
        Args:
            file_path: Caminho do arquivo YAML
            data: Dados para escrever
            create_backup: True para criar backup antes de escrever
            
        Returns:
            True se operação foi bem-sucedida
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("Biblioteca PyYAML não instalada")
        
        try:
            content = yaml.dump(data, sort_keys=False, allow_unicode=True)
            return self.write_file(file_path, content, create_backup=create_backup)
        except (TypeError, ValueError) as e:
            raise FileIntegrityError(f"Erro ao serializar YAML: {str(e)}")
    
    def create_temporary_copy(self, file_path: Union[str, Path]) -> Path:
        """
        Cria cópia temporária de arquivo
        
        Args:
            file_path: Caminho do arquivo original
            
        Returns:
            Caminho do arquivo temporário
        """
        file_path = Path(file_path)
        self._validate_file_access(file_path, 'read')
        
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        # Cria arquivo temporário
        suffix = file_path.suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        # Copia conteúdo
        with self.safe_file_lock(file_path):
            shutil.copy2(file_path, temp_path)
        
        logger.info(f"Cópia temporária criada: {file_path} -> {temp_path}")
        return temp_path
    
    def atomic_update(self, file_path: Union[str, Path], update_func: callable) -> bool:
        """
        Atualiza arquivo atomicamente usando função de atualização
        
        Args:
            file_path: Caminho do arquivo
            update_func: Função que recebe o conteúdo atual e retorna novo conteúdo
            
        Returns:
            True se operação foi bem-sucedida
        """
        file_path = Path(file_path)
        
        # Lê conteúdo atual
        current_content = self.read_file(file_path) if file_path.exists() else ""
        
        # Aplica atualização
        try:
            new_content = update_func(current_content)
        except Exception as e:
            raise FileAccessError(f"Erro na função de atualização: {str(e)}")
        
        # Verifica se conteúdo mudou
        if new_content == current_content:
            logger.info(f"Sem mudanças no arquivo: {file_path}")
            return False
        
        # Cria arquivo temporário
        temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
        
        try:
            # Escreve no arquivo temporário
            self.write_file(temp_path, new_content, create_backup=False)
            
            # Verifica integridade do arquivo temporário
            if not temp_path.exists() or temp_path.stat().st_size == 0:
                raise FileIntegrityError("Arquivo temporário vazio ou não criado")
            
            # Move atomicamente
            with self.safe_file_lock(file_path):
                if file_path.exists():
                    file_path.unlink()
                temp_path.rename(file_path)
            
            logger.info(f"Atualização atômica concluída: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro na atualização atômica de {file_path}: {str(e)}")
            # Limpa arquivo temporário
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except:
                pass
            raise

# Instância global para uso no sistema
safe_file_operations = SafeFileOperations()

class CodeParser:
    """
    Parser de código para análise e transformação segura
    """
    
    def __init__(self):
        self.language_patterns = {
            'python': {
                'imports': r'^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)',
                'functions': r'^\s*def\s+([a-zA-Z0-9_]+)\s*\(',
                'classes': r'^\s*class\s+([a-zA-Z0-9_]+)',
                'comments': r'#.*$|\'\'\'[\s\S]*?\'\'\'|\"\"\"[\s\S]*?\"\"\"',
                'strings': r'\".*?\"|\'.*?\''
            },
            'javascript': {
                'imports': r'^\s*(?:import|export)\s+(?:.*?from\s+)?[\'"]([a-zA-Z0-9_\-\.\/]+)[\'"]',
                'functions': r'^\s*(?:function\s+([a-zA-Z0-9_]+)|const\s+([a-zA-Z0-9_]+)\s*=\s*\([^)]*\)\s*=>)',
                'classes': r'^\s*class\s+([a-zA-Z0-9_]+)',
                'comments': r'//.*$|/\*[\s\S]*?\*/',
                'strings': r'\".*?\"|\'.*?\'|`.*?`'
            },
            'typescript': {
                'imports': r'^\s*(?:import|export)\s+(?:.*?from\s+)?[\'"]([a-zA-Z0-9_\-\.\/]+)[\'"]',
                'functions': r'^\s*(?:function\s+([a-zA-Z0-9_]+)|const\s+([a-zA-Z0-9_]+)\s*=\s*\([^)]*\)\s*=>)',
                'classes': r'^\s*class\s+\b([a-zA-Z0-9_]+)\b',
                'interfaces': r'^\s*interface\s+(\w+)',
                'types': r'^\s*type\s+(\w+)\s+=',
                'comments': r'//.*$|/\*[\s\S]*?\*/',
                'strings': r'\".*?\"|\'.*?\'|`.*?`'
            },
            'java': {
                'imports': r'^\s*import\s+([a-zA-Z0-9_\.]+);',
                'functions': r'^\s*(?:public|private|protected|static)?\s*(?:\w+\s+)*?([a-zA-Z0-9_]+)\s*\(',
                'classes': r'^\s*(?:public|private|protected)?\s*class\s+(\w+)',
                'comments': r'//.*$|/\*[\s\S]*?\*/',
                'strings': r'\".*?\"'
            }
        }
    
    def detect_language(self, code: str) -> str:
        """
        Detecta linguagem de programação do código
        
        Args:
            code: Código fonte
            
        Returns:
            Nome da linguagem detectada
        """
        code_lower = code.lower()
        
        # Verifica padrões específicos
        if 'import ' in code_lower or 'def ' in code_lower or 'class ' in code_lower:
            if 'function ' in code_lower or 'const ' in code_lower or 'let ' in code_lower:
                return 'javascript'
            return 'python'
        elif 'function ' in code_lower or 'const ' in code_lower or 'let ' in code_lower:
            if ':' in code_lower or 'interface ' in code_lower or 'type ' in code_lower:
                return 'typescript'
            return 'javascript'
        elif 'public class ' in code_lower or 'private class ' in code_lower:
            return 'java'
        elif '#include' in code_lower or 'namespace ' in code_lower:
            return 'cpp'
        elif 'package ' in code_lower and 'func ' in code_lower:
            return 'go'
        
        return 'unknown'
    
    def extract_imports(self, code: str, language: str = None) -> List[str]:
        """
        Extrai imports de código
        
        Args:
            code: Código fonte
            language: Linguagem de programação (None para detectar automaticamente)
            
        Returns:
            Lista de imports
        """
        if language is None:
            language = self.detect_language(code)
        
        if language not in self.language_patterns:
            return []
        
        pattern = self.language_patterns[language].get('imports', '')
        if not pattern:
            return []
        
        try:
            import re
            matches = re.findall(pattern, code, re.MULTILINE)
            return list(set(matches))  # Remove duplicados
        except Exception as e:
            logger.error(f"Erro ao extrair imports: {str(e)}")
            return []
    
    def extract_functions(self, code: str, language: str = None) -> List[str]:
        """
        Extrai nomes de funções de código
        
        Args:
            code: Código fonte
            language: Linguagem de programação
            
        Returns:
            Lista de nomes de funções
        """
        if language is None:
            language = self.detect_language(code)
        
        if language not in self.language_patterns:
            return []
        
        pattern = self.language_patterns[language].get('functions', '')
        if not pattern:
            return []
        
        try:
            import re
            matches = re.findall(pattern, code, re.MULTILINE)
            # Trata diferentes formatos de captura
            function_names = []
            for match in matches:
                if isinstance(match, tuple):
                    # Pega primeiro grupo não vazio
                    name = next((m for m in match if m), None)
                else:
                    name = match
                if name:
                    function_names.append(name)
            return list(set(function_names))
        except Exception as e:
            logger.error(f"Erro ao extrair funções: {str(e)}")
            return []
    
    def check_code_quality(self, code: str, language: str = None) -> Dict[str, Any]:
        """
        Verifica qualidade básica do código
        
        Args:
            code: Código fonte
            language: Linguagem de programação
            
        Returns:
            Dicionário com métricas de qualidade
        """
        if language is None:
            language = self.detect_language(code)
        
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        total_lines = len(lines)
        non_empty_count = len(non_empty_lines)
        
        # Conta comentários
        comment_count = 0
        if language in self.language_patterns:
            comment_pattern = self.language_patterns[language].get('comments', '')
            if comment_pattern:
                import re
                comment_count = len(re.findall(comment_pattern, code, re.MULTILINE))
        
        # Conta strings
        string_count = 0
        if language in self.language_patterns:
            string_pattern = self.language_patterns[language].get('strings', '')
            if string_pattern:
                import re
                string_count = len(re.findall(string_pattern, code, re.MULTILINE))
        
        # Calcula métricas
        comment_ratio = comment_count / non_empty_count if non_empty_count > 0 else 0
        string_ratio = string_count / non_empty_count if non_empty_count > 0 else 0
        
        # Verifica complexidade simples (linhas por função)
        functions = self.extract_functions(code, language)
        avg_lines_per_function = non_empty_count / len(functions) if functions else non_empty_count
        
        return {
            'language': language,
            'total_lines': total_lines,
            'non_empty_lines': non_empty_count,
            'comment_lines': comment_count,
            'string_literals': string_count,
            'comment_ratio': comment_ratio,
            'string_ratio': string_ratio,
            'functions_count': len(functions),
            'avg_lines_per_function': avg_lines_per_function,
            'quality_score': self._calculate_quality_score(comment_ratio, avg_lines_per_function)
        }
    
    def _calculate_quality_score(self, comment_ratio: float, avg_lines_per_function: float) -> float:
        """
        Calcula score de qualidade baseado em métricas simples
        """
        # Score baseado em comentários (ideal: 0.1 a 0.3)
        comment_score = max(0, min(1, (comment_ratio - 0.05) / 0.25))
        
        # Score baseado em tamanho de funções (ideal: < 20 linhas)
        function_score = max(0, min(1, (30 - avg_lines_per_function) / 30))
        
        # Combina scores
        return (comment_score * 0.4 + function_score * 0.6)

def safe_file_operation_wrapper(func):
    """
    Decorador para operações seguras de arquivo
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (FileAccessError, FileIntegrityError) as e:
            logger.error(f"Erro de segurança em operação de arquivo: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado em operação de arquivo: {str(e)}")
            raise FileAccessError(f"Erro inesperado: {str(e)}")
    return wrapper

# Funções utilitárias para uso geral
def get_safe_file_operations(base_dir: str = None) -> SafeFileOperations:
    """
    Retorna instância de SafeFileOperations
    
    Args:
        base_dir: Diretório base para operações
        
    Returns:
        Instância de SafeFileOperations
    """
    return SafeFileOperations(base_dir) if base_dir else safe_file_operations

def parse_code(code: str, language: str = None) -> CodeParser:
    """
    Retorna parser de código
    
    Args:
        code: Código fonte
        language: Linguagem de programação
        
    Returns:
        Instância de CodeParser com análise do código
    """
    parser = CodeParser()
    return parser