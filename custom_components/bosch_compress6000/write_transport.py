"""The only write route: a transport subclass that can POST. Built only when write mode is on."""

from __future__ import annotations

import json
from typing import Protocol

from .crypto import encrypt
from .transport import Clock, ReadBackend, SpacedTransport


class WriteBackend(ReadBackend, Protocol):
    async def post(self, path: str, body: str) -> None: ...


class WritableTransport(SpacedTransport):
    def __init__(self, key: bytes, backend: WriteBackend, clock: Clock, spacing: float) -> None:
        super().__init__(key, backend, clock, spacing)
        self._write_backend = backend

    async def post_value(self, path: str, value: float | str) -> None:
        """Send ``{"value": ...}`` to one resource, through the shared lock and limiter."""
        body = encrypt(self._key, json.dumps({"value": value}, separators=(",", ":")))
        async with self._lock:
            await self._pace()
            await self._write_backend.post(path, body)
