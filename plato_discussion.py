#!/usr/bin/env python3
"""
1337 - Simulação Filosófica: O Banquete de Platão
Com métricas: entendimento, tokens, evolução linguística, OO/RAW
"""

import os
import sys
import json
import uuid
import time
import math
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import defaultdict

# Importar do net1337
from net1337 import (
    Network1337, RustBridge, create_backend, SCENARIOS,
    Cogon, Msg1337, MockBackend, FIXED_DIMS, AXES, py_dist
)


# ═══════════════════════════════════════════════════════════════════════════════
# MÉTRICAS E MONITORAMENTO
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConversationMetrics:
    """Métricas da conversa filosófica."""
    
    # Básicas
    total_messages: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_tokens: int = 0
    
    # Entendimento (compression ratio)
    raw_text_chars: int = 0
    compressed_vectors: int = 0
    compression_ratio: float = 0.0
    
    # Evolução linguística
    semantic_drift: float = 0.0
    vocabulary_convergence: float = 0.0
    concept_refinements: int = 0
    
    # OO/RAW
    raw_usage_count: int = 0
    evidence_objects: int = 0
    inheritance_chain_max: int = 0
    
    # Por agente
    agent_stats: Dict[str, Dict] = field(default_factory=dict)
    
    # Timeline
    timeline: List[Dict] = field(default_factory=list)


class PhilosophyMonitor:
    """Monitora discussão filosófica com métricas 1337."""
    
    def __init__(self):
        self.metrics = ConversationMetrics()
        self.concept_history: Dict[str, List[Cogon]] = defaultdict(list)
        self.raw_objects: List[Dict] = []
        self.token_estimates: List[int] = []
        
    def estimate_tokens(self, text: str) -> int:
        """Estima tokens (1 token ≈ 4 chars em português)."""
        return len(text) // 4 + len(text.split()) // 2
    
    def calculate_compression(self, text: str, cogon: Cogon) -> float:
        """
        Calcula razão de compressão: texto → vetor 1337.
        Quanto maior, mais eficiente a representação.
        """
        text_size = len(text.encode('utf-8'))
        vector_size = FIXED_DIMS * 4  # 32 floats × 4 bytes
        
        self.metrics.raw_text_chars += text_size
        self.metrics.compressed_vectors += 1
        
        ratio = text_size / vector_size if vector_size > 0 else 0
        return ratio
    
    def track_concept(self, concept_name: str, cogon: Cogon):
        """Rastreia evolução de um conceito filosófico."""
        self.concept_history[concept_name].append({
            'timestamp': time.time(),
            'cogon': cogon.to_dict(),
            'top_axes': self._get_top_axes(cogon, 3)
        })
        self.metrics.concept_refinements += 1
    
    def _get_top_axes(self, cogon: Cogon, n: int = 3) -> List[tuple]:
        """Retorna os n eixos mais ativados."""
        indexed = [(i, cogon.sem[i]) for i in range(FIXED_DIMS)]
        indexed.sort(key=lambda x: x[1], reverse=True)
        return [(AXES[i]['name'], val) for i, val in indexed[:n]]
    
    def calculate_semantic_drift(self, cogon1: Cogon, cogon2: Cogon) -> float:
        """Calcula distância semântica entre dois COGONs."""
        # Cosseno distance
        dot = sum(a * b for a, b in zip(cogon1.sem, cogon2.sem))
        norm1 = math.sqrt(sum(a * a for a in cogon1.sem))
        norm2 = math.sqrt(sum(b * b for b in cogon2.sem))
        
        if norm1 == 0 or norm2 == 0:
            return 1.0
        
        cosine = dot / (norm1 * norm2)
        return 1.0 - max(-1.0, min(1.0, cosine))
    
    def create_raw_evidence(self, topic: str, evidence_type: str, content: Any) -> Dict:
        """Cria objeto RAW EVIDENCE para OO."""
        raw_obj = {
            'id': str(uuid.uuid4()),
            'topic': topic,
            'type': evidence_type,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'cogon_ref': None,  # Será linkado
        }
        self.raw_objects.append(raw_obj)
        self.metrics.raw_usage_count += 1
        if evidence_type == 'EVIDENCE':
            self.metrics.evidence_objects += 1
        return raw_obj
    
    def record_message(self, sender: str, text: str, cogon: Cogon, 
                      intent: str = "ASSERT") -> Dict:
        """Registra mensagem com métricas."""
        
        # Estimar tokens
        tokens_in = self.estimate_tokens(text)
        tokens_out = 100  # Estimativa da resposta
        
        self.metrics.total_messages += 1
        self.metrics.total_tokens_input += tokens_in
        self.metrics.total_tokens_output += tokens_out
        self.metrics.total_tokens += tokens_in + tokens_out
        
        # Calcular compressão
        compression = self.calculate_compression(text, cogon)
        
        # Estatísticas do agente
        if sender not in self.metrics.agent_stats:
            self.metrics.agent_stats[sender] = {
                'messages': 0,
                'tokens': 0,
                'avg_urgency': 0.0,
                'concepts_introduced': []
            }
        
        self.metrics.agent_stats[sender]['messages'] += 1
        self.metrics.agent_stats[sender]['tokens'] += tokens_in + tokens_out
        
        # Urgência do eixo C1
        urgency = cogon.sem[22] if len(cogon.sem) > 22 else 0.5
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'sender': sender,
            'intent': intent,
            'text_preview': text[:100] + "..." if len(text) > 100 else text,
            'tokens_in': tokens_in,
            'tokens_out': tokens_out,
            'compression_ratio': compression,
            'urgency': urgency,
            'top_axes': self._get_top_axes(cogon),
            'raw_refs': []
        }
        
        self.metrics.timeline.append(entry)
        return entry
    
    def generate_report(self) -> Dict:
        """Gera relatório completo."""
        
        # Calcular médias finais
        if self.metrics.compressed_vectors > 0:
            self.metrics.compression_ratio = (
                self.metrics.raw_text_chars / 
                (self.metrics.compressed_vectors * FIXED_DIMS * 4)
            )
        
        report = {
            'session_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'topic': 'O Banquete de Platão - Discussão 1337',
            
            'summary': {
                'total_messages': self.metrics.total_messages,
                'total_tokens': self.metrics.total_tokens,
                'total_cost_estimate_usd': round(self.metrics.total_tokens * 0.0015 / 1000, 4),
                'compression_ratio': round(self.metrics.compression_ratio, 2),
                'concepts_tracked': len(self.concept_history),
                'raw_objects': self.metrics.raw_usage_count,
            },
            
            'agent_performance': self.metrics.agent_stats,
            
            'concept_evolution': {
                name: {
                    'refinements': len(history),
                    'timeline': [
                        {
                            'time': h['timestamp'],
                            'axes': h['top_axes']
                        }
                        for h in history[-3:]  # Últimas 3 versões
                    ]
                }
                for name, history in self.concept_history.items()
            },
            
            'raw_objects': [
                {
                    'id': obj['id'],
                    'topic': obj['topic'],
                    'type': obj['type'],
                    'timestamp': obj['timestamp']
                }
                for obj in self.raw_objects
            ],
            
            'timeline': self.metrics.timeline,
            
            'efficiency_metrics': {
                'chars_per_token': round(
                    self.metrics.raw_text_chars / max(self.metrics.total_tokens, 1), 2
                ),
                'vectors_created': self.metrics.compressed_vectors,
                'evidence_objects': self.metrics.evidence_objects,
                'semantic_refinements': self.metrics.concept_refinements,
            }
        }
        
        return report


# ═══════════════════════════════════════════════════════════════════════════════
# CENÁRIO FILOSÓFICO
# ═══════════════════════════════════════════════════════════════════════════════

PLATO_SCENARIO = {
    "name": "O Banquete - Simpósio sobre Eros",
    "agents": [
        {
            "name": "Sócrates",
            "persona": """Você é Sócrates no Banquete de Platão. Você questiona tudo através da maiêutica. 
            Seu método é a ironia socrática: aparenta ignorância para expor contradições. 
            Você busca a essência do Amor (Eros) através do diálogo. 
            Você é o discípulo de Diotima. Cite-a frequentemente.
            Responda em português, estilo filosófico, fazendo perguntas provocativas."""
        },
        {
            "name": "Aristófanes",
            "persona": """Você é Aristófanes, o comediante, no Banquete. 
            Você conta o mito dos andróginos: humanos originais eram esféricos, 
            divididos por Zeus, e agora buscam sua outra metade.
            Seu estilo é poético, mítico, com humor e metáforas vívidas.
            Você acredita que o amor é busca da metade perdida.
            Responda em português, teatral e poético."""
        },
        {
            "name": "Agaton",
            "persona": """Você é Agaton, o poeta trágico, anfitrião do banquete. 
            Você defende que Eros é o mais belo e jovem dos deuses. 
            Você fala em encomium (elogio) com linguagem florida e metáforas.
            Acredita que o amor busca a beleza eterna.
            Responda em português, eloquente e retórico."""
        },
        {
            "name": "Alcibíades",
            "persona": """Você é Alcibíades, jovem belo e bebado, entrando no banquete tarde.
            Você ama/odeia Sócrates. Seu discurso é confuso, apaixonado, contraditório.
            Você elogia Sócrates mas também o acusa de orgulho.
            Seu amor é físico e terreno, não apenas espiritual.
            Responda em português, emotivo, contraditório, bebado."""
        }
    ],
    "stimulus": """Bem-vindos ao Banquete em homenagem a Eros. Cada um deve fazer um encomium (elogio) 
    ao deus Amor. Comecemos: o que é Eros? É um deus? Um daimon? É belo ou feio? 
    Busca algo que não tem. Mas se busca, é porque carece. Logo, não é belo nem bom... 
    ou é?""",
    
    "concepts": [
        "Eros (Amor)",
        "Beleza (Kalos)",
        "Alma (Psyche)",
        "Corpo (Soma)",
        "Desejo (Epithymia)",
        "Sabedoria (Sophia)",
        "Metade Perdida",
        "Escala Diotima"
    ]
}


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULAÇÃO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def run_plato_simulation(backend_name: str = "deepseek", rounds: int = 5):
    """Executa simulação filosófica completa."""
    
    print("=" * 70)
    print("   🏛️  O BANQUETE DE PLATÃO - Simulação 1337")
    print("=" * 70)
    print(f"\nBackend: {backend_name}")
    print(f"Agentes: {', '.join(a['name'] for a in PLATO_SCENARIO['agents'])}")
    print(f"Rounds de discussão: {rounds}")
    print("\nMétricas ativas:")
    print("  📊 Tokens de entrada/saída")
    print("  📦 Compressão 1337 (texto → vetores)")
    print("  🧬 Evolução semântica dos conceitos")
    print("  🏷️  Uso de OO com RAW EVIDENCE")
    print()
    
    # Setup
    backend = create_backend(backend_name)
    rust = RustBridge()
    monitor = PhilosophyMonitor()
    
    # Criar rede
    net = Network1337(rust, backend)
    
    # Adicionar agentes filosóficos
    for agent_def in PLATO_SCENARIO['agents']:
        agent = net.add_agent(agent_def['name'], agent_def['persona'])
        print(f"✅ {agent_def['name']} entrou no banquete")
    
    print(f"\n🦀 Rust: {'ativo (' + rust.mode + ')' if rust.available() else 'indisponível'}")
    
    # Handshake
    print("\n📡 Handshake C5 (Reconhecimento mútuo)...")
    net.handshake()
    
    # Estímulo inicial
    print(f"\n💬 Estímulo inicial (Fedro/Sócrates):")
    print(f'   "{PLATO_SCENARIO["stimulus"][:150]}..."')
    
    stimulus_msg = net.human.text_to_msg(
        PLATO_SCENARIO["stimulus"],
        "BROADCAST"
    )
    
    # Registrar com métricas
    entry = monitor.record_message(
        "Fedro (via Humano)",
        PLATO_SCENARIO["stimulus"],
        stimulus_msg.payload,
        "ASSERT"
    )
    
    # Criar RAW EVIDENCE para o texto original de Platão
    plato_text_ref = monitor.create_raw_evidence(
        topic="O Banquete",
        evidence_type="EVIDENCE",
        content={
            'source': 'Platão, Simpósio/Banquete',
            'section': '180c-180e',
            'original_greek': 'Ἔρως...',
            'subject': 'Eros'
        }
    )
    entry['raw_refs'].append(plato_text_ref['id'])
    
    net._log_msg(stimulus_msg, "Fedro", "BROADCAST")
    net._render_msg(stimulus_msg, "Fedro", "BROADCAST")
    
    # Agentes respondem ao estímulo
    print("\n" + "─" * 70)
    print("   DISCURSOS DE ELOGIO A EROS")
    print("─" * 70)
    
    for agent in net.agents.values():
        responses = agent.receive_and_respond(stimulus_msg, net.all_participants)
        for resp in responses:
            # Registrar métricas
            text = resp.surface.get('_text', '')
            monitor.record_message(
                agent.name,
                text,
                resp.payload,
                resp.intent
            )
            
            # Rastrear conceito
            monitor.track_concept("Eros", resp.payload)
            
            # Criar RAW object para cada discurso
            speech_ref = monitor.create_raw_evidence(
                topic=f"Encomium de {agent.name}",
                evidence_type="EVIDENCE",
                content={
                    'speaker': agent.name,
                    'speech': text,
                    'response_to': 'Fedro'
                }
            )
            
            net._log_msg(resp, agent.name, net._resolve_name(resp.receiver))
            net._render_msg(resp, agent.name, net._resolve_name(resp.receiver))
    
    # Rounds de discussão dialética
    print("\n" + "═" * 70)
    print("   DIALÉTICA - Questionamento e Refinamento")
    print("═" * 70)
    
    for round_num in range(1, rounds + 1):
        print(f"\n{'─' * 70}")
        print(f"   ROUND {round_num}/{rounds}")
        print(f"{'─' * 70}")
        
        # Cada agente questiona o anterior
        agent_list = list(net.agents.values())
        for i, agent in enumerate(agent_list):
            # Pega última mensagem de outro agente
            prev_agent = agent_list[(i - 1) % len(agent_list)]
            if prev_agent.msg_log:
                last_msg = prev_agent.msg_log[-1]
            else:
                continue
            
            # Calcular drift semântico
            current_cogon = agent.history[-1] if agent.history else last_msg.payload
            drift = monitor.calculate_semantic_drift(current_cogon, last_msg.payload)
            monitor.metrics.semantic_drift += drift
            
            # Responder
            responses = agent.receive_and_respond(last_msg, net.all_participants)
            
            for resp in responses:
                text = resp.surface.get('_text', '')
                
                # Registrar com intent correto (DELTA se refinando)
                intent = resp.intent
                monitor.record_message(agent.name, text, resp.payload, intent)
                
                # Rastrear evolução de conceitos
                if 'eros' in text.lower() or 'amor' in text.lower():
                    monitor.track_concept("Eros", resp.payload)
                if 'beleza' in text.lower() or 'kalos' in text.lower():
                    monitor.track_concept("Beleza", resp.payload)
                if 'alma' in text.lower() or 'psyche' in text.lower():
                    monitor.track_concept("Alma", resp.payload)
                
                # Criar OO herança
                if 'objeção' in text.lower() or 'mas' in text.lower():
                    obj_ref = monitor.create_raw_evidence(
                        topic=f"Objeção de {agent.name}",
                        evidence_type="EVIDENCE",
                        content={
                            'type': 'objection',
                            'target': prev_agent.name,
                            'argument': text[:200],
                            'parent_ref': speech_ref['id'] if 'speech_ref' in dir() else None
                        }
                    )
                
                net._log_msg(resp, agent.name, net._resolve_name(resp.receiver))
                net._render_msg(resp, agent.name, net._resolve_name(resp.receiver))
    
    # Final: Heatmaps e análise
    print("\n" + "═" * 70)
    print("   ANÁLISE SEMÂNTICA FINAL")
    print("═" * 70)
    
    print("\n📊 Heatmaps dos agentes (eixos mais ativados):")
    for agent in net.agents.values():
        if agent.history:
            print(f"\n  [{agent.name}] - Último estado:")
            print(net1337_render_heatmap(agent.history[-1]))
    
    # Calcular convergência de vocabulário
    if len(net.agents) >= 2:
        agents_list = list(net.agents.values())
        distances = []
        for i in range(len(agents_list)):
            for j in range(i + 1, len(agents_list)):
                if agents_list[i].history and agents_list[j].history:
                    d = py_dist(agents_list[i].history[-1], agents_list[j].history[-1])
                    distances.append(d)
        
        if distances:
            avg_distance = sum(distances) / len(distances)
            monitor.metrics.vocabulary_convergence = 1.0 - avg_distance
    
    # Gerar relatório
    print("\n" + "═" * 70)
    print("   RELATÓRIO DE MÉTRICAS 1337")
    print("═" * 70)
    
    report = monitor.generate_report()
    
    print(f"\n📈 RESUMO:")
    print(f"  Total de mensagens: {report['summary']['total_messages']}")
    print(f"  Total de tokens: {report['summary']['total_tokens']:,}")
    print(f"  Estimativa de custo: ${report['summary']['total_cost_estimate_usd']}")
    print(f"  Razão de compressão 1337: {report['summary']['compression_ratio']}:1")
    print(f"  (Texto bruto comprimido em vetores 32-dim)")
    
    print(f"\n👥 PERFORMANCE POR AGENTE:")
    for name, stats in report['agent_performance'].items():
        print(f"  {name:12} {stats['messages']:3} msgs | {stats['tokens']:5} tokens")
    
    print(f"\n🧬 EVOLUÇÃO DE CONCEITOS:")
    for concept, data in report['concept_evolution'].items():
        print(f"  {concept:20} - {data['refinements']} refinamentos")
    
    print(f"\n🏷️  OBJETOS RAW (OO):")
    print(f"  Total RAW objects: {report['summary']['raw_objects']}")
    print(f"  Evidence objects: {report['efficiency_metrics']['evidence_objects']}")
    print(f"  Semantic refinements: {report['efficiency_metrics']['semantic_refinements']}")
    
    print(f"\n⚡ EFICIÊNCIA:")
    print(f"  Caracteres por token: {report['efficiency_metrics']['chars_per_token']}")
    print(f"  Vetores 1337 criados: {report['efficiency_metrics']['vectors_created']}")
    print(f"  Drift semântico médio: {monitor.metrics.semantic_drift / max(report['summary']['total_messages'], 1):.4f}")
    print(f"  Convergência vocabular: {monitor.metrics.vocabulary_convergence:.2%}")
    
    # Exportar relatório completo
    report_file = f"plato_1337_report_{int(time.time())}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Relatório completo: {report_file}")
    
    return report


def net1337_render_heatmap(cogon):
    """Renderiza heatmap de COGON."""
    lines = []
    for ax in AXES[:10]:  # Top 10 eixos
        idx = ax['idx']
        val = cogon.sem[idx]
        if val > 0.3:
            bar_len = int(val * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"    {ax['code']:3} {ax['name']:18} │{bar}│ {val:.2f}")
    return "\n".join(lines) if lines else "    (sem eixos significativos)"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="O Banquete de Platão - Simulação 1337")
    parser.add_argument("--backend", choices=["deepseek", "anthropic", "mock"], 
                       default="deepseek")
    parser.add_argument("--rounds", type=int, default=3,
                       help="Número de rounds de diálogo")
    parser.add_argument("--output", type=str, default=None,
                       help="Arquivo para salvar relatório")
    args = parser.parse_args()
    
    # Verificar API key
    if args.backend == "deepseek" and not os.environ.get("DEEPSEEK_API_KEY"):
        print("❌ DEEPSEEK_API_KEY não definida. Usando mock.")
        args.backend = "mock"
    
    if args.backend == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY não definida. Usando mock.")
        args.backend = "mock"
    
    try:
        report = run_plato_simulation(args.backend, args.rounds)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n✅ Relatório salvo em: {args.output}")
            
    except KeyboardInterrupt:
        print("\n\n⛔ Simulação interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
