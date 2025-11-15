"""
Módulo Utils - Utilitários e funções auxiliares para o sistema DEVs AI
"""

from . import security_utils
from .embedders import HybridEmbedder, SentenceTransformerEmbedder, SimpleEmbedder
from .file_operations import (
    CodeParser,
    SafeFileOperations,
    get_safe_file_operations,
    parse_code,
    safe_file_operation_wrapper,
    safe_file_operations,
)
from .hardware_detection import (
    HardwareProfile,
    HardwareTier,
    SystemMetrics,
    detect_hardware_profile,
    detect_system_metrics,
)
from .llm_abstraction import (
    LLMAbstractLayer,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
)

__all__ = [
    "SimpleEmbedder",
    "SentenceTransformerEmbedder",
    "HybridEmbedder",
    "detect_hardware_profile",
    "detect_system_metrics",
    "HardwareProfile",
    "SystemMetrics",
    "HardwareTier",
    "SafeFileOperations",
    "CodeParser",
    "safe_file_operations",
    "safe_file_operation_wrapper",
    "get_safe_file_operations",
    "parse_code",
    "LLMProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "LLMAbstractLayer",
    "security_utils",
]
