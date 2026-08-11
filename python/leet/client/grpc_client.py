"""gRPC Client for leet-service.

Connects to the 1337 gRPC service for:
- Encode: text → COGON
- Decode: COGON → text
- Delta: compute differences
- Recall: retrieve similar COGONs
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

# Try to import gRPC
try:
    import grpc
    import grpc.aio
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    warnings.warn("grpcio not installed. gRPC client unavailable.")

from leet import Cogon


@dataclass
class GrpcConfig:
    """gRPC client configuration."""
    host: str = "localhost"
    port: int = 50051
    timeout: float = 30.0
    max_retries: int = 3
    compression: Optional[str] = None  # 'gzip' or None

    @property
    def target(self) -> str:
        """Returns the gRPC connection string."""
        return f"{self.host}:{self.port}"


@dataclass
class EncodeResult:
    """Encode result."""
    cogon_id: str
    sem: list[float]
    unc: list[float]
    stamp: int
    tokens_saved: int

    def to_cogon(self) -> Cogon:
        """Converts to a Cogon."""
        return Cogon.new(sem=self.sem, unc=self.unc)


@dataclass
class CogonRecord:
    """COGON record from the store."""
    cogon_id: str
    sem: list[float]
    unc: list[float]
    dist: float
    stamp: int


class GrpcClient:
    """gRPC client for leet-service.

    Implements the 1337 protocol over gRPC:
    - Encode: text → COGON (sem[32], unc[32])
    - Decode: COGON → text
    - Delta: compute difference
    - Recall: retrieve similar entries

    Args:
        config: gRPC configuration

    Example:
        >>> async with GrpcClient(GrpcConfig()) as client:
        ...     result = await client.encode("Hello", agent_id="agent1")
        ...     print(result.sem)
    """

    def __init__(self, config: Optional[GrpcConfig] = None):
        if not GRPC_AVAILABLE:
            raise RuntimeError(
                "grpcio not installed. "
                "Install with: pip install grpcio grpcio-tools"
            )

        self.config = config or GrpcConfig()
        self._channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[object] = None
        self._connected = False

    async def connect(self) -> "GrpcClient":
        """Connects to the gRPC service.

        Returns:
            Self for chaining
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

        # Try to connect with a timeout
        try:
            await asyncio.wait_for(
                self._channel.channel_ready(),
                timeout=self.config.timeout
            )
            self._connected = True
        except asyncio.TimeoutError:
            raise ConnectionError(
                f"Timeout connecting to {self.config.target}"
            )

        # Create stub (once the generated proto stubs are available)
        # self._stub = leet_pb2_grpc.LeetServiceStub(self._channel)

        return self

    async def close(self):
        """Closes the connection."""
        if self._channel:
            await self._channel.close()
            self._connected = False

    async def __aenter__(self) -> "GrpcClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def health_check(self) -> dict:
        """Checks the health of the service.

        Returns:
            Dict with status, backend and uptime
        """
        # Fallback: try a TCP connection
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
        """Encodes text into a COGON.

        Args:
            text: Text to encode
            agent_id: Agent ID
            session_id: Session ID

        Returns:
            EncodeResult with sem[32], unc[32]

        Raises:
            ConnectionError: If not connected
            RuntimeError: If gRPC unavailable
        """
        if not self._connected:
            raise ConnectionError("Client not connected. Use connect() first.")

        # Once we have protobuf stubs:
        # request = leet_pb2.EncodeRequest(
        #     text=text,
        #     agent_id=agent_id,
        #     session_id=session_id
        # )
        # response = await self._stub.Encode(request, timeout=self.config.timeout)
        # return EncodeResult(...)

        # Stub: returns mock values for testing
        warnings.warn("encode method requires generated protobuf stubs. Returning mock.")
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
        """Decodes a COGON into text.

        Args:
            sem: Semantic vector [32]
            unc: Uncertainty vector [32]
            lang: Language

        Returns:
            Reconstructed text
        """
        if not self._connected:
            raise ConnectionError("Client not connected.")

        warnings.warn("decode method requires generated protobuf stubs. Returning mock.")
        return f"[Decoded: {sem[:3]}...]"

    async def delta(
        self,
        sem_prev: list[float],
        sem_curr: list[float]
    ) -> tuple[list[float], float]:
        """Computes the delta between two semantic vectors.

        Args:
            sem_prev: Previous vector [32]
            sem_curr: Current vector [32]

        Returns:
            Tuple (patch, magnitude)
        """
        if len(sem_prev) != 32 or len(sem_curr) != 32:
            raise ValueError("Vectors must have 32 dimensions")

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
        """Retrieves similar COGONs from the store.

        Args:
            sem: Query semantic vector [32]
            unc: Uncertainty [32]
            agent_id: Agent ID
            k: Number of results

        Returns:
            List of the most similar CogonRecords
        """
        if not self._connected:
            raise ConnectionError("Client not connected.")

        warnings.warn("recall method requires generated protobuf stubs. Returning mock.")
        return []

    async def encode_batch(
        self,
        texts: list[str],
        agent_id: str = "",
        session_id: str = ""
    ) -> AsyncIterator[EncodeResult]:
        """Encodes multiple texts in batch (streaming).

        Args:
            texts: List of texts
            agent_id: Agent ID
            session_id: Session ID

        Yields:
            EncodeResult for each text
        """
        for text in texts:
            yield await self.encode(text, agent_id, session_id)


# Fallback: HTTP/REST client
class HttpClient:
    """HTTP fallback client used when gRPC is unavailable.

    Uses the REST API (once implemented on the server).
    """

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self._session: Optional[object] = None

    async def connect(self):
        """Initializes the HTTP session."""
        import aiohttp
        self._session = aiohttp.ClientSession()
        return self

    async def close(self):
        """Closes the session."""
        if self._session:
            await self._session.close()

    async def encode(self, text: str, **kwargs) -> EncodeResult:
        """Encode via HTTP POST."""
        if not self._session:
            raise ConnectionError("Session not started")

        async with self._session.post(
            f"{self.base_url}/encode",
            json={"text": text, **kwargs}
        ) as resp:
            data = await resp.json()
            return EncodeResult(**data)
