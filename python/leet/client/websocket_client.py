"""WebSocket Client for 1337.

Enables connecting via WebSocket for:
- Browsers
- Real-time communication
- Bidirectional streaming
- Automatic heartbeat
- Smart reconnection

Example:
    >>> from leet.client import WebSocketClient
    >>>
    >>> client = WebSocketClient("ws://localhost:8080/ws")
    >>> await client.connect()
    >>> await client.send({"type": "COGON", "data": cogon.to_dict()})
"""

from __future__ import annotations

import asyncio
import json
import time
import warnings
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, AsyncIterator
from enum import Enum

# Try to import websockets
try:
    import websockets
    from websockets.exceptions import ConnectionClosed, ConnectionClosedOK
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False
    warnings.warn("websockets not installed. WebSocket client unavailable.")


class WSConnectionState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSED = "closed"


@dataclass
class WSMessage:
    """WebSocket message."""
    msg_type: str
    payload: dict
    timestamp: Optional[float] = None
    msg_id: str = field(default_factory=lambda: str(int(time.time() * 1000000)))

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_json(self) -> str:
        return json.dumps({
            "type": self.msg_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "msg_id": self.msg_id
        })

    @classmethod
    def from_json(cls, data: str) -> "WSMessage":
        d = json.loads(data)
        return cls(
            msg_type=d["type"],
            payload=d["payload"],
            timestamp=d.get("timestamp"),
            msg_id=d.get("msg_id", str(int(time.time() * 1000000)))
        )


@dataclass
class ConnectionStats:
    """Connection statistics."""
    connected_at: Optional[float] = None
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    reconnects: int = 0
    errors: int = 0

    @property
    def uptime(self) -> float:
        if self.connected_at:
            return time.time() - self.connected_at
        return 0.0


class WebSocketClient:
    """WebSocket client for 1337.

    Connects to a WebSocket server for real-time
    bidirectional communication.

    Args:
        url: WebSocket URL (ws:// or wss://)
        auto_reconnect: Automatically reconnect
        reconnect_delay: Delay between reconnections
        heartbeat_interval: Heartbeat interval (seconds)
        heartbeat_timeout: Timeout for heartbeat response

    Example:
        >>> client = WebSocketClient("ws://localhost:8080/ws")
        >>> await client.connect()
        >>>
        >>> # Send message
        >>> await client.send_cogon(cogon)
        >>>
        >>> # Receive messages
        >>> async for msg in client.receive():
        ...     print(msg)
    """

    def __init__(
        self,
        url: str,
        auto_reconnect: bool = True,
        reconnect_delay: float = 5.0,
        max_reconnects: int = 10,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 10.0
    ):
        if not WS_AVAILABLE:
            raise RuntimeError(
                "websockets not installed. "
                "Install with: pip install websockets"
            )

        self.url = url
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        self.max_reconnects = max_reconnects
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout

        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._state = WSConnectionState.DISCONNECTED
        self._stats = ConnectionStats()

        # Handlers
        self._message_handlers: list[Callable[[WSMessage], Any]] = []
        self._error_handlers: list[Callable[[Exception], Any]] = []
        self._connect_handlers: list[Callable[[], Any]] = []
        self._disconnect_handlers: list[Callable[[], Any]] = []

        # Tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._pending_heartbeats: dict[str, asyncio.Future] = {}

    @property
    def state(self) -> WSConnectionState:
        """Current connection state."""
        return self._state

    @property
    def connected(self) -> bool:
        """Checks whether it is connected."""
        return self._state == WSConnectionState.CONNECTED and self._websocket is not None

    @property
    def stats(self) -> ConnectionStats:
        """Connection statistics."""
        return self._stats

    async def connect(self) -> "WebSocketClient":
        """Connects to the WebSocket server."""
        self._state = WSConnectionState.CONNECTING

        try:
            self._websocket = await websockets.connect(self.url)
            self._state = WSConnectionState.CONNECTED
            self._stats.connected_at = time.time()

            # Start loops
            self._receive_task = asyncio.create_task(self._receive_loop())
            if self.heartbeat_interval > 0:
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Notify handlers
            for handler in self._connect_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler())
                    else:
                        handler()
                except Exception:
                    pass

            return self

        except Exception as e:
            self._state = WSConnectionState.DISCONNECTED
            if self.auto_reconnect and self._stats.reconnects < self.max_reconnects:
                self._stats.reconnects += 1
                await asyncio.sleep(self.reconnect_delay)
                return await self.connect()
            raise ConnectionError(f"Failed to connect: {e}")

    async def close(self):
        """Closes the connection."""
        self._state = WSConnectionState.CLOSED

        # Cancel tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        # Cancel pending heartbeats
        for future in self._pending_heartbeats.values():
            if not future.done():
                future.cancel()
        self._pending_heartbeats.clear()

        # Close websocket
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass

        # Notify handlers
        for handler in self._disconnect_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler())
                else:
                    handler()
            except Exception:
                pass

    async def __aenter__(self) -> "WebSocketClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def on_connect(self, handler: Callable[[], Any]):
        """Registers a handler for a connection being established."""
        self._connect_handlers.append(handler)

    def on_disconnect(self, handler: Callable[[], Any]):
        """Registers a handler for disconnection."""
        self._disconnect_handlers.append(handler)

    def on_message(self, handler: Callable[[WSMessage], Any]):
        """Registers a handler for messages."""
        self._message_handlers.append(handler)

    def on_error(self, handler: Callable[[Exception], Any]):
        """Registers a handler for errors."""
        self._error_handlers.append(handler)

    async def send(self, data: str) -> bool:
        """Sends a string. Returns True if sent."""
        if not self.connected or not self._websocket:
            raise ConnectionError("Not connected")

        try:
            await self._websocket.send(data)
            self._stats.messages_sent += 1
            self._stats.bytes_sent += len(data.encode())
            return True
        except Exception as e:
            await self._notify_error(e)
            return False

    async def send_json(self, data: dict) -> bool:
        """Sends JSON."""
        return await self.send(json.dumps(data))

    async def send_message(self, message: WSMessage) -> bool:
        """Sends a WSMessage."""
        return await self.send(message.to_json())

    async def send_cogon(self, cogon: Any, receiver: str = "") -> bool:
        """Sends a COGON."""
        from leet.types import Cogon

        if not isinstance(cogon, Cogon):
            raise TypeError("Expected Cogon instance")

        msg = WSMessage(
            msg_type="COGON",
            payload={
                "cogon": json.loads(cogon.to_json()),
                "receiver": receiver
            }
        )
        return await self.send_message(msg)

    async def send_msg1337(self, msg1337: Any) -> bool:
        """Sends a full MSG_1337."""
        msg = WSMessage(
            msg_type="MSG_1337",
            payload=json.loads(msg1337.to_json())
        )
        return await self.send_message(msg)

    async def ping(self) -> float:
        """Sends a ping and returns the latency in ms."""
        ping_id = str(int(time.time() * 1000000))
        ping_msg = WSMessage(
            msg_type="PING",
            payload={"ping_id": ping_id}
        )

        future: asyncio.Future = asyncio.Future()
        self._pending_heartbeats[ping_id] = future

        start_time = time.time()
        await self.send_message(ping_msg)

        try:
            await asyncio.wait_for(future, timeout=self.heartbeat_timeout)
            latency = (time.time() - start_time) * 1000  # ms
            return latency
        except asyncio.TimeoutError:
            return -1.0
        finally:
            self._pending_heartbeats.pop(ping_id, None)

    async def recv(self) -> str:
        """Receives a string."""
        if not self.connected or not self._websocket:
            raise ConnectionError("Not connected")

        return await self._websocket.recv()

    async def recv_json(self) -> dict:
        """Receives JSON."""
        data = await self.recv()
        return json.loads(data)

    async def recv_message(self) -> WSMessage:
        """Receives a message."""
        data = await self.recv()
        self._stats.messages_received += 1
        self._stats.bytes_received += len(data.encode())
        return WSMessage.from_json(data)

    async def receive(self) -> AsyncIterator[WSMessage]:
        """Iterator over messages."""
        queue: asyncio.Queue[WSMessage] = asyncio.Queue()

        def handler(msg):
            queue.put_nowait(msg)

        self.on_message(handler)

        try:
            while self.connected:
                msg = await queue.get()
                yield msg
        finally:
            if handler in self._message_handlers:
                self._message_handlers.remove(handler)

    async def stream_messages(self, msg_type: Optional[str] = None) -> AsyncIterator[WSMessage]:
        """Streams messages with an optional type filter."""
        async for msg in self.receive():
            if msg_type is None or msg.msg_type == msg_type:
                yield msg

    async def _receive_loop(self):
        """Receive loop."""
        while self.connected:
            try:
                msg = await self.recv_message()

                # Process heartbeats
                if msg.msg_type == "PONG":
                    ping_id = msg.payload.get("ping_id")
                    if ping_id and ping_id in self._pending_heartbeats:
                        future = self._pending_heartbeats.pop(ping_id)
                        if not future.done():
                            future.set_result(True)
                    continue

                # Notify handlers
                for handler in self._message_handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            asyncio.create_task(handler(msg))
                        else:
                            handler(msg)
                    except Exception as e:
                        await self._notify_error(e)

            except ConnectionClosedOK:
                break
            except ConnectionClosed:
                if self.auto_reconnect:
                    await self._reconnect()
                break
            except Exception as e:
                await self._notify_error(e)

    async def _heartbeat_loop(self):
        """Heartbeat loop."""
        while self.connected:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                if not self.connected:
                    break

                latency = await self.ping()
                if latency < 0:
                    # Heartbeat timeout
                    if self.auto_reconnect:
                        await self._reconnect()
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._notify_error(e)

    async def _reconnect(self):
        """Attempts to reconnect."""
        self._state = WSConnectionState.RECONNECTING

        if self._websocket:
            try:
                await self._websocket.close()
            except:
                pass

        while self.auto_reconnect and self._stats.reconnects < self.max_reconnects:
            try:
                self._stats.reconnects += 1
                await asyncio.sleep(self.reconnect_delay)
                await self.connect()
                return
            except Exception:
                pass

        self._state = WSConnectionState.DISCONNECTED

    async def _notify_error(self, error: Exception):
        """Notifies error handlers."""
        self._stats.errors += 1
        for handler in self._error_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(error))
                else:
                    handler(error)
            except:
                pass


class WebSocketManager:
    """Manager for multiple WebSocket connections.

    Useful for connecting to multiple agents or
    servers simultaneously.

    Example:
        >>> manager = WebSocketManager()
        >>>
        >>> # Connect to multiple servers
        >>> client1 = await manager.connect("ws://server1/ws")
        >>> client2 = await manager.connect("ws://server2/ws")
        >>>
        >>> # Broadcast to all
        >>> await manager.broadcast({"type": "hello"})
    """

    def __init__(self):
        self._clients: dict[str, WebSocketClient] = {}
        self._default_client: Optional[str] = None

    async def connect(
        self,
        url: str,
        client_id: Optional[str] = None,
        **kwargs
    ) -> WebSocketClient:
        """Connects and registers a client."""
        if client_id is None:
            client_id = f"client_{len(self._clients)}"

        client = WebSocketClient(url, **kwargs)
        await client.connect()

        self._clients[client_id] = client
        if self._default_client is None:
            self._default_client = client_id

        return client

    def get(self, client_id: Optional[str] = None) -> Optional[WebSocketClient]:
        """Gets a client by ID."""
        if client_id is None:
            client_id = self._default_client
        return self._clients.get(client_id)

    async def disconnect(self, client_id: Optional[str] = None):
        """Disconnects a client."""
        if client_id is None:
            # Disconnect all
            for client in list(self._clients.values()):
                await client.close()
            self._clients.clear()
            self._default_client = None
        else:
            client = self._clients.pop(client_id, None)
            if client:
                await client.close()
            if self._default_client == client_id:
                self._default_client = next(iter(self._clients), None)

    async def broadcast(self, data: dict) -> dict[str, bool]:
        """Sends a message to all clients."""
        results = {}
        for client_id, client in self._clients.items():
            try:
                results[client_id] = await client.send_json(data)
            except Exception:
                results[client_id] = False
        return results

    async def __aenter__(self) -> "WebSocketManager":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


# Exports
__all__ = [
    'WebSocketClient',
    'WebSocketManager',
    'WSMessage',
    'WSConnectionState',
    'ConnectionStats',
]
