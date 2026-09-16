# from langgraph.graph import StateGraph, END
# from backend.app.agent.state import AgentState
# # Added analyze_input to the import list
# from backend.app.agent.nodes import analyze_input, retrieve_context, generate_sql, validate_and_execute
# from langgraph.checkpoint.sqlite import SqliteSaver
# import sqlite3

# # Connect to your operational metadata DB or a dedicated checkpointer db
# conn = sqlite3.connect("operational_metadata.db", check_same_thread=False)
# memory = SqliteSaver(conn)

# def route_execution(state: AgentState):
#     """Determines where the graph goes after attempting execution."""
    
#     # Check for hard guardrail rejections (INPUT_REJECTED or MATH_REJECTED)
#     # Since validate_and_execute sets results to [] on rejection, this will safely trigger END.
#     if state.get("results") is not None:
#         return END # Success or Guardrail Rejection handled gracefully
        
#     if state.get("retries", 0) >= 3:
#         return END # Reached max retries, fail gracefully.
        
#     return "generate_sql" # Loop back to LLM to self-correct the SQL error.

# # Build the Graph
# workflow = StateGraph(AgentState)

# # Add all 4 nodes
# workflow.add_node("analyze_input", analyze_input)
# workflow.add_node("retrieve_context", retrieve_context)
# workflow.add_node("generate_sql", generate_sql)
# workflow.add_node("validate_and_execute", validate_and_execute)

# # Define the Flow (analyze_input is the new gatekeeper)
# workflow.set_entry_point("analyze_input")
# workflow.add_edge("analyze_input", "retrieve_context")
# workflow.add_edge("retrieve_context", "generate_sql")
# workflow.add_edge("generate_sql", "validate_and_execute")

# # The Conditional Loop
# workflow.add_conditional_edges(
#     "validate_and_execute",
#     route_execution,
#     {
#         END: END,
#         "generate_sql": "generate_sql"
#     }
# )

# agent_app = workflow.compile(checkpointer=memory)


from langgraph.graph import StateGraph, END
from backend.app.agent.state import AgentState
from backend.app.agent.nodes import analyze_input, retrieve_context, generate_sql, validate_and_execute, sanitize_error
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

conn = sqlite3.connect("operational_metadata.db", check_same_thread=False)
memory = SqliteSaver(conn)

def route_execution(state: AgentState):
    """Determines where the graph goes after attempting execution."""
    
    # If successful execution OR handled gracefully by an early guardrail
    if state.get("results") is not None:
        return END 
        
    # If the corrector hits the retry limit, route to the sanitizer to hide the stack trace
    if state.get("retries", 0) >= 3:
        return "sanitize_error"
        
    # Loop back to LLM to self-correct the SQL error
    return "generate_sql"

# Build the Graph
workflow = StateGraph(AgentState)

# Add all 5 nodes
workflow.add_node("analyze_input", analyze_input)
workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("generate_sql", generate_sql)
workflow.add_node("validate_and_execute", validate_and_execute)
workflow.add_node("sanitize_error", sanitize_error)

# Define the Flow
workflow.set_entry_point("analyze_input")
workflow.add_edge("analyze_input", "retrieve_context")
workflow.add_edge("retrieve_context", "generate_sql")
workflow.add_edge("generate_sql", "validate_and_execute")

# The Conditional Loop
workflow.add_conditional_edges(
    "validate_and_execute",
    route_execution,
    {
        END: END,
        "generate_sql": "generate_sql",
        "sanitize_error": "sanitize_error"
    }
)

# Safely close the loop
workflow.add_edge("sanitize_error", END)

agent_app = workflow.compile(checkpointer=memory)