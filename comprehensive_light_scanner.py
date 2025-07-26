#!/usr/bin/env python3
"""
Comprehensive C-Bus Light Scanner for Home Assistant
Scans ALL possible C-Bus groups (1-255) to find all lights in your system.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# Configuration - Your Home Assistant MQTT settings
MQTT_BROKER = "192.168.0.50"  # Your HA IP
MQTT_PORT = 1883
MQTT_USER = "pai"
MQTT_PASSWORD = "pai"

# C-Bus configuration  
CBUS_NETWORK = 254
CBUS_APPLICATION = 56

class ComprehensiveLightScanner:
    """Scan ALL C-Bus groups to find every light in the system."""
    
    def __init__(self):
        self.client = mqtt.Client()
        self.discovered_lights = {}
        self.connected = False
        
        # Configure MQTT client
        self.client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            self.connected = True
            
            # Subscribe to ALL C-Bus state and level topics
            topics = [
                f"cbus/read/{CBUS_NETWORK}/{CBUS_APPLICATION}/+/state",
                f"cbus/read/{CBUS_NETWORK}/{CBUS_APPLICATION}/+/level", 
                f"cbus/read/{CBUS_NETWORK}///tree",
            ]
            
            for topic in topics:
                client.subscribe(topic)
                print(f"📡 Subscribed to: {topic}")
                
        else:
            print(f"❌ Failed to connect to MQTT broker (code: {rc})")
            
    def on_disconnect(self, client, userdata, rc):
        print(f"⚠️ Disconnected from MQTT broker")
        self.connected = False
        
    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8').strip()
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Parse C-Bus light messages
            if f"cbus/read/{CBUS_NETWORK}/{CBUS_APPLICATION}/" in topic:
                parts = topic.split('/')
                if len(parts) >= 6:
                    group = parts[4]
                    message_type = parts[5]  # 'state' or 'level'
                    
                    # Initialize light if not seen before
                    if group not in self.discovered_lights:
                        self.discovered_lights[group] = {
                            'group': group,
                            'state': None,
                            'level': None,
                            'last_seen': timestamp,
                            'responsive': True
                        }
                        print(f"[{timestamp}] 🔍 NEW LIGHT: Group {group}")
                    
                    # Update light information
                    if message_type == 'state':
                        self.discovered_lights[group]['state'] = payload
                        print(f"[{timestamp}] 💡 Group {group}: State = {payload}")
                    elif message_type == 'level':
                        self.discovered_lights[group]['level'] = payload
                        print(f"[{timestamp}] 🔆 Group {group}: Level = {payload}")
                    
                    self.discovered_lights[group]['last_seen'] = timestamp
                    
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            
    def send_comprehensive_discovery(self):
        """Send discovery commands to find ALL lights."""
        if not self.connected:
            print("❌ Not connected to MQTT broker")
            return
            
        print("\n🚀 Starting comprehensive light discovery...")
        
        # 1. Request network tree
        tree_topic = f"cbus/write/{CBUS_NETWORK}///gettree"
        self.client.publish(tree_topic, "", 1)
        print(f"📤 1. Sent network tree request: {tree_topic}")
        
        # 2. Request all lights in application
        getall_topic = f"cbus/write/{CBUS_NETWORK}/{CBUS_APPLICATION}//getall"
        self.client.publish(getall_topic, "", 1)
        print(f"📤 2. Sent getall request: {getall_topic}")
        
        # 3. Test individual groups systematically
        print(f"📤 3. Testing individual groups...")
        
        # Test in batches to avoid overwhelming the system
        test_ranges = [
            (1, 20),     # Common residential lights
            (21, 50),    # Extended residential
            (51, 100),   # Commercial/extended
            (101, 150),  # High-end systems
            (151, 200),  # Large installations
            (201, 255),  # Maximum range
        ]
        
        for start, end in test_ranges:
            print(f"   Testing groups {start}-{end}...")
            for group in range(start, end + 1):
                # Query group state
                query_topic = f"cbus/write/{CBUS_NETWORK}/{CBUS_APPLICATION}/{group}/switch"
                # Send a "status request" - this should trigger a response if light exists
                self.client.publish(query_topic, "STATUS", 1)
                
                # Small delay to avoid overwhelming
                time.sleep(0.05)  # 50ms between queries
                
            # Larger delay between ranges
            time.sleep(1)
            
        print("✅ Comprehensive discovery commands sent!")
        
    def force_light_discovery(self):
        """Force discovery by briefly pulsing each possible group."""
        if not self.connected:
            print("❌ Not connected to MQTT broker")
            return
            
        print("\n⚡ FORCE DISCOVERY: Testing all groups with brief pulses...")
        print("⚠️  This will briefly flash lights that exist!")
        
        response = input("Continue? This will briefly turn lights on/off (y/N): ")
        if response.lower() != 'y':
            print("Cancelled force discovery.")
            return
            
        # Test each group by sending a brief ON command
        for group in range(1, 256):
            if group % 20 == 0:
                print(f"   Testing groups {group-19}-{group}...")
                
            # Send brief ON pulse
            on_topic = f"cbus/write/{CBUS_NETWORK}/{CBUS_APPLICATION}/{group}/switch"
            self.client.publish(on_topic, "ON", 1)
            time.sleep(0.1)  # Very brief
            
            # Send OFF 
            self.client.publish(on_topic, "OFF", 1)
            time.sleep(0.1)
            
        print("✅ Force discovery complete!")
        
    def print_summary(self):
        """Print summary of ALL discovered lights."""
        print("\n" + "="*80)
        print("📋 COMPREHENSIVE LIGHT DISCOVERY RESULTS")
        print("="*80)
        
        if self.discovered_lights:
            # Sort by group number
            sorted_lights = sorted(self.discovered_lights.items(), key=lambda x: int(x[0]))
            
            print(f"🎉 FOUND {len(sorted_lights)} C-BUS LIGHTS!\n")
            
            for group, info in sorted_lights:
                state = info.get('state', 'Unknown')
                level = info.get('level', 'Unknown')
                last_seen = info.get('last_seen', 'Unknown')
                
                # Determine status
                if state == 'ON':
                    status = f"🟢 ON  (Level: {level})"
                elif state == 'OFF':
                    status = f"⚫ OFF (Level: {level})"
                else:
                    status = f"❓ {state} (Level: {level})"
                    
                print(f"Group {group:>3}: {status:<25} | Last seen: {last_seen}")
                
            print(f"\n✅ TOTAL LIGHTS DISCOVERED: {len(sorted_lights)}")
            
            # Save to file
            results_file = f"discovered_lights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w') as f:
                json.dump(self.discovered_lights, f, indent=2)
            print(f"💾 Results saved to: {results_file}")
            
        else:
            print("😞 No lights discovered.")
            print("\nPossible issues:")
            print("• MQTT broker not accessible")
            print("• C-Bus CNI not responding") 
            print("• Wrong network/application numbers")
            print("• All lights are unresponsive")
            
    def run_scan(self, duration=120):
        """Run comprehensive light discovery scan."""
        print("🔍 COMPREHENSIVE C-BUS LIGHT SCANNER")
        print(f"Target: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"C-Bus: Network {CBUS_NETWORK}, Application {CBUS_APPLICATION}")
        print(f"Duration: {duration} seconds\n")
        
        try:
            # Connect to MQTT
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(1)
                timeout -= 1
                
            if not self.connected:
                print("❌ Failed to connect to MQTT broker")
                return
                
            # Start discovery
            time.sleep(2)  # Let subscriptions settle
            self.send_comprehensive_discovery()
            
            # Ask about force discovery
            print(f"\n⏱️  Monitoring responses for {duration} seconds...")
            print("💡 Tip: Turn physical lights on/off to help discovery")
            
            # Monitor for responses
            start_time = time.time()
            last_count = 0
            
            while time.time() - start_time < duration:
                remaining = int(duration - (time.time() - start_time))
                current_count = len(self.discovered_lights)
                
                if current_count != last_count:
                    print(f"\r⏰ Time: {remaining:3d}s | Lights found: {current_count:3d} (NEW!)", end='', flush=True)
                    last_count = current_count
                else:
                    print(f"\r⏰ Time: {remaining:3d}s | Lights found: {current_count:3d}", end='', flush=True)
                    
                time.sleep(1)
                
            print("\n")
            
            # Offer force discovery if few lights found
            if len(self.discovered_lights) < 20:
                print(f"\n🤔 Only found {len(self.discovered_lights)} lights, but you have ~100.")
                print("This suggests lights are OFF and not responding to queries.")
                self.force_light_discovery()
                
                # Monitor for additional responses
                print("Monitoring for 30 more seconds after force discovery...")
                for i in range(30, 0, -1):
                    print(f"\r⏰ Monitoring: {i:2d}s | Total lights: {len(self.discovered_lights):3d}", end='', flush=True)
                    time.sleep(1)
                print("\n")
                
        except KeyboardInterrupt:
            print("\n⏹️ Scan interrupted by user")
            
        except Exception as e:
            print(f"❌ Scanner failed: {e}")
            
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            self.print_summary()


def main():
    """Main function."""
    scanner = ComprehensiveLightScanner()
    
    print("This scanner will find ALL C-Bus lights in your system!")
    print("It will test groups 1-255 systematically.\n")
    
    duration = 120  # 2 minutes default
    try:
        duration_input = input(f"Scan duration in seconds (default {duration}): ").strip()
        if duration_input:
            duration = int(duration_input)
    except:
        pass
        
    scanner.run_scan(duration)


if __name__ == "__main__":
    main() 