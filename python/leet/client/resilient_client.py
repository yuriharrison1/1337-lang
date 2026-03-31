"""
Cliente resiliente com retry, circuit breaker e fallback.

Este módulo fornece um cliente robusto para comunicação com o leet-service,
com recursos de resiliência como:
- Retry automático com backoff exponencial
- Circuit breaker para evitar cascata de falhas
- Fallback entre gRPC e HTTP
- Health checking contínuo
- Pool de conexões
"""

from __future__ import annotations

import asyncio
import functools
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable, TypeVar, Any, AsyncIterator
import logging

logger = logging.getLogger(__name__)


T = TypeVar('T')


class CircuitState(Enum):
    """Estados do circuit breaker."""
    CLOSED = auto()      # Normal - requests passam
    OPEN = auto()        # Falha - requests rejeitados
    HALF_OPEN = auto()   # Testando - um request permitido


@dataclass
class CircuitBreaker:
    """
    Circuit breaker para evitar cascata de falhas.
    
    Quando o número de falhas excede o limite, o circuito "abre"
    e rejeita novos requests por um período de cooldown.
    """
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    
    _state: CircuitState = field(default=CircuitState.CLOSED, repr=False)
    _failures: int = field(default=0, repr=False)
    _last_failure_time: float = field(default=0.0, repr=False)
    _half_open_calls: int = field(default=0, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    
    @property
    def state(self) -> CircuitState:
        """Retorna estado atual do circuito."""
        if self._state == CircuitState.OPEN:
            # Verifica se deve tentar half-open
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit breaker: OPEN -> HALF_OPEN")
        return self._state
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Executa função com proteção do circuit breaker.
        
        Args:
            func: Função a ser protegida
            *args, **kwargs: Argumentos da função
            
        Returns:
            Resultado da função
            
        Raises:
            CircuitBreakerOpen: Se circuito está aberto
            Exception: Se função falha
        """
        async with self._lock:
            current_state = self.state
            
            if current_state == CircuitState.OPEN:
                raise CircuitBreakerOpen("Circuit breaker is OPEN")
            
            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpen("Circuit breaker HALF_OPEN limit reached")
                self._half_open_calls += 1
        
        # Executa fora do lock
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self):
        """Registra sucesso."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # Sucesso em half-open fecha o circuito
                self._state = CircuitState.CLOSED
                self._failures = 0
                self._half_open_calls = 0
                logger.info("Circuit breaker: HALF_OPEN -> CLOSED")
    
    async def _on_failure(self):
        """Registra falha."""
        async with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Falha em half-open reabre o circuito
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker: HALF_OPEN -> OPEN ({self._failures} failures)")
            elif self._failures >= self.failure_threshold:
                if self._state == CircuitState.CLOSED:
                    self._state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker: CLOSED -> OPEN ({self._failures} failures)")


class CircuitBreakerOpen(Exception):
    """Exceção quando circuit breaker está aberto."""
    pass


@dataclass
class RetryConfig:
    """Configuração de retry."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)


async def with_retry(
    func: Callable[..., T],
    config: RetryConfig,
    *args,
    **kwargs
) -> T:
    """
    Executa função com retry e backoff exponencial.
    
    Args:
        func: Função a ser executada
        config: Configuração de retry
        *args, **kwargs: Argumentos da função
        
    Returns:
        Resultado da função
        
    Raises:
        Exception: Se todas as tentativas falharem
    """
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt == config.max_retries:
                logger.error(f"All {config.max_retries} retries failed: {e}")
                raise
            
            # Calcula delay com backoff exponencial
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay
            )
            
            # Adiciona jitter para evitar thundering herd
            if config.jitter:
                delay *= (0.5 + random.random() * 0.5)
            
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)
    
    # Não deveria chegar aqui
    raise last_exception


@dataclass
class ClientMetrics:
    """Métricas do cliente."""
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    requests_retried: int = 0
    latency_ms: list[float] = field(default_factory=list)
    circuit_breaker_state: str = "CLOSED"
    last_error: Optional[str] = None
    last_success_time: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        """Taxa de sucesso (0-1)."""
        if self.requests_total == 0:
            return 1.0
        return self.requests_success / self.requests_total
    
    @property
    def avg_latency_ms(self) -> float:
        """Latência média em ms."""
        if not self.latency_ms:
            return 0.0
        return sum(self.latency_ms) / len(self.latency_ms)
    
    def record_request(self, success: bool, latency: float, retried: bool = False):
        """Registra uma requisição."""
        self.requests_total += 1
        if success:
            self.requests_success += 1
            self.last_success_time = time.time()
        else:
            self.requests_failed += 1
        
        if retried:
            self.requests_retried += 1
        
        self.latency_ms.append(latency)
        # Mantém apenas últimas 1000 latências
        if len(self.latency_ms) > 1000:
            self.latency_ms = self.latency_ms[-1000:]
    
    def to_dict(self) -> dict:
        """Converte para dict."""
        return {
            "requests_total": self.requests_total,
            "requests_success": self.requests_success,
            "requests_failed": self.requests_failed,
            "requests_retried": self.requests_retried,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "circuit_breaker_state": self.circuit_breaker_state,
            "last_error": self.last_error,
        }


class ResilientClient:
    """
    Cliente resiliente com retry, circuit breaker e métricas.
    
    Esta é uma camada de abstração que envolve qualquer cliente
    (gRPC, HTTP, etc.) com recursos de resiliência.
    
    Example:
        >>> base_client = GrpcClient(GrpcConfig())
        >>> resilient = ResilientClient(base_client)
        >>> await resilient.connect()
        >>> 
        >>> # Tenta encode com retry automático
        >>> result = await resilient.encode("Hello", agent_id="agent1")
        >>> 
        >>> # Métricas
        >>> print(resilient.metrics.success_rate)
    """
    
    def __init__(
        self,
        base_client: Any,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        """
        Args:
            base_client: Cliente base (GrpcClient, HttpClient, etc.)
            retry_config: Configuração de retry
            circuit_breaker: Circuit breaker customizado
        """
        self.base = base_client
        self.retry_config = retry_config or RetryConfig()
        self.circuit = circuit_breaker or CircuitBreaker()
        self.metrics = ClientMetrics()
        
    async def connect(self) -> "ResilientClient":
        """Conecta o cliente base."""
        await self.base.connect()
        return self
    
    async def close(self):
        """Fecha conexão."""
        await self.base.close()
    
    async def __aenter__(self) -> "ResilientClient":
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _execute(
        self,
        operation: str,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Executa operação com retry e circuit breaker.
        
        Args:
            operation: Nome da operação (para logging)
            func: Função a executar
            *args, **kwargs: Argumentos
            
        Returns:
            Resultado da operação
        """
        start_time = time.time()
        retried = False
        
        async def wrapped():
            nonlocal retried
            try:
                return await self.circuit.call(func, *args, **kwargs)
            except CircuitBreakerOpen:
                raise
            except Exception as e:
                retried = True
                raise
        
        try:
            # Tenta com retry
            result = await with_retry(wrapped, self.retry_config)
            
            # Registra sucesso
            latency = (time.time() - start_time) * 1000
            self.metrics.record_request(True, latency, retried)
            self.metrics.circuit_breaker_state = self.circuit.state.name
            
            return result
            
        except Exception as e:
            # Registra falha
            latency = (time.time() - start_time) * 1000
            self.metrics.record_request(False, latency, retried)
            self.metrics.last_error = str(e)
            self.metrics.circuit_breaker_state = self.circuit.state.name
            
            logger.error(f"Operation {operation} failed after all retries: {e}")
            raise
    
    # Proxies para métodos do cliente base
    
    async def encode(self, text: str, **kwargs) -> Any:
        """Encode com resiliência."""
        return await self._execute("encode", self.base.encode, text, **kwargs)
    
    async def decode(self, sem: list[float], unc: list[float], **kwargs) -> str:
        """Decode com resiliência."""
        return await self._execute("decode", self.base.decode, sem, unc, **kwargs)
    
    async def delta(self, sem_prev: list[float], sem_curr: list[float]) -> tuple:
        """Delta com resiliência."""
        return await self._execute("delta", self.base.delta, sem_prev, sem_curr)
    
    async def recall(self, sem: list[float], unc: list[float], **kwargs) -> list:
        """Recall com resiliência."""
        return await self._execute("recall", self.base.recall, sem, unc, **kwargs)
    
    async def health_check(self) -> dict:
        """Health check com resiliência."""
        try:
            return await self._execute("health_check", self.base.health_check)
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "circuit_state": self.circuit.state.name
            }
    
    async def encode_batch(
        self,
        texts: list[str],
        **kwargs
    ) -> AsyncIterator[Any]:
        """
        Encode batch com resiliência.
        
        Yields resultados à medida que ficam prontos.
        """
        semaphore = asyncio.Semaphore(10)  # Limita concorrência
        
        async def encode_one(text: str) -> Any:
            async with semaphore:
                return await self.encode(text, **kwargs)
        
        # Executa em paralelo com limite
        tasks = [encode_one(text) for text in texts]
        
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                yield result
            except Exception as e:
                logger.error(f"Batch item failed: {e}")
                yield None


class FallbackClient:
    """
    Cliente com fallback entre múltiplos backends.
    
    Tenta o primeiro cliente, se falhar usa o segundo.
    
    Example:
        >>> primary = GrpcClient(GrpcConfig(host="server1"))
        >>> secondary = HttpClient("http://server2:8080")
        >>> fallback = FallbackClient([primary, secondary])
        >>> 
        >>> result = await fallback.encode("Hello")
    """
    
    def __init__(self, clients: list[Any]):
        """
        Args:
            clients: Lista de clientes em ordem de preferência
        """
        self.clients = clients
        self.metrics = {i: ClientMetrics() for i in range(len(clients))}
        self._current_index = 0
    
    async def connect(self):
        """Conecta todos os clientes."""
        for client in self.clients:
            await client.connect()
    
    async def close(self):
        """Fecha todos os clientes."""
        for client in self.clients:
            await client.close()
    
    async def _try_clients(self, operation: str, *args, **kwargs):
        """
        Tenta executar em cada cliente até um funcionar.
        
        Returns:
            Tuple (index_do_cliente, resultado)
        """
        errors = []
        
        # Começa pelo cliente atual (pode ter sido alterado por falha anterior)
        order = list(range(self._current_index, len(self.clients))) + \
                list(range(0, self._current_index))
        
        for idx in order:
            client = self.clients[idx]
            start_time = time.time()
            
            try:
                func = getattr(client, operation)
                result = await func(*args, **kwargs)
                
                # Sucesso - registra métricas
                latency = (time.time() - start_time) * 1000
                self.metrics[idx].record_request(True, latency)
                
                # Se usou cliente diferente do primário, atualiza índice
                if idx != self._current_index:
                    logger.info(f"Fallback: switched back to client {idx}")
                    self._current_index = idx
                
                return idx, result
                
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                self.metrics[idx].record_request(False, latency)
                self.metrics[idx].last_error = str(e)
                errors.append(f"Client {idx}: {e}")
                continue
        
        # Todos falharam
        raise RuntimeError(f"All clients failed: {'; '.join(errors)}")
    
    async def encode(self, text: str, **kwargs):
        """Encode com fallback."""
        _, result = await self._try_clients("encode", text, **kwargs)
        return result
    
    async def decode(self, sem: list[float], unc: list[float], **kwargs):
        """Decode com fallback."""
        _, result = await self._try_clients("decode", sem, unc, **kwargs)
        return result
    
    async def delta(self, sem_prev: list[float], sem_curr: list[float]):
        """Delta com fallback."""
        _, result = await self._try_clients("delta", sem_prev, sem_curr)
        return result
    
    async def health_check(self) -> dict:
        """Health check de todos os clientes."""
        results = []
        for i, client in enumerate(self.clients):
            try:
                health = await client.health_check()
                health["client_index"] = i
                health["metrics"] = self.metrics[i].to_dict()
                results.append(health)
            except Exception as e:
                results.append({
                    "client_index": i,
                    "status": "error",
                    "error": str(e),
                    "metrics": self.metrics[i].to_dict()
                })
        
        return {
            "clients": results,
            "current_client": self._current_index,
            "healthy_clients": sum(1 for r in results if r.get("status") == "ok")
        }


# Factory function para criar cliente completo
def create_resilient_client(
    host: str = "localhost",
    port: int = 50051,
    fallback_hosts: Optional[list[str]] = None,
    enable_retry: bool = True,
    enable_circuit_breaker: bool = True,
) -> ResilientClient | FallbackClient:
    """
    Cria um cliente resiliente completo.
    
    Args:
        host: Host primário
        port: Porta
        fallback_hosts: Lista de hosts fallback
        enable_retry: Se habilita retry
        enable_circuit_breaker: Se habilita circuit breaker
        
    Returns:
        Cliente configurado
    """
    from .grpc_client import GrpcClient, GrpcConfig
    
    # Cliente primário
    primary = GrpcClient(GrpcConfig(host=host, port=port))
    
    # Se tem fallback, cria FallbackClient
    if fallback_hosts:
        clients = [primary]
        for fallback_host in fallback_hosts:
            if ":" in fallback_host:
                h, p = fallback_host.split(":")
                clients.append(GrpcClient(GrpcConfig(host=h, port=int(p))))
            else:
                clients.append(GrpcClient(GrpcConfig(host=fallback_host, port=port)))
        
        return FallbackClient(clients)
    
    # Cliente único com resiliência
    retry_config = RetryConfig() if enable_retry else None
    circuit = CircuitBreaker() if enable_circuit_breaker else None
    
    return ResilientClient(primary, retry_config, circuit)
