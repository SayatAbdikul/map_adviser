"""Lightweight vector store for saving and searching named locations."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path
from typing import Optional

import litellm

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "location_store.db"
_DB_PATH = Path(os.getenv("LOCATION_STORE_PATH", str(_DEFAULT_DB_PATH)))

EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

_store_instance: Optional["LocationStore"] = None
_store_lock = asyncio.Lock()


@dataclass
class SavedLocation:
    key: str
    longitude: float
    latitude: float
    description: str | None


async def get_location_store() -> "LocationStore":
    global _store_instance
    async with _store_lock:
        if _store_instance is None:
            _store_instance = LocationStore(_DB_PATH)
    return _store_instance


async def close_location_store() -> None:
    global _store_instance
    async with _store_lock:
        if _store_instance is not None:
            _store_instance.close()
            _store_instance = None


class LocationStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                key_normalized TEXT NOT NULL UNIQUE,
                description TEXT,
                longitude REAL NOT NULL,
                latitude REAL NOT NULL,
                embedding TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception as exc:
            logger.warning("Failed to close location store: %s", exc)

    async def save_location(
        self,
        key: str,
        longitude: float,
        latitude: float,
        description: str | None = None,
    ) -> dict:
        key_clean = key.strip()
        if not key_clean:
            return {"error": "Key cannot be empty"}
        embedding = await _get_embedding(_build_embedding_text(key_clean, description))
        if not embedding:
            return {"error": "Failed to compute embedding"}

        now = _utc_now()
        normalized = key_clean.lower()

        async with self._lock:
            self._conn.execute(
                """
                INSERT INTO locations (
                    key, key_normalized, description, longitude, latitude, embedding, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key_normalized) DO UPDATE SET
                    key=excluded.key,
                    description=excluded.description,
                    longitude=excluded.longitude,
                    latitude=excluded.latitude,
                    embedding=excluded.embedding,
                    updated_at=excluded.updated_at
                """,
                (
                    key_clean,
                    normalized,
                    description,
                    float(longitude),
                    float(latitude),
                    json.dumps(embedding),
                    now,
                    now,
                ),
            )
            self._conn.commit()

        return {
            "status": "saved",
            "key": key_clean,
            "description": description,
            "coordinates": [float(longitude), float(latitude)],
        }

    async def search(self, query: str, limit: int = 5) -> dict:
        query_clean = query.strip()
        if not query_clean:
            return {"matches": []}

        async with self._lock:
            rows = self._conn.execute(
                "SELECT key, description, longitude, latitude, embedding FROM locations"
            ).fetchall()
        if not rows:
            return {"matches": []}

        query_embedding = await _get_embedding(query_clean)
        if not query_embedding:
            return {"matches": _fallback_keyword_search(rows, query_clean, limit)}

        scored = []
        for key, description, longitude, latitude, embedding_raw in rows:
            try:
                embedding = json.loads(embedding_raw)
            except json.JSONDecodeError:
                continue
            score = _cosine_similarity(query_embedding, embedding)
            scored.append(
                {
                    "key": key,
                    "description": description,
                    "coordinates": [float(longitude), float(latitude)],
                    "score": round(score, 4),
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return {"matches": scored[: max(1, limit)]}


def _fallback_keyword_search(rows: list[tuple], query: str, limit: int) -> list[dict]:
    query_lower = query.lower()
    matches = []
    for key, description, longitude, latitude, _ in rows:
        key_text = (key or "").lower()
        desc_text = (description or "").lower()
        if query_lower in key_text or query_lower in desc_text:
            matches.append(
                {
                    "key": key,
                    "description": description,
                    "coordinates": [float(longitude), float(latitude)],
                    "score": 1.0,
                }
            )
    return matches[: max(1, limit)]


def _build_embedding_text(key: str, description: str | None) -> str:
    if description:
        return f"{key} - {description}"
    return key


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


async def _get_embedding(text: str) -> list[float] | None:
    try:
        response = await litellm.aembedding(
            model=EMBEDDING_MODEL,
            input=[text],
        )
        data = response.get("data") if isinstance(response, dict) else None
        if not data:
            return None
        return data[0].get("embedding")
    except Exception as exc:
        logger.warning("Embedding failed: %s", exc)
        return None
