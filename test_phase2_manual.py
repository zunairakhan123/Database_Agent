from backend.app.database.session_manager import WorkspaceSession
from backend.app.database.metadata_extractor import extract_schema_entities
from backend.app.database.metadata_store import metadata_store

def run_test():
    workspace_id = "test_workspace_alpha"
    source_id = "pg_local"
    
    # 1. Initialize an in-memory session and create dummy tables
    print("[1] Initializing DuckDB workspace session...")
    session = WorkspaceSession(workspace_id)
    
    # Create sample tables with constraints
    session.conn.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            email VARCHAR NOT NULL,
            signup_date DATE
        );
    """)
    session.conn.execute("""
        CREATE TABLE transactions (
            tx_id VARCHAR PRIMARY KEY,
            customer_id INTEGER,
            amount DECIMAL(10, 2),
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );
    """)
    print("    Created 'customers' and 'transactions' tables in DuckDB.")

    # 2. Extract schema entities
    print("\n[2] Extracting schema entities via duckdb_constraints()...")
    entities = extract_schema_entities(session, source_id=source_id)
    for entity in entities:
        print(f"    URN: {entity.urn}")
        print(f"    Fingerprint: {entity.fingerprint[:16]}...")
        print(f"    Embedding Payload: {entity.to_embedding_string()}")

    # 3. First Sync (Should insert both)
    print("\n[3] Running 1st Sync (Indexing into ChromaDB & SQLite)...")
    metadata_store.sync_entities_incrementally(entities)
    print("    Synced successfully.")

    # 4. Second Sync with no changes (Should skip both)
    print("\n[4] Running 2nd Sync with unchanged schemas (Testing diff skipping)...")
    metadata_store.sync_entities_incrementally(entities)
    print("    Second sync completed (unchanged entities skipped).")

    # 5. Test Vector Search
    print("\n[5] Testing Vector Search...")
    queries = [
        "Where are billing and payment amounts stored?",
        "User contact info and emails"
    ]
    for q in queries:
        matched_urns = metadata_store.hybrid_search(workspace_id=workspace_id, query=q, top_k=1)
        print(f"    Query: '{q}' -> Matched URN: {matched_urns}")

    session.close()

if __name__ == "__main__":
    run_test()