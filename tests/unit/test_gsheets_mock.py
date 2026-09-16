import pytest
from unittest.mock import patch, MagicMock
from backend.app.database.session_manager import WorkspaceSession
from backend.app.database.gsheets_connector import register_sheet_metadata, fetch_live_sheet_jit

@pytest.fixture
def mock_gspread():
    """Mocks gspread to prevent real network calls during testing."""
    with patch("backend.app.database.gsheets_connector.gspread.service_account") as mock_sa:
        mock_client = MagicMock()
        mock_sheet = MagicMock()
        
        # Mock the headers and data returns
        mock_sheet.row_values.return_value = ["id", "name", "sales"]
        mock_sheet.get_all_records.return_value = [
            {"id": 1, "name": "Alice", "sales": 100},
            {"id": 2, "name": "Bob", "sales": 200}
        ]
        
        mock_client.open_by_url.return_value.sheet1 = mock_sheet
        mock_sa.return_value = mock_client
        yield mock_sheet

@pytest.mark.unit
def test_google_sheets_strict_freshness_lifecycle(mock_gspread):
    session = WorkspaceSession("workspace_gsheets")
    url = "https://docs.google.com/spreadsheets/d/mock-id/edit"
    
    # 1. Connection Phase: Verify it ONLY fetches headers, not all data
    res = register_sheet_metadata(session, url, "live_targets", "dummy.json")
    
    assert res["status"] == "success"
    assert res["columns"] == ["id", "name", "sales"]
    assert "live_targets" in session.registered_sheets
    
    # Assert get_all_records() was NEVER called during connection
    mock_gspread.get_all_records.assert_not_called()
    
    # Verify the table doesn't actually exist in DuckDB yet
    with pytest.raises(Exception):
        session.conn.execute("SELECT * FROM live_targets").fetchall()

    # 2. Execution Phase: Trigger the JIT fetch
    fetch_live_sheet_jit(session, "live_targets", "dummy.json")
    
    # Assert the data was finally fetched
    mock_gspread.get_all_records.assert_called_once()
    
    # Verify the table now exists in DuckDB and is queryable
    data = session.conn.execute("SELECT name FROM live_targets WHERE sales = 200").fetchall()
    assert data[0][0] == "Bob"
    
    session.close()