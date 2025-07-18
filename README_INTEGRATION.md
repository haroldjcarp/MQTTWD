# C-Bus MQTT Bridge for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/yourusername/ha-cbusmqtt.svg)](https://github.com/yourusername/ha-cbusmqtt/releases)
[![License](https://img.shields.io/github/license/yourusername/ha-cbusmqtt.svg)](LICENSE)

An improved C-Bus to MQTT bridge for Home Assistant with accurate state tracking and GUI configuration.

## Features

- 🎯 **Accurate State Tracking**: Real-time monitoring with polling fallback
- 🔄 **Bidirectional Sync**: Full two-way communication between C-Bus and Home Assistant
- 🖥️ **GUI Configuration**: Easy setup through Home Assistant UI
- 🔧 **Multiple Interface Support**: TCP/CNI, Serial, and PCI connections
- 📱 **Auto-Discovery**: Automatic device discovery and configuration
- 🛠️ **Custom Services**: Advanced C-Bus control services

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/yourusername/ha-cbusmqtt`
6. Select "Integration" as category
7. Click "Add"
8. Find "C-Bus MQTT Bridge" in the list and click "Install"
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/yourusername/ha-cbusmqtt/releases)
2. Extract the contents to your `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "C-Bus MQTT Bridge"
4. Follow the configuration wizard:
   - Select interface type (TCP/CNI, Serial, or PCI)
   - Enter connection details
   - Configure monitoring options

### Interface Types

#### TCP/CNI Interface
- **Host**: IP address of your C-Bus CNI
- **Port**: Default is 10001
- **Network**: C-Bus network number (default: 254)
- **Application**: Lighting application (default: 56)

#### Serial Interface
- **Serial Port**: Path to serial device (e.g., `/dev/ttyUSB0`)
- **Network**: C-Bus network number (default: 254)
- **Application**: Lighting application (default: 56)

#### PCI Interface
- **Serial Port**: Path to PCI device (e.g., `/dev/ttyUSB0`)
- **Network**: C-Bus network number (default: 254)
- **Application**: Lighting application (default: 56)

### Advanced Options

- **Enable Monitoring**: Real-time state monitoring (recommended)
- **Poll Interval**: How often to poll devices (30 seconds default)
- **Timeout**: Connection timeout (5 seconds default)
- **Max Retries**: Maximum connection retries (3 default)

## Supported Devices

The integration automatically discovers C-Bus devices and creates appropriate Home Assistant entities:

- **Lights**: Dimmable and non-dimmable lighting
- **Switches**: General purpose switching
- **Fans**: Ceiling fans with speed control

## Services

The integration provides several custom services for advanced control:

### `cbusmqtt.sync_device`
Sync a specific C-Bus device state
- **group**: C-Bus group number (0-255)

### `cbusmqtt.refresh_devices`
Refresh all C-Bus devices (no parameters)

### `cbusmqtt.set_level`
Set a C-Bus device to a specific level
- **group**: C-Bus group number (0-255)
- **level**: Level to set (0-255)

### `cbusmqtt.ramp_to_level`
Ramp a C-Bus device to a specific level over time
- **group**: C-Bus group number (0-255)
- **level**: Level to ramp to (0-255)
- **ramp_time**: Time to ramp in seconds (optional)

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check network connectivity to C-Bus interface
   - Verify IP address and port for TCP/CNI
   - Ensure serial device is accessible for Serial/PCI

2. **Devices Not Discovered**
   - Turn devices on/off to trigger discovery
   - Check monitoring is enabled
   - Verify network and application settings

3. **State Not Updating**
   - Ensure monitoring is enabled
   - Check poll interval setting
   - Verify C-Bus interface is responding

### Debug Logging

Enable debug logging to troubleshoot issues:

```yaml
logger:
  default: warning
  logs:
    custom_components.cbusmqtt: debug
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- [Issues](https://github.com/yourusername/ha-cbusmqtt/issues)
- [Discussions](https://github.com/yourusername/ha-cbusmqtt/discussions)

## Acknowledgments

- Home Assistant community for platform guidelines
- C-Bus protocol documentation
- Existing cbusmqtt implementations for inspiration 