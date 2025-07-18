"""Constants for the C-Bus MQTT Bridge integration."""

DOMAIN = "cbusmqtt"
NAME = "C-Bus MQTT Bridge"
VERSION = "1.0.0"

# Default values
DEFAULT_NAME = "C-Bus MQTT Bridge"
DEFAULT_PORT = 10001
DEFAULT_NETWORK = 254
DEFAULT_APPLICATION = 56
DEFAULT_POLL_INTERVAL = 30
DEFAULT_TIMEOUT = 5
DEFAULT_MAX_RETRIES = 3

# Configuration keys
CONF_INTERFACE_TYPE = "interface_type"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SERIAL_PORT = "serial_port"
CONF_NETWORK = "network"
CONF_APPLICATION = "application"
CONF_POLL_INTERVAL = "poll_interval"
CONF_TIMEOUT = "timeout"
CONF_MAX_RETRIES = "max_retries"
CONF_MONITORING_ENABLED = "monitoring_enabled"

# Interface types
INTERFACE_TCP = "tcp"
INTERFACE_SERIAL = "serial"
INTERFACE_PCI = "pci"

INTERFACE_TYPES = [INTERFACE_TCP, INTERFACE_SERIAL, INTERFACE_PCI]

# Supported device types
DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_SWITCH = "switch"
DEVICE_TYPE_FAN = "fan"
DEVICE_TYPE_COVER = "cover"
DEVICE_TYPE_SENSOR = "sensor"
DEVICE_TYPE_BINARY_SENSOR = "binary_sensor"

SUPPORTED_DEVICE_TYPES = [
    DEVICE_TYPE_LIGHT,
    DEVICE_TYPE_SWITCH,
    DEVICE_TYPE_FAN,
    DEVICE_TYPE_COVER,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_BINARY_SENSOR,
]

# Services
SERVICE_SYNC_DEVICE = "sync_device"
SERVICE_REFRESH_DEVICES = "refresh_devices"
SERVICE_SET_LEVEL = "set_level"
SERVICE_RAMP_TO_LEVEL = "ramp_to_level"

# Attributes
ATTR_GROUP = "group"
ATTR_LEVEL = "level"
ATTR_RAMP_TIME = "ramp_time"

# Events
EVENT_CBUS_STATE_CHANGED = "cbus_state_changed"
EVENT_CBUS_DEVICE_DISCOVERED = "cbus_device_discovered"

# Device info
DEVICE_MANUFACTURER = "Clipsal"
DEVICE_MODEL = "C-Bus Device"

# Update intervals
UPDATE_INTERVAL = 10  # seconds
FAST_UPDATE_INTERVAL = 1  # seconds for recently changed devices 