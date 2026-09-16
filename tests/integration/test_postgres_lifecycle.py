import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import text
from backend.app.database.pool_manager import pool_manager
from backend.app.database.session_manager import WorkspaceSession

@pytest.mark.integration
def test_postgres_container_lifecycle_and_pooling():
    with PostgresContainer("postgres:15-alpine") as postgres:
        pg_url_sqla = postgres.get_connection_url()  # Has +psycopg2
        pg_url_duckdb = pg_url_sqla.replace("+psycopg2", "") # Clean URL for DuckDB
        
        # 1. Seed PostgreSQL Database via SQLAlchemy
        engine = pool_manager.get_engine(pg_url_sqla)
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(50));"))
            conn.execute(text("INSERT INTO users (name) VALUES ('Zunaira'), ('Alice');"))
            conn.commit()
            
        # 2. Test Connection Pool Liveness
        assert pool_manager.test_connection(pg_url_sqla) is True
        
        # 3. Test DuckDB Native Federation over Network
        session = WorkspaceSession("workspace_pg")
        # DuckDB gets the clean URL
        session.conn.execute(f"ATTACH '{pg_url_duckdb}' AS pg_remote (TYPE POSTGRES, READ_ONLY);")
        
        res = session.conn.execute("SELECT name FROM pg_remote.public.users ORDER BY id;").fetchall()
        assert res == [('Zunaira',), ('Alice',)]
        
        # 4. Enforce READ_ONLY Security Constraint
        with pytest.raises(Exception):
            session.conn.execute("INSERT INTO pg_remote.public.users (name) VALUES ('Hacker');")
            
        session.close()