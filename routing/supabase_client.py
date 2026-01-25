"""
Supabase client initialization for backend
For now, using a mock implementation. Replace with real Supabase when library is available.
"""
import os
from typing import Optional, Dict, Any

# Try to import real supabase, fall back to mock if not available
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


class MockSupabaseClient:
    """Mock Supabase client for development without the full supabase library"""
    
    def __init__(self):
        # In-memory store for users (replace with database in production)
        self.users = {}
        self.user_id_counter = 1
    
    def table(self, table_name: str):
        """Mock table access"""
        return MockTable(table_name, self.users)
    
    def auth(self):
        """Mock auth module"""
        return self


class MockTable:
    """Mock table for database operations"""
    
    def __init__(self, name: str, users_store: Dict):
        self.name = name
        self.users_store = users_store
        self._data = None
        self._filter_criteria = None
        self._is_insert = False
    
    def insert(self, data: Dict[str, Any]):
        """Mock insert operation"""
        if self.name == "users":
            user_id = max([int(k) for k in self.users_store.keys()] + [0]) + 1
            user_data = {**data, "id": user_id}  # Use int id, not string
            self.users_store[str(user_id)] = user_data
            self._data = user_data
            self._is_insert = True
        return self
    
    def select(self, *args):
        """Mock select operation"""
        self._data = list(self.users_store.values()) if self.users_store else []
        return self
    
    def eq(self, field: str, value: Any):
        """Mock equality filter"""
        self._filter_criteria = (field, value)
        return self
    
    def execute(self):
        """Mock execute to return filtered results"""
        class Result:
            def __init__(self, data):
                self.data = data
        
        if self._filter_criteria:
            field, value = self._filter_criteria
            filtered = [u for u in self.users_store.values() if u.get(field) == value]
            return Result(filtered)
        
        # For insert operations, return data as a list (like real Supabase does)
        if self._is_insert and self._data:
            return Result([self._data])
        
        return Result(self._data if isinstance(self._data, list) else [])


# Singleton mock client instance
_mock_client: Optional[MockSupabaseClient] = None


# Create client
def get_supabase():
    """Get Supabase client instance (singleton pattern for mock client)"""
    global _mock_client
    
    if SUPABASE_AVAILABLE:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_ANON_KEY", "")
        if url and key:
            return create_client(url, key)
    
    # Fall back to mock client (singleton)
    if _mock_client is None:
        _mock_client = MockSupabaseClient()
    return _mock_client


# For backward compatibility
supabase = get_supabase()
