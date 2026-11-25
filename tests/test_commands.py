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
from custom_components.bosch_compress6000.protocol import (
    POINT_BY_KEY,
    Confidence,
    Point,
    WriteGroup,
)
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


def test_a_group_is_a_separate_opt_in() -> None:
    no_group = CommandPermissions(True, frozenset())
    assert reason("dhw_charge", CHARGE, "start", no_group) == RejectReason.GROUP_NOT_ALLOWED


@pytest.mark.parametrize(
    "key",
    [
        "dhw_operation_mode",
        "dhw_temperature_high",
        "heating_operation_mode",
        "heating_manual_setpoint",
    ],
)
def test_unverified_settings_can_never_be_written(key: str) -> None:
    reading = Reading(45.0, "C", 30.0, 43.0, writeable=True)
    assert reason(key, reading, 40.0, ALL) == RejectReason.NOT_WRITEABLE


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
    # No catalog point is a number any more; the numeric path is kept for a future group.
    point = Point("test_number", "test/number", Confidence.STANDARD, WriteGroup.EXTRA_HOT_WATER)
    assert validate_command(point, TEMPERATURE, 52.25, ALL) == 52.25
    for value, expected in (
        (39.9, RejectReason.OUT_OF_RANGE),
        (65.1, RejectReason.OUT_OF_RANGE),
        (float("nan"), RejectReason.INVALID_VALUE),
        ("hot", RejectReason.INVALID_VALUE),
    ):
        with pytest.raises(CommandRejectedError) as err:
            validate_command(point, TEMPERATURE, value, ALL)
        assert err.value.reason == expected


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
    point = POINT_BY_KEY["dhw_charge"]
    for value in ("start", "stop", "start"):
        h.executor.submit(point, value)
    await asyncio.sleep(0.1)
    assert h.gateway.posts == [("dhwCircuits/dhw1/charge", "start")]
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
