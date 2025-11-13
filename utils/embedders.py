"""
Embedders - Geradores de embeddings para diferentes tipos de conteúdo
"""

import logging
from abc import ABC, abstractmethod

import numpy as np

logger = logging.getLogger("DEVs_AI")


class BaseEmbedder(ABC):
    """
    Classe base abstrata para embedders
    """

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """
        Gera embedding para o texto fornecido

        Args:
            text: Texto para gerar embedding

        Returns:
            Lista de floats representando o embedding
        """
        pass

    @abstractmethod
    def batch_embed(self, texts: list[str]) -> list[list[float]]:
        """
        Gera embeddings para múltiplos textos

        Args:
            texts: Lista de textos

        Returns:
            Lista de embeddings
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """
        Retorna a dimensão do embedding

        Returns:
            Dimensão do embedding
        """
        pass


class SimpleEmbedder(BaseEmbedder):
    """
    Embedder simples baseado em hashing para ambientes sem GPU
    Útil para desenvolvimento e sistemas com recursos limitados
    """

    def __init__(self, dimensions: int = 384):
        """
        Inicializa o embedder simples

        Args:
            dimensions: Dimensão do embedding (padrão 384 para compatibilidade)
        """
        self.dimensions = dimensions
        self.cache = {}
        logger.info(f"SimpleEmbedder inicializado com dimensão {dimensions}")

    def embed(self, text: str) -> list[float]:
        """
        Gera embedding determinístico baseado em hashing MD5
        """
        if not text or not isinstance(text, str):
            text = ""

        # Usa cache para textos já processados
        if text in self.cache:
            return self.cache[text]

        try:
            import hashlib
            import struct

            # Gera hash MD5 do texto
            hash_obj = hashlib.md5(text.encode("utf-8", errors="ignore"))
            hash_bytes = hash_obj.digest()

            # Converte bytes para floats determinísticos
            embedding = []
            for i in range(0, len(hash_bytes), 4):
                if len(embedding) >= self.dimensions:
                    break

                # Pega 4 bytes e converte para float
                chunk = hash_bytes[i : i + 4] + b"\x00" * (4 - len(hash_bytes[i : i + 4]))
                value = struct.unpack("f", chunk)[0]

                # Normaliza para faixa 0-1 e aplica transformação não-linear
                normalized = (value % 1.0 + 1.0) % 1.0
                transformed = np.sin(normalized * np.pi)  # Transformação não-linear

                embedding.append(transformed)

            # Preenche com valores determinísticos se necessário
            while len(embedding) < self.dimensions:
                next_value = np.sin(len(embedding) * 0.1) * 0.5 + 0.5
                embedding.append(next_value)

            # Normaliza o vetor completo
            embedding = np.array(embedding)
            if np.linalg.norm(embedding) > 0:
                embedding = embedding / np.linalg.norm(embedding)

            embedding = embedding.tolist()
            self.cache[text] = embedding
            return embedding

        except Exception as e:
            logger.error(f"Erro ao gerar embedding para '{text[:50]}...': {str(e)}")
            # Retorna embedding de fallback
            return [0.0] * self.dimensions

    def batch_embed(self, texts: list[str]) -> list[list[float]]:
        """
        Gera embeddings para múltiplos textos
        """
        return [self.embed(text) for text in texts]

    def get_dimension(self) -> int:
        """
        Retorna a dimensão do embedding
        """
        return self.dimensions


class SentenceTransformerEmbedder(BaseEmbedder):
    """
    Embedder avançado usando Sentence Transformers
    Requer biblioteca sentence-transformers e torch
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        device: str = "cpu",
        batch_size: int = 32,
    ):
        """
        Inicializa o embedder com Sentence Transformers

        Args:
            model_name: Nome do modelo do Hugging Face
            device: Dispositivo para inferência ('cpu' ou 'cuda')
            batch_size: Tamanho do batch para processamento
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.model = None
        self.tokenizer = None
        self._initialize_model()
        logger.info(f"SentenceTransformerEmbedder inicializado com modelo {model_name} no dispositivo {device}")

    def _initialize_model(self):
        """Inicializa o modelo e tokenizer"""
        try:
            import torch
            from sentence_transformers import SentenceTransformer

            # Força o uso de CPU se não houver GPU disponível
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("GPU não disponível, usando CPU")
                self.device = "cpu"

            # Carrega o modelo
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"Modelo {self.model_name} carregado com sucesso")

        except ImportError:
            logger.warning(
                "Bibliotecas sentence-transformers ou torch não encontradas. Usando SimpleEmbedder como fallback."
            )
            self.model = None
            self.fallback_embedder = SimpleEmbedder(dimensions=384)
        except Exception as e:
            logger.error(f"Erro ao inicializar SentenceTransformerEmbedder: {str(e)}")
            self.model = None
            self.fallback_embedder = SimpleEmbedder(dimensions=384)

    def embed(self, text: str) -> list[float]:
        """
        Gera embedding usando Sentence Transformers
        """
        if self.model is None:
            return self.fallback_embedder.embed(text)

        try:
            # Processa o texto
            embedding = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Erro ao gerar embedding com SentenceTransformer: {str(e)}")
            return [0.0] * self.get_dimension()

    def batch_embed(self, texts: list[str]) -> list[list[float]]:
        """
        Gera embeddings para múltiplos textos usando batching
        """
        if self.model is None:
            return self.fallback_embedder.batch_embed(texts)

        try:
            # Processa em batches
            all_embeddings = []
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i : i + self.batch_size]
                embeddings = self.model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
                all_embeddings.extend(embeddings.tolist())
            return all_embeddings
        except Exception as e:
            logger.error(f"Erro ao gerar embeddings em batch: {str(e)}")
            return [[0.0] * self.get_dimension() for _ in texts]

    def get_dimension(self) -> int:
        """
        Retorna a dimensão do embedding
        """
        if self.model is None:
            return self.fallback_embedder.get_dimension()

        try:
            return self.model.get_sentence_embedding_dimension()
        except Exception:
            # Dimensão padrão para modelos comuns
            return 384


class HybridEmbedder(BaseEmbedder):
    """
    Embedder híbrido que combina diferentes tipos de embeddings
    para diferentes aspectos do conteúdo
    """

    def __init__(
        self,
        semantic_embedder: BaseEmbedder | None = None,
        technical_embedder: BaseEmbedder | None = None,
        contextual_embedder: BaseEmbedder | None = None,
    ):
        """
        Inicializa o embedder híbrido

        Args:
            semantic_embedder: Embedder para significado semântico
            technical_embedder: Embedder para conteúdo técnico
            contextual_embedder: Embedder para contexto
        """
        self.semantic_embedder = semantic_embedder or SimpleEmbedder(dimensions=256)
        self.technical_embedder = technical_embedder or SimpleEmbedder(dimensions=256)
        self.contextual_embedder = contextual_embedder or SimpleEmbedder(dimensions=256)

        # Dimensões totais
        self.total_dimensions = (
            self.semantic_embedder.get_dimension()
            + self.technical_embedder.get_dimension()
            + self.contextual_embedder.get_dimension()
        )

        logger.info(f"HybridEmbedder inicializado com dimensão total {self.total_dimensions}")

    def embed(self, text: str, content_type: str = "generic") -> list[float]:
        """
        Gera embedding híbrido baseado no tipo de conteúdo

        Args:
            text: Texto para gerar embedding
            content_type: Tipo de conteúdo ('code', 'architecture', 'requirement', 'commit', 'generic')

        Returns:
            Embedding combinado
        """
        # Determina pesos baseados no tipo de conteúdo
        weights = self._get_content_weights(content_type)

        # Gera embeddings individuais
        semantic_emb = self.semantic_embedder.embed(text)
        technical_emb = self.technical_embedder.embed(text)
        contextual_emb = self.contextual_embedder.embed(text)

        # Combina embeddings com pesos
        combined_embedding = []

        # Adiciona parte semântica
        for val in semantic_emb:
            combined_embedding.append(val * weights["semantic"])

        # Adiciona parte técnica
        for val in technical_emb:
            combined_embedding.append(val * weights["technical"])

        # Adiciona parte contextual
        for val in contextual_emb:
            combined_embedding.append(val * weights["contextual"])

        # Normaliza o vetor resultante
        if any(combined_embedding):
            norm = np.linalg.norm(combined_embedding)
            if norm > 0:
                combined_embedding = [x / norm for x in combined_embedding]

        return combined_embedding

    def batch_embed(self, texts: list[str], content_types: list[str | None] = None) -> list[list[float]]:
        """
        Gera embeddings híbridos para múltiplos textos

        Args:
            texts: Lista de textos
            content_types: Lista de tipos de conteúdo (opcional)

        Returns:
            Lista de embeddings combinados
        """
        if content_types is None:
            content_types = ["generic"] * len(texts)

        return [self.embed(text, content_type) for text, content_type in zip(texts, content_types, strict=False)]

    def get_dimension(self) -> int:
        """
        Retorna a dimensão total do embedding
        """
        return self.total_dimensions

    def _get_content_weights(self, content_type: str) -> dict[str, float]:
        """
        Retorna pesos para diferentes tipos de conteúdo
        """
        weight_profiles = {
            "code": {"semantic": 0.3, "technical": 0.6, "contextual": 0.1},
            "architecture": {"semantic": 0.4, "technical": 0.4, "contextual": 0.2},
            "requirement": {"semantic": 0.7, "technical": 0.2, "contextual": 0.1},
            "commit": {"semantic": 0.5, "technical": 0.3, "contextual": 0.2},
            "generic": {"semantic": 0.5, "technical": 0.3, "contextual": 0.2},
        }

        return weight_profiles.get(content_type.lower(), weight_profiles["generic"])


class CodeSpecificEmbedder(BaseEmbedder):
    """
    Embedder especializado para código fonte
    Combina análise sintática com embeddings semânticos
    """

    def __init__(self, base_embedder: BaseEmbedder | None = None, parser_enabled: bool = True):
        """
        Inicializa o embedder especializado para código

        Args:
            base_embedder: Embedder base para texto
            parser_enabled: Habilita análise sintática
        """
        self.base_embedder = base_embedder or SimpleEmbedder(dimensions=256)
        self.parser_enabled = parser_enabled
        self.code_patterns = {
            "function_def": r"\bdef\s+\w+\s*\(|\bfunction\s+\w+\s*\(|\bvoid\s+\w+\s*\(",
            "class_def": r"\bclass\s+\w+\s*[:{]|\binterface\s+\w+\s*[:{]",
            "import": r"\bimport\s+|\bfrom\s+.*\bimport\s+|\brequire\s*\(|\binclude\s*",
            "comment": r"//.*|/\*.*?\*/|#.*",
            "string": r'".*?"|\'.*?\'',
            "control_flow": r"\bif\b|\belse\b|\bfor\b|\bwhile\b|\bswitch\b|\bcase\b",
            "data_structures": r"\blist\b|\bdict\b|\bset\b|\barray\b|\bmap\b|\bvector\b",
            "error_handling": r"\btry\b|\bcatch\b|\bexcept\b|\bfinally\b|\bthrow\b",
        }

        # Dimensão expandida para características de código
        self.dimensions = self.base_embedder.get_dimension() + 16  # 16 dimensões extras para características

        logger.info(f"CodeSpecificEmbedder inicializado com dimensão {self.dimensions}")

    def embed(self, code: str, language: str = "python") -> list[float]:
        """
        Gera embedding especializado para código

        Args:
            code: Código fonte
            language: Linguagem de programação

        Returns:
            Embedding especializado para código
        """
        if not code:
            return [0.0] * self.dimensions

        try:
            # Gera embedding base do texto completo
            base_embedding = self.base_embedder.embed(code)

            # Extrai características específicas de código
            code_features = self._extract_code_features(code, language)

            # Combina embeddings
            combined_embedding = base_embedding + code_features

            # Normaliza o vetor resultante
            if any(combined_embedding):
                norm = np.linalg.norm(combined_embedding)
                if norm > 0:
                    combined_embedding = [x / norm for x in combined_embedding]

            return combined_embedding

        except Exception as e:
            logger.error(f"Erro ao gerar embedding para código: {str(e)}")
            return [0.0] * self.dimensions

    def batch_embed(self, codes: list[str], languages: list[str | None] = None) -> list[list[float]]:
        """
        Gera embeddings para múltiplos códigos

        Args:
            codes: Lista de códigos fonte
            languages: Lista de linguagens (opcional)

        Returns:
            Lista de embeddings especializados
        """
        if languages is None:
            languages = ["python"] * len(codes)

        return [self.embed(code, lang) for code, lang in zip(codes, languages, strict=False)]

    def get_dimension(self) -> int:
        """
        Retorna a dimensão do embedding
        """
        return self.dimensions

    def _extract_code_features(self, code: str, language: str) -> list[float]:
        """
        Extrai características específicas de código para o embedding
        """
        features = []

        # Contagem de elementos sintáticos
        for _pattern_name, pattern in self.code_patterns.items():
            try:
                import re

                matches = len(re.findall(pattern, code, re.DOTALL))
                features.append(min(matches / 10.0, 1.0))  # Normaliza para 0-1
            except Exception:
                features.append(0.0)

        # Características adicionais
        lines = code.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        # Proporção de comentários
        comment_lines = len([line for line in non_empty_lines if line.strip().startswith(("#", "//", "/*"))])
        comment_ratio = comment_lines / len(non_empty_lines) if non_empty_lines else 0
        features.append(comment_ratio)

        # Complexidade aproximada (linhas não vazias)
        complexity = min(len(non_empty_lines) / 100.0, 1.0)
        features.append(complexity)

        # Profundidade de indentação média
        indent_depths = []
        for line in non_empty_lines:
            indent = len(line) - len(line.lstrip())
            if indent > 0:
                indent_depths.append(indent)

        avg_indent = sum(indent_depths) / len(indent_depths) if indent_depths else 0
        indent_ratio = min(avg_indent / 8.0, 1.0)  # Normaliza para indentação de 8 espaços
        features.append(indent_ratio)

        # Preenche com zeros se necessário
        while len(features) < 16:
            features.append(0.0)

        return features[:16]  # Garante exatamente 16 características


# Função utilitária para criar embedder apropriado baseado no hardware
def create_optimized_embedder(system_profile: dict[str, any]) -> BaseEmbedder:
    """
    Cria um embedder otimizado baseado no perfil do sistema

    Args:
        system_profile: Perfil do sistema com informações de hardware

    Returns:
        Embedder otimizado para o hardware disponível
    """
    # Verifica se tem GPU e memória suficiente
    has_gpu = system_profile.get("gpu_available", False)
    vram_gb = system_profile.get("vram_gb", 0)
    ram_gb = system_profile.get("ram_gb", 0)

    if has_gpu and vram_gb >= 4 and ram_gb >= 16:
        try:
            # Tenta carregar SentenceTransformer com GPU
            return SentenceTransformerEmbedder(model_name="BAAI/bge-small-en-v1.5", device="cuda", batch_size=64)
        except Exception as e:
            logger.warning(f"Erro ao inicializar SentenceTransformer com GPU: {str(e)}. Usando CPU.")

    if ram_gb >= 8:
        try:
            # Usa SentenceTransformer com CPU
            return SentenceTransformerEmbedder(model_name="BAAI/bge-small-en-v1.5", device="cpu", batch_size=32)
        except Exception as e:
            logger.warning(f"Erro ao inicializar SentenceTransformer com CPU: {str(e)}. Usando SimpleEmbedder.")

    # Fallback para SimpleEmbedder em sistemas com recursos limitados
    return SimpleEmbedder(dimensions=384)
