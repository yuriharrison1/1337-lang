"""Full 1337 agent for network participation.

An agent is an autonomous entity that:
- Participates in the C5 handshake
- Sends and receives 1337 messages
- Maintains state and history
- Persists COGONs

Example:
    >>> from leet.client import Agent1337, AgentConfig
    >>>
    >>> config = AgentConfig(
    ...     name="Analyst",
    ...     persona="You are a code analyst",
    ...     zmq_url="tcp://localhost:5555"
    ... )
    >>>
    >>> agent = Agent1337(config)
    >>> await agent.start()
    >>>
    >>> await agent.send_assert("The system is slow", urgency=0.8)
    >>>
    >>> async for msg in agent.receive():
    ...     print(f"Received: {msg}")
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, Any, AsyncIterator, Dict, List

from leet import Cogon, Dag, Msg1337, Intent, Receiver, CanonicalSpace, Surface, blend, dist, delta
from leet.client.zmq_client import ZmqClient, ZmqConfig, ZmqMode, ZmqMessage


class AgentState(Enum):
    """Agent states."""
    INIT = "init"
    CONNECTING = "connecting"
    HANDSHAKE = "handshake"
    ACTIVE = "active"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class AgentConfig:
    """Configuration for a 1337 agent.

    Attributes:
        name: Agent name
        persona: Persona description
        agent_id: Unique ID (generated if not provided)
        zmq_url: ZeroMQ broker URL
        grpc_url: gRPC service URL
        project_dir: Project directory
        auto_commit: Automatic commit of COGONs
        max_history: Maximum history size
        log_level: Log level
    """
    name: str = "Agent1337"
    persona: str = ""
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    zmq_url: str = "tcp://localhost:5555"
    grpc_url: str = "localhost:50051"
    project_dir: Optional[str] = None
    auto_commit: bool = True
    max_history: int = 1000
    log_level: str = "INFO"
    
    # C5 handshake
    c5_enabled: bool = True
    c5_timeout: float = 30.0

    # Reconnection
    auto_reconnect: bool = True
    reconnect_delay: float = 5.0
    max_reconnects: int = 10


@dataclass
class AgentStats:
    """Agent statistics."""
    messages_sent: int = 0
    messages_received: int = 0
    cogon_encoded: int = 0
    cogon_decoded: int = 0
    errors: int = 0
    start_time: Optional[float] = None
    last_activity: Optional[float] = None
    
    @property
    def uptime(self) -> float:
        if self.start_time:
            return time.time() - self.start_time
        return 0.0
    
    def to_dict(self) -> dict:
        return {
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "cogon_encoded": self.cogon_encoded,
            "cogon_decoded": self.cogon_decoded,
            "errors": self.errors,
            "uptime": self.uptime,
        }


class Agent1337:
    """Full agent for the 1337 network.

    An agent can:
    - Connect to the network via ZeroMQ or gRPC
    - Perform the C5 handshake
    - Send messages (ASSERT, QUERY, DELTA, etc)
    - Receive and process messages
    - Maintain conversational state
    - Persist history

    Args:
        config: Agent configuration

    Example:
        >>> agent = Agent1337(AgentConfig(name="Dev"))
        >>> await agent.start()
        >>> await agent.send_assert("Deploy completed")
        >>> await agent.stop()
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.id = self.config.agent_id
        self.state = AgentState.INIT
        self.stats = AgentStats()
        
        # Clients
        self._zmq_client: Optional[ZmqClient] = None
        self._grpc_client: Optional[Any] = None

        # State
        self._history: List[Msg1337] = []
        self._cogons: List[Cogon] = []
        self._session_id: Optional[str] = None
        self._c5_verified = False

        # Handlers
        self._message_handlers: List[Callable[[Msg1337], Any]] = []
        self._error_handlers: List[Callable[[Exception], Any]] = []

        # Tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._running = False

        # Cache
        self._cache: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        return self.config.name
    
    async def start(self) -> "Agent1337":
        """Starts the agent and connects to the network.

        Returns:
            Self for chaining
        """
        self.state = AgentState.CONNECTING

        # Connect ZeroMQ
        try:
            zmq_config = ZmqConfig(mode=ZmqMode.DEALER)
            self._zmq_client = ZmqClient(zmq_config)
            await self._zmq_client.connect(self.config.zmq_url)

            # Register handler
            self._zmq_client.on_message(self._handle_zmq_message)

        except Exception as e:
            self.state = AgentState.ERROR
            await self._notify_error(e)
            raise ConnectionError(f"Failed to connect: {e}")

        # C5 handshake
        if self.config.c5_enabled:
            self.state = AgentState.HANDSHAKE
            await self._c5_handshake()

        self.state = AgentState.ACTIVE
        self.stats.start_time = time.time()
        self._running = True

        # Start receive loop
        self._receive_task = asyncio.create_task(self._receive_loop())

        # Send COGON_ZERO (R20)
        await self._send_cogon_zero()

        return self

    async def stop(self):
        """Stops the agent and disconnects."""
        self._running = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self._zmq_client:
            await self._zmq_client.close()
        
        self.state = AgentState.DISCONNECTED
    
    async def __aenter__(self) -> "Agent1337":
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
    
    # ─── Message Sending ────────────────────────────────────────────────────

    async def send_assert(
        self,
        text: str,
        urgency: float = 0.5,
        receiver: Optional[str] = None,
        **kwargs
    ) -> Msg1337:
        """Sends an ASSERT message.

        Args:
            text: Text to send
            urgency: Urgency (0-1)
            receiver: Recipient ID (None = broadcast)

        Returns:
            Sent message
        """
        cogon = await self._text_to_cogon(text)
        
        msg = self._build_message(
            intent=Intent.ASSERT,
            payload=cogon,
            receiver=receiver,
            urgency=urgency,
            **kwargs
        )
        
        await self._send_message(msg)
        self.stats.messages_sent += 1
        
        return msg
    
    async def send_query(
        self,
        query: str,
        receiver: str,
        timeout: float = 30.0
    ) -> Optional[Msg1337]:
        """Sends a QUERY message and awaits the response.

        Args:
            query: Query text
            receiver: Target agent ID
            timeout: Timeout in seconds

        Returns:
            Response or None on timeout
        """
        cogon = await self._text_to_cogon(query)

        msg = self._build_message(
            intent=Intent.QUERY,
            payload=cogon,
            receiver=receiver
        )

        await self._send_message(msg)

        # Await response
        future = asyncio.Future()
        
        def handler(response: Msg1337):
            if not future.done():
                future.set_result(response)
        
        self._message_handlers.append(handler)
        
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            if handler in self._message_handlers:
                self._message_handlers.remove(handler)
    
    async def send_delta(
        self,
        previous: Cogon,
        current: Cogon,
        receiver: Optional[str] = None
    ) -> Msg1337:
        """Sends a DELTA message.

        Args:
            previous: Previous COGON
            current: Current COGON
            receiver: Recipient ID

        Returns:
            Sent message
        """
        patch = delta(previous, current)
        ref_hash = self._hash_cogon(previous)
        
        msg = self._build_message(
            intent=Intent.DELTA,
            payload=current,
            receiver=receiver,
            ref_hash=ref_hash,
            patch=patch
        )
        
        await self._send_message(msg)
        return msg
    
    async def send_anomaly(
        self,
        description: str,
        severity: float = 0.8,
        **kwargs
    ) -> Msg1337:
        """Sends an ANOMALY message (broadcast).

        Args:
            description: Anomaly description
            severity: Severity (0-1)

        Returns:
            Sent message
        """
        cogon = await self._text_to_cogon(description)

        # Force broadcast
        msg = self._build_message(
            intent=Intent.ANOMALY,
            payload=cogon,
            receiver="BROADCAST",
            urgency=severity,
            **kwargs
        )
        
        await self._send_message(msg)
        return msg
    
    async def send_ack(
        self,
        original_msg: Msg1337,
        **kwargs
    ) -> Msg1337:
        """Sends an ACK for a message.

        Args:
            original_msg: Message being acknowledged

        Returns:
            Sent ACK
        """
        msg = self._build_message(
            intent=Intent.ACK,
            payload=Cogon.zero(),
            receiver=original_msg.sender,
            ref_hash=self._hash_message(original_msg),
            **kwargs
        )
        
        await self._send_message(msg)
        return msg
    
    # ─── Receiving ──────────────────────────────────────────────────────────

    def on_message(self, handler: Callable[[Msg1337], Any]):
        """Registers a handler for received messages."""
        self._message_handlers.append(handler)

    def on_error(self, handler: Callable[[Exception], Any]):
        """Registers a handler for errors."""
        self._error_handlers.append(handler)

    async def receive(self) -> AsyncIterator[Msg1337]:
        """Asynchronous iterator over received messages.

        Yields:
            Received messages
        """
        queue: asyncio.Queue[Msg1337] = asyncio.Queue()
        
        def handler(msg: Msg1337):
            queue.put_nowait(msg)
        
        self.on_message(handler)
        
        try:
            while self._running:
                msg = await queue.get()
                yield msg
        finally:
            if handler in self._message_handlers:
                self._message_handlers.remove(handler)
    
    # ─── Internal Methods ───────────────────────────────────────────────────

    async def _c5_handshake(self):
        """Performs the 4-phase C5 handshake."""
        # Phase 1: PROBE
        probe_msg = ZmqMessage.handshake_message(
            sender=self.id,
            phase="PROBE",
            data={"schema_ver": "0.4.0", "anchors": []}
        )

        await self._zmq_client.send_message(probe_msg)

        # Await ECHO
        echo = await asyncio.wait_for(
            self._zmq_client.recv_message(),
            timeout=self.config.c5_timeout
        )

        if echo.msg_type != "HANDSHAKE_ECHO":
            raise RuntimeError(f"Handshake failed: {echo.msg_type}")

        # Phase 3: ALIGN (compute matrix)
        align_hash = hashlib.sha256(
            json.dumps(echo.payload).encode()
        ).hexdigest()

        align_msg = ZmqMessage.handshake_message(
            sender=self.id,
            phase="ALIGN",
            data={"align_hash": align_hash}
        )

        await self._zmq_client.send_message(align_msg)

        # Phase 4: VERIFY
        verify = await asyncio.wait_for(
            self._zmq_client.recv_message(),
            timeout=self.config.c5_timeout
        )

        if verify.msg_type == "HANDSHAKE_VERIFY":
            self._c5_verified = verify.payload.get("success", False)

        if not self._c5_verified:
            raise RuntimeError("C5 handshake failed verification")

    async def _send_cogon_zero(self):
        """Sends COGON_ZERO (R20)."""
        msg = self._build_message(
            intent=Intent.SYNC,
            payload=Cogon.zero(),
            receiver="BROADCAST"
        )
        await self._send_message(msg)
    
    async def _send_message(self, msg: Msg1337):
        """Sends a message over the transport."""
        if self._zmq_client:
            zmq_msg = ZmqMessage(
                msg_type="MSG_1337",
                sender=self.id,
                receiver=msg.receiver.agent_id if not msg.receiver.is_broadcast() else "BROADCAST",
                payload=msg.to_dict()
            )
            await self._zmq_client.send_message(zmq_msg)

        # Persist to history
        self._history.append(msg)
        if len(self._history) > self.config.max_history:
            self._history.pop(0)

    def _build_message(
        self,
        intent: Intent,
        payload: Any,
        receiver: Optional[str] = None,
        urgency: float = 0.5,
        **kwargs
    ) -> Msg1337:
        """Builds a 1337 message."""
        recv = Receiver(agent_id=receiver) if receiver else Receiver.broadcast()
        
        return Msg1337(
            id=str(uuid.uuid4()),
            sender=self.id,
            receiver=recv,
            intent=intent,
            payload=payload,
            c5=CanonicalSpace(
                zone_fixed=[0.5] * 32,
                zone_emergent={},
                schema_ver="0.4.0",
                align_hash="" if not self._c5_verified else "verified"
            ),
            surface=Surface(
                human_required=False,
                urgency=urgency,
                reconstruct_depth=3,
                lang="pt"
            ),
            **kwargs
        )
    
    async def _text_to_cogon(self, text: str) -> Cogon:
        """Converts text into a COGON."""
        # Uses local or gRPC projection
        # Stub: simple projection
        sem = [0.5] * 32
        unc = [0.1] * 32

        # Simple heuristics
        if "urgente" in text.lower():
            sem[22] = 0.9  # C1_URGENCIA
        if "erro" in text.lower() or "falha" in text.lower():
            sem[26] = 0.85  # C5_ANOMALIA

        return Cogon.new(sem=sem, unc=unc)

    async def _receive_loop(self):
        """Main receive loop."""
        while self._running:
            try:
                await asyncio.sleep(0.1)
            except Exception as e:
                await self._notify_error(e)

    async def _handle_zmq_message(self, msg: ZmqMessage):
        """Processes a received ZeroMQ message."""
        if msg.msg_type == "MSG_1337":
            try:
                data = msg.payload
                # Reconstruct Msg1337
                msg_1337 = Msg1337.from_dict(data)

                self.stats.messages_received += 1
                self.stats.last_activity = time.time()

                # Notify handlers
                for handler in self._message_handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            asyncio.create_task(handler(msg_1337))
                        else:
                            handler(msg_1337)
                    except Exception as e:
                        await self._notify_error(e)
                
            except Exception as e:
                await self._notify_error(e)
    
    async def _notify_error(self, error: Exception):
        """Notifies error handlers."""
        self.stats.errors += 1
        for handler in self._error_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(error))
                else:
                    handler(error)
            except:
                pass
    
    def _hash_cogon(self, cogon: Cogon) -> str:
        """Generates a hash of a COGON."""
        data = json.dumps({"sem": cogon.sem, "unc": cogon.unc})
        return hashlib.sha256(data.encode()).hexdigest()

    def _hash_message(self, msg: Msg1337) -> str:
        """Generates a hash of a message."""
        return msg.hash()

    # ─── Public API ─────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Returns agent statistics."""
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            **self.stats.to_dict(),
        }

    def get_history(self, limit: int = 100) -> list[Msg1337]:
        """Returns message history."""
        return self._history[-limit:]

    def clear_history(self):
        """Clears the history."""
        self._history.clear()

    async def save_state(self, path: str):
        """Saves agent state to a file."""
        state = {
            "config": asdict(self.config),
            "stats": asdict(self.stats),
            "history": [m.to_dict() for m in self._history],
            "saved_at": datetime.now().isoformat(),
        }
        
        with open(path, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    async def load_state(self, path: str):
        """Loads agent state."""
        with open(path, 'r') as f:
            state = json.load(f)

        # Restore history
        self._history = [Msg1337.from_dict(m) for m in state.get("history", [])]
