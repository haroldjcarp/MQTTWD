"""
State Manager for C-Bus MQTT Bridge
Handles device state tracking, validation, and synchronization
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from config.config import Config
from cbus.interface import CBusInterface
from devices.manager import DeviceManager


class StateSource(Enum):
    """Source of state change."""
    CBUS = "cbus"
    MQTT = "mqtt"
    POLL = "poll"
    UNKNOWN = "unknown"


@dataclass
class DeviceState:
    """Represents the state of a C-Bus device."""
    group: int
    level: int
    state: bool
    last_updated: float = field(default_factory=time.time)
    last_source: StateSource = StateSource.UNKNOWN
    last_mqtt_update: float = 0
    last_cbus_update: float = 0
    pending_mqtt_update: bool = False
    pending_cbus_update: bool = False
    
    def update(self, level: int, source: StateSource):
        """Update device state."""
        self.level = level
        self.state = level > 0
        self.last_updated = time.time()
        self.last_source = source
        
        if source == StateSource.CBUS:
            self.last_cbus_update = self.last_updated
            self.pending_cbus_update = False
        elif source == StateSource.MQTT:
            self.last_mqtt_update = self.last_updated
            self.pending_mqtt_update = False
    
    def age(self) -> float:
        """Get age of last update in seconds."""
        return time.time() - self.last_updated
    
    def is_stale(self, max_age: float = 60.0) -> bool:
        """Check if state is stale."""
        return self.age() > max_age


class StateManager:
    """Manages device states and synchronization."""
    
    def __init__(self, config: Config, cbus_interface: CBusInterface, device_manager: DeviceManager):
        self.config = config
        self.cbus_interface = cbus_interface
        self.device_manager = device_manager
        self.mqtt_bridge = None  # Set later
        self.logger = logging.getLogger(__name__)
        
        # State storage
        self.device_states: Dict[int, DeviceState] = {}
        self.state_lock = asyncio.Lock()
        
        # Configuration
        self.poll_interval = config.get_poll_interval()
        self.monitoring_enabled = config.is_monitoring_enabled()
        self.max_retries = config.get_max_retries()
        
        # Tasks
        self.poll_task = None
        self.sync_task = None
        self.cleanup_task = None
        
        # Tracking
        self.poll_errors = 0
        self.sync_conflicts = 0
        self.last_poll_time = 0
        
    async def initialize(self):
        """Initialize state manager."""
        self.logger.info("Initializing state manager")
        
        # Register for C-Bus events
        self.cbus_interface.add_event_callback(self._on_cbus_event)
        
        # Initialize states for configured devices
        devices = self.device_manager.get_devices()
        for device in devices:
            if device.group not in self.device_states:
                self.device_states[device.group] = DeviceState(
                    group=device.group,
                    level=0,
                    state=False
                )
        
        self.logger.info(f"Initialized state tracking for {len(self.device_states)} devices")
        
    async def start(self):
        """Start state manager tasks."""
        self.logger.info("Starting state manager")
        
        if self.monitoring_enabled:
            # Start polling task
            self.poll_task = asyncio.create_task(self._poll_loop())
            
            # Start synchronization task
            self.sync_task = asyncio.create_task(self._sync_loop())
            
            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
        self.logger.info("State manager started")
        
    async def stop(self):
        """Stop state manager tasks."""
        self.logger.info("Stopping state manager")
        
        # Cancel tasks
        if self.poll_task:
            self.poll_task.cancel()
        if self.sync_task:
            self.sync_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
            
        self.logger.info("State manager stopped")
        
    def set_mqtt_bridge(self, mqtt_bridge):
        """Set MQTT bridge reference."""
        self.mqtt_bridge = mqtt_bridge
        
    async def _on_cbus_event(self, event: Dict[str, Any]):
        """Handle C-Bus event."""
        if event['type'] == 'group_state':
            await self._update_device_state(
                group=event['group'],
                level=event['level'],
                source=StateSource.CBUS
            )
            
    async def _update_device_state(self, group: int, level: int, source: StateSource):
        """Update device state and notify MQTT if needed."""
        async with self.state_lock:
            # Get or create device state
            if group not in self.device_states:
                self.device_states[group] = DeviceState(
                    group=group,
                    level=0,
                    state=False
                )
            
            device_state = self.device_states[group]
            old_level = device_state.level
            old_state = device_state.state
            
            # Update state
            device_state.update(level, source)
            
            # Check if state actually changed
            if old_level != level or old_state != device_state.state:
                self.logger.debug(f"Group {group}: {old_level} -> {level} (source: {source.value})")
                
                # Notify MQTT bridge if state came from C-Bus
                if source == StateSource.CBUS and self.mqtt_bridge:
                    await self.mqtt_bridge.publish_state_update(group, level, device_state.state)
                    
                # Update statistics
                if source == StateSource.CBUS:
                    self.cbus_interface.last_cbus_update = time.time()
                    
    async def _poll_loop(self):
        """Polling loop to check device states."""
        self.logger.info("Starting polling loop")
        
        while True:
            try:
                await asyncio.sleep(self.poll_interval)
                
                if await self._should_poll():
                    await self._poll_devices()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}")
                self.poll_errors += 1
                await asyncio.sleep(5)  # Wait before retrying
                
        self.logger.info("Polling loop stopped")
        
    async def _should_poll(self) -> bool:
        """Check if we should poll devices."""
        # Don't poll if we're getting regular C-Bus events
        if time.time() - self.last_poll_time < self.poll_interval:
            return False
            
        # Check if we've received recent C-Bus events
        recent_events = any(
            state.last_cbus_update > time.time() - self.poll_interval
            for state in self.device_states.values()
        )
        
        # Poll if no recent events or if we have stale states
        if not recent_events:
            return True
            
        # Check for stale states
        stale_states = any(
            state.is_stale(self.poll_interval * 2)
            for state in self.device_states.values()
        )
        
        return stale_states
        
    async def _poll_devices(self):
        """Poll all devices for current state."""
        self.logger.debug("Polling devices for state")
        
        poll_start = time.time()
        polled_count = 0
        
        for group in self.device_states.keys():
            try:
                # Request current level
                await self.cbus_interface.send_command(f"g{self.cbus_interface.application:02X}{group:02X}")
                polled_count += 1
                
                # Small delay to avoid overwhelming the interface
                await asyncio.sleep(0.05)
                
            except Exception as e:
                self.logger.error(f"Error polling group {group}: {e}")
                
        self.last_poll_time = time.time()
        poll_duration = self.last_poll_time - poll_start
        
        self.logger.debug(f"Polled {polled_count} devices in {poll_duration:.2f}s")
        
    async def _sync_loop(self):
        """Synchronization loop to handle conflicts."""
        self.logger.info("Starting synchronization loop")
        
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                await self._check_sync_conflicts()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(10)
                
        self.logger.info("Synchronization loop stopped")
        
    async def _check_sync_conflicts(self):
        """Check for and resolve synchronization conflicts."""
        async with self.state_lock:
            for group, state in self.device_states.items():
                # Check for pending updates that might conflict
                if state.pending_mqtt_update and state.pending_cbus_update:
                    # Resolve conflict - C-Bus wins
                    self.logger.warning(f"Sync conflict for group {group}, C-Bus takes precedence")
                    state.pending_mqtt_update = False
                    self.sync_conflicts += 1
                    
                    # Notify MQTT of the actual state
                    if self.mqtt_bridge:
                        await self.mqtt_bridge.publish_state_update(group, state.level, state.state)
                        
    async def _cleanup_loop(self):
        """Cleanup loop to remove stale states."""
        self.logger.info("Starting cleanup loop")
        
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._cleanup_stale_states()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
                
        self.logger.info("Cleanup loop stopped")
        
    async def _cleanup_stale_states(self):
        """Remove stale device states."""
        async with self.state_lock:
            # Find stale states
            stale_groups = [
                group for group, state in self.device_states.items()
                if state.is_stale(3600)  # 1 hour
            ]
            
            # Remove stale states
            for group in stale_groups:
                del self.device_states[group]
                self.logger.debug(f"Removed stale state for group {group}")
                
    async def handle_mqtt_command(self, group: int, level: int, source: str = "mqtt"):
        """Handle MQTT command to change device state."""
        try:
            # Send command to C-Bus
            await self.cbus_interface.set_group_level(group, level)
            
            # Mark as pending update
            async with self.state_lock:
                if group in self.device_states:
                    self.device_states[group].pending_cbus_update = True
                    
            # Update local state optimistically
            await self._update_device_state(group, level, StateSource.MQTT)
            
            self.logger.debug(f"MQTT command sent: group {group} -> {level}")
            
        except Exception as e:
            self.logger.error(f"Error handling MQTT command for group {group}: {e}")
            
    async def handle_mqtt_ramp(self, group: int, level: int, ramp_time: int):
        """Handle MQTT ramp command."""
        try:
            await self.cbus_interface.ramp_group(group, level, ramp_time)
            
            # Mark as pending update
            async with self.state_lock:
                if group in self.device_states:
                    self.device_states[group].pending_cbus_update = True
                    
            self.logger.debug(f"MQTT ramp command sent: group {group} -> {level} over {ramp_time}s")
            
        except Exception as e:
            self.logger.error(f"Error handling MQTT ramp for group {group}: {e}")
            
    async def get_device_state(self, group: int) -> Optional[DeviceState]:
        """Get current device state."""
        async with self.state_lock:
            return self.device_states.get(group)
            
    async def get_all_states(self) -> Dict[int, DeviceState]:
        """Get all device states."""
        async with self.state_lock:
            return self.device_states.copy()
            
    async def force_refresh(self, group: int = None):
        """Force refresh of device states."""
        if group is not None:
            # Refresh specific group
            await self.cbus_interface.get_group_level(group)
        else:
            # Refresh all groups
            await self._poll_devices()
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get state manager statistics."""
        return {
            'device_count': len(self.device_states),
            'poll_errors': self.poll_errors,
            'sync_conflicts': self.sync_conflicts,
            'last_poll_time': self.last_poll_time,
            'monitoring_enabled': self.monitoring_enabled,
            'poll_interval': self.poll_interval,
            'stale_states': sum(1 for state in self.device_states.values() if state.is_stale())
        } 