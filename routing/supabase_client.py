"""
Supabase client using REST API directly (no supabase-py dependency needed).
This avoids the grpcio/pydantic-core build issues on Windows.
"""
import os
import httpx
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List

# Load environment variables
load_dotenv()


class SupabaseRestClient:
    """Supabase client using REST API directly"""
    
    def __init__(self, url: str, key: str):
        self.url = url.rstrip('/')
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def table(self, table_name: str):
        """Get table accessor"""
        return SupabaseTable(self.url, self.headers, table_name)


class SupabaseTable:
    """Table operations using REST API"""
    
    def __init__(self, base_url: str, headers: Dict, table_name: str):
        self.base_url = base_url
        self.headers = headers
        self.table_name = table_name
        self._filters: List[str] = []
        self._select_cols = "*"
        self._data: Optional[Dict] = None
        self._operation = None
    
    def insert(self, data: Dict[str, Any]):
        """Prepare insert operation"""
        self._data = data
        self._operation = "insert"
        return self
    
    def select(self, columns: str = "*"):
        """Prepare select operation"""
        self._select_cols = columns
        self._operation = "select"
        return self
    
    def eq(self, column: str, value: Any):
        """Add equality filter"""
        self._filters.append(f"{column}=eq.{value}")
        return self
    
    def execute(self):
        """Execute the operation"""
        url = f"{self.base_url}/rest/v1/{self.table_name}"
        
        class Result:
            def __init__(self, data):
                self.data = data if isinstance(data, list) else []
        
        try:
            with httpx.Client(timeout=10.0) as client:
                if self._operation == "insert":
                    response = client.post(url, headers=self.headers, json=self._data)
                    response.raise_for_status()
                    return Result(response.json())
                
                elif self._operation == "select":
                    params = {"select": self._select_cols}
                    if self._filters:
                        url += "?" + "&".join(self._filters)
                    response = client.get(url, headers=self.headers, params=params if not self._filters else None)
                    response.raise_for_status()
                    return Result(response.json())
        
        except httpx.HTTPStatusError as e:
            raise Exception(f"{e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise
        
        return Result([])


# Singleton client instance
_client: Optional[SupabaseRestClient] = None


def get_supabase() -> SupabaseRestClient:
    """Get Supabase client instance (singleton)"""
    global _client
    
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_ANON_KEY", "")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment")
        
        _client = SupabaseRestClient(url, key)
    
    return _client


# For backward compatibility
supabase = get_supabase()
