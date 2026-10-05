import hashlib
import json
from typing import List, Optional
from pydantic import BaseModel, Field

class ColumnMetadata(BaseModel):
    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False
    foreign_keys: List[str] = Field(default_factory=list) # List of Target URNs

    # --- NEW: UI Friendly Name ---
    business_name: Optional[str] = None

class PhysicalSchema(BaseModel):
    schema_name: str
    table_name: str
    columns: List[ColumnMetadata]
    indexes: List[str] = Field(default_factory=list)

class BusinessMetadata(BaseModel):
    deterministic_description: Optional[str] = None
    llm_generated_description: Optional[str] = None
    user_description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    # --- NEW: UI Friendly Name ---
    business_name: Optional[str] = None

class TableEntity(BaseModel):
    workspace_id: str
    source_id: str
    physical: PhysicalSchema
    business: BusinessMetadata
    
    @property
    def urn(self) -> str:
        """Globally unique identifier for this table."""
        return f"urn:workspace:{self.workspace_id}:source:{self.source_id}:table:{self.physical.schema_name}.{self.physical.table_name}"
    
    @property
    def fingerprint(self) -> str:
        """SHA-256 hash of the physical schema for incremental diffing."""
        # We only hash the physical schema. Business descriptions changing shouldn't trigger expensive re-embeddings.
        canonical_json = self.physical.model_dump_json()
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        
    def to_embedding_string(self) -> str:
        """Build semantic retrieval text; SQL generation still receives physical schema names."""
        
        cols = []
        for c in self.physical.columns:
            column_label = f" ({c.business_name})" if c.business_name else ""
            cols.append(f"{c.name}{column_label} ({c.data_type})")
        
        table_desc = (
            self.business.user_description
            or self.business.deterministic_description
            or self.business.llm_generated_description
            or "No description provided."
        )
        table_name = self.physical.table_name
        if self.business.business_name:
            table_name = f"{table_name} ({self.business.business_name})"

        return f"Table: {self.physical.schema_name}.{table_name}. Description: {table_desc}. Columns: {', '.join(cols)}"

    