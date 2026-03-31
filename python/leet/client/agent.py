"""Agente 1337 completo para participação na rede.

Um agente é uma entidade autônoma que:
- Participa do handshake C5
- Envia e recebe mensagens 1337
- Mantém estado e histórico
- Persiste COGONs

Example:
    >>> from leet.client import Agent1337, AgentConfig
    >>> 
    >>> config = AgentConfig(
    ...     name="Analista",
    ...     persona="Você é um analista de código",
    ...     zmq_url="tcp://localhost:5555"
    ... )
    >>> 
    >>> agent = Agent1337(config)
    >>> await agent.start()
    >>> 
    >>> await agent.send_assert("O sistema está lento", urgency=0.8)
    >>> 
    >>> async for msg in agent.receive():
    ...     print(f"Recebido: {msg}")
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
    """Estados do agente."""
    INIT = "init"
    CONNECTING = "connecting"
    HANDSHAKE = "handshake"
    ACTIVE = "active"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class AgentConfig:
    """Configuração de um agente 1337.
    
    Attributes:
        name: Nome do agente
        persona: Descrição da persona
        agent_id: ID único (gerado se não fornecido)
        zmq_url: URL do broker ZeroMQ
        grpc_url: URL do serviço gRPC
        project_dir: Diretório do projeto
        auto_commit: Commit automático de COGONs
        max_history: Tamanho máximo do histórico
        log_level: Nível de log
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
    
    # Handshake C5
    c5_enabled: bool = True
    c5_timeout: float = 30.0
    
    # Reconexão
    auto_reconnect: bool = True
    reconnect_delay: float = 5.0
    max_reconnects: int = 10


@dataclass
class AgentStats:
    """Estatísticas do agente."""
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
    """Agente completo para rede 1337.
    
    Um agente pode:
    - Conectar à rede via ZeroMQ ou gRPC
    - Realizar handshake C5
    - Enviar mensagens (ASSERT, QUERY, DELTA, etc)
    - Receber e processar mensagens
    - Manter estado conversacional
    - Persistir histórico
    
    Args:
        config: Configuração do agente
        
    Example:
        >>> agent = Agent1337(AgentConfig(name="Dev"))
        >>> await agent.start()
        >>> await agent.send_assert("Deploy realizado")
        >>> await agent.stop()
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.id = self.config.agent_id
        self.state = AgentState.INIT
        self.stats = AgentStats()
        
        # Clientes
        self._zmq_client: Optional[ZmqClient] = None
        self._grpc_client: Optional[Any] = None
        
        # Estado
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
        """Inicia o agente e conecta à rede.
        
        Returns:
            Self para chaining
        """
        self.state = AgentState.CONNECTING
        
        # Conecta ZeroMQ
        try:
            zmq_config = ZmqConfig(mode=ZmqMode.DEALER)
            self._zmq_client = ZmqClient(zmq_config)
            await self._zmq_client.connect(self.config.zmq_url)
            
            # Registra handler
            self._zmq_client.on_message(self._handle_zmq_message)
            
        except Exception as e:
            self.state = AgentState.ERROR
            await self._notify_error(e)
            raise ConnectionError(f"Falha ao conectar: {e}")
        
        # Handshake C5
        if self.config.c5_enabled:
            self.state = AgentState.HANDSHAKE
            await self._c5_handshake()
        
        self.state = AgentState.ACTIVE
        self.stats.start_time = time.time()
        self._running = True
        
        # Inicia loop de recebimento
        self._receive_task = asyncio.create_task(self._receive_loop())
        
        # Envia COGON_ZERO (R20)
        await self._send_cogon_zero()
        
        return self
    
    async def stop(self):
        """Para o agente e desconecta."""
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
    
    # ─── Envio de Mensagens ─────────────────────────────────────────────────
    
    async def send_assert(
        self,
        text: str,
        urgency: float = 0.5,
        receiver: Optional[str] = None,
        **kwargs
    ) -> Msg1337:
        """Envia mensagem ASSERT.
        
        Args:
            text: Texto a enviar
            urgency: Urgência (0-1)
            receiver: ID do destinatário (None = broadcast)
            
        Returns:
            Mensagem enviada
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
        """Envia mensagem QUERY e aguarda resposta.
        
        Args:
            query: Query text
            receiver: ID do agente destino
            timeout: Timeout em segundos
            
        Returns:
            Resposta ou None se timeout
        """
        cogon = await self._text_to_cogon(query)
        
        msg = self._build_message(
            intent=Intent.QUERY,
            payload=cogon,
            receiver=receiver
        )
        
        await self._send_message(msg)
        
        # Aguarda resposta
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
        """Envia mensagem DELTA.
        
        Args:
            previous: COGON anterior
            current: COGON atual
            receiver: ID do destinatário
            
        Returns:
            Mensagem enviada
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
        """Envia mensagem ANOMALY (broadcast).
        
        Args:
            description: Descrição da anomalia
            severity: Severidade (0-1)
            
        Returns:
            Mensagem enviada
        """
        cogon = await self._text_to_cogon(description)
        
        # Força broadcast
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
        """Envia ACK para uma mensagem.
        
        Args:
            original_msg: Mensagem sendo confirmada
            
        Returns:
            ACK enviado
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
    
    # ─── Recebimento ────────────────────────────────────────────────────────
    
    def on_message(self, handler: Callable[[Msg1337], Any]):
        """Registra handler para mensagens recebidas."""
        self._message_handlers.append(handler)
    
    def on_error(self, handler: Callable[[Exception], Any]):
        """Registra handler para erros."""
        self._error_handlers.append(handler)
    
    async def receive(self) -> AsyncIterator[Msg1337]:
        """Iterador assíncrono de mensagens recebidas.
        
        Yields:
            Mensagens recebidas
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
    
    # ─── Métodos Internos ───────────────────────────────────────────────────
    
    async def _c5_handshake(self):
        """Realiza handshake C5 de 4 fases."""
        # Fase 1: PROBE
        probe_msg = ZmqMessage.handshake_message(
            sender=self.id,
            phase="PROBE",
            data={"schema_ver": "0.4.0", "anchors": []}
        )
        
        await self._zmq_client.send_message(probe_msg)
        
        # Aguarda ECHO
        echo = await asyncio.wait_for(
            self._zmq_client.recv_message(),
            timeout=self.config.c5_timeout
        )
        
        if echo.msg_type != "HANDSHAKE_ECHO":
            raise RuntimeError(f"Handshake falhou: {echo.msg_type}")
        
        # Fase 3: ALIGN (computa matriz)
        align_hash = hashlib.sha256(
            json.dumps(echo.payload).encode()
        ).hexdigest()
        
        align_msg = ZmqMessage.handshake_message(
            sender=self.id,
            phase="ALIGN",
            data={"align_hash": align_hash}
        )
        
        await self._zmq_client.send_message(align_msg)
        
        # Fase 4: VERIFY
        verify = await asyncio.wait_for(
            self._zmq_client.recv_message(),
            timeout=self.config.c5_timeout
        )
        
        if verify.msg_type == "HANDSHAKE_VERIFY":
            self._c5_verified = verify.payload.get("success", False)
        
        if not self._c5_verified:
            raise RuntimeError("Handshake C5 falhou na verificação")
    
    async def _send_cogon_zero(self):
        """Envia COGON_ZERO (R20)."""
        msg = self._build_message(
            intent=Intent.SYNC,
            payload=Cogon.zero(),
            receiver="BROADCAST"
        )
        await self._send_message(msg)
    
    async def _send_message(self, msg: Msg1337):
        """Envia mensagem via transporte."""
        if self._zmq_client:
            zmq_msg = ZmqMessage(
                msg_type="MSG_1337",
                sender=self.id,
                receiver=msg.receiver.agent_id if not msg.receiver.is_broadcast() else "BROADCAST",
                payload=msg.to_dict()
            )
            await self._zmq_client.send_message(zmq_msg)
        
        # Persiste no histórico
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
        """Constrói mensagem 1337."""
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
        """Converte texto em COGON."""
        # Usa projeção local ou via gRPC
        # Stub: projeção simples
        sem = [0.5] * 32
        unc = [0.1] * 32
        
        # Heurísticas simples
        if "urgente" in text.lower():
            sem[22] = 0.9  # C1_URGENCIA
        if "erro" in text.lower() or "falha" in text.lower():
            sem[26] = 0.85  # C5_ANOMALIA
        
        return Cogon.new(sem=sem, unc=unc)
    
    async def _receive_loop(self):
        """Loop principal de recebimento."""
        while self._running:
            try:
                await asyncio.sleep(0.1)
            except Exception as e:
                await self._notify_error(e)
    
    async def _handle_zmq_message(self, msg: ZmqMessage):
        """Processa mensagem ZeroMQ recebida."""
        if msg.msg_type == "MSG_1337":
            try:
                data = msg.payload
                # Reconstrói Msg1337
                msg_1337 = Msg1337.from_dict(data)
                
                self.stats.messages_received += 1
                self.stats.last_activity = time.time()
                
                # Notifica handlers
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
        """Notifica handlers de erro."""
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
        """Gera hash de COGON."""
        data = json.dumps({"sem": cogon.sem, "unc": cogon.unc})
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _hash_message(self, msg: Msg1337) -> str:
        """Gera hash de mensagem."""
        return msg.hash()
    
    # ─── API Pública ────────────────────────────────────────────────────────
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do agente."""
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            **self.stats.to_dict(),
        }
    
    def get_history(self, limit: int = 100) -> list[Msg1337]:
        """Retorna histórico de mensagens."""
        return self._history[-limit:]
    
    def clear_history(self):
        """Limpa histórico."""
        self._history.clear()
    
    async def save_state(self, path: str):
        """Salva estado do agente em arquivo."""
        state = {
            "config": asdict(self.config),
            "stats": asdict(self.stats),
            "history": [m.to_dict() for m in self._history],
            "saved_at": datetime.now().isoformat(),
        }
        
        with open(path, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    async def load_state(self, path: str):
        """Carrega estado do agente."""
        with open(path, 'r') as f:
            state = json.load(f)
        
        # Restaura histórico
        self._history = [Msg1337.from_dict(m) for m in state.get("history", [])]
