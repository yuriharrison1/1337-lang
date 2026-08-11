"""
Aggregator for combining multiple data sources.
"""

import json
from pathlib import Path
from typing import Iterator, Optional
from collections import Counter

from .base import DataSource, TextSample, SourceConfig
from .local import LocalFileSource
from .synthetic import SyntheticSource
from .domain import TechDomainSource, LegalDomainSource


class SourceAggregator(DataSource):
    """
    Aggregates multiple data sources into a single stream.

    Allows combining data from different sources (local, API, synthetic)
    with balancing and deduplication.

    Example:
        # Create individual sources
        local = LocalFileSource("data/extras.jsonl")
        wiki = WikipediaSource(config=SourceConfig(max_samples=50))
        synthetic = SyntheticSource(provider="mock")

        # Aggregate with weights
        aggregator = SourceAggregator([
            (local, 0.3),      # 30% local data
            (wiki, 0.4),       # 40% Wikipedia
            (synthetic, 0.3),  # 30% synthetic
        ])

        # Fetch all balanced data
        samples = aggregator.fetch_all()
    """
    
    def __init__(
        self,
        sources: list[tuple[DataSource, float]],
        config: Optional[SourceConfig] = None,
        deduplicate: bool = True,
        balance: bool = True,
    ):
        """
        Args:
            sources: List of (source, weight) where weight is the desired proportion
            config: Global configuration (max_samples determines the total)
            deduplicate: Whether to remove duplicates across sources
            balance: Whether to balance sources by their weights
        """
        super().__init__(config)
        self.sources = sources
        self._deduplicate = deduplicate
        self.balance = balance
        self.name = "aggregated"

        # Normalize weights
        total_weight = sum(w for _, w in sources)
        self.normalized_weights = [(s, w / total_weight) for s, w in sources]
    
    def fetch(self) -> Iterator[TextSample]:
        """Fetches data from all combined sources."""
        if self.balance:
            yield from self._fetch_balanced()
        else:
            yield from self._fetch_sequential()

    def _fetch_balanced(self) -> Iterator[TextSample]:
        """Fetches data balanced by weight."""
        # Calculate how many samples from each source
        allocations = []
        for source, weight in self.normalized_weights:
            n_samples = int(self.config.max_samples * weight)
            allocations.append((source, n_samples))

        # Adjust to ensure the sum equals max_samples
        total_allocated = sum(n for _, n in allocations)
        if total_allocated < self.config.max_samples:
            # Add the difference to the highest-weight source
            diff = self.config.max_samples - total_allocated
            allocations[0] = (allocations[0][0], allocations[0][1] + diff)

        # Collect from each source
        all_samples = []
        for source, n in allocations:
            try:
                samples = []
                for i, sample in enumerate(source.fetch()):
                    if i >= n:
                        break
                    samples.append(sample)
                all_samples.extend(samples)
            except Exception as e:
                print(f"Warning: source {source.name} failed: {e}")
                continue
        
        # Deduplicate if needed
        if self._deduplicate:
            all_samples = self.deduplicate(all_samples)

        # Yield in shuffled random order
        import random
        random.shuffle(all_samples)
        
        for sample in all_samples[:self.config.max_samples]:
            yield sample
    
    def _fetch_sequential(self) -> Iterator[TextSample]:
        """Fetches data sequentially from each source."""
        seen = set() if self._deduplicate else None
        count = 0
        
        for source, _ in self.sources:
            try:
                for sample in source.fetch():
                    if count >= self.config.max_samples:
                        return
                    
                    # Deduplication
                    if seen is not None:
                        if sample.id in seen:
                            continue
                        seen.add(sample.id)
                    
                    yield sample
                    count += 1
                    
            except Exception as e:
                print(f"Warning: source {source.name} failed: {e}")
                continue
    
    def get_stats(self) -> dict:
        """Returns aggregated statistics."""
        stats = super().get_stats()
        
        source_stats = []
        for source, weight in self.normalized_weights:
            s = source.get_stats()
            s["allocated_weight"] = weight
            source_stats.append(s)
        
        stats.update({
            "num_sources": len(self.sources),
            "deduplicate": self.deduplicate,
            "balance": self.balance,
            "sources": source_stats,
        })
        
        return stats
    
    def export_combined(self, path: str, format: str = "jsonl") -> None:
        """
        Exports all combined data to a file.

        Args:
            path: Output file path
            format: Format (jsonl, json, csv)
        """
        samples = self.fetch_all()
        
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "jsonl":
            with open(output_path, 'w', encoding='utf-8') as f:
                for sample in samples:
                    f.write(json.dumps(sample.to_dict(), ensure_ascii=False) + '\n')
                    
        elif format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump([s.to_dict() for s in samples], f, indent=2, ensure_ascii=False)
                
        elif format == "csv":
            import csv
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if samples:
                    writer = csv.DictWriter(f, fieldnames=samples[0].to_dict().keys())
                    writer.writeheader()
                    for sample in samples:
                        writer.writerow(sample.to_dict())
        
        print(f"Exported {len(samples)} samples to {output_path}")
    
    def analyze_sources(self) -> dict:
        """
        Analyzes the composition of sources.

        Returns statistics about domains, languages, categories, etc.
        """
        samples = self.fetch_all()
        
        domains = Counter()
        languages = Counter()
        categories = Counter()
        sources = Counter()
        
        for sample in samples:
            sources[sample.source] += 1
            
            if "domain" in sample.metadata:
                domains[sample.metadata["domain"]] += 1
            if "language" in sample.metadata:
                languages[sample.metadata["language"]] += 1
            if "category" in sample.metadata:
                categories[sample.metadata["category"]] += 1
        
        return {
            "total_samples": len(samples),
            "unique_sources": len(sources),
            "source_distribution": dict(sources),
            "domain_distribution": dict(domains),
            "language_distribution": dict(languages),
            "category_distribution": dict(categories),
        }


def create_default_aggregator(
    target_samples: int = 500,
    include_apis: bool = False,
    include_synthetic: bool = True,
    include_domains: bool = True,
) -> SourceAggregator:
    """
    Creates an aggregator with the recommended default configuration.

    This is the "sensible default" configuration for initial training.

    Args:
        target_samples: Total number of desired samples
        include_apis: Whether to include API sources (requires internet)
        include_synthetic: Whether to include synthetic data
        include_domains: Whether to include specialized domain data

    Returns:
        Configured SourceAggregator
    """
    sources = []

    # 1. Local data (if it exists)
    local_path = Path("calibration/data/local_texts.jsonl")
    if local_path.exists():
        sources.append((
            LocalFileSource(str(local_path)),
            0.2
        ))
    
    # 2. Synthetic data (controlled diversity)
    if include_synthetic:
        sources.append((
            SyntheticSource(provider="mock", diversity="high"),
            0.3
        ))
    
    # 3. Domain data
    if include_domains:
        sources.append((
            TechDomainSource(config=SourceConfig(max_samples=200)),
            0.25
        ))
        sources.append((
            LegalDomainSource(config=SourceConfig(max_samples=100)),
            0.15
        ))
    
    # 4. External APIs (optional)
    if include_apis:
        sources.append((
            WikipediaSource(config=SourceConfig(max_samples=100, language="pt")),
            0.1
        ))
    
    config = SourceConfig(
        max_samples=target_samples,
        min_length=20,
        max_length=2000,
    )
    
    return SourceAggregator(sources, config=config, deduplicate=True, balance=True)
