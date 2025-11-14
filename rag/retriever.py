"""
Recuperador RAG - Recupera contexto relevante para auxiliar na geração de respostas
"""

import json
import logging

import chromadb

logger = logging.getLogger("DEVs_AI")


class RAGRetriever:
    """
    Recuperador de contexto para auxiliar na geração de respostas com conhecimento especializado
    """

    def __init__(self, chroma_client: chromadb.Client, embedders: dict[str, object]):
        self.chroma_client = chroma_client
        self.semantic_embedder = embedders["semantic"]
        self.technical_embedder = embedders["technical"]
        self.context_embedder = embedders["contextual"]

        # Cria ou obtém referências às coleções
        collection_names = {
            "code": "code_documents",
            "architecture": "architecture_documents",
            "requirement": "requirement_documents",
            "commit": "commit_documents",
            "generic": "generic_documents",
        }

        self.collections = {}
        for key, name in collection_names.items():
            try:
                self.collections[key] = self.chroma_client.get_collection(name=name)
            except Exception:
                logger.debug(f"Collection {name} não existe ainda, será criada pelo RAGIndexer quando necessário")
                self.collections[key] = None

        logger.info("✅ RAGRetriever inicializado com sucesso")

    def retrieve(
        self,
        query: str,
        doc_type: str = None,
        n_results: int = 5,
        min_similarity: float = 0.3,
    ) -> list[dict[str, object]]:
        """
        Recupera documentos relevantes para uma consulta

        Args:
            query: Consulta de texto
            doc_type: Tipo de documento específico (code, architecture, requirement, commit, generic)
            n_results: Número máximo de resultados
            min_similarity: Similaridade mínima para considerar um resultado relevante

        Returns:
            Lista de documentos relevantes formatados
        """
        try:
            # Determina coleções a pesquisar
            collections_to_search = []
            if doc_type and doc_type in self.collections and self.collections[doc_type] is not None:
                collections_to_search = [self.collections[doc_type]]
            else:
                collections_to_search = [col for col in self.collections.values() if col is not None]

            # Gera embedding da consulta
            query_embedding = self.semantic_embedder.embed(query)

            # Pesquisa em todas as coleções relevantes
            all_results = []
            for collection in collections_to_search:
                try:
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=n_results,
                        include=["documents", "metadatas", "distances"],
                    )

                    # Converte resultados para formato consistente
                    formatted_results = self._format_collection_results(results, collection.name)
                    all_results.extend(formatted_results)

                except Exception as e:
                    logger.warning(f"Erro ao pesquisar na coleção {collection.name}: {str(e)}")
                    continue

            # Filtra por similaridade mínima e ordena por relevância
            filtered_results = [result for result in all_results if result["similarity_score"] >= min_similarity]

            # Ordena por similaridade (maior para menor)
            filtered_results.sort(key=lambda x: x["similarity_score"], reverse=True)

            # Limita ao número máximo de resultados
            filtered_results = filtered_results[:n_results]

            logger.info(f"Recuperados {len(filtered_results)} documentos relevantes para consulta: {query[:50]}...")
            return filtered_results

        except Exception as e:
            logger.error(f"Erro na recuperação de contexto: {str(e)}")
            return []

    def retrieve_by_semantic_similarity(
        self, query: str, context_type: str, n_results: int = 3
    ) -> list[dict[str, object]]:
        """
        Recupera documentos por similaridade semântica para um tipo específico de contexto

        Args:
            query: Consulta de texto
            context_type: Tipo de contexto (technical, business, code_example, etc.)
            n_results: Número máximo de resultados

        Returns:
            Lista de documentos relevantes
        """
        # Mapeia tipos de contexto para tipos de documentos
        context_to_doc_type = {
            "technical": ["architecture", "code"],
            "business": ["requirement", "generic"],
            "code_example": ["code"],
            "architecture_pattern": ["architecture"],
            "best_practice": ["code", "architecture"],
            "testing": ["code", "generic"],
            "deployment": ["generic"],
        }

        doc_types = context_to_doc_type.get(context_type, ["generic"])
        all_results = []

        for doc_type in doc_types:
            if doc_type in self.collections:
                results = self.retrieve(query, doc_type, n_results)
                all_results.extend(results)

        # Remove duplicados e ordena
        unique_results = self._remove_duplicate_results(all_results)
        unique_results.sort(key=lambda x: x["similarity_score"], reverse=True)

        return unique_results[:n_results]

    def _format_collection_results(self, results: dict[str, object], collection_name: str) -> list[dict[str, object]]:
        """
        Formata resultados de uma coleção para formato consistente
        """
        formatted_results = []

        # Processa cada resultado
        for i in range(len(results["documents"][0])):
            document = results["documents"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]

            # Converte distância para similaridade (quanto menor a distância, maior a similaridade)
            similarity_score = 1.0 / (1.0 + distance)

            # Tenta parsear structured_content se existir
            structured_content = {}
            if "structured_content" in metadata:
                try:
                    structured_content = json.loads(metadata["structured_content"])
                except Exception:
                    pass

            formatted_results.append(
                {
                    "id": results["ids"][0][i],
                    "content": document,
                    "metadata": metadata,
                    "collection": collection_name,
                    "distance": distance,
                    "similarity_score": similarity_score,
                    "structured_content": structured_content,
                }
            )

        return formatted_results

    def _remove_duplicate_results(self, results: list[dict[str, object]]) -> list[dict[str, object]]:
        """
        Remove resultados duplicados mantendo o mais relevante
        """
        seen_content = set()
        unique_results = []

        for result in results:
            # Usa hash do conteúdo para identificar duplicados
            content_hash = hash(result["content"].strip()[:100])

            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)

        return unique_results

    def hybrid_retrieval(
        self,
        semantic_query: str,
        keyword_query: str = None,
        doc_type: str = None,
        n_results: int = 5,
    ) -> list[dict[str, object]]:
        """
        Recupera documentos usando busca híbrida (semântica + keywords)

        Args:
            semantic_query: Consulta para busca semântica
            keyword_query: Consulta para busca por palavras-chave
            doc_type: Tipo de documento específico
            n_results: Número máximo de resultados

        Returns:
            Lista de documentos relevantes
        """
        # Busca semântica
        semantic_results = self.retrieve(semantic_query, doc_type, n_results * 2)

        if not keyword_query or not semantic_results:
            return semantic_results[:n_results]

        # Filtra resultados por palavras-chave
        keyword_results = []
        keyword_lower = keyword_query.lower()

        for result in semantic_results:
            content_lower = result["content"].lower()
            if keyword_lower in content_lower:
                keyword_results.append(result)

        # Se não encontrar resultados por keyword, retorna os semânticos
        if not keyword_results:
            return semantic_results[:n_results]

        # Ordena resultados por keyword por similaridade
        keyword_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return keyword_results[:n_results]

    def get_context_summary(self, query: str, context_type: str = "technical", max_tokens: int = 500) -> str:
        """
        Gera um resumo do contexto recuperado para uso em prompts

        Args:
            query: Consulta de texto
            context_type: Tipo de contexto
            max_tokens: Limite máximo de tokens para o resumo

        Returns:
            String com resumo do contexto
        """
        results = self.retrieve_by_semantic_similarity(query, context_type, 3)

        if not results:
            return ""

        # Constrói resumo formatado
        summary_parts = []
        for _i, result in enumerate(results, 1):
            content = result["content"]
            metadata = result["metadata"]
            doc_type = metadata.get("type", "unknown")
            similarity = result["similarity_score"]

            # Formata conteúdo baseado no tipo
            if doc_type == "code":
                summary_parts.append(f"EXEMPLO DE CÓDIGO (relevância: {similarity:.2f}):\n{content.strip()[:200]}...")
            elif doc_type == "architecture":
                summary_parts.append(f"PADRÃO ARQUITETURAL (relevância: {similarity:.2f}):\n{content.strip()[:200]}...")
            elif doc_type == "requirement":
                summary_parts.append(
                    f"REQUISITO RELACIONADO (relevância: {similarity:.2f}):\n{content.strip()[:200]}..."
                )
            else:
                summary_parts.append(f"CONTEXTO RELEVANTE (relevância: {similarity:.2f}):\n{content.strip()[:200]}...")

        # Junta partes e limita por tokens (aproximadamente 4 caracteres por token)
        summary = "\n\n".join(summary_parts)
        max_chars = max_tokens * 4
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."

        return summary

    def get_code_examples(self, functionality: str, language: str = None, n_examples: int = 2) -> list[dict[str, any]]:
        """
        Recupera exemplos de código para uma funcionalidade específica

        Args:
            functionality: Funcionalidade desejada
            language: Linguagem de programação específica
            n_examples: Número de exemplos

        Returns:
            Lista de exemplos de código
        """
        # Modifica a query para focar em exemplos de código
        query = f"Exemplo de código para {functionality}"
        if language:
            query += f" em {language}"

        results = self.retrieve(query, "code", n_examples * 2)

        # Filtra por linguagem se especificado
        if language:
            filtered_results = []
            language_lower = language.lower()

            for result in results:
                structured = result.get("structured_content", {})
                if structured.get("language", "").lower() == language_lower:
                    filtered_results.append(result)

            results = filtered_results[:n_examples]

        return results[:n_examples]

    def get_architecture_patterns(self, system_type: str, n_patterns: int = 2) -> list[dict[str, any]]:
        """
        Recupera padrões arquiteturais para um tipo de sistema

        Args:
            system_type: Tipo de sistema (web, mobile, distributed, etc.)
            n_patterns: Número de padrões

        Returns:
            Lista de padrões arquiteturais
        """
        query = f"Padrões arquiteturais para sistema {system_type}"
        results = self.retrieve(query, "architecture", n_patterns * 2)

        # Filtra por padrões relevantes
        relevant_results = []
        for result in results:
            structured = result.get("structured_content", {})
            patterns = structured.get("architecture_patterns", [])
            if any(system_type.lower() in pattern.lower() for pattern in patterns):
                relevant_results.append(result)

        return relevant_results[:n_patterns]
