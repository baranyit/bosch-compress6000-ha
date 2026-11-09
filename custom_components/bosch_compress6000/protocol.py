"""Pure protocol layer: the point catalog and the codecs. No I/O, no Home Assistant.

Confidence of the catalog (see ``docs/02-protocol-specification.md``): the paths marked ``homegate``
were read by the retired HomeGate bridge on the real installation. The others are standard KM200
resources that this gateway family exposes; they are probed at setup and skipped when the gateway
answers 404.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from .const import ENERGY_GRACE_MINUTES
from .errors import MalformedResponseError, PointUnavailableError
from .models import Reading


class WriteGroup(StrEnum):
    """Separate write opt-ins. Writing is off by default; each group is enabled on its own."""

    EXTRA_HOT_WATER = "extra_hot_water"
    HOT_WATER = "hot_water"
    HEATING = "heating"


class Confidence(StrEnum):
    HOMEGATE = "homegate"  # read on the real installation by the retired bridge
    STANDARD = "standard"  # standard KM200 resource, probed at setup


@dataclass(frozen=True, slots=True)
class Point:
    """One readable gateway resource. ``group`` is set only for the few writable ones."""

    key: str
    path: str
    confidence: Confidence
    group: WriteGroup | None = None


@dataclass(frozen=True, slots=True)
class EnergyPoint:
    """An hourly recording, published as the consumption of the last completed hour."""

    key: str
    path: str
    confidence: Confidence


H = Confidence.HOMEGATE
S = Confidence.STANDARD

DHW = "dhwCircuits/dhw1/"
HC1 = "heatingCircuits/hc1/"
HS = "heatSources/"
REC = "recordings/heatSources/total/energyMonitoring/"

POINTS: tuple[Point, ...] = (
    # Read-only metrics.
    Point("outdoor_temperature", "system/sensors/temperatures/outdoor_t1", H),
    Point("supply_temperature", HS + "actualSupplyTemperature", H),
    Point("return_temperature", HS + "returnTemperature", H),
    Point("modulation", HS + "actualModulation", H),
    Point("pump_modulation", HC1 + "pumpModulation", H),
    Point("room_temperature", HC1 + "roomtemperature", H),
    Point("room_setpoint", HC1 + "currentRoomSetpoint", H),
    Point("dhw_temperature", DHW + "actualTemp", H),
    Point("dhw_setpoint", DHW + "currentSetpoint", H),
    Point("number_of_starts", HS + "numberOfStarts", S),
    Point("system_pressure", HS + "systemPressure", S),
    Point("power_setpoint", HS + "powerSetpoint", S),
    # The only writable resources (each behind its own opt-in).
    Point("dhw_charge", DHW + "charge", H, WriteGroup.EXTRA_HOT_WATER),
    Point("dhw_operation_mode", DHW + "operationMode", S, WriteGroup.HOT_WATER),
    Point("dhw_temperature_high", DHW + "temperatureLevels/high", S, WriteGroup.HOT_WATER),
    Point("heating_operation_mode", HC1 + "operationMode", H, WriteGroup.HEATING),
    Point("heating_manual_setpoint", HC1 + "manualRoomSetpoint", S, WriteGroup.HEATING),
)

ENERGY_POINTS: tuple[EnergyPoint, ...] = (
    EnergyPoint("total_energy", REC + "consumedEnergy", H),
    EnergyPoint("compressor_energy", REC + "compressor", H),
    EnergyPoint("eheater_energy", REC + "eheater", H),
    EnergyPoint("heat_output_energy", REC + "outputProduced", S),
)

POINT_BY_KEY: dict[str, Point] = {point.key: point for point in POINTS}
ENERGY_BY_KEY: dict[str, EnergyPoint] = {point.key: point for point in ENERGY_POINTS}

# The value the gateway uses to start and stop one extra hot water charge.
CHARGE_START = "start"
CHARGE_STOP = "stop"


def _as_float(raw: Any) -> float | None:
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        return None
    number = float(raw)
    return number if math.isfinite(number) else None


def parse_reading(text: str) -> Reading:
    """Decode a ``floatValue`` / ``stringValue`` reply. Anything else is not a point."""
    try:
        data = json.loads(text)
    except ValueError as err:
        raise MalformedResponseError("reply is not JSON") from err
    if not isinstance(data, dict):
        raise MalformedResponseError("reply is not a JSON object")
    if "value" not in data:
        raise PointUnavailableError("resource has no value")
    raw = data["value"]
    allowed = tuple(str(item) for item in data.get("allowedValues") or ())
    unit = str(data["unitOfMeasure"]) if data.get("unitOfMeasure") else None
    writeable = data.get("writeable") in (1, True, "1")
    number = _as_float(raw)
    if number is not None:
        return Reading(
            number,
            unit,
            allowed,
            _as_float(data.get("minValue")),
            _as_float(data.get("maxValue")),
            writeable,
        )
    if isinstance(raw, str):
        return Reading(raw, unit, allowed, None, None, writeable)
    raise MalformedResponseError("value is neither a number nor a string")


def parse_hour_sample(text: str, hour: int) -> float | None:
    """Value of one hour of a daily recording, or ``None`` when that hour has no data.

    An hour with ``c == 0`` samples has no data: it is *not* zero. Reporting zero for it would
    pollute the Energy statistics, which is what the retired bridge did.
    """
    try:
        data = json.loads(text)
    except ValueError as err:
        raise MalformedResponseError("recording is not JSON") from err
    records = data.get("recording") if isinstance(data, dict) else None
    if not isinstance(records, list):
        raise MalformedResponseError("recording has no sample list")
    if not 0 <= hour < len(records):
        return None
    record = records[hour]
    if not isinstance(record, dict):
        return None
    total = _as_float(record.get("y"))
    count = _as_float(record.get("c"))
    if total is None or count is None or count == 0:
        return None
    return round(total / count, 2)


def last_complete_hour(now: datetime) -> datetime:
    """Start of the newest hour that ended at least the grace period ago."""
    settled = now - timedelta(minutes=ENERGY_GRACE_MINUTES)
    return settled.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)


def recording_params(hour_start: datetime) -> dict[str, str]:
    """Query parameters of the daily recording that contains ``hour_start``."""
    return {"interval": hour_start.strftime("%Y-%m-%d")}
