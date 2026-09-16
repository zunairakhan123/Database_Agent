import chromadb
import sqlite3
import json
import logging
from typing import List
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from backend.app.core.schema_models import TableEntity

logger = logging.getLogger(__name__)

class HybridMetadataStore:
    def __init__(self):
        self.chroma = chromadb.PersistentClient(path=".chroma")
        self.sqlite = sqlite3.connect("operational_metadata.db", check_same_thread=False)
        self._init_operational_db()
        
        # Load lightweight Cross-Encoder for Stage 2 Reranking
        logger.info("Loading Cross-Encoder model...")
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)

    def _init_operational_db(self):
        self.sqlite.execute("""
            CREATE TABLE IF NOT EXISTS metadata_registry (
                urn TEXT PRIMARY KEY, workspace_id TEXT, fingerprint TEXT, payload JSON
            )
        """)
        self.sqlite.commit()

    def sync_entities_incrementally(self, entities: List[TableEntity]):
        collection = self.chroma.get_or_create_collection("schema_rag")
        for entity in entities:
            cursor = self.sqlite.execute("SELECT fingerprint FROM metadata_registry WHERE urn = ?", (entity.urn,))
            row = cursor.fetchone()
            if row and row[0] == entity.fingerprint:
                continue 
                
            collection.upsert(
                ids=[entity.urn],
                documents=[entity.to_embedding_string()],
                metadatas=[{"workspace_id": entity.workspace_id, "table_name": entity.physical.table_name}] 
            )
            self.sqlite.execute(
                "REPLACE INTO metadata_registry (urn, workspace_id, fingerprint, payload) VALUES (?, ?, ?, ?)",
                (entity.urn, entity.workspace_id, entity.fingerprint, entity.model_dump_json())
            )
        self.sqlite.commit()

    def hybrid_search(self, workspace_id: str, query: str, top_k: int = 3) -> List[str]:
        """V2 Retrieval: Dense + Clean Lexical -> Cross-Encoder Reranking"""
        
        # --- STAGE 1: HIGH RECALL RETRIEVAL ---
        # 1A. Dense Search (Chroma)
        collection = self.chroma.get_or_create_collection("schema_rag")
        dense_urns = set()
        if collection.count() > 0:
            dense_results = collection.query(
                query_texts=[query], n_results=10, where={"workspace_id": workspace_id}
            )
            if dense_results["ids"]:
                dense_urns.update(dense_results["ids"][0])

        # 1B. Clean Lexical Search (BM25)
        cursor = self.sqlite.execute("SELECT urn, payload FROM metadata_registry WHERE workspace_id = ?", (workspace_id,))
        rows = cursor.fetchall()
        
        lexical_urns = set()
        schema_docs = {}
        if rows:
            corpus = []
            urn_list = []
            for row in rows:
                urn, payload_str = row[0], row[1]
                payload = json.loads(payload_str)
                
                # FIX: Build corpus only from table names and column names (ignore JSON structural keys)
                t_name = payload.get("physical", {}).get("table_name", "").lower()
                cols = [c["name"].lower() for c in payload.get("physical", {}).get("columns", [])]
                clean_text = f"{t_name} " + " ".join(cols)
                
                corpus.append(clean_text.split())
                urn_list.append(urn)
                schema_docs[urn] = clean_text # Save for reranker
                
            tokenized_query = query.lower().split()
            bm25 = BM25Okapi(corpus)
            scores = bm25.get_scores(tokenized_query)
            
            lexical_ranked = [urn for _, urn in sorted(zip(scores, urn_list), reverse=True) if _ > 0]
            lexical_urns.update(lexical_ranked[:10])

        # Combine Stage 1 candidates
        candidate_urns = list(dense_urns.union(lexical_urns))
        if not candidate_urns:
            return []

        # --- STAGE 2: CROSS-ENCODER RERANKING ---
        # Evaluate how well the query matches the clean schema text
        rerank_pairs = [[query, schema_docs[urn]] for urn in candidate_urns]
        rerank_scores = self.reranker.predict(rerank_pairs)
        
        # Sort URNs by their cross-encoder score descending
        ranked_results = [urn for _, urn in sorted(zip(rerank_scores, candidate_urns), reverse=True)]
        
        return ranked_results[:top_k]

metadata_store = HybridMetadataStore()