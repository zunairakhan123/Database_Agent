from typing import List, Optional
from pydantic import BaseModel, Field

class JoinRule(BaseModel):
    """Explicitly defines how two URNs connect (overrides or augments DB foreign keys)."""
    source_urn: str
    target_urn: str
    condition: str = ""
    join_type: str = "LEFT" # INNER, LEFT, FULL
    cardinality: str = "1:N" # 1:1, 1:N, N:M
    is_user_defined: bool = True

class Metric(BaseModel):
    """Business definitions that prevent LLM math hallucinations."""
    name: str                           # e.g., "Net Revenue"
# ✅ FIX: Make synonyms optional and default to an empty list if the LLM skips it
    synonyms: List[str] = Field(default_factory=list, description="Alternative names or phrases for this metric")
    base_urn: str                       # e.g., "urn:...:table:public.orders"
    calculation: str                    # e.g., "SUM(amount) - SUM(refunds)"
    filters: Optional[str] = None       # e.g., "status = 'completed'"

class DataGovernanceRule(BaseModel):
    """Enforces row-level/column-level security before the SQL executes."""
    target_urn: str
    restricted_columns: List[str]       # e.g., ["ssn", "password_hash"]
    masking_policy: Optional[str] = None # e.g., "regexp_replace(email, '(?<=.).(?=.*@)', '*')"

class SemanticLayer(BaseModel):
    """The master business brain for a specific workspace."""
    workspace_id: str
    join_rules: List[JoinRule]
    metrics: List[Metric]
    governance_rules: List[DataGovernanceRule]