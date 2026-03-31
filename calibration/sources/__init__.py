"""
Training Data Sources for 1337 Calibration.

Este módulo fornece diversas fontes de dados de treinamento para
calibração da matriz W, permitindo expandir além dos 100 seed_texts.

Fontes suportadas:
- Local: arquivos CSV, JSONL, TXT
- APIs: Wikipedia, arXiv, Gutendex (Project Gutenberg)
- Synthetic: Geração via LLM com prompts estruturados
- Domain: Datasets especializados por domínio (tech, medical, legal)
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
