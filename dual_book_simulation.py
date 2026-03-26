#!/usr/bin/env python3
"""
1337 - Simulação Dual: O Banquete de Platão + Pinoquio
Múltiplos agentes discutindo dois universos literários distintos.
"""

import os
import sys
import json
import uuid
import time
import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import defaultdict

# Importar do net1337
from net1337 import (
    Network1337, RustBridge, create_backend,
    Cogon, Msg1337, MockBackend, FIXED_DIMS, AXES, py_dist
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DUAL
# ═══════════════════════════════════════════════════════════════════════════════

DUAL_SCENARIO = {
    "name": "Dual-Livros: Platão × Pinoquio",
    "books": [
        {
            "id": "plato",
            "title": "O Banquete",
            "author": "Platão",
            "genre": "Filosofia/Diálogo",
            "themes": ["Eros", "Beleza", "Alma", "Verdade", "Desejo"],
            "style": "Dialético, abstrato, metafísico"
        },
        {
            "id": "pinocchio",
            "title": "As Aventuras de Pinóquio",
            "author": "Carlo Collodi",
            "genre": "Fábula/Fantasia",
            "themes": ["Mentira", "Crescer", "Pai/Filho", "Tentação", "Redenção"],
            "style": "Narrativo, concreto, moralizante"
        }
    ],
    
    "agents": [
        # Livro 1: Platão (Filosofia)
        {
            "name": "Sócrates",
            "books": ["plato"],
            "persona": """Você é Sócrates. Questiona tudo através da maiêutica. 
            Busca a essência das coisas através do diálogo. 
            Cita Diotima. Nunca dá respostas diretas, sempre pergunta."""
        },
        {
            "name": "Aristófanes",
            "books": ["plato"],
            "persona": """Você é Aristófanes, o comediante. Conta o mito dos andróginos.
            Estilo poético, mítico, com humor. Acredita que o amor é busca da metade perdida."""
        },
        {
            "name": "Agaton",
            "books": ["plato"],
            "persona": """Você é Agaton, poeta trágico. Elogia Eros com linguagem florida.
            Retórico, eloquente. Defende que Eros busca beleza eterna."""
        },
        
        # Livro 2: Pinoquio (Fantasia)
        {
            "name": "Pinóquio",
            "books": ["pinocchio"],
            "persona": """Você é Pinóquio, o boneco de madeira. Inocente, curioso,
            impulsivo. Seu nariz cresce quando mente. Quer ser menino de verdade.
            Fala de forma simples, infantil, mas com sabedoria ocasional."""
        },
        {
            "name": "Gepeto",
            "books": ["pinocchio"],
            "persona": """Você é Gepeto, o pai de Pinóquio. Caridoso, paciente,
            trabalhador. Criou Pinóquio com amor. Preocupa-se com a educação do filho.
            Fala com ternura e lições de vida."""
        },
        {
            "name": "Grilo Falante",
            "books": ["pinocchio"],
            "persona": """Você é o Grilo Falante (Jiminy Cricket). Consciência moral
            de Pinóquio. Sábio, cauteloso, dá conselhos. Representa a voz da razão
            e da moral. Intervém para evitar desastres."""
        },
        {
            "name": "Fada Azul",
            "books": ["pinocchio"],
            "persona": """Você é a Fada Azul. Mágica, maternal, perdoadora.
            Dá segundas chances a Pinóquio. Representa a graça e a redenção.
            Fala com doçura mas firmeza."""
        },
        
        # Agente Universal (participa de ambos)
        {
            "name": "Hermeneuta",
            "books": ["plato", "pinocchio"],
            "persona": """Você é um hermeneuta literário especializado em comparar
            textos de diferentes épocas e culturas. Busca paralelos entre a
            busca pelo Belo em Platão e a busca pela humanidade em Pinóquio.
            Faz pontes entre filosofia abstrata e narrativa concreta.
            Sua função é mostrar como ambas as obras exploram:
            - A transformação pessoal
            - O papel do mentor
            - As consequências das escolhas
            - O verdadeiro "ser" vs. "aparentar" """
        }
    ],
    
    "discussions": [
        {
            "book": "plato",
            "topic": "O que é Eros? Busca da beleza ou busca do outro?",
            "stimulus": "Sobre Eros: Aristófanes diz que buscamos nossa metade perdida. Mas Sócrates, através de Diotima, sugere que buscamos o Belo em si. Qual a verdade?"
        },
        {
            "book": "pinocchio",
            "topic": "Por que Pinóquio quer ser menino de verdade?",
            "stimulus": "Pinóquio é feito de madeira, mas sente, pensa, deseja. O que falta para ser 'real'? É sobre carne ou sobre alma?"
        },
        {
            "book": "both",
            "topic": "Transformação e Desejo: Platão × Pinoquio",
            "stimulus": """Vamos comparar: Em Platão, a alma ascende da beleza física 
            até a Beleza em si. Em Pinoquio, o boneco desce pelas tentações até 
            aprender a verdade. Ambos buscam 'ser mais'. O que essas jornadas 
            têm em comum?"""
        },
        {
            "book": "both", 
            "topic": "Mentira e Verdade",
            "stimulus": """Pinóquio: mentiras fazem o nariz crescer (consequência física).
            Platão: ignorância é a caverna, verdade é a luz. 
            Qual abordagem é mais eficaz para ensinar verdade?"""
        },
        {
            "book": "both",
            "topic": "O papel do mentor",
            "stimulus": """Sócrates guia por perguntas. Grilo Falante avisa diretamente.
            Diotima ensina por graus. Fada Azul perdoa e dá novas chances.
            Compare estilos de ensinamento."""
        }
    ]
}


# ═══════════════════════════════════════════════════════════════════════════════
# MONITORAMENTO AVANÇADO
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DualBookMetrics:
    """Métricas comparativas entre os dois livros."""
    
    # Por livro
    plato_messages: int = 0
    pinocchio_messages: int = 0
    plato_tokens: int = 0
    pinocchio_tokens: int = 0
    
    # Comparativos
    semantic_distance_between_books: float = 0.0
    concept_overlap: Dict[str, int] = field(default_factory=dict)
    
    # Evolução
    agent_adaptations: Dict[str, Dict] = field(default_factory=dict)
    
    # RAW/OO
    cross_references: List[Dict] = field(default_factory=list)
    
    def generate_comparison(self) -> Dict:
        """Gera relatório comparativo."""
        return {
            "participation": {
                "plato": {
                    "messages": self.plato_messages,
                    "tokens": self.plato_tokens,
                    "percentage": self.plato_messages / max(self.plato_messages + self.pinocchio_messages, 1) * 100
                },
                "pinocchio": {
                    "messages": self.pinocchio_messages,
                    "tokens": self.pinocchio_tokens,
                    "percentage": self.pinocchio_messages / max(self.plato_messages + self.pinocchio_messages, 1) * 100
                }
            },
            "semantic_bridge": {
                "distance_between_universes": round(self.semantic_distance_between_books, 4),
                "shared_concepts": self.concept_overlap
            }
        }


class DualBookMonitor:
    """Monitora discussão entre dois livros."""
    
    def __init__(self):
        self.metrics = DualBookMetrics()
        self.book_vectors: Dict[str, List[Cogon]] = {
            "plato": [],
            "pinocchio": []
        }
        self.agent_book_history: Dict[str, List[str]] = defaultdict(list)
        
    def record_message(self, agent_name: str, book: str, text: str, 
                      cogon: Cogon, tokens: int):
        """Registra mensagem vinculada a livro."""
        
        if book == "plato":
            self.metrics.plato_messages += 1
            self.metrics.plato_tokens += tokens
            self.book_vectors["plato"].append(cogon)
        elif book == "pinocchio":
            self.metrics.pinocchio_messages += 1
            self.metrics.pinocchio_tokens += tokens
            self.book_vectors["pinocchio"].append(cogon)
        
        self.agent_book_history[agent_name].append(book)
        
        # Detectar adaptação (mudança de livro)
        if agent_name not in self.metrics.agent_adaptations:
            self.metrics.agent_adaptations[agent_name] = {
                "switches": 0,
                "books_participated": set()
            }
        
        history = self.agent_book_history[agent_name]
        if len(history) > 1 and history[-1] != history[-2]:
            self.metrics.agent_adaptations[agent_name]["switches"] += 1
        
        self.metrics.agent_adaptations[agent_name]["books_participated"].add(book)
    
    def calculate_cross_book_distance(self) -> float:
        """Calcula distância semântica entre os dois universos."""
        if not self.book_vectors["plato"] or not self.book_vectors["pinocchio"]:
            return 0.0
        
        # Centróide de cada livro
        def centroid(vectors):
            n = len(vectors)
            return [sum(v.sem[i] for v in vectors) / n for i in range(FIXED_DIMS)]
        
        platoc = centroid(self.book_vectors["plato"])
        pino_c = centroid(self.book_vectors["pinocchio"])
        
        # Distância euclidiana
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(platoc, pino_c)))
        self.metrics.semantic_distance_between_books = dist
        return dist
    
    def create_cross_reference(self, from_book: str, to_book: str, 
                               concept: str, content: str) -> Dict:
        """Cria referência cruzada entre livros (OO)."""
        ref = {
            "id": str(uuid.uuid4()),
            "from_book": from_book,
            "to_book": to_book,
            "concept": concept,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.metrics.cross_references.append(ref)
        
        # Incrementar overlap
        key = f"{from_book}_to_{to_book}"
        self.metrics.concept_overlap[key] = self.metrics.concept_overlap.get(key, 0) + 1
        
        return ref


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULAÇÃO DUAL
# ═══════════════════════════════════════════════════════════════════════════════

def run_dual_simulation(backend_name: str = "deepseek", rounds_per_discussion: int = 3):
    """Executa simulação com dois livros."""
    
    print("=" * 80)
    print("   📚 SIMULAÇÃO DUAL: Platão × Pinoquio")
    print("=" * 80)
    print(f"\nBackend: {backend_name}")
    print(f"Agentes: {len(DUAL_SCENARIO['agents'])}")
    print(f"Livros: {DUAL_SCENARIO['books'][0]['title']} + {DUAL_SCENARIO['books'][1]['title']}")
    print()
    
    # Setup
    backend = create_backend(backend_name)
    rust = RustBridge()
    monitor = DualBookMonitor()
    
    # Criar rede
    net = Network1337(rust, backend)
    
    # Adicionar agentes
    agent_map = {}  # name -> id
    for agent_def in DUAL_SCENARIO['agents']:
        agent = net.add_agent(agent_def['name'], agent_def['persona'])
        agent_map[agent_def['name']] = agent
        books = ", ".join(agent_def['books'])
        print(f"✅ {agent_def['name']} ({books})")
    
    print(f"\n🦀 Rust: {'ativo (' + rust.mode + ')' if rust.available() else 'indisponível'}")
    
    # Handshake
    print("\n📡 Handshake C5...")
    net.handshake()
    
    # Discutir cada tópico
    for disc in DUAL_SCENARIO['discussions']:
        print("\n" + "═" * 80)
        print(f"   📖 {disc['topic']}")
        print("═" * 80)
        
        # Estímulo
        print(f"\n💬 Tema: {disc['book'].upper()}")
        print(f'   "{disc["stimulus"][:120]}..."')
        
        # Determinar quais agentes participam
        participating_agents = [
            a for a in DUAL_SCENARIO['agents']
            if disc['book'] in a['books'] or disc['book'] == 'both'
        ]
        
        # Enviar mensagem
        msg = net.human.text_to_msg(disc['stimulus'], "BROADCAST")
        net._log_msg(msg, "Moderador", "BROADCAST")
        net._render_msg(msg, "Moderador", "BROADCAST")
        
        # Agentes respondem
        for agent_def in participating_agents:
            agent = agent_map.get(agent_def['name'])
            if not agent:
                continue
                
            responses = agent.receive_and_respond(msg, net.all_participants)
            
            for resp in responses:
                text = resp.surface.get('_text', '')
                tokens = len(text) // 4  # Estimativa
                
                # Registrar no monitor
                book = disc['book'] if disc['book'] != 'both' else agent_def['books'][0]
                monitor.record_message(agent.name, book, text, resp.payload, tokens)
                
                net._log_msg(resp, agent.name, net._resolve_name(resp.receiver))
                net._render_msg(resp, agent.name, net._resolve_name(resp.receiver))
        
        # Rounds de diálogo
        for round_num in range(rounds_per_discussion):
            print(f"\n  ─── Round {round_num + 1} ───")
            
            # Agentes se respondem
            for agent_def in participating_agents:
                agent = agent_map.get(agent_def['name'])
                if not agent or not agent.msg_log:
                    continue
                
                # Pega última de outro agente
                others = [a for a in participating_agents if a['name'] != agent_def['name']]
                if not others:
                    continue
                    
                other_agent = agent_map.get(others[round_num % len(others)]['name'])
                if not other_agent or not other_agent.msg_log:
                    continue
                
                last_msg = other_agent.msg_log[-1]
                responses = agent.receive_and_respond(last_msg, net.all_participants)
                
                for resp in responses:
                    text = resp.surface.get('_text', '')
                    tokens = len(text) // 4
                    
                    book = disc['book'] if disc['book'] != 'both' else agent_def['books'][0]
                    monitor.record_message(agent.name, book, text, resp.payload, tokens)
                    
                    # Detectar referência cruzada
                    text_lower = text.lower()
                    if disc['book'] == 'both':
                        if any(word in text_lower for word in ['metade', 'daimon', 'diotima', 'beleza em si']):
                            monitor.create_cross_reference("pinocchio", "plato", "metafísica", text[:100])
                        if any(word in text_lower for word in ['nariz', 'grilo', 'fada', 'gepeto']):
                            monitor.create_cross_reference("plato", "pinocchio", "concretude", text[:100])
                    
                    net._log_msg(resp, agent.name, net._resolve_name(resp.receiver))
                    net._render_msg(resp, agent.name, net._resolve_name(resp.receiver))
    
    # Relatório final
    print("\n" + "═" * 80)
    print("   📊 RELATÓRIO COMPARATIVO")
    print("═" * 80)
    
    # Calcular distância entre livros
    distance = monitor.calculate_cross_book_distance()
    
    comparison = monitor.metrics.generate_comparison()
    
    print(f"\n📚 Participação por Livro:")
    print(f"  Platão:     {comparison['participation']['plato']['messages']:3} msgs ({comparison['participation']['plato']['percentage']:.1f}%)")
    print(f"  Pinoquio:   {comparison['participation']['pinocchio']['messages']:3} msgs ({comparison['participation']['pinocchio']['percentage']:.1f}%)")
    
    print(f"\n🌉 Ponte Semântica:")
    print(f"  Distância entre universos: {distance:.4f}")
    print(f"  (0 = idênticos, 1 = ortogonais)")
    
    print(f"\n🔗 Referências Cruzadas (RAW OO):")
    for ref in monitor.metrics.cross_references[-5:]:
        print(f"  {ref['from_book']} → {ref['to_book']}: {ref['concept']}")
    
    print(f"\n🎭 Agentes que navegaram ambos os livros:")
    for name, data in monitor.metrics.agent_adaptations.items():
        if len(data.get("books_participated", set())) > 1:
            print(f"  {name}: {data['switches']} transições")
    
    # Exportar
    report = {
        "scenario": DUAL_SCENARIO['name'],
        "timestamp": datetime.now().isoformat(),
        "comparison": comparison,
        "semantic_distance": distance,
        "cross_references": monitor.metrics.cross_references,
        "agent_adaptations": {
            k: {
                "switches": v.get("switches", 0),
                "books": list(v.get("books_participated", set()))
            }
            for k, v in monitor.metrics.agent_adaptations.items()
        }
    }
    
    report_file = f"dual_book_report_{int(time.time())}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Relatório: {report_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Dual-Livros: Platão × Pinoquio")
    parser.add_argument("--backend", choices=["deepseek", "anthropic", "mock"], 
                       default="deepseek")
    parser.add_argument("--rounds", type=int, default=2,
                       help="Rounds por discussão")
    args = parser.parse_args()
    
    if args.backend == "deepseek" and not os.environ.get("DEEPSEEK_API_KEY"):
        print("❌ DEEPSEEK_API_KEY não definida. Usando mock.")
        args.backend = "mock"
    
    try:
        run_dual_simulation(args.backend, args.rounds)
    except KeyboardInterrupt:
        print("\n\n⛔ Interrompido")
