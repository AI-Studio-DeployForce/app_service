from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_HOST_URL')
supabase_key = os.getenv('SUPABASE_API_SECRET')
supabase_client = create_client(supabase_url, supabase_key) 

def get_new_supabase_client():
    return supabase_client

# INSERT
def insert_row(table_name: str, data: dict):
    """Insert a single row into a Supabase table."""
    response = supabase_client.table(table_name).insert(data).execute()
    return response.data if response.data else response.error

def insert_multiple_rows(table_name: str, data_list: list[dict]) -> list[dict] | None:
    """
    Inserts multiple rows into a Supabase table.

    Parameters:
        table_name (str): The name of the Supabase table.
        data_list (list): A list of dictionaries, each representing a row.

    Returns:
        list: List of inserted row data if successful, None otherwise.
    """
    if not data_list or not isinstance(data_list, list):
        print("Invalid data for insertion.")
        return None

    try:
        response = supabase_client.table(table_name).insert(data_list).execute()
        if response.data:
            return response.data
        else:
            print("Insertion failed:", response.error)
            return None
    except Exception as e:
        print(f"Supabase insertion error: {e}")
        return None

# RETRIEVE BY ID
def get_row_by_id(table_name: str, id_field: str, id_value):
    """Retrieve a single row by its ID field (usually primary key)."""
    response = supabase_client.table(table_name).select("*").eq(id_field, id_value).execute()
    return response.data if response.data else response.error

# RETRIEVE BY MULTIPLE FIELDS
def get_rows_by_filters(table_name: str, filters: dict):
    """Retrieve rows matching multiple filters (e.g., {'user_id': 1, 'status': 'done'})."""
    query = supabase_client.table(table_name).select("*")
    for field, value in filters.items():
        query = query.eq(field, value)
    response = query.execute()
    return response.data if response.data else response.error

# UPDATE BY ID
def update_row_by_id(table_name: str, id_field: str, id_value, updated_data: dict):
    """Update a row based on its ID field."""
    response = supabase_client.table(table_name).update(updated_data).eq(id_field, id_value).execute()
    return response.data if response.data else response.error

# DELETE BY ID
def delete_row_by_id(table_name: str, id_field: str, id_value):
    """Delete a row based on its ID field."""
    response = supabase_client.table(table_name).delete().eq(id_field, id_value).execute()
    return response.data if response.data else response.error