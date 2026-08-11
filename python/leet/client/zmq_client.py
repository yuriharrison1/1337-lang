"""ZeroMQ Client for communicating with the 1337 network.

Lightweight client for P2P communication or with ZeroMQ brokers.
Supports patterns: REQ/REP, PUB/SUB, PUSH/PULL, DEALER/ROUTER

Example:
    >>> client = ZmqClient(ZmqConfig(mode=ZmqMode.REQ))
    >>> await client.connect("tcp://localhost:5555")
    >>> await client.send({"type": "COGON", "payload": cogon.to_dict()})
    >>> response = await client.recv()
"""

from __future__ import annotations

import asyncio
import json
import warnings
from dataclasses import dataclass, asdict
from enum import Enum, auto
from typing import Optional, Callable, Any, AsyncIterator

# Try to import zmq
try:
    import zmq
    import zmq.asyncio
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False
    warnings.warn("pyzmq not installed. ZeroMQ client unavailable.")


class ZmqMode(Enum):
    """ZeroMQ operation modes."""
    REQ = auto()      # Request (synchronous)
    REP = auto()      # Reply (server)
    PUB = auto()      # Publish (broadcast)
    SUB = auto()      # Subscribe (receives broadcast)
    PUSH = auto()     # Push (worker)
    PULL = auto()     # Pull (collector)
    DEALER = auto()   # Async client
    ROUTER = auto()   # Async broker


@dataclass
class ZmqConfig:
    """ZeroMQ client configuration."""
    mode: ZmqMode = ZmqMode.REQ
    timeout: float = 30.0
    receive_timeout: float = 5.0
    linger: int = 1000  # ms
    identity: Optional[bytes] = None

    @property
    def socket_type(self) -> int:
        """Returns the zmq constant."""
        if not ZMQ_AVAILABLE:
            raise RuntimeError("zmq unavailable")

        mapping = {
            ZmqMode.REQ: zmq.REQ,
            ZmqMode.REP: zmq.REP,
            ZmqMode.PUB: zmq.PUB,
            ZmqMode.SUB: zmq.SUB,
            ZmqMode.PUSH: zmq.PUSH,
            ZmqMode.PULL: zmq.PULL,
            ZmqMode.DEALER: zmq.DEALER,
            ZmqMode.ROUTER: zmq.ROUTER,
        }
        return mapping[self.mode]


@dataclass
class ZmqMessage:
    """ZeroMQ message for the 1337 network.

    Attributes:
        msg_type: Message type (COGON, MSG_1337, DELTA, etc)
        sender: Sender ID
        receiver: Recipient ID (or "BROADCAST")
        payload: Message data
        timestamp: Unix timestamp
    """
    msg_type: str
    sender: str
    receiver: str
    payload: dict
    timestamp: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            import time
            self.timestamp = time.time()

    def to_json(self) -> str:
        """Serializes to JSON."""
        return json.dumps(asdict(self), default=str)

    @classmethod
    def from_json(cls, data: str) -> "ZmqMessage":
        """Deserializes from JSON."""
        d = json.loads(data)
        return cls(**d)

    @classmethod
    def cogon_message(
        cls,
        sender: str,
        receiver: str,
        cogon_data: dict
    ) -> "ZmqMessage":
        """Creates a COGON message."""
        return cls(
            msg_type="COGON",
            sender=sender,
            receiver=receiver,
            payload=cogon_data
        )

    @classmethod
    def handshake_message(
        cls,
        sender: str,
        phase: str,  # PROBE, ECHO, ALIGN, VERIFY
        data: dict
    ) -> "ZmqMessage":
        """Creates a C5 handshake message."""
        return cls(
            msg_type=f"HANDSHAKE_{phase}",
            sender=sender,
            receiver="NETWORK",
            payload=data
        )


class ZmqClient:
    """ZeroMQ client for the 1337 network.

    Implements asynchronous communication over ZeroMQ:
    - REQ/REP: Synchronous RPC
    - PUB/SUB: Broadcast
    - PUSH/PULL: Work queues
    - DEALER/ROUTER: Async routing

    Args:
        config: ZeroMQ configuration
        context: Shared zmq context (optional)

    Example:
        >>> config = ZmqConfig(mode=ZmqMode.REQ)
        >>> client = ZmqClient(config)
        >>> await client.connect("tcp://localhost:5555")
        >>>
        >>> msg = ZmqMessage.cogon_message("agent1", "agent2", {...})
        >>> await client.send_message(msg)
        >>> response = await client.recv_message()
    """

    def __init__(
        self,
        config: Optional[ZmqConfig] = None,
        context: Optional[zmq.asyncio.Context] = None
    ):
        if not ZMQ_AVAILABLE:
            raise RuntimeError(
                "pyzmq not installed. "
                "Install with: pip install pyzmq"
            )

        self.config = config or ZmqConfig()
        self._context = context or zmq.asyncio.Context()
        self._socket: Optional[zmq.asyncio.Socket] = None
        self._connected = False
        self._url: Optional[str] = None

        # Callbacks for received messages (SUB/PULL)
        self._message_callbacks: list[Callable[[ZmqMessage], Any]] = []
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self, url: str, bind: bool = False) -> "ZmqClient":
        """Connects (or binds) to an endpoint.

        Args:
            url: ZeroMQ URL (e.g. "tcp://localhost:5555")
            bind: If True, binds instead of connecting

        Returns:
            Self for chaining
        """
        self._socket = self._context.socket(self.config.socket_type)

        # Settings
        self._socket.setsockopt(zmq.LINGER, self.config.linger)

        if self.config.identity:
            self._socket.setsockopt(zmq.IDENTITY, self.config.identity)

        # Subscribe to all topics if SUB
        if self.config.mode == ZmqMode.SUB:
            self._socket.setsockopt(zmq.SUBSCRIBE, b"")

        if bind:
            self._socket.bind(url)
        else:
            self._socket.connect(url)

        self._url = url
        self._connected = True

        # Start receive task if SUB/PULL
        if self.config.mode in (ZmqMode.SUB, ZmqMode.PULL):
            self._receive_task = asyncio.create_task(self._receive_loop())

        return self

    async def close(self):
        """Closes the connection."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._socket:
            self._socket.close()
            self._socket = None

        self._connected = False

    async def __aenter__(self) -> "ZmqClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def send(self, data: bytes, flags: int = 0):
        """Sends raw bytes."""
        if not self._connected:
            raise ConnectionError("Client not connected")

        await self._socket.send(data, flags=flags)

    async def recv(self, flags: int = 0) -> bytes:
        """Receives raw bytes."""
        if not self._connected:
            raise ConnectionError("Client not connected")

        # Configure timeout
        if self.config.receive_timeout > 0:
            self._socket.setsockopt(
                zmq.RCVTIMEO,
                int(self.config.receive_timeout * 1000)
            )

        return await self._socket.recv(flags=flags)

    async def send_message(self, message: ZmqMessage):
        """Sends a ZmqMessage."""
        data = message.to_json().encode('utf-8')
        await self.send(data)

    async def recv_message(self) -> ZmqMessage:
        """Receives a ZmqMessage."""
        data = await self.recv()
        return ZmqMessage.from_json(data.decode('utf-8'))

    async def send_multipart(self, parts: list[bytes]):
        """Sends a multipart message."""
        if not self._connected:
            raise ConnectionError("Client not connected")

        await self._socket.send_multipart(parts)

    async def recv_multipart(self) -> list[bytes]:
        """Receives a multipart message."""
        if not self._connected:
            raise ConnectionError("Client not connected")

        return await self._socket.recv_multipart()

    def on_message(self, callback: Callable[[ZmqMessage], Any]):
        """Registers a callback for received messages (SUB/PULL)."""
        self._message_callbacks.append(callback)

    async def _receive_loop(self):
        """Receive loop for SUB/PULL."""
        while self._connected:
            try:
                msg = await self.recv_message()
                for callback in self._message_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            asyncio.create_task(callback(msg))
                        else:
                            callback(msg)
                    except Exception as e:
                        warnings.warn(f"Error in callback: {e}")
            except zmq.Again:  # Timeout
                await asyncio.sleep(0.1)
            except Exception as e:
                warnings.warn(f"Error in receive loop: {e}")
                await asyncio.sleep(1)

    async def request(
        self,
        message: ZmqMessage,
        timeout: Optional[float] = None
    ) -> ZmqMessage:
        """Makes a request and waits for the response (REQ mode).

        Args:
            message: Message to send
            timeout: Timeout in seconds

        Returns:
            Response message
        """
        if self.config.mode != ZmqMode.REQ:
            raise RuntimeError("request() only works in REQ mode")

        await self.send_message(message)

        # Set temporary timeout
        old_timeout = self.config.receive_timeout
        if timeout:
            self._socket.setsockopt(zmq.RCVTIMEO, int(timeout * 1000))

        try:
            return await self.recv_message()
        finally:
            if timeout:
                self._socket.setsockopt(zmq.RCVTIMEO, int(old_timeout * 1000))

    async def publish(self, message: ZmqMessage):
        """Publishes a message (PUB mode)."""
        if self.config.mode != ZmqMode.PUB:
            raise RuntimeError("publish() only works in PUB mode")

        await self.send_message(message)

    async def subscribe(
        self,
        topic: str = "",
        handler: Optional[Callable[[ZmqMessage], Any]] = None
    ) -> AsyncIterator[ZmqMessage]:
        """Subscribes to topics (SUB mode).

        Yields:
            Received messages
        """
        if self.config.mode != ZmqMode.SUB:
            raise RuntimeError("subscribe() only works in SUB mode")

        # Set topic filter
        self._socket.setsockopt(zmq.SUBSCRIBE, topic.encode())

        while self._connected:
            try:
                msg = await self.recv_message()
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(msg))
                    else:
                        handler(msg)
                yield msg
            except zmq.Again:
                await asyncio.sleep(0.01)


class ZmqBroker:
    """Simple ZeroMQ broker for message routing.

    Implements the ROUTER-DEALER pattern to distribute messages
    among multiple agents.

    Example:
        >>> broker = ZmqBroker("tcp://*:5556")
        >>> await broker.start()
        >>> # Agents connect and send messages
        >>> await broker.stop()
    """

    def __init__(self, frontend_url: str, backend_url: Optional[str] = None):
        if not ZMQ_AVAILABLE:
            raise RuntimeError("pyzmq not installed")

        self.frontend_url = frontend_url
        self.backend_url = backend_url or "inproc://backend"
        self._context = zmq.asyncio.Context()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Starts the broker."""
        self._running = True
        self._task = asyncio.create_task(self._proxy_loop())

    async def stop(self):
        """Stops the broker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _proxy_loop(self):
        """Proxy loop between frontend and backend."""
        frontend = self._context.socket(zmq.ROUTER)
        backend = self._context.socket(zmq.DEALER)

        frontend.bind(self.frontend_url)
        backend.bind(self.backend_url)

        poller = zmq.asyncio.Poller()
        poller.register(frontend, zmq.POLLIN)
        poller.register(backend, zmq.POLLIN)

        while self._running:
            try:
                events = dict(await poller.poll(timeout=100))

                if frontend in events:
                    msg = await frontend.recv_multipart()
                    await backend.send_multipart(msg)

                if backend in events:
                    msg = await backend.recv_multipart()
                    await frontend.send_multipart(msg)
            except Exception as e:
                warnings.warn(f"Error in broker: {e}")

        frontend.close()
        backend.close()
