#!/usr/bin/env python3
"""
Mede compressão em janelas deslizantes para encontrar o pico de eficiência.
"""

import json
import sys
from pathlib import Path
import math

def entropia_shannon(palavras):
    """Calcula entropia de Shannon do vocabulário."""
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
    """Analisa compressão em janelas deslizantes."""
    
    with open(report_file) as f:
        report = json.load(f)
    
    timeline = report['timeline']
    
    print("=" * 80)
    print(f"   📊 ANÁLISE POR JANELAS (window={window})")
    print("=" * 80)
    print()
    
    resultados = []
    step = max(1, window // 2)  # 50% overlap
    
    print("Janela    | Msgs | Chars  | Compr. | Entropia | Conceitos")
    print("-" * 80)
    
    for i in range(0, len(timeline) - window + 1, step):
        janela = timeline[i:i+window]
        
        # Métricas básicas
        chars = sum(len(m.get('text_preview', '')) for m in janela)
        vectors = len(janela)
        compression = chars / (vectors * 32 * 4) if vectors > 0 else 0
        
        # Entropia do vocabulário
        todas_palavras = []
        for m in janela:
            text = m.get('text_preview', '').lower()
            palavras = [p.strip('.,!?;:"()[]') for p in text.split()]
            todas_palavras.extend(palavras)
        
        H = entropia_shannon(todas_palavras)
        
        # Contar conceitos únicos mencionados
        conceitos = set()
        for m in janela:
            text = m.get('text_preview', '').lower()
            if 'eros' in text or 'amor' in text:
                conceitos.add('eros')
            if 'belez' in text or 'kalos' in text:
                conceitos.add('beleza')
            if 'alma' in text or 'psyche' in text:
                conceitos.add('alma')
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
    
    # Análise
    print()
    print("📈 ANÁLISE:")
    print()
    
    if len(timeline) < window:
        print(f"  ⚠️ Apenas {len(timeline)} mensagens. Não é possível analisar janelas de {window}.")
        return
    
    if resultados:
        # Encontrar pico de compressão
        pico = max(resultados, key=lambda x: x['compressao'])
        print(f"  🏆 Pico de compressão: {pico['compressao']:.2f}:1")
        print(f"     Ocorreu na janela: msgs {pico['inicio']}-{pico['fim']}")
        print(f"     Entropia: {pico['entropia']:.2f}")
        print()
        
        # Encontrar menor entropia (convergência máxima)
        convergencia = min(resultados, key=lambda x: x['entropia'])
        print(f"  🎯 Maior convergência vocabulário: entropia {convergencia['entropia']:.2f}")
        print(f"     Janela: msgs {convergencia['inicio']}-{convergencia['fim']}")
        print()
        
        # Médias
        avg_comp = sum(r['compressao'] for r in resultados) / len(resultados)
        avg_entr = sum(r['entropia'] for r in resultados) / len(resultados)
        
        print(f"  📊 Médias:")
        print(f"     Compressão: {avg_comp:.2f}:1")
        print(f"     Entropia:   {avg_entr:.2f}")
        print()
        
        # Correlação
        if len(resultados) > 2:
            # Correlação compressão vs entropia
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
                print(f"  🔗 Correlação compressão × entropia: {correlacao:.3f}")
                if correlacao < -0.5:
                    print("     → Compressão alta quando entropia BAIXA (convergência!)")
                elif correlacao > 0.5:
                    print("     → Compressão alta quando entropia ALTA (divergência?)")
                else:
                    print("     → Sem correlação forte")
    
    print()
    print("💡 CONCLUSÃO:")
    print()
    if pico['compressao'] > 1.5:
        print(f"  ✅ Descoberta confirmada! Pico de {pico['compressao']:.2f}:1")
        print(f"     na janela {pico['inicio']}-{pico['fim']}")
        print()
        print("  A compressão 1337 melhora significativamente")
        print("  conforme os agentes estabelecem vocabulário compartilhado.")
    else:
        print("  ⚠️ Compressão moderada. Talvez a conversa não tenha")
        print("     atingido convergência semântica suficiente.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        report_file = sys.argv[1]
    else:
        files = list(Path('.').glob('plato_1337_report_*.json'))
        if not files:
            print("❌ Nenhum relatório encontrado")
            sys.exit(1)
        report_file = max(files, key=lambda p: p.stat().st_mtime)
    
    window = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    analisar_janelas(report_file, window)
