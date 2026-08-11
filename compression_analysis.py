#!/usr/bin/env python3
"""
1337 Compression Analysis - Evolution over the conversation
"""

import json
import sys
from pathlib import Path

def analyze_compression_evolution(report_file: str):
    """Analyzes how compression evolved over the conversation."""

    with open(report_file) as f:
        report = json.load(f)

    timeline = report['timeline']

    print("=" * 70)
    print("   📊 1337 COMPRESSION ANALYSIS - Temporal Evolution")
    print("=" * 70)
    print()

    # Compute cumulative compression at checkpoints
    checkpoints = [5, 10, 20, 30, 40, 50, 60, 70, 80]
    cumulative_chars = 0
    cumulative_vectors = 0

    print("Checkpoint | Msgs | Chars    | Vectors | Compression | Efficiency")
    print("-" * 70)

    for i, entry in enumerate(timeline):
        text = entry.get('text_preview', '')
        cumulative_chars += len(text) * 4  # estimated UTF-8
        cumulative_vectors += 1
        
        msg_num = i + 1
        
        if msg_num in checkpoints or msg_num == len(timeline):
            compression = cumulative_chars / (cumulative_vectors * 32 * 4)
            efficiency = cumulative_chars / max(cumulative_vectors, 1)
            
            print(f"{msg_num:8} | {msg_num:4} | {cumulative_chars:8} | "
                  f"{cumulative_vectors:7} | {compression:10.2f}:1 | "
                  f"{efficiency:8.0f}")
    
    print()
    print("📈 OBSERVATIONS:")
    print()

    # Pattern analysis
    total_msgs = len(timeline)
    total_chars = sum(len(e.get('text_preview', '')) for e in timeline) * 4

    print(f"  • Total messages: {total_msgs}")
    print(f"  • Total characters (est. UTF-8): {total_chars:,}")
    print(f"  • 1337 vectors created: {total_msgs}")
    print(f"  • Final compression: {report['summary']['compression_ratio']}:1")
    print()

    # Compare first 10 vs last 10
    if total_msgs >= 20:
        first_10_chars = sum(len(timeline[i].get('text_preview', '')) for i in range(10)) * 4
        last_10_chars = sum(len(timeline[-(i+1)].get('text_preview', '')) for i in range(10)) * 4

        first_compression = first_10_chars / (10 * 32 * 4)
        last_compression = last_10_chars / (10 * 32 * 4)

        print(f"  • Compression, first 10 msgs: {first_compression:.2f}:1")
        print(f"  • Compression, last 10 msgs:  {last_compression:.2f}:1")
        print(f"  • Improvement: {(last_compression/first_compression - 1)*100:.1f}%")
        print()

    # Concept reuse analysis
    print("🧬 CONCEPT REUSE:")
    for concept, data in report['concept_evolution'].items():
        refs = data['refinements']
        if refs > 5:
            efficiency = refs / total_msgs * 100
            print(f"  • {concept:20} referenced {refs:3}x ({efficiency:.1f}% of msgs)")

    print()
    print("💡 HYPOTHESIS:")
    print("  As the conversation progresses:")
    print("  1. Vocabulary converges (same words)")
    print("  2. Context is shared (less explanation)")
    print("  3. Concepts are referenced, not redefined")
    print("  4. 1337 vectors reuse semantic structure")
    print()
    print("  Result: FEWER bytes per concept over time")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        report_file = sys.argv[1]
    else:
        # Find the most recent file
        files = list(Path('.').glob('plato_1337_report_*.json'))
        if not files:
            print("❌ No report found")
            print("Usage: python compression_analysis.py <file.json>")
            sys.exit(1)
        report_file = max(files, key=lambda p: p.stat().st_mtime)

    analyze_compression_evolution(str(report_file))
