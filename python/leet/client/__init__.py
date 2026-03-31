"""Clientes para comunicação com serviços 1337.

Fornece clientes para:
- gRPC (leet-service)
- ZeroMQ (transporte leve)
- WebSocket (real-time)
- Agente completo (participação na rede)
- Pool de conexões (load balancing)

Example:
    >>> from leet.client import GrpcClient, Agent1337
    >>> 
    >>> # Cliente gRPC
    >>> async with GrpcClient("localhost:50051") as client:
    ...     cogon = await client.encode("Hello world")
    >>> 
    >>> # Agente completo
    >>> agent = Agent1337(AgentConfig(name="Dev"))
    >>> await agent.start()
    >>> await agent.send_assert("Deploy realizado")
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
