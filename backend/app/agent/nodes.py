import json
import logging
import os
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from backend.app.agent.state import AgentState
from langchain_groq import ChatGroq
from backend.app.database.metadata_store import metadata_store
from backend.app.database.session_manager import session_manager
from backend.app.agent.ast_validator import validate_read_only_ast
from backend.app.database.semantic_store import semantic_store
from dotenv import load_dotenv

load_dotenv()
# --- PRODUCTION LOGGING SETUP ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

OLLAMA_TUNNEL_URL = "https://subscriptions-persons-emission-thus.trycloudflare.com/v1"

# llm = ChatOpenAI(
#     base_url=OLLAMA_TUNNEL_URL,
#     api_key="ollama",
#     model="qwen3-coder-next:latest",
#     temperature=0.0
# )


# --- GROQ API INITIALIZATION ---
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"), 
    model_name="openai/gpt-oss-20b", 
    temperature=0.0 # Zero for deterministic output
)

# --- PYDANTIC SCHEMAS FOR STRUCTURED OUTPUT ---
class InputGuardrail(BaseModel):
    is_data_query: bool = Field(description="True ONLY if the user is asking a data analysis, metrics, or database query. False for general chat, coding help, or off-topic subjects (e.g., fashion, weather).")
    rejection_reason: Optional[str] = Field(description="If is_data_query is False, provide a polite 1-sentence explanation that you are a specialized BI agent.")

class SQLGuardrailOutput(BaseModel):
    is_valid_analytical_request: bool = Field(description="False if the user asks to perform math (SUM, AVG) on categorical IDs (Postal Codes, Phone Numbers).")
    conversational_response: str = Field(description="Explain why the query is invalid, or confirm the analytical approach if valid.")
    sql_query: Optional[str] = Field(description="The pure DuckDB SQL query. Null if invalid.")

class SanitizeErrorOutput(BaseModel):
    friendly_message: str = Field(description="A polite, non-technical explanation of the failure.")

# --- AGENT NODES ---

def analyze_input(state: AgentState) -> dict:
    """ENTRY NODE: Input Guardrail to block non-BI queries."""
    logger.info(f"[NODE: analyze_input] Validating query intent: '{state['question']}'")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an Enterprise BI routing agent. Determine if the user's input is a valid database/analytics query."),
        ("human", "{question}")
    ])
    
    structured_llm = llm.with_structured_output(InputGuardrail)
    chain = prompt | structured_llm
    response = chain.invoke({"question": state["question"]})
    
    if not response.is_data_query:
        logger.warning(f"[GUARDRAIL BLOCKED] Off-topic query detected: {response.rejection_reason}")
        return {
            "error_message": "INPUT_REJECTED",
            "conversational_reply": response.rejection_reason
        }
        
    logger.info("[GUARDRAIL PASSED] Query is valid for BI analysis.")
    return {"error_message": None}

def retrieve_context(state: AgentState) -> dict:
    """Uses Hybrid RRF to pull schemas and fetches Business Metrics."""
    if state.get("error_message") == "INPUT_REJECTED":
        return {}

    logger.info(f"[NODE: retrieve_context] Fetching schemas for workspace: {state['workspace_id']}")
    urns = metadata_store.hybrid_search(state["workspace_id"], state["question"], top_k=3)
    
    schema_texts = []
    for urn in urns:
        cursor = metadata_store.sqlite.execute("SELECT payload FROM metadata_registry WHERE urn = ?", (urn,))
        row = cursor.fetchone()
        if row:
            payload = json.loads(row[0])
            catalog = payload.get("source_id", "")
            schema = payload.get("physical", {}).get("schema_name", "")
            table = payload.get("physical", {}).get("table_name", "")
            
            fqn = f"{schema}.{table}" if schema == "main" else f"{catalog}.{schema}.{table}"
            columns_str = ", ".join([f"{c['name']} ({c['data_type']})" for c in payload['physical']['columns']])
            schema_texts.append(f"TABLE TO USE: {fqn}\nCOLUMNS: {columns_str}\n")
            
    if not schema_texts:
        logger.warning("[RAG FALLBACK] No semantic match found. Extracting raw DuckDB main schema.")
        session = session_manager.get_session(state["workspace_id"])
        tables = session.conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()
        for t in tables:
            t_name = t[0]
            cols = session.conn.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{t_name}'").fetchall()
            col_str = ", ".join([f"{c[0]} ({c[1]})" for c in cols])
            schema_texts.append(f"TABLE TO USE: main.{t_name}\nCOLUMNS: {col_str}\n")

    # 1. Collect the exact Fully Qualified Names (FQNs) we are passing to the LLM
    retrieved_fqns = []
    for text in schema_texts:
        lines = text.split('\n')
        if lines[0].startswith("TABLE TO USE: "):
            retrieved_fqns.append(lines[0].replace("TABLE TO USE: ", "").strip())

    # 2. Fetch dependencies ONCE
    metrics = semantic_store.get_metrics(state["workspace_id"])
    join_rules = semantic_store.get_join_rules(state["workspace_id"])
    
    # 3. Build Semantic Context
    semantic_context = "CRITICAL BUSINESS METRICS:\n" + "".join([f"- {m.name}: {m.calculation} on {m.base_urn}\n" for m in metrics]) if metrics else ""
    
    # 4. Programmatic Namespace Normalization
    normalized_join_texts = []
    if join_rules:
        for j in join_rules:
            # Dynamically map the saved semantic URN to the exact physical FQN
            norm_source = next((fqn for fqn in retrieved_fqns if fqn.endswith(j.source_urn)), j.source_urn)
            norm_target = next((fqn for fqn in retrieved_fqns if fqn.endswith(j.target_urn)), j.target_urn)
            
            normalized_join_texts.append(
                f"- {norm_source} to {norm_target} ON {j.condition} (Type: {j.join_type}, Cardinality: {j.cardinality})"
            )
            
        semantic_context += "\nCUSTOM JOIN RULES:\n" + "\n".join(normalized_join_texts) + "\n"

    print("\n" + "-"*20)
    print(f"RAG RETRIEVAL FOR QUERY: '{state['question']}'")
    print("-" * 50)
    print("📎 SCHEMA CHUNKS RETRIEVED:")
    for text in schema_texts:
        print(text.strip())
        print("-" * 20)
    if semantic_context:
        print(" INJECTED SEMANTIC RULES:")
        print(semantic_context.strip())
    print("-"*20 + "\n")

    return {"retrieved_urns": urns, "schema_context": "\n".join(schema_texts), "semantic_context": semantic_context}


def generate_sql(state: AgentState) -> dict:
    """Generates pure DuckDB SQL with Structured Output logical validation."""
    if state.get("error_message") == "INPUT_REJECTED":
        return {}

    logger.info("[NODE: generate_sql] Drafting SQL via LLM...")
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a highly constrained Enterprise Agentic BI Assistant generating federated SQL for DuckDB.
Your primary task is to evaluate the user's analytical request against the provided schemas, semantic metrics, and join rules, and populate the required output fields accurately.

[1. FEDERATED NAMESPACE RULES - CRITICAL]
DuckDB seamlessly queries across different databases and files. You MUST use the exact "TABLE TO USE" strings provided below in your FROM, JOIN, and UNION clauses. Do not strip catalog prefixes. NEVER hallucinate table names.

[2. MULTI-SOURCE TOPOLOGY: JOINS vs. UNIONS]
- ENRICHMENT (JOIN): You are STRICTLY FORBIDDEN from writing ANY `JOIN` clauses UNLESS the exact relationship is defined in the "CUSTOM JOIN RULES" section. Do not guess relationships based on column names.
- UNIFICATION (UNION): If the user asks for a holistic view of an entity (e.g., "all customers", "total sales history") and the schema context reveals this entity is fragmented across multiple disparate tables (e.g., a database table and a CSV file), you MUST dynamically use `UNION ALL` to combine them vertically. Ensure the selected columns match in data type and relative order across the SELECT statements.

[3. SEMANTIC LAYER COMPLIANCE]
If the user asks for a specific metric (e.g., "Revenue", "Sales", "KPI"), you MUST check the "CRITICAL BUSINESS METRICS" section first. Apply these exact calculations on the specified tables.

[4. GUARDRAILS & REJECTIONS]
- Semantic Validity: If a user asks to calculate an Average, Sum, or mathematical operation on a categorical identifier (e.g., Postal Codes, Phone Numbers, User IDs), set 'is_valid_analytical_request' to FALSE.
- Missing Topology: If the query requires combining data from multiple tables for enrichment but NO explicit join rule exists linking them, you MUST set 'is_valid_analytical_request' to FALSE.
- Conversational Pushback: If rejecting a query, provide a clear explanation in 'conversational_response' in strict business terms. DO NOT mention SQL, DuckDB, catalogs, schemas, or technical jargon.

Chat History:
{chat_history}

Database Schemas:
{schemas}

Semantic Rules & Topology:
{semantics}
"""),
        ("human", "User Request: {question}"),
        ("human", "Previous Error: {error}")
    ])
    
    chain = prompt | llm.with_structured_output(SQLGuardrailOutput)
    chat_history_str = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in state.get("chat_history", [])])
    
    response = chain.invoke({
        "schemas": state.get("schema_context", ""),
        "semantics": state.get("semantic_context", ""),
        "question": state["question"],
        "error": state.get("error_message") or "None",
        "chat_history": chat_history_str
    })

    print("\n" + "-"*20)
    print("AGENT EXECUTION PLAN:")
    if not response.is_valid_analytical_request:
        print("❌ GUARDRAIL TRIGGERED: Request blocked by semantic/topology policy.")
        print(f"Explanation: {response.conversational_response}")
    else:
        print("✅ GUARDRAIL PASSED: Query is logically sound and topology verified.")
        print("GENERATED SQL:\n" + str(response.sql_query))
    print("-"*20 + "\n")
    
    if not response.is_valid_analytical_request:
        return {"error_message": "MATH_REJECTED", "conversational_reply": response.conversational_response}
        
    return {"generated_sql": response.sql_query, "conversational_reply": response.conversational_response, "retries": state.get("retries", 0) + 1}

def validate_and_execute(state: AgentState) -> dict:
    if state.get("error_message") in ["INPUT_REJECTED", "MATH_REJECTED"]:
        return {"results": [], "error_message": state.get("error_message")}
        
    sql = state["generated_sql"]
    ast_error = validate_read_only_ast(sql)
    if ast_error:
        return {"error_message": ast_error}
        
    try:
        session = session_manager.get_session(state["workspace_id"])
        df = session.conn.execute(sql).df()
        return {"results": df.to_dict(orient="records"), "error_message": None}
    except Exception as e:
        return {"error_message": f"Execution Error: {str(e)}"}

def sanitize_error(state: AgentState) -> dict:
    """Final graph node: Translates catastrophic system failures into clean business logic."""
    if not state.get("error_message") or state.get("error_message") in ["INPUT_REJECTED", "MATH_REJECTED"]:
        return {}
        
    logger.warning(f"[NODE: sanitize_error] Intercepting raw backend error: {state['error_message']}")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a customer-facing Data Assistant. An internal system error just occurred in the backend. 
Translate this failure into a polite, single-sentence response for the user.
CRITICAL RULES:
1. NEVER mention SQL, DuckDB, schemas, AST, databases, or LLMs.
2. Do not expose the raw error text.
3. Simply state that you cannot access or join the requested information right now."""),
        ("human", "Raw Technical Error: {error}")
    ])
    
    chain = prompt | llm.with_structured_output(SanitizeErrorOutput)
    response = chain.invoke({"error": state["error_message"]})
    
    return {"conversational_reply": response.friendly_message, "error_message": "SANITIZED_ERROR"}