from __future__ import annotations

from itertools import pairwise

import pytest

from custom_components.bosch_compress6000.client import Km200ReadClient, minimum_poll_interval
from custom_components.bosch_compress6000.crypto import build_key
from custom_components.bosch_compress6000.errors import InvalidKeyError
from custom_components.bosch_compress6000.protocol import ENERGY_POINTS, POINTS
from custom_components.bosch_compress6000.transport import SpacedTransport

from .fakes import GATEWAY_PASSWORD, KEY, PRIVATE_PASSWORD, FakeGateway, VirtualClock

SPACING = 0.5


def make(gateway: FakeGateway, clock: VirtualClock, key: bytes = KEY) -> Km200ReadClient:
    return Km200ReadClient(SpacedTransport(key, gateway, clock, SPACING))


async def test_reads_every_catalog_point_and_never_posts() -> None:
    gateway, clock = FakeGateway(), VirtualClock()
    client = make(gateway, clock)
    state = await client.read_state(POINTS)
    assert state.failed == () and state.missing == ("power_setpoint",)  # not on this fake gateway
    assert state.readings["outdoor_temperature"].value == 4.3
    assert gateway.posts == []


async def test_request_starts_are_spaced_on_the_virtual_clock() -> None:
    gateway, clock = FakeGateway(), VirtualClock()
    starts: list[float] = []
    original = gateway.get

    async def spy(path: str, params: dict[str, str] | None = None) -> str:
        starts.append(clock.monotonic())
        return await original(path, params)

    gateway.get = spy  # type: ignore[method-assign]
    await make(gateway, clock).read_state(POINTS)
    gaps = [b - a for a, b in pairwise(starts)]
    assert gaps and all(gap >= SPACING - 1e-9 for gap in gaps)


async def test_one_failing_point_does_not_abort_the_cycle() -> None:
    gateway, clock = FakeGateway(), VirtualClock()
    gateway.fail_paths.add("heatSources/returnTemperature")
    state = await make(gateway, clock).read_state(POINTS)
    assert state.failed == ("return_temperature",)
    assert "supply_temperature" in state.readings


async def test_wrong_password_is_raised_not_swallowed() -> None:
    gateway, clock = FakeGateway(), VirtualClock()
    wrong = build_key(GATEWAY_PASSWORD, PRIVATE_PASSWORD + "x")
    client = make(gateway, clock, wrong)
    with pytest.raises(InvalidKeyError):
        await client.read_state(POINTS)
    with pytest.raises(InvalidKeyError):
        await client.probe()


async def test_probe_and_identity() -> None:
    gateway, clock = FakeGateway(), VirtualClock()
    client = make(gateway, clock)
    assert await client.probe() == "2026-11-09T15:07:00"
    assert await client.identity() == "test-gateway-uuid"
    del gateway.points["gateway/uuid"]
    assert await client.identity() is None


async def test_read_hour_returns_the_completed_hour_or_none() -> None:
    from datetime import UTC, datetime

    gateway, clock = FakeGateway(), VirtualClock()
    client = make(gateway, clock)
    total = ENERGY_POINTS[0]
    assert await client.read_hour(total, datetime(2026, 11, 9, 14, tzinfo=UTC)) == 1.5
    assert await client.read_hour(total, datetime(2026, 11, 9, 13, tzinfo=UTC)) is None
    assert gateway.gets[-1] == (total.path, {"interval": "2026-11-09"})


def test_minimum_poll_interval_grows_with_the_plan() -> None:
    assert minimum_poll_interval(21) == 16
    assert minimum_poll_interval(100) > minimum_poll_interval(21)
