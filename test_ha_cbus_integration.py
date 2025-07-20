#!/usr/bin/env python3
"""
Test script for C-Bus integration - works with ha-cbus2mqtt addon
This script shows how our integration works with the standard cmqttd approach
"""

import asyncio
import json
import logging
from datetime import datetime
import paho.mqtt.client as mqtt

# Configuration matching ha-cbus2mqtt addon
MQTT_BROKER = "192.168.0.50"  # Your Home Assistant IP
MQTT_PORT = 1883
MQTT_USER = "pai"
MQTT_PASSWORD = "pai"

# C-Bus configuration
CBUS_NETWORK = 254
CBUS_APPLICATION = 56

# MQTT Topics following cmqttd pattern (from ha-cbus2mqtt)
TOPICS_TO_MONITOR = [
    f"cbus/read/{CBUS_NETWORK}/{CBUS_APPLICATION}/+/state",    # Light states
    f"cbus/read/{CBUS_NETWORK}/{CBUS_APPLICATION}/+/level",    # Light levels  
    f"cbus/read/{CBUS_NETWORK}///tree",                        # Network tree
    f"homeassistant/light/cbus_+/config",                      # HA Discovery
]

TOPICS_TO_SEND = {
    "getall": f"cbus/write/{CBUS_NETWORK}/{CBUS_APPLICATION}//getall",
    "gettree": f"cbus/write/{CBUS_NETWORK}///gettree",
    "light_on": f"cbus/write/{CBUS_NETWORK}/{CBUS_APPLICATION}/<GROUP>/switch",
    "light_ramp": f"cbus/write/{CBUS_NETWORK}/{CBUS_APPLICATION}/<GROUP>/ramp",
}

class CBusIntegrationTester:
    """Test C-Bus integration with ha-cbus2mqtt patterns."""
    
    def __init__(self):
        self.client = mqtt.Client()
        self.lights_discovered = {}
        self.connected = False
        
        # Configure client
        self.client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            self.connected = True
            
            # Subscribe to all C-Bus topics
            for topic in TOPICS_TO_MONITOR:
                client.subscribe(topic)
                print(f"📡 Subscribed to: {topic}")
                
            print("\n🔍 Monitoring C-Bus MQTT topics...")
            print("=" * 60)
            
        else:
            print(f"❌ Failed to connect to MQTT broker (code: {rc})")
            
    def on_disconnect(self, client, userdata, rc):
        print(f"⚠️ Disconnected from MQTT broker")
        self.connected = False
        
    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Parse C-Bus messages
            if "cbus/read" in topic:
                self.handle_cbus_read(topic, payload, timestamp)
            elif "homeassistant" in topic:
                self.handle_ha_discovery(topic, payload, timestamp)
            else:
                print(f"[{timestamp}] 📨 Other: {topic} = {payload}")
                
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            
    def handle_cbus_read(self, topic, payload, timestamp):
        """Handle C-Bus read messages following ha-cbus2mqtt patterns."""
        parts = topic.split('/')
        
        if len(parts) >= 6 and parts[5] == "state":
            # cbus/read/254/56/123/state
            group = parts[4]
            state = payload.strip().upper()
            
            if group not in self.lights_discovered:
                print(f"[{timestamp}] 🔍 DISCOVERED: C-Bus Light Group {group}")
                self.lights_discovered[group] = {"state": state, "level": None}
            else:
                self.lights_discovered[group]["state"] = state
                
            print(f"[{timestamp}] 💡 Light {group}: {state}")
            
        elif len(parts) >= 6 and parts[5] == "level":
            # cbus/read/254/56/123/level  
            group = parts[4]
            level = payload.strip()
            
            if group in self.lights_discovered:
                self.lights_discovered[group]["level"] = level
                
            print(f"[{timestamp}] 🔆 Light {group}: Level {level}")
            
        elif "tree" in topic:
            # Network tree information
            print(f"[{timestamp}] 🌳 Network Tree: {len(payload)} bytes")
            
    def handle_ha_discovery(self, topic, payload, timestamp):
        """Handle Home Assistant discovery messages."""
        print(f"[{timestamp}] 🏠 HA Discovery: {topic}")
        if payload:
            try:
                config = json.loads(payload)
                name = config.get("name", "Unknown")
                print(f"         Entity: {name}")
            except:
                print(f"         Config: {len(payload)} bytes")
                
    def send_test_commands(self):
        """Send test commands following ha-cbus2mqtt patterns."""
        if not self.connected:
            print("❌ Not connected to MQTT broker")
            return
            
        print("\n📤 Sending C-Bus test commands...")
        
        # 1. Request all lights (like our integration does)
        print("1️⃣ Requesting all lights...")
        self.client.publish(TOPICS_TO_SEND["getall"], "", 1)
        
        # 2. Request network tree
        print("2️⃣ Requesting network tree...")
        self.client.publish(TOPICS_TO_SEND["gettree"], "", 1)
        
        print("✅ Commands sent! Watch for responses above.")
        
    def test_light_control(self, group_id):
        """Test light control commands."""
        if not self.connected:
            print("❌ Not connected to MQTT broker")
            return
            
        print(f"\n💡 Testing light control for Group {group_id}...")
        
        # Turn on light
        on_topic = TOPICS_TO_SEND["light_on"].replace("<GROUP>", str(group_id))
        self.client.publish(on_topic, "ON", 1)
        print(f"📤 Sent ON command to: {on_topic}")
        
        # Ramp to 50%
        ramp_topic = TOPICS_TO_SEND["light_ramp"].replace("<GROUP>", str(group_id))
        self.client.publish(ramp_topic, "50", 1)
        print(f"📤 Sent RAMP 50% command to: {ramp_topic}")
        
    def print_summary(self):
        """Print summary of discovered lights."""
        print("\n" + "="*60)
        print("📋 DISCOVERED LIGHTS SUMMARY")
        print("="*60)
        
        if self.lights_discovered:
            for group, info in self.lights_discovered.items():
                state = info.get("state", "Unknown")
                level = info.get("level", "Unknown")
                print(f"Group {group:>3}: {state:<3} | Level: {level}")
                
            print(f"\n✅ Total lights discovered: {len(self.lights_discovered)}")
        else:
            print("⚠️ No lights discovered yet.")
            print("Make sure ha-cbus2mqtt addon is running and configured!")
            
    def run(self, duration=60):
        """Run the integration test."""
        print("🚀 C-Bus Integration Tester")
        print("Tests our custom integration with ha-cbus2mqtt addon")
        print(f"Target: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"Network: {CBUS_NETWORK}, Application: {CBUS_APPLICATION}\n")
        
        try:
            # Connect to MQTT
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            while not self.connected and timeout > 0:
                import time
                time.sleep(1)
                timeout -= 1
                
            if not self.connected:
                print("❌ Failed to connect to MQTT broker")
                return
                
            # Send initial commands
            import time
            time.sleep(2)
            self.send_test_commands()
            
            # Monitor for specified duration
            print(f"\n⏱️ Monitoring for {duration} seconds... (Press Ctrl+C to stop)")
            
            for remaining in range(duration, 0, -1):
                print(f"\r⏰ Time: {remaining:3d}s | Lights: {len(self.lights_discovered):2d}", end='', flush=True)
                time.sleep(1)
                
            print("\n")
            
        except KeyboardInterrupt:
            print("\n⏹️ Test stopped by user")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            
        finally:
            self.client.loop_stop() 
            self.client.disconnect()
            self.print_summary()
            
        print("\n💡 To test light control, run:")
        print(f"   python {__file__} --control <group_number>")


def main():
    """Main function."""
    import sys
    
    tester = CBusIntegrationTester()
    
    if len(sys.argv) > 2 and sys.argv[1] == "--control":
        # Quick light control test
        group_id = sys.argv[2]
        print(f"🔧 Quick light control test for Group {group_id}")
        
        # Connect and send commands
        tester.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        tester.client.loop_start()
        
        import time
        time.sleep(2)
        
        if tester.connected:
            tester.test_light_control(group_id)
            time.sleep(5)
        
        tester.client.loop_stop()
        tester.client.disconnect()
        
    else:
        # Full integration test
        duration = 60
        if len(sys.argv) > 1:
            try:
                duration = int(sys.argv[1])
            except:
                pass
                
        tester.run(duration)


if __name__ == "__main__":
    main() 