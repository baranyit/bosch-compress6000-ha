"""HA-free helpers: build the read client / write transport."""

from __future__ import annotations

import aiohttp

from .client import Km200ReadClient
from .const import REQUEST_SPACING
from .crypto import build_key
from .http_backend import HttpBackend
from .transport import AsyncioClock, Clock, ReadBackend, SpacedTransport
from .write_backend import HttpWriteBackend
from .write_transport import WritableTransport, WriteBackend


def build_client(
    session: aiohttp.ClientSession,
    host: str,
    gateway_password: str,
    private_password: str,
    *,
    backend: ReadBackend | None = None,
    clock: Clock | None = None,
    spacing: float = REQUEST_SPACING,
) -> Km200ReadClient:
    key = build_key(gateway_password, private_password)
    transport = SpacedTransport(
        key, backend or HttpBackend(session, host), clock or AsyncioClock(), spacing
    )
    return Km200ReadClient(transport)


def build_writable_client(
    session: aiohttp.ClientSession,
    host: str,
    gateway_password: str,
    private_password: str,
    *,
    backend: WriteBackend | None = None,
    clock: Clock | None = None,
    spacing: float = REQUEST_SPACING,
) -> tuple[WritableTransport, Km200ReadClient]:
    """One transport (one lock, one limiter) shared by the reads and the explicit writes."""
    key = build_key(gateway_password, private_password)
    transport = WritableTransport(
        key, backend or HttpWriteBackend(session, host), clock or AsyncioClock(), spacing
    )
    return transport, Km200ReadClient(transport)
