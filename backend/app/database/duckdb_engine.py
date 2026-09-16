import duckdb
import pandas as pd
import os

class DuckDBFederationEngine:
    def __init__(self):
        # Initialize an in-memory DuckDB connection
        self.conn = duckdb.connect(database=':memory:')
        
        # Install and load required extensions
        self.conn.execute("INSTALL postgres;")
        self.conn.execute("LOAD postgres;")
        self.conn.execute("INSTALL excel;")
        self.conn.execute("LOAD excel;")
        
    def attach_postgres(self, connection_name: str, connection_string: str):
        """
        Attaches a PostgreSQL database directly over the network.
        Enforces READ_ONLY to prevent the LLM from mutating data.
        """
        try:
            # e.g., connection_string = 'postgresql://user:password@host:5432/dbname'
            query = f"ATTACH '{connection_string}' AS {connection_name} (TYPE POSTGRES, READ_ONLY);"
            self.conn.execute(query)
            return {"status": "success", "message": f"Postgres attached as {connection_name}"}
        except Exception as e:
            raise Exception(f"Failed to attach Postgres: {str(e)}")

    def load_local_file(self, table_name: str, file_path: str, file_type: str):
        """
        Loads CSV or Excel files natively into DuckDB.
        """
        try:
            if file_type == 'csv':
                self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{file_path}');")
            elif file_type == 'xlsx':
                # read_xlsx requires the excel extension
                self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_xlsx('{file_path}');")
            return {"status": "success", "message": f"File loaded into table {table_name}"}
        except Exception as e:
            raise Exception(f"Failed to load file: {str(e)}")

    def register_dataframe(self, table_name: str, df: pd.DataFrame):
        """
        Registers an in-memory Pandas DataFrame as a queryable DuckDB table.
        This is used for Google Sheets and Generic SQL databases.
        """
        try:
            self.conn.register(table_name, df)
            return {"status": "success", "message": f"DataFrame registered as {table_name}"}
        except Exception as e:
            raise Exception(f"Failed to register dataframe: {str(e)}")

    def get_available_tables(self):
        """Returns all currently connected tables and their source schemas."""
        result = self.conn.execute("SELECT table_catalog, table_schema, table_name FROM information_schema.tables;").fetchall()
        return [{"database": r[0], "schema": r[1], "table": r[2]} for r in result]

# Create a global instance to be used across FastAPI routes
db_engine = DuckDBFederationEngine()