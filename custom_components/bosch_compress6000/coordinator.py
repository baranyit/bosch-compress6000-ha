"""Coordinator: state every poll, hourly energy once per completed hour.

A refresh only reads. Writes come exclusively from the command executor, after an explicit user
command, followed by one read-back of the written point.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import Km200ReadClient, minimum_poll_interval
from .commands import CommandExecutor, validate_command
from .const import DOMAIN
from .errors import (
    CommandRejectedError,
    InvalidKeyError,
    Km200Error,
    RejectReason,
)
from .models import EnergySample, Snapshot
from .protocol import ENERGY_POINTS, POINT_BY_KEY, POINTS, Point, last_complete_hour

if TYPE_CHECKING:
    from . import Km200ConfigEntry

_LOGGER = logging.getLogger(__name__)

# An hour without a sample is asked for this many times, then left alone until the next hour.
MAX_EMPTY_ATTEMPTS = 3


class Km200Coordinator(DataUpdateCoordinator[Snapshot]):
    config_entry: Km200ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: Km200ConfigEntry,
        client: Km200ReadClient,
        interval: int,
    ) -> None:
        self._points: tuple[Point, ...] = POINTS
        interval = max(interval, minimum_poll_interval(len(POINTS) + len(ENERGY_POINTS)))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self.executor: CommandExecutor | None = None
        self._discovered = False
        self._energy: dict[str, EnergySample] = {}
        self._energy_done: dict[str, datetime] = {}
        self._energy_tries: dict[str, tuple[datetime, int]] = {}

    def now(self) -> datetime:
        return dt_util.now()

    def optimistic(self, key: str) -> float | str | None:
        return self.executor.optimistic(key) if self.executor is not None else None

    def submit(self, key: str, value: float | str) -> None:
        """Validate and queue a command. No I/O: the debounced flush writes it."""
        executor = self.executor
        if executor is None:
            raise CommandRejectedError(RejectReason.WRITE_DISABLED, "write mode is off")
        point = POINT_BY_KEY[key]
        reading = self.data.readings.get(key) if self.data else None
        executor.submit(point, validate_command(point, reading, value, executor.permissions))

    async def read_back(self, point: Point) -> None:
        """One read of a point that was just written; the answer decides the shown state."""
        reading = await self.client.read_point(point)
        if self.data is not None:
            readings = {**self.data.readings, point.key: reading}
            self.async_set_updated_data(replace(self.data, readings=readings))

    async def _async_update_data(self) -> Snapshot:
        try:
            state = await self.client.read_state(self._points)
        except InvalidKeyError as err:
            raise ConfigEntryAuthFailed("The gateway or private password is wrong") from err
        except Km200Error as err:  # pragma: no cover - read_state isolates per-point errors
            raise UpdateFailed(str(err)) from err
        if not state.readings:
            raise UpdateFailed("No point answered")
        if not self._discovered:
            # Skip what this gateway does not have; keep what only failed this time.
            self._points = tuple(p for p in POINTS if p.key not in state.missing)
            self._discovered = True
        try:
            await self._refresh_energy()
        except InvalidKeyError as err:
            raise ConfigEntryAuthFailed("The gateway or private password is wrong") from err
        return Snapshot(state.readings, dict(self._energy), state.failed, state.missing)

    async def _refresh_energy(self) -> None:
        target = last_complete_hour(self.now())
        for point in ENERGY_POINTS:
            if self._energy_done.get(point.key) == target:
                continue
            try:
                value = await self.client.read_hour(point, target)
            except InvalidKeyError:
                raise
            except Km200Error as err:
                _LOGGER.debug("Energy %s for %s not available: %s", point.key, target, err)
                continue
            if value is None:
                hour, tries = self._energy_tries.get(point.key, (target, 0))
                tries = tries + 1 if hour == target else 1
                self._energy_tries[point.key] = (target, tries)
                if tries >= MAX_EMPTY_ATTEMPTS:
                    self._energy_done[point.key] = target
                continue
            self._energy[point.key] = EnergySample(value, target)
            self._energy_done[point.key] = target

    async def async_shutdown(self) -> None:
        await super().async_shutdown()
