from sqlalchemy import create_engine
from typing import Dict
import sqlalchemy
from backend.app.core.security import mask_connection_uri

class ConnectionPoolManager:
    """Maintains connection pools for PostgreSQL and MySQL with pre-ping validation."""
    def __init__(self):
        self._engines: Dict[str, any] = {}

    def get_engine(self, connection_uri: str):
        if connection_uri not in self._engines:
            self._engines[connection_uri] = create_engine(
                connection_uri,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,      # Tests connection liveness before checkout
                pool_recycle=1800,       # Prevents stale sockets
                pool_timeout=5,          # Fails fast on connection delays
                connect_args={"connect_timeout": 5} if "postgres" in connection_uri else {}
            )
        return self._engines[connection_uri]

    def test_connection(self, connection_uri: str) -> bool:
        masked = mask_connection_uri(connection_uri)
        try:
            engine = self.get_engine(connection_uri)
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            return True
        except Exception as e:
            raise ConnectionError(f"Connection test failed for {masked}")

    def dispose_all(self):
        for engine in self._engines.values():
            engine.dispose()
        self._engines.clear()

pool_manager = ConnectionPoolManager()