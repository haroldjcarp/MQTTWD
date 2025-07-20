#!/usr/bin/env python3
"""
Get C-Bus light statuses via MQTT.
This script listens to MQTT topics to discover and monitor C-Bus lights.
"""

import asyncio
import json
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
import time

# Configuration - matches your Home Assistant MQTT setup
# Use your Home Assistant's IP address instead of core-mosquitto
MQTT_BROKER = "192.168.0.50"  # Your Home Assistant IP (same as C-Bus CNI)
MQTT_PORT = 1883
MQTT_USER = "pai"
MQTT_PASSWORD = "pai"

# MQTT Topics to monitor
TOPICS = [
    "cbus/+/state",           # Light states
    "cbus/+/+/state",         # Alternative format
    "cbus/light/+/state",     # Specific light states
    "homeassistant/+/+/state", # Home Assistant discovery
    "cbusmqtt/+/state",       # Alternative bridge format
]

class MQTTLightMonitor:
    def __init__(self):
        self.client = mqtt.Client()
        self.lights = {}
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
            for topic in TOPICS:
                client.subscribe(topic)
                print(f"📡 Subscribed to: {topic}")
                
            print("\n🔍 Listening for C-Bus light messages...")
            print("Turn lights on/off to see them appear here.\n")
            
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
            
            # Try to parse JSON payload
            try:
                data = json.loads(payload)
                if isinstance(data, dict):
                    payload_str = json.dumps(data, indent=2)
                else:
                    payload_str = str(data)
            except:
                payload_str = payload
            
            # Extract light info from topic
            light_id = self.extract_light_id(topic)
            
            print(f"[{timestamp}] 📨 {topic}")
            print(f"           💡 Light ID: {light_id or 'Unknown'}")
            print(f"           📄 Payload: {payload_str}")
            
            # Store light information
            if light_id:
                self.lights[light_id] = {
                    'topic': topic,
                    'payload': payload,
                    'last_seen': timestamp,
                    'data': data if 'data' in locals() else payload
                }
                
            print("-" * 60)
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            
    def extract_light_id(self, topic):
        """Extract light ID from MQTT topic."""
        parts = topic.split('/')
        
        # Look for numeric IDs in common positions
        for part in parts:
            if part.isdigit():
                return part
            # Look for light names/IDs
            if 'light' in part.lower() and part != 'light':
                return part
                
        return None
        
    def print_summary(self):
        """Print summary of discovered lights."""
        if self.lights:
            print("\n" + "="*60)
            print("📋 DISCOVERED LIGHTS SUMMARY")
            print("="*60)
            
            for light_id, info in self.lights.items():
                print(f"Light {light_id:>3}: Last seen {info['last_seen']} - {info['topic']}")
                
            print(f"\n✅ Total lights discovered: {len(self.lights)}")
        else:
            print("\n⚠️  No lights discovered yet.")
            print("Try turning some lights on/off to trigger MQTT messages.")
            
    def run(self, duration=60):
        """Run the MQTT monitor for specified duration."""
        print(f"🚀 Starting MQTT Light Monitor")
        print(f"Target: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"Duration: {duration} seconds\n")
        
        try:
            # Connect to MQTT broker
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            
            # Start the loop
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(1)
                timeout -= 1
                
            if not self.connected:
                print("❌ Failed to connect to MQTT broker")
                return
                
            # Monitor for specified duration
            print(f"⏱️  Monitoring for {duration} seconds... (Press Ctrl+C to stop early)")
            
            for remaining in range(duration, 0, -1):
                print(f"\r⏰ Time remaining: {remaining:3d}s | Lights found: {len(self.lights):2d}", end='', flush=True)
                time.sleep(1)
                
            print("\n")
            
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            self.print_summary()

if __name__ == "__main__":
    monitor = MQTTLightMonitor()
    
    print("C-Bus MQTT Light Status Monitor")
    print("This tool listens to MQTT messages to discover C-Bus lights")
    print("Make sure your C-Bus MQTT bridge is running!\n")
    
    # Ask for monitoring duration
    try:
        duration_input = input("Enter monitoring duration in seconds (default 60): ").strip()
        duration = int(duration_input) if duration_input else 60
    except:
        duration = 60
        
    monitor.run(duration) 