"""Constants. Home Assistant free, so the core modules can import it."""

from __future__ import annotations

DOMAIN = "bosch_compress6000"

CONF_GATEWAY_PASSWORD = "gateway_password"
CONF_PRIVATE_PASSWORD = "private_password"
CONF_POLL_INTERVAL = "poll_interval"
CONF_WRITE_ENABLED = "write_enabled"
CONF_WRITE_GROUPS = "write_groups"
CONF_CLAIM_LEGACY = "claim_legacy_entities"

DEFAULT_NAME = "heatpump"
DEVICE_MANUFACTURER = "Bosch"
DEVICE_MODEL = "Compress6000"

DEFAULT_POLL_INTERVAL = 120
MAX_POLL_INTERVAL = 3600
MIN_POLL_INTERVAL = 30

# The gateway is a small embedded web server: one request at a time, with a pause in between.
REQUEST_SPACING = 0.5
REQUEST_TIMEOUT = 10.0
USER_AGENT = "TeleHeater"

# Energy recordings are hourly. The previous hour is read this long after it ended (HomeGate
# read at minute 5), then once per hour.
ENERGY_GRACE_MINUTES = 5

# Explicit user commands are debounced, then written once (latest value wins per point).
COMMAND_DEBOUNCE = 1.5

# unique_id of the entities the retired HomeGate MQTT bridge provided. They are kept so the
# history and the Energy dashboard continue; the integration claims the old registry entries.
LEGACY_MQTT_UNIQUE_IDS: dict[str, str] = {
    "total_energy": "bosch_energymonitoring_total",
    "compressor_energy": "bosch_energymonitoring_compressor",
    "eheater_energy": "bosch_energymonitoring_eheater",
    "outdoor_temperature": "bosch_outdoor_temperature",
}
