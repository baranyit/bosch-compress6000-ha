"""Command layer: permissions, validation, debounce, latest-value-wins, optimistic overlay.

Nothing here runs on its own. A command exists only because a user asked for it; setup, polling,
reload, diagnostics and unload never create one, and unwritten commands are dropped on close
(never replayed).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .errors import CommandRejectedError, Km200Error, RejectReason
from .models import Reading
from .protocol import Point, WriteGroup
from .write_transport import WritableTransport

_LOGGER = logging.getLogger(__name__)

COMMAND_MAX_WAIT = 10.0


@dataclass(frozen=True, slots=True)
class CommandPermissions:
    write_enabled: bool = False
    groups: frozenset[WriteGroup] = frozenset()

    def allows(self, group: WriteGroup) -> bool:
        return self.write_enabled and group in self.groups


def validate_command(
    point: Point,
    reading: Reading | None,
    value: float | str,
    permissions: CommandPermissions,
) -> float | str:
    """Return the value to send, or raise ``CommandRejectedError``. Never rounds silently."""
    if point.group is None:
        raise CommandRejectedError(RejectReason.NOT_WRITEABLE, f"{point.key} is read-only")
    if not permissions.write_enabled:
        raise CommandRejectedError(RejectReason.WRITE_DISABLED, "write mode is off")
    if point.group not in permissions.groups:
        raise CommandRejectedError(
            RejectReason.GROUP_NOT_ALLOWED, f"writing {point.group.value} is not enabled"
        )
    if reading is None:
        raise CommandRejectedError(RejectReason.UNKNOWN_POINT, f"{point.key} has no reading")
    if not reading.writeable:
        raise CommandRejectedError(RejectReason.NOT_WRITEABLE, f"{point.key} is not writeable")
    if isinstance(reading.value, str):
        if not isinstance(value, str):
            raise CommandRejectedError(RejectReason.INVALID_VALUE, "expected a text value")
        if reading.allowed and value not in reading.allowed:
            raise CommandRejectedError(
                RejectReason.INVALID_VALUE, f"{value!r} is not one of {list(reading.allowed)}"
            )
        return value
    if isinstance(value, str) or not math.isfinite(value):
        raise CommandRejectedError(RejectReason.INVALID_VALUE, "expected a finite number")
    if reading.minimum is not None and value < reading.minimum:
        raise CommandRejectedError(RejectReason.OUT_OF_RANGE, f"{value} < {reading.minimum}")
    if reading.maximum is not None and value > reading.maximum:
        raise CommandRejectedError(RejectReason.OUT_OF_RANGE, f"{value} > {reading.maximum}")
    return value


class CommandExecutor:
    """Debounce, then one POST per changed point (latest value wins), then a read-back."""

    def __init__(
        self,
        transport: WritableTransport,
        permissions: CommandPermissions,
        *,
        debounce: float,
        read_back: Callable[[Point], Awaitable[None]],
        on_change: Callable[[], None],
        max_wait: float = COMMAND_MAX_WAIT,
    ) -> None:
        self.permissions = permissions
        self._transport = transport
        self._debounce = debounce
        self._max_wait = max_wait
        self._read_back = read_back
        self._on_change = on_change
        self._pending: dict[str, tuple[Point, float | str]] = {}
        self._in_flight: dict[str, float | str] = {}
        self._first_pending: float | None = None
        self._task: asyncio.Future[None] | None = None
        self._flushing = False
        self.errors: deque[str] = deque(maxlen=10)
        self.writes_sent = 0

    def optimistic(self, key: str) -> float | str | None:
        """The requested value to show until the read-back decides."""
        if key in self._pending:
            return self._pending[key][1]
        return self._in_flight.get(key)

    def submit(self, point: Point, value: float | str) -> None:
        """Queue an already validated command. No I/O: the debounced flush writes it."""
        loop = asyncio.get_running_loop()
        if self._first_pending is None:
            self._first_pending = loop.time()
        self._pending[point.key] = (point, value)
        if not self._flushing:  # a running flush picks the new value up by itself
            if self._task is not None:
                self._task.cancel()  # still debouncing: restart the window
            delay = min(
                self._debounce, max(0.0, self._first_pending + self._max_wait - loop.time())
            )
            self._task = asyncio.ensure_future(self._flush_after(delay))
        self._on_change()

    async def _flush_after(self, delay: float) -> None:
        await asyncio.sleep(delay)
        self._flushing = True
        self._first_pending = None
        try:
            while self._pending:
                key, (point, value) = next(iter(self._pending.items()))
                del self._pending[key]
                self._in_flight[key] = value
                try:
                    await self._transport.post_value(point.path, value)
                    self.writes_sent += 1
                    await self._read_back(point)
                except Km200Error as err:
                    self.errors.append(f"{point.key}: {err}")
                    _LOGGER.warning("Write of %s failed: %s", point.key, err)
                finally:
                    self._in_flight.pop(key, None)
                    self._on_change()
        finally:
            self._flushing = False

    async def close(self) -> None:
        """Drop unwritten commands (never replayed) and stop the flush task."""
        self._pending.clear()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._in_flight.clear()
