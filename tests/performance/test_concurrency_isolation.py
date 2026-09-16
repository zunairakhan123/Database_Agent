import pytest
import concurrent.futures
from backend.app.database.session_manager import session_manager
import pandas as pd

@pytest.mark.performance
def test_high_concurrency_tenant_isolation():
    """
    Spins up 20 concurrent threads creating different workspaces,
    ingesting data, and verifying zero memory contamination.
    """
    def worker_task(tenant_id: int):
        workspace_id = f"workspace_{tenant_id}"
        session = session_manager.get_session(workspace_id)
        
        # Register a unique value per tenant
        df = pd.DataFrame({"tenant_val": [tenant_id]})
        session.conn.register("tenant_data", df)
        
        # Verify read integrity
        res = session.conn.execute("SELECT tenant_val FROM tenant_data").fetchone()
        return res[0] == tenant_id

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_task, i) for i in range(20)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
    assert all(results) is True
    assert len(session_manager._sessions) == 20
    session_manager.close_all()