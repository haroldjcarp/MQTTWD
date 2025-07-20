#!/usr/bin/env python3
"""
Simple script to get all C-Bus light names and their current states.
Update the HOST and PORT variables below to match your C-Bus CNI settings.
"""

import asyncio
import sys
from pathlib import Path

# Add the project directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configuration - UPDATE THESE VALUES FOR YOUR SYSTEM
HOST = "192.168.0.50"   # Your C-Bus CNI IP address
PORT = 10001            # Your C-Bus CNI port (usually 10001)

async def get_all_lights_status():
    """Get status of all lights from C-Bus system."""
    try:
        from cbus.interface import CBusInterface
        from config.config import Config
        import yaml
        
        print(f"🔍 Connecting to C-Bus system at {HOST}:{PORT}")
        
        # Create temporary configuration file
        config_data = {
            'cbus': {
                'interface': 'tcp',
                'host': HOST,
                'port': PORT,
                'network': 254,
                'application': 56,
                'monitoring': {
                    'enabled': True,
                    'timeout': 5,
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
        
        # Write temporary config file
        temp_config_path = "temp_config.yaml"
        with open(temp_config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        # Load configuration
        config = Config(temp_config_path)
        await config.load()
        
        # Create C-Bus interface
        cbus = CBusInterface(config)
        
        print("📡 Scanning for active groups...")
        active_groups = await cbus.scan_active_groups()
        
        if not active_groups:
            print("❌ No active groups found. Check your C-Bus connection and settings.")
            return
        
        print(f"✅ Found {len(active_groups)} active groups: {active_groups}")
        print("\n" + "="*60)
        print("LIGHT STATUS REPORT")
        print("="*60)
        
        # Get status for each active group
        for group in active_groups:
            try:
                # Get current level
                level = await cbus.get_group_level(group)
                
                # Try to get label/name
                label_info = await cbus.get_group_label(group)
                name = label_info.get('label', f"Group {group}")
                
                # Format status
                if level is not None:
                    if level == 0:
                        status = "OFF"
                        brightness = "0%"
                    else:
                        status = "ON"
                        brightness = f"{int(level/255*100)}%"
                    
                    print(f"Group {group:3d} | {name:<20} | {status:<3} | {brightness:>4}")
                else:
                    print(f"Group {group:3d} | {name:<20} | ??? | N/A")
                    
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Group {group:3d} | Unknown              | ERR | Failed: {e}")
        
        print("="*60)
        print(f"✅ Scan complete. Found {len(active_groups)} groups.")
        
        # Clean up temporary config file
        import os
        try:
            os.remove(temp_config_path)
        except:
            pass
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required modules are installed:")
        print("pip install paho-mqtt pyserial pyyaml asyncio-mqtt aiofiles")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("Check your C-Bus CNI connection and settings.")

if __name__ == "__main__":
    print("C-Bus Light Status Scanner")
    print(f"Targeting: {HOST}:{PORT}")
    print("Press Ctrl+C to stop\n")
    
    try:
        asyncio.run(get_all_lights_status())
    except KeyboardInterrupt:
        print("\n⏹️ Scan interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}") 