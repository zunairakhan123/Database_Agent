from backend.app.database.session_manager import session_manager
from backend.app.database.metadata_extractor import extract_schema_entities
from backend.app.database.metadata_store import metadata_store
from backend.app.agent.graph import agent_app

def run_agent_test():
    workspace_id = "test_agent_ws"
    
    print("[1] Provisioning test DuckDB database...")
    session = session_manager.get_session(workspace_id)
    session.conn.execute("""
        CREATE TABLE departments (
            dept_id INT PRIMARY KEY,
            dept_name VARCHAR NOT NULL
        );
        CREATE TABLE employees (
            emp_id INT PRIMARY KEY,
            name VARCHAR NOT NULL,
            salary DECIMAL(10, 2),
            dept_id INT,
            FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
        );
        INSERT INTO departments VALUES (1, 'Engineering'), (2, 'Sales');
        INSERT INTO employees VALUES 
            (101, 'Zunaira', 120000, 1),
            (102, 'Alice', 95000, 1),
            (103, 'Bob', 80000, 2);
    """)

    print("[2] Indexing schema metadata into ChromaDB & SQLite...")
    entities = extract_schema_entities(session, source_id="internal")
    metadata_store.sync_entities_incrementally(entities)

    # 3. Invoke LangGraph Agent
    question = "List each department name along with its average employee salary."
    print(f"\n[3] Running Agent with question: '{question}'...")
    
    initial_state = {
        "workspace_id": workspace_id,
        "question": question,
        "retrieved_urns": [],
        "schema_context": "",
        "semantic_context": "",
        "generated_sql": None,
        "error_message": None,
        "retries": 0,
        "results": None
    }
    
    final_state = agent_app.invoke(initial_state)

    print("\n--- Execution Results ---")
    print(f"Generated SQL:\n{final_state.get('generated_sql')}")
    print(f"Retries needed: {final_state.get('retries')}")
    print(f"Error state: {final_state.get('error_message')}")
    print(f"Query Results:\n{final_state.get('results')}")

if __name__ == "__main__":
    run_agent_test()