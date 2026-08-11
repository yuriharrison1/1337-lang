"""
Base class for training data sources.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional, Any
from datetime import datetime
import hashlib


@dataclass
class TextSample:
    """
    A text sample for training.

    Includes the text, metadata, and optionally the already-computed
    semantic projections (sem/unc).
    """
    text: str
    source: str  # Source identifier
    id: str = field(default="")
    metadata: dict = field(default_factory=dict)
    # Optional fields populated after projection
    sem: Optional[list[float]] = None
    unc: Optional[list[float]] = None
    # Collection timestamp
    collected_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.id:
            # Generate ID from the text hash
            self.id = hashlib.sha256(self.text.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "metadata": self.metadata,
            "sem": self.sem,
            "unc": self.unc,
            "collected_at": self.collected_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "TextSample":
        return cls(
            id=d.get("id", ""),
            text=d["text"],
            source=d.get("source", "unknown"),
            metadata=d.get("metadata", {}),
            sem=d.get("sem"),
            unc=d.get("unc"),
            collected_at=datetime.fromisoformat(d["collected_at"]) if "collected_at" in d else datetime.now(),
        )


@dataclass
class SourceConfig:
    """Configuration for a data source."""
    # Maximum number of samples to collect
    max_samples: int = 1000
    # Language filter (ISO 639-1)
    language: str = "en"
    # Minimum/maximum text length (characters)
    min_length: int = 20
    max_length: int = 2000
    # Delay between requests (seconds)
    request_delay: float = 0.5
    # Timeout for requests
    timeout: int = 30
    # Retry config
    max_retries: int = 3
    # API keys (if needed)
    api_keys: dict = field(default_factory=dict)
    # Additional source-specific filters
    filters: dict = field(default_factory=dict)


class DataSource(ABC):
    """
    Base interface for training data sources.

    All sources must implement this contract.
    """
    
    def __init__(self, config: Optional[SourceConfig] = None):
        self.config = config or SourceConfig()
        self.name = self.__class__.__name__.replace("Source", "").lower()
    
    @abstractmethod
    def fetch(self) -> Iterator[TextSample]:
        """
        Fetches text samples from the source.

        Yields:
            TextSample: Text samples
        """
        pass

    def fetch_all(self) -> list[TextSample]:
        """Fetches all samples up to max_samples."""
        samples = []
        for i, sample in enumerate(self.fetch()):
            if i >= self.config.max_samples:
                break
            samples.append(sample)
        return samples
    
    def filter_sample(self, sample: TextSample) -> bool:
        """
        Filters a sample based on the configuration criteria.

        Returns:
            True if the sample passes the filter
        """
        text = sample.text.strip()

        # Length
        if len(text) < self.config.min_length:
            return False
        if len(text) > self.config.max_length:
            return False

        # Language (if available in metadata)
        if "language" in sample.metadata:
            if sample.metadata["language"] != self.config.language:
                return False
        
        return True
    
    def deduplicate(self, samples: list[TextSample]) -> list[TextSample]:
        """Removes duplicates based on ID."""
        seen = set()
        unique = []
        for s in samples:
            if s.id not in seen:
                seen.add(s.id)
                unique.append(s)
        return unique
    
    def get_stats(self) -> dict:
        """Returns source statistics."""
        return {
            "name": self.name,
            "config": {
                "max_samples": self.config.max_samples,
                "language": self.config.language,
                "min_length": self.config.min_length,
                "max_length": self.config.max_length,
            }
        }
