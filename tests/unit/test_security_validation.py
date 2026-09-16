import pytest
from backend.app.core.security import validate_identifier, mask_connection_uri

@pytest.mark.unit
def test_valid_identifiers():
    assert validate_identifier("valid_table") == "valid_table"
    assert validate_identifier("_hidden_schema") == "_hidden_schema"
    assert validate_identifier("sales_2026_q1") == "sales_2026_q1"

@pytest.mark.unit
@pytest.mark.parametrize("malicious_input", [
    "table; DROP TABLE users; --",
    "table name with spaces",
    "123_starts_with_number",
    "table--comment",
    "user$schema",
    "a" * 64 # Exceeds 63-byte max identifier length
])
def test_sql_injection_identifiers_rejected(malicious_input):
    with pytest.raises(ValueError, match="Invalid identifier"):
        validate_identifier(malicious_input)

@pytest.mark.unit
def test_mask_connection_uri():
    # Use %40 for the @ symbol in the password
    uri = "postgresql://db_user:s3cr3t_p%40ssw0rd!@10.0.0.1:5432/finance"
    masked = mask_connection_uri(uri)
    assert "s3cr3t_p%40ssw0rd!" not in masked
    assert "db_user:***@10.0.0.1:5432/finance" in masked