"""
Step 1 (v2): Generate training data from multiple sources.

Este script melhora o generate_dataset.py original ao permitir
múltiplas fontes de dados: local, APIs, domínios especializados
e geração sintética.

Usage:
    # Fonte padrão (diversas fontes combinadas)
    python generate_dataset_v2.py --output data/dataset_augmented.jsonl
    
    # Apenas dados sintéticos
    python generate_dataset_v2.py --source synthetic --provider mock
    
    # Apenas dados técnicos
    python generate_dataset_v2.py --source domain_tech
    
    # Com APIs externas
    python generate_dataset_v2.py --include-apis --n 200
    
    # Ver estatísticas das fontes
    python generate_dataset_v2.py --analyze
"""

import argparse
import json
import sys
from pathlib import Path

# Adiciona o calibration ao path
sys.path.insert(0, str(Path(__file__).parent))

from sources import (
    SourceConfig, LocalFileSource, WikipediaSource, ArxivSource,
    SyntheticSource, TechDomainSource, MedicalDomainSource, LegalDomainSource,
    SourceAggregator, create_default_aggregator,
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate 1337 training dataset from multiple sources."
    )
    parser.add_argument("--output", default="data/dataset_augmented.jsonl",
                       help="Output file (default: data/dataset_augmented.jsonl)")
    parser.add_argument("--n", type=int, default=500,
                       help="Number of samples to generate (default: 500)")
    parser.add_argument("--source", default="auto",
                       choices=["auto", "local", "wikipedia", "arxiv", "synthetic",
                               "domain_tech", "domain_medical", "domain_legal"],
                       help="Data source to use (default: auto = combined)")
    parser.add_argument("--provider", default="mock",
                       choices=["mock", "openai", "anthropic"],
                       help="LLM provider for synthetic generation")
    parser.add_argument("--include-apis", action="store_true",
                       help="Include external API sources (requires internet)")
    parser.add_argument("--language", default="pt",
                       help="Language filter (default: pt)")
    parser.add_argument("--min-length", type=int, default=20,
                       help="Minimum text length")
    parser.add_argument("--max-length", type=int, default=2000,
                       help="Maximum text length")
    parser.add_argument("--analyze", action="store_true",
                       help="Only analyze sources, don't generate")
    parser.add_argument("--stats", action="store_true",
                       help="Show detailed statistics after generation")
    
    args = parser.parse_args()
    
    # Configuração base
    config = SourceConfig(
        max_samples=args.n,
        language=args.language,
        min_length=args.min_length,
        max_length=args.max_length,
    )
    
    print("=" * 60)
    print(" 1337 Dataset Generator v2")
    print("=" * 60)
    print(f"Source: {args.source}")
    print(f"Target samples: {args.n}")
    print(f"Language: {args.language}")
    print()
    
    # Cria a fonte apropriada
    if args.source == "auto":
        print("Creating default aggregator with multiple sources...")
        aggregator = create_default_aggregator(
            target_samples=args.n,
            include_apis=args.include_apis,
            include_synthetic=True,
            include_domains=True,
        )
        source = aggregator
        
    elif args.source == "local":
        local_path = input("Path to local file: ").strip()
        source = LocalFileSource(local_path, config=config)
        
    elif args.source == "wikipedia":
        source = WikipediaSource(config=config)
        
    elif args.source == "arxiv":
        category = input("arXiv category (default: cs.AI): ").strip() or "cs.AI"
        source = ArxivSource(category=category, config=config)
        
    elif args.source == "synthetic":
        source = SyntheticSource(
            provider=args.provider,
            diversity="high",
            language=args.language,
            config=config,
        )
        
    elif args.source == "domain_tech":
        source = TechDomainSource(config=config)
        
    elif args.source == "domain_medical":
        source = MedicalDomainSource(config=config)
        
    elif args.source == "domain_legal":
        source = LegalDomainSource(config=config)
    
    # Modo análise
    if args.analyze:
        print("\nSource Analysis:")
        print("-" * 40)
        
        if isinstance(source, SourceAggregator):
            stats = source.analyze_sources()
            print(f"Total samples: {stats['total_samples']}")
            print(f"Unique sources: {stats['unique_sources']}")
            print("\nSource distribution:")
            for src, count in stats['source_distribution'].items():
                print(f"  {src}: {count}")
            print("\nDomain distribution:")
            for domain, count in stats['domain_distribution'].items():
                print(f"  {domain}: {count}")
            print("\nLanguage distribution:")
            for lang, count in stats['language_distribution'].items():
                print(f"  {lang}: {count}")
        else:
            print(f"Source: {source.name}")
            print(f"Stats: {source.get_stats()}")
        
        return
    
    # Gera os dados
    print(f"\nFetching samples from {source.name}...")
    print("-" * 40)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Verifica se há dados existentes para resume
    existing_ids = set()
    if output_path.exists():
        print(f"Resuming: checking {output_path}...")
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    existing_ids.add(data.get('id', ''))
                except:
                    pass
        print(f"  {len(existing_ids)} existing samples found")
    
    count = 0
    skipped = 0
    errors = 0
    
    with open(output_path, 'a', encoding='utf-8') as f:
        for sample in source.fetch():
            # Pula duplicatas
            if sample.id in existing_ids:
                skipped += 1
                continue
            
            try:
                f.write(json.dumps(sample.to_dict(), ensure_ascii=False) + '\n')
                count += 1
                existing_ids.add(sample.id)
                
                if count % 50 == 0:
                    print(f"  Generated: {count} | Skipped: {skipped} | Errors: {errors}")
                    
            except Exception as e:
                errors += 1
                print(f"  Error: {e}")
                continue
    
    print(f"\n{'=' * 60}")
    print(f"Done!")
    print(f"  New samples: {count}")
    print(f"  Skipped (duplicates): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Output: {output_path}")
    print(f"{'=' * 60}")
    
    # Estatísticas
    if args.stats:
        print("\nDataset Statistics:")
        print("-" * 40)
        
        # Recarrega para análise
        all_samples = []
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    all_samples.append(json.loads(line))
                except:
                    pass
        
        from collections import Counter
        
        sources = Counter(s.get('source', 'unknown') for s in all_samples)
        categories = Counter(s.get('metadata', {}).get('category', 'unknown') for s in all_samples)
        
        print(f"Total samples in file: {len(all_samples)}")
        print("\nBy source:")
        for src, cnt in sources.most_common():
            print(f"  {src}: {cnt}")
        print("\nBy category:")
        for cat, cnt in categories.most_common(10):
            print(f"  {cat}: {cnt}")


if __name__ == "__main__":
    main()
