"""
Módulo RAG (Retrieval-Augmented Generation) - Sistema de recuperação de contexto
para melhorar geração de texto com conhecimento especializado
"""

from .indexer import RAGIndexer
from .retriever import RAGRetriever

__all__ = ['RAGIndexer', 'RAGRetriever']