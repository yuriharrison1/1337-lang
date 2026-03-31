"""ZeroMQ Client para comunicação com rede 1337.

Cliente leve para comunicação P2P ou com brokers ZeroMQ.
Suporta padrões: REQ/REP, PUB/SUB, PUSH/PULL, DEALER/ROUTER

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

# Tenta importar zmq
try:
    import zmq
    import zmq.asyncio
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False
    warnings.warn("pyzmq não instalado. Cliente ZeroMQ não disponível.")


class ZmqMode(Enum):
    """Modos de operação ZeroMQ."""
    REQ = auto()      # Request (síncrono)
    REP = auto()      # Reply (servidor)
    PUB = auto()      # Publish (broadcast)
    SUB = auto()      # Subscribe (recebe broadcast)
    PUSH = auto()     # Push (worker)
    PULL = auto()     # Pull (coletor)
    DEALER = auto()   # Async client
    ROUTER = auto()   # Async broker


@dataclass
class ZmqConfig:
    """Configuração do cliente ZeroMQ."""
    mode: ZmqMode = ZmqMode.REQ
    timeout: float = 30.0
    receive_timeout: float = 5.0
    linger: int = 1000  # ms
    identity: Optional[bytes] = None
    
    @property
    def socket_type(self) -> int:
        """Retorna constante zmq."""
        if not ZMQ_AVAILABLE:
            raise RuntimeError("zmq não disponível")
        
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
    """Mensagem ZeroMQ para rede 1337.
    
    Attributes:
        msg_type: Tipo da mensagem (COGON, MSG_1337, DELTA, etc)
        sender: ID do remetente
        receiver: ID do destinatário (ou "BROADCAST")
        payload: Dados da mensagem
        timestamp: Timestamp Unix
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
        """Serializa para JSON."""
        return json.dumps(asdict(self), default=str)
    
    @classmethod
    def from_json(cls, data: str) -> "ZmqMessage":
        """Desserializa de JSON."""
        d = json.loads(data)
        return cls(**d)
    
    @classmethod
    def cogon_message(
        cls,
        sender: str,
        receiver: str,
        cogon_data: dict
    ) -> "ZmqMessage":
        """Cria mensagem de COGON."""
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
        """Cria mensagem de handshake C5."""
        return cls(
            msg_type=f"HANDSHAKE_{phase}",
            sender=sender,
            receiver="NETWORK",
            payload=data
        )


class ZmqClient:
    """Cliente ZeroMQ para rede 1337.
    
    Implementa comunicação assíncrona via ZeroMQ:
    - REQ/REP: RPC síncrono
    - PUB/SUB: Broadcast
    - PUSH/PULL: Work queues
    - DEALER/ROUTER: Async routing
    
    Args:
        config: Configuração ZeroMQ
        context: Contexto zmq compartilhado (opcional)
        
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
                "pyzmq não instalado. "
                "Instale: pip install pyzmq"
            )
        
        self.config = config or ZmqConfig()
        self._context = context or zmq.asyncio.Context()
        self._socket: Optional[zmq.asyncio.Socket] = None
        self._connected = False
        self._url: Optional[str] = None
        
        # Callbacks para mensagens recebidas (SUB/PULL)
        self._message_callbacks: list[Callable[[ZmqMessage], Any]] = []
        self._receive_task: Optional[asyncio.Task] = None
    
    async def connect(self, url: str, bind: bool = False) -> "ZmqClient":
        """Conecta (ou binda) a um endpoint.
        
        Args:
            url: URL ZeroMQ (ex: "tcp://localhost:5555")
            bind: Se True, binda ao invés de connect
            
        Returns:
            Self para chaining
        """
        self._socket = self._context.socket(self.config.socket_type)
        
        # Configurações
        self._socket.setsockopt(zmq.LINGER, self.config.linger)
        
        if self.config.identity:
            self._socket.setsockopt(zmq.IDENTITY, self.config.identity)
        
        # Subscribe em todos os tópicos se for SUB
        if self.config.mode == ZmqMode.SUB:
            self._socket.setsockopt(zmq.SUBSCRIBE, b"")
        
        if bind:
            self._socket.bind(url)
        else:
            self._socket.connect(url)
        
        self._url = url
        self._connected = True
        
        # Inicia task de recebimento se for SUB/PULL
        if self.config.mode in (ZmqMode.SUB, ZmqMode.PULL):
            self._receive_task = asyncio.create_task(self._receive_loop())
        
        return self
    
    async def close(self):
        """Fecha conexão."""
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
        """Envia bytes brutos."""
        if not self._connected:
            raise ConnectionError("Cliente não conectado")
        
        await self._socket.send(data, flags=flags)
    
    async def recv(self, flags: int = 0) -> bytes:
        """Recebe bytes brutos."""
        if not self._connected:
            raise ConnectionError("Cliente não conectado")
        
        # Configura timeout
        if self.config.receive_timeout > 0:
            self._socket.setsockopt(
                zmq.RCVTIMEO,
                int(self.config.receive_timeout * 1000)
            )
        
        return await self._socket.recv(flags=flags)
    
    async def send_message(self, message: ZmqMessage):
        """Envia uma mensagem ZmqMessage."""
        data = message.to_json().encode('utf-8')
        await self.send(data)
    
    async def recv_message(self) -> ZmqMessage:
        """Recebe uma mensagem ZmqMessage."""
        data = await self.recv()
        return ZmqMessage.from_json(data.decode('utf-8'))
    
    async def send_multipart(self, parts: list[bytes]):
        """Envia mensagem multipart."""
        if not self._connected:
            raise ConnectionError("Cliente não conectado")
        
        await self._socket.send_multipart(parts)
    
    async def recv_multipart(self) -> list[bytes]:
        """Recebe mensagem multipart."""
        if not self._connected:
            raise ConnectionError("Cliente não conectado")
        
        return await self._socket.recv_multipart()
    
    def on_message(self, callback: Callable[[ZmqMessage], Any]):
        """Registra callback para mensagens recebidas (SUB/PULL)."""
        self._message_callbacks.append(callback)
    
    async def _receive_loop(self):
        """Loop de recebimento para SUB/PULL."""
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
                        warnings.warn(f"Erro em callback: {e}")
            except zmq.Again:  # Timeout
                await asyncio.sleep(0.1)
            except Exception as e:
                warnings.warn(f"Erro no receive loop: {e}")
                await asyncio.sleep(1)
    
    async def request(
        self,
        message: ZmqMessage,
        timeout: Optional[float] = None
    ) -> ZmqMessage:
        """Faz request e aguarda response (modo REQ).
        
        Args:
            message: Mensagem a enviar
            timeout: Timeout em segundos
            
        Returns:
            Mensagem de resposta
        """
        if self.config.mode != ZmqMode.REQ:
            raise RuntimeError("request() só funciona em modo REQ")
        
        await self.send_message(message)
        
        # Set timeout temporário
        old_timeout = self.config.receive_timeout
        if timeout:
            self._socket.setsockopt(zmq.RCVTIMEO, int(timeout * 1000))
        
        try:
            return await self.recv_message()
        finally:
            if timeout:
                self._socket.setsockopt(zmq.RCVTIMEO, int(old_timeout * 1000))
    
    async def publish(self, message: ZmqMessage):
        """Publica mensagem (modo PUB)."""
        if self.config.mode != ZmqMode.PUB:
            raise RuntimeError("publish() só funciona em modo PUB")
        
        await self.send_message(message)
    
    async def subscribe(
        self,
        topic: str = "",
        handler: Optional[Callable[[ZmqMessage], Any]] = None
    ) -> AsyncIterator[ZmqMessage]:
        """Subscreve em tópicos (modo SUB).
        
        Yields:
            Mensagens recebidas
        """
        if self.config.mode != ZmqMode.SUB:
            raise RuntimeError("subscribe() só funciona em modo SUB")
        
        # Seta filtro de tópico
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
    """Broker ZeroMQ simples para routing de mensagens.
    
    Implementa padrão ROUTER-DEALER para distribuir mensagens
    entre múltiplos agents.
    
    Example:
        >>> broker = ZmqBroker("tcp://*:5556")
        >>> await broker.start()
        >>> # Agents conectam e enviam mensagens
        >>> await broker.stop()
    """
    
    def __init__(self, frontend_url: str, backend_url: Optional[str] = None):
        if not ZMQ_AVAILABLE:
            raise RuntimeError("pyzmq não instalado")
        
        self.frontend_url = frontend_url
        self.backend_url = backend_url or "inproc://backend"
        self._context = zmq.asyncio.Context()
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Inicia o broker."""
        self._running = True
        self._task = asyncio.create_task(self._proxy_loop())
    
    async def stop(self):
        """Para o broker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _proxy_loop(self):
        """Loop de proxy entre frontend e backend."""
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
                warnings.warn(f"Erro no broker: {e}")
        
        frontend.close()
        backend.close()
