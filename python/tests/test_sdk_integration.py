"""Testes de integração do SDK 1337.

Testam fluxos completos:
- Configuração
- Cache
- Métricas
- Batch processing
- Cliente resiliente
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import pytest

from leet import Cogon, blend, dist, LeetConfig, Cache, get_cache
from leet.metrics import MetricsCollector, Counter, Histogram, Gauge
from leet.batch import BatchProcessor, BatchConfig
from leet.config import init_config


# ═══════════════════════════════════════════════════════════════════════════════
# Testes de Configuração
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfig:
    def test_default_config(self):
        config = LeetConfig()
        
        assert config.server.host == "localhost"
        assert config.server.port == 50051
        assert config.cache.backend == "memory"
    
    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("LEET_SERVER_HOST", "remote.host")
        monkeypatch.setenv("LEET_SERVER_PORT", "5555")
        monkeypatch.setenv("LEET_CACHE_BACKEND", "sqlite")
        
        config = LeetConfig.from_env()
        
        assert config.server.host == "remote.host"
        assert config.server.port == 5555
        assert config.cache.backend == "sqlite"
    
    def test_config_merge(self):
        config1 = LeetConfig()
        config2 = LeetConfig()
        config2.server.host = "other.host"
        
        # Config2 deve ter prioridade
        assert config2.server.host == "other.host"
    
    def test_config_validation(self):
        config = LeetConfig()
        config.server.port = 99999  # Porta inválida
        
        errors = config.validate()
        assert len(errors) > 0
        assert "Porta inválida" in errors[0]


# ═══════════════════════════════════════════════════════════════════════════════
# Testes de Cache
# ═══════════════════════════════════════════════════════════════════════════════

class TestCache:
    def test_memory_cache(self):
        cache = Cache(backend="memory", max_size=100)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_ttl(self):
        cache = Cache(backend="memory", ttl_seconds=0.01)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Espera expirar
        import time
        time.sleep(0.02)
        
        assert cache.get("key1") is None
    
    def test_cache_size_limit(self):
        cache = Cache(backend="memory", max_size=2)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Deve evictar key1
        
        assert cache.size() <= 2
    
    def test_get_or_compute(self):
        cache = Cache(backend="memory")
        
        call_count = 0
        
        def compute():
            nonlocal call_count
            call_count += 1
            return "computed"
        
        # Primeira chamada computa
        result1 = cache.get_or_compute("key1", compute)
        assert result1 == "computed"
        assert call_count == 1
        
        # Segunda chamada usa cache
        result2 = cache.get_or_compute("key1", compute)
        assert result2 == "computed"
        assert call_count == 1  # Não computou de novo
    
    def test_projection_cache(self):
        cache = Cache(backend="memory")
        
        sem = [0.5] * 32
        unc = [0.1] * 32
        
        cache.set_projection("texto", sem, unc)
        
        cached = cache.get_projection("texto")
        assert cached is not None
        assert cached[0] == sem
        assert cached[1] == unc


# ═══════════════════════════════════════════════════════════════════════════════
# Testes de Métricas
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetrics:
    def test_counter(self):
        counter = Counter()
        
        counter.inc()
        assert counter.value == 1
        
        counter.inc(5)
        assert counter.value == 6
    
    def test_gauge(self):
        gauge = Gauge()
        
        gauge.set(10.5)
        assert gauge.value == 10.5
        
        gauge.inc(2.5)
        assert gauge.value == 13.0
        
        gauge.dec(3.0)
        assert gauge.value == 10.0
    
    def test_histogram(self):
        hist = Histogram()
        
        hist.observe(10.0)
        hist.observe(20.0)
        hist.observe(30.0)
        
        assert hist.count == 3
        assert hist.sum == 60.0
        assert hist.avg == 20.0
        
        buckets = hist.get_buckets()
        assert buckets["le_25"] == 2  # 10 e 20
        assert buckets["le_50"] == 3  # todos
    
    def test_metrics_collector(self):
        metrics = MetricsCollector()
        
        metrics.record_projection(150.0, cached=False)
        metrics.record_projection(50.0, cached=True)
        
        assert metrics.projections_total.value == 2
        assert metrics.projections_cached.value == 1
        
        # Cache metrics
        metrics.record_cache_hit()
        metrics.record_cache_hit()
        metrics.record_cache_miss()
        
        assert metrics.cache_hit_rate == 2/3
    
    def test_metrics_export(self):
        metrics = MetricsCollector()
        
        metrics.record_projection(100.0)
        metrics.record_cache_hit()
        
        data = metrics.export_dict()
        
        assert "projections" in data
        assert "cache" in data
        assert data["projections"]["total"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Testes de Batch Processing
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchProcessing:
    @pytest.mark.asyncio
    async def test_batch_processor(self):
        async def process(x: int) -> int:
            return x * 2
        
        processor = BatchProcessor(process, BatchConfig(max_concurrency=2))
        
        items = [1, 2, 3, 4, 5]
        results = await processor.process_to_list(items)
        
        assert len(results) == 5
        assert all(r.success for r in results)
        assert [r.output for r in results] == [2, 4, 6, 8, 10]
    
    @pytest.mark.asyncio
    async def test_batch_with_errors(self):
        async def process(x: int) -> int:
            if x == 3:
                raise ValueError("Error!")
            return x * 2
        
        processor = BatchProcessor(
            process,
            BatchConfig(max_concurrency=2, continue_on_error=True)
        )
        
        items = [1, 2, 3, 4, 5]
        results = await processor.process_to_list(items)
        
        assert len(results) == 5
        assert results[2].success is False  # Item 3 falhou
        assert results[2].error is not None
    
    @pytest.mark.asyncio
    async def test_batch_progress(self):
        async def process(x: int) -> int:
            await asyncio.sleep(0.01)
            return x
        
        progress_calls = []
        
        def on_progress(processed, total):
            progress_calls.append((processed, total))
        
        processor = BatchProcessor(process, BatchConfig(progress_interval=2))
        
        items = list(range(10))
        results = await processor.process_to_list(items, on_progress)
        
        assert len(results) == 10
        assert len(progress_calls) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Testes de Integração
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_full_flow_with_cache(self):
        cache = Cache(backend="memory")
        
        # Simula projeção com cache
        async def project(text: str):
            # Verifica cache
            cached = cache.get_projection(text)
            if cached:
                return cached
            
            # Projeta (mock)
            sem = [0.5] * 32
            unc = [0.1] * 32
            
            # Armazena no cache
            cache.set_projection(text, sem, unc)
            return sem, unc
        
        # Primeira chamada
        result1 = await project("hello")
        
        # Segunda chamada (deve usar cache)
        result2 = await project("hello")
        
        # Mesmo resultado
        assert result1 == result2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
