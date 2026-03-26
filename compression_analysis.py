#!/usr/bin/env python3
"""
Análise de Compressão 1337 - Evolução ao longo da conversa
"""

import json
import sys
from pathlib import Path

def analyze_compression_evolution(report_file: str):
    """Analisa como compressão evoluiu na conversa."""
    
    with open(report_file) as f:
        report = json.load(f)
    
    timeline = report['timeline']
    
    print("=" * 70)
    print("   📊 ANÁLISE DE COMPRESSÃO 1337 - Evolução Temporal")
    print("=" * 70)
    print()
    
    # Calcular compressão acumulada em checkpoints
    checkpoints = [5, 10, 20, 30, 40, 50, 60, 70, 80]
    cumulative_chars = 0
    cumulative_vectors = 0
    
    print("Checkpoint | Msgs | Chars    | Vectors | Compressão | Eficiência")
    print("-" * 70)
    
    for i, entry in enumerate(timeline):
        text = entry.get('text_preview', '')
        cumulative_chars += len(text) * 4  # UTF-8 estimado
        cumulative_vectors += 1
        
        msg_num = i + 1
        
        if msg_num in checkpoints or msg_num == len(timeline):
            compression = cumulative_chars / (cumulative_vectors * 32 * 4)
            efficiency = cumulative_chars / max(cumulative_vectors, 1)
            
            print(f"{msg_num:8} | {msg_num:4} | {cumulative_chars:8} | "
                  f"{cumulative_vectors:7} | {compression:10.2f}:1 | "
                  f"{efficiency:8.0f}")
    
    print()
    print("📈 OBSERVAÇÕES:")
    print()
    
    # Análise de padrões
    total_msgs = len(timeline)
    total_chars = sum(len(e.get('text_preview', '')) for e in timeline) * 4
    
    print(f"  • Total de mensagens: {total_msgs}")
    print(f"  • Total de caracteres (est. UTF-8): {total_chars:,}")
    print(f"  • Vetores 1337 criados: {total_msgs}")
    print(f"  • Compressão final: {report['summary']['compression_ratio']}:1")
    print()
    
    # Comparar primeiros 10 vs últimos 10
    if total_msgs >= 20:
        first_10_chars = sum(len(timeline[i].get('text_preview', '')) for i in range(10)) * 4
        last_10_chars = sum(len(timeline[-(i+1)].get('text_preview', '')) for i in range(10)) * 4
        
        first_compression = first_10_chars / (10 * 32 * 4)
        last_compression = last_10_chars / (10 * 32 * 4)
        
        print(f"  • Compressão primeiras 10 msgs: {first_compression:.2f}:1")
        print(f"  • Compressão últimas 10 msgs:   {last_compression:.2f}:1")
        print(f"  • Melhoria: {(last_compression/first_compression - 1)*100:.1f}%")
        print()
    
    # Análise de reutilização de conceitos
    print("🧬 REUTILIZAÇÃO DE CONCEITOS:")
    for concept, data in report['concept_evolution'].items():
        refs = data['refinements']
        if refs > 5:
            efficiency = refs / total_msgs * 100
            print(f"  • {concept:20} referenciado {refs:3}x ({efficiency:.1f}% das msgs)")
    
    print()
    print("💡 HIPÓTESE:")
    print("  Conforme a conversa progride:")
    print("  1. Vocabulário converge (mesmas palavras)")
    print("  2. Contexto é compartilhado (menos explicação)")
    print("  3. Conceitos são referenciados, não redefinidos")
    print("  4. Vetores 1337 reutilizam estrutura semântica")
    print()
    print("  Resultado: MENOS bytes por conceito ao longo do tempo")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        report_file = sys.argv[1]
    else:
        # Procurar arquivo mais recente
        files = list(Path('.').glob('plato_1337_report_*.json'))
        if not files:
            print("❌ Nenhum relatório encontrado")
            print("Usage: python compression_analysis.py <arquivo.json>")
            sys.exit(1)
        report_file = max(files, key=lambda p: p.stat().st_mtime)
    
    analyze_compression_evolution(str(report_file))
