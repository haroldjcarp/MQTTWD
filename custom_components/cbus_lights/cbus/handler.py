"""C-Bus communication handler."""

import asyncio
import logging
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)


class CBusHandler:
    """Handle C-Bus communication."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize the C-Bus handler."""
        self._host = host
        self._port = port
        self._connected = False
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> bool:
        """Connect to C-Bus CNI."""
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self._host, self._port
            )
            self._connected = True
            _LOGGER.info("Connected to C-Bus CNI at %s:%s", self._host, self._port)
            return True
        except Exception as err:
            _LOGGER.error("Failed to connect to C-Bus CNI: %s", err)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from C-Bus CNI."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._connected = False
        _LOGGER.info("Disconnected from C-Bus CNI")

    async def send_command(self, command: str) -> bool:
        """Send a command to C-Bus."""
        if not self._connected or not self._writer:
            _LOGGER.error("Not connected to C-Bus CNI")
            return False

        try:
            self._writer.write(command.encode() + b"\n")
            await self._writer.drain()
            _LOGGER.debug("Sent C-Bus command: %s", command)
            return True
        except Exception as err:
            _LOGGER.error("Failed to send C-Bus command: %s", err)
            return False

    async def set_light_level(self, group_address: int, level: int) -> bool:
        """Set light level for a group address."""
        # C-Bus lighting command format: lighting ramp group_address level
        if level == 0:
            command = f"lighting off {group_address}"
        else:
            command = f"lighting ramp {group_address} {level}"

        return await self.send_command(command)

    async def get_light_level(self, group_address: int) -> Optional[int]:
        """Get current light level for a group address."""
        if not self._connected or not self._reader:
            return None

        try:
            command = f"get lighting {group_address}"
            await self.send_command(command)

            # Read response (simplified - in real implementation you'd parse the response)
            response = await self._reader.readline()
            _LOGGER.debug("C-Bus response: %s", response.decode().strip())

            # For now, return a placeholder value
            # In real implementation, you'd parse the actual response
            return 255 if response else 0

        except Exception as err:
            _LOGGER.error("Failed to get light level: %s", err)
            return None

    @property
    def connected(self) -> bool:
        """Return connection status."""
        return self._connected
