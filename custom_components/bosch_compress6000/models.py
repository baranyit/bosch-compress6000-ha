"""Typed immutable snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Reading:
    """One decoded point: a number or a string, plus what the device says about it."""

    value: float | str
    unit: str | None = None
    allowed: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    writeable: bool = False


@dataclass(frozen=True, slots=True)
class EnergySample:
    """The consumption of one completed hour (kWh) and the start of that hour."""

    value: float
    hour_start: datetime


@dataclass(frozen=True, slots=True)
class Snapshot:
    """What one refresh produced. Points that failed this cycle are simply absent."""

    readings: Mapping[str, Reading]
    energy: Mapping[str, EnergySample] = field(default_factory=dict)
    failed: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
