"""
Batch processing system for the 1337 SDK.

Allows efficient processing of multiple texts/COGONs with:
- Controlled parallelization
- Automatic chunking
- Progress reporting
- Partial error handling
"""

from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Callable, TypeVar, Generic, AsyncIterator, Optional, Any
from collections import deque

from leet.types import Cogon
from leet.bridge import SemanticProjector

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class BatchResult(Generic[T, R]):
    """Result of processing a single item."""
    index: int
    input: T
    output: Optional[R] = None
    error: Optional[Exception] = None
    duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        """Returns True if processing succeeded."""
        return self.error is None and self.output is not None


@dataclass
class BatchConfig:
    """Batch processing configuration."""
    batch_size: int = 100
    max_concurrency: int = 10
    continue_on_error: bool = True
    error_threshold: float = 0.5  # Aborts if more than 50% errors
    progress_interval: int = 10   # Reports progress every N items


class BatchProcessor(Generic[T, R]):
    """
    Generic batch processor.

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
            process_fn: Processing function
            config: Batch configuration
        """
        self.process_fn = process_fn
        self.config = config or BatchConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrency)
        self._processed = 0
        self._errors = 0

    async def _process_one(self, index: int, item: T) -> BatchResult[T, R]:
        """Processes a single item with concurrency control."""
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
        Processes a list of items.

        Args:
            items: List of items to process
            on_progress: Callback (processed, total) -> None

        Yields:
            BatchResult for each item
        """
        self._processed = 0
        self._errors = 0
        total = len(items)

        # Create tasks
        tasks = [
            asyncio.create_task(self._process_one(i, item))
            for i, item in enumerate(items)
        ]

        # Process as they complete
        completed = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1

            # Report progress
            if on_progress and completed % self.config.progress_interval == 0:
                on_progress(completed, total)

            # Check error threshold
            if self._errors / completed > self.config.error_threshold:
                if not self.config.continue_on_error:
                    # Cancel remaining tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    raise RuntimeError(
                        f"Error threshold exceeded: {self._errors}/{completed}"
                    )

            yield result

        # Final progress
        if on_progress:
            on_progress(completed, total)

    async def process_to_list(
        self,
        items: list[T],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> list[BatchResult[T, R]]:
        """
        Processes and returns a list of results.

        Args:
            items: List of items
            on_progress: Progress callback

        Returns:
            List of BatchResult (in the same order as items)
        """
        results = []
        async for result in self.process(items, on_progress):
            results.append(result)

        # Sort by index
        results.sort(key=lambda r: r.index)
        return results


class ProjectionBatcher:
    """
    Batcher specialized for text projections.

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
        Projects multiple texts.

        Args:
            texts: List of texts
            on_progress: Progress callback

        Returns:
            List of (text, cogon) - cogon may be None if it failed
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
        Projects with cache - uses cache for hits, projects misses.

        Args:
            texts: List of texts
            cache: Cache instance
            on_progress: Progress callback

        Returns:
            List of (text, cogon)
        """
        # Split hits and misses
        hits: dict[int, Cogon] = {}
        misses: list[tuple[int, str]] = []

        for i, text in enumerate(texts):
            cached = cache.get_projection(text)
            if cached:
                sem, unc = cached
                hits[i] = Cogon.new(sem=sem, unc=unc)
            else:
                misses.append((i, text))

        # Project misses
        if misses:
            indices, miss_texts = zip(*misses)

            projected = await self.project(list(miss_texts), on_progress)

            # Store in cache and merge with hits
            for idx, (text, cogon) in zip(indices, projected):
                if cogon:
                    cache.set_projection(text, cogon.sem, cogon.unc)
                    hits[idx] = cogon

        # Sort by original index
        return [
            (texts[i], hits.get(i))
            for i in range(len(texts))
        ]


class StreamingBatcher:
    """
    Batcher for continuous (streaming) processing.

    Processes items as they arrive, with buffering.

    Example:
        >>> batcher = StreamingBatcher(process_fn, max_buffer=100)
        >>>
        >>> # Produce items
        >>> for text in stream:
        ...     await batcher.put(text)
        >>>
        >>> # Finalize and process
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
        """Adds an item to the buffer."""
        if self._closed:
            raise RuntimeError("Batcher is closed")

        self._buffer.append(item)

        # Process if buffer is full
        if len(self._buffer) >= self.max_buffer:
            await self._flush()

    async def _flush(self) -> None:
        """Processes all items in the buffer."""
        if not self._buffer:
            return

        items = list(self._buffer)
        self._buffer.clear()

        # Create tasks
        async with self._semaphore:
            tasks = [
                asyncio.create_task(self._process_one(i, item))
                for i, item in enumerate(items)
            ]
            self._tasks.update(tasks)

            # Wait for and collect results
            for task in asyncio.as_completed(tasks):
                result = await task
                self._results.append(result)
                self._tasks.discard(task)

    async def _process_one(self, index: int, item: T) -> BatchResult[T, R]:
        """Processes a single item."""
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
        """Finalizes and returns all results."""
        self._closed = True

        # Process the remaining buffer
        await self._flush()

        # Wait for pending tasks
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Return sorted results
        results = list(self._results)
        results.sort(key=lambda r: r.index)
        return results

    async def results(self) -> AsyncIterator[BatchResult[T, R]]:
        """Yields results as they become ready."""
        while not self._closed or self._results or self._tasks:
            if self._results:
                yield self._results.popleft()
            else:
                await asyncio.sleep(0.01)


# Utility functions

async def batch_project(
    texts: list[str],
    projector: SemanticProjector,
    max_concurrency: int = 10,
    on_progress: Optional[Callable[[int, int], None]] = None
) -> list[tuple[str, Optional[Cogon]]]:
    """
    Utility function to project a batch of texts.

    Args:
        texts: List of texts
        projector: Semantic projector
        max_concurrency: Maximum parallel projections
        on_progress: Progress callback

    Returns:
        List of (text, cogon)
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
    Blends a list of COGONs with a target.

    Useful for computing "similarity" in batch.

    Args:
        cogons: List of COGONs
        target: Target COGON
        alpha: Blend weight
        max_concurrency: Parallelism

    Returns:
        List of resulting COGONs
    """
    from leet.operators import blend

    def do_blend(c: Cogon) -> Cogon:
        return blend(c, target, alpha)

    processor = BatchProcessor(do_blend, BatchConfig(max_concurrency=max_concurrency))
    results = await processor.process_to_list(cogons)

    return [r.output for r in results if r.success]


def chunk_list(items: list[T], chunk_size: int) -> list[list[T]]:
    """Splits a list into chunks of the specified size."""
    return [
        items[i:i + chunk_size]
        for i in range(0, len(items), chunk_size)
    ]
