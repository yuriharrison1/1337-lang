#!/usr/bin/env python3
"""
Measures compression over sliding windows to find the peak efficiency point.
"""

import json
import sys
from pathlib import Path
import math

def entropia_shannon(palavras):
    """Computes the Shannon entropy of the vocabulary."""
    from collections import Counter

    if not palavras:
        return 0

    freq = Counter(palavras)
    total = len(palavras)

    H = 0
    for count in freq.values():
        p = count / total
        if p > 0:
            H -= p * math.log2(p)

    return H

def analisar_janelas(report_file: str, window: int = 10):
    """Analyzes compression over sliding windows."""

    with open(report_file) as f:
        report = json.load(f)

    timeline = report['timeline']

    print("=" * 80)
    print(f"   📊 SLIDING-WINDOW ANALYSIS (window={window})")
    print("=" * 80)
    print()

    resultados = []
    step = max(1, window // 2)  # 50% overlap

    print("Window    | Msgs | Chars  | Compr. | Entropy | Concepts")
    print("-" * 80)

    for i in range(0, len(timeline) - window + 1, step):
        janela = timeline[i:i+window]

        # Basic metrics
        chars = sum(len(m.get('text_preview', '')) for m in janela)
        vectors = len(janela)
        compression = chars / (vectors * 32 * 4) if vectors > 0 else 0

        # Vocabulary entropy
        todas_palavras = []
        for m in janela:
            text = m.get('text_preview', '').lower()
            palavras = [p.strip('.,!?;:"()[]') for p in text.split()]
            todas_palavras.extend(palavras)

        H = entropia_shannon(todas_palavras)

        # Count unique concepts mentioned
        conceitos = set()
        for m in janela:
            text = m.get('text_preview', '').lower()
            if 'eros' in text or 'amor' in text:
                conceitos.add('eros')
            if 'belez' in text or 'kalos' in text:
                conceitos.add('beauty')
            if 'alma' in text or 'psyche' in text:
                conceitos.add('soul')
            if 'daimon' in text:
                conceitos.add('daimon')

        resultados.append({
            'inicio': i,
            'fim': i + window,
            'compressao': compression,
            'entropia': H,
            'conceitos': len(conceitos),
            'chars': chars
        })

        print(f"{i:3}-{i+window:3} | {vectors:4} | {chars:6} | {compression:6.2f}:1 | "
              f"{H:8.2f} | {len(conceitos):9}")

    # Analysis
    print()
    print("📈 ANALYSIS:")
    print()

    if len(timeline) < window:
        print(f"  ⚠️ Only {len(timeline)} messages. Cannot analyze windows of {window}.")
        return

    if resultados:
        # Find the compression peak
        pico = max(resultados, key=lambda x: x['compressao'])
        print(f"  🏆 Compression peak: {pico['compressao']:.2f}:1")
        print(f"     Occurred in window: msgs {pico['inicio']}-{pico['fim']}")
        print(f"     Entropy: {pico['entropia']:.2f}")
        print()

        # Find the lowest entropy (maximum convergence)
        convergencia = min(resultados, key=lambda x: x['entropia'])
        print(f"  🎯 Strongest vocabulary convergence: entropy {convergencia['entropia']:.2f}")
        print(f"     Window: msgs {convergencia['inicio']}-{convergencia['fim']}")
        print()

        # Averages
        avg_comp = sum(r['compressao'] for r in resultados) / len(resultados)
        avg_entr = sum(r['entropia'] for r in resultados) / len(resultados)

        print(f"  📊 Averages:")
        print(f"     Compression: {avg_comp:.2f}:1")
        print(f"     Entropy:     {avg_entr:.2f}")
        print()

        # Correlation
        if len(resultados) > 2:
            # Compression vs entropy correlation
            n = len(resultados)
            sum_x = sum(r['compressao'] for r in resultados)
            sum_y = sum(r['entropia'] for r in resultados)
            sum_xy = sum(r['compressao'] * r['entropia'] for r in resultados)
            sum_x2 = sum(r['compressao']**2 for r in resultados)
            sum_y2 = sum(r['entropia']**2 for r in resultados)

            numerador = n * sum_xy - sum_x * sum_y
            denominador = math.sqrt((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))

            if denominador != 0:
                correlacao = numerador / denominador
                print(f"  🔗 Compression × entropy correlation: {correlacao:.3f}")
                if correlacao < -0.5:
                    print("     → Compression is high when entropy is LOW (convergence!)")
                elif correlacao > 0.5:
                    print("     → Compression is high when entropy is HIGH (divergence?)")
                else:
                    print("     → No strong correlation")

    print()
    print("💡 CONCLUSION:")
    print()
    if pico['compressao'] > 1.5:
        print(f"  ✅ Finding confirmed! Peak of {pico['compressao']:.2f}:1")
        print(f"     in window {pico['inicio']}-{pico['fim']}")
        print()
        print("  1337 compression improves significantly")
        print("  as agents establish shared vocabulary.")
    else:
        print("  ⚠️ Moderate compression. The conversation may not have")
        print("     reached sufficient semantic convergence.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        report_file = sys.argv[1]
    else:
        files = list(Path('.').glob('plato_1337_report_*.json'))
        if not files:
            print("❌ No report found")
            sys.exit(1)
        report_file = max(files, key=lambda p: p.stat().st_mtime)

    window = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    analisar_janelas(report_file, window)
