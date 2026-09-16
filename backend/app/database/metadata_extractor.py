import json
import logging
import os
from typing import List, Optional
from click import prompt
from backend.app.core.schema_models import TableEntity, PhysicalSchema, ColumnMetadata, BusinessMetadata
from backend.app.database.session_manager import WorkspaceSession
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

enrichment_llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"), # Replace with your actual key or load from os.getenv
    model_name="openai/gpt-oss-20b", # Swapped for strict JSON determinism
    temperature=0.0 # Zero for deterministic JSON
)

class TableEnrichment(BaseModel):
    table_business_name: str = Field(description="A clean, Title Cased name for the entire table (e.g., 'User Accounts').")
    table_description: str = Field(description="1-2 sentence summary of what this table represents to guide the AI agent.")
    column_business_names: dict[str, str] = Field(description="Dictionary mapping physical column names to clean, Title Cased UI names.")

def extract_schema_entities(session: WorkspaceSession, selected_tables: Optional[List[str]] = None) -> List[TableEntity]:
    logger.info(f"[METADATA EXTRACTOR] Starting extraction for workspace: {session.workspace_id}")
    entities = []
    
    tables_query = """
        SELECT table_catalog, table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog') 
        AND table_schema NOT LIKE 'pg_toast%'
        AND table_type = 'BASE TABLE';
    """
    try:
        tables = session.conn.execute(tables_query).fetchall()
    except Exception as e:
        logger.error(f"[METADATA EXTRACTOR] Failed to query information_schema.tables: {e}")
        return []

    # Map all available tables to help our inference engine
    all_table_names = {t[2]: t[1] for t in tables} # {table_name: schema_name}

    for t_catalog, t_schema, t_name in tables:
        fqn = f"{t_schema}.{t_name}" if t_schema != "main" else t_name
        
        if selected_tables and fqn not in selected_tables:
            continue
            
        col_query = f"""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = '{t_name}' AND table_schema = '{t_schema}';
        """
        raw_cols = session.conn.execute(col_query).fetchall()
        
        pk_columns = []
        fk_mappings = {}
        
        # 1. ATTEMPT PHYSICAL EXTRACTION (Works for native DuckDB tables)
        try:
            constraint_query = f"""
                SELECT constraint_type, constraint_column_names, referenced_table 
                FROM duckdb_constraints() 
                WHERE table_name = '{t_name}' AND schema_name = '{t_schema}';
            """
            constraints = session.conn.execute(constraint_query).fetchall()
            for c_type, c_cols, ref_table in constraints:
                if c_type == "PRIMARY KEY":
                    pk_columns.extend(c_cols)
                elif c_type == "FOREIGN KEY":
                    target_fqn = f"{t_schema}.{ref_table}" if t_schema != "main" else ref_table
                    target_urn = f"urn:workspace:{session.workspace_id}:source:{t_catalog}:table:{target_fqn}"
                    for col in c_cols:
                        fk_mappings[col] = target_urn
        except Exception:
            pass

        # 2. HEURISTIC INFERENCE FALLBACK (Critical for Postgres/MySQL/CSVs)
        # If no explicit FKs were found, intelligently guess based on column names
        if not fk_mappings:
            for c_name, _, _ in raw_cols:
                if c_name.endswith('_id') and c_name != f"{t_name}_id":
                    base_name = c_name[:-3] # e.g., 'customer_id' -> 'customer'
                    
                    # Look for plural or singular table matches (e.g., 'customers' or 'customer')
                    possible_targets = [f"{base_name}s", base_name]
                    for pt in possible_targets:
                        if pt in all_table_names and pt != t_name:
                            target_schema = all_table_names[pt]
                            target_fqn = f"{target_schema}.{pt}" if target_schema != "main" else pt
                            target_urn = f"urn:workspace:{session.workspace_id}:source:{t_catalog}:table:{target_fqn}"
                            fk_mappings[c_name] = target_urn
                            break

        # Check for Primary Keys heuristically if not defined
        if not pk_columns:
            for c_name, _, _ in raw_cols:
                if c_name == "id" or c_name == f"{t_name}_id" or c_name == f"{t_name[:-1]}_id":
                    pk_columns.append(c_name)
                    break

        columns = []
        for c_name, d_type, is_null in raw_cols:
            columns.append(ColumnMetadata(
                name=c_name, 
                data_type=d_type, 
                is_nullable=(is_null == 'YES'),
                is_primary_key=(c_name in pk_columns), 
                foreign_keys=[fk_mappings[c_name]] if c_name in fk_mappings else [],
                description=""
            ))

        print("\n" + "-"*20)
        print(f"EXTRACTED PHYSICAL SCHEMA: {fqn}")
        for col in columns:
            pk_flag = "🔑 [PK]" if col.is_primary_key else ""
            fk_flag = f"🔗 [JOIN -> {col.foreign_keys[0].split(':')[-1]}]" if col.foreign_keys else ""
            print(f"  - {col.name.ljust(20)} | {col.data_type.ljust(10)} {pk_flag} {fk_flag}".strip())
        print("-"*20 + "\n")

        entities.append(TableEntity(
            workspace_id=session.workspace_id,
            source_id=t_catalog,
            physical=PhysicalSchema(schema_name=t_schema, table_name=t_name, columns=columns),
            business=BusinessMetadata()
        ))

    return entities

def enrich_schema_descriptions(entities: List[TableEntity]) -> List[TableEntity]:
    """Uses Groq's native structured output to guarantee schema compliance."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a Data Architect. Generate a clean UI 'table_business_name', a 'table_description' for AI context, and clean 'column_business_names' for the provided physical schema."),
        ("human", "Table: {table_name}\nColumns: {columns}")
    ])

    # Restore the strict Pydantic enforcement
    chain = prompt | enrichment_llm.with_structured_output(TableEnrichment)

    for entity in entities:
        # Skip if already enriched
        if entity.business.business_name:
            continue
            
        logger.info(f"[ENRICHMENT] Auto-generating UI names and description for {entity.physical.table_name}")
        try:
            cols_str = ", ".join([c.name for c in entity.physical.columns])
            
            # The result is now guaranteed to be a TableEnrichment Pydantic object
            result = chain.invoke({
                "table_name": entity.physical.table_name,
                "columns": cols_str
            })
            
            # Restore the rich terminal logging
            print("\n" + "="*50)
            print(f"✨ ENRICHMENT FOR: {entity.physical.table_name}")
            print(f"Table Business Name: {result.table_business_name}")
            print(f"Table Description:   {result.table_description}")
            print("Columns:")
            for p_col, b_name in result.column_business_names.items():
                print(f"  - {p_col.ljust(15)} -> {b_name}")
            print("="*50 + "\n")

            # Apply the data
            entity.business.business_name = result.table_business_name
            entity.business.llm_generated_description = result.table_description
            
            for col in entity.physical.columns:
                if col.name in result.column_business_names:
                    col.business_name = result.column_business_names[col.name]
                    
        except Exception as e:
            logger.warning(f"[ENRICHMENT] Failed for {entity.physical.table_name}: {e}")
            
    return entities