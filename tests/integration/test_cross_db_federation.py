import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.mysql import MySqlContainer
from sqlalchemy import text
import pandas as pd
from backend.app.database.pool_manager import pool_manager
from backend.app.database.session_manager import WorkspaceSession

@pytest.mark.integration
def test_full_cross_database_join(sample_csv):
    """
    Executes a 3-way federated join:
    PostgreSQL (Users) + MySQL (Inventory) + DuckDB (CSV Orders)
    """
    with PostgresContainer("postgres:15-alpine") as pg, MySqlContainer("mysql:8.0") as mysql:
        
        pg_url_sqla = pg.get_connection_url()
        pg_url_duckdb = pg_url_sqla.replace("+psycopg2", "")
        
        mysql_url_sqla = mysql.get_connection_url().replace("mysql://", "mysql+pymysql://")
        # DuckDB needs the native mysql:// prefix
        mysql_url_duckdb = mysql.get_connection_url()

        # Seed Postgres
        pg_engine = pool_manager.get_engine(pg_url_sqla)
        with pg_engine.connect() as conn:
            conn.execute(text("CREATE TABLE users (user_id INT PRIMARY KEY, username VARCHAR(50));"))
            conn.execute(text("INSERT INTO users VALUES (1, 'Alice');"))
            conn.commit()
            
        # Seed MySQL
        mysql_engine = pool_manager.get_engine(mysql_url_sqla)
        with mysql_engine.connect() as conn:
            conn.execute(text("CREATE TABLE products (product_id INT PRIMARY KEY, sku VARCHAR(20));"))
            conn.execute(text("INSERT INTO products VALUES (10, 'WIDGET-A');"))
            conn.commit()

        # Orchestrate in Workspace DuckDB
        session = WorkspaceSession("cross_db_workspace")
        
        # 1. Attach Postgres (DuckDB)
        session.conn.execute(f"ATTACH '{pg_url_duckdb}' AS pg_db (TYPE POSTGRES, READ_ONLY);")
        
        # 2. Attach MySQL (DuckDB natively!)
        session.conn.execute(f"ATTACH '{mysql_url_duckdb}' AS mysql_products (TYPE MYSQL, READ_ONLY);")
        
        # 3. Load Local CSV (simulate order)
        df_orders = pd.DataFrame({"order_id": [1], "user_id": [1], "product_id": [10]})
        session.conn.register("orders_local", df_orders)
        
        # 4. Federated 3-way Join!
        query = """
            SELECT o.order_id, u.username, p.sku
            FROM orders_local o
            JOIN pg_db.public.users u ON o.user_id = u.user_id
            JOIN mysql_products.products p ON o.product_id = p.product_id
        """
        result = session.conn.execute(query).fetchall()
        assert result == [(1, 'Alice', 'WIDGET-A')]
        session.close()