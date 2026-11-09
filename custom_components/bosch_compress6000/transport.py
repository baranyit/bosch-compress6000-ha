"""Serialized, rate-limited, read-only access to the gateway.

One request at a time per gateway with a pause between request starts. Time comes from an
injected clock so tests never sleep for real.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from typing import Protocol

from .crypto import decrypt


class ReadBackend(Protocol):
    """Wire access. Returns the raw (still encrypted) body, raises ``TransportError`` or
    ``PointUnavailableError``."""

    async def get(self, path: str, params: Mapping[str, str] | None = None) -> str: ...

    async def close(self) -> None: ...


class Clock(Protocol):
    def monotonic(self) -> float: ...

    async def sleep(self, seconds: float) -> None: ...


class AsyncioClock:
    def monotonic(self) -> float:
        return time.monotonic()

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class SpacedTransport:
    """The shared lock and limiter. Reads go through ``get``; subclasses add nothing else here."""

    def __init__(self, key: bytes, backend: ReadBackend, clock: Clock, spacing: float) -> None:
        self._key = key
        self._backend = backend
        self._clock = clock
        self._spacing = spacing
        self._lock = asyncio.Lock()
        self._last_start: float | None = None
        self.requests_started = 0

    async def _pace(self) -> None:
        if self._last_start is not None:
            wait = self._last_start + self._spacing - self._clock.monotonic()
            if wait > 0:
                await self._clock.sleep(wait)
        self._last_start = self._clock.monotonic()
        self.requests_started += 1

    async def get(self, path: str, params: Mapping[str, str] | None = None) -> str:
        """Return the decrypted reply text."""
        async with self._lock:
            await self._pace()
            body = await self._backend.get(path, params)
        return decrypt(self._key, body)

    async def close(self) -> None:
        await self._backend.close()
