"""Pool de clientes para conexões eficientes.

Gerencia pool de conexões gRPC/ZeroMQ para:
- Reutilização de conexões
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
    """Cliente em pool com metadata."""
    client: Any
    url: str
    healthy: bool = True
    failures: int = 0
    requests: int = 0


class ClientPool:
    """Pool de clientes para load balancing.
    
    Distribui requisições entre múltiplos endpoints
    com health checking e circuit breaker.
    
    Args:
        urls: Lista de URLs de endpoints
        client_type: Tipo de cliente (grpc, zmq)
        max_failures: Máximo de falhas antes de marcar unhealthy
        health_interval: Intervalo de health check
        
    Example:
        >>> pool = ClientPool([
        ...     "localhost:50051",
        ...     "localhost:50052"
        ])
        >>> 
        >>> # Round-robin automático
        >>> result = await pool.execute(lambda c: c.encode("hello"))
        >>> 
        >>> # Ou com context manager
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
        """Inicia pool e conecta clientes."""
        self._running = True
        
        for url in self.urls:
            client = await self._create_client(url)
            self._pool.append(PooledClient(client, url))
        
        # Inicia health checks
        self._health_task = asyncio.create_task(self._health_loop())
    
    async def stop(self):
        """Para pool e fecha conexões."""
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
        """Cria cliente para URL."""
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
            raise ValueError(f"Tipo desconhecido: {self.client_type}")
    
    def _get_next_client(self) -> Optional[PooledClient]:
        """Seleciona próximo cliente (round-robin)."""
        healthy = [p for p in self._pool if p.healthy]
        
        if not healthy:
            return None
        
        # Round-robin
        client = healthy[self._current_index % len(healthy)]
        self._current_index += 1
        
        return client
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[Any]:
        """Adquire cliente do pool.
        
        Yields:
            Cliente disponível
        """
        pooled = self._get_next_client()
        
        if pooled is None:
            raise RuntimeError("Nenhum cliente healthy disponível")
        
        try:
            pooled.requests += 1
            yield pooled.client
        except Exception as e:
            pooled.failures += 1
            if pooled.failures >= self.max_failures:
                pooled.healthy = False
            raise
    
    async def execute(self, operation: Callable[[Any], Any]) -> Any:
        """Executa operação em cliente do pool.
        
        Args:
            operation: Função que recebe cliente e retorna resultado
            
        Returns:
            Resultado da operação
        """
        async with self.acquire() as client:
            return await operation(client)
    
    async def _health_loop(self):
        """Loop de health check."""
        while self._running:
            await asyncio.sleep(self.health_interval)
            
            for pooled in self._pool:
                try:
                    # Tenta health check
                    if hasattr(pooled.client, 'health_check'):
                        result = await pooled.client.health_check()
                        pooled.healthy = result.get("status") == "ok"
                    else:
                        # Assume healthy se conectado
                        pooled.healthy = True
                    
                    if pooled.healthy:
                        pooled.failures = 0
                        
                except Exception:
                    pooled.failures += 1
                    if pooled.failures >= self.max_failures:
                        pooled.healthy = False
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do pool."""
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
    """Pool com sticky sessions.
    
    Cliente é selecionado baseado em uma chave (ex: user_id)
    para garantir que o mesmo cliente seja usado para a mesma chave.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sticky_map: dict = {}
    
    def _get_client_for_key(self, key: str) -> Optional[PooledClient]:
        """Seleciona cliente baseado em chave."""
        healthy = [p for p in self._pool if p.healthy]
        
        if not healthy:
            return None
        
        # Hash consistente
        if key not in self._sticky_map:
            idx = hash(key) % len(healthy)
            self._sticky_map[key] = healthy[idx]
        
        return self._sticky_map[key]
    
    @asynccontextmanager
    async def acquire_sticky(self, key: str) -> AsyncIterator[Any]:
        """Adquire cliente sticky para chave."""
        pooled = self._get_client_for_key(key)
        
        if pooled is None:
            raise RuntimeError("Nenhum cliente healthy disponível")
        
        try:
            pooled.requests += 1
            yield pooled.client
        except Exception:
            pooled.failures += 1
            if pooled.failures >= self.max_failures:
                pooled.healthy = False
                # Remove do sticky map
                if key in self._sticky_map:
                    del self._sticky_map[key]
            raise
