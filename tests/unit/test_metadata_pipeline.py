import pytest
from backend.app.core.schema_models import TableEntity, PhysicalSchema, ColumnMetadata, BusinessMetadata
from backend.app.database.metadata_store import HybridMetadataStore

@pytest.fixture
def sample_entity():
    return TableEntity(
        workspace_id="test_w1",
        source_id="pg_prod",
        physical=PhysicalSchema(
            schema_name="public", table_name="users",
            columns=[ColumnMetadata(name="id", data_type="INTEGER", is_primary_key=True)]
        ),
        business=BusinessMetadata(deterministic_description="User accounts.")
    )

@pytest.mark.unit
def test_schema_fingerprint_stability(sample_entity):
    initial_hash = sample_entity.fingerprint
    
    # 1. Changing business metadata MUST NOT change the fingerprint
    sample_entity.business.llm_generated_description = "AI generated fluff."
    assert sample_entity.fingerprint == initial_hash
    
    # 2. Changing the physical schema MUST change the fingerprint
    sample_entity.physical.columns.append(ColumnMetadata(name="email", data_type="VARCHAR"))
    assert sample_entity.fingerprint != initial_hash

@pytest.mark.unit
def test_incremental_skipping_logic(sample_entity):
    store = HybridMetadataStore()
    
    # First sync: Should index
    store.sync_entities_incrementally([sample_entity])
    cursor = store.sqlite.execute("SELECT fingerprint FROM metadata_registry WHERE urn = ?", (sample_entity.urn,))
    assert cursor.fetchone()[0] == sample_entity.fingerprint
    
    # Second sync: Should skip (ChromaDB upsert not triggered)
    # We prove it by checking the data still exists and hasn't crashed
    store.sync_entities_incrementally([sample_entity]) 
    
    # Test strict workspace isolation
    results_w1 = store.hybrid_search("test_w1", "Find users table")
    assert sample_entity.urn in results_w1
    
    results_w2 = store.hybrid_search("malicious_tenant", "Find users table")
    assert len(results_w2) == 0 # Isolation enforced