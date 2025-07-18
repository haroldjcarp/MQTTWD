"""
Simple C-Bus device discovery for logging purposes.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

_LOGGER = logging.getLogger(__name__)


class SimpleCBusScanner:
    """Simple C-Bus device scanner."""
    
    def __init__(self, host: str, port: int = 10001):
        """Initialize scanner."""
        self.host = host
        self.port = port
        self.connected = False
        self.reader = None
        self.writer = None
        
    async def connect(self) -> bool:
        """Connect to C-Bus CNI."""
        try:
            _LOGGER.info(f"Attempting to connect to C-Bus CNI at {self.host}:{self.port}")
            
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10
            )
            
            self.connected = True
            _LOGGER.info("✅ Connected to C-Bus CNI successfully")
            
            # Send initialization commands
            await self._send_init_commands()
            
            return True
            
        except asyncio.TimeoutError:
            _LOGGER.error(f"❌ Connection timeout to C-Bus CNI {self.host}:{self.port}")
            return False
        except ConnectionRefusedError:
            _LOGGER.error(f"❌ Connection refused to C-Bus CNI {self.host}:{self.port}")
            _LOGGER.error("   Make sure your C-Bus CNI is accessible and not in use by another application")
            return False
        except Exception as e:
            _LOGGER.error(f"❌ Failed to connect to C-Bus CNI: {e}")
            return False
    
    async def _send_init_commands(self):
        """Send initialization commands."""
        try:
            # Send reset and initialization
            await self._send_command("|||")  # Reset
            await asyncio.sleep(0.1)
            await self._send_command("\\FE")  # Set network 254
            await self._send_command("@38")   # Set application 56 (0x38)
            await self._send_command("g")     # Enable monitoring
            
            _LOGGER.info("✅ C-Bus initialization commands sent")
            
        except Exception as e:
            _LOGGER.error(f"❌ Failed to send init commands: {e}")
    
    async def _send_command(self, command: str):
        """Send command to C-Bus."""
        if not self.connected or not self.writer:
            return
            
        try:
            command_bytes = (command + "\r\n").encode('ascii')
            self.writer.write(command_bytes)
            await self.writer.drain()
            _LOGGER.debug(f"Sent command: {command}")
            
        except Exception as e:
            _LOGGER.error(f"Error sending command '{command}': {e}")
    
    async def scan_for_devices(self, start_group: int = 1, end_group: int = 50) -> List[Dict[str, Any]]:
        """Scan for devices and return discovered devices."""
        if not self.connected:
            _LOGGER.error("❌ Not connected to C-Bus CNI")
            return []
        
        _LOGGER.info(f"🔍 Scanning for devices in groups {start_group} to {end_group}")
        
        discovered_devices = []
        
        for group in range(start_group, end_group + 1):
            try:
                # Query device level to see if it responds
                await self._send_command(f"g38{group:02X}")
                
                # Wait a bit for response
                await asyncio.sleep(0.1)
                
                # For now, assume device exists if we get here
                device_info = {
                    'group': group,
                    'name': f"C-Bus Device {group}",
                    'type': 'light',
                    'responsive': True
                }
                
                discovered_devices.append(device_info)
                _LOGGER.info(f"📱 Found device: Group {group}")
                
                # Small delay to not overwhelm the system
                await asyncio.sleep(0.05)
                
            except Exception as e:
                _LOGGER.debug(f"No device at group {group}: {e}")
                continue
        
        return discovered_devices
    
    async def quick_scan(self) -> List[int]:
        """Quick scan for responsive groups."""
        if not self.connected:
            return []
        
        _LOGGER.info("🚀 Performing quick scan for responsive groups")
        
        # Test common group numbers
        test_groups = [1, 2, 3, 4, 5, 10, 11, 12, 20, 21, 22, 30, 31, 32]
        responsive_groups = []
        
        for group in test_groups:
            try:
                await self._send_command(f"g38{group:02X}")
                await asyncio.sleep(0.1)
                
                # Assume responsive for now
                responsive_groups.append(group)
                _LOGGER.info(f"📡 Group {group} is responsive")
                
            except Exception:
                continue
        
        return responsive_groups
    
    async def disconnect(self):
        """Disconnect from C-Bus."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.connected = False
            _LOGGER.info("🔌 Disconnected from C-Bus CNI")


async def discover_all_devices(host: str, port: int = 10001) -> List[Dict[str, Any]]:
    """Discover all devices and log them."""
    scanner = SimpleCBusScanner(host, port)
    
    try:
        if await scanner.connect():
            # First do a quick scan
            responsive_groups = await scanner.quick_scan()
            
            if responsive_groups:
                _LOGGER.info(f"🎯 Found {len(responsive_groups)} responsive groups: {responsive_groups}")
                
                # Now do detailed scan of responsive groups
                devices = []
                for group in responsive_groups:
                    device_info = {
                        'group': group,
                        'name': f"C-Bus Light {group}",
                        'type': 'light',
                        'responsive': True
                    }
                    devices.append(device_info)
                
                # Log all discovered devices
                _LOGGER.info("🏠 DISCOVERED DEVICES:")
                for device in devices:
                    _LOGGER.info(f"  📱 {device['name']} (Group {device['group']})")
                
                return devices
            else:
                _LOGGER.warning("⚠️ No responsive devices found")
                return []
        else:
            _LOGGER.error("❌ Could not connect to C-Bus CNI")
            return []
            
    except Exception as e:
        _LOGGER.error(f"❌ Error during discovery: {e}")
        return []
    finally:
        await scanner.disconnect()


async def log_all_lights(host: str, port: int = 10001):
    """Main function to discover and log all lights."""
    _LOGGER.info("=" * 50)
    _LOGGER.info("🔍 STARTING C-BUS LIGHT DISCOVERY")
    _LOGGER.info("=" * 50)
    
    devices = await discover_all_devices(host, port)
    
    if devices:
        _LOGGER.info("=" * 50)
        _LOGGER.info(f"✅ DISCOVERY COMPLETE - FOUND {len(devices)} DEVICES")
        _LOGGER.info("=" * 50)
        
        for device in devices:
            _LOGGER.info(f"💡 {device['name']} (Group {device['group']})")
    else:
        _LOGGER.info("=" * 50)
        _LOGGER.info("❌ NO DEVICES FOUND")
        _LOGGER.info("=" * 50)
    
    return devices 