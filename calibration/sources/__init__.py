"""
Training Data Sources for 1337 Calibration.

This module provides several training data sources for
calibrating the W matrix, allowing expansion beyond the 100 seed_texts.

Supported sources:
- Local: CSV, JSONL, TXT files
- APIs: Wikipedia, arXiv, Gutendex (Project Gutenberg)
- Synthetic: LLM generation with structured prompts
- Domain: Specialized datasets by domain (tech, medical, legal)
"""

from .base import DataSource, TextSample, SourceConfig
from .local import LocalFileSource
from .apis import WikipediaSource, ArxivSource, GutendexSource
from .synthetic import SyntheticSource
from .domain import TechDomainSource, MedicalDomainSource, LegalDomainSource
from .aggregator import SourceAggregator, create_default_aggregator

__all__ = [
    # Base
    "DataSource",
    "TextSample", 
    "SourceConfig",
    # Local
    "LocalFileSource",
    # APIs
    "WikipediaSource",
    "ArxivSource",
    "GutendexSource",
    # Synthetic
    "SyntheticSource",
    # Domain
    "TechDomainSource",
    "MedicalDomainSource",
    "LegalDomainSource",
    # Aggregator
    "SourceAggregator",
]
