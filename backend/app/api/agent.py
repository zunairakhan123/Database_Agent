import logging
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.app.agent.graph import agent_app

router = APIRouter()
logger = logging.getLogger(__name__)

class QueryRequest(BaseModel):
    question: str
    chat_history: Optional[List[Dict[str, str]]] = []  # e.g., [{"role": "user", "content": "..."}]

class QueryResponse(BaseModel):
    question: str
    conversational_reply: Optional[str]
    generated_sql: Optional[str]
    retries: int
    results: Optional[List[Dict[str, Any]]]
    error: Optional[str]

@router.post("/query", response_model=QueryResponse)
def execute_natural_language_query(
    req: QueryRequest,
    workspace_id: str = Header(alias="X-Workspace-ID")
):
    """Executes a natural language query via the LangGraph AI Agent."""
    logger.info(f"--- Incoming Query for Workspace: {workspace_id} ---")
    
    # Context Truncation: Keep only the last 10 messages (5 turns)
    MAX_HISTORY_LENGTH = 10
    trimmed_history = req.chat_history[-MAX_HISTORY_LENGTH:] if req.chat_history else []
    
    initial_state = {
        "workspace_id": workspace_id,
        "question": req.question,
        "chat_history": trimmed_history,
        "retrieved_urns": [],
        "schema_context": "",
        "semantic_context": "",
        "generated_sql": None,
        "conversational_reply": None,
        "error_message": None,
        "retries": 0,
        "results": None
    }
    
    try:
        # ✅ FIX: Pass the workspace_id as the thread configuration so SqliteSaver tracks state per workspace
        config = {"configurable": {"thread_id": workspace_id}}
        final_state = agent_app.invoke(initial_state, config)
        
        error_val = final_state.get("error_message")
        is_guardrail = error_val in ["INPUT_REJECTED", "MATH_REJECTED"]
        
        return QueryResponse(
            question=req.question,
            conversational_reply=final_state.get("conversational_reply"),
            generated_sql=final_state.get("generated_sql"),
            retries=final_state.get("retries", 0),
            results=final_state.get("results"),
            error=None if is_guardrail else error_val
        )
    except Exception as e:
        logger.error(f"[CRITICAL AGENT FAILURE] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))