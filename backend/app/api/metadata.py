from pydantic import BaseModel, Field
from typing import List, Optional
from fastapi import APIRouter, Header, HTTPException
from backend.app.database.session_manager import session_manager
from backend.app.database.metadata_extractor import extract_schema_entities, enrich_schema_descriptions
from backend.app.database.metadata_store import metadata_store
from backend.app.database.semantic_store import semantic_store
from backend.app.core.semantic_models import JoinRule
from backend.app.core.schema_models import TableEntity
from backend.app.agent.semantic_drafter import auto_draft_metrics
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class SyncRequest(BaseModel):
    selected_tables: List[str] 

class SearchQuery(BaseModel):
    query: str
    top_k: int = 3

class ColumnMetadataEdit(BaseModel):
    name: str
    business_name: Optional[str] = Field(default=None, max_length=200)

class MetadataReindexRequest(BaseModel):
    urn: str
    business_name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    columns: List[ColumnMetadataEdit]

@router.get("/metadata/entities")
def get_metadata_entities(
    table_name: Optional[str] = None,
    workspace_id: str = Header(alias="X-Workspace-ID")
):
    try:
        cursor = metadata_store.sqlite.execute(
            "SELECT urn, payload FROM metadata_registry WHERE workspace_id = ?",
            (workspace_id,)
        )
        entities = []
        for urn, payload in cursor.fetchall():
            entity = TableEntity.model_validate_json(payload)
            fqn = (
                f"{entity.physical.schema_name}.{entity.physical.table_name}"
                if entity.physical.schema_name != "main"
                else entity.physical.table_name
            )
            if table_name and fqn != table_name:
                continue
            entities.append({
                "urn": urn,
                "physical": entity.physical.model_dump(),
                "business": entity.business.model_dump()
            })
        return {"entities": entities}
    except Exception as e:
        logger.error(f"[METADATA FETCH FAILED] {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to load indexed metadata.")

@router.post("/metadata/reindex")
def reindex_metadata(
    req: MetadataReindexRequest,
    workspace_id: str = Header(alias="X-Workspace-ID")
):
    try:
        cursor = metadata_store.sqlite.execute(
            "SELECT payload FROM metadata_registry WHERE urn = ? AND workspace_id = ?",
            (req.urn, workspace_id)
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Indexed table metadata was not found. Sync the table first.")

        entity = TableEntity.model_validate_json(row[0])
        known_columns = {column.name: column for column in entity.physical.columns}
        submitted_columns = {column.name: column for column in req.columns}
        if len(submitted_columns) != len(req.columns) or set(submitted_columns) != set(known_columns):
            raise HTTPException(status_code=422, detail="Column metadata must include each indexed column exactly once.")

        if "business_name" in req.model_fields_set:
            entity.business.business_name = req.business_name
        if "description" in req.model_fields_set:
            entity.business.user_description = req.description
        for name, edit in submitted_columns.items():
            known_columns[name].business_name = edit.business_name

        metadata_store.reindex_entity(entity)
        return {"status": "success", "reindexed_table": req.urn}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[METADATA REINDEX FAILED] {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to save metadata and refresh its search index.")

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