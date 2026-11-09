"""Opt-in hardware WRITE test: one extra hot water start, observe, stop. Never in CI.

Needs explicit maintainer approval and ``BOSCH_HW_WRITE_OK=1``. It only proceeds when the
charge is idle (``stop``), always sends ``stop`` afterwards, and writes nothing else.
"""

from __future__ import annotations

import asyncio
import os

import aiohttp
import pytest
from pytest_socket import socket_allow_hosts

from custom_components.bosch_compress6000.commands import CommandPermissions, validate_command
from custom_components.bosch_compress6000.protocol import POINT_BY_KEY, WriteGroup
from custom_components.bosch_compress6000.runtime import build_writable_client

pytestmark = pytest.mark.hardware_write

ENV = (
    "BOSCH_HW_HOST",
    "BOSCH_HW_GATEWAY_PASSWORD",
    "BOSCH_HW_PRIVATE_PASSWORD",
    "BOSCH_HW_WRITE_OK",
)
OBSERVE_SECONDS = (5, 10, 15)


@pytest.mark.skipif(not all(os.environ.get(v) for v in ENV), reason="write test not approved")
async def test_extra_hot_water_start_then_stop(socket_enabled: None) -> None:
    socket_allow_hosts([os.environ["BOSCH_HW_HOST"]])
    point = POINT_BY_KEY["dhw_charge"]
    permissions = CommandPermissions(True, frozenset({WriteGroup.EXTRA_HOT_WATER}))
    async with aiohttp.ClientSession() as session:
        transport, client = build_writable_client(
            session,
            os.environ["BOSCH_HW_HOST"],
            os.environ["BOSCH_HW_GATEWAY_PASSWORD"],
            os.environ["BOSCH_HW_PRIVATE_PASSWORD"],
        )
        before = await client.read_point(point)
        print(f"before: {before.value}")
        assert before.value == "stop", "charge is not idle; refusing to start another"
        try:
            await transport.post_value(
                point.path, validate_command(point, before, "start", permissions)
            )
            for delay in OBSERVE_SECONDS:
                await asyncio.sleep(delay)
                reading = await client.read_point(point)
                print(f"after start +{delay}s: {reading.value}")
        finally:
            await transport.post_value(
                point.path, validate_command(point, before, "stop", permissions)
            )
        await asyncio.sleep(3)
        after = await client.read_point(point)
        print(f"after stop: {after.value}")
        assert after.value == "stop"
