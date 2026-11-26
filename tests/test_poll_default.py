from custom_components.bosch_compress6000.const import DEFAULT_POLL_INTERVAL, MIN_POLL_INTERVAL


def test_default_poll_interval_is_one_minute() -> None:
    assert DEFAULT_POLL_INTERVAL == 60
    assert MIN_POLL_INTERVAL <= DEFAULT_POLL_INTERVAL
