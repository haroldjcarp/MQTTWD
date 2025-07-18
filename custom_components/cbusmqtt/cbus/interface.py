"""C-Bus Interface for communication with C-Bus PCI/CNI devices."""

import asyncio
import logging
import socket
from typing import Optional, Dict, Any, Callable

import serial
import serial.aio

_LOGGER = logging.getLogger(__name__)


class CBusInterface:
    """Interface for C-Bus communication."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = _LOGGER
        self.connection = None
        self.connected = False
        self.event_callbacks = []
        self.command_queue = asyncio.Queue()
        self.response_queue = asyncio.Queue()
        self.monitoring_task = None
        self.command_task = None
        
        # Configuration
        self.interface_type = config.get('interface', 'tcp')
        self.host = config.get('host')
        self.port = config.get('port', 10001)
        self.serial_port = config.get('serial_port')
        self.network = config.get('network', 254)
        self.application = config.get('application', 56)
        self.timeout = config.get('monitoring', {}).get('timeout', 5)
        
    async def initialize(self):
        """Initialize the C-Bus interface."""
        self.logger.info(f"Initializing C-Bus interface ({self.interface_type})")
        
        if self.interface_type == 'tcp':
            await self._initialize_tcp()
        elif self.interface_type == 'serial':
            await self._initialize_serial()
        elif self.interface_type == 'pci':
            await self._initialize_pci()
        else:
            raise ValueError(f"Unsupported interface type: {self.interface_type}")
            
    async def _initialize_tcp(self):
        """Initialize TCP/CNI connection."""
        self.logger.info(f"Initializing TCP connection to {self.host}:{self.port}")
        
    async def _initialize_serial(self):
        """Initialize serial connection."""
        self.logger.info(f"Initializing serial connection to {self.serial_port}")
        
    async def _initialize_pci(self):
        """Initialize PCI connection."""
        self.logger.info("Initializing PCI connection")
        
    async def start(self):
        """Start the C-Bus interface."""
        await self.connect()
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Start command processing task
        self.command_task = asyncio.create_task(self._command_loop())
        
        self.logger.info("C-Bus interface started")
        
    async def stop(self):
        """Stop the C-Bus interface."""
        self.logger.info("Stopping C-Bus interface")
        
        # Cancel tasks
        if self.monitoring_task:
            self.monitoring_task.cancel()
        if self.command_task:
            self.command_task.cancel()
            
        # Disconnect
        await self.disconnect()
        
    async def connect(self):
        """Connect to C-Bus."""
        if self.connected:
            return
            
        try:
            if self.interface_type == 'tcp':
                await self._connect_tcp()
            elif self.interface_type == 'serial':
                await self._connect_serial()
            elif self.interface_type == 'pci':
                await self._connect_pci()
                
            self.connected = True
            self.logger.info("Connected to C-Bus")
            
            # Send initialization commands
            await self._send_init_commands()
            
        except Exception as e:
            self.logger.error(f"Failed to connect to C-Bus: {e}")
            raise
            
    async def _connect_tcp(self):
        """Connect via TCP/CNI."""
        try:
            # Create socket connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
            
            self.connection = {
                'reader': reader,
                'writer': writer,
                'type': 'tcp'
            }
            
            self.logger.info(f"TCP connection established to {self.host}:{self.port}")
            
        except asyncio.TimeoutError:
            raise ConnectionError(f"Connection timeout to {self.host}:{self.port}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect via TCP: {e}")
            
    async def _connect_serial(self):
        """Connect via serial."""
        try:
            # Create serial connection
            serial_conn = serial.aio.Serial(
                port=self.serial_port,
                baudrate=9600,
                timeout=self.timeout
            )
            
            self.connection = {
                'serial': serial_conn,
                'type': 'serial'
            }
            
            self.logger.info(f"Serial connection established to {self.serial_port}")
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect via serial: {e}")
            
    async def _connect_pci(self):
        """Connect via PCI."""
        try:
            serial_conn = serial.aio.Serial(
                port=self.serial_port,
                baudrate=9600,
                timeout=self.timeout
            )
            
            self.connection = {
                'serial': serial_conn,
                'type': 'pci'
            }
            
            self.logger.info("PCI connection established")
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect via PCI: {e}")
            
    async def disconnect(self):
        """Disconnect from C-Bus."""
        if not self.connected:
            return
            
        try:
            if self.connection:
                if self.connection['type'] == 'tcp':
                    self.connection['writer'].close()
                    await self.connection['writer'].wait_closed()
                elif self.connection['type'] in ['serial', 'pci']:
                    self.connection['serial'].close()
                    
            self.connection = None
            self.connected = False
            self.logger.info("Disconnected from C-Bus")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")
            
    async def _send_init_commands(self):
        """Send initialization commands to C-Bus."""
        # Enable monitoring
        await self._send_command("|||")  # Reset
        await asyncio.sleep(0.1)
        
        # Set network and application
        await self._send_command(f"\\{self.network:02X}")
        await self._send_command(f"@{self.application:02X}")
        
        # Enable monitoring
        await self._send_command("g")  # Enable monitoring
        
        self.logger.info("Initialization commands sent")
        
    async def _send_command(self, command: str):
        """Send a command to C-Bus."""
        if not self.connected or not self.connection:
            raise ConnectionError("Not connected to C-Bus")
            
        try:
            command_bytes = (command + "\r\n").encode('ascii')
            
            if self.connection['type'] == 'tcp':
                self.connection['writer'].write(command_bytes)
                await self.connection['writer'].drain()
            elif self.connection['type'] in ['serial', 'pci']:
                await self.connection['serial'].write(command_bytes)
                
            self.logger.debug(f"Sent command: {command}")
            
        except Exception as e:
            self.logger.error(f"Error sending command '{command}': {e}")
            raise
            
    async def _read_response(self) -> Optional[str]:
        """Read response from C-Bus."""
        if not self.connected or not self.connection:
            return None
            
        try:
            if self.connection['type'] == 'tcp':
                data = await asyncio.wait_for(
                    self.connection['reader'].readline(),
                    timeout=self.timeout
                )
                return data.decode('ascii').strip()
            elif self.connection['type'] in ['serial', 'pci']:
                data = await asyncio.wait_for(
                    self.connection['serial'].readline(),
                    timeout=self.timeout
                )
                return data.decode('ascii').strip()
                
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.logger.error(f"Error reading response: {e}")
            return None
            
    async def _monitoring_loop(self):
        """Main monitoring loop for C-Bus events."""
        self.logger.info("Starting monitoring loop")
        
        while self.connected:
            try:
                response = await self._read_response()
                if response:
                    await self._process_response(response)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(1)
                
        self.logger.info("Monitoring loop stopped")
        
    async def _command_loop(self):
        """Process command queue."""
        self.logger.info("Starting command loop")
        
        while self.connected:
            try:
                command = await asyncio.wait_for(
                    self.command_queue.get(),
                    timeout=1.0
                )
                
                await self._send_command(command)
                self.command_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in command loop: {e}")
                await asyncio.sleep(1)
                
        self.logger.info("Command loop stopped")
        
    async def _process_response(self, response: str):
        """Process a response from C-Bus."""
        self.logger.debug(f"Received response: {response}")
        
        # Parse C-Bus response
        if response.startswith("\\"):
            # Network response
            pass
        elif response.startswith("@"):
            # Application response
            pass
        elif response.startswith("g"):
            # Group response - this is where we get state updates
            await self._process_group_response(response)
        else:
            # Other response
            pass
            
    async def _process_group_response(self, response: str):
        """Process a group response."""
        try:
            # Parse group response format: gAAGGLL
            # AA = Application, GG = Group, LL = Level
            if len(response) >= 7:
                app_hex = response[1:3]
                group_hex = response[3:5]
                level_hex = response[5:7]
                
                application = int(app_hex, 16)
                group = int(group_hex, 16)
                level = int(level_hex, 16)
                
                # Only process if it's our application
                if application == self.application:
                    event = {
                        'type': 'group_state',
                        'application': application,
                        'group': group,
                        'level': level,
                        'state': level > 0
                    }
                    
                    # Notify callbacks
                    for callback in self.event_callbacks:
                        try:
                            await callback(event)
                        except Exception as e:
                            self.logger.error(f"Error in event callback: {e}")
                            
        except Exception as e:
            self.logger.error(f"Error processing group response: {e}")
            
    async def send_command(self, command: str):
        """Queue a command to be sent."""
        await self.command_queue.put(command)
        
    async def set_group_level(self, group: int, level: int):
        """Set a group to a specific level."""
        command = f"@{self.application:02X}{group:02X}{level:02X}"
        await self.send_command(command)
        
    async def get_group_level(self, group: int) -> Optional[int]:
        """Get current level of a group."""
        command = f"g{self.application:02X}{group:02X}"
        await self.send_command(command)
        
        # Wait for response (simplified - in real implementation you'd correlate responses)
        await asyncio.sleep(0.1)
        return None
        
    async def ramp_group(self, group: int, level: int, ramp_time: int = 0):
        """Ramp a group to a level over time."""
        if ramp_time > 0:
            command = f"@{self.application:02X}{group:02X}{level:02X}{ramp_time:02X}"
        else:
            command = f"@{self.application:02X}{group:02X}{level:02X}"
        await self.send_command(command)
        
    def add_event_callback(self, callback: Callable):
        """Add an event callback."""
        self.event_callbacks.append(callback)
        
    def remove_event_callback(self, callback: Callable):
        """Remove an event callback."""
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)
            
    async def ping(self) -> bool:
        """Ping C-Bus to check connection."""
        if not self.connected:
            return False
            
        try:
            await self._send_command("z")  # Status command
            return True
        except Exception:
            return False 