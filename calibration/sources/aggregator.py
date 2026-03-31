"""
Aggregator para combinar múltiplas fontes de dados.
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
    Agrega múltiplas fontes de dados em um único stream.
    
    Permite combinar dados de diferentes fontes (local, API, synthetic)
    com balanceamento e deduplicação.
    
    Exemplo:
        # Cria fontes individuais
        local = LocalFileSource("data/extras.jsonl")
        wiki = WikipediaSource(config=SourceConfig(max_samples=50))
        synthetic = SyntheticSource(provider="mock")
        
        # Agrega com pesos
        aggregator = SourceAggregator([
            (local, 0.3),      # 30% de dados locais
            (wiki, 0.4),       # 40% da Wikipedia
            (synthetic, 0.3),  # 30% sintéticos
        ])
        
        # Busca todos os dados balanceados
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
            sources: Lista de (fonte, peso) onde peso é a proporção desejada
            config: Configuração global (max_samples determina o total)
            deduplicate: Se deve remover duplicatas entre fontes
            balance: Se deve balancear as fontes pelos pesos
        """
        super().__init__(config)
        self.sources = sources
        self._deduplicate = deduplicate
        self.balance = balance
        self.name = "aggregated"
        
        # Normaliza pesos
        total_weight = sum(w for _, w in sources)
        self.normalized_weights = [(s, w / total_weight) for s, w in sources]
    
    def fetch(self) -> Iterator[TextSample]:
        """Busca dados de todas as fontes combinadas."""
        if self.balance:
            yield from self._fetch_balanced()
        else:
            yield from self._fetch_sequential()
    
    def _fetch_balanced(self) -> Iterator[TextSample]:
        """Busca dados balanceados pelos pesos."""
        # Calcula quantas amostras de cada fonte
        allocations = []
        for source, weight in self.normalized_weights:
            n_samples = int(self.config.max_samples * weight)
            allocations.append((source, n_samples))
        
        # Ajusta para garantir que soma = max_samples
        total_allocated = sum(n for _, n in allocations)
        if total_allocated < self.config.max_samples:
            # Adiciona a diferença na fonte com maior peso
            diff = self.config.max_samples - total_allocated
            allocations[0] = (allocations[0][0], allocations[0][1] + diff)
        
        # Coleta de cada fonte
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
        
        # Deduplica se necessário
        if self._deduplicate:
            all_samples = self.deduplicate(all_samples)
        
        # Yield em ordem aleatória misturada
        import random
        random.shuffle(all_samples)
        
        for sample in all_samples[:self.config.max_samples]:
            yield sample
    
    def _fetch_sequential(self) -> Iterator[TextSample]:
        """Busca dados sequencialmente de cada fonte."""
        seen = set() if self._deduplicate else None
        count = 0
        
        for source, _ in self.sources:
            try:
                for sample in source.fetch():
                    if count >= self.config.max_samples:
                        return
                    
                    # Deduplicação
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
        """Retorna estatísticas agregadas."""
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
        Exporta todos os dados combinados para arquivo.
        
        Args:
            path: Caminho do arquivo de saída
            format: Formato (jsonl, json, csv)
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
        Analisa a composição das fontes.
        
        Retorna estatísticas sobre domínios, idiomas, categorias, etc.
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
    Cria um aggregator com configuração padrão recomendada.
    
    Esta é a configuração "sensata padrão" para treinamento inicial.
    
    Args:
        target_samples: Número total de amostras desejado
        include_apis: Se deve incluir fontes de API (requer internet)
        include_synthetic: Se deve incluir dados sintéticos
        include_domains: Se deve incluir dados de domínio especializado
    
    Returns:
        SourceAggregator configurado
    """
    sources = []
    
    # 1. Dados locais (se existirem)
    local_path = Path("calibration/data/local_texts.jsonl")
    if local_path.exists():
        sources.append((
            LocalFileSource(str(local_path)),
            0.2
        ))
    
    # 2. Dados sintéticos (diversidade controlada)
    if include_synthetic:
        sources.append((
            SyntheticSource(provider="mock", diversity="high"),
            0.3
        ))
    
    # 3. Dados de domínio
    if include_domains:
        sources.append((
            TechDomainSource(config=SourceConfig(max_samples=200)),
            0.25
        ))
        sources.append((
            LegalDomainSource(config=SourceConfig(max_samples=100)),
            0.15
        ))
    
    # 4. APIs externas (opcional)
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
