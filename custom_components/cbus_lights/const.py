"""Constants for C-Bus Lights integration."""

DOMAIN = "cbus_lights"

# Configuration keys
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_CBUS_HOST = "cbus_host"
CONF_CBUS_PORT = "cbus_port"

# Default values
DEFAULT_CBUS_PORT = 20023
DEFAULT_MQTT_TOPIC = "cbus"

# MQTT Topics
MQTT_TOPIC_LIGHT_STATE = "cbus/light/{}/state"
MQTT_TOPIC_LIGHT_COMMAND = "cbus/light/{}/set"
MQTT_TOPIC_BUTTON_PRESS = "cbus/button/{}/press"

# C-Bus Groups (common Clipsal light group IDs)
CBUS_LIGHTING_GROUP = 56

# Device classes
DEVICE_CLASS_LIGHT = "light"
DEVICE_CLASS_SWITCH = "switch" 