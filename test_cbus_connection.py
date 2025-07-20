#!/usr/bin/env python3
"""
Simple C-Bus connection test script.
Tests basic connectivity and tries to find any responsive groups.
"""

import asyncio
import socket
import sys
from pathlib import Path

# Add the project directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configuration - UPDATE THESE VALUES FOR YOUR SYSTEM
HOST = "192.168.0.50"
PORT = 10001

async def test_basic_connection():
    """Test basic TCP connection to C-Bus CNI."""
    print(f"🔌 Testing basic TCP connection to {HOST}:{PORT}")
    
    try:
        # Test socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((HOST, PORT))
        sock.close()
        
        if result == 0:
            print(f"✅ TCP connection successful to {HOST}:{PORT}")
            return True
        else:
            print(f"❌ TCP connection failed to {HOST}:{PORT} (error code: {result})")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

async def test_cbus_interface():
    """Test C-Bus interface communication."""
    if not await test_basic_connection():
        return
    
    try:
        from cbus.interface import CBusInterface
        from config.config import Config
        import yaml
        import os
        
        print(f"\n🔍 Testing C-Bus communication...")
        
        # Create configuration
        config_data = {
            'cbus': {
                'interface': 'tcp',
                'host': HOST,
                'port': PORT,
                'network': 254,
                'application': 56,
                'monitoring': {
                    'enabled': True,
                    'timeout': 10,
                    'max_retries': 3
                }
            },
                         'mqtt': {
                 'broker': 'core-mosquitto',
                 'port': 1883,
                 'username': 'pai',
                 'password': 'pai',
                'topics': {
                    'command': 'cbus/command',
                    'state': 'cbus/state'
                },
                'keepalive': 60,
                'reconnect_delay': 5
            },
            'discovery': {
                'enabled': True,
                'prefix': 'homeassistant',
                'auto_discovery': True
            },
            'logging': {
                'level': 'INFO',
                'file': '/var/log/cbusmqtt.log'
            }
        }
        
        # Write temporary config
        temp_config = "temp_test_config.yaml"
        with open(temp_config, 'w') as f:
            yaml.dump(config_data, f)
        
        # Load configuration and create interface
        config = Config(temp_config)
        await config.load()
        
        cbus = CBusInterface(config)
        
        print("📡 Connecting to C-Bus...")
        await cbus.connect()
        
        if cbus.connected:
            print("✅ C-Bus connection established!")
            
            # Test a few common groups directly
            print("\n🔍 Testing common light groups:")
            test_groups = [1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 100, 200]
            
            found_groups = []
            for group in test_groups:
                try:
                    print(f"   Testing group {group}...", end="")
                    level = await cbus.get_group_level(group)
                    if level is not None:
                        found_groups.append((group, level))
                        status = "ON" if level > 0 else "OFF"
                        brightness = f"{int(level/255*100)}%" if level > 0 else "0%"
                        print(f" ✅ Found! Status: {status}, Level: {brightness}")
                    else:
                        print(f" ❌ No response")
                    
                    await asyncio.sleep(0.5)  # Delay between queries
                    
                except Exception as e:
                    print(f" ❌ Error: {e}")
                    
            if found_groups:
                print(f"\n✅ Found {len(found_groups)} responsive groups:")
                for group, level in found_groups:
                    status = "ON" if level > 0 else "OFF" 
                    brightness = f"{int(level/255*100)}%" if level > 0 else "0%"
                    print(f"   Group {group}: {status} ({brightness})")
            else:
                print(f"\n⚠️  No responsive groups found in tested range.")
                print("   Try turning on a light and running the test again.")
                
        else:
            print("❌ Failed to establish C-Bus connection")
            
        # Cleanup
        try:
            await cbus.disconnect()
            os.remove(temp_config)
        except:
            pass
            
    except Exception as e:
        print(f"❌ C-Bus test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("C-Bus Connection Test")
    print(f"Target: {HOST}:{PORT}\n")
    
    try:
        asyncio.run(test_cbus_interface())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}") 