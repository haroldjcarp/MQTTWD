"""Constants for C-Bus Lights integration."""

DOMAIN = "cbus_lights"

# Configuration keys - following ha-cbus2mqtt pattern
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_CBUS_HOST = "cbus_host" 
CONF_CBUS_PORT = "cbus_port"
CONF_MQTT_USER = "mqtt_user"
CONF_MQTT_PASSWORD = "mqtt_password"
CONF_MQTT_BROKER = "mqtt_broker"

# Default values - matching ha-cbus2mqtt defaults
DEFAULT_CBUS_PORT = 10001
DEFAULT_MQTT_TOPIC = "cbus"
DEFAULT_MQTT_BROKER = "core-mosquitto"

# MQTT Topics - following cmqttd patterns from ha-cbus2mqtt
MQTT_TOPIC_LIGHT_STATE = "cbus/read/{}/{}/{}/state"          # network/app/group/state
MQTT_TOPIC_LIGHT_LEVEL = "cbus/read/{}/{}/{}/level"          # network/app/group/level  
MQTT_TOPIC_LIGHT_COMMAND = "cbus/write/{}/{}/{}/switch"      # network/app/group/switch
MQTT_TOPIC_LIGHT_RAMP = "cbus/write/{}/{}/{}/ramp"           # network/app/group/ramp
MQTT_TOPIC_GETALL = "cbus/write/{}/{}//getall"               # network/app//getall
MQTT_TOPIC_GETTREE = "cbus/write/{}///gettree"               # network///gettree

# Home Assistant Discovery - following ha-cbus2mqtt pattern
DISCOVERY_PREFIX = "homeassistant"
DISCOVERY_LIGHT = f"{DISCOVERY_PREFIX}/light"
DISCOVERY_SENSOR = f"{DISCOVERY_PREFIX}/sensor"

# C-Bus Default Values - standard C-Bus configuration
CBUS_DEFAULT_NETWORK = 254
CBUS_DEFAULT_APPLICATION = 56  # Lighting application
CBUS_LIGHTING_GROUP = 56

# Device classes
DEVICE_CLASS_LIGHT = "light"
DEVICE_CLASS_SWITCH = "switch"

# Update intervals
UPDATE_INTERVAL = 30  # seconds
DISCOVERY_INTERVAL = 60  # seconds
