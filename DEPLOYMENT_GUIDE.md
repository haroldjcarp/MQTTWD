# C-Bus Integration Deployment Guide

## ✅ Local Testing Complete

The integration has been locally tested and validated. All core patterns follow the proven **ha-cbus2mqtt** approach.

## 🚀 Deployment to Home Assistant

### Method 1: Using ha-cbus2mqtt Add-on (Recommended)

Since you already have the ha-cbus2mqtt add-on, configure it first:

1. **In Home Assistant**: Settings → Add-ons → cbus2mqtt
2. **Configuration**:
   ```yaml
   mqtt_broker_address: core-mosquitto
   mqtt_user: pai
   mqtt_password: pai
   tcp_or_serial: "Use a IP connection to CBUS"
   cbus_connection_string: "192.168.0.50:10001"
   ```
3. **Save and Restart** the add-on
4. **Check logs** for successful connection

### Method 2: Deploy Custom Integration

1. **Copy Integration Files**:
   ```
   # From this project
   custom_components/cbus_lights/
   
   # To Home Assistant
   /config/custom_components/cbus_lights/
   ```

2. **Restart Home Assistant**

3. **Add Integration**:
   - Settings → Devices & Services → Add Integration
   - Search: "C-Bus Lights"
   - Configure with your settings (pre-filled):
     - C-Bus Host: `192.168.0.50`
     - C-Bus Port: `10001`
     - MQTT Broker: `core-mosquitto`
     - MQTT User: `pai`
     - MQTT Password: `pai`

## 🔧 Testing in Home Assistant

### 1. Services Testing
In **Developer Tools** → **Services**:

- `cbus_lights.get_all_lights` - Request all light states
- `cbus_lights.discover_lights` - Full discovery process
- `cbus_lights.get_network_tree` - Get C-Bus structure

### 2. MQTT Monitoring
In **Developer Tools** → **MQTT**:

- **Subscribe to**: `cbus/read/254/56/+/state`
- **Subscribe to**: `cbus/read/254/56/+/level`
- **Publish to**: `cbus/write/254/56//getall` (empty payload)

### 3. Entity Discovery
- **Settings** → **Devices & Services** → **C-Bus Lights**
- Look for entities like: `light.cbus_254_56_1`
- Turn physical lights on/off to see real-time updates

## 📋 Expected Results

When working correctly:

✅ **Automatic Light Discovery**: Lights appear as entities  
✅ **Real-time Updates**: Physical switches update HA immediately  
✅ **Bidirectional Control**: HA controls work on physical lights  
✅ **Proper Naming**: Lights show as "C-Bus Light X" or actual names  
✅ **MQTT Topics**: Messages on `cbus/read/254/56/X/state`  

## 🛠️ Troubleshooting

### No Lights Discovered
1. Check ha-cbus2mqtt add-on logs
2. Verify C-Bus CNI connection (192.168.0.50:10001)
3. Test MQTT: `cbus/write/254/56//getall`
4. Check Home Assistant MQTT integration

### MQTT Issues
1. Verify MQTT broker is running
2. Check credentials: pai/pai
3. Test with MQTT Explorer

### C-Bus Connection Issues
1. Ping test: `ping 192.168.0.50`
2. Port test: Check if 10001 is open
3. CNI configuration check

## 📊 Integration Features

### MQTT Topics (Following cmqttd Standard)
- **States**: `cbus/read/254/56/{group}/state`
- **Levels**: `cbus/read/254/56/{group}/level`
- **Commands**: `cbus/write/254/56/{group}/switch`
- **Ramp**: `cbus/write/254/56/{group}/ramp`
- **Discovery**: `cbus/write/254/56//getall`

### Services Available
- `get_all_lights` - Discover all lights
- `get_network_tree` - Get C-Bus structure
- `discover_lights` - Combined discovery
- `scan_active_groups` - Legacy compatibility

### Entity Features
- **Brightness Control**: 0-255 range
- **Real-time State**: Instant updates
- **Device Information**: Proper HA device grouping
- **Unique IDs**: Persistent across restarts

## 🎯 Success Criteria

✅ Lights auto-discovered from C-Bus  
✅ Physical buttons update Home Assistant  
✅ Home Assistant controls work on lights  
✅ Services respond correctly  
✅ MQTT topics working  
✅ No errors in logs  

Your integration follows professional ha-cbus2mqtt patterns and should work reliably! 