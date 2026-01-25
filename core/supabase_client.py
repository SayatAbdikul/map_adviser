"""
Supabase client using REST API directly (no supabase-py dependency).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


class SupabaseRestClient:
    """Supabase client using REST API directly."""

    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self._client = httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        await self._client.aclose()

    def table(self, table_name: str) -> "SupabaseTable":
        """Get table accessor."""
        return SupabaseTable(self._client, self.url, self.headers, table_name)


class SupabaseTable:
    """Table operations using REST API."""

    def __init__(self, client: httpx.AsyncClient, base_url: str, headers: Dict[str, str], table_name: str):
        self._client = client
        self._base_url = base_url
        self._headers = headers
        self._table_name = table_name
        self._filters: List[tuple[str, str]] = []
        self._select_cols = "*"
        self._data: Optional[Dict[str, Any]] = None
        self._operation: Optional[str] = None

    def insert(self, data: Dict[str, Any]) -> "SupabaseTable":
        """Prepare insert operation."""
        self._data = data
        self._operation = "insert"
        return self

    def select(self, columns: str = "*") -> "SupabaseTable":
        """Prepare select operation."""
        self._select_cols = columns
        self._operation = "select"
        return self

    def eq(self, column: str, value: Any) -> "SupabaseTable":
        """Add equality filter."""
        self._filters.append((column, f"eq.{value}"))
        return self

    async def execute(self):
        """Execute the operation."""
        url = f"{self._base_url}/rest/v1/{self._table_name}"

        class Result:
            def __init__(self, data):
                self.data = data if isinstance(data, list) else []

        try:
            if self._operation == "insert":
                response = await self._client.post(url, headers=self._headers, json=self._data)
                response.raise_for_status()
                return Result(response.json())

            if self._operation == "select":
                params: Dict[str, str] = {"select": self._select_cols}
                for key, value in self._filters:
                    params[key] = value
                response = await self._client.get(url, headers=self._headers, params=params)
                response.raise_for_status()
                return Result(response.json())

        except httpx.HTTPStatusError as exc:
            raise Exception(f"{exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise exc

        return Result([])


_client: Optional[SupabaseRestClient] = None


def get_supabase() -> SupabaseRestClient:
    """Get Supabase client instance (singleton)."""
    global _client

    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_ANON_KEY", "")

        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment")

        _client = SupabaseRestClient(url, key)

    return _client


async def close_supabase() -> None:
    """Close the shared Supabase client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
