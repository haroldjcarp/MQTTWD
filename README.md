# CBus MQTT Bridge - Improved Version

An improved C-Bus to MQTT bridge for Home Assistant with better state tracking and bidirectional synchronization.

## Features

- ✅ **Accurate State Tracking**: Actively monitors C-Bus devices for real-time state updates
- ✅ **Bidirectional Sync**: Full two-way communication between C-Bus and Home Assistant
- ✅ **Auto-Discovery**: Automatic device discovery in Home Assistant via MQTT
- ✅ **Multiple Interface Support**: Works with PCI, CNI, and serial interfaces
- ✅ **Robust Error Handling**: Comprehensive error handling and recovery
- ✅ **Easy Configuration**: Simple YAML configuration
- ✅ **Docker Support**: Ready-to-use Docker container and Home Assistant add-on
- ✅ **Comprehensive Logging**: Detailed logging for troubleshooting

## Key Improvements Over Existing Solutions

### 1. State Accuracy
- **Real-time monitoring** of C-Bus device states
- **Polling fallback** when event monitoring fails
- **State validation** to ensure consistency
- **Conflict resolution** for state mismatches

### 2. Better Communication
- **Asynchronous processing** for better performance
- **Message queuing** to handle high-frequency updates
- **Connection resilience** with automatic reconnection
- **Heartbeat monitoring** for connection health

### 3. Enhanced Configuration
- **Device templates** for common C-Bus devices
- **Automatic device mapping** from C-Bus project files
- **Flexible addressing** (group addresses, device names)
- **Custom device properties** (icons, areas, etc.)

## Quick Start

### Using Docker

```bash
# Create configuration directory
mkdir -p ./config

# Create basic configuration
cat > ./config/config.yaml << EOF
cbus:
  interface: tcp
  host: 192.168.1.100
  port: 10001
  
mqtt:
  broker: localhost
  port: 1883
  username: homeassistant
  password: your_password
  
discovery:
  enabled: true
  prefix: homeassistant
EOF

# Run container
docker run -d \
  --name cbusmqtt \
  -v ./config:/config \
  --network host \
  cbusmqtt:latest
```

### Using Python

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bridge
python main.py --config config/config.yaml
```

## Configuration

### Basic Configuration

```yaml
# config/config.yaml
cbus:
  interface: tcp          # tcp, serial, or pci
  host: 192.168.1.100    # For TCP/CNI interfaces
  port: 10001            # Default CNI port
  # serial_port: /dev/ttyUSB0  # For serial interfaces
  
  # Network configuration
  network: 254           # C-Bus network number
  application: 56        # Lighting application (56 = 0x38)
  
  # State monitoring
  monitoring:
    enabled: true
    poll_interval: 30    # Poll devices every 30 seconds
    max_retries: 3
    timeout: 5
    
mqtt:
  broker: localhost
  port: 1883
  username: homeassistant
  password: your_password
  
  # MQTT topics
  topics:
    command: cbus/command
    state: cbus/state
    
  # Connection settings
  keepalive: 60
  reconnect_delay: 5
  
discovery:
  enabled: true
  prefix: homeassistant
  
logging:
  level: INFO
  file: /var/log/cbusmqtt.log
```

### Device Configuration

```yaml
# config/devices.yaml
devices:
  # Group address based configuration
  - group: 1
    name: "Living Room Main Light"
    type: light
    area: "Living Room"
    icon: "mdi:lightbulb"
    
  - group: 2
    name: "Kitchen Downlights"
    type: light
    area: "Kitchen"
    dimmable: true
    
  - group: 10
    name: "Bathroom Exhaust Fan"
    type: fan
    area: "Bathroom"
    
  # Device templates for common setups
  templates:
    - name: "dimmable_light"
      type: light
      dimmable: true
      fade_time: 2
      
    - name: "switch"
      type: switch
      dimmable: false
```

## Architecture

### Core Components

1. **CBus Interface** (`cbus/interface.py`)
   - Handles communication with C-Bus PCI/CNI
   - Manages connection states and error recovery
   - Provides abstraction for different interface types

2. **State Manager** (`cbus/state_manager.py`)
   - Tracks device states in real-time
   - Handles state validation and conflict resolution
   - Manages polling and event-based updates

3. **MQTT Bridge** (`mqtt/bridge.py`)
   - Manages MQTT communication
   - Handles Home Assistant discovery
   - Processes commands and publishes states

4. **Device Manager** (`devices/manager.py`)
   - Manages device configurations
   - Handles device discovery and mapping
   - Provides device-specific behavior

### State Synchronization Flow

```
C-Bus Device → C-Bus Interface → State Manager → MQTT Bridge → Home Assistant
     ↑                                                              ↓
     ←─────────── Command Processing ←─────────────────────────────
```

## Supported Devices

- **Lights**: Dimmable and non-dimmable lighting
- **Fans**: Ceiling fans and exhaust fans
- **Switches**: General purpose switching
- **Sensors**: Motion, temperature, and other sensors
- **Blinds**: Motorized blinds and curtains

## Installation

### Home Assistant Add-on

1. Add the repository to your Home Assistant add-on store
2. Install the "CBus MQTT Bridge" add-on
3. Configure the add-on with your C-Bus settings
4. Start the add-on

### Manual Installation

1. Clone this repository
2. Install Python dependencies: `pip install -r requirements.txt`
3. Copy configuration templates and modify for your setup
4. Run: `python main.py`

## Troubleshooting

### Common Issues

1. **Lights show wrong state**
   - Check `monitoring.enabled` is `true`
   - Verify `poll_interval` is appropriate
   - Check C-Bus interface connection

2. **Devices not discovered**
   - Verify MQTT discovery is enabled
   - Check MQTT broker connection
   - Ensure device configuration is correct

3. **Connection issues**
   - Check C-Bus interface settings
   - Verify network connectivity
   - Review logs for error messages

### Debug Mode

```bash
# Enable debug logging
python main.py --config config/config.yaml --debug

# Or modify config.yaml
logging:
  level: DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 