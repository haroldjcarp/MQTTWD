# C-Bus Lights Integration for Home Assistant

A Home Assistant custom integration for controlling Clipsal C-Bus lights via MQTT.

## Features

- **Light Control**: Turn lights on/off and control brightness
- **MQTT Integration**: Communicates with C-Bus system via MQTT
- **Button Press Handling**: Returns light state when physical buttons are pressed
- **Real-time State Updates**: Lights reflect current state in Home Assistant

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations" 
3. Click the three dots menu → "Custom repositories"
4. Add repository URL: `https://github.com/haroldjcarp/MQTTWD`
5. Select "Integration" category
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy the `cbus_lights` folder to your `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **"Add Integration"**
3. Search for **"C-Bus Lights"**
4. Configure:
   - **C-Bus Host**: IP address of your C-Bus CNI (e.g., `192.168.1.100`)
   - **C-Bus Port**: Port number (default: `20023`)
   - **MQTT Topic**: Base MQTT topic (default: `cbus`)

## MQTT Topics

The integration uses the following MQTT topic structure:

- **State**: `cbus/light/{light_id}/state`
- **Commands**: `cbus/light/{light_id}/set`
- **Button Press**: `cbus/button/{light_id}/press`

## Example Usage

When you press a physical C-Bus button, the integration will:
1. Detect the button press via MQTT
2. Query the current light state
3. Return the state information (on/off, brightness)
4. Update Home Assistant entities

## Requirements

- Home Assistant 2023.1.0 or later
- MQTT broker configured in Home Assistant
- C-Bus CNI (network interface) connected to your C-Bus system

## Support

- [Issues](https://github.com/haroldjcarp/MQTTWD/issues)
- [Discussions](https://github.com/haroldjcarp/MQTTWD/discussions)

## License

This project is licensed under the MIT License. 