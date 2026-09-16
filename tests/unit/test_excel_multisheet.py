import pytest
import openpyxl
import pandas as pd
from backend.app.database.session_manager import WorkspaceSession
from backend.app.core.security import validate_identifier

@pytest.mark.unit
def test_multisheet_excel_ingestion(sample_multisheet_excel):
    session = WorkspaceSession("workspace_excel")
    wb = openpyxl.load_workbook(sample_multisheet_excel, read_only=True)
    registered_tables = []
    
    try:
        for sheet_name in wb.sheetnames:
            df = pd.read_excel(sample_multisheet_excel, sheet_name=sheet_name)
            if df.empty:
                continue # Gracefully ignore empty sheets
            
            clean_name = validate_identifier(f"excel_{sheet_name.lower()}")
            session.conn.register(clean_name, df)
            registered_tables.append(clean_name)
    finally:
        wb.close() # Ensure file handle is closed immediately
        
    assert "excel_orders" in registered_tables
    assert "excel_returns" in registered_tables
    assert "excel_metadata" not in registered_tables # Was empty
    
    # Verify relations can be joined in DuckDB
    join_res = session.conn.execute("""
        SELECT o.order_id, r.reason 
        FROM excel_orders o 
        JOIN excel_returns r ON o.order_id = r.order_id
    """).fetchall()
    
    assert len(join_res) == 1
    assert join_res[0] == (102, "Damaged")
    session.close()