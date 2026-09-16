import os
import pytest
import pandas as pd
import openpyxl
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session_manager import session_manager
from backend.app.database.pool_manager import pool_manager

@pytest.fixture(autouse=True)
def clean_system_state():
    """Ensures clean state across test boundaries."""
    yield
    session_manager.close_all()
    pool_manager.dispose_all()

@pytest.fixture
def api_client():
    """Provides a fresh FastAPI test client."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def sample_csv(tmp_path):
    """Generates a verified CSV test file."""
    file_path = tmp_path / "valid_data.csv"
    df = pd.DataFrame({
        "order_id": [101, 102, 103],
        "customer": ["Alice", "Bob", "Charlie"],
        "amount": [45.50, 120.00, 99.99]
    })
    df.to_csv(file_path, index=False)
    return str(file_path)

@pytest.fixture
def sample_multisheet_excel(tmp_path):
    """Generates a multi-sheet Excel file representing Orders and Returns."""
    file_path = tmp_path / "enterprise_data.xlsx"
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        pd.DataFrame({
            "order_id": [101, 102],
            "sales": [500, 300]
        }).to_excel(writer, sheet_name="Orders", index=False)
        
        pd.DataFrame({
            "return_id": [9001],
            "order_id": [102],
            "reason": ["Damaged"]
        }).to_excel(writer, sheet_name="Returns", index=False)
        
        # Empty sheet test case
        pd.DataFrame().to_excel(writer, sheet_name="Metadata", index=False)
    return str(file_path)