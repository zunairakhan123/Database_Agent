import time
import os
import logging
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from backend.app.core.semantic_models import Metric
from backend.app.database.semantic_store import semantic_store
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# --- STRICT PYDANTIC WRAPPER ---
class DraftedMetrics(BaseModel):
    drafted_metrics: list[Metric] = Field(description="List of drafted business metrics")

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY2"), 
    model_name="openai/gpt-oss-20b", 
    temperature=0.0
    )

def auto_draft_metrics(workspace_id: str, schema_context_string: str, max_retries: int = 3):
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an Enterprise Data Architect building a Semantic Layer.
Analyze the provided database schema, which represents a curated subset of tables explicitly selected by the user.

Your task is to define robust, production-grade business metrics (KPIs) based ONLY on the provided schema.

CRITICAL RULES:
1. Valid SQL Only: The 'calculation' field must be a valid DuckDB SQL aggregate function (e.g., SUM(amount), COUNT(DISTINCT user_id), AVG(price)).
2. No Hallucinations: Do not reference columns or tables that do not exist in the provided schema context.
3. Domain Agnostic: Infer the industry from the table names and generate standard KPIs for that industry.
4. Base URN format: The 'base_urn' must match the exact table name provided in the schema context.
5. Synonyms Required: Every metric MUST include a 'synonyms' array containing 2 to 3 alternative business terms or phrasing for the metric.
6. Granularity: Provide 3 to 5 highly valuable metrics."""),
        ("human", "User's Selected Schemas:\n{schemas}")
    ])

    # Leverage Groq's native structured output
    chain = prompt | llm.with_structured_output(DraftedMetrics)
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 Auto-drafting metrics via Groq... (Attempt {attempt + 1}/{max_retries})")
            
            # The result is automatically validated and parsed into a DraftedMetrics Pydantic object
            result = chain.invoke({"schemas": schema_context_string})
            
            print("\n" + "*"*50)
            print(" DRAFTED BUSINESS METRICS")
            for m in result.drafted_metrics:
                print(f"\nMetric: {m.name}")
                print(f"  ├─ Calculation: {m.calculation}")
                print(f"  ├─ Base Table:  {m.base_urn}")
                print(f"  └─ Synonyms:    {', '.join(m.synonyms)}")
            print("\n" + "*"*50 + "\n")

            # Persist to SQLite
            for metric in result.drafted_metrics:
                semantic_store.add_metric(workspace_id, metric)
                
            print("✅ Metrics successfully drafted and saved!")
            return {"status": "success", "drafted_metrics": [m.name for m in result.drafted_metrics]}
            
        except Exception as e:
            print(f"⚠️ Auto-draft attempt {attempt + 1} failed: {e}")
            logger.warning(f"Drafting error details: {str(e)}")
            
        if attempt < max_retries - 1:
            time.sleep(1) 
        else:
            print("❌ All auto-draft attempts failed.")
            return {"status": "failed", "error": "Max retries reached due to LLM extraction failures."}