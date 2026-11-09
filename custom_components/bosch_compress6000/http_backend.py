"""aiohttp wire backend. The gateway only answers requests with the ``TeleHeater`` user agent."""

from __future__ import annotations

from collections.abc import Mapping

import aiohttp

from .const import REQUEST_TIMEOUT, USER_AGENT
from .errors import PointUnavailableError, TransportError


class HttpBackend:
    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        self._session = session
        self._base = f"http://{host}/"
        self._timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    async def get(self, path: str, params: Mapping[str, str] | None = None) -> str:
        try:
            async with self._session.get(
                self._base + path.lstrip("/"),
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=self._timeout,
            ) as response:
                if response.status == 404:
                    raise PointUnavailableError(f"{path}: not found")
                if response.status != 200:
                    raise TransportError(f"{path}: HTTP {response.status}")
                return await response.text()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise TransportError(f"{path}: {err}") from err

    async def close(self) -> None:
        """The session belongs to Home Assistant; nothing to close here."""
