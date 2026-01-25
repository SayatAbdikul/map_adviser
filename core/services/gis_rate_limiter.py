"""Rate limiter for 2GIS API calls."""

import asyncio
import os
import time
from collections import deque
from typing import Deque, Optional

import httpx

_DEFAULT_RATE_LIMIT = 5
_DEFAULT_RATE_PERIOD = 1.0

_rate_limiter_instance: Optional["AsyncRateLimiter"] = None
_rate_limiter_disabled = False


def _load_rate_limit_config() -> Optional[tuple[int, float]]:
    try:
        max_calls = int(os.getenv("GIS_API_RATE_LIMIT", str(_DEFAULT_RATE_LIMIT)))
    except ValueError:
        max_calls = _DEFAULT_RATE_LIMIT

    try:
        period_seconds = float(os.getenv("GIS_API_RATE_PERIOD", str(_DEFAULT_RATE_PERIOD)))
    except ValueError:
        period_seconds = _DEFAULT_RATE_PERIOD

    if max_calls <= 0 or period_seconds <= 0:
        return None

    return max_calls, period_seconds


class AsyncRateLimiter:
    """Simple sliding-window rate limiter for async workloads."""

    def __init__(self, max_calls: int, period_seconds: float) -> None:
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._lock = asyncio.Lock()
        self._calls: Deque[float] = deque()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._calls and self._calls[0] <= now - self.period_seconds:
                self._calls.popleft()

            if len(self._calls) >= self.max_calls:
                sleep_for = self.period_seconds - (now - self._calls[0])
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                now = time.monotonic()
                while self._calls and self._calls[0] <= now - self.period_seconds:
                    self._calls.popleft()

            self._calls.append(now)


def get_2gis_rate_limiter() -> Optional[AsyncRateLimiter]:
    global _rate_limiter_instance, _rate_limiter_disabled
    if _rate_limiter_disabled:
        return None

    if _rate_limiter_instance is None:
        config = _load_rate_limit_config()
        if config is None:
            _rate_limiter_disabled = True
            return None

        max_calls, period_seconds = config
        _rate_limiter_instance = AsyncRateLimiter(max_calls, period_seconds)

    return _rate_limiter_instance


async def rate_limit_request(_: httpx.Request) -> None:
    limiter = get_2gis_rate_limiter()
    if limiter is not None:
        await limiter.acquire()


def create_2gis_async_client(timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        event_hooks={"request": [rate_limit_request]},
    )
