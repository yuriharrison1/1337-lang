"""
Fontes de dados via APIs públicas.
"""

import time
import random
import urllib.request
import urllib.error
from typing import Iterator
import json

from .base import DataSource, TextSample, SourceConfig


class WikipediaSource(DataSource):
    """
    Fonte de dados da Wikipedia API.
    
    Busca artigos aleatórios ou por categoria.
    
    Exemplo:
        config = SourceConfig(max_samples=50, language="pt")
        source = WikipediaSource(category="Ciência", config=config)
        samples = source.fetch_all()
    """
    
    API_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
    RANDOM_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/random/summary"
    
    def __init__(self, category: str | None = None, config: SourceConfig = None):
        super().__init__(config)
        self.category = category
        self.name = f"wikipedia_{config.language if config else 'en'}"
    
    def fetch(self) -> Iterator[TextSample]:
        """Busca artigos da Wikipedia."""
        lang = self.config.language
        
        for _ in range(self.config.max_samples):
            try:
                # Busca página aleatória
                url = self.RANDOM_URL.format(lang=lang)
                
                req = urllib.request.Request(
                    url,
                    headers={
                        'User-Agent': '1337-calibration/0.1 (research project)',
                        'Accept': 'application/json',
                    }
                )
                
                with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                
                # Extrai texto
                title = data.get('title', '')
                extract = data.get('extract', '')
                
                if not extract or len(extract) < self.config.min_length:
                    continue
                
                # Páginas de disambiguation têm extratos muito curtos
                if "may refer to" in extract or "pode se referir" in extract:
                    continue
                
                sample = TextSample(
                    text=extract,
                    source=self.name,
                    metadata={
                        "title": title,
                        "page_id": data.get('pageid'),
                        "language": lang,
                        "category": self.category,
                    }
                )
                
                if self.filter_sample(sample):
                    yield sample
                
                # Delay para respeitar rate limits
                time.sleep(self.config.request_delay)
                
            except urllib.error.HTTPError as e:
                if e.code == 429:  # Too Many Requests
                    time.sleep(5)
                continue
            except Exception:
                continue


class ArxivSource(DataSource):
    """
    Fonte de dados do arXiv (papers científicos).
    
    Busca abstracts de papers por categoria.
    
    Exemplo:
        config = SourceConfig(max_samples=30)
        source = ArxivSource(category="cs.AI", config=config)
        samples = source.fetch_all()
    """
    
    API_URL = "http://export.arxiv.org/api/query"
    
    # Categorias populares
    CATEGORIES = {
        "cs.AI": "Artificial Intelligence",
        "cs.CL": "Computation and Language",
        "cs.LG": "Machine Learning",
        "cs.SE": "Software Engineering",
        "cs.DC": "Distributed Computing",
        "cs.DB": "Databases",
        "cs.NI": "Networking",
        "cs.OS": "Operating Systems",
        "cs.PL": "Programming Languages",
        "cs.RO": "Robotics",
        "cs.SY": "Systems and Control",
        "math.ST": "Statistics",
        "physics.data-an": "Data Analysis",
    }
    
    def __init__(self, category: str = "cs.AI", config: SourceConfig = None):
        super().__init__(config)
        self.category = category
        self.name = f"arxiv_{category.replace('.', '_')}"
    
    def fetch(self) -> Iterator[TextSample]:
        """Busca abstracts do arXiv."""
        import xml.etree.ElementTree as ET
        
        # arXiv retorna no máximo 2000 resultados por query
        # Usamos start para paginar
        batch_size = 100
        start = 0
        collected = 0
        
        while collected < self.config.max_samples:
            try:
                # Constrói query
                params = {
                    "search_query": f"cat:{self.category}",
                    "start": start,
                    "max_results": min(batch_size, self.config.max_samples - collected),
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                }
                
                query = "&".join(f"{k}={v}" for k, v in params.items())
                url = f"{self.API_URL}?{query}"
                
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': '1337-calibration/0.1'}
                )
                
                with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                    xml_data = resp.read().decode('utf-8')
                
                # Parse XML
                root = ET.fromstring(xml_data)
                
                # Namespace arXiv
                ns = {
                    'atom': 'http://www.w3.org/2005/Atom',
                    'arxiv': 'http://arxiv.org/schemas/atom'
                }
                
                entries = root.findall('atom:entry', ns)
                
                if not entries:
                    break
                
                for entry in entries:
                    title = entry.find('atom:title', ns)
                    summary = entry.find('atom:summary', ns)
                    
                    if title is None or summary is None:
                        continue
                    
                    text = f"{title.text.strip()}. {summary.text.strip()}"
                    
                    authors = [a.find('atom:name', ns).text 
                              for a in entry.findall('atom:author', ns)
                              if a.find('atom:name', ns) is not None]
                    
                    sample = TextSample(
                        text=text,
                        source=self.name,
                        metadata={
                            "title": title.text.strip(),
                            "authors": authors,
                            "category": self.category,
                            "published": entry.find('atom:published', ns).text if entry.find('atom:published', ns) is not None else None,
                        }
                    )
                    
                    if self.filter_sample(sample):
                        yield sample
                        collected += 1
                        
                        if collected >= self.config.max_samples:
                            break
                
                start += batch_size
                time.sleep(self.config.request_delay)
                
            except Exception:
                break


class GutendexSource(DataSource):
    """
    Fonte de dados do Gutendex (Project Gutenberg).
    
    Busca textos literários do domínio público.
    
    Exemplo:
        config = SourceConfig(max_samples=20, language="en")
        source = GutendexSource(topic="science", config=config)
        samples = source.fetch_all()
    """
    
    API_URL = "https://gutendex.com/books"
    
    def __init__(self, topic: str | None = None, config: SourceConfig = None):
        super().__init__(config)
        self.topic = topic
        self.name = "gutendex"
    
    def fetch(self) -> Iterator[TextSample]:
        """Busca livros do Project Gutenberg."""
        page = 1
        collected = 0
        
        while collected < self.config.max_samples:
            try:
                # Constrói URL
                params = {"page": page}
                if self.topic:
                    params["topic"] = self.topic
                if self.config.language:
                    params["languages"] = self.config.language
                
                query = "&".join(f"{k}={v}" for k, v in params.items())
                url = f"{self.API_URL}?{query}"
                
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': '1337-calibration/0.1'}
                )
                
                with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                
                books = data.get('results', [])
                
                if not books:
                    break
                
                for book in books:
                    # Pega o texto em texto plain se disponível
                    formats = book.get('formats', {})
                    text_url = formats.get('text/plain; charset=utf-8') or \
                              formats.get('text/plain')
                    
                    # Se não tem texto plain, usa descrição
                    if not text_url:
                        title = book.get('title', '')
                        authors = [a['name'] for a in book.get('authors', [])]
                        text = f"{title} by {', '.join(authors)}. {book.get('subjects', [''])[0]}"
                    else:
                        # Baixa o texto (limitado ao começo)
                        text = self._fetch_text_sample(text_url)
                    
                    if not text:
                        continue
                    
                    sample = TextSample(
                        text=text[:self.config.max_length],
                        source=self.name,
                        metadata={
                            "title": book.get('title'),
                            "authors": [a['name'] for a in book.get('authors', [])],
                            "subjects": book.get('subjects', []),
                            "language": book.get('languages', [None])[0],
                        }
                    )
                    
                    if self.filter_sample(sample):
                        yield sample
                        collected += 1
                        
                        if collected >= self.config.max_samples:
                            break
                
                page += 1
                time.sleep(self.config.request_delay)
                
            except Exception:
                break
    
    def _fetch_text_sample(self, url: str) -> str | None:
        """Busca uma amostra do texto do livro."""
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': '1337-calibration/0.1'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                # Lê apenas os primeiros 50KB
                data = resp.read(50000).decode('utf-8', errors='ignore')
            
            # Remove header do Project Gutenberg
            lines = data.split('\n')
            
            # Encontra o início real do conteúdo
            start_idx = 0
            for i, line in enumerate(lines):
                if '*** START OF' in line or '***START OF' in line:
                    start_idx = i + 1
                    break
            
            # Pega até 5000 caracteres de conteúdo
            content = '\n'.join(lines[start_idx:start_idx+100])
            return content.strip()[:5000]
            
        except Exception:
            return None
