import sqlglot
from sqlglot import exp
from typing import Optional

def validate_read_only_ast(sql: str) -> Optional[str]:
    """
    Parses SQL into an AST. Returns an error string if invalid, else None.
    Blocks all destructive operations mathematically.
    """
    if not sql or not sql.strip():
        return "Model generated an empty query. Please provide a valid SELECT statement."

    try:
        parsed_statements = sqlglot.parse(sql.strip(), read="duckdb")
        
        # Guard against None entries produced by empty comments or whitespace
        statements = [stmt for stmt in parsed_statements if stmt is not None]
        if not statements:
            return "No valid SQL statements found."
            
        if len(statements) > 1:
            return "Multiple statements detected. Only a single query is allowed."
            
        ast = statements[0]
        
        # 1. Root MUST be a read-only query (SELECT, UNION, INTERSECT, EXCEPT)
        if not isinstance(ast, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
            return f"Security Violation: Query must be a SELECT or UNION statement. Found {type(ast).__name__}."
            
        # 2. Walk the tree to ensure no destructive nodes exist
        for node in ast.walk():
            if isinstance(node, (exp.Drop, exp.Delete, exp.Update, exp.Insert, exp.Alter, exp.Command)):
                return "Security Violation: Destructive operations are strictly prohibited."
                
        return None  # SQL is safe
        
    except sqlglot.errors.ParseError as e:
        return f"SQL Syntax Error during AST parsing: {str(e)}"
    except Exception as e:
        return f"Unexpected AST validation error: {str(e)}"