#!/usr/bin/env python3
"""
1337 vs English Report Generator — Full Analysis with Charts

Usage:
    python generate_report.py comparison_reports/comparison_1775087559.json
    python generate_report.py comparison_reports/comparison_1775087559.json --html
"""

import json
import sys
import argparse
from datetime import datetime
from collections import defaultdict


def format_bytes(bytes_val):
    """Formats bytes as a human-readable string."""
    if bytes_val >= 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.2f} MB"
    elif bytes_val >= 1024:
        return f"{bytes_val / 1024:.2f} KB"
    return f"{bytes_val} B"


def format_currency(val):
    """Formats a monetary value."""
    if val >= 1.0:
        return f"${val:.2f}"
    elif val >= 0.01:
        return f"${val:.4f}"
    return f"${val:.6f}"


def sparkline(data, width=40, min_val=None, max_val=None):
    """Generates an ASCII sparkline."""
    if not data:
        return ""
    
    blocks = "▁▂▃▄▅▆▇█"
    min_v = min_val if min_val is not None else min(data)
    max_v = max_val if max_val is not None else max(data)
    
    if max_v == min_v:
        return "█" * width
    
    result = []
    for i in range(width):
        idx = int(i * len(data) / width)
        idx = min(idx, len(data) - 1)
        val = data[idx]
        norm = (val - min_v) / (max_v - min_v)
        block_idx = int(norm * (len(blocks) - 1))
        result.append(blocks[block_idx])
    
    return "".join(result)


def bar_chart(value, max_val, width=30, filled="█", empty="░"):
    """Generates a horizontal bar."""
    if max_val == 0:
        return empty * width
    filled_len = int((value / max_val) * width)
    filled_len = min(filled_len, width)
    return filled * filled_len + empty * (width - filled_len)


def generate_ascii_report(data):
    """Generates the report in ASCII/Unicode format."""

    m = data["metrics"]
    agents = data["per_agent"]
    conv_hist = data.get("convergence_history", [])
    topic = data.get("topic", "Unknown")
    rounds = data.get("rounds", 0)
    deepseek_used = data.get("deepseek_used", False)
    timestamp = data.get("timestamp", "")

    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("                    📊 1337 vs ENGLISH REPORT")
    lines.append("=" * 80)
    lines.append(f"""
    📅 Date:          {timestamp}
    🎯 Topic:         {topic}
    🔄 Rounds:        {rounds}
    🤖 Agents:        {len(agents)}
    🔌 DeepSeek:      {'✅ Yes (Real API)' if deepseek_used else '❌ Mock'}
""")

    # Executive Summary
    lines.append("─" * 80)
    lines.append("                         🎯 EXECUTIVE SUMMARY")
    lines.append("─" * 80)
    
    compression = m.get("compression", 1.0)
    savings_pct = (1 - 1/compression) * 100
    
    lines.append(f"""
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                                                                             │
    │   💰 COST SAVINGS                                                          │
    │      English cost:      {format_currency(m.get('cost_english_usd', 0)):>15}                                   │
    │      1337 cost:         {format_currency(m.get('cost_1337_usd', 0)):>15}    ( ZERO transport tokens )         │
    │      ─────────────────────────────────────                                  │
    │      SAVINGS:           {format_currency(m.get('cost_english_usd', 0)):>15}    (100% reduction)               │
    │                                                                             │
    │   📦 COMPRESSION EFFICIENCY                                                 │
    │      Compression factor:      {compression:.2f}x                                       │
    │      Size reduction:          {savings_pct:.1f}%                                     │
    │      English bytes:           {format_bytes(m.get('bytes_en', 0)):>15}                                   │
    │      1337 bytes:              {format_bytes(m.get('bytes_1337', 0)):>15}                                   │
    │                                                                             │
    │   ⚡ PERFORMANCE                                                            │
    │      Throughput:              {m.get('throughput_msgs_s', 0):.1f} msgs/s                                    │
    │      Total duration:          {m.get('duration_ms', 0)/1000:.1f} s                                        │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘
""")

    # Delta Compression
    lines.append("─" * 80)
    lines.append("                      🗜️  DELTA COMPRESSION ANALYSIS")
    lines.append("─" * 80)
    
    delta_ratio = m.get("delta_ratio", 0)
    cogon_msgs = m.get("cogon_msgs", 0)
    delta_msgs = m.get("delta_msgs", 0)
    total_msgs = cogon_msgs + delta_msgs
    avg_axes = m.get("avg_axes_changed", 0)
    bytes_saved = m.get("bytes_saved_delta", 0)
    
    lines.append(f"""
    Full COGON messages:          {cogon_msgs:>4}  ({bar_chart(cogon_msgs, total_msgs, 25)})
    SparseDelta messages:         {delta_msgs:>4}  ({bar_chart(delta_msgs, total_msgs, 25)})

    Delta coverage:               {delta_ratio*100:.1f}%
    Average axes changed:         {avg_axes:.1f} of 32

    📉 Delta savings:
       Bytes saved:                {format_bytes(bytes_saved)}
       Average COGON size:         ~166 B
       Average SparseDelta size:   ~{50 + int(avg_axes * 5)} B
       Reduction per delta:        ~{(1 - (50 + avg_axes * 5)/166)*100:.0f}%
""")

    # Semantic Convergence
    if conv_hist:
        lines.append("─" * 80)
        lines.append("                      📈 SEMANTIC CONVERGENCE")
        lines.append("─" * 80)

        initial = conv_hist[0] if conv_hist else 0
        final = conv_hist[-1] if conv_hist else 0
        min_conv = min(conv_hist) if conv_hist else 0
        max_conv = max(conv_hist) if conv_hist else 0

        change_pct = ((initial - final) / initial * 100) if initial > 0 else 0

        lines.append(f"""
    Average distance between agents (lower = more convergence):

    Initial:  {initial:.4f}  {sparkline([initial], 20, min_conv, max_conv)}
    Final:    {final:.4f}  {sparkline([final], 20, min_conv, max_conv)}

    Evolution: {sparkline(conv_hist, 50)}
              {'↑' if change_pct < 0 else '↓'} {abs(change_pct):.1f}% {'divergence' if change_pct < 0 else 'convergence'}

    Minimum:  {min_conv:.4f}  (strongest agreement)
    Maximum:  {max_conv:.4f}  (strongest divergence)
""")

    # Per-Agent Analysis
    lines.append("─" * 80)
    lines.append("                      👥 PER-AGENT ANALYSIS")
    lines.append("─" * 80)

    # Sort agents by compression
    sorted_agents = sorted(agents.items(), key=lambda x: x[1].get("compression", 0), reverse=True)

    lines.append(f"""
    {'Agent':<20} {'Msgs':>5} {'B(1337)':>10} {'B(EN)':>10} {'Ratio':>8} {'Tokens':>8} {'Cost':>10}
    {'─'*80}
""")

    for agent_id, stats in sorted_agents[:10]:  # Top 10
        name = agent_id[:18]
        msgs = stats.get("msgs", 0)
        b1337 = stats.get("bytes_1337", 0)
        ben = stats.get("bytes_en", 0)
        ratio = stats.get("compression", 1.0)
        tokens = stats.get("tokens_in", 0) + stats.get("tokens_out", 0)
        cost = stats.get("cost_usd", 0)

        lines.append(f"    {name:<20} {msgs:>5} {b1337:>10,} {ben:>10,} {ratio:>7.2f}x {tokens:>8} {format_currency(cost):>10}")

    # Insights
    lines.append("─" * 80)
    lines.append("                      💡 INSIGHTS AND RECOMMENDATIONS")
    lines.append("─" * 80)

    # Compute insights
    best_compression_agent = max(agents.items(), key=lambda x: x[1].get("compression", 0))
    worst_compression_agent = min(agents.items(), key=lambda x: x[1].get("compression", 0))
    most_expensive_agent = max(agents.items(), key=lambda x: x[1].get("cost_usd", 0))

    insights = []

    if compression > 5:
        insights.append(f"""
    ✅ EXCELLENT: {compression:.1f}x compression is exceptional!
       For every 5 bytes of English, only 1 byte of 1337 is transmitted.""")
    elif compression > 3:
        insights.append(f"""
    ✅ GOOD: {compression:.1f}x compression is above average.
       Recommended for production.""")
    else:
        insights.append(f"""
    ⚠️  FAIR: {compression:.1f}x compression could be improved.
       Consider adjusting the delta threshold.""")

    if delta_ratio > 0.6:
        insights.append(f"""
    ✅ Delta compression is well-optimized: {delta_ratio*100:.0f}% of messages use sparse delta.
       This drastically reduces network traffic.""")

    insights.append(f"""
    💰 SAVINGS: At a scale of 1M messages, 1337 would save
       approximately {format_currency(m.get('cost_english_usd', 0) * 1000000 / total_msgs)}
       compared to plain English.""")

    insights.append(f"""
    🏆 Best compression: {best_compression_agent[0]} ({best_compression_agent[1].get('compression', 0):.2f}x)
    📉 Worst compression: {worst_compression_agent[0]} ({worst_compression_agent[1].get('compression', 0):.2f}x)
    💸 Most expensive: {most_expensive_agent[0]} ({format_currency(most_expensive_agent[1].get('cost_usd', 0))})
""")

    lines.extend(insights)

    # Footer
    lines.append("=" * 80)
    lines.append("                    End of 1337 vs English Report")
    lines.append("=" * 80)

    return "\n".join(lines)


def generate_html_report(data):
    """Generates the report in HTML."""

    m = data["metrics"]
    agents = data["per_agent"]
    conv_hist = data.get("convergence_history", [])
    topic = data.get("topic", "Unknown")

    compression = m.get("compression", 1.0)
    savings_pct = (1 - 1/compression) * 100

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>1337 vs English Report - {topic}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .metric-box {{ background: #ecf0f1; padding: 20px; border-radius: 8px; margin: 10px 0; }}
        .highlight {{ background: #2ecc71; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; }}
        .warning {{ background: #e74c3c; color: white; padding: 3px 8px; border-radius: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #3498db; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .chart {{ background: #34495e; color: white; padding: 20px; border-radius: 8px; font-family: monospace; }}
        .big-number {{ font-size: 48px; font-weight: bold; color: #2ecc71; }}
        .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
        .card {{ background: white; border: 1px solid #ddd; padding: 20px; border-radius: 8px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 1337 vs English Report</h1>
        <p><strong>Topic:</strong> {topic} | <strong>Date:</strong> {data.get('timestamp', '')}</p>

        <div class="grid">
            <div class="card">
                <div class="big-number">{compression:.1f}x</div>
                <p>Compression</p>
            </div>
            <div class="card">
                <div class="big-number">{savings_pct:.0f}%</div>
                <p>Savings</p>
            </div>
            <div class="card">
                <div class="big-number">${m.get('cost_english_usd', 0):.4f}</div>
                <p>English Cost</p>
            </div>
        </div>

        <h2>📈 Semantic Convergence</h2>
        <div class="chart">
            Average distance between agents over the rounds:<br>
            {generate_convergence_svg(conv_hist) if conv_hist else 'No data'}
        </div>

        <h2>👥 Per-Agent Performance</h2>
        <table>
            <tr>
                <th>Agent</th>
                <th>Messages</th>
                <th>1337 Bytes</th>
                <th>English Bytes</th>
                <th>Compression</th>
                <th>Cost</th>
            </tr>
"""
    
    for agent_id, stats in sorted(agents.items(), key=lambda x: x[1].get("compression", 0), reverse=True):
        html += f"""
            <tr>
                <td>{agent_id}</td>
                <td>{stats.get('msgs', 0)}</td>
                <td>{stats.get('bytes_1337', 0):,}</td>
                <td>{stats.get('bytes_en', 0):,}</td>
                <td><span class="highlight">{stats.get('compression', 0):.2f}x</span></td>
                <td>${stats.get('cost_usd', 0):.6f}</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
</body>
</html>
"""
    
    return html


def generate_convergence_svg(data):
    """Generates a simple convergence SVG."""
    if not data:
        return ""
    
    width = 800
    height = 200
    padding = 40
    
    min_val = min(data)
    max_val = max(data)
    val_range = max_val - min_val if max_val != min_val else 1
    
    points = []
    for i, val in enumerate(data):
        x = padding + (i / (len(data) - 1)) * (width - 2 * padding)
        y = height - padding - ((val - min_val) / val_range) * (height - 2 * padding)
        points.append(f"{x},{y}")
    
    return f'<svg width="{width}" height="{height}"><polyline points="{" ".join(points)}" fill="none" stroke="#2ecc71" stroke-width="2"/></svg>'


def main():
    parser = argparse.ArgumentParser(description='1337 vs English Report Generator')
    parser.add_argument('json_file', help='Comparison JSON file')
    parser.add_argument('--html', action='store_true', help='Generate HTML instead of ASCII')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')

    args = parser.parse_args()

    # Read JSON
    with open(args.json_file, 'r') as f:
        data = json.load(f)

    # Generate report
    if args.html:
        report = generate_html_report(data)
    else:
        report = generate_ascii_report(data)

    # Output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
