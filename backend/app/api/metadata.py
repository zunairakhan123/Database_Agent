from pydantic import BaseModel
from typing import List
from fastapi import APIRouter, Header, HTTPException
from backend.app.database.session_manager import session_manager
from backend.app.database.metadata_extractor import extract_schema_entities, enrich_schema_descriptions
from backend.app.database.metadata_store import metadata_store
from backend.app.database.semantic_store import semantic_store
from backend.app.core.semantic_models import JoinRule
from backend.app.agent.semantic_drafter import auto_draft_metrics
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class SyncRequest(BaseModel):
    selected_tables: List[str] 

class SearchQuery(BaseModel):
    query: str
    top_k: int = 3

@router.post("/metadata/sync")
def sync_metadata(
    req: SyncRequest, 
    workspace_id: str = Header(alias="X-Workspace-ID")
):
    try:
        session = session_manager.get_session(workspace_id)
        
        raw_entities = extract_schema_entities(session, selected_tables=req.selected_tables)
        enriched_entities = enrich_schema_descriptions(raw_entities)
        metadata_store.sync_entities_incrementally(enriched_entities)
        
        # --- NEW: Unified Topology Registry ---
        # Push physical database constraints to the Semantic Store so the LLM and ERD can use them
        for entity in enriched_entities:
            schema = entity.physical.schema_name
            t_name = entity.physical.table_name
            source_fqn = f"{schema}.{t_name}" if schema != 'main' else t_name
            
            for col in entity.physical.columns:
                if col.foreign_keys:
                    for fk_urn in col.foreign_keys:
                        target_fqn = fk_urn.split(":")[-1]
                        
                        rule = JoinRule(
                            source_urn=source_fqn,
                            target_urn=target_fqn,
                            condition=f"{source_fqn}.{col.name} = {target_fqn}.id", # Target default ID
                            join_type="INNER",
                            cardinality="1:N",
                            is_user_defined=False # Flags it as a native DB relationship
                        )
                        semantic_store.add_join_rule(workspace_id, rule)

        schema_context = "\n".join([e.to_embedding_string() for e in enriched_entities])
        draft_result = auto_draft_metrics(workspace_id, schema_context)
        
        return {
            "status": "success",
            "indexed_tables": req.selected_tables,
            "drafted_metrics": draft_result.get("drafted_metrics", [])
        }
    except Exception as e:
        logger.error(f"[SYNC FAILED] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/metadata/search")
def search_schema(
    payload: SearchQuery,
    workspace_id: str = Header(alias="X-Workspace-ID")
):
    try:
        results = metadata_store.hybrid_search(workspace_id, payload.query, top_k=payload.top_k)
        return {"query": payload.query, "matched_urns": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))