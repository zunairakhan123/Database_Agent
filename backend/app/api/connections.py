from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header
from backend.app.database.session_manager import session_manager
from backend.app.database.pool_manager import pool_manager
from backend.app.core.security import mask_connection_uri, validate_identifier
import tempfile
import os
import csv
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pandas as pd

router = APIRouter()


def clean_spreadsheet_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Finds the actual data table inside a messy dashboard-style spreadsheet."""
    # Drop columns and rows that are 100% empty
    df = df.dropna(axis=1, how='all').dropna(axis=0, how='all')
    df = df.reset_index(drop=True)
    
    if df.empty:
        return df

    # Search the first 20 rows to find the most "dense" row (likely the headers)
    max_non_nulls = 0
    header_idx = 0
    
    for idx, row in df.head(20).iterrows():
        non_null_count = row.count()
        if non_null_count > max_non_nulls:
            max_non_nulls = non_null_count
            header_idx = idx

    # Set the densest row as the header and slice the dataframe
    df.columns = df.iloc[header_idx]
    df = df.iloc[header_idx + 1:].reset_index(drop=True)
    
    # Clean up the column names for SQL compatibility
    df.columns = [str(c).replace('\n', ' ').strip().replace(' ', '_').lower() for c in df.columns]
    
    return df

@router.post("/connect/database")
def connect_relational_db(
    workspace_id: str = Header(alias="X-Workspace-ID"),
    db_type: str = Form(...),
    connection_name: str = Form(...), 
    connection_url: str = Form(...)
):
    try:
        clean_name = validate_identifier(connection_name)
        session = session_manager.get_session(workspace_id)
        
        pool_manager.test_connection(connection_url)

        if db_type.lower() == "postgres":
            session.conn.execute(f"ATTACH '{connection_url}' AS {clean_name} (TYPE POSTGRES, READ_ONLY);")
        elif db_type.lower() == "mysql":
            session.conn.execute(f"ATTACH '{connection_url}' AS {clean_name} (TYPE MYSQL, READ_ONLY);")
        else:
            raise ValueError("Unsupported database type.")
            
        return {"status": "success", "message": f"{db_type} attached securely."}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed for {mask_connection_uri(connection_url)}")

@router.post("/connect/file")
async def connect_local_file(
    workspace_id: str = Header(alias="X-Workspace-ID"),
    table_name: str = Form(...), 
    file: UploadFile = File(...)
):
    tmp_path = None
    try:
        clean_name = validate_identifier(table_name)
        session = session_manager.get_session(workspace_id)
        
        # 1. Strict File Extension Validation
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in ['csv', 'xlsx', 'xls']:
            raise ValueError(f"Unsupported file extension: {file_ext}. Only CSV and Excel files are allowed.")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        ingested_tables = []

        # 2. Process CSV Files
        if file_ext == 'csv':
            # --- ROBUST ENCODING FALLBACK ---
            try:
                raw_df = pd.read_csv(tmp_path, header=None, encoding='utf-8')
            except UnicodeDecodeError:
                # Fallback for Windows/Excel generated CSV files
                raw_df = pd.read_csv(tmp_path, header=None, encoding='latin1')
            # --------------------------------
            
            clean_df = clean_spreadsheet_dataframe(raw_df)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', newline='', encoding='utf-8') as clean_tmp:
                clean_df.to_csv(clean_tmp.name, index=False)
                clean_tmp_path = clean_tmp.name
            
            session.conn.execute(f"CREATE TABLE {clean_name} AS SELECT * FROM read_csv_auto('{clean_tmp_path}', header=True)")
            os.unlink(clean_tmp_path)
            ingested_tables.append(clean_name)

        # 3. Process Excel Files (Multi-Sheet Handling)
        elif file_ext in ['xlsx', 'xls']:
            xls = pd.ExcelFile(tmp_path)
            
            for sheet in xls.sheet_names:
                raw_df = pd.read_excel(xls, sheet_name=sheet, header=None)
                if raw_df.empty:
                    continue
                    
                clean_df = clean_spreadsheet_dataframe(raw_df)
                
                # Combine the base file name with the sheet name (e.g., "financials_q1_budget")
                sheet_clean_name = validate_identifier(f"{clean_name}_{sheet}".replace(" ", "_").lower())
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', newline='', encoding='utf-8') as clean_tmp:
                    clean_df.to_csv(clean_tmp.name, index=False)
                    clean_tmp_path = clean_tmp.name
                    
                session.conn.execute(f"CREATE TABLE {sheet_clean_name} AS SELECT * FROM read_csv_auto('{clean_tmp_path}', header=True)")
                os.unlink(clean_tmp_path)
                ingested_tables.append(sheet_clean_name)

        return {
            "status": "success", 
            "message": f"Successfully ingested {len(ingested_tables)} table(s) from {file.filename}."
        }

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # Clean up the original uploaded temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@router.post("/connect/google_sheets")
def connect_google_sheets(
    workspace_id: str = Header(alias="X-Workspace-ID"),
    spreadsheet_id: str = Form(...),
    spreadsheet_name: str = Form(...),
    access_token: str = Form(...)
):
    try:
        session = session_manager.get_session(workspace_id)
        
        # 1. Initialize the Google Sheets API Client securely via the user's token
        creds = Credentials(token=access_token)
        service = build('sheets', 'v4', credentials=creds)

        # 2. Fetch the workbook metadata to discover all tabs (sheets)
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', [])
        
        if not sheets:
            raise ValueError("No tabs found in the selected spreadsheet.")

        ingested_tables = []

        # 3. Iterate through every tab in the workbook
        for sheet in sheets:
            tab_name = sheet.get("properties", {}).get("title", "")
            
            # Fetch the actual grid data for this specific tab
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, 
                range=tab_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                continue # Skip empty tabs
                
            # --- NEW PANDAS CLEANING PIPELINE FOR GOOGLE SHEETS ---
            raw_df = pd.DataFrame(values)
            clean_df = clean_spreadsheet_dataframe(raw_df)
            # ------------------------------------------------------

            # Create a SQL-safe table name: e.g. "my_budget_2026_q1_expenses"
            base_name = f"{spreadsheet_name}_{tab_name}"
            clean_name = validate_identifier(base_name.replace(" ", "_").lower())
            
            # 4. Write data to a temporary CSV to leverage DuckDB's fast read_csv_auto
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', newline='', encoding='utf-8') as clean_tmp:
                clean_df.to_csv(clean_tmp.name, index=False)
                clean_tmp_path = clean_tmp.name

            # 5. Ingest into the DuckDB session
            session.conn.execute(f"CREATE TABLE {clean_name} AS SELECT * FROM read_csv_auto('{clean_tmp_path}', header=True)")
            os.unlink(clean_tmp_path)
            ingested_tables.append(clean_name)

        if not ingested_tables:
            raise ValueError("The selected spreadsheet was completely empty.")

        return {
            "status": "success", 
            "message": f"Successfully ingested {len(ingested_tables)} tabs from {spreadsheet_name}."
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tables")
def list_tables(workspace_id: str = Header(alias="X-Workspace-ID")):
    session = session_manager.get_session(workspace_id)
    
    # 1. Hide pg_catalog and information_schema
    # 2. Allow 'main' (where CSV/Excel/Sheets live)
    # 3. Filter out DuckDB internal tables
    query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        AND table_schema NOT LIKE 'pg_toast%'
        AND table_type = 'BASE TABLE'; 
    """
    
    tables = session.conn.execute(query).fetchall()
    table_list = [t[0] for t in tables]
    
    return {"tables": table_list}