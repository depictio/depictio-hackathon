"""WebSocket connection manager for broadcasting updates."""

import json
import logging
from datetime import datetime
from typing import Dict, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.channels: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: Optional[str] = None):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        if channel:
            if channel not in self.channels:
                self.channels[channel] = set()
            self.channels[channel].add(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, channel: Optional[str] = None):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        if channel and channel in self.channels:
            self.channels[channel].discard(websocket)
            if not self.channels[channel]:
                del self.channels[channel]
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict, channel: Optional[str] = None):
        """Broadcast a message to all connected clients or a specific channel."""
        data = json.dumps(message)
        targets = self.channels.get(channel, set()) if channel else self.active_connections

        dead_connections = set()
        for connection in targets:
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.warning(f"Send failed: {e}")
                dead_connections.add(connection)

        for conn in dead_connections:
            self.disconnect(conn, channel)

    async def notify_new_images(self, count: int, total: int, new_rows_info: list):
        """Broadcast new image notifications to all clients."""
        message = {
            "type": "new_image",
            "count": count,
            "total": total,
            "images": new_rows_info,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted {count} new images")


manager = ConnectionManager()
