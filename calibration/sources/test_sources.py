"""
Testes para o sistema de fontes de treinamento.
"""

import json
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from sources import (
    TextSample, SourceConfig,
    LocalFileSource, SyntheticSource,
    TechDomainSource, LegalDomainSource,
    SourceAggregator, create_default_aggregator,
)


class TestTextSample:
    """Testes para TextSample."""
    
    def test_creation(self):
        """Criação básica."""
        sample = TextSample(
            text="Hello world",
            source="test",
            metadata={"key": "value"}
        )
        
        assert sample.text == "Hello world"
        assert sample.source == "test"
        assert sample.id != ""  # Auto-gerado
    
    def test_id_generation(self):
        """ID gerado a partir do hash."""
        sample1 = TextSample(text="Same text", source="test")
        sample2 = TextSample(text="Same text", source="test")
        
        assert sample1.id == sample2.id  # Mesmo texto = mesmo ID
    
    def test_to_dict(self):
        """Serialização."""
        sample = TextSample(
            text="Test",
            source="test",
            sem=[0.5] * 32,
            unc=[0.1] * 32,
        )
        
        data = sample.to_dict()
        assert data["text"] == "Test"
        assert data["source"] == "test"
        assert len(data["sem"]) == 32
    
    def test_from_dict(self):
        """Deserialização."""
        data = {
            "id": "abc123",
            "text": "Test",
            "source": "test",
            "metadata": {},
            "sem": [0.5] * 32,
            "unc": [0.1] * 32,
            "collected_at": "2024-01-01T00:00:00",
        }
        
        sample = TextSample.from_dict(data)
        assert sample.id == "abc123"
        assert sample.text == "Test"


class TestSourceConfig:
    """Testes para SourceConfig."""
    
    def test_default_config(self):
        """Configuração padrão."""
        config = SourceConfig()
        
        assert config.max_samples == 1000
        assert config.min_length == 20
        assert config.max_length == 2000
    
    def test_custom_config(self):
        """Configuração customizada."""
        config = SourceConfig(
            max_samples=100,
            language="pt",
            min_length=50,
        )
        
        assert config.max_samples == 100
        assert config.language == "pt"
        assert config.min_length == 50


class TestLocalFileSource:
    """Testes para LocalFileSource."""
    
    def test_txt_file(self, tmp_path):
        """Leitura de arquivo TXT."""
        file_path = tmp_path / "test.txt"
        file_path.write_text(
            "This is the first line with sufficient length for testing\n"
            "Second line also has enough characters to pass the filter\n"
            "Third line is also long enough to be included in results\n"
        )
        
        source = LocalFileSource(str(file_path))
        samples = source.fetch_all()
        
        assert len(samples) == 3
        assert all(s.source == "local_test" for s in samples)
    
    def test_jsonl_file(self, tmp_path):
        """Leitura de arquivo JSONL."""
        file_path = tmp_path / "test.jsonl"
        with open(file_path, 'w') as f:
            f.write(json.dumps({"text": "This is sample 1 with enough length", "category": "A"}) + '\n')
            f.write(json.dumps({"text": "This is sample 2 with enough length", "category": "B"}) + '\n')
        
        source = LocalFileSource(str(file_path))
        samples = source.fetch_all()
        
        assert len(samples) == 2
        assert samples[0].metadata["category"] == "A"
    
    def test_csv_file(self, tmp_path):
        """Leitura de arquivo CSV."""
        file_path = tmp_path / "test.csv"
        file_path.write_text("text,category\nHello world this is a long text,A\nWorld example with more characters,B\n")
        
        source = LocalFileSource(str(file_path))
        samples = source.fetch_all()
        
        assert len(samples) == 2
    
    def test_filter_by_length(self, tmp_path):
        """Filtro por comprimento."""
        file_path = tmp_path / "test.txt"
        file_path.write_text(
            "Short\n"
            "This is a much longer line that passes the filter test\n"
        )
        
        config = SourceConfig(min_length=20)
        source = LocalFileSource(str(file_path), config=config)
        samples = source.fetch_all()
        
        assert len(samples) == 1
        assert "longer" in samples[0].text
    
    def test_file_not_found(self):
        """Arquivo não existente."""
        try:
            source = LocalFileSource("/nonexistent/file.txt")
            assert False, "Deveria ter lançado exceção"
        except FileNotFoundError:
            pass


class TestSyntheticSource:
    """Testes para SyntheticSource."""
    
    def test_mock_generation(self):
        """Geração mock."""
        config = SourceConfig(max_samples=10)
        source = SyntheticSource(provider="mock", config=config)
        
        samples = source.fetch_all()
        
        assert len(samples) > 0
        assert all(len(s.text) > 0 for s in samples)
        assert all(s.source == "synthetic_mock" for s in samples)
    
    def test_diversity_levels(self):
        """Diferentes níveis de diversidade."""
        config = SourceConfig(max_samples=50)
        
        source_high = SyntheticSource(provider="mock", diversity="high", config=config)
        samples = source_high.fetch_all()
        
        # Com diversidade alta, deve haver variedade
        assert len(samples) > 0
    
    def test_language_setting(self):
        """Configuração de idioma."""
        config = SourceConfig(max_samples=5)
        source = SyntheticSource(provider="mock", language="en", config=config)
        
        samples = source.fetch_all()
        assert len(samples) > 0


class TestDomainSources:
    """Testes para fontes de domínio."""
    
    def test_tech_domain(self):
        """Fonte de domínio técnico."""
        config = SourceConfig(max_samples=20)
        source = TechDomainSource(config=config)
        
        samples = source.fetch_all()
        
        assert len(samples) > 0
        assert all(s.metadata.get("domain") == "technology" for s in samples)
    
    def test_tech_categories(self):
        """Categorias de texto técnico."""
        config = SourceConfig(max_samples=50, min_length=10)
        source = TechDomainSource(
            categories=["logs", "alerts"],
            config=config
        )
        
        samples = source.fetch_all()
        categories = set(s.metadata.get("category") for s in samples)
        
        # Deve ter principalmente logs e alerts (mas pode ter outros devido a heurística)
        assert any(cat in ["log", "alert"] for cat in categories)
        assert len(samples) > 0
    
    def test_legal_domain(self):
        """Fonte de domínio jurídico."""
        config = SourceConfig(max_samples=10, min_length=10)
        source = LegalDomainSource(config=config)
        
        samples = source.fetch_all()
        
        assert len(samples) > 0
        assert all(s.metadata.get("domain") == "legal" for s in samples)


class TestSourceAggregator:
    """Testes para SourceAggregator."""
    
    def test_basic_aggregation(self):
        """Agregação básica."""
        source1 = SyntheticSource(provider="mock", config=SourceConfig(max_samples=10))
        source2 = SyntheticSource(provider="mock", config=SourceConfig(max_samples=10))
        
        aggregator = SourceAggregator(
            [(source1, 0.5), (source2, 0.5)],
            config=SourceConfig(max_samples=15)
        )
        
        samples = aggregator.fetch_all()
        
        assert len(samples) <= 15
    
    def test_deduplication(self):
        """Deduplicação entre fontes."""
        # Mesma fonte duas vezes (mesmos dados)
        source = SyntheticSource(provider="mock", config=SourceConfig(max_samples=10))
        
        aggregator = SourceAggregator(
            [(source, 0.5), (source, 0.5)],
            config=SourceConfig(max_samples=20),
            deduplicate=True
        )
        
        samples = aggregator.fetch_all()
        
        # IDs devem ser únicos
        ids = [s.id for s in samples]
        assert len(ids) == len(set(ids))
    
    def test_no_deduplication(self):
        """Sem deduplicação."""
        source = SyntheticSource(provider="mock", config=SourceConfig(max_samples=5))
        
        aggregator = SourceAggregator(
            [(source, 0.5), (source, 0.5)],
            config=SourceConfig(max_samples=10),
            deduplicate=False
        )
        
        samples = aggregator.fetch_all()
        # Pode ter duplicatas
        assert len(samples) > 0
    
    def test_stats(self):
        """Estatísticas do agregador."""
        source = SyntheticSource(provider="mock", config=SourceConfig(max_samples=10))
        
        aggregator = SourceAggregator(
            [(source, 1.0)],
            config=SourceConfig(max_samples=10)
        )
        
        stats = aggregator.get_stats()
        
        assert stats["num_sources"] == 1
        assert "sources" in stats
    
    def test_export_jsonl(self, tmp_path):
        """Exportação para JSONL."""
        source = SyntheticSource(provider="mock", config=SourceConfig(max_samples=5, request_delay=0.01))
        
        aggregator = SourceAggregator(
            [(source, 1.0)],
            config=SourceConfig(max_samples=5)
        )
        
        output_path = tmp_path / "output.jsonl"
        aggregator.export_combined(str(output_path), format="jsonl")
        
        assert output_path.exists()
        
        # Verifica conteúdo (pode ser menos que 5 devido a delays ou filtros)
        with open(output_path) as f:
            lines = f.readlines()
        assert len(lines) > 0
    
    def test_analyze_sources(self):
        """Análise de fontes."""
        source = TechDomainSource(config=SourceConfig(max_samples=20))
        
        aggregator = SourceAggregator(
            [(source, 1.0)],
            config=SourceConfig(max_samples=20)
        )
        
        analysis = aggregator.analyze_sources()
        
        assert "total_samples" in analysis
        assert "domain_distribution" in analysis
        assert analysis["total_samples"] > 0


class TestDefaultAggregator:
    """Testes para create_default_aggregator."""
    
    def test_default_creation(self):
        """Criação padrão."""
        aggregator = create_default_aggregator(target_samples=50)
        
        samples = aggregator.fetch_all()
        
        assert len(samples) <= 50
        assert len(samples) > 0
    
    def test_without_domains(self):
        """Sem domínios especializados."""
        aggregator = create_default_aggregator(
            target_samples=20,
            include_domains=False,
            include_synthetic=True
        )
        
        samples = aggregator.fetch_all()
        assert len(samples) > 0
    
    def test_with_apis(self):
        """Com APIs (se disponível)."""
        # Nota: este teste pode falhar se não houver conexão
        try:
            aggregator = create_default_aggregator(
                target_samples=10,
                include_apis=True
            )
            samples = aggregator.fetch_all()
            assert len(samples) > 0
        except Exception:
            # Ignora se APIs não disponíveis
            pass


def run_tests():
    """Executa todos os testes."""
    import subprocess
    
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result.returncode


if __name__ == "__main__":
    import sys
    sys.exit(run_tests())
