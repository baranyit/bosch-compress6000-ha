"""Read-only client: probe, state snapshot and hourly recordings."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

from .const import REQUEST_SPACING
from .errors import InvalidKeyError, PointUnavailableError, TransportError
from .models import Reading
from .protocol import (
    EnergyPoint,
    Point,
    parse_hour_sample,
    parse_reading,
    recording_params,
)
from .transport import SpacedTransport


@dataclass(frozen=True, slots=True)
class StateRead:
    readings: Mapping[str, Reading]
    failed: tuple[str, ...]
    missing: tuple[str, ...]


def minimum_poll_interval(requests: int) -> int:
    """The shortest cycle that still leaves the gateway idle between cycles."""
    return math.ceil(requests * REQUEST_SPACING * 1.5)


class Km200ReadClient:
    def __init__(self, transport: SpacedTransport) -> None:
        self._transport = transport

    @property
    def transport(self) -> SpacedTransport:
        return self._transport

    async def probe(self) -> str:
        """Read the gateway clock. Proves reachability and, by decrypting, both passwords."""
        text = await self._transport.get("gateway/DateTime")
        reading = parse_reading(text)
        return str(reading.value)

    async def identity(self) -> str | None:
        """The gateway UUID when it offers one (used as the stable unique ID)."""
        try:
            reading = parse_reading(await self._transport.get("gateway/uuid"))
        except (PointUnavailableError, TransportError):
            return None
        return str(reading.value) or None

    async def read_point(self, point: Point) -> Reading:
        return parse_reading(await self._transport.get(point.path))

    async def read_state(self, points: Iterable[Point]) -> StateRead:
        """Read the points one by one; a failing point never aborts the others.

        A wrong key is not a per-point failure and is raised at once.
        """
        readings: dict[str, Reading] = {}
        failed: list[str] = []
        missing: list[str] = []
        for point in points:
            try:
                readings[point.key] = await self.read_point(point)
            except InvalidKeyError:
                raise
            except PointUnavailableError:
                missing.append(point.key)
            except TransportError:
                failed.append(point.key)
        return StateRead(readings, tuple(failed), tuple(missing))

    async def read_hour(self, point: EnergyPoint, hour_start: datetime) -> float | None:
        """Consumption of one completed hour, ``None`` if the gateway has no sample for it."""
        text = await self._transport.get(point.path, recording_params(hour_start))
        return parse_hour_sample(text, hour_start.hour)
