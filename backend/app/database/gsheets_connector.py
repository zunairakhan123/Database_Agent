# import pandas as pd
# import gspread

# def register_sheet_metadata(session, sheet_url: str, table_name: str, creds_path: str):
#     """
#     PHASE 1 (Connection): Validates the URL and fetches column headers for RAG.
#     Does NOT materialize the full dataset.
#     """
#     gc = gspread.service_account(filename=creds_path)
#     try:
#         sheet = gc.open_by_url(sheet_url).sheet1
#         headers = sheet.row_values(1) # Fetch row 1 only
        
#         # Save state for JIT execution
#         session.registered_sheets[table_name] = sheet_url
#         return {"status": "success", "message": f"Google Sheet registered as {table_name}", "columns": headers}
#     except Exception as e:
#         raise Exception(f"Failed to access Google Sheet: {str(e)}")

# def fetch_live_sheet_jit(session, table_name: str, creds_path: str):
#     """
#     PHASE 3 (Execution): Called by LangGraph right before executing a query.
#     Fetches the absolute latest data from Google.
#     """
#     if table_name not in session.registered_sheets:
#         raise ValueError(f"Sheet {table_name} not registered in session.")
        
#     sheet_url = session.registered_sheets[table_name]
#     gc = gspread.service_account(filename=creds_path)
#     sheet = gc.open_by_url(sheet_url).sheet1
    
#     # Fetch live data and materialize temporarily
#     data = sheet.get_all_records()
#     df = pd.DataFrame(data)
    
#     # Overwrite the duckdb table with the freshest data
#     session.conn.register(table_name, df)