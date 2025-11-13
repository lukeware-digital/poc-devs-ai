"""
Detecção de Hardware - Identifica perfil de hardware e configurações otimizadas
"""

import os
import platform
import logging
import subprocess
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("DEVs_AI")

class HardwareTier(Enum):
    """Níveis de capacidade de hardware"""
    ULTRA = "ultra"           # High-end GPUs com 24GB+ VRAM, 64GB+ RAM
    HIGH = "high"             # Mid-high GPUs com 16GB+ VRAM, 32GB+ RAM  
    MEDIUM = "medium"         # Mid-range GPUs com 8GB+ VRAM, 16GB+ RAM
    LOW = "low"               # Entry-level GPUs com 4GB+ VRAM, 8GB+ RAM
    MINIMAL = "minimal"       # CPU-only ou GPUs muito limitadas

class HardwareProfile:
    """
    Perfil de hardware detectado com configurações recomendadas
    """
    
    def __init__(self, system_info: Dict[str, Any]):
        self.system_info = system_info
        self.profile_name = self._determine_profile_name()
        self.hardware_tier = self._determine_hardware_tier()
        self.recommended_config = self._generate_recommended_config()
        
    def _determine_profile_name(self) -> str:
        """Determina nome do perfil baseado em hardware comum"""
        cpu_model = self.system_info.get('cpu_model', '').lower()
        gpu_model = self.system_info.get('gpu_model', '').lower()
        ram_gb = self.system_info.get('ram_gb', 0)
        vram_gb = self.system_info.get('vram_gb', 0)
        
        # Perfil do usuário atual (Ryzen 5800X + RTX 3060 Ti)
        if '5800x' in cpu_model and 'rtx 3060 ti' in gpu_model and ram_gb >= 32:
            return 'ryzen5800x_rtx3060ti'
        
        # Outros perfis comuns
        profiles = [
            ('i9_13900k_rtx4090', lambda: '13900k' in cpu_model and 'rtx 4090' in gpu_model and ram_gb >= 64),
            ('ryzen9_7950x_rtx4080', lambda: '7950x' in cpu_model and 'rtx 4080' in gpu_model and ram_gb >= 64),
            ('m1_max', lambda: 'm1 max' in cpu_model and ram_gb >= 64),
            ('i7_12700k_rtx3080', lambda: '12700k' in cpu_model and 'rtx 3080' in gpu_model and ram_gb >= 32),
            ('ryzen7_5800x_rtx3070', lambda: '5800x' in cpu_model and 'rtx 3070' in gpu_model and ram_gb >= 32),
            ('i5_12600k_rtx3060', lambda: '12600k' in cpu_model and 'rtx 3060' in gpu_model and ram_gb >= 16),
            ('ryzen5_5600x_rtx3060', lambda: '5600x' in cpu_model and 'rtx 3060' in gpu_model and ram_gb >= 16),
            ('mac_m1_pro', lambda: 'm1 pro' in cpu_model and ram_gb >= 16),
            ('mac_m2_air', lambda: 'm2' in cpu_model and 'air' in cpu_model and ram_gb >= 8),
            ('cpu_only_high', lambda: vram_gb == 0 and ram_gb >= 32),
            ('cpu_only_medium', lambda: vram_gb == 0 and ram_gb >= 16),
            ('cpu_only_low', lambda: vram_gb == 0 and ram_gb >= 8),
        ]
        
        for profile_name, condition in profiles:
            if condition():
                return profile_name
        
        return 'custom_profile'
    
    def _determine_hardware_tier(self) -> HardwareTier:
        """Determina nível de hardware baseado em capacidades"""
        vram_gb = self.system_info.get('vram_gb', 0)
        ram_gb = self.system_info.get('ram_gb', 0)
        cpu_cores = self.system_info.get('cpu_cores', 0)
        
        if vram_gb >= 24 and ram_gb >= 64 and cpu_cores >= 16:
            return HardwareTier.ULTRA
        elif vram_gb >= 16 and ram_gb >= 32 and cpu_cores >= 12:
            return HardwareTier.HIGH
        elif vram_gb >= 8 and ram_gb >= 16 and cpu_cores >= 8:
            return HardwareTier.MEDIUM
        elif vram_gb >= 4 and ram_gb >= 8 and cpu_cores >= 4:
            return HardwareTier.LOW
        else:
            return HardwareTier.MINIMAL
    
    def _generate_recommended_config(self) -> Dict[str, Any]:
        """Gera configuração recomendada baseada no perfil"""
        tier = self.hardware_tier
        vram_gb = self.system_info.get('vram_gb', 0)
        ram_gb = self.system_info.get('ram_gb', 0)
        
        # Configurações baseadas no nível de hardware
        configs = {
            HardwareTier.ULTRA: {
                'primary_model': 'llama3:70b-instruct-q2_K',
                'fallback_models': [
                    'mixtral:8x22b-instruct-v0.1-q3_K_M',
                    'codellama:34b-instruct-q3_K_M',
                    'phi3:medium-128k-instruct-q4_K_M'
                ],
                'orchestrator': {
                    'concurrent_agents': 8,
                    'max_auto_retries': 3,
                    'batch_size': 32
                },
                'llm_params': {
                    'max_tokens': 8192,
                    'temperature_range': [0.1, 0.9]
                },
                'performance': {
                    'gpu_offloading': True,
                    'vram_optimization': 'aggressive',
                    'model_parallelism': 4
                }
            },
            HardwareTier.HIGH: {
                'primary_model': 'llama3:70b-instruct-q3_K_M',
                'fallback_models': [
                    'mixtral:8x7b-instruct-v0.1-q4_K_M',
                    'codellama:13b-instruct-q4_K_M',
                    'phi3:medium-4k-instruct-q5_K_M'
                ],
                'orchestrator': {
                    'concurrent_agents': 6,
                    'max_auto_retries': 3,
                    'batch_size': 24
                },
                'llm_params': {
                    'max_tokens': 4096,
                    'temperature_range': [0.1, 0.8]
                },
                'performance': {
                    'gpu_offloading': True,
                    'vram_optimization': 'balanced',
                    'model_parallelism': 2
                }
            },
            HardwareTier.MEDIUM: {
                'primary_model': 'llama3:8b-instruct-q5_K_M',
                'fallback_models': [
                    'mistral:7b-instruct-v0.2-q5_K_M',
                    'phi3:medium-4k-instruct-q5_K_M',
                    'codegemma:7b-instruct-q5_K_M'
                ],
                'orchestrator': {
                    'concurrent_agents': 4,
                    'max_auto_retries': 2,
                    'batch_size': 16
                },
                'llm_params': {
                    'max_tokens': 2048,
                    'temperature_range': [0.2, 0.7]
                },
                'performance': {
                    'gpu_offloading': True,
                    'vram_optimization': 'conservative',
                    'model_parallelism': 1
                }
            },
            HardwareTier.LOW: {
                'primary_model': 'llama3:8b-instruct-q4_0',
                'fallback_models': [
                    'mistral:7b-instruct-v0.2-q4_0',
                    'phi3:medium-4k-instruct-q4_0',
                    'codegemma:7b-instruct-q4_0'
                ],
                'orchestrator': {
                    'concurrent_agents': 3,
                    'max_auto_retries': 2,
                    'batch_size': 8
                },
                'llm_params': {
                    'max_tokens': 1024,
                    'temperature_range': [0.3, 0.6]
                },
                'performance': {
                    'gpu_offloading': True,
                    'vram_optimization': 'aggressive',
                    'model_parallelism': 1
                }
            },
            HardwareTier.MINIMAL: {
                'primary_model': 'phi3:3.8b-medium-4k-instruct-q4_0',
                'fallback_models': [
                    'stablelm2:1.6b-chat-q4_0',
                    'tinyllama:1.1b-chat-v1.0-q4_0'
                ],
                'orchestrator': {
                    'concurrent_agents': 2,
                    'max_auto_retries': 1,
                    'batch_size': 4
                },
                'llm_params': {
                    'max_tokens': 512,
                    'temperature_range': [0.4, 0.5]
                },
                'performance': {
                    'gpu_offloading': False,
                    'vram_optimization': 'extreme',
                    'model_parallelism': 1
                }
            }
        }
        
        base_config = configs[tier]
        
        # Ajustes finos baseados em VRAM específica
        if 8 <= vram_gb < 16:
            base_config['primary_model'] = 'llama3:8b-instruct-q5_K_M'
        elif 4 <= vram_gb < 8:
            base_config['primary_model'] = 'llama3:8b-instruct-q4_0'
        elif vram_gb < 4:
            base_config['primary_model'] = 'phi3:3.8b-medium-4k-instruct-q4_0'
        
        # Ajustes baseados em RAM
        if ram_gb < 16:
            base_config['orchestrator']['concurrent_agents'] = max(1, base_config['orchestrator']['concurrent_agents'] // 2)
            base_config['llm_params']['max_tokens'] = max(256, base_config['llm_params']['max_tokens'] // 2)
        
        return base_config
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte perfil para dicionário"""
        return {
            'profile_name': self.profile_name,
            'hardware_tier': self.hardware_tier.value,
            'system_info': self.system_info,
            'recommended_config': self.recommended_config
        }
    
    def get_agent_temperatures(self) -> Dict[str, float]:
        """
        Retorna temperaturas recomendadas para cada agente
        """
        base_config = self.recommended_config
        base_temp_range = base_config['llm_params']['temperature_range']
        
        # Temperaturas específicas por agente baseadas no perfil
        agent_temps = {
            'agent1': base_temp_range[0] + 0.1,  # Clarificador - mais conservador
            'agent2': base_temp_range[1],       # Product Manager - mais criativo
            'agent3': base_temp_range[0],       # Arquiteto - mais conservador
            'agent4': base_temp_range[0] + 0.1, # Tech Lead - equilibrado
            'agent5': base_temp_range[0],       # Scaffolder - mais conservador
            'agent6': base_temp_range[0] + 0.2, # Desenvolvedor - mais flexível
            'agent7': base_temp_range[0],       # Code Reviewer - mais conservador
            'agent8': base_temp_range[0] + 0.3  # Finalizador - mais flexível
        }
        
        return agent_temps
    
    def get_performance_settings(self) -> Dict[str, Any]:
        """
        Retorna configurações de performance otimizadas
        """
        perf_config = self.recommended_config['performance']
        orch_config = self.recommended_config['orchestrator']
        
        return {
            'max_concurrent_agents': orch_config['concurrent_agents'],
            'batch_size': orch_config['batch_size'],
            'gpu_offloading': perf_config['gpu_offloading'],
            'vram_optimization': perf_config['vram_optimization'],
            'model_parallelism': perf_config['model_parallelism'],
            'memory_swap_limit': max(0.3, min(0.7, 1.0 - (self.system_info.get('ram_gb', 8) / 32)))
        }

@dataclass
class SystemMetrics:
    """
    Métricas do sistema em tempo real
    """
    cpu_percent: float
    memory_percent: float
    vram_percent: float
    disk_io: float
    network_io: float
    temperature: float
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte métricas para dicionário"""
        return {
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'vram_percent': self.vram_percent,
            'disk_io': self.disk_io,
            'network_io': self.network_io,
            'temperature': self.temperature,
            'timestamp': self.timestamp
        }

def detect_hardware_profile() -> str:
    """
    Detecta perfil de hardware e retorna nome do arquivo de configuração
    """
    try:
        system_info = _gather_system_info()
        profile = HardwareProfile(system_info)
        logger.info(f"Perfil de hardware detectado: {profile.profile_name} ({profile.hardware_tier.value})")
        return profile.profile_name
    except Exception as e:
        logger.error(f"Erro ao detectar perfil de hardware: {str(e)}")
        return "default"  # Perfil padrão como fallback

def detect_system_metrics() -> SystemMetrics:
    """
    Detecta métricas do sistema em tempo real
    """
    try:
        import psutil
        import time
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        
        # Memória
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # VRAM (tentativa com nvidia-smi)
        vram_percent = 0.0
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.memory', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                vram_percent = float(result.stdout.strip())
        except (subprocess.SubprocessError, ValueError, FileNotFoundError):
            vram_percent = 0.0
        
        # Disco
        disk_io = psutil.disk_io_counters()
        disk_io_rate = (disk_io.read_bytes + disk_io.write_bytes) / (1024 * 1024)  # MB
        
        # Rede
        net_io = psutil.net_io_counters()
        net_io_rate = (net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024)  # MB
        
        # Temperatura (tentativa)
        temperature = 0.0
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Pega temperatura da CPU
                cpu_temps = temps.get('coretemp', temps.get('k10temp', []))
                if cpu_temps:
                    temperature = max(temp.current for temp in cpu_temps)
        except:
            temperature = 0.0
        
        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            vram_percent=vram_percent,
            disk_io=disk_io_rate,
            network_io=net_io_rate,
            temperature=temperature,
            timestamp=time.time()
        )
        
    except Exception as e:
        logger.error(f"Erro ao detectar métricas do sistema: {str(e)}")
        return SystemMetrics(
            cpu_percent=0.0,
            memory_percent=0.0,
            vram_percent=0.0,
            disk_io=0.0,
            network_io=0.0,
            temperature=0.0,
            timestamp=time.time()
        )

def _gather_system_info() -> Dict[str, Any]:
    """
    Coleta informações detalhadas do sistema
    """
    info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'cpu_cores': os.cpu_count() or 4,
        'cpu_model': _get_cpu_model(),
        'ram_gb': _get_ram_size(),
        'gpu_model': _get_gpu_model(),
        'vram_gb': _get_vram_size(),
        'gpu_available': _check_gpu_available(),
        'cuda_available': _check_cuda_available(),
        'disk_space': _get_disk_space(),
        'python_version': platform.python_version()
    }
    
    return info

def _get_cpu_model() -> str:
    """Obtém modelo da CPU"""
    try:
        if platform.system() == "Windows":
            import wmi
            w = wmi.WMI()
            processors = w.Win32_Processor()
            return processors[0].Name if processors else "Unknown CPU"
        elif platform.system() == "Linux":
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line:
                        return line.split(':')[1].strip()
        elif platform.system() == "Darwin":  # macOS
            result = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
            return result
    except Exception as e:
        logger.warning(f"Erro ao obter modelo da CPU: {str(e)}")
    
    return platform.processor() or "Unknown CPU"

def _get_ram_size() -> float:
    """Obtém tamanho da RAM em GB"""
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except Exception as e:
        logger.warning(f"Erro ao obter tamanho da RAM: {str(e)}")
        return 8.0  # Valor padrão

def _get_gpu_model() -> str:
    """Obtém modelo da GPU"""
    try:
        # NVIDIA
        result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        
        # AMD (Linux)
        if platform.system() == "Linux":
            result = subprocess.run(['lspci', '-nn', '|', 'grep', '-i', 'vga'], 
                                  shell=True, capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split(':')[-1].strip()
        
        # Intel/Mac
        if platform.system() == "Darwin":
            result = subprocess.check_output(['system_profiler', 'SPDisplaysDataType']).decode()
            for line in result.split('\n'):
                if 'Chipset Model' in line:
                    return line.split(':')[-1].strip()
    
    except (subprocess.SubprocessError, FileNotFoundError, OSError, Exception) as e:
        logger.warning(f"Erro ao obter modelo da GPU: {str(e)}")
    
    return "Unknown GPU"

def _get_vram_size() -> float:
    """Obtém tamanho da VRAM em GB"""
    try:
        # NVIDIA
        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip()) / 1024  # Convert MB to GB
        
        # AMD (Linux)
        if platform.system() == "Linux":
            # Tenta várias abordagens para AMD
            try:
                result = subprocess.run(['rocm-smi', '--showmeminfo', 'vram', '--csv'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    # Processa saída CSV
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        vram_str = lines[1].split(',')[1]  # Assume formato CSV
                        return float(vram_str) / 1024
            except:
                pass
        
        # Mac com M1/M2
        if platform.system() == "Darwin":
            result = subprocess.check_output(['system_profiler', 'SPDisplaysDataType']).decode()
            for line in result.split('\n'):
                if 'VRAM' in line or 'Memory' in line:
                    # Extrai valor numérico
                    import re
                    match = re.search(r'(\d+\.?\d*)\s*(GB|MB)', line)
                    if match:
                        value = float(match.group(1))
                        unit = match.group(2)
                        return value if unit == 'GB' else value / 1024
    
    except (subprocess.SubprocessError, ValueError, FileNotFoundError, Exception) as e:
        logger.warning(f"Erro ao obter tamanho da VRAM: {str(e)}")
    
    return 0.0  # 0 indica CPU-only ou falha na detecção

def _check_gpu_available() -> bool:
    """Verifica se GPU está disponível"""
    try:
        # Verifica NVIDIA
        try:
            subprocess.run(['nvidia-smi'], capture_output=True, timeout=2)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Verifica AMD ROCm
        try:
            subprocess.run(['rocm-smi'], capture_output=True, timeout=2)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Verifica Intel oneAPI
        try:
            import intel_extension_for_pytorch
            return True
        except ImportError:
            pass
        
        # Verifica Apple MPS
        if platform.system() == "Darwin":
            import torch
            return hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
        
        return False
        
    except Exception as e:
        logger.warning(f"Erro ao verificar GPU disponível: {str(e)}")
        return False

def _check_cuda_available() -> bool:
    """Verifica se CUDA está disponível"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        logger.warning("PyTorch não instalado, não é possível verificar CUDA")
        return False

def _get_disk_space() -> float:
    """Obtém espaço em disco disponível em GB"""
    try:
        import psutil
        disk = psutil.disk_usage('/')
        return disk.free / (1024 ** 3)
    except Exception as e:
        logger.warning(f"Erro ao obter espaço em disco: {str(e)}")
        return 100.0  # Valor padrão

def get_optimal_batch_size(hardware_profile: HardwareProfile) -> int:
    """
    Determina tamanho de batch ideal baseado no perfil de hardware
    """
    tier = hardware_profile.hardware_tier
    vram_gb = hardware_profile.system_info.get('vram_gb', 0)
    ram_gb = hardware_profile.system_info.get('ram_gb', 0)
    
    if tier == HardwareTier.ULTRA:
        return 64
    elif tier == HardwareTier.HIGH:
        return 32
    elif tier == HardwareTier.MEDIUM:
        return 16
    elif tier == HardwareTier.LOW:
        return 8
    else:  # MINIMAL
        return 4

def get_model_sharding_strategy(hardware_profile: HardwareProfile) -> Dict[str, Any]:
    """
    Determina estratégia de sharding de modelo baseado no hardware
    """
    vram_gb = hardware_profile.system_info.get('vram_gb', 0)
    has_gpu = hardware_profile.system_info.get('gpu_available', False)
    
    if has_gpu and vram_gb >= 24:
        return {
            'strategy': 'tensor_parallel',
            'num_shards': 4,
            'pipeline_parallel': True
        }
    elif has_gpu and vram_gb >= 16:
        return {
            'strategy': 'pipeline_parallel',
            'num_shards': 2,
            'pipeline_parallel': True
        }
    elif has_gpu and vram_gb >= 8:
        return {
            'strategy': 'layer_sharding',
            'num_shards': 2,
            'pipeline_parallel': False
        }
    else:
        return {
            'strategy': 'cpu_offload',
            'num_shards': 1,
            'pipeline_parallel': False
        }