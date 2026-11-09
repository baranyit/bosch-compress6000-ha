"""In-process gateway double: speaks the real wire format (base64 + AES-ECB) from a dict."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from custom_components.bosch_compress6000.crypto import build_key, decrypt, encrypt
from custom_components.bosch_compress6000.errors import PointUnavailableError, TransportError

GATEWAY_PASSWORD = "AAAABBBBCCCCDDDD"  # test value, not a real credential
PRIVATE_PASSWORD = "test-private-password"  # test value, not a real credential
KEY = build_key(GATEWAY_PASSWORD, PRIVATE_PASSWORD)


class VirtualClock:
    """Time that only moves when something sleeps, so tests never wait."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def float_point(value: float, *, unit: str = "C", writeable: bool = False, **extra: Any) -> dict:
    return {
        "type": "floatValue",
        "value": value,
        "unitOfMeasure": unit,
        "writeable": 1 if writeable else 0,
        **extra,
    }


def string_point(value: str, allowed: list[str] | None = None, *, writeable: bool = False) -> dict:
    point: dict[str, Any] = {
        "type": "stringValue",
        "value": value,
        "writeable": 1 if writeable else 0,
    }
    if allowed:
        point["allowedValues"] = allowed
    return point


def hourly(values: Mapping[int, float | None]) -> list[dict[str, float]]:
    """A daily recording: ``None`` means no sample (c == 0), a number is one sample."""
    return [
        {"y": float(values[hour]), "c": 1.0} if values.get(hour) is not None else {"y": 0, "c": 0}
        for hour in range(24)
    ]


DEFAULT_POINTS: dict[str, dict] = {
    "system/sensors/temperatures/outdoor_t1": float_point(4.3),
    "heatSources/actualSupplyTemperature": float_point(32.1),
    "heatSources/returnTemperature": float_point(31.4),
    "heatSources/actualModulation": float_point(54.0, unit="%"),
    "heatingCircuits/hc1/pumpModulation": float_point(0.0, unit="%"),
    "heatingCircuits/hc1/roomtemperature": float_point(24.7),
    "heatingCircuits/hc1/currentRoomSetpoint": float_point(23.0),
    "dhwCircuits/dhw1/actualTemp": float_point(49.5),
    "dhwCircuits/dhw1/currentSetpoint": float_point(55.0),
    "heatSources/numberOfStarts": float_point(1234, unit=""),
    "heatSources/systemPressure": float_point(1.6, unit="bar"),
    "dhwCircuits/dhw1/charge": string_point("stop", ["start", "stop"], writeable=True),
    "dhwCircuits/dhw1/operationMode": string_point("auto", ["auto", "high", "off"], writeable=True),
    "dhwCircuits/dhw1/temperatureLevels/high": float_point(
        55.0, writeable=True, minValue=40, maxValue=65
    ),
    "heatingCircuits/hc1/operationMode": string_point("auto", ["auto", "manual"], writeable=True),
    "heatingCircuits/hc1/manualRoomSetpoint": float_point(
        21.0, writeable=True, minValue=10, maxValue=28
    ),
    "gateway/DateTime": string_point("2026-11-09T15:07:00"),
    "gateway/uuid": string_point("test-gateway-uuid"),
}

REC = "recordings/heatSources/total/energyMonitoring/"
DEFAULT_RECORDINGS: dict[str, list[dict[str, float]]] = {
    REC + "consumedEnergy": hourly({14: 1.5}),
    REC + "compressor": hourly({14: 1.2}),
    REC + "eheater": hourly({14: 0.3}),
    REC + "outputProduced": hourly({14: 4.8}),
}


class FakeGateway:
    """Backend double. Records every request; POST applies the value like the device would."""

    def __init__(self) -> None:
        self.points: dict[str, dict] = json.loads(json.dumps(DEFAULT_POINTS))
        self.recordings: dict[str, list[dict[str, float]]] = json.loads(
            json.dumps(DEFAULT_RECORDINGS)
        )
        self.gets: list[tuple[str, dict[str, str]]] = []
        self.posts: list[tuple[str, Any]] = []
        self.fail_paths: set[str] = set()
        self.key = KEY
        self.offline = False

    async def get(self, path: str, params: Mapping[str, str] | None = None) -> str:
        self.gets.append((path, dict(params or {})))
        if self.offline or path in self.fail_paths:
            raise TransportError(f"{path}: unreachable")
        if path.startswith("recordings/"):
            if path not in self.recordings:
                raise PointUnavailableError(path)
            return encrypt(self.key, json.dumps({"recording": self.recordings[path]}))
        if path not in self.points:
            raise PointUnavailableError(path)
        return encrypt(self.key, json.dumps({"id": "/" + path, **self.points[path]}))

    async def post(self, path: str, body: str) -> None:
        if self.offline or path in self.fail_paths:
            raise TransportError(f"{path}: unreachable")
        value = json.loads(decrypt(self.key, body))["value"]
        self.posts.append((path, value))
        self.points[path]["value"] = value

    async def close(self) -> None:
        return None
