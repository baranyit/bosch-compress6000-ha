from __future__ import annotations

import asyncio

import pytest

from custom_components.bosch_compress6000.commands import (
    CommandExecutor,
    CommandPermissions,
    validate_command,
)
from custom_components.bosch_compress6000.errors import CommandRejectedError, RejectReason
from custom_components.bosch_compress6000.models import Reading
from custom_components.bosch_compress6000.protocol import POINT_BY_KEY, WriteGroup
from custom_components.bosch_compress6000.write_transport import WritableTransport

from .fakes import KEY, FakeGateway, VirtualClock

ALL = CommandPermissions(True, frozenset(WriteGroup))
CHARGE = Reading("stop", allowed=("start", "stop"), writeable=True)
TEMPERATURE = Reading(55.0, "C", minimum=40.0, maximum=65.0, writeable=True)


def reason(
    point: str, reading: Reading | None, value: float | str, perms: CommandPermissions
) -> str:
    with pytest.raises(CommandRejectedError) as excinfo:
        validate_command(POINT_BY_KEY[point], reading, value, perms)
    return excinfo.value.reason


def test_write_mode_off_by_default() -> None:
    assert (
        reason("dhw_charge", CHARGE, "start", CommandPermissions()) == RejectReason.WRITE_DISABLED
    )


def test_groups_are_separate_opt_ins() -> None:
    only_hot_water = CommandPermissions(True, frozenset({WriteGroup.HOT_WATER}))
    assert reason("dhw_charge", CHARGE, "start", only_hot_water) == RejectReason.GROUP_NOT_ALLOWED
    assert (
        validate_command(POINT_BY_KEY["dhw_temperature_high"], TEMPERATURE, 50.0, only_hot_water)
        == 50.0
    )


def test_read_only_points_can_never_be_written() -> None:
    reading = Reading(4.3, "C", writeable=True)
    assert reason("outdoor_temperature", reading, 1.0, ALL) == RejectReason.NOT_WRITEABLE


def test_device_must_say_writeable_and_have_a_reading() -> None:
    assert reason("dhw_charge", Reading("stop", allowed=("start", "stop")), "start", ALL) == (
        RejectReason.NOT_WRITEABLE
    )
    assert reason("dhw_charge", None, "start", ALL) == RejectReason.UNKNOWN_POINT


def test_enum_values_are_checked_against_the_device_list() -> None:
    assert validate_command(POINT_BY_KEY["dhw_charge"], CHARGE, "start", ALL) == "start"
    assert reason("dhw_charge", CHARGE, "boost", ALL) == RejectReason.INVALID_VALUE
    assert reason("dhw_charge", CHARGE, 1.0, ALL) == RejectReason.INVALID_VALUE


def test_numbers_are_range_checked_and_never_rounded() -> None:
    point = POINT_BY_KEY["dhw_temperature_high"]
    assert validate_command(point, TEMPERATURE, 52.25, ALL) == 52.25
    assert reason("dhw_temperature_high", TEMPERATURE, 39.9, ALL) == RejectReason.OUT_OF_RANGE
    assert reason("dhw_temperature_high", TEMPERATURE, 65.1, ALL) == RejectReason.OUT_OF_RANGE
    assert (
        reason("dhw_temperature_high", TEMPERATURE, float("nan"), ALL) == RejectReason.INVALID_VALUE
    )
    assert reason("dhw_temperature_high", TEMPERATURE, "hot", ALL) == RejectReason.INVALID_VALUE


class Harness:
    def __init__(self, debounce: float = 0.02) -> None:
        self.gateway = FakeGateway()
        transport = WritableTransport(KEY, self.gateway, VirtualClock(), 0.0)
        self.read_backs: list[str] = []
        self.changes = 0

        async def read_back(point: object) -> None:
            self.read_backs.append(point.key)  # type: ignore[attr-defined]

        self.executor = CommandExecutor(
            transport,
            ALL,
            debounce=debounce,
            read_back=read_back,
            on_change=self._changed,
        )

    def _changed(self) -> None:
        self.changes += 1


async def test_nothing_is_sent_before_the_debounce_ends() -> None:
    h = Harness(debounce=0.05)
    h.executor.submit(POINT_BY_KEY["dhw_charge"], "start")
    await asyncio.sleep(0)
    assert h.gateway.posts == []
    assert h.executor.optimistic("dhw_charge") == "start"
    await asyncio.sleep(0.12)
    assert h.gateway.posts == [("dhwCircuits/dhw1/charge", "start")]
    assert h.read_backs == ["dhw_charge"]
    assert h.executor.optimistic("dhw_charge") is None  # the read-back decides afterwards
    await h.executor.close()


async def test_latest_value_wins_and_one_write_per_point() -> None:
    h = Harness()
    point = POINT_BY_KEY["dhw_temperature_high"]
    for value in (50.0, 51.0, 52.0):
        h.executor.submit(point, value)
    await asyncio.sleep(0.1)
    assert h.gateway.posts == [("dhwCircuits/dhw1/temperatureLevels/high", 52.0)]
    await h.executor.close()


async def test_close_drops_unwritten_commands_without_replay() -> None:
    h = Harness(debounce=0.2)
    h.executor.submit(POINT_BY_KEY["dhw_charge"], "start")
    await h.executor.close()
    await asyncio.sleep(0.3)
    assert h.gateway.posts == [] and h.executor.optimistic("dhw_charge") is None


async def test_a_failed_write_is_reported_and_not_retried() -> None:
    h = Harness()
    h.gateway.fail_paths.add("dhwCircuits/dhw1/charge")
    h.executor.submit(POINT_BY_KEY["dhw_charge"], "start")
    await asyncio.sleep(0.1)
    assert h.gateway.posts == [] and h.read_backs == []
    assert len(h.executor.errors) == 1
    assert h.executor.optimistic("dhw_charge") is None
    await asyncio.sleep(0.1)
    assert h.gateway.posts == []
    await h.executor.close()
