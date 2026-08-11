#!/usr/bin/env python3
"""
Simulação Dual: Platão × Pinoquio COM Compressão Delta
Economia máxima de banda entre agentes.
"""

import os
import sys
sys.path.insert(0, '.')

from dual_book_simulation import DUAL_SCENARIO, DualBookMonitor
from delta_compression import DeltaCompressor, SmartDeltaNetwork
from net1337 import (
    Network1337, RustBridge, create_backend,
    Cogon, FIXED_DIMS, py_dist
)
import time
import json
from datetime import datetime


def run_dual_with_delta(backend_name: str = "deepseek", rounds: int = 2):
    """Executa simulação dual com compressão delta."""
    
    print("=" * 80)
    print("   📚🎭 DUAL-BOOKS + DELTA COMPRESSION")
    print("   Platão × Pinoquio with 1337 Optimization")
    print("=" * 80)
    print()
    print(f"Backend: {backend_name}")
    print(f"Agents: {len(DUAL_SCENARIO['agents'])}")
    print(f"Books: Platão + Pinoquio")
    print()

    # Configurar compressores
    compressor = DeltaCompressor(threshold=0.25, max_delta_chain=4)

    print("⚙️  Delta Configuration:")
    print(f"   - Threshold: {compressor.threshold} (max distance for DELTA)")
    print(f"   - Max chain: {compressor.max_delta_chain} (deltas before FULL)")
    print()
    
    # Setup rede
    backend = create_backend(backend_name)
    rust = RustBridge()
    net = Network1337(rust, backend)
    smart_net = SmartDeltaNetwork(net, compressor)
    book_monitor = DualBookMonitor()
    
    # Adicionar agentes
    agent_map = {}
    for agent_def in DUAL_SCENARIO['agents']:
        agent = net.add_agent(agent_def['name'], agent_def['persona'])
        agent_map[agent_def['name']] = agent
        books = ", ".join(agent_def['books'])
        print(f"✅ {agent_def['name']:15} ({books})")
    
    print(f"\n🦀 Rust: {'active (' + rust.mode + ')' if rust.available() else 'unavailable'}")
    
    # Handshake
    print("\n📡 Handshake C5...")
    net.handshake()
    
    total_messages = 0
    total_saved = 0
    
    # Discussões
    for disc_idx, disc in enumerate(DUAL_SCENARIO['discussions']):
        print("\n" + "═" * 80)
        print(f"   📖 TOPIC {disc_idx + 1}/{len(DUAL_SCENARIO['discussions'])}")
        print(f"   {disc['topic']}")
        print("═" * 80)

        print(f"\n💬 Stimulus: \"{disc['stimulus'][:100]}...\"")
        
        # Determinar agentes participantes
        participating = [
            a for a in DUAL_SCENARIO['agents']
            if disc['book'] in a['books'] or disc['book'] == 'both'
        ]
        
        print(f"   Participants: {', '.join(a['name'] for a in participating)}")
        
        # Mensagem inicial (FULL forçado - sem referência)
        msg = net.human.text_to_msg(disc['stimulus'], "BROADCAST")
        net._log_msg(msg, "Moderador", "BROADCAST")
        
        # Respostas iniciais com compressão delta
        print("\n   🎤 Initial responses:")
        for agent_def in participating:
            agent = agent_map.get(agent_def['name'])
            if not agent:
                continue
            
            # Gerar resposta
            responses = agent.receive_and_respond(msg, net.all_participants)
            
            for resp in responses:
                text = resp.surface.get('_text', '')
                cogon = resp.payload
                
                # COMPRIMIR COM DELTA
                compressed = smart_net.send_message(agent.name, cogon, text)
                
                # Estatísticas
                total_messages += 1
                if compressed['type'] == 'DELTA':
                    total_saved += compressed['savings_bytes']
                
                # Mostrar ícone
                icon = "🟢 Δ" if compressed['type'] == 'DELTA' else "🔵 ◆"
                saved = compressed['savings_bytes']
                print(f"      {icon} {agent.name:12} | {compressed['type']:5} | saved {saved:4}b")
                print(f"         \"{text[:60]}{'...' if len(text) > 60 else ''}\"")
                
                # Registrar no monitor de livros
                book = disc['book'] if disc['book'] != 'both' else agent_def['books'][0]
                tokens = len(text) // 4
                book_monitor.record_message(agent.name, book, text, cogon, tokens)
                
                net._log_msg(resp, agent.name, net._resolve_name(resp.receiver))
        
        # Rounds de diálogo
        for round_num in range(rounds):
            print(f"\n   🔄 Round {round_num + 1}/{rounds}")
            
            for agent_def in participating:
                agent = agent_map.get(agent_def['name'])
                if not agent or not agent.msg_log:
                    continue
                
                # Responder a outro agente
                others = [a for a in participating if a['name'] != agent_def['name']]
                if not others:
                    continue
                
                other = agent_map.get(others[round_num % len(others)]['name'])
                if not other or not other.msg_log:
                    continue
                
                last_msg = other.msg_log[-1]
                responses = agent.receive_and_respond(last_msg, net.all_participants)
                
                for resp in responses:
                    text = resp.surface.get('_text', '')
                    cogon = resp.payload
                    
                    # COMPRIMIR COM DELTA
                    compressed = smart_net.send_message(agent.name, cogon, text)
                    
                    total_messages += 1
                    if compressed['type'] == 'DELTA':
                        total_saved += compressed['savings_bytes']
                    
                    icon = "🟢 Δ" if compressed['type'] == 'DELTA' else "🔵 ◆"
                    saved = compressed['savings_bytes']
                    dist = compressed['distance']
                    
                    print(f"      {icon} {agent.name:12} | dist={dist:.3f} | saved {saved:4}b")
                    
                    # Registrar
                    book = disc['book'] if disc['book'] != 'both' else agent_def['books'][0]
                    tokens = len(text) // 4
                    book_monitor.record_message(agent.name, book, text, cogon, tokens)
                    
                    net._log_msg(resp, agent.name, net._resolve_name(resp.receiver))
    
    # Relatório final
    print("\n" + "=" * 80)
    print("   📊 FINAL REPORT - DUAL + DELTA")
    print("=" * 80)

    # Métricas de compressão
    print("\n📦 DELTA COMPRESSION:")
    report = compressor.get_report()
    savings = report['savings']

    print(f"   Total messages:      {report['summary']['total_messages']}")
    print(f"   DELTA:               {report['summary']['delta_messages']} ({report['summary']['delta_percentage']}%)")
    print(f"   FULL:                {report['summary']['full_messages']}")
    print(f"   Bandwidth savings:   {savings['percent_saved']}%")
    print(f"   Bytes saved:         {savings['bytes_saved']:,}")
    print(f"   Compression rate:    {savings['efficiency']}:1")

    # Métricas de livros
    print("\n📚 PARTICIPATION BY BOOK:")
    distance = book_monitor.calculate_cross_book_distance()
    comparison = book_monitor.metrics.generate_comparison()

    print(f"   Platão:    {comparison['participation']['plato']['messages']:3} msgs ({comparison['participation']['plato']['percentage']:.1f}%)")
    print(f"   Pinoquio:  {comparison['participation']['pinocchio']['messages']:3} msgs ({comparison['participation']['pinocchio']['percentage']:.1f}%)")
    print(f"   Semantic distance between universes: {distance:.4f}")

    # Eixos que mais mudaram
    print("\n📈 MOST MODIFIED AXES (DELTA):")
    for axis_info in report['top_changing_axes'][:5]:
        axis_name = smart_net._get_axis_name(axis_info['axis'])
        print(f"   [{axis_info['axis']:2}] {axis_name:20} {axis_info['changes']:3} changes")
    
    # Exportar relatório combinado
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "scenario": "Dual-Livros + Delta Compression",
        "config": {
            "delta_threshold": compressor.threshold,
            "delta_max_chain": compressor.max_delta_chain
        },
        "compression": report,
        "books": comparison,
        "semantic_distance": distance,
        "total_messages": total_messages,
        "total_bytes_saved": total_saved
    }
    
    filename = f"dual_delta_report_{int(time.time())}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Report: {filename}")

    print("\n" + "=" * 80)
    print("✅ Simulation complete!")
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Dual-Books + Delta")
    parser.add_argument("--backend", choices=["deepseek", "anthropic", "mock"],
                       default="mock")
    parser.add_argument("--rounds", type=int, default=2)
    args = parser.parse_args()

    if args.backend == "deepseek" and not os.environ.get("DEEPSEEK_API_KEY"):
        print("⚠️ DEEPSEEK_API_KEY not set. Using mock.")
        args.backend = "mock"
    
    run_dual_with_delta(args.backend, args.rounds)
