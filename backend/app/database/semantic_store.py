import sqlite3
import json
from typing import List
from backend.app.core.semantic_models import Metric, JoinRule

class SemanticStore:
    def __init__(self):
        self.sqlite = sqlite3.connect("operational_metadata.db", check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.sqlite.execute("""
            CREATE TABLE IF NOT EXISTS business_metrics (
                workspace_id TEXT, 
                name TEXT, 
                base_urn TEXT, 
                payload JSON,
                UNIQUE(workspace_id, name)
            )
        """)
        # Join rules table
        self.sqlite.execute("""
            CREATE TABLE IF NOT EXISTS join_rules (
                workspace_id TEXT, source_urn TEXT, target_urn TEXT, payload JSON,
                UNIQUE(workspace_id, source_urn, target_urn)
            )
        """)
        self.sqlite.commit()

    def add_metric(self, workspace_id: str, metric: Metric):
        """Saves a business definition (from User or Auto-Drafter)."""
        self.sqlite.execute(
            """INSERT OR REPLACE INTO business_metrics 
               (workspace_id, name, base_urn, payload) VALUES (?, ?, ?, ?)""",
            (workspace_id, metric.name, metric.base_urn, metric.model_dump_json())
        )
        self.sqlite.commit()

    def get_metrics(self, workspace_id: str) -> List[Metric]:
        """Retrieves all metrics for injection into LangGraph."""
        cursor = self.sqlite.execute(
            "SELECT payload FROM business_metrics WHERE workspace_id = ?", 
            (workspace_id,)
        )
        return [Metric.model_validate_json(row[0]) for row in cursor.fetchall()]

    def add_join_rule(self, workspace_id: str, rule: JoinRule):
        """Saves a manual frontend ERD connection."""
        self.sqlite.execute(
            """INSERT OR REPLACE INTO join_rules 
               (workspace_id, source_urn, target_urn, payload) VALUES (?, ?, ?, ?)""",
            (workspace_id, rule.source_urn, rule.target_urn, rule.model_dump_json())
        )
        self.sqlite.commit()

    def get_join_rules(self, workspace_id: str) -> List[JoinRule]:
        cursor = self.sqlite.execute(
            "SELECT payload FROM join_rules WHERE workspace_id = ?", (workspace_id,)
        )
        return [JoinRule.model_validate_json(row[0]) for row in cursor.fetchall()]

    def delete_join_rule(self, workspace_id: str, source_urn: str, target_urn: str):
        """Removes a manual join rule."""
        self.sqlite.execute(
            "DELETE FROM join_rules WHERE workspace_id = ? AND source_urn = ? AND target_urn = ?", 
            (workspace_id, source_urn, target_urn)
        )
        self.sqlite.commit()

semantic_store = SemanticStore()