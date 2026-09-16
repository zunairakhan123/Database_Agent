import pytest
import pandas as pd
from backend.app.database.session_manager import WorkspaceSession
from backend.app.core.security import validate_identifier

@pytest.mark.unit
def test_csv_ingestion_and_query(sample_csv):
    session = WorkspaceSession("workspace_test")
    table_name = validate_identifier("orders_csv")
    
    # Ingest CSV into isolated DuckDB session
    session.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{sample_csv}')")
    
    result = session.conn.execute(f"SELECT COUNT(*), SUM(amount) FROM {table_name}").fetchall()
    assert result[0][0] == 3
    assert round(result[0][1], 2) == 265.49
    session.close()

@pytest.mark.unit
def test_dataframe_registration():
    session = WorkspaceSession("workspace_df")
    df = pd.DataFrame({"id": [1, 2], "metric": [10.5, 20.5]})
    
    # Register Pandas DataFrame
    session.conn.register("metrics_view", df)
    
    res = session.conn.execute("SELECT AVG(metric) FROM metrics_view").fetchone()
    assert res[0] == 15.5
    session.close()

@pytest.mark.unit
def test_empty_dataset_handling(tmp_path):
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("") # 0 bytes file
    
    session = WorkspaceSession("workspace_empty")
    # DuckDB will successfully create an empty table
    session.conn.execute(f"CREATE TABLE empty_table AS SELECT * FROM read_csv_auto('{str(empty_csv)}')")
    
    # Assert there are 0 rows
    res = session.conn.execute("SELECT COUNT(*) FROM empty_table").fetchone()
    assert res[0] == 0
    session.close()