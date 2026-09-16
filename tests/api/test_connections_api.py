import pytest
from backend.app.core.security import mask_connection_uri

@pytest.mark.api
def test_upload_file_isolation_and_discovery(api_client, sample_csv):
    with open(sample_csv, "rb") as f:
        resp1 = api_client.post(
            "/api/v1/connect/file",
            headers={"X-Workspace-ID": "tenant_1"},
            data={"table_name": "orders"},
            files={"file": ("sample.csv", f, "text/csv")}
        )
    assert resp1.status_code == 200
    
    tables_w1 = api_client.get("/api/v1/tables", headers={"X-Workspace-ID": "tenant_1"}).json()
    assert "orders" in tables_w1["tables"]  # Fixed: Our API now returns a flat list of strings
    
    tables_w2 = api_client.get("/api/v1/tables", headers={"X-Workspace-ID": "tenant_2"}).json()
    assert "orders" not in tables_w2["tables"]

@pytest.mark.api
def test_invalid_table_name_rejected_by_api(api_client, sample_csv):
    with open(sample_csv, "rb") as f:
        resp = api_client.post(
            "/api/v1/connect/file",
            headers={"X-Workspace-ID": "tenant_1"},
            data={"table_name": "orders; DROP TABLE audit;"},
            files={"file": ("sample.csv", f, "text/csv")}
        )
    assert resp.status_code == 422 
    assert "Invalid identifier" in resp.json()["detail"]

@pytest.mark.api
def test_credential_masking_on_failed_connection(api_client):
    secret_url = "postgresql://super_admin:super_secret_password@127.0.0.1:5432/nonexistent_db"
    resp = api_client.post(
        "/api/v1/connect/database",  # Fixed: Point to the updated route
        headers={"X-Workspace-ID": "tenant_1"},
        data={"db_type": "postgres", "connection_name": "prod_db", "connection_url": secret_url}
    )
    assert resp.status_code == 400
    assert "super_secret_password" not in resp.text
    assert "super_admin:***@127.0.0.1:5432/nonexistent_db" in resp.text