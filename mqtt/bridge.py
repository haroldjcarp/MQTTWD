"""
MQTT Bridge for C-Bus MQTT Bridge
Handles MQTT communication with Home Assistant
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List

import paho.mqtt.client as mqtt
from asyncio_mqtt import Client as AsyncMQTTClient

from config.config import Config
from cbus.state_manager import StateManager
from devices.manager import DeviceManager, DeviceType


class MQTTBridge:
    """MQTT bridge for Home Assistant communication."""
    
    def __init__(self, config: Config, state_manager: StateManager, device_manager: DeviceManager):
        self.config = config
        self.state_manager = state_manager
        self.device_manager = device_manager
        self.logger = logging.getLogger(__name__)
        
        # MQTT client
        self.client = None
        self.connected = False
        
        # Configuration
        self.broker = config.get('mqtt.broker')
        self.port = config.get('mqtt.port', 1883)
        self.username = config.get('mqtt.username')
        self.password = config.get('mqtt.password')
        self.keepalive = config.get('mqtt.keepalive', 60)
        self.reconnect_delay = config.get('mqtt.reconnect_delay', 5)
        
        # Topics
        self.command_topic = config.get('mqtt.topics.command', 'cbus/command')
        self.state_topic = config.get('mqtt.topics.state', 'cbus/state')
        
        # Discovery
        self.discovery_enabled = config.get('discovery.enabled', True)
        self.discovery_prefix = config.get('discovery.prefix', 'homeassistant')
        
        # Tasks
        self.listen_task = None
        self.heartbeat_task = None
        
        # Statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.discovery_sent = 0
        
    async def initialize(self):
        """Initialize MQTT bridge."""
        self.logger.info("Initializing MQTT bridge")
        
        # Create MQTT client
        self.client = AsyncMQTTClient(
            hostname=self.broker,
            port=self.port,
            username=self.username,
            password=self.password,
            keepalive=self.keepalive,
            client_id="cbus_mqtt_bridge"
        )
        
        self.logger.info(f"MQTT bridge initialized for {self.broker}:{self.port}")
        
    async def start(self):
        """Start MQTT bridge."""
        self.logger.info("Starting MQTT bridge")
        
        try:
            # Connect to MQTT broker
            await self.client.__aenter__()
            self.connected = True
            
            # Subscribe to command topics
            await self._subscribe_to_commands()
            
            # Start message listener
            self.listen_task = asyncio.create_task(self._message_listener())
            
            # Start heartbeat
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Send discovery messages
            if self.discovery_enabled:
                await self._send_discovery_messages()
                
            self.logger.info("MQTT bridge started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start MQTT bridge: {e}")
            self.connected = False
            raise
            
    async def stop(self):
        """Stop MQTT bridge."""
        self.logger.info("Stopping MQTT bridge")
        
        # Cancel tasks
        if self.listen_task:
            self.listen_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            
        # Disconnect
        if self.client and self.connected:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception as e:
                self.logger.error(f"Error disconnecting MQTT client: {e}")
                
        self.connected = False
        self.logger.info("MQTT bridge stopped")
        
    async def _subscribe_to_commands(self):
        """Subscribe to command topics."""
        # Subscribe to individual device commands
        command_pattern = f"{self.command_topic}/+/+/set"
        await self.client.subscribe(command_pattern)
        self.logger.debug(f"Subscribed to {command_pattern}")
        
        # Subscribe to discovery refresh
        discovery_topic = f"{self.discovery_prefix}/cbus/discovery"
        await self.client.subscribe(discovery_topic)
        self.logger.debug(f"Subscribed to {discovery_topic}")
        
    async def _message_listener(self):
        """Listen for MQTT messages."""
        self.logger.info("Starting MQTT message listener")
        
        async for message in self.client.messages:
            try:
                await self._handle_message(message)
                self.messages_received += 1
                
            except Exception as e:
                self.logger.error(f"Error handling MQTT message: {e}")
                
    async def _handle_message(self, message):
        """Handle incoming MQTT message."""
        topic = message.topic
        payload = message.payload.decode()
        
        self.logger.debug(f"Received message on {topic}: {payload}")
        
        # Handle device commands
        if topic.startswith(self.command_topic):
            await self._handle_device_command(topic, payload)
            
        # Handle discovery refresh
        elif topic.endswith("/discovery"):
            await self._send_discovery_messages()
            
    async def _handle_device_command(self, topic: str, payload: str):
        """Handle device command message."""
        # Parse topic: cbus/command/light/1/set
        topic_parts = topic.split('/')
        if len(topic_parts) >= 4:
            device_type = topic_parts[2]
            group = int(topic_parts[3])
            command = topic_parts[4] if len(topic_parts) > 4 else 'set'
            
            try:
                # Parse command payload
                if payload.lower() in ['on', 'true', '1']:
                    level = 255
                elif payload.lower() in ['off', 'false', '0']:
                    level = 0
                else:
                    # Try to parse as brightness/level
                    try:
                        level = int(payload)
                        level = max(0, min(255, level))  # Clamp to valid range
                    except ValueError:
                        # Try JSON payload
                        try:
                            data = json.loads(payload)
                            level = data.get('brightness', data.get('level', 0))
                        except json.JSONDecodeError:
                            self.logger.warning(f"Invalid payload for {topic}: {payload}")
                            return
                
                # Send command to state manager
                await self.state_manager.handle_mqtt_command(group, level)
                
                self.logger.debug(f"Processed command: group {group} -> {level}")
                
            except Exception as e:
                self.logger.error(f"Error processing device command: {e}")
                
    async def _heartbeat_loop(self):
        """Heartbeat loop for connection monitoring."""
        while self.connected:
            try:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
                # Send status update
                await self._send_status_update()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)
                
    async def _send_status_update(self):
        """Send status update to MQTT."""
        status = {
            'status': 'online',
            'timestamp': asyncio.get_event_loop().time(),
            'statistics': {
                'messages_sent': self.messages_sent,
                'messages_received': self.messages_received,
                'discovery_sent': self.discovery_sent,
                'devices': len(self.device_manager.get_devices())
            }
        }
        
        await self._publish(f"{self.state_topic}/bridge/status", json.dumps(status))
        
    async def _send_discovery_messages(self):
        """Send Home Assistant discovery messages."""
        if not self.discovery_enabled:
            return
            
        self.logger.info("Sending Home Assistant discovery messages")
        
        devices = self.device_manager.get_devices()
        
        for device in devices:
            try:
                await self._send_device_discovery(device)
                self.discovery_sent += 1
                
            except Exception as e:
                self.logger.error(f"Error sending discovery for device {device.name}: {e}")
                
        self.logger.info(f"Sent {self.discovery_sent} discovery messages")
        
    async def _send_device_discovery(self, device):
        """Send discovery message for a device."""
        # Get device configuration
        config = device.to_ha_config()
        
        # Add MQTT topics
        device_topic_base = f"{self.state_topic}/{device.device_type.value}/{device.group}"
        
        config.update({
            'state_topic': f"{device_topic_base}/state",
            'command_topic': f"{self.command_topic}/{device.device_type.value}/{device.group}/set",
            'availability_topic': f"{self.state_topic}/bridge/status",
            'availability_template': "{{ 'online' if value_json.status == 'online' else 'offline' }}",
            'payload_on': 'ON',
            'payload_off': 'OFF',
            'optimistic': False
        })
        
        # Device-specific configuration
        if device.device_type == DeviceType.LIGHT:
            if device.dimmable:
                config.update({
                    'brightness_state_topic': f"{device_topic_base}/brightness",
                    'brightness_command_topic': f"{self.command_topic}/{device.device_type.value}/{device.group}/brightness/set",
                    'brightness_scale': 255,
                    'on_command_type': 'brightness'
                })
        elif device.device_type == DeviceType.FAN:
            if device.dimmable:
                config.update({
                    'speed_state_topic': f"{device_topic_base}/speed",
                    'speed_command_topic': f"{self.command_topic}/{device.device_type.value}/{device.group}/speed/set",
                    'speed_range_min': 1,
                    'speed_range_max': 255
                })
        
        # Send discovery message
        discovery_topic = f"{self.discovery_prefix}/{device.device_type.value}/cbus_{device.group}/config"
        await self._publish(discovery_topic, json.dumps(config), retain=True)
        
        self.logger.debug(f"Sent discovery for {device.name}: {discovery_topic}")
        
    async def publish_state_update(self, group: int, level: int, state: bool):
        """Publish state update to MQTT."""
        device = self.device_manager.get_device(group)
        if not device:
            # Try to discover the device
            device = await self.device_manager.discover_device(group)
            if device and self.discovery_enabled:
                await self._send_device_discovery(device)
                
        if device:
            device_topic_base = f"{self.state_topic}/{device.device_type.value}/{group}"
            
            # Publish state
            state_payload = 'ON' if state else 'OFF'
            await self._publish(f"{device_topic_base}/state", state_payload)
            
            # Publish brightness/level if dimmable
            if device.dimmable:
                if device.device_type == DeviceType.LIGHT:
                    await self._publish(f"{device_topic_base}/brightness", str(level))
                elif device.device_type == DeviceType.FAN:
                    await self._publish(f"{device_topic_base}/speed", str(level))
                    
            self.logger.debug(f"Published state update: {device.name} -> {state_payload} ({level})")
            
    async def _publish(self, topic: str, payload: str, retain: bool = False):
        """Publish message to MQTT."""
        if not self.connected:
            self.logger.warning("Cannot publish - not connected to MQTT broker")
            return
            
        try:
            await self.client.publish(topic, payload, retain=retain)
            self.messages_sent += 1
            self.logger.debug(f"Published to {topic}: {payload}")
            
        except Exception as e:
            self.logger.error(f"Error publishing to {topic}: {e}")
            
    async def send_device_discovery(self, group: int):
        """Send discovery message for a specific device."""
        device = self.device_manager.get_device(group)
        if device:
            await self._send_device_discovery(device)
            
    async def remove_device_discovery(self, group: int):
        """Remove discovery message for a device."""
        device = self.device_manager.get_device(group)
        if device:
            discovery_topic = f"{self.discovery_prefix}/{device.device_type.value}/cbus_{group}/config"
            await self._publish(discovery_topic, "", retain=True)
            self.logger.info(f"Removed discovery for {device.name}")
            
    async def refresh_discovery(self):
        """Refresh all discovery messages."""
        await self._send_discovery_messages()
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get MQTT bridge statistics."""
        return {
            'connected': self.connected,
            'broker': self.broker,
            'port': self.port,
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'discovery_sent': self.discovery_sent,
            'discovery_enabled': self.discovery_enabled,
            'discovery_prefix': self.discovery_prefix
        } 