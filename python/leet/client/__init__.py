"""Clients for communicating with 1337 services.

Provides clients for:
- gRPC (leet-service)
- ZeroMQ (lightweight transport)
- WebSocket (real-time)
- Full agent (network participation)
- Connection pool (load balancing)

Example:
    >>> from leet.client import GrpcClient, Agent1337
    >>>
    >>> # gRPC client
    >>> async with GrpcClient("localhost:50051") as client:
    ...     cogon = await client.encode("Hello world")
    >>>
    >>> # Full agent
    >>> agent = Agent1337(AgentConfig(name="Dev"))
    >>> await agent.start()
    >>> await agent.send_assert("Deploy completed")
"""

from .grpc_client import GrpcClient, GrpcConfig, EncodeResult
from .zmq_client import ZmqClient, ZmqConfig, ZmqMode, ZmqMessage
from .websocket_client import (
    WebSocketClient, WSMessage, WebSocketManager,
    WSConnectionState, ConnectionStats
)
from .agent import Agent1337, AgentConfig, AgentState
from .pool import ClientPool, StickyClientPool

__all__ = [
    # gRPC
    "GrpcClient",
    "GrpcConfig",
    "EncodeResult",
    # ZeroMQ
    "ZmqClient",
    "ZmqConfig",
    "ZmqMode",
    "ZmqMessage",
    # WebSocket
    "WebSocketClient",
    "WebSocketManager",
    "WSMessage",
    "WSConnectionState",
    "ConnectionStats",
    # Agent
    "Agent1337",
    "AgentConfig",
    "AgentState",
    # Pool
    "ClientPool",
    "StickyClientPool",
]
