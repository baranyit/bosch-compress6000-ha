"""Home Assistant fixtures: the real integration code behind an in-process gateway double."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from functools import partial
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST, CONF_NAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bosch_compress6000 import runtime
from custom_components.bosch_compress6000.const import (
    CONF_CLAIM_LEGACY,
    CONF_GATEWAY_PASSWORD,
    CONF_POLL_INTERVAL,
    CONF_PRIVATE_PASSWORD,
    CONF_WRITE_ENABLED,
    CONF_WRITE_GROUPS,
    DOMAIN,
)

from ..fakes import GATEWAY_PASSWORD, PRIVATE_PASSWORD, FakeGateway, VirtualClock

HOST = "192.0.2.20"  # TEST-NET-1, never reached: the backend is the in-process double
NOW = datetime(2026, 11, 9, 15, 7, tzinfo=UTC)  # the last complete hour is 14:00


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let HA load custom_components/bosch_compress6000 in every HA test."""


@pytest.fixture(autouse=True)
def _fast_debounce() -> Iterator[None]:
    with patch("custom_components.bosch_compress6000.COMMAND_DEBOUNCE", 0.05):
        yield


@pytest.fixture(autouse=True)
def _fixed_clock() -> Iterator[None]:
    with patch(
        "custom_components.bosch_compress6000.coordinator.Km200Coordinator.now",
        return_value=NOW,
    ):
        yield


@pytest.fixture
def gateway() -> Iterator[FakeGateway]:
    fake = FakeGateway()
    clock = VirtualClock()
    read: Callable[..., Any] = partial(runtime.build_client, backend=fake, clock=clock)
    write: Callable[..., Any] = partial(runtime.build_writable_client, backend=fake, clock=clock)
    with (
        patch("custom_components.bosch_compress6000.build_client", read),
        patch("custom_components.bosch_compress6000.build_writable_client", write),
        patch("custom_components.bosch_compress6000.config_flow.build_client", read),
    ):
        yield fake


def make_entry(**options: Any) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="heatpump",
        unique_id="test-gateway-uuid",
        data={
            CONF_NAME: "heatpump",
            CONF_HOST: HOST,
            CONF_GATEWAY_PASSWORD: GATEWAY_PASSWORD,
            CONF_PRIVATE_PASSWORD: PRIVATE_PASSWORD,
        },
        options={
            CONF_POLL_INTERVAL: 120,
            CONF_WRITE_ENABLED: False,
            CONF_WRITE_GROUPS: [],
            CONF_CLAIM_LEGACY: True,
            **options,
        },
    )


@pytest.fixture
def entry() -> MockConfigEntry:
    return make_entry()
