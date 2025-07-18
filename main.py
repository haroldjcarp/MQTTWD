#!/usr/bin/env python3
"""
CBus MQTT Bridge - Main Entry Point
An improved C-Bus to MQTT bridge for Home Assistant with better state tracking.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import click
import colorlog
import yaml

from cbus.interface import CBusInterface
from cbus.state_manager import StateManager
from mqtt.bridge import MQTTBridge
from devices.manager import DeviceManager
from config.config import Config


# Configure logging
def setup_logging(level: str = "INFO", log_file: str = None):
    """Setup logging configuration."""
    # Create colored console handler
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))
    logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(file_handler)
    
    # Reduce noise from external libraries
    logging.getLogger("paho.mqtt").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


class CBusMQTTBridge:
    """Main application class for CBus MQTT Bridge."""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = None
        self.cbus_interface = None
        self.state_manager = None
        self.mqtt_bridge = None
        self.device_manager = None
        self.running = False
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize all components."""
        self.logger.info("Initializing CBus MQTT Bridge...")
        
        # Load configuration
        self.config = Config(self.config_path)
        await self.config.load()
        
        # Setup logging with config
        setup_logging(
            level=self.config.get("logging.level", "INFO"),
            log_file=self.config.get("logging.file")
        )
        
        # Initialize device manager
        self.device_manager = DeviceManager(self.config)
        await self.device_manager.initialize()
        
        # Initialize C-Bus interface
        self.cbus_interface = CBusInterface(self.config)
        await self.cbus_interface.initialize()
        
        # Initialize state manager
        self.state_manager = StateManager(
            self.config,
            self.cbus_interface,
            self.device_manager
        )
        await self.state_manager.initialize()
        
        # Initialize MQTT bridge
        self.mqtt_bridge = MQTTBridge(
            self.config,
            self.state_manager,
            self.device_manager
        )
        await self.mqtt_bridge.initialize()
        
        # Connect components
        self.state_manager.set_mqtt_bridge(self.mqtt_bridge)
        
        self.logger.info("CBus MQTT Bridge initialized successfully")
        
    async def start(self):
        """Start the bridge."""
        self.logger.info("Starting CBus MQTT Bridge...")
        
        # Start all components
        await self.cbus_interface.start()
        await self.state_manager.start()
        await self.mqtt_bridge.start()
        
        self.running = True
        self.logger.info("CBus MQTT Bridge started successfully")
        
    async def stop(self):
        """Stop the bridge."""
        self.logger.info("Stopping CBus MQTT Bridge...")
        
        self.running = False
        
        # Stop all components
        if self.mqtt_bridge:
            await self.mqtt_bridge.stop()
        if self.state_manager:
            await self.state_manager.stop()
        if self.cbus_interface:
            await self.cbus_interface.stop()
            
        self.logger.info("CBus MQTT Bridge stopped")
        
    async def run(self):
        """Run the bridge main loop."""
        try:
            await self.initialize()
            await self.start()
            
            # Main loop
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise
        finally:
            await self.stop()


@click.command()
@click.option(
    "--config", "-c",
    default="config/config.yaml",
    help="Path to configuration file",
    type=click.Path(exists=True)
)
@click.option(
    "--debug", "-d",
    is_flag=True,
    help="Enable debug logging"
)
def main(config: str, debug: bool):
    """CBus MQTT Bridge - Connect C-Bus to Home Assistant via MQTT."""
    
    # Setup basic logging
    level = "DEBUG" if debug else "INFO"
    setup_logging(level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting CBus MQTT Bridge")
    
    # Create and run the bridge
    bridge = CBusMQTTBridge(config)
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        bridge.running = False
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(bridge.run())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 