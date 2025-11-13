"""
Indexador RAG - Indexa documentos técnicos para recuperação de contexto
"""

import hashlib
import json
import logging
import re
from datetime import datetime

import chromadb

logger = logging.getLogger("DEVs_AI")


class RAGIndexer:
    """
    Indexador para documentos técnicos com processamento especializado por tipo
    """

    def __init__(self, chroma_client: chromadb.Client, embedders: dict[str, any]):
        self.chroma_client = chroma_client
        self.semantic_embedder = embedders["semantic"]
        self.technical_embedder = embedders["technical"]
        self.context_embedder = embedders["contextual"]

        # Cria ou obtém coleções para diferentes tipos de documentos
        self.collections = {
            "code": self.chroma_client.get_or_create_collection(
                name="code_documents",
                metadata={"description": "Código fonte e exemplos de implementação"},
            ),
            "architecture": self.chroma_client.get_or_create_collection(
                name="architecture_documents",
                metadata={"description": "Documentos de arquitetura e design"},
            ),
            "requirement": self.chroma_client.get_or_create_collection(
                name="requirement_documents",
                metadata={"description": "Requisitos e especificações"},
            ),
            "commit": self.chroma_client.get_or_create_collection(
                name="commit_documents",
                metadata={"description": "Mensagens de commit e histórico"},
            ),
            "generic": self.chroma_client.get_or_create_collection(
                name="generic_documents",
                metadata={"description": "Documentos genéricos"},
            ),
        }

        logger.info("✅ RAGIndexer inicializado com sucesso")

    def index_technical_document(self, doc_type: str, content: str, metadata: dict[str, any] = None):
        """
        Indexa um documento técnico com processamento especializado

        Args:
            doc_type: Tipo do documento (code, architecture, requirement, commit, generic)
            content: Conteúdo do documento
            metadata: Metadados adicionais
        """
        try:
            # Seleciona processador baseado no tipo do documento
            processors = {
                "code": self._process_code_document,
                "architecture": self._process_arch_document,
                "requirement": self._process_req_document,
                "commit": self._process_commit_document,
            }

            processor = processors.get(doc_type, self._process_generic_document)
            structured_content = processor(content)

            # Gera embeddings para diferentes aspectos
            embeddings = {
                "semantic": self.semantic_embedder.embed(structured_content["main_text"]),
                "technical": self.technical_embedder.embed(" ".join(structured_content["code_blocks"])),
                "contextual": self.context_embedder.embed(structured_content["context"]),
            }

            # Usa embedding semântico como principal
            main_embedding = embeddings["semantic"]

            # Gera ID único baseado no conteúdo
            doc_id = hashlib.md5((content + doc_type).encode()).hexdigest()

            # Prepara metadados
            doc_metadata = {
                "type": doc_type,
                "indexed_at": datetime.utcnow().isoformat(),
                "structured_content": json.dumps(structured_content),
                "content_length": len(content),
                **(metadata or {}),
            }

            # Seleciona coleção apropriada
            collection = self.collections.get(doc_type, self.collections["generic"])

            # Adiciona ao ChromaDB
            collection.add(
                ids=[doc_id],
                embeddings=[main_embedding],
                documents=[content],
                metadatas=[doc_metadata],
            )

            logger.info(f"Documento indexado com sucesso: {doc_type} ({doc_id})")

        except Exception as e:
            logger.error(f"Falha ao indexar documento {doc_type}: {str(e)}")
            raise

    def _process_code_document(self, content: str) -> dict[str, any]:
        """
        Processa documento de código fonte
        """
        # Extrai blocos de código relevantes
        code_blocks = re.findall(
            r"```(?:python|javascript|typescript|java|cpp|csharp|go|rust)?\n(.*?)\n```",
            content,
            re.DOTALL,
        )
        if not code_blocks:
            # Se não encontrar blocos de código formatados, considera o conteúdo inteira como código
            code_blocks = [content.strip()]

        # Gera contexto baseado no tipo de código
        context = "code_implementation"
        if any(keyword in content.lower() for keyword in ["test", "unit test", "pytest", "junit"]):
            context = "code_testing"
        elif any(keyword in content.lower() for keyword in ["api", "endpoint", "route", "controller"]):
            context = "code_api"
        elif any(keyword in content.lower() for keyword in ["database", "sql", "query", "orm"]):
            context = "code_database"

        return {
            "main_text": content,
            "code_blocks": code_blocks,
            "context": context,
            "language": self._detect_programming_language(content),
        }

    def _process_arch_document(self, content: str) -> dict[str, any]:
        """
        Processa documento de arquitetura
        """
        # Identifica componentes e padrões arquiteturais
        context = "system_architecture"
        if any(keyword in content.lower() for keyword in ["microservice", "service", "distributed"]):
            context = "microservices_architecture"
        elif any(keyword in content.lower() for keyword in ["monolith", "monolithic"]):
            context = "monolithic_architecture"
        elif any(keyword in content.lower() for keyword in ["serverless", "lambda", "function"]):
            context = "serverless_architecture"

        return {
            "main_text": content,
            "code_blocks": [],
            "context": context,
            "architecture_patterns": self._extract_architecture_patterns(content),
        }

    def _process_req_document(self, content: str) -> dict[str, any]:
        """
        Processa documento de requisitos
        """
        context = "functional_requirements"
        if any(keyword in content.lower() for keyword in ["performance", "scalability", "security", "non-functional"]):
            context = "non_functional_requirements"

        return {
            "main_text": content,
            "code_blocks": [],
            "context": context,
            "requirement_types": self._extract_requirement_types(content),
        }

    def _process_commit_document(self, content: str) -> dict[str, any]:
        """
        Processa mensagem de commit
        """
        # Extrai tipo de commit (feat, fix, refactor, etc.)
        commit_type = "other"
        if content.lower().startswith(("feat:", "feature:")):
            commit_type = "feature"
        elif content.lower().startswith(("fix:", "bugfix:")):
            commit_type = "bugfix"
        elif content.lower().startswith(("refactor:", "refactoring:")):
            commit_type = "refactor"
        elif content.lower().startswith(("docs:", "documentation:")):
            commit_type = "documentation"
        elif content.lower().startswith(("test:", "testing:")):
            commit_type = "testing"
        elif content.lower().startswith(("chore:", "build:", "ci:")):
            commit_type = "maintenance"

        context = f"commit_{commit_type}"

        return {
            "main_text": content,
            "code_blocks": [],
            "context": context,
            "commit_type": commit_type,
            "changes_summary": self._summarize_commit_changes(content),
        }

    def _process_generic_document(self, content: str) -> dict[str, any]:
        """
        Processa documento genérico
        """
        return {
            "main_text": content,
            "code_blocks": [],
            "context": "generic_documentation",
            "document_type": self._classify_document_type(content),
        }

    def _detect_programming_language(self, content: str) -> str:
        """
        Detecta linguagem de programação no conteúdo
        """
        content_lower = content.lower()
        if any(lang in content_lower for lang in ["python", "import ", "def ", "class ", "pip install"]):
            return "python"
        elif any(
            lang in content_lower
            for lang in [
                "javascript",
                "js",
                "npm install",
                "function ",
                "const ",
                "let ",
            ]
        ):
            return "javascript"
        elif any(lang in content_lower for lang in ["typescript", "ts", "interface ", "type ", "enum "]):
            return "typescript"
        elif any(lang in content_lower for lang in ["java", "public class", "new ", ".java"]):
            return "java"
        elif any(lang in content_lower for lang in ["cpp", "c++", "#include", "std::", ".h", ".cpp"]):
            return "cpp"
        return "unknown"

    def _extract_architecture_patterns(self, content: str) -> list[str]:
        """
        Extrai padrões arquiteturais do conteúdo
        """
        patterns = []
        content_lower = content.lower()

        if "microservice" in content_lower or "micro-service" in content_lower:
            patterns.append("microservices")
        if "monolith" in content_lower or "monolithic" in content_lower:
            patterns.append("monolithic")
        if "serverless" in content_lower or "lambda" in content_lower:
            patterns.append("serverless")
        if "event-driven" in content_lower or "event driven" in content_lower:
            patterns.append("event-driven")
        if "layered" in content_lower or "n-tier" in content_lower or "n tier" in content_lower:
            patterns.append("layered")
        if "hexagonal" in content_lower or "ports and adapters" in content_lower:
            patterns.append("hexagonal")
        if "clean architecture" in content_lower:
            patterns.append("clean-architecture")
        if "ddd" in content_lower or "domain-driven design" in content_lower:
            patterns.append("domain-driven-design")

        return patterns or ["unknown"]

    def _extract_requirement_types(self, content: str) -> list[str]:
        """
        Extrai tipos de requisitos do conteúdo
        """
        types = []
        content_lower = content.lower()

        if any(word in content_lower for word in ["user interface", "ui", "ux", "screen", "page", "layout"]):
            types.append("ui_ux")
        if any(word in content_lower for word in ["api", "endpoint", "rest", "graphql", "interface"]):
            types.append("api")
        if any(word in content_lower for word in ["database", "data", "storage", "persist", "sql", "nosql"]):
            types.append("data")
        if any(word in content_lower for word in ["security", "auth", "authoriz", "encryption", "password"]):
            types.append("security")
        if any(word in content_lower for word in ["performance", "speed", "latency", "throughput", "scalability"]):
            types.append("performance")
        if any(word in content_lower for word in ["error", "exception", "handling", "recovery", "backup"]):
            types.append("error_handling")

        return types or ["functional"]

    def _summarize_commit_changes(self, content: str) -> str:
        """
        Sumariza mudanças de um commit
        """
        # Remove prefixo de tipo de commit
        content = re.sub(r"^\w+:\s*", "", content, count=1)

        # Limita a 100 caracteres para sumário
        if len(content) > 100:
            return content[:97] + "..."
        return content

    def _classify_document_type(self, content: str) -> str:
        """
        Classifica tipo de documento genérico
        """
        content_lower = content.lower()

        if any(word in content_lower for word in ["design", "architecture", "component", "module", "system"]):
            return "design"
        elif any(word in content_lower for word in ["requirement", "feature", "user story", "acceptance criteria"]):
            return "requirements"
        elif any(word in content_lower for word in ["test", "testing", "qa", "quality", "bug", "defect"]):
            return "testing"
        elif any(word in content_lower for word in ["api", "endpoint", "integration", "service", "microservice"]):
            return "api_documentation"
        elif any(
            word in content_lower
            for word in [
                "deploy",
                "deployment",
                "ci/cd",
                "pipeline",
                "build",
                "release",
            ]
        ):
            return "deployment"
        return "other"

    def batch_index_documents(self, documents: list[dict[str, any]]) -> dict[str, any]:
        """
        Indexa múltiplos documentos em lote

        Args:
            documents: Lista de documentos com estrutura {'type': str, 'content': str, 'metadata': dict}

        Returns:
            Dicionário com estatísticas de indexação
        """
        stats = {
            "total_documents": len(documents),
            "successful": 0,
            "failed": 0,
            "by_type": {},
            "errors": [],
        }

        for doc in documents:
            try:
                doc_type = doc.get("type", "generic")
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})

                self.index_technical_document(doc_type, content, metadata)

                stats["successful"] += 1
                stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1

            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append({"document_type": doc.get("type", "unknown"), "error": str(e)})
                logger.error(f"Erro ao indexar documento {doc.get('type', 'unknown')}: {str(e)}")

        logger.info(f"Indexação em lote concluída: {stats['successful']} sucesso, {stats['failed']} falhas")
        return stats

    def update_document(self, doc_id: str, new_content: str, metadata: dict[str, any] = None) -> bool:
        """
        Atualiza um documento existente

        Args:
            doc_id: ID do documento
            new_content: Novo conteúdo
            metadata: Novos metadados

        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            # Primeiro deleta o documento existente
            for collection_name, collection in self.collections.items():
                try:
                    collection.delete(ids=[doc_id])
                    logger.info(f"Documento {doc_id} deletado da coleção {collection_name}")
                    break
                except Exception:
                    continue

            # Reindexa com novo conteúdo
            # Determina tipo baseado no conteúdo
            doc_type = "generic"
            if any(lang in new_content.lower() for lang in ["python", "javascript", "java", "cpp", "code"]):
                doc_type = "code"
            elif any(word in new_content.lower() for word in ["architecture", "design", "pattern", "component"]):
                doc_type = "architecture"
            elif any(word in new_content.lower() for word in ["requirement", "feature", "user story"]):
                doc_type = "requirement"

            self.index_technical_document(doc_type, new_content, metadata)
            return True

        except Exception as e:
            logger.error(f"Falha ao atualizar documento {doc_id}: {str(e)}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        Deleta um documento pelo ID

        Args:
            doc_id: ID do documento

        Returns:
            True se deletado com sucesso, False caso contrário
        """
        try:
            deleted = False
            for collection_name, collection in self.collections.items():
                try:
                    collection.delete(ids=[doc_id])
                    logger.info(f"Documento {doc_id} deletado da coleção {collection_name}")
                    deleted = True
                    break
                except Exception:
                    continue

            return deleted

        except Exception as e:
            logger.error(f"Falha ao deletar documento {doc_id}: {str(e)}")
            return False
