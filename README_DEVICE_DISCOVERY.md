# C-Bus Device Discovery Implementation

## Overview

This implementation adds **automatic device discovery** to your C-Bus integration, allowing the system to **query your C-Bus network directly** to find devices and their actual names/labels, rather than using hardcoded device lists.

## How It Works

### 1. **Device Discovery Process**

The system now **pings your C-Bus CNI** to discover devices using these methods:

1. **Active Group Scanning**: Quickly scans common group ranges (1-50, 100-150, 200-255) to find responsive devices
2. **Device Information Query**: For each found device, queries:
   - Device name/label (using DLT - Dynamic Labelling Technology)
   - Device type (light, switch, fan, etc.)
   - Dimming capability
   - Current state/level
3. **Label Resolution**: Attempts multiple methods to get device names:
   - DLT label queries (`get label` commands)
   - Alternative label queries (`info` commands)
   - Falls back to generic names if queries fail

### 2. **Protocol Commands Used**

The implementation uses actual C-Bus protocol commands:

```bash
# Device level queries
get lighting <group>

# Label queries (DLT)
get <application> <group> label
info <application> <group>

# Device scanning
g<application><group>  # Query group status
```

### 3. **Device Types and Detection**

The system automatically detects:
- **Lights**: Dimmable and non-dimmable lighting
- **Switches**: On/off switching devices
- **Fans**: Variable speed fans
- **Sensors**: Temperature, motion, etc.

## Features

### ✅ **Real Device Names**
- Queries actual device labels from your C-Bus system
- Uses DLT (Dynamic Labelling Technology) when available
- Falls back to generic names if labels aren't found

### ✅ **Smart Discovery**
- Scans only common group ranges initially for speed
- Performs full scan if no devices found
- Detects device capabilities (dimming, switching, etc.)

### ✅ **Fallback Support**
- Works even if C-Bus CNI is not accessible
- Creates sample devices for testing
- Graceful error handling

### ✅ **Home Assistant Integration**
- Automatically creates Home Assistant light entities
- Proper device information and areas
- Discovery services for manual scanning

## Usage

### 1. **Automatic Discovery** (Default)

The integration automatically discovers devices when you add it to Home Assistant:

```yaml
# Home Assistant will automatically:
# 1. Connect to your C-Bus CNI
# 2. Scan for active devices
# 3. Query device names and capabilities
# 4. Create appropriate entities
```

### 2. **Manual Discovery Services**

You can manually trigger discovery using Home Assistant services:

#### Discover Devices
```yaml
service: cbus_lights.discover_devices
data:
  start_group: 1
  end_group: 50
```

#### Scan Active Groups
```yaml
service: cbus_lights.scan_active_groups
```

#### Query Specific Device
```yaml
service: cbus_lights.query_device_info
data:
  group: 5
```

#### Refresh Device Names
```yaml
service: cbus_lights.refresh_device_names
```

### 3. **Testing Discovery**

Run the test script to validate discovery:

```bash
python test_discovery.py discovery
```

## Configuration

### C-Bus CNI Settings

Update your configuration with your C-Bus CNI details:

```yaml
# Integration configuration
host: "192.168.1.100"  # Your C-Bus CNI IP
port: 10001             # C-Bus CNI port (usually 10001)
network: 254            # C-Bus network number
application: 56         # Lighting application (56 = 0x38)
```

### Discovery Settings

```python
# Device discovery configuration
discovery:
  enabled: true
  auto_discovery: true
  scan_ranges:
    - [1, 50]      # Common lighting groups
    - [100, 150]   # Extended lighting
    - [200, 255]   # Special functions
  timeout: 5       # Query timeout in seconds
  max_retries: 3   # Maximum retry attempts
```

## What You'll See

### Before (Hardcoded)
```
✗ Living Room (hardcoded)
✗ Kitchen (hardcoded)  
✗ Bedroom (hardcoded)
```

### After (Discovered)
```
✓ Master Bedroom Ceiling Light (Group 1)
✓ Kitchen Downlights (Group 2)
✓ Living Room Table Lamp (Group 3)
✓ Bathroom Exhaust Fan (Group 12)
✓ Outdoor Security Light (Group 20)
```

## Error Handling

The system includes comprehensive error handling:

1. **Connection Failures**: Falls back to sample devices
2. **Query Timeouts**: Uses generic names with group numbers
3. **Protocol Errors**: Gracefully handles unsupported commands
4. **Discovery Failures**: Creates basic devices for testing

## Supported C-Bus Interfaces

- **5500CN/5500CN2**: Ethernet C-Bus Network Interface
- **5500PC**: Serial C-Bus PC Interface  
- **5500PCU**: USB C-Bus PC Interface

## Technical Details

### Device Information Structure
```python
{
    'group': 1,
    'name': 'Master Bedroom Ceiling Light',
    'type': 'light',
    'dimmable': True,
    'current_level': 128,
    'discovered': True,
    'last_seen': timestamp
}
```

### Discovery Methods
1. **scan_active_groups()**: Fast scan for responsive devices
2. **discover_devices()**: Full discovery with name resolution
3. **query_device_info()**: Detailed info for specific device
4. **get_device_label()**: Name/label resolution

## Troubleshooting

### No Devices Found
- Check C-Bus CNI IP address and port
- Verify network connectivity to CNI
- Ensure C-Bus application number is correct (usually 56)

### Generic Names Only
- C-Bus system may not have device labels configured
- DLT (Dynamic Labelling Technology) may not be available
- Use C-Bus Toolkit to configure device labels

### Connection Errors
- Verify CNI is accessible on network
- Check firewall settings
- Ensure CNI is not in use by another application

## Log Examples

```
2024-01-15 10:30:00 - cbus.interface - INFO - Starting device discovery scan from group 1 to 50
2024-01-15 10:30:01 - cbus.interface - INFO - Found 5 active groups: [1, 2, 3, 12, 20]
2024-01-15 10:30:02 - cbus.interface - INFO - Discovered device: Master Bedroom Ceiling Light (Group 1)
2024-01-15 10:30:03 - cbus.interface - INFO - Discovered device: Kitchen Downlights (Group 2)
2024-01-15 10:30:04 - cbus.interface - INFO - Device discovery complete. Found 5 devices.
```

## Next Steps

1. **Configure your C-Bus CNI IP** in the integration settings
2. **Add device labels** in your C-Bus system using C-Bus Toolkit
3. **Test discovery** using the provided test script
4. **Use discovery services** to manually scan for new devices

The integration now **truly discovers your C-Bus devices** rather than using hardcoded lists! 🎉 