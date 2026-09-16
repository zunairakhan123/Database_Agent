import re
from sqlalchemy.engine.url import make_url

IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")

def validate_identifier(name: str) -> str:
    """Validates that table/schema identifiers prevent SQL injection."""
    if not name or not IDENTIFIER_REGEX.match(name):
        raise ValueError(f"Invalid identifier: '{name}'. Must match ^[a-zA-Z_][a-zA-Z0-9_]{{0,62}}$")
    return name

def mask_connection_uri(uri: str) -> str:
    """Safely masks passwords in database connection URIs."""
    try:
        url = make_url(uri)
        return url.render_as_string(hide_password=True)
    except Exception:
        return "invalid-uri-format"