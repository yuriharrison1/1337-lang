"""Client pool for efficient connections.

Manages a pool of gRPC/ZeroMQ connections for:
- Connection reuse
- Load balancing
- Health checking
- Circuit breaker

Example:
    >>> from leet.client import ClientPool
    >>>
    >>> pool = ClientPool([
        "localhost:50051",
        "localhost:50052",
        "localhost:50053"
    ])
    >>>
    >>> async with pool.acquire() as client:
    ...     result = await client.encode("hello")
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import List, Optional, AsyncIterator, Callable, Any
from contextlib import asynccontextmanager

from leet.client.grpc_client import GrpcClient, GrpcConfig
from leet.client.zmq_client import ZmqClient, ZmqConfig


@dataclass
class PooledClient:
    """Pooled client with metadata."""
    client: Any
    url: str
    healthy: bool = True
    failures: int = 0
    requests: int = 0


class ClientPool:
    """Client pool for load balancing.

    Distributes requests across multiple endpoints
    with health checking and circuit breaker.

    Args:
        urls: List of endpoint URLs
        client_type: Client type (grpc, zmq)
        max_failures: Max failures before marking unhealthy
        health_interval: Health check interval

    Example:
        >>> pool = ClientPool([
        ...     "localhost:50051",
        ...     "localhost:50052"
        ])
        >>>
        >>> # Automatic round-robin
        >>> result = await pool.execute(lambda c: c.encode("hello"))
        >>>
        >>> # Or with a context manager
        >>> async with pool.acquire() as client:
        ...     result = await client.encode("hello")
    """

    def __init__(
        self,
        urls: List[str],
        client_type: str = "grpc",
        max_failures: int = 3,
        health_interval: float = 30.0
    ):
        self.urls = urls
        self.client_type = client_type
        self.max_failures = max_failures
        self.health_interval = health_interval

        self._pool: List[PooledClient] = []
        self._current_index = 0
        self._lock = asyncio.Lock()

        self._health_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Starts the pool and connects clients."""
        self._running = True

        for url in self.urls:
            client = await self._create_client(url)
            self._pool.append(PooledClient(client, url))

        # Start health checks
        self._health_task = asyncio.create_task(self._health_loop())

    async def stop(self):
        """Stops the pool and closes connections."""
        self._running = False

        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        for pooled in self._pool:
            if hasattr(pooled.client, 'close'):
                await pooled.client.close()

        self._pool.clear()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def _create_client(self, url: str) -> Any:
        """Creates a client for the given URL."""
        if self.client_type == "grpc":
            config = GrpcConfig()
            if ":" in url:
                host, port = url.rsplit(":", 1)
                config.host = host
                config.port = int(port)
            else:
                config.host = url

            client = GrpcClient(config)
            await client.connect()
            return client

        elif self.client_type == "zmq":
            config = ZmqConfig()
            client = ZmqClient(config)
            await client.connect(url)
            return client

        else:
            raise ValueError(f"Unknown type: {self.client_type}")

    def _get_next_client(self) -> Optional[PooledClient]:
        """Selects the next client (round-robin)."""
        healthy = [p for p in self._pool if p.healthy]

        if not healthy:
            return None

        # Round-robin
        client = healthy[self._current_index % len(healthy)]
        self._current_index += 1

        return client

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[Any]:
        """Acquires a client from the pool.

        Yields:
            An available client
        """
        pooled = self._get_next_client()

        if pooled is None:
            raise RuntimeError("No healthy client available")

        try:
            pooled.requests += 1
            yield pooled.client
        except Exception as e:
            pooled.failures += 1
            if pooled.failures >= self.max_failures:
                pooled.healthy = False
            raise

    async def execute(self, operation: Callable[[Any], Any]) -> Any:
        """Executes an operation on a client from the pool.

        Args:
            operation: Function that receives a client and returns a result

        Returns:
            The operation's result
        """
        async with self.acquire() as client:
            return await operation(client)

    async def _health_loop(self):
        """Health check loop."""
        while self._running:
            await asyncio.sleep(self.health_interval)

            for pooled in self._pool:
                try:
                    # Try health check
                    if hasattr(pooled.client, 'health_check'):
                        result = await pooled.client.health_check()
                        pooled.healthy = result.get("status") == "ok"
                    else:
                        # Assume healthy if connected
                        pooled.healthy = True

                    if pooled.healthy:
                        pooled.failures = 0

                except Exception:
                    pooled.failures += 1
                    if pooled.failures >= self.max_failures:
                        pooled.healthy = False

    def get_stats(self) -> dict:
        """Returns pool statistics."""
        return {
            "total": len(self._pool),
            "healthy": sum(1 for p in self._pool if p.healthy),
            "unhealthy": sum(1 for p in self._pool if not p.healthy),
            "clients": [
                {
                    "url": p.url,
                    "healthy": p.healthy,
                    "failures": p.failures,
                    "requests": p.requests
                }
                for p in self._pool
            ]
        }


class StickyClientPool(ClientPool):
    """Pool with sticky sessions.

    A client is selected based on a key (e.g. user_id)
    to ensure the same client is used for the same key.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sticky_map: dict = {}

    def _get_client_for_key(self, key: str) -> Optional[PooledClient]:
        """Selects a client based on a key."""
        healthy = [p for p in self._pool if p.healthy]

        if not healthy:
            return None

        # Consistent hashing
        if key not in self._sticky_map:
            idx = hash(key) % len(healthy)
            self._sticky_map[key] = healthy[idx]

        return self._sticky_map[key]

    @asynccontextmanager
    async def acquire_sticky(self, key: str) -> AsyncIterator[Any]:
        """Acquires the sticky client for a key."""
        pooled = self._get_client_for_key(key)

        if pooled is None:
            raise RuntimeError("No healthy client available")

        try:
            pooled.requests += 1
            yield pooled.client
        except Exception:
            pooled.failures += 1
            if pooled.failures >= self.max_failures:
                pooled.healthy = False
                # Remove from sticky map
                if key in self._sticky_map:
                    del self._sticky_map[key]
            raise
