import json
from fastapi import APIRouter, Header, HTTPException
from typing import Optional
from backend.app.database.session_manager import session_manager
from backend.app.database.semantic_store import semantic_store
from backend.app.database.metadata_store import metadata_store
from backend.app.core.semantic_models import JoinRule

router = APIRouter()

@router.get("/tables")
def get_available_tables(workspace_id: str = Header(alias="X-Workspace-ID")):
    try:
        session = session_manager.get_session(workspace_id)
        query = """
            SELECT table_catalog, table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog') 
            AND table_schema NOT LIKE 'pg_toast%'
            AND table_type = 'BASE TABLE';
        """
        tables = session.conn.execute(query).fetchall()
        return {
            "tables": [
                {
                    "catalog": t[0], 
                    "schema": t[1], 
                    "name": t[2], 
                    "fqn": f"{t[1]}.{t[2]}" if t[1] != 'main' else t[2]
                } for t in tables
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/erd")
def get_erd_topology(
    selected_tables: Optional[str] = None, 
    workspace_id: str = Header(alias="X-Workspace-ID")
):
    """Returns ERD nodes and fully unified Topology Edges."""
    print(f"\n--- Fetching Logical ERD for Workspace: {workspace_id} ---")
    try:
        filter_list = [t.strip() for t in selected_tables.split(",") if t.strip()] if selected_tables else []
        nodes = []
        edges = []
        
        # 1. Fetch Logical Entities (Nodes)
        cursor = metadata_store.sqlite.execute(
            "SELECT payload FROM metadata_registry WHERE workspace_id = ?", 
            (workspace_id,)
        )
        for row in cursor.fetchall():
            payload = json.loads(row[0])
            phys = payload.get("physical", {})
            bus = payload.get("business", {})
            
            schema = phys.get("schema_name", "")
            t_name = phys.get("table_name", "")
            fqn = f"{schema}.{t_name}" if schema != 'main' else t_name
            
            if filter_list and fqn not in filter_list:
                continue
                
            columns = []
            for c in phys.get("columns", []):
                columns.append({
                    "name": c.get("name"), 
                    "label": c.get("business_name") or c.get("name"), 
                    "type": c.get("data_type")
                })
                
            nodes.append({
                "id": fqn,
                "data": {"label": bus.get("business_name") or t_name, "schema": schema, "columns": columns}, 
                "position": {"x": 0, "y": 0} 
            })

        # 2. Fetch Unified Edges (Both Physical DB constraints & Manual UI Joins)
        semantic_joins = semantic_store.get_join_rules(workspace_id)
        for join in semantic_joins:
            if filter_list and (join.source_urn not in filter_list or join.target_urn not in filter_list):
                continue

            edges.append({
                "id": f"edge-{join.source_urn}-{join.target_urn}",
                "source": join.source_urn,
                "target": join.target_urn,
                "type": "editable",
                "animated": join.is_user_defined, # User joins are dashed/animated, DB joins are solid
                "style": {
                    "stroke": "#3b82f6" if join.is_user_defined else "#94a3b8", 
                    "strokeWidth": 2, 
                    "strokeDasharray": "5,5" if join.is_user_defined else "none"
                },
                "data": {
                    "source_table": join.source_urn,
                    "target_table": join.target_urn,
                    "condition": join.condition,
                    "join_type": join.join_type,
                    "cardinality": join.cardinality,
                    "is_physical": not join.is_user_defined
                }
            })

        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/join-rule")
def add_manual_join_rule(rule: JoinRule, workspace_id: str = Header(alias="X-Workspace-ID")):
    try:
        semantic_store.add_join_rule(workspace_id, rule)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/join-rule/{source_urn}/{target_urn}")
def delete_manual_join_rule(source_urn: str, target_urn: str, workspace_id: str = Header(alias="X-Workspace-ID")):
    try:
        semantic_store.delete_join_rule(workspace_id, source_urn, target_urn)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))