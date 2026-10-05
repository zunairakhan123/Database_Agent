import sqlite3

import pytest

from backend.app.api import metadata as metadata_api
from backend.app.core.schema_models import (
    BusinessMetadata,
    ColumnMetadata,
    PhysicalSchema,
    TableEntity,
)


class InMemoryMetadataStore:
    def __init__(self, entity: TableEntity):
        self.sqlite = sqlite3.connect(":memory:", check_same_thread=False)
        self.sqlite.execute(
            "CREATE TABLE metadata_registry (urn TEXT PRIMARY KEY, workspace_id TEXT, payload JSON)"
        )
        self.sqlite.execute(
            "INSERT INTO metadata_registry VALUES (?, ?, ?)",
            (entity.urn, entity.workspace_id, entity.model_dump_json()),
        )
        self.sqlite.commit()
        self.reindexed_entity = None

    def reindex_entity(self, entity: TableEntity):
        self.reindexed_entity = entity
        self.sqlite.execute(
            "REPLACE INTO metadata_registry VALUES (?, ?, ?)",
            (entity.urn, entity.workspace_id, entity.model_dump_json()),
        )
        self.sqlite.commit()


@pytest.mark.api
def test_reindex_saves_edits_and_returns_them(api_client, monkeypatch):
    entity = TableEntity(
        workspace_id="metadata_reindex_test",
        source_id="main",
        physical=PhysicalSchema(
            schema_name="main",
            table_name="customers",
            columns=[
                ColumnMetadata(name="customer_id", data_type="INTEGER"),
                ColumnMetadata(name="email", data_type="VARCHAR"),
            ],
        ),
        business=BusinessMetadata(
            business_name="Customers",
            llm_generated_description="People who placed orders.",
        ),
    )
    store = InMemoryMetadataStore(entity)
    monkeypatch.setattr(metadata_api, "metadata_store", store)

    response = api_client.post(
        "/api/v1/metadata/reindex",
        headers={"X-Workspace-ID": entity.workspace_id},
        json={
            "urn": entity.urn,
            "business_name": "Customer Directory",
            "description": "A directory of active customer accounts.",
            "columns": [
                {"name": "customer_id", "business_name": "Customer Number"},
                {"name": "email", "business_name": "Email Address"},
            ],
        },
    )

    assert response.status_code == 200
    assert store.reindexed_entity is not None
    assert store.reindexed_entity.business.business_name == "Customer Directory"
    assert store.reindexed_entity.business.user_description == "A directory of active customer accounts."
    assert store.reindexed_entity.physical.columns[0].business_name == "Customer Number"

    loaded = api_client.get(
        "/api/v1/metadata/entities",
        headers={"X-Workspace-ID": entity.workspace_id},
        params={"table_name": "customers"},
    )
    assert loaded.status_code == 200
    result = loaded.json()["entities"][0]
    assert result["business"]["business_name"] == "Customer Directory"
    assert result["business"]["user_description"] == "A directory of active customer accounts."


@pytest.mark.api
def test_reindex_rejects_columns_not_matching_table(api_client, monkeypatch):
    entity = TableEntity(
        workspace_id="metadata_reindex_invalid_test",
        source_id="main",
        physical=PhysicalSchema(
            schema_name="main",
            table_name="customers",
            columns=[ColumnMetadata(name="customer_id", data_type="INTEGER")],
        ),
        business=BusinessMetadata(),
    )
    store = InMemoryMetadataStore(entity)
    monkeypatch.setattr(metadata_api, "metadata_store", store)

    response = api_client.post(
        "/api/v1/metadata/reindex",
        headers={"X-Workspace-ID": entity.workspace_id},
        json={
            "urn": entity.urn,
            "business_name": "Customers",
            "description": "Customer accounts.",
            "columns": [{"name": "missing_column", "business_name": "Wrong"}],
        },
    )

    assert response.status_code == 422
    assert store.reindexed_entity is None
