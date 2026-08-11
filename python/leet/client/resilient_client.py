"""
Resilient client with retry, circuit breaker and fallback.

This module provides a robust client for communicating with leet-service,
with resilience features such as:
- Automatic retry with exponential backoff
- Circuit breaker to avoid cascading failures
- Fallback between gRPC and HTTP
- Continuous health checking
- Connection pool
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
    """Circuit breaker states."""
    CLOSED = auto()      # Normal - requests pass through
    OPEN = auto()        # Failing - requests rejected
    HALF_OPEN = auto()   # Testing - one request allowed


@dataclass
class CircuitBreaker:
    """
    Circuit breaker to avoid cascading failures.

    When the number of failures exceeds the threshold, the circuit "opens"
    and rejects new requests for a cooldown period.
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
        """Returns the current circuit state."""
        if self._state == CircuitState.OPEN:
            # Check whether to try half-open
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit breaker: OPEN -> HALF_OPEN")
        return self._state

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Executes a function protected by the circuit breaker.

        Args:
            func: Function to protect
            *args, **kwargs: Function arguments

        Returns:
            The function's result

        Raises:
            CircuitBreakerOpen: If the circuit is open
            Exception: If the function fails
        """
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                raise CircuitBreakerOpen("Circuit breaker is OPEN")

            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpen("Circuit breaker HALF_OPEN limit reached")
                self._half_open_calls += 1

        # Execute outside the lock
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise

    async def _on_success(self):
        """Records a success."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # Success in half-open closes the circuit
                self._state = CircuitState.CLOSED
                self._failures = 0
                self._half_open_calls = 0
                logger.info("Circuit breaker: HALF_OPEN -> CLOSED")

    async def _on_failure(self):
        """Records a failure."""
        async with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Failure in half-open reopens the circuit
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker: HALF_OPEN -> OPEN ({self._failures} failures)")
            elif self._failures >= self.failure_threshold:
                if self._state == CircuitState.CLOSED:
                    self._state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker: CLOSED -> OPEN ({self._failures} failures)")


class CircuitBreakerOpen(Exception):
    """Exception raised when the circuit breaker is open."""
    pass


@dataclass
class RetryConfig:
    """Retry configuration."""
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
    Executes a function with retry and exponential backoff.

    Args:
        func: Function to execute
        config: Retry configuration
        *args, **kwargs: Function arguments

    Returns:
        The function's result

    Raises:
        Exception: If all attempts fail
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

            # Compute delay with exponential backoff
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay
            )

            # Add jitter to avoid thundering herd
            if config.jitter:
                delay *= (0.5 + random.random() * 0.5)

            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)

    # Should not reach here
    raise last_exception


@dataclass
class ClientMetrics:
    """Client metrics."""
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
        """Success rate (0-1)."""
        if self.requests_total == 0:
            return 1.0
        return self.requests_success / self.requests_total

    @property
    def avg_latency_ms(self) -> float:
        """Average latency in ms."""
        if not self.latency_ms:
            return 0.0
        return sum(self.latency_ms) / len(self.latency_ms)

    def record_request(self, success: bool, latency: float, retried: bool = False):
        """Records a request."""
        self.requests_total += 1
        if success:
            self.requests_success += 1
            self.last_success_time = time.time()
        else:
            self.requests_failed += 1

        if retried:
            self.requests_retried += 1

        self.latency_ms.append(latency)
        # Keep only the last 1000 latencies
        if len(self.latency_ms) > 1000:
            self.latency_ms = self.latency_ms[-1000:]

    def to_dict(self) -> dict:
        """Converts to a dict."""
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
    Resilient client with retry, circuit breaker and metrics.

    This is an abstraction layer that wraps any client
    (gRPC, HTTP, etc.) with resilience features.

    Example:
        >>> base_client = GrpcClient(GrpcConfig())
        >>> resilient = ResilientClient(base_client)
        >>> await resilient.connect()
        >>>
        >>> # Try encode with automatic retry
        >>> result = await resilient.encode("Hello", agent_id="agent1")
        >>>
        >>> # Metrics
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
            base_client: Base client (GrpcClient, HttpClient, etc.)
            retry_config: Retry configuration
            circuit_breaker: Custom circuit breaker
        """
        self.base = base_client
        self.retry_config = retry_config or RetryConfig()
        self.circuit = circuit_breaker or CircuitBreaker()
        self.metrics = ClientMetrics()

    async def connect(self) -> "ResilientClient":
        """Connects the base client."""
        await self.base.connect()
        return self

    async def close(self):
        """Closes the connection."""
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
        Executes an operation with retry and circuit breaker.

        Args:
            operation: Operation name (for logging)
            func: Function to execute
            *args, **kwargs: Arguments

        Returns:
            The operation's result
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
            # Try with retry
            result = await with_retry(wrapped, self.retry_config)

            # Record success
            latency = (time.time() - start_time) * 1000
            self.metrics.record_request(True, latency, retried)
            self.metrics.circuit_breaker_state = self.circuit.state.name

            return result

        except Exception as e:
            # Record failure
            latency = (time.time() - start_time) * 1000
            self.metrics.record_request(False, latency, retried)
            self.metrics.last_error = str(e)
            self.metrics.circuit_breaker_state = self.circuit.state.name

            logger.error(f"Operation {operation} failed after all retries: {e}")
            raise

    # Proxies for base client methods

    async def encode(self, text: str, **kwargs) -> Any:
        """Encode with resilience."""
        return await self._execute("encode", self.base.encode, text, **kwargs)

    async def decode(self, sem: list[float], unc: list[float], **kwargs) -> str:
        """Decode with resilience."""
        return await self._execute("decode", self.base.decode, sem, unc, **kwargs)

    async def delta(self, sem_prev: list[float], sem_curr: list[float]) -> tuple:
        """Delta with resilience."""
        return await self._execute("delta", self.base.delta, sem_prev, sem_curr)

    async def recall(self, sem: list[float], unc: list[float], **kwargs) -> list:
        """Recall with resilience."""
        return await self._execute("recall", self.base.recall, sem, unc, **kwargs)

    async def health_check(self) -> dict:
        """Health check with resilience."""
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
        Encode batch with resilience.

        Yields results as they become ready.
        """
        semaphore = asyncio.Semaphore(10)  # Limits concurrency

        async def encode_one(text: str) -> Any:
            async with semaphore:
                return await self.encode(text, **kwargs)

        # Run in parallel with a limit
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
    Client with fallback across multiple backends.

    Tries the first client; if it fails, uses the second.

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
            clients: List of clients in order of preference
        """
        self.clients = clients
        self.metrics = {i: ClientMetrics() for i in range(len(clients))}
        self._current_index = 0

    async def connect(self):
        """Connects all clients."""
        for client in self.clients:
            await client.connect()

    async def close(self):
        """Closes all clients."""
        for client in self.clients:
            await client.close()

    async def _try_clients(self, operation: str, *args, **kwargs):
        """
        Tries to execute on each client until one succeeds.

        Returns:
            Tuple (client_index, result)
        """
        errors = []

        # Start from the current client (may have changed due to a previous failure)
        order = list(range(self._current_index, len(self.clients))) + \
                list(range(0, self._current_index))

        for idx in order:
            client = self.clients[idx]
            start_time = time.time()

            try:
                func = getattr(client, operation)
                result = await func(*args, **kwargs)

                # Success - record metrics
                latency = (time.time() - start_time) * 1000
                self.metrics[idx].record_request(True, latency)

                # If a different client than the primary was used, update the index
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

        # All failed
        raise RuntimeError(f"All clients failed: {'; '.join(errors)}")

    async def encode(self, text: str, **kwargs):
        """Encode with fallback."""
        _, result = await self._try_clients("encode", text, **kwargs)
        return result

    async def decode(self, sem: list[float], unc: list[float], **kwargs):
        """Decode with fallback."""
        _, result = await self._try_clients("decode", sem, unc, **kwargs)
        return result

    async def delta(self, sem_prev: list[float], sem_curr: list[float]):
        """Delta with fallback."""
        _, result = await self._try_clients("delta", sem_prev, sem_curr)
        return result

    async def health_check(self) -> dict:
        """Health check for all clients."""
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


# Factory function to create a full client
def create_resilient_client(
    host: str = "localhost",
    port: int = 50051,
    fallback_hosts: Optional[list[str]] = None,
    enable_retry: bool = True,
    enable_circuit_breaker: bool = True,
) -> ResilientClient | FallbackClient:
    """
    Creates a fully configured resilient client.

    Args:
        host: Primary host
        port: Port
        fallback_hosts: List of fallback hosts
        enable_retry: Whether to enable retry
        enable_circuit_breaker: Whether to enable circuit breaker

    Returns:
        Configured client
    """
    from .grpc_client import GrpcClient, GrpcConfig

    # Primary client
    primary = GrpcClient(GrpcConfig(host=host, port=port))

    # If fallback is configured, create a FallbackClient
    if fallback_hosts:
        clients = [primary]
        for fallback_host in fallback_hosts:
            if ":" in fallback_host:
                h, p = fallback_host.split(":")
                clients.append(GrpcClient(GrpcConfig(host=h, port=int(p))))
            else:
                clients.append(GrpcClient(GrpcConfig(host=fallback_host, port=port)))

        return FallbackClient(clients)

    # Single client with resilience
    retry_config = RetryConfig() if enable_retry else None
    circuit = CircuitBreaker() if enable_circuit_breaker else None

    return ResilientClient(primary, retry_config, circuit)
