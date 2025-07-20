#!/usr/bin/env python3
"""
Comprehensive C-Bus light scanner.
Tries multiple ranges and methods to find ALL lights.
"""

import asyncio
import sys
from pathlib import Path

# Add the project directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configuration
HOST = "192.168.0.50"
PORT = 10001

async def comprehensive_scan():
    """Comprehensive scan of all possible C-Bus groups."""
    try:
        from cbus.interface import CBusInterface
        from config.config import Config
        import yaml
        import os
        
        print(f"🚀 COMPREHENSIVE C-BUS SCAN")
        print(f"Target: {HOST}:{PORT}")
        print(f"This will scan groups 1-255 to find ALL lights\n")
        
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
                    'timeout': 2,  # Shorter timeout for faster scanning
                    'max_retries': 1
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
        temp_config = "temp_scan_config.yaml"
        with open(temp_config, 'w') as f:
            yaml.dump(config_data, f)
        
        # Load configuration and create interface
        config = Config(temp_config)
        await config.load()
        
        cbus = CBusInterface(config)
        
        print("📡 Connecting to C-Bus...")
        await cbus.connect()
        
        if not cbus.connected:
            print("❌ Failed to connect to C-Bus")
            return
            
        print("✅ Connected! Starting comprehensive scan...")
        print("\n" + "="*80)
        print("GROUP SCAN RESULTS")
        print("="*80)
        
        # Scan ranges to try
        scan_ranges = [
            ("Common Lights", range(1, 51)),      # 1-50
            ("Extended", range(51, 101)),         # 51-100
            ("Mid Range", range(101, 201)),       # 101-200
            ("High Range", range(201, 256)),      # 201-255
        ]
        
        total_found = 0
        all_lights = {}
        
        for range_name, group_range in scan_ranges:
            print(f"\n🔍 Scanning {range_name} (Groups {min(group_range)}-{max(group_range)})")
            found_in_range = 0
            
            for group in group_range:
                try:
                    # Show progress every 10 groups
                    if group % 10 == 0:
                        print(f"   Checking group {group}...", end="", flush=True)
                    
                    # Try to get group level
                    level = await cbus.get_group_level(group)
                    
                    if level is not None:
                        found_in_range += 1
                        total_found += 1
                        
                        # Try to get label/name
                        try:
                            label_info = await cbus.get_group_label(group)
                            name = label_info.get('label', f"Group {group}")
                        except:
                            name = f"Group {group}"
                        
                        # Determine status
                        if level == 0:
                            status = "OFF"
                            brightness = "0%"
                        else:
                            status = "ON"
                            brightness = f"{int(level/255*100)}%"
                        
                        all_lights[group] = {
                            'name': name,
                            'level': level,
                            'status': status,
                            'brightness': brightness
                        }
                        
                        print(f"\n   ✅ FOUND: Group {group:3d} | {name:<25} | {status:<3} | {brightness:>4}")
                    
                    # Small delay to avoid overwhelming the system
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    # Silent continue for non-responsive groups
                    pass
                    
            if group % 10 == 0:
                print(f" ✅ Done")
                
            print(f"   📊 Found {found_in_range} lights in {range_name}")
        
        print("\n" + "="*80)
        print("FINAL RESULTS")
        print("="*80)
        
        if all_lights:
            print(f"🎉 SUCCESS! Found {total_found} C-Bus lights:\n")
            
            for group in sorted(all_lights.keys()):
                light = all_lights[group]
                print(f"Group {group:3d}: {light['name']:<25} | {light['status']:<3} | {light['brightness']:>4}")
                
            print(f"\n✅ Scan complete - {total_found} lights discovered!")
            
            # Save results to file
            results_file = "cbus_lights_found.txt"
            with open(results_file, 'w') as f:
                f.write("C-Bus Lights Discovery Results\n")
                f.write("=" * 40 + "\n\n")
                for group in sorted(all_lights.keys()):
                    light = all_lights[group]
                    f.write(f"Group {group:3d}: {light['name']:<25} | {light['status']:<3} | {light['brightness']:>4}\n")
                    
            print(f"📄 Results saved to: {results_file}")
            
        else:
            print("😞 No lights found in any tested ranges (1-255)")
            print("\nPossible reasons:")
            print("• All lights are currently off (try turning some on)")
            print("• Lights use different network/application numbers")  
            print("• Different C-Bus protocol version")
            print("• Lights require different query method")
            
        # Cleanup
        try:
            await cbus.disconnect()
            os.remove(temp_config)
        except:
            pass
            
    except Exception as e:
        print(f"❌ Scan failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main function."""
    print("🔍 COMPREHENSIVE C-BUS LIGHT SCANNER")
    print("This tool will scan groups 1-255 to find all lights")
    print("⚠️  This may take a few minutes...\n")
    
    # Ask user to confirm
    response = input("Press ENTER to start scan, or 'q' to quit: ").strip().lower()
    if response == 'q':
        print("Scan cancelled.")
        return
        
    print(f"\n🚀 Starting comprehensive scan...")
    await comprehensive_scan()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Scan interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}") 