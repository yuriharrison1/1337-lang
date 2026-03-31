"""
Fonte de dados para arquivos locais.
"""

import json
import csv
from pathlib import Path
from typing import Iterator

from .base import DataSource, TextSample, SourceConfig


class LocalFileSource(DataSource):
    """
    Fonte de dados para arquivos locais.
    
    Suporta formatos:
    - .txt: um texto por linha
    - .jsonl: JSON lines com campo 'text' ou estrutura similar
    - .csv: CSV com coluna 'text'
    - .json: Array de objetos ou objeto único
    
    Exemplo de uso:
        source = LocalFileSource("data/meus_textos.jsonl")
        samples = source.fetch_all()
    """
    
    def __init__(self, file_path: str, text_field: str = "text", config: SourceConfig = None):
        super().__init__(config)
        self.file_path = Path(file_path)
        self.text_field = text_field
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        self.name = f"local_{self.file_path.stem}"
    
    def fetch(self) -> Iterator[TextSample]:
        """Lê amostras do arquivo."""
        suffix = self.file_path.suffix.lower()
        
        if suffix == '.jsonl':
            yield from self._fetch_jsonl()
        elif suffix == '.json':
            yield from self._fetch_json()
        elif suffix == '.csv':
            yield from self._fetch_csv()
        elif suffix == '.txt':
            yield from self._fetch_txt()
        else:
            raise ValueError(f"Formato não suportado: {suffix}")
    
    def _fetch_jsonl(self) -> Iterator[TextSample]:
        """Lê arquivo JSON lines."""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    sample = self._parse_sample(data)
                    if sample and self.filter_sample(sample):
                        yield sample
                except json.JSONDecodeError:
                    continue
    
    def _fetch_json(self) -> Iterator[TextSample]:
        """Lê arquivo JSON (array ou objeto)."""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            for item in data:
                sample = self._parse_sample(item)
                if sample and self.filter_sample(sample):
                    yield sample
        else:
            sample = self._parse_sample(data)
            if sample and self.filter_sample(sample):
                yield sample
    
    def _fetch_csv(self) -> Iterator[TextSample]:
        """Lê arquivo CSV."""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get(self.text_field, '')
                if text:
                    sample = TextSample(
                        text=text,
                        source=self.name,
                        metadata={k: v for k, v in row.items() if k != self.text_field}
                    )
                    if self.filter_sample(sample):
                        yield sample
    
    def _fetch_txt(self) -> Iterator[TextSample]:
        """Lê arquivo texto (uma linha por amostra)."""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                text = line.strip()
                if text:
                    sample = TextSample(text=text, source=self.name)
                    if self.filter_sample(sample):
                        yield sample
    
    def _parse_sample(self, data: dict) -> TextSample | None:
        """Parseia um dicionário em TextSample."""
        # Tenta extrair texto
        text = None
        
        if self.text_field in data:
            text = data[self.text_field]
        elif 'text' in data:
            text = data['text']
        elif 'content' in data:
            text = data['content']
        elif 'body' in data:
            text = data['body']
        
        if not text or not isinstance(text, str):
            return None
        
        # Extrai metadados relevantes
        metadata = {k: v for k, v in data.items() 
                   if k not in [self.text_field, 'text', 'content', 'body', 'sem', 'unc']}
        
        # Se já tem sem/unc, inclui
        sem = data.get('sem')
        unc = data.get('unc')
        
        return TextSample(
            text=text,
            source=self.name,
            metadata=metadata,
            sem=sem,
            unc=unc,
        )
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do arquivo."""
        stats = super().get_stats()
        stats.update({
            "file_path": str(self.file_path),
            "file_size": self.file_path.stat().st_size,
            "file_type": self.file_path.suffix,
        })
        return stats
