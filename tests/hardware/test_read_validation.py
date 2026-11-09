"""Opt-in READ-ONLY validation against a real gateway. Never runs in CI.

Run only on the maintainer's request, one run at a time, through the integration's own transport
(spaced requests, no writes). Credentials come from the environment, never from the repository:

    BOSCH_HW_HOST=... BOSCH_HW_GATEWAY_PASSWORD=... BOSCH_HW_PRIVATE_PASSWORD=... \
        python -m pytest tests/hardware -m hardware -s
"""

from __future__ import annotations

import os

import aiohttp
import pytest
from pytest_socket import socket_allow_hosts

from custom_components.bosch_compress6000.coordinator import Km200Coordinator
from custom_components.bosch_compress6000.protocol import ENERGY_POINTS, POINTS, last_complete_hour
from custom_components.bosch_compress6000.runtime import build_client

pytestmark = pytest.mark.hardware

ENV = ("BOSCH_HW_HOST", "BOSCH_HW_GATEWAY_PASSWORD", "BOSCH_HW_PRIVATE_PASSWORD")


@pytest.mark.skipif(not all(os.environ.get(v) for v in ENV), reason="no hardware configured")
async def test_catalog_points_are_readable(socket_enabled: None) -> None:
    socket_allow_hosts([os.environ["BOSCH_HW_HOST"]])  # the HA plugin allows localhost only
    async with aiohttp.ClientSession() as session:
        client = build_client(
            session,
            os.environ["BOSCH_HW_HOST"],
            os.environ["BOSCH_HW_GATEWAY_PASSWORD"],
            os.environ["BOSCH_HW_PRIVATE_PASSWORD"],
        )
        await client.probe()
        state = await client.read_state(POINTS)
        hour = last_complete_hour(Km200Coordinator.now(None))  # type: ignore[arg-type]
        energy: dict[str, object] = {}
        for point in ENERGY_POINTS:
            try:
                energy[point.key] = await client.read_hour(point, hour)
            except Exception as err:  # noqa: BLE001 - report, never abort the survey
                energy[point.key] = f"error: {err}"
    # Report which catalog paths this gateway lacks; the first run grades the "standard" points.
    print(f"readable={sorted(state.readings)} missing={state.missing} failed={state.failed}")
    print(f"hour={hour.isoformat()} energy={energy}")
    for key, reading in sorted(state.readings.items()):
        print(
            f"{key}: unit={reading.unit!r} writeable={reading.writeable} allowed={reading.allowed}"
            f" min={reading.minimum} max={reading.maximum} type={type(reading.value).__name__}"
        )
    assert not state.failed
    assert "outdoor_temperature" in state.readings
