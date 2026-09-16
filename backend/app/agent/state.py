from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    # Tenant & Session Context
    workspace_id: str
    question: str
    chat_history: Optional[List[Dict[str, str]]]  # Sliding-window context

    # Context Retrieval (RAG & Semantic Layer)
    retrieved_urns: List[str]
    schema_context: str
    semantic_context: str

    # Execution & Routing
    generated_sql: Optional[str]
    conversational_reply: Optional[str]           # For guardrail pushback & narrative
    error_message: Optional[str]
    retries: int

    # Final Output
    results: Optional[List[Dict[str, Any]]]