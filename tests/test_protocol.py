from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from custom_components.bosch_compress6000.errors import (
    MalformedResponseError,
    PointUnavailableError,
)
from custom_components.bosch_compress6000.protocol import (
    ENERGY_POINTS,
    POINTS,
    WriteGroup,
    last_complete_hour,
    parse_hour_sample,
    parse_reading,
    recording_params,
)


def test_parse_numeric_and_text_readings() -> None:
    number = parse_reading(
        json.dumps(
            {"value": 21.5, "unitOfMeasure": "C", "minValue": 5, "maxValue": 30, "writeable": 1}
        )
    )
    assert (number.value, number.unit, number.minimum, number.maximum, number.writeable) == (
        21.5,
        "C",
        5.0,
        30.0,
        True,
    )
    text = parse_reading(json.dumps({"value": "stop", "allowedValues": ["start", "stop"]}))
    assert text.value == "stop" and text.allowed == ("start", "stop") and not text.writeable


@pytest.mark.parametrize("body", ["nope", "[]", '{"value": [1]}', '{"value": true}'])
def test_malformed_readings(body: str) -> None:
    with pytest.raises(MalformedResponseError):
        parse_reading(body)


def test_a_resource_without_value_is_not_a_point() -> None:
    with pytest.raises(PointUnavailableError):
        parse_reading('{"id": "/heatSources", "references": []}')


def test_hour_sample_is_the_average_rounded_to_two_decimals() -> None:
    records = [{"y": 0, "c": 0}] * 24
    records[5] = {"y": 10.0, "c": 3.0}
    body = json.dumps({"recording": records})
    assert parse_hour_sample(body, 5) == 3.33


def test_an_hour_without_samples_is_none_never_zero() -> None:
    records = [{"y": 0, "c": 0}] * 24
    records[7] = {"y": 0, "c": 4}
    body = json.dumps({"recording": records})
    assert parse_hour_sample(body, 3) is None  # c == 0: no data, must not become 0.0
    assert parse_hour_sample(body, 7) == 0.0  # real zero consumption
    assert parse_hour_sample(body, 99) is None


def test_recording_must_have_a_sample_list() -> None:
    with pytest.raises(MalformedResponseError):
        parse_hour_sample('{"recording": 3}', 0)


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        ((2026, 11, 9, 15, 7), (2026, 11, 9, 14)),
        ((2026, 11, 9, 15, 5), (2026, 11, 9, 14)),
        ((2026, 11, 9, 15, 4), (2026, 11, 9, 13)),
        ((2026, 11, 9, 0, 2), (2026, 11, 8, 22)),
    ],
)
def test_last_complete_hour_respects_the_grace_period(
    now: tuple[int, ...], expected: tuple[int, ...]
) -> None:
    assert last_complete_hour(datetime(*now, tzinfo=UTC)) == datetime(*expected, tzinfo=UTC)


def test_recording_params_use_the_day_of_the_hour() -> None:
    assert recording_params(datetime(2026, 11, 8, 22, tzinfo=UTC)) == {"interval": "2026-11-08"}


def test_catalog_is_consistent() -> None:
    keys = [p.key for p in POINTS] + [p.key for p in ENERGY_POINTS]
    assert len(keys) == len(set(keys))
    paths = [p.path for p in POINTS] + [p.path for p in ENERGY_POINTS]
    assert len(paths) == len(set(paths))
    assert not any(path.startswith("/") for path in paths)
    # Writable resources are an explicit, small list (one switch, two numbers, two selects).
    assert sorted(p.key for p in POINTS if p.group is not None) == [
        "dhw_charge",
        "dhw_operation_mode",
        "dhw_temperature_high",
        "heating_manual_setpoint",
        "heating_operation_mode",
    ]
    assert {p.group for p in POINTS if p.key == "dhw_charge"} == {WriteGroup.EXTRA_HOT_WATER}
