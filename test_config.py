#!/usr/bin/env python3
"""
Test script to verify configuration loading and basic functionality
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config.config import Config
from devices.manager import DeviceManager


async def test_configuration():
    """Test configuration loading."""
    print("Testing configuration loading...")
    
    try:
        config = Config("config/config.yaml")
        await config.load()
        
        print("✓ Configuration loaded successfully")
        print(f"  - C-Bus interface: {config.get('cbus.interface')}")
        print(f"  - MQTT broker: {config.get('mqtt.broker')}")
        print(f"  - Discovery enabled: {config.get('discovery.enabled')}")
        
        return config
        
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return None


async def test_device_manager(config):
    """Test device manager."""
    print("\nTesting device manager...")
    
    try:
        device_manager = DeviceManager(config)
        await device_manager.initialize()
        
        devices = device_manager.get_devices()
        print(f"✓ Device manager initialized with {len(devices)} devices")
        
        for device in devices[:3]:  # Show first 3 devices
            print(f"  - {device.name} (Group {device.group}, Type: {device.device_type.value})")
            
        return device_manager
        
    except Exception as e:
        print(f"✗ Device manager failed: {e}")
        return None


async def main():
    """Main test function."""
    print("CBus MQTT Bridge - Configuration Test")
    print("=" * 50)
    
    # Test configuration
    config = await test_configuration()
    if not config:
        sys.exit(1)
        
    # Test device manager
    device_manager = await test_device_manager(config)
    if not device_manager:
        sys.exit(1)
        
    print("\n✓ All tests passed!")
    print("\nNext steps:")
    print("1. Update config/config.yaml with your C-Bus settings")
    print("2. Update config/devices.yaml with your device configuration")
    print("3. Run: python main.py --config config/config.yaml")


if __name__ == "__main__":
    asyncio.run(main()) 