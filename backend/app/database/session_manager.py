import duckdb
import time
import os
from typing import Dict

# Define a central directory to store tenant databases
STORAGE_DIR = "./workspace_storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

class WorkspaceSession:
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        
        # 1. PHYSICAL FILES: Each workspace gets its own isolated file on disk
        self.db_path = os.path.join(STORAGE_DIR, f"{workspace_id}.duckdb")
        self.conn = duckdb.connect(database=self.db_path)
        
        self.last_accessed = time.time()
        self._initialize_extensions()
        self._apply_resource_limits()

    def _initialize_extensions(self):
        # Install both Postgres and MySQL native federation extensions
        self.conn.execute("INSTALL postgres;")
        self.conn.execute("LOAD postgres;")
        self.conn.execute("INSTALL mysql;")
        self.conn.execute("LOAD mysql;")
        self.conn.execute("INSTALL excel;")
        self.conn.execute("LOAD excel;")

    def _apply_resource_limits(self):
        # 2. OOM PREVENTION: Cap memory usage so heavy analytical queries don't crash FastAPI
        self.conn.execute("SET max_memory = '2GB';")
        self.conn.execute("SET preserve_insertion_order = false;")

    def get_cursor(self):
        # 3. CURSOR ISOLATION: Prevents thread locking on concurrent queries
        return self.conn.cursor()

    def touch(self):
        self.last_accessed = time.time()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
        
class WorkspaceSessionManager:
    """Manages isolated, tenant-scoped DuckDB instances with idle eviction."""
    def __init__(self, ttl_seconds: int = 900):
        self._sessions: Dict[str, WorkspaceSession] = {}
        self.ttl_seconds = ttl_seconds

    def get_session(self, workspace_id: str) -> WorkspaceSession:
        self.evict_stale()
        if workspace_id not in self._sessions:
            self._sessions[workspace_id] = WorkspaceSession(workspace_id)
        session = self._sessions[workspace_id]
        session.touch()
        return session

    def evict_session(self, workspace_id: str):
        if workspace_id in self._sessions:
            self._sessions[workspace_id].close()
            del self._sessions[workspace_id]

    def evict_stale(self):
        now = time.time()
        stale_keys = [
            wid for wid, sess in self._sessions.items() 
            if now - sess.last_accessed > self.ttl_seconds
        ]
        for wid in stale_keys:
            self.evict_session(wid)

    def close_all(self):
        for sess in self._sessions.values():
            sess.close()
        self._sessions.clear()

session_manager = WorkspaceSessionManager()