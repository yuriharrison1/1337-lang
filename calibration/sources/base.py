"""
Classe base para fontes de dados de treinamento.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional, Any
from datetime import datetime
import hashlib


@dataclass
class TextSample:
    """
    Uma amostra de texto para treinamento.
    
    Inclui o texto, metadados e opcionalmente as projeções
    semânticas já calculadas (sem/unc).
    """
    text: str
    source: str  # Identificador da fonte
    id: str = field(default="")
    metadata: dict = field(default_factory=dict)
    # Campos opcionais preenchidos após projeção
    sem: Optional[list[float]] = None
    unc: Optional[list[float]] = None
    # Timestamp de coleta
    collected_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.id:
            # Gera ID a partir do hash do texto
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
    """Configuração para uma fonte de dados."""
    # Número máximo de amostras a coletar
    max_samples: int = 1000
    # Filtro de idioma (ISO 639-1)
    language: str = "en"
    # Tamanho mínimo/máximo do texto (caracteres)
    min_length: int = 20
    max_length: int = 2000
    # Delay entre requisições (segundos)
    request_delay: float = 0.5
    # Timeout para requisições
    timeout: int = 30
    # Retry config
    max_retries: int = 3
    # API keys (se necessário)
    api_keys: dict = field(default_factory=dict)
    # Filtros adicionais específicos da fonte
    filters: dict = field(default_factory=dict)


class DataSource(ABC):
    """
    Interface base para fontes de dados de treinamento.
    
    Todas as fontes devem implementar este contrato.
    """
    
    def __init__(self, config: Optional[SourceConfig] = None):
        self.config = config or SourceConfig()
        self.name = self.__class__.__name__.replace("Source", "").lower()
    
    @abstractmethod
    def fetch(self) -> Iterator[TextSample]:
        """
        Busca amostras de texto da fonte.
        
        Yields:
            TextSample: Amostras de texto
        """
        pass
    
    def fetch_all(self) -> list[TextSample]:
        """Busca todas as amostras até max_samples."""
        samples = []
        for i, sample in enumerate(self.fetch()):
            if i >= self.config.max_samples:
                break
            samples.append(sample)
        return samples
    
    def filter_sample(self, sample: TextSample) -> bool:
        """
        Filtra uma amostra baseado nos critérios de configuração.
        
        Returns:
            True se a amostra passa no filtro
        """
        text = sample.text.strip()
        
        # Comprimento
        if len(text) < self.config.min_length:
            return False
        if len(text) > self.config.max_length:
            return False
        
        # Idioma (se disponível nos metadados)
        if "language" in sample.metadata:
            if sample.metadata["language"] != self.config.language:
                return False
        
        return True
    
    def deduplicate(self, samples: list[TextSample]) -> list[TextSample]:
        """Remove duplicatas baseado no ID."""
        seen = set()
        unique = []
        for s in samples:
            if s.id not in seen:
                seen.add(s.id)
                unique.append(s)
        return unique
    
    def get_stats(self) -> dict:
        """Retorna estatísticas da fonte."""
        return {
            "name": self.name,
            "config": {
                "max_samples": self.config.max_samples,
                "language": self.config.language,
                "min_length": self.config.min_length,
                "max_length": self.config.max_length,
            }
        }
