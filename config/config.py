"""
Configuration management for CBus MQTT Bridge
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles
import yaml


class Config:
    """Configuration manager for CBus MQTT Bridge."""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        self.data = {}
        self.logger = logging.getLogger(__name__)
        
    async def load(self):
        """Load configuration from file."""
        try:
            async with aiofiles.open(self.config_path, 'r') as f:
                content = await f.read()
                self.data = yaml.safe_load(content)
                
            self.logger.info(f"Configuration loaded from {self.config_path}")
            
            # Validate configuration
            self._validate_config()
            
            # Load additional configuration files
            await self._load_additional_configs()
            
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Invalid YAML in configuration: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise
            
    async def _load_additional_configs(self):
        """Load additional configuration files."""
        # Load devices configuration
        devices_path = self.config_dir / "devices.yaml"
        if devices_path.exists():
            try:
                async with aiofiles.open(devices_path, 'r') as f:
                    content = await f.read()
                    devices_config = yaml.safe_load(content)
                    self.data['devices'] = devices_config.get('devices', [])
                    self.data['templates'] = devices_config.get('templates', [])
                    self.logger.info(f"Devices configuration loaded from {devices_path}")
            except Exception as e:
                self.logger.warning(f"Could not load devices configuration: {e}")
        
        # Load areas configuration
        areas_path = self.config_dir / "areas.yaml"
        if areas_path.exists():
            try:
                async with aiofiles.open(areas_path, 'r') as f:
                    content = await f.read()
                    areas_config = yaml.safe_load(content)
                    self.data['areas'] = areas_config.get('areas', [])
                    self.logger.info(f"Areas configuration loaded from {areas_path}")
            except Exception as e:
                self.logger.warning(f"Could not load areas configuration: {e}")
                
    def _validate_config(self):
        """Validate configuration structure."""
        required_sections = ['cbus', 'mqtt']
        
        for section in required_sections:
            if section not in self.data:
                raise ValueError(f"Missing required configuration section: {section}")
                
        # Validate C-Bus configuration
        cbus_config = self.data['cbus']
        if 'interface' not in cbus_config:
            raise ValueError("Missing 'interface' in cbus configuration")
            
        interface_type = cbus_config['interface']
        if interface_type == 'tcp':
            if 'host' not in cbus_config:
                raise ValueError("Missing 'host' for TCP interface")
            if 'port' not in cbus_config:
                cbus_config['port'] = 10001  # Default CNI port
        elif interface_type == 'serial':
            if 'serial_port' not in cbus_config:
                raise ValueError("Missing 'serial_port' for serial interface")
        elif interface_type == 'pci':
            if 'pci_device' not in cbus_config:
                cbus_config['pci_device'] = '/dev/ttyUSB0'  # Default
        else:
            raise ValueError(f"Invalid interface type: {interface_type}")
            
        # Set defaults
        cbus_config.setdefault('network', 254)
        cbus_config.setdefault('application', 56)
        cbus_config.setdefault('monitoring', {})
        cbus_config['monitoring'].setdefault('enabled', True)
        cbus_config['monitoring'].setdefault('poll_interval', 30)
        cbus_config['monitoring'].setdefault('max_retries', 3)
        cbus_config['monitoring'].setdefault('timeout', 5)
        
        # Validate MQTT configuration
        mqtt_config = self.data['mqtt']
        if 'broker' not in mqtt_config:
            raise ValueError("Missing 'broker' in mqtt configuration")
            
        mqtt_config.setdefault('port', 1883)
        mqtt_config.setdefault('keepalive', 60)
        mqtt_config.setdefault('reconnect_delay', 5)
        mqtt_config.setdefault('topics', {})
        mqtt_config['topics'].setdefault('command', 'cbus/command')
        mqtt_config['topics'].setdefault('state', 'cbus/state')
        
        # Set discovery defaults
        self.data.setdefault('discovery', {})
        self.data['discovery'].setdefault('enabled', True)
        self.data['discovery'].setdefault('prefix', 'homeassistant')
        
        # Set logging defaults
        self.data.setdefault('logging', {})
        self.data['logging'].setdefault('level', 'INFO')
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def set(self, key: str, value: Any):
        """Set configuration value using dot notation."""
        keys = key.split('.')
        data = self.data
        
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
            
        data[keys[-1]] = value
        
    def get_devices(self) -> list:
        """Get devices configuration."""
        return self.data.get('devices', [])
        
    def get_templates(self) -> list:
        """Get device templates."""
        return self.data.get('templates', [])
        
    def get_areas(self) -> list:
        """Get areas configuration."""
        return self.data.get('areas', [])
        
    def get_cbus_config(self) -> dict:
        """Get C-Bus configuration."""
        return self.data.get('cbus', {})
        
    def get_mqtt_config(self) -> dict:
        """Get MQTT configuration."""
        return self.data.get('mqtt', {})
        
    def get_discovery_config(self) -> dict:
        """Get discovery configuration."""
        return self.data.get('discovery', {})
        
    def is_monitoring_enabled(self) -> bool:
        """Check if monitoring is enabled."""
        return self.get('cbus.monitoring.enabled', True)
        
    def get_poll_interval(self) -> int:
        """Get polling interval."""
        return self.get('cbus.monitoring.poll_interval', 30)
        
    def get_max_retries(self) -> int:
        """Get maximum retries."""
        return self.get('cbus.monitoring.max_retries', 3)
        
    def get_timeout(self) -> int:
        """Get timeout value."""
        return self.get('cbus.monitoring.timeout', 5)
        
    def to_dict(self) -> dict:
        """Return configuration as dictionary."""
        return self.data.copy() 