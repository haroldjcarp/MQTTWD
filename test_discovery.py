#!/usr/bin/env python3
"""
Test script for C-Bus device discovery functionality.
Run this script to test the device discovery implementation.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_device_discovery():
    """Test the device discovery functionality."""
    logger = logging.getLogger("test_discovery")
    
    try:
        # Import modules
        from config.config import Config
        from devices.manager import DeviceManager
        from cbus.interface import CBusInterface
        
        logger.info("Starting C-Bus device discovery test")
        
        # Create test configuration
        config_data = {
            'cbus': {
                'interface': 'tcp',
                'host': '192.168.1.100',  # Update with your C-Bus CNI IP
                'port': 10001,
                'network': 254,
                'application': 56,
                'monitoring': {
                    'enabled': True,
                    'timeout': 5,
                    'max_retries': 3
                }
            }
        }
        
        # Initialize configuration
        config = Config(config_data)
        logger.info(f"Configuration loaded: {config_data}")
        
        # Test C-Bus interface directly
        logger.info("Testing C-Bus interface connection...")
        cbus_interface = CBusInterface(config)
        
        try:
            await cbus_interface.initialize()
            await cbus_interface.connect()
            logger.info("✓ C-Bus interface connected successfully")
            
            # Test active group scanning
            logger.info("Scanning for active groups...")
            active_groups = await cbus_interface.scan_active_groups()
            logger.info(f"✓ Found {len(active_groups)} active groups: {active_groups}")
            
            # Test device information query for each active group
            for group in active_groups[:5]:  # Test first 5 groups
                logger.info(f"Querying device info for group {group}...")
                device_info = await cbus_interface.query_device_info(group)
                
                if device_info:
                    logger.info(f"✓ Group {group}: {device_info}")
                else:
                    logger.warning(f"✗ No device info found for group {group}")
            
            # Test full device discovery
            logger.info("Testing full device discovery...")
            discovered_devices = await cbus_interface.discover_devices(1, 20)
            logger.info(f"✓ Full discovery found {len(discovered_devices)} devices")
            
            for group, device_info in discovered_devices.items():
                logger.info(f"  - Group {group}: {device_info['name']} ({device_info['type']})")
            
            await cbus_interface.disconnect()
            logger.info("✓ C-Bus interface disconnected")
            
        except Exception as e:
            logger.error(f"✗ C-Bus interface test failed: {e}")
            logger.info("This is expected if you don't have a C-Bus CNI connected")
        
        # Test device manager
        logger.info("Testing device manager...")
        device_manager = DeviceManager(config)
        
        try:
            await device_manager.initialize()
            logger.info("✓ Device manager initialized")
            
            # Get all devices
            all_devices = device_manager.get_devices()
            logger.info(f"✓ Total devices: {len(all_devices)}")
            
            # Get devices by type
            lights = device_manager.get_devices_by_type(device_manager.DeviceType.LIGHT)
            logger.info(f"✓ Light devices: {len(lights)}")
            
            for device in lights:
                logger.info(f"  - {device.name} (Group {device.group})")
            
            # Test statistics
            stats = device_manager.get_statistics()
            logger.info(f"✓ Device statistics: {stats}")
            
        except Exception as e:
            logger.error(f"✗ Device manager test failed: {e}")
        
        logger.info("Device discovery test completed")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.info("Make sure all required modules are available")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

async def test_protocol_commands():
    """Test C-Bus protocol commands."""
    logger = logging.getLogger("test_protocol")
    
    try:
        from cbus.interface import CBusInterface
        from config.config import Config
        
        logger.info("Testing C-Bus protocol commands...")
        
        config_data = {
            'cbus': {
                'interface': 'tcp',
                'host': '192.168.1.100',
                'port': 10001,
                'network': 254,
                'application': 56,
                'monitoring': {'enabled': True, 'timeout': 5}
            }
        }
        
        config = Config(config_data)
        cbus_interface = CBusInterface(config)
        
        try:
            await cbus_interface.initialize()
            await cbus_interface.connect()
            
            # Test individual protocol commands
            logger.info("Testing protocol commands...")
            
            # Test group level query
            test_group = 1
            level = await cbus_interface.get_group_level(test_group)
            logger.info(f"Group {test_group} level: {level}")
            
            # Test device label query
            label = await cbus_interface.get_device_label(test_group)
            logger.info(f"Group {test_group} label: {label}")
            
            # Test device type detection
            device_type = await cbus_interface.detect_device_type(test_group)
            logger.info(f"Group {test_group} type: {device_type}")
            
            # Test dimming capability
            is_dimmable = await cbus_interface.is_device_dimmable(test_group)
            logger.info(f"Group {test_group} dimmable: {is_dimmable}")
            
            await cbus_interface.disconnect()
            logger.info("✓ Protocol test completed")
            
        except Exception as e:
            logger.error(f"Protocol test failed: {e}")
            
    except Exception as e:
        logger.error(f"Protocol test setup failed: {e}")

def print_usage():
    """Print usage information."""
    print("""
C-Bus Device Discovery Test Script
==================================

This script tests the C-Bus device discovery functionality.

Usage:
    python test_discovery.py [test_type]

Test types:
    discovery  - Test device discovery (default)
    protocol   - Test protocol commands
    all        - Run all tests

Configuration:
    Update the IP address in the script to match your C-Bus CNI.
    Default: 192.168.1.100:10001

Expected results:
    - If C-Bus CNI is connected: Shows discovered devices with real names
    - If no C-Bus CNI: Shows connection errors (expected for testing)
    """)

async def main():
    """Main test function."""
    import sys
    
    test_type = sys.argv[1] if len(sys.argv) > 1 else "discovery"
    
    if test_type == "help" or test_type == "--help":
        print_usage()
        return
    
    logger = logging.getLogger("main")
    logger.info(f"Starting C-Bus tests: {test_type}")
    
    if test_type == "discovery" or test_type == "all":
        await test_device_discovery()
    
    if test_type == "protocol" or test_type == "all":
        await test_protocol_commands()
    
    logger.info("All tests completed")

if __name__ == "__main__":
    asyncio.run(main()) 