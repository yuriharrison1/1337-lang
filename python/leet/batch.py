"""
Sistema de processamento em batch para o SDK 1337.

Permite processar múltiplos textos/COGONs de forma eficiente com:
- Paralelização controlada
- Chunking automático
- Progress reporting
- Error handling parcial
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Callable, TypeVar, Generic, AsyncIterator, Optional, Any
from collections import deque
import logging

from leet.types import Cogon
from leet.bridge import SemanticProjector

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class BatchResult(Generic[T, R]):
    """Resultado de processamento de um item."""
    index: int
    input: T
    output: Optional[R] = None
    error: Optional[Exception] = None
    duration_ms: float = 0.0
    
    @property
    def success(self) -> bool:
        """Retorna True se processamento foi bem-sucedido."""
        return self.error is None and self.output is not None


@dataclass
class BatchConfig:
    """Configuração de batch processing."""
    batch_size: int = 100
    max_concurrency: int = 10
    continue_on_error: bool = True
    error_threshold: float = 0.5  # Aborta se mais de 50% de erros
    progress_interval: int = 10   # Reporta progresso a cada N itens


class BatchProcessor(Generic[T, R]):
    """
    Processador de batch genérico.
    
    Example:
        >>> async def process_text(text: str) -> Cogon:
        ...     return await encode(text)
        >>> 
        >>> processor = BatchProcessor(process_text, BatchConfig(max_concurrency=5))
        >>> 
        >>> texts = ["text1", "text2", "text3"]
        >>> async for result in processor.process(texts):
        ...     if result.success:
        ...         print(f"{result.index}: {result.output}")
        ...     else:
        ...         print(f"{result.index}: ERROR - {result.error}")
    """
    
    def __init__(
        self,
        process_fn: Callable[[T], R],
        config: Optional[BatchConfig] = None
    ):
        """
        Args:
            process_fn: Função de processamento
            config: Configuração de batch
        """
        self.process_fn = process_fn
        self.config = config or BatchConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrency)
        self._processed = 0
        self._errors = 0
    
    async def _process_one(self, index: int, item: T) -> BatchResult[T, R]:
        """Processa um item com controle de concorrência."""
        import time
        
        start = time.perf_counter()
        
        async with self._semaphore:
            try:
                if asyncio.iscoroutinefunction(self.process_fn):
                    output = await self.process_fn(item)
                else:
                    output = self.process_fn(item)
                
                duration = (time.perf_counter() - start) * 1000
                self._processed += 1
                
                return BatchResult(
                    index=index,
                    input=item,
                    output=output,
                    duration_ms=duration
                )
                
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                self._processed += 1
                self._errors += 1
                
                logger.error(f"Error processing item {index}: {e}")
                
                return BatchResult(
                    index=index,
                    input=item,
                    error=e,
                    duration_ms=duration
                )
    
    async def process(
        self,
        items: list[T],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> AsyncIterator[BatchResult[T, R]]:
        """
        Processa lista de items.
        
        Args:
            items: Lista de items a processar
            on_progress: Callback (processed, total) -> None
            
        Yields:
            BatchResult para cada item
        """
        self._processed = 0
        self._errors = 0
        total = len(items)
        
        # Cria tasks
        tasks = [
            asyncio.create_task(self._process_one(i, item))
            for i, item in enumerate(items)
        ]
        
        # Processa conforme completam
        completed = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1
            
            # Reporta progresso
            if on_progress and completed % self.config.progress_interval == 0:
                on_progress(completed, total)
            
            # Verifica threshold de erro
            if self._errors / completed > self.config.error_threshold:
                if not self.config.continue_on_error:
                    # Cancela tasks restantes
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    raise RuntimeError(
                        f"Error threshold exceeded: {self._errors}/{completed}"
                    )
            
            yield result
        
        # Progresso final
        if on_progress:
            on_progress(completed, total)
    
    async def process_to_list(
        self,
        items: list[T],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> list[BatchResult[T, R]]:
        """
        Processa e retorna lista de resultados.
        
        Args:
            items: Lista de items
            on_progress: Callback de progresso
            
        Returns:
            Lista de BatchResult (na mesma ordem de items)
        """
        results = []
        async for result in self.process(items, on_progress):
            results.append(result)
        
        # Ordena por índice
        results.sort(key=lambda r: r.index)
        return results


class ProjectionBatcher:
    """
    Batcher especializado para projeções de texto.
    
    Example:
        >>> batcher = ProjectionBatcher(projector, BatchConfig(max_concurrency=5))
        >>> 
        >>> texts = ["Hello", "World", "Foo", "Bar"]
        >>> results = await batcher.project(texts)
        >>> 
        >>> for text, cogon in results:
        ...     print(f"{text}: {cogon.sem[:5]}")
    """
    
    def __init__(
        self,
        projector: SemanticProjector,
        config: Optional[BatchConfig] = None
    ):
        self.projector = projector
        self.config = config or BatchConfig()
    
    async def project(
        self,
        texts: list[str],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> list[tuple[str, Optional[Cogon]]]:
        """
        Projeta múltiplos textos.
        
        Args:
            texts: Lista de textos
            on_progress: Callback de progresso
            
        Returns:
            Lista de (texto, cogon) - cogon pode ser None se falhou
        """
        async def project_one(text: str) -> Optional[Cogon]:
            try:
                sem, unc = await self.projector.project(text)
                return Cogon.new(sem=sem, unc=unc)
            except Exception as e:
                logger.error(f"Failed to project '{text[:50]}...': {e}")
                return None
        
        processor: BatchProcessor[str, Optional[Cogon]] = BatchProcessor(
            project_one,
            self.config
        )
        
        results = await processor.process_to_list(texts, on_progress)
        
        return [
            (result.input, result.output)
            for result in results
        ]
    
    async def project_with_cache(
        self,
        texts: list[str],
        cache: Any,  # Cache
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> list[tuple[str, Optional[Cogon]]]:
        """
        Projeta com cache - usa cache para hits, projeta misses.
        
        Args:
            texts: Lista de textos
            cache: Instância de Cache
            on_progress: Callback de progresso
            
        Returns:
            Lista de (texto, cogon)
        """
        # Separa hits e misses
        hits: dict[int, Cogon] = {}
        misses: list[tuple[int, str]] = []
        
        for i, text in enumerate(texts):
            cached = cache.get_projection(text)
            if cached:
                sem, unc = cached
                hits[i] = Cogon.new(sem=sem, unc=unc)
            else:
                misses.append((i, text))
        
        # Projeta misses
        if misses:
            indices, miss_texts = zip(*misses)
            
            projected = await self.project(list(miss_texts), on_progress)
            
            # Armazena no cache e junta com hits
            for idx, (text, cogon) in zip(indices, projected):
                if cogon:
                    cache.set_projection(text, cogon.sem, cogon.unc)
                    hits[idx] = cogon
        
        # Ordena por índice original
        return [
            (texts[i], hits.get(i))
            for i in range(len(texts))
        ]


class StreamingBatcher:
    """
    Batcher para processamento contínuo (streaming).
    
    Processa items à medida que chegam, com buffering.
    
    Example:
        >>> batcher = StreamingBatcher(process_fn, max_buffer=100)
        >>> 
        >>> # Produz items
        >>> for text in stream:
        ...     await batcher.put(text)
        >>> 
        >>> # Finaliza e processa
        >>> await batcher.close()
        >>> 
        >>> async for result in batcher.results():
        ...     print(result.output)
    """
    
    def __init__(
        self,
        process_fn: Callable[[T], R],
        max_buffer: int = 100,
        max_concurrency: int = 10
    ):
        self.process_fn = process_fn
        self.max_buffer = max_buffer
        self.max_concurrency = max_concurrency
        
        self._buffer: deque[T] = deque(maxlen=max_buffer)
        self._results: deque[BatchResult[T, R]] = deque()
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._closed = False
        self._tasks: set[asyncio.Task] = set()
    
    async def put(self, item: T) -> None:
        """Adiciona item ao buffer."""
        if self._closed:
            raise RuntimeError("Batcher is closed")
        
        self._buffer.append(item)
        
        # Processa se buffer cheio
        if len(self._buffer) >= self.max_buffer:
            await self._flush()
    
    async def _flush(self) -> None:
        """Processa todos os items no buffer."""
        if not self._buffer:
            return
        
        items = list(self._buffer)
        self._buffer.clear()
        
        # Cria tasks
        async with self._semaphore:
            tasks = [
                asyncio.create_task(self._process_one(i, item))
                for i, item in enumerate(items)
            ]
            self._tasks.update(tasks)
            
            # Aguarda e coleta resultados
            for task in asyncio.as_completed(tasks):
                result = await task
                self._results.append(result)
                self._tasks.discard(task)
    
    async def _process_one(self, index: int, item: T) -> BatchResult[T, R]:
        """Processa um item."""
        import time
        
        start = time.perf_counter()
        
        try:
            if asyncio.iscoroutinefunction(self.process_fn):
                output = await self.process_fn(item)
            else:
                output = self.process_fn(item)
            
            duration = (time.perf_counter() - start) * 1000
            
            return BatchResult(
                index=index,
                input=item,
                output=output,
                duration_ms=duration
            )
            
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            
            return BatchResult(
                index=index,
                input=item,
                error=e,
                duration_ms=duration
            )
    
    async def close(self) -> list[BatchResult[T, R]]:
        """Finaliza e retorna todos os resultados."""
        self._closed = True
        
        # Processa restante do buffer
        await self._flush()
        
        # Aguarda tasks pendentes
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Retorna resultados ordenados
        results = list(self._results)
        results.sort(key=lambda r: r.index)
        return results
    
    async def results(self) -> AsyncIterator[BatchResult[T, R]]:
        """Yield resultados à medida que ficam prontos."""
        while not self._closed or self._results or self._tasks:
            if self._results:
                yield self._results.popleft()
            else:
                await asyncio.sleep(0.01)


# Funções utilitárias

async def batch_project(
    texts: list[str],
    projector: SemanticProjector,
    max_concurrency: int = 10,
    on_progress: Optional[Callable[[int, int], None]] = None
) -> list[tuple[str, Optional[Cogon]]]:
    """
    Função utilitária para projetar batch de textos.
    
    Args:
        texts: Lista de textos
        projector: Projetor semântico
        max_concurrency: Máximo de projeções paralelas
        on_progress: Callback de progresso
        
    Returns:
        Lista de (texto, cogon)
    """
    batcher = ProjectionBatcher(
        projector,
        BatchConfig(max_concurrency=max_concurrency)
    )
    return await batcher.project(texts, on_progress)


async def batch_blend(
    cogons: list[Cogon],
    target: Cogon,
    alpha: float = 0.5,
    max_concurrency: int = 10
) -> list[Cogon]:
    """
    Faz blend de uma lista de COGONs com um target.
    
    Útil para computar "similaridade" em batch.
    
    Args:
        cogons: Lista de COGONs
        target: COGON alvo
        alpha: Peso do blend
        max_concurrency: Paralelismo
        
    Returns:
        Lista de COGONs resultantes
    """
    from leet.operators import blend
    
    def do_blend(c: Cogon) -> Cogon:
        return blend(c, target, alpha)
    
    processor = BatchProcessor(do_blend, BatchConfig(max_concurrency=max_concurrency))
    results = await processor.process_to_list(cogons)
    
    return [r.output for r in results if r.success]


def chunk_list(items: list[T], chunk_size: int) -> list[list[T]]:
    """Divide lista em chunks de tamanho especificado."""
    return [
        items[i:i + chunk_size]
        for i in range(0, len(items), chunk_size)
    ]
