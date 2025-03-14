"""
Supabase configuration module
"""
import os
from django.conf import settings
from supabase import create_client, Client

# Global Supabase client
supabase_client = None

def initialize_supabase():
    """
    Initialize Supabase client with credentials from settings or environment variables
    """
    global supabase_client
    
    # Try to get credentials from settings.py first
    supabase_url = getattr(settings, 'SUPABASE_URL', None)
    supabase_key = getattr(settings, 'SUPABASE_KEY', None)
    
    # If not in settings, try environment variables
    if not all([supabase_url, supabase_key]):
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
    
    # Validate credentials
    if not all([supabase_url, supabase_key]):
        print("Supabase credentials not found in settings or environment variables")
        return False
    
    try:
        # Initialize the Supabase client
        supabase_client = create_client(supabase_url, supabase_key)
        
        # Test the connection with a simple query
        # This will raise an exception if the connection fails
        supabase_client.table('test').select('*').limit(1).execute()
        
        print("Supabase configuration successful")
        return True
    except Exception as e:
        print(f"Supabase configuration failed: {str(e)}")
        return False

def get_supabase_client() -> Client:
    """
    Get the Supabase client instance
    
    Returns:
        Supabase client instance or None if not initialized
    """
    global supabase_client
    
    if supabase_client is None:
        # Try to initialize if not already done
        initialize_supabase()
    
    return supabase_client

def query_example(table_name, query_params=None):
    """
    Example function to query Supabase
    
    Args:
        table_name: Name of the table to query
        query_params: Dictionary of query parameters
        
    Returns:
        Query results or error message
    """
    client = get_supabase_client()
    
    if client is None:
        return {'error': 'Supabase client not initialized'}
    
    try:
        # Start building the query
        query = client.table(table_name).select('*')
        
        # Apply filters if provided
        if query_params:
            if 'limit' in query_params:
                query = query.limit(query_params['limit'])
            
            if 'filters' in query_params:
                for column, value in query_params['filters'].items():
                    query = query.eq(column, value)
        
        # Execute the query
        response = query.execute()
        
        return {
            'success': True,
            'data': response.data
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        } 