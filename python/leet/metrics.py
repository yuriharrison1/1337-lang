"""
Metrics and observability system for the 1337 SDK.

Features:
- Automatic performance metrics collection
- Prometheus export
- Structured logging
- Distributed tracing (OpenTelemetry)
"""

from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Protocol
from collections import deque
import threading


class MetricsExporter(Protocol):
    """Protocol for metrics exporters."""

    def export(self, metrics: dict) -> None:
        """Exports metrics."""
        ...


@dataclass
class Histogram:
    """Simple histogram for latencies."""
    buckets: list[float] = field(default_factory=lambda: [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000])
    _values: deque[float] = field(default_factory=lambda: deque(maxlen=10000), repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def observe(self, value: float):
        """Records an observation."""
        with self._lock:
            self._values.append(value)

    def get_buckets(self) -> dict[str, int]:
        """Returns count per bucket."""
        with self._lock:
            result = {}
            for bucket in self.buckets:
                count = sum(1 for v in self._values if v <= bucket)
                result[f"le_{bucket}"] = count
            result["+Inf"] = len(self._values)
            return result

    @property
    def count(self) -> int:
        """Number of observations."""
        with self._lock:
            return len(self._values)

    @property
    def sum(self) -> float:
        """Sum of all observations."""
        with self._lock:
            return sum(self._values)

    @property
    def avg(self) -> float:
        """Average."""
        with self._lock:
            if not self._values:
                return 0.0
            return sum(self._values) / len(self._values)


@dataclass
class Counter:
    """Thread-safe counter."""
    _value: int = field(default=0, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc(self, amount: int = 1):
        """Increments the counter."""
        with self._lock:
            self._value += amount

    @property
    def value(self) -> int:
        """Current value."""
        with self._lock:
            return self._value


@dataclass
class Gauge:
    """Thread-safe gauge (a value that goes up and down)."""
    _value: float = field(default=0.0, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set(self, value: float):
        """Sets the value."""
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1.0):
        """Increments."""
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0):
        """Decrements."""
        with self._lock:
            self._value -= amount

    @property
    def value(self) -> float:
        """Current value."""
        with self._lock:
            return self._value


class MetricsCollector:
    """
    Metrics collector for the 1337 SDK.

    Collects metrics for:
    - Projections (encode/decode)
    - Operations (blend, dist, delta)
    - Cache (hits, misses)
    - Client (requests, latency)

    Example:
        >>> metrics = MetricsCollector()
        >>>
        >>> # Record a projection
        >>> metrics.record_projection(duration_ms=150, cached=False)
        >>>
        >>> # Record an operation
        >>> metrics.record_operation("blend", duration_ms=0.5)
        >>>
        >>> # Export
        >>> print(metrics.export_prometheus())
    """

    def __init__(self):
        # Projections
        self.projections_total = Counter()
        self.projections_cached = Counter()
        self.projection_duration_ms = Histogram()

        # Operations
        self.operations_total = Counter()
        self.operation_duration_ms: dict[str, Histogram] = {}

        # Cache
        self.cache_hits = Counter()
        self.cache_misses = Counter()
        self.cache_size = Gauge()

        # Client
        self.requests_total = Counter()
        self.requests_failed = Counter()
        self.request_duration_ms = Histogram()

        # Connections
        self.active_connections = Gauge()
        self.connection_errors = Counter()

        # Initialize operation histograms
        for op in ["blend", "delta", "dist", "focus", "anomaly_score", "apply_patch"]:
            self.operation_duration_ms[op] = Histogram()

    def record_projection(self, duration_ms: float, cached: bool = False):
        """Records a projection."""
        self.projections_total.inc()
        self.projection_duration_ms.observe(duration_ms)

        if cached:
            self.projections_cached.inc()

    def record_operation(self, operation: str, duration_ms: float):
        """Records an operation."""
        self.operations_total.inc()

        if operation in self.operation_duration_ms:
            self.operation_duration_ms[operation].observe(duration_ms)

    def record_cache_hit(self):
        """Records a cache hit."""
        self.cache_hits.inc()

    def record_cache_miss(self):
        """Records a cache miss."""
        self.cache_misses.inc()

    def set_cache_size(self, size: int):
        """Sets the cache size."""
        self.cache_size.set(float(size))

    def record_request(self, duration_ms: float, success: bool = True):
        """Records a request."""
        self.requests_total.inc()
        self.request_duration_ms.observe(duration_ms)

        if not success:
            self.requests_failed.inc()

    def record_connection_error(self):
        """Records a connection error."""
        self.connection_errors.inc()

    def set_active_connections(self, count: int):
        """Sets the number of active connections."""
        self.active_connections.set(float(count))

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate."""
        hits = self.cache_hits.value
        misses = self.cache_misses.value
        total = hits + misses

        if total == 0:
            return 0.0
        return hits / total

    @property
    def request_success_rate(self) -> float:
        """Request success rate."""
        total = self.requests_total.value
        failed = self.requests_failed.value

        if total == 0:
            return 1.0
        return (total - failed) / total

    def export_prometheus(self) -> str:
        """Exports metrics in Prometheus format."""
        lines = []

        # Projections
        lines.append("# HELP leet_projections_total Total number of projections")
        lines.append("# TYPE leet_projections_total counter")
        lines.append(f"leet_projections_total {self.projections_total.value}")

        lines.append("# HELP leet_projections_cached Total number of projections served from cache")
        lines.append("# TYPE leet_projections_cached counter")
        lines.append(f"leet_projections_cached {self.projections_cached.value}")

        lines.append("# HELP leet_projection_duration_ms Projection duration")
        lines.append("# TYPE leet_projection_duration_ms histogram")
        for bucket, count in self.projection_duration_ms.get_buckets().items():
            lines.append(f'leet_projection_duration_ms_bucket{{le="{bucket}"}} {count}')
        lines.append(f"leet_projection_duration_ms_sum {self.projection_duration_ms.sum}")
        lines.append(f"leet_projection_duration_ms_count {self.projection_duration_ms.count}")

        # Operations
        lines.append("# HELP leet_operations_total Total number of operations")
        lines.append("# TYPE leet_operations_total counter")
        lines.append(f"leet_operations_total {self.operations_total.value}")

        # Cache
        lines.append("# HELP leet_cache_hits Total number of cache hits")
        lines.append("# TYPE leet_cache_hits counter")
        lines.append(f"leet_cache_hits {self.cache_hits.value}")

        lines.append("# HELP leet_cache_misses Total number of cache misses")
        lines.append("# TYPE leet_cache_misses counter")
        lines.append(f"leet_cache_misses {self.cache_misses.value}")

        lines.append("# HELP leet_cache_hit_rate Cache hit rate")
        lines.append("# TYPE leet_cache_hit_rate gauge")
        lines.append(f"leet_cache_hit_rate {self.cache_hit_rate}")

        lines.append("# HELP leet_cache_size Cache size")
        lines.append("# TYPE leet_cache_size gauge")
        lines.append(f"leet_cache_size {self.cache_size.value}")

        # Requests
        lines.append("# HELP leet_requests_total Total number of requests")
        lines.append("# TYPE leet_requests_total counter")
        lines.append(f"leet_requests_total {self.requests_total.value}")

        lines.append("# HELP leet_requests_failed Total number of failed requests")
        lines.append("# TYPE leet_requests_failed counter")
        lines.append(f"leet_requests_failed {self.requests_failed.value}")

        lines.append("# HELP leet_request_success_rate Success rate")
        lines.append("# TYPE leet_request_success_rate gauge")
        lines.append(f"leet_request_success_rate {self.request_success_rate}")

        return "\n".join(lines)

    def export_dict(self) -> dict:
        """Exports metrics as a dict."""
        return {
            "projections": {
                "total": self.projections_total.value,
                "cached": self.projections_cached.value,
                "duration_avg_ms": self.projection_duration_ms.avg,
            },
            "operations": {
                "total": self.operations_total.value,
            },
            "cache": {
                "hits": self.cache_hits.value,
                "misses": self.cache_misses.value,
                "hit_rate": self.cache_hit_rate,
                "size": self.cache_size.value,
            },
            "requests": {
                "total": self.requests_total.value,
                "failed": self.requests_failed.value,
                "success_rate": self.request_success_rate,
                "duration_avg_ms": self.request_duration_ms.avg,
            },
        }


# Decorator for automatic metrics
def timed(metric_name: str, collector: Optional[MetricsCollector] = None):
    """
    Decorator that measures execution time and records metrics.

    Example:
        >>> metrics = MetricsCollector()
        >>>
        >>> @timed("encode", metrics)
        >>> async def encode_text(text: str):
        ...     return await project(text)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception:
                success = False
                raise
            finally:
                duration_ms = (time.perf_counter() - start) * 1000

                if collector:
                    if metric_name == "projection":
                        collector.record_projection(duration_ms, cached=False)
                    elif metric_name in collector.operation_duration_ms:
                        collector.record_operation(metric_name, duration_ms)
                    elif metric_name == "request":
                        collector.record_request(duration_ms, success)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception:
                success = False
                raise
            finally:
                duration_ms = (time.perf_counter() - start) * 1000

                if collector:
                    if metric_name == "projection":
                        collector.record_projection(duration_ms, cached=False)
                    elif metric_name in collector.operation_duration_ms:
                        collector.record_operation(metric_name, duration_ms)
                    elif metric_name == "request":
                        collector.record_request(duration_ms, success)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


@contextmanager
def timed_context(metric_name: str, collector: Optional[MetricsCollector] = None):
    """
    Context manager to measure execution time.

    Example:
        >>> metrics = MetricsCollector()
        >>>
        >>> with timed_context("encode", metrics):
        ...     result = await encode("Hello")
    """
    import asyncio

    start = time.perf_counter()
    success = True

    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000

        if collector:
            if metric_name == "projection":
                collector.record_projection(duration_ms, cached=False)
            elif metric_name in collector.operation_duration_ms:
                collector.record_operation(metric_name, duration_ms)
            elif metric_name == "request":
                collector.record_request(duration_ms, success)


# Global metrics
_global_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Returns the global metrics collector."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = MetricsCollector()
    return _global_metrics


def set_metrics(metrics: MetricsCollector):
    """Sets the global metrics collector."""
    global _global_metrics
    _global_metrics = metrics


class PrometheusExporter:
    """
    Exports metrics to Prometheus via HTTP.

    Example:
        >>> exporter = PrometheusExporter(metrics, port=9090)
        >>> exporter.start()
        >>> # Metrics available at http://localhost:9090/metrics
    """

    def __init__(self, metrics: MetricsCollector, port: int = 9090, host: str = "0.0.0.0"):
        self.metrics = metrics
        self.port = port
        self.host = host
        self._server = None

    def start(self):
        """Starts the metrics HTTP server."""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler

            metrics = self.metrics  # Closure

            class MetricsHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == "/metrics":
                        self.send_response(200)
                        self.send_header("Content-Type", "text/plain")
                        self.end_headers()
                        self.wfile.write(metrics.export_prometheus().encode())
                    else:
                        self.send_response(404)
                        self.end_headers()

                def log_message(self, format, *args):
                    # Silence logs
                    pass

            self._server = HTTPServer((self.host, self.port), MetricsHandler)

            import threading
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()

        except Exception as e:
            raise RuntimeError(f"Failed to start Prometheus exporter: {e}")

    def stop(self):
        """Stops the server."""
        if self._server:
            self._server.shutdown()


# For OpenTelemetry export (future)
class OpenTelemetryExporter:
    """
    Exports metrics via OpenTelemetry.

    Requires: pip install opentelemetry-api opentelemetry-sdk
    """

    def __init__(self, service_name: str = "leet-sdk"):
        self.service_name = service_name
        self._meter = None

        try:
            from opentelemetry import metrics
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create({"service.name": service_name})
            provider = MeterProvider(resource=resource)
            metrics.set_meter_provider(provider)
            self._meter = metrics.get_meter(__name__)

        except ImportError:
            pass

    def export(self, metrics_collector: MetricsCollector):
        """Exports metrics to OpenTelemetry."""
        if not self._meter:
            return

        # Create gauges/counters
        projections_total = self._meter.create_counter("projections_total")
        cache_hits = self._meter.create_counter("cache_hits")
        cache_misses = self._meter.create_counter("cache_misses")

        # Export values
        projections_total.add(metrics_collector.projections_total.value)
        cache_hits.add(metrics_collector.cache_hits.value)
        cache_misses.add(metrics_collector.cache_misses.value)
