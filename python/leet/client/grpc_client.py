"""gRPC Client para leet-service.

Conecta com o serviço gRPC do 1337 para:
- Encode: texto → COGON
- Decode: COGON → texto
- Delta: computar diferenças
- Recall: recuperar COGONs similares
- Health: health check

Example:
    >>> client = GrpcClient("localhost:50051")
    >>> await client.connect()
    >>> cogon = await client.encode("Hello")
    >>> await client.close()
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional, AsyncIterator, Callable
import warnings

# Tenta importar gRPC
try:
    import grpc
    import grpc.aio
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    warnings.warn("grpcio não instalado. Cliente gRPC não disponível.")

from leet import Cogon


@dataclass
class GrpcConfig:
    """Configuração do cliente gRPC."""
    host: str = "localhost"
    port: int = 50051
    timeout: float = 30.0
    max_retries: int = 3
    compression: Optional[str] = None  # 'gzip' ou None
    
    @property
    def target(self) -> str:
        """Retorna string de conexão gRPC."""
        return f"{self.host}:{self.port}"


@dataclass
class EncodeResult:
    """Resultado de encode."""
    cogon_id: str
    sem: list[float]
    unc: list[float]
    stamp: int
    tokens_saved: int
    
    def to_cogon(self) -> Cogon:
        """Converte para Cogon."""
        return Cogon.new(sem=self.sem, unc=self.unc)


@dataclass
class CogonRecord:
    """Registro de COGON do store."""
    cogon_id: str
    sem: list[float]
    unc: list[float]
    dist: float
    stamp: int


class GrpcClient:
    """Cliente gRPC para leet-service.
    
    Implementa o protocolo 1337 via gRPC:
    - Encode: texto → COGON (sem[32], unc[32])
    - Decode: COGON → texto
    - Delta: computar diferença
    - Recall: recuperar similares
    
    Args:
        config: Configuração gRPC
        
    Example:
        >>> async with GrpcClient(GrpcConfig()) as client:
        ...     result = await client.encode("Hello", agent_id="agent1")
        ...     print(result.sem)
    """
    
    def __init__(self, config: Optional[GrpcConfig] = None):
        if not GRPC_AVAILABLE:
            raise RuntimeError(
                "grpcio não instalado. "
                "Instale: pip install grpcio grpcio-tools"
            )
        
        self.config = config or GrpcConfig()
        self._channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[object] = None
        self._connected = False
        
    async def connect(self) -> "GrpcClient":
        """Conecta ao serviço gRPC.
        
        Returns:
            Self para chaining
        """
        options = [
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
        ]
        
        if self.config.compression == 'gzip':
            options.append(('grpc.default_compression_algorithm', 2))  # gzip
        
        self._channel = grpc.aio.insecure_channel(
            self.config.target,
            options=options
        )
        
        # Tenta conectar com timeout
        try:
            await asyncio.wait_for(
                self._channel.channel_ready(),
                timeout=self.config.timeout
            )
            self._connected = True
        except asyncio.TimeoutError:
            raise ConnectionError(
                f"Timeout conectando a {self.config.target}"
            )
        
        # Cria stub (quando temos os proto stubs gerados)
        # self._stub = leet_pb2_grpc.LeetServiceStub(self._channel)
        
        return self
    
    async def close(self):
        """Fecha conexão."""
        if self._channel:
            await self._channel.close()
            self._connected = False
    
    async def __aenter__(self) -> "GrpcClient":
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def health_check(self) -> dict:
        """Verifica saúde do serviço.
        
        Returns:
            Dict com status, backend e uptime
        """
        # Fallback: tenta conexão TCP
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.host, self.config.port),
                timeout=5.0
            )
            writer.close()
            await writer.wait_closed()
            return {
                "status": "ok",
                "backend": "unknown",
                "uptime": 0,
                "connected": self._connected
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "connected": False
            }
    
    async def encode(
        self,
        text: str,
        agent_id: str = "",
        session_id: str = ""
    ) -> EncodeResult:
        """Codifica texto em COGON.
        
        Args:
            text: Texto a codificar
            agent_id: ID do agente
            session_id: ID da sessão
            
        Returns:
            EncodeResult com sem[32], unc[32]
            
        Raises:
            ConnectionError: Se não conectado
            RuntimeError: Se gRPC não disponível
        """
        if not self._connected:
            raise ConnectionError("Cliente não conectado. Use connect() primeiro.")
        
        # Quando temos stubs protobuf:
        # request = leet_pb2.EncodeRequest(
        #     text=text,
        #     agent_id=agent_id,
        #     session_id=session_id
        # )
        # response = await self._stub.Encode(request, timeout=self.config.timeout)
        # return EncodeResult(...)
        
        # Stub: retorna valores mock para teste
        warnings.warn("Método encode requer stubs protobuf gerados. Retornando mock.")
        return EncodeResult(
            cogon_id="mock-cogon-id",
            sem=[0.5] * 32,
            unc=[0.1] * 32,
            stamp=0,
            tokens_saved=len(text) // 4
        )
    
    async def decode(
        self,
        sem: list[float],
        unc: list[float],
        lang: str = "pt"
    ) -> str:
        """Decodifica COGON em texto.
        
        Args:
            sem: Vetor semântico [32]
            unc: Vetor de incerteza [32]
            lang: Linguagem
            
        Returns:
            Texto reconstruído
        """
        if not self._connected:
            raise ConnectionError("Cliente não conectado.")
        
        warnings.warn("Método decode requer stubs protobuf gerados. Retornando mock.")
        return f"[Decoded: {sem[:3]}...]"
    
    async def delta(
        self,
        sem_prev: list[float],
        sem_curr: list[float]
    ) -> tuple[list[float], float]:
        """Computa delta entre dois vetores semânticos.
        
        Args:
            sem_prev: Vetor anterior [32]
            sem_curr: Vetor atual [32]
            
        Returns:
            Tuple (patch, magnitude)
        """
        if len(sem_prev) != 32 or len(sem_curr) != 32:
            raise ValueError("Vetores devem ter 32 dimensões")
        
        patch = [curr - prev for prev, curr in zip(sem_prev, sem_curr)]
        magnitude = sum(p ** 2 for p in patch) ** 0.5
        
        return patch, magnitude
    
    async def recall(
        self,
        sem: list[float],
        unc: list[float],
        agent_id: str,
        k: int = 5
    ) -> list[CogonRecord]:
        """Recupera COGONs similares do store.
        
        Args:
            sem: Query semântico [32]
            unc: Incerteza [32]
            agent_id: ID do agente
            k: Número de resultados
            
        Returns:
            Lista de CogonRecord mais similares
        """
        if not self._connected:
            raise ConnectionError("Cliente não conectado.")
        
        warnings.warn("Método recall requer stubs protobuf gerados. Retornando mock.")
        return []
    
    async def encode_batch(
        self,
        texts: list[str],
        agent_id: str = "",
        session_id: str = ""
    ) -> AsyncIterator[EncodeResult]:
        """Codifica múltiplos textos em batch (streaming).
        
        Args:
            texts: Lista de textos
            agent_id: ID do agente
            session_id: ID da sessão
            
        Yields:
            EncodeResult para cada texto
        """
        for text in texts:
            yield await self.encode(text, agent_id, session_id)


# Fallback: Cliente HTTP/REST
class HttpClient:
    """Cliente HTTP fallback quando gRPC não disponível.
    
    Usa REST API (quando implementada no servidor).
    """
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self._session: Optional[object] = None
    
    async def connect(self):
        """Inicializa sessão HTTP."""
        import aiohttp
        self._session = aiohttp.ClientSession()
        return self
    
    async def close(self):
        """Fecha sessão."""
        if self._session:
            await self._session.close()
    
    async def encode(self, text: str, **kwargs) -> EncodeResult:
        """Encode via HTTP POST."""
        if not self._session:
            raise ConnectionError("Sessão não iniciada")
        
        async with self._session.post(
            f"{self.base_url}/encode",
            json={"text": text, **kwargs}
        ) as resp:
            data = await resp.json()
            return EncodeResult(**data)
