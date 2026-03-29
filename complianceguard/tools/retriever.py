"""
ComplianceGuard — retriever.py
================================
Retriever hybride GraphRAG : combine recherche vectorielle et
traversée du knowledge graph Neo4j pour des réponses juridiques précises.

Deux modes :
  - VectorRetriever     : similarité sémantique sur les chunks
  - GraphRetriever      : traversée du graphe de relations légales
  - HybridRetriever     : fusion des deux (recommandé pour ComplianceGuard)
"""

import os
from complianceguard.config import config, get_azure_llm_kwargs, get_ollama_embed_kwargs
from typing import Any, List
from pathlib import Path
import re

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from langchain_ollama import OllamaEmbeddings
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph
from langchain_core.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun

load_dotenv()

# ── CONNEXIONS ────────────────────────────────────────────────────────────────

def get_qdrant_client() -> QdrantClient:
    qdrant_url = config.QDRANT_URL.strip()
    qdrant_api_key = config.QDRANT_API_KEY.strip()
    if qdrant_url:
        kwargs = {"url": qdrant_url}
        if qdrant_api_key:
            kwargs["api_key"] = qdrant_api_key
        return QdrantClient(**kwargs)

    qdrant_path = str(Path(__file__).resolve().parents[2] / ".qdrant")
    return QdrantClient(path=qdrant_path)


def get_embeddings_model() -> OllamaEmbeddings:
    return OllamaEmbeddings(**get_ollama_embed_kwargs())


def get_graph() -> Neo4jGraph:
    return Neo4jGraph(
        url=config.NEO4J_URI,
        username=config.NEO4J_USERNAME,
        password=config.NEO4J_PASSWORD
    )


class ComplianceGuardRetriever(BaseRetriever):
    """
    Retriever hybride pour ComplianceGuard.
    Combine :
      1. Recherche vectorielle (similarité sémantique sur chunks)
      2. Traversée du graphe Neo4j (relations juridiques)
      3. Re-ranking par pertinence légale
    """

    qdrant_client: QdrantClient
    embeddings: OllamaEmbeddings
    qdrant_collection: str
    graph: Neo4jGraph
    k_vector: int = 4       # Nombre de chunks vectoriels
    k_graph: int = 5        # Nombre de résultats graph

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:

        docs = []

        # 1. Recherche vectorielle
        vector_docs = self._vector_search(query)
        docs.extend(vector_docs)

        # 2. Recherche dans le graphe Neo4j via Cypher
        graph_docs = self._graph_search(query)
        docs.extend(graph_docs)

        # 3. Dédoublonnage et tri par score de pertinence légale
        seen, unique = set(), []
        for d in docs:
            key = d.page_content[:100]
            if key not in seen:
                seen.add(key)
                unique.append(d)

        # Laisse de la place aux preuves relationnelles (paths + summary) ajoutées
        # après les résultats vectoriels pour mieux couvrir les requêtes multi-hop.
        return unique[: self.k_vector + self.k_graph + 6]

    def _qdrant_search(self, query_vector: list[float]) -> list[Any]:
        """Compatibilité qdrant-client: search (legacy) et query_points (new)."""
        if hasattr(self.qdrant_client, "search"):
            return self.qdrant_client.search(
                collection_name=self.qdrant_collection,
                query_vector=query_vector,
                limit=self.k_vector,
                with_payload=True,
            )

        result = self.qdrant_client.query_points(
            collection_name=self.qdrant_collection,
            query=query_vector,
            limit=self.k_vector,
            with_payload=True,
        )
        return list(getattr(result, "points", []) or [])

    def _fetch_doc_by_id(self, doc_id: str, payload: dict[str, Any], score: float) -> Document | None:
        doc_query = """
        MATCH (d:Document {id: $doc_id})
        OPTIONAL MATCH (d)-[:MENTIONS]->(e)
        RETURN d.text AS text,
               d.reference AS reference,
               d.source_file AS source_file,
               collect(DISTINCT coalesce(e.description, e.id))[0..5] AS entities
        LIMIT 1
        """
        chunk_query = """
        MATCH (c:Chunk)
        WHERE c.id = $doc_id OR c.chunk_id = $doc_id
        RETURN c.text AS text,
               c.reference AS reference,
               c.source_file AS source_file,
               [] AS entities
        LIMIT 1
        """

        rows = self.graph.query(doc_query, params={"doc_id": doc_id})
        if not rows:
            rows = self.graph.query(chunk_query, params={"doc_id": doc_id})

        if rows:
            row = rows[0]
            text = row.get("text") or ""
            reference = row.get("reference") or payload.get("reference", "")
            source_file = row.get("source_file") or payload.get("source_file", "")
            entities = [e for e in (row.get("entities") or []) if e]
        else:
            text = payload.get("text_snippet", "")
            reference = payload.get("reference", "")
            source_file = payload.get("source_file", "")
            entities = []

        if not text:
            return None

        if entities:
            text = f"{text}\nEntités liées: {', '.join(entities)}"

        return Document(
            page_content=text,
            metadata={
                "retrieval_source": "vector_qdrant",
                "reference": reference,
                "source_file": source_file,
                "doc_id": doc_id,
                "score": score,
            },
        )

    def _vector_search(self, query: str) -> List[Document]:
        """Recherche vectorielle dans Qdrant puis récupération du contexte dans Neo4j."""
        try:
            query_vector = self.embeddings.embed_query(query)
            results = self._qdrant_search(query_vector)
        except Exception as e:
            print(f"[QdrantSearch] Erreur: {e}")
            return []

        docs = []
        for item in results:
            payload = getattr(item, "payload", None) or {}
            doc_id = str(payload.get("doc_id") or getattr(item, "id", ""))
            if not doc_id:
                continue

            score = float(getattr(item, "score", 0.0) or 0.0)
            doc = self._fetch_doc_by_id(doc_id, payload, score)
            if doc:
                docs.append(doc)

        return docs

    def _graph_search(self, query: str) -> List[Document]:
        """
        Recherche dans le graphe Neo4j.
        Extrait les nœuds liés à la question via des requêtes Cypher ciblées.
        """
        # Requête générale : trouve les avantages et obligations liés à la question
        cypher = """
        CALL db.index.fulltext.queryNodes('legal_entities', $query)
        YIELD node, score
        WITH node, score
        ORDER BY score DESC
        LIMIT $limit
        OPTIONAL MATCH (node)-[r]->(related)
         RETURN coalesce(node.description, node.valeur, node.reference, node.id) AS description,
             coalesce(node.reference, node.id) AS reference,
               labels(node) AS types,
             collect({
                 type: type(r),
                 target: coalesce(related.description, related.valeur, related.reference, related.id)
             }) AS relations,
               score
        """
        try:
            results = self.graph.query(
                cypher,
                params={"query": query, "limit": self.k_graph}
            )
            docs = []
            for r in results:
                if r.get("description"):
                    content = f"[{', '.join(r['types'])}] {r['reference']}: {r['description']}"
                    if r.get("relations"):
                        rels = "; ".join(
                            f"{rel['type']} → {rel['target']}"
                            for rel in r["relations"][:3]
                            if rel.get("target")
                        )
                        if rels:
                            content += f"\nRelations: {rels}"
                    docs.append(Document(
                        page_content=content,
                        metadata={
                            "retrieval_source": "graph",
                            "reference": r.get("reference", ""),
                            "score": r.get("score", 0),
                        }
                    ))

            # Fallback relationnel: injecte des chemins explicites src-[REL]->tgt
            # pour renforcer les requêtes multi-hop orientées inter-documents.
            rel_types = [
                "APPLIQUE", "REFERENCE", "MODIFIE",
                "PREVOIT", "CONDITIONNE", "CONCERNE",
                "DEPEND_DE", "FIXE",
            ]

            tokens = [
                tok for tok in re.findall(r"[a-zA-Z0-9_-]{4,}", query.lower())
                if tok not in {"avec", "dans", "pour", "entre", "quels", "quelles", "donne"}
            ]

            relation_cypher = """
            MATCH (a)-[r]->(b)
            WHERE type(r) IN $rel_types
              AND (
                size($tokens) = 0 OR
                any(tok IN $tokens WHERE
                  toLower(coalesce(a.reference, '')) CONTAINS tok OR
                  toLower(coalesce(b.reference, '')) CONTAINS tok OR
                  toLower(coalesce(a.description, '')) CONTAINS tok OR
                  toLower(coalesce(b.description, '')) CONTAINS tok
                )
              )
            RETURN coalesce(a.reference, a.id) AS src,
                   type(r) AS rel,
                   coalesce(b.reference, b.id) AS tgt
            LIMIT $limit
            """

            rel_rows = self.graph.query(
                relation_cypher,
                params={
                    "rel_types": rel_types,
                    "tokens": tokens,
                    "limit": self.k_graph,
                },
            )

            if not rel_rows:
                rel_rows = self.graph.query(
                    """
                    MATCH (a)-[r]->(b)
                    WHERE type(r) IN $rel_types
                    RETURN coalesce(a.reference, a.id) AS src,
                           type(r) AS rel,
                           coalesce(b.reference, b.id) AS tgt
                    LIMIT $limit
                    """,
                    params={"rel_types": rel_types, "limit": self.k_graph},
                )

            for row in rel_rows:
                src = row.get("src") or ""
                rel = row.get("rel") or ""
                tgt = row.get("tgt") or ""
                if not (src and rel and tgt):
                    continue
                docs.append(
                    Document(
                        page_content=f"[Path] {src} -[{rel}]-> {tgt}",
                        metadata={
                            "retrieval_source": "graph_path",
                            "reference": src,
                            "score": 1.0,
                        },
                    )
                )

            summary_rows = self.graph.query(
                """
                MATCH ()-[r]->()
                WHERE type(r) IN $rel_types
                RETURN type(r) AS rel, count(*) AS c
                ORDER BY c DESC
                LIMIT 12
                """,
                params={"rel_types": rel_types},
            )

            if summary_rows:
                rel_summary = ", ".join(
                    f"{row.get('rel')}({row.get('c')})"
                    for row in summary_rows
                    if row.get("rel")
                )
                if rel_summary:
                    docs.append(
                        Document(
                            page_content=f"[RelationSummary] {rel_summary}",
                            metadata={
                                "retrieval_source": "graph_summary",
                                "reference": "graph",
                                "score": 1.0,
                            },
                        )
                    )

            return docs
        except Exception as e:
            print(f"[GraphSearch] Erreur Cypher: {e}")
            return []


def get_hybrid_retriever() -> ComplianceGuardRetriever:
    """Factory pour obtenir le retriever hybride configuré."""
    return ComplianceGuardRetriever(
        qdrant_client=get_qdrant_client(),
        embeddings=get_embeddings_model(),
        qdrant_collection=config.QDRANT_COLLECTION_NAME,
        graph=get_graph(),
        k_vector=4,
        k_graph=5,
    )


# ── SETUP INDEX FULLTEXT NEO4J ────────────────────────────────────────────────

def setup_fulltext_index():
    """
    Crée l'index fulltext Neo4j pour la recherche dans le graphe.
    À exécuter une seule fois après l'ingestion.
    """
    graph = get_graph()
    try:
        graph.query("""
        CREATE FULLTEXT INDEX legal_entities IF NOT EXISTS
        FOR (n:Article|Loi|Decret|Circulaire|Organisme|Avantage|Obligation|Condition)
        ON EACH [n.description, n.reference, n.valeur]
        """)
        print("Index fulltext 'legal_entities' créé ✓")
    except Exception as e:
        print(f"Index fulltext: {e}")


if __name__ == "__main__":
    print("Setup des index Neo4j...")
    setup_fulltext_index()
    print("Retriever prêt.")