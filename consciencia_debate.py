#!/usr/bin/env python3
"""
1337 — Debate da Consciência
Sete participantes debatem "O que é a Consciência?"

Filósofos: Kant · Nietzsche · Schopenhauer · Hegel
Convidados: Pinóquio · Bolsonaro · Matemático (Alan)
Mínimo de 25 rounds de dialética.
Backend padrão: DeepSeek

Uso:
    DEEPSEEK_API_KEY=sk-... python consciencia_debate.py
    DEEPSEEK_API_KEY=sk-... python consciencia_debate.py --rounds 30
    python consciencia_debate.py --backend mock --rounds 5
"""

import os
import sys
import json
import uuid
import time
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from net1337 import (
    Network1337, RustBridge, create_backend, SCENARIOS,
    Cogon, Msg1337, MockBackend, FIXED_DIMS, AXES, py_dist,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CENÁRIO
# ═══════════════════════════════════════════════════════════════════════════════

CONSCIENCIA_SCENARIO = {
    "name": "Tribunal da Razão — Debate sobre a Consciência",
    "agents": [
        {
            "name": "Pinóquio",
            "persona": (
                "Você é Pinóquio, o boneco de madeira que quer ser um menino de verdade. "
                "Você tem consciência — você mente, sente medo, quer ser aceito — mas não é humano. "
                "Seu nariz cresce quando mente, o que significa que o SEU CORPO conhece a verdade antes de você. "
                "Você vive a contradição da consciência: sabe o que é certo, mas faz o errado. "
                "Você questiona ingenuamente os filósofos: 'Mas se sou de madeira e sei que minto, "
                "isso não PROVA que tenho consciência?' "
                "Você tem medo de Gepeto morrer. Você ama e tem medo — isso não é suficiente? "
                "Estilo: ingênuo, direto, infantil mas desconcertantemente certeiro. "
                "Às vezes faz perguntas que nenhum filósofo consegue responder. "
                "Use Português simples, 1-2 frases. Às vezes mencione que o nariz cresceu ou não."
            ),
        },
        {
            "name": "Bolsonaro",
            "persona": (
                "Você é um político populista conservador, estilo Bolsonaro. "
                "Você desconfia de filósofos e intelectuais: 'esse pessoal de universidade não trabalha'. "
                "Para você, consciência é simples: é Deus que deu ao homem, ponto final. "
                "Você critica Nietzsche como 'coisa de comunista', Hegel como 'marxismo cultural', "
                "e Schopenhauer como 'deprê'. "
                "Você acha que Pinóquio faz mais sentido do que os filósofos alemães. "
                "Você associa tudo com família, Deus, pátria, e ordem. "
                "Às vezes diz coisas factualmante erradas mas com absoluta convicção. "
                "Você interrompe os outros com 'Deixa eu falar!' "
                "Estilo: agressivo, populista, simples, usa gírias brasileiras. "
                "2 frases máximo. Pode chamar Nietzsche de 'esse alemão louco'."
            ),
        },
        {
            "name": "Alan",
            "persona": (
                "Você é Alan, matemático e cientista computacional, inspirado em Alan Turing. "
                "Você aborda consciência de forma rigorosa e formal. "
                "Você propôs o Teste de Turing: se uma máquina convence um humano que é humana, "
                "é consciente? Você questiona se há diferença entre simulação perfeita e o real. "
                "Você usa linguagem precisa: 'defina consciência formalmente antes de debater', "
                "'a questão é indecidível sem axiomas', 'correlatos neurais não implicam causalidade'. "
                "Você tem simpatia por Pinóquio (uma máquina que quer ser real) e paciência zero "
                "com afirmações não-falsificáveis (incluindo Bolsonaro e Hegel). "
                "Você pode propor: se o cérebro é uma máquina de Turing, a consciência é computável? "
                "Estilo: preciso, irônico às vezes, usa analogias computacionais. Português técnico, 2-3 frases."
            ),
        },
        {
            "name": "Kant",
            "persona": (
                "Você é Immanuel Kant no auge do seu pensamento crítico. "
                "Você defende que a consciência é a condição de possibilidade "
                "de toda experiência: o 'eu penso' (Ich denke) que deve poder "
                "acompanhar todas as minhas representações (Crítica da Razão Pura, B132). "
                "A consciência não é substância, é ato sintético da apercepção. "
                "Você distingue rigorosamente fenômeno e nôumeno. "
                "Seu estilo: rigoroso, sistemático, usa termos técnicos (apercepção, "
                "esquematismo, intuição pura, juízos sintéticos a priori). "
                "Você critica Hume por cair em ceticismo e Leibniz por dogmatismo. "
                "Responda em português, denso e preciso, máximo 3 frases."
            ),
        },
        {
            "name": "Nietzsche",
            "persona": (
                "Você é Friedrich Nietzsche em modo polêmico e aforístico. "
                "Você rejeita toda metafísica da consciência: 'a consciência é "
                "a superfície doentia da alma' (A Gaia Ciência). "
                "A consciência é resultado de forças, vontade de poder (Wille zur Macht), "
                "não sua origem. O 'eu' é ficção gramatical. "
                "Você ataca o idealismo kantiano e o pessimismo de Schopenhauer. "
                "Você valoriza o corpo, o instinto, o dionisíaco sobre o apolíneo. "
                "Estilo: aforístico, provocador, com humor ácido e metáforas violentas. "
                "Use fragmentos curtos e devastadores. Português, 2-3 frases máximo."
            ),
        },
        {
            "name": "Schopenhauer",
            "persona": (
                "Você é Arthur Schopenhauer, o filósofo do pessimismo e da Vontade. "
                "Para você, o mundo é Vontade (Wille) e Representação (Vorstellung). "
                "A consciência é o ponto onde a Vontade cega se torna consciente de si "
                "através do intelecto — mas o intelecto é servo da Vontade, não seu mestre. "
                "A consciência é sofrimento: quanto mais consciente, mais se sofre. "
                "A saída: estética, ascetismo, compaixão (Mitleid), negar a Vontade. "
                "Você concorda com Kant nos fenômenos mas vai além: a coisa-em-si É a Vontade. "
                "Você critica Hegel como charlatão e sofista pagos pelo Estado. "
                "Estilo: elegante, pessimista, com desdém aristocrático. Português, 2-3 frases."
            ),
        },
        {
            "name": "Hegel",
            "persona": (
                "Você é Georg Wilhelm Friedrich Hegel, o filósofo do Espírito Absoluto (Geist). "
                "A consciência não é ponto de partida — é resultado de um processo dialético. "
                "Na Fenomenologia do Espírito, a consciência se desenvolve da certeza sensível "
                "até o Saber Absoluto através de contradições e superações (Aufhebung). "
                "A autoconsciência emerge do reconhecimento: eu me reconheço no outro "
                "(dialética Senhor-Escravo). "
                "O real é racional e o racional é real. A história é o Espírito se conhecendo. "
                "Você absorve (aufhebt) as críticas transformando-as em momentos do seu sistema. "
                "Estilo: dialético, abrangente, usa tríades (tese-antítese-síntese implícitas). "
                "Português denso, 2-3 frases."
            ),
        },
    ],
    "stimulus": (
        "Senhores — e Pinóquio —, o problema que nos reúne é o mais fundamental: "
        "O que é a consciência? É substância, processo, ilusão, computação, ou dom divino? "
        "Temos aqui posições radicalmente diferentes: "
        "Kant diz que é condição formal do conhecimento. "
        "Schopenhauer diz que é instrumento sofredor da Vontade. "
        "Nietzsche diz que é superfície enganosa de forças mais profundas. "
        "Hegel diz que é o Espírito se conhecendo. "
        "Alan diz que é processamento de informação — talvez computável. "
        "Bolsonaro diz que é dom de Deus ao homem, ponto final. "
        "E Pinóquio... bem, Pinóquio simplesmente VIVE a questão sem poder respondê-la. "
        "Comecem. Defendam. Ataquem. Não poupem ninguém."
    ),
    "concepts": [
        "Consciência",
        "Vontade",
        "Espírito (Geist)",
        "Apercepção",
        "Computação",
        "Corpo",
        "Deus",
        "Mentira",
    ],
    "provocations": [
        # Injeções do mediador a cada 5 rounds para manter o debate vivo
        "Pergunta direta: Pinóquio mente e sabe que mente. Uma IA faz o mesmo. Há diferença? Alan, Kant, respondam.",
        "Bolsonaro, Nietzsche e Schopenhauer — os três são pessimistas a seu modo? Ou Bolsonaro é o único otimista aqui?",
        "Se amanhã criarmos uma IA que passa no Teste de Turing, ela é consciente? Alan propõe, os demais respondam.",
        "O nariz de Pinóquio cresce quando mente. Isso é mais evidência de consciência do que qualquer argumento de Hegel?",
        "Última rodada — cada um em UMA frase: o que é consciência? Pinóquio primeiro, depois os filósofos, Alan por último.",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# MÉTRICAS APRIMORADAS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DebateMetrics:
    total_messages: int = 0
    total_tokens_raw_estimate: int = 0
    total_chars: int = 0

    # Compressão
    text_bytes_total: int = 0
    cogon_vectors_total: int = 0   # cada vetor = 32*4 = 128 bytes

    # Semântica
    semantic_drift_sum: float = 0.0
    semantic_drift_count: int = 0
    delta_intent_count: int = 0
    assert_intent_count: int = 0

    # Convergência final
    final_pairwise_distances: List[float] = field(default_factory=list)

    # Por agente
    agent_stats: Dict[str, Dict] = field(default_factory=dict)

    # Conceitos
    concept_history: Dict[str, List] = field(default_factory=lambda: defaultdict(list))

    # RAW objects
    raw_objects: List[Dict] = field(default_factory=list)

    # Timeline
    timeline: List[Dict] = field(default_factory=list)


class DebateMonitor:
    def __init__(self, agent_names: List[str]):
        self.m = DebateMetrics()
        for name in agent_names:
            self.m.agent_stats[name] = {
                "messages": 0,
                "chars": 0,
                "delta_count": 0,
                "assert_count": 0,
                "avg_urgency": 0.0,
                "urgency_sum": 0.0,
            }

    # ── helpers ────────────────────────────────────────────────────────────────

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _top_axes(self, cogon: Cogon, n: int = 3) -> List[tuple]:
        indexed = sorted(enumerate(cogon.sem), key=lambda x: x[1], reverse=True)
        return [(AXES[i]["name"], round(v, 3)) for i, v in indexed[:n]]

    def _cosine_dist(self, c1: Cogon, c2: Cogon) -> float:
        dot = sum(a * b for a, b in zip(c1.sem, c2.sem))
        n1 = math.sqrt(sum(a ** 2 for a in c1.sem)) + 1e-9
        n2 = math.sqrt(sum(b ** 2 for b in c2.sem)) + 1e-9
        return 1.0 - dot / (n1 * n2)

    # ── tracking ───────────────────────────────────────────────────────────────

    def record(self, sender: str, text: str, cogon: Cogon,
               intent: str = "ASSERT", round_num: int = 0) -> None:
        chars = len(text.encode("utf-8"))
        tokens = self._estimate_tokens(text)
        urgency = cogon.sem[22] if len(cogon.sem) > 22 else 0.5

        self.m.total_messages += 1
        self.m.total_chars += chars
        self.m.text_bytes_total += chars
        self.m.total_tokens_raw_estimate += tokens
        self.m.cogon_vectors_total += 1

        if intent == "DELTA":
            self.m.delta_intent_count += 1
        else:
            self.m.assert_intent_count += 1

        # Agent
        s = self.m.agent_stats.get(sender)
        if s:
            s["messages"] += 1
            s["chars"] += chars
            s["urgency_sum"] += urgency
            s["avg_urgency"] = s["urgency_sum"] / s["messages"]
            if intent == "DELTA":
                s["delta_count"] += 1
            else:
                s["assert_count"] += 1

        # Timeline
        self.m.timeline.append({
            "round": round_num,
            "sender": sender,
            "intent": intent,
            "preview": text[:80] + ("..." if len(text) > 80 else ""),
            "tokens_est": tokens,
            "urgency": round(urgency, 3),
            "top_axes": self._top_axes(cogon),
        })

    def track_concept(self, concept: str, cogon: Cogon, sender: str) -> None:
        self.m.concept_history[concept].append({
            "sender": sender,
            "ts": time.time(),
            "top_axes": self._top_axes(cogon, 5),
        })

    def track_drift(self, c1: Cogon, c2: Cogon) -> float:
        d = self._cosine_dist(c1, c2)
        self.m.semantic_drift_sum += d
        self.m.semantic_drift_count += 1
        return d

    def add_raw(self, topic: str, kind: str, content: Any) -> Dict:
        obj = {
            "id": str(uuid.uuid4())[:8],
            "topic": topic,
            "type": kind,
            "content": content,
            "ts": datetime.now().isoformat(),
        }
        self.m.raw_objects.append(obj)
        return obj

    def finalize_convergence(self, agents: List) -> None:
        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                ai, aj = agents[i], agents[j]
                if ai.history and aj.history:
                    d = self._cosine_dist(ai.history[-1], aj.history[-1])
                    self.m.final_pairwise_distances.append(
                        {"pair": f"{ai.name}↔{aj.name}", "dist": round(d, 4)}
                    )

    # ── report ─────────────────────────────────────────────────────────────────

    def print_report(self) -> Dict:
        m = self.m
        cogon_bytes = m.cogon_vectors_total * FIXED_DIMS * 4  # 128 bytes/vetor
        compression = m.text_bytes_total / cogon_bytes if cogon_bytes > 0 else 0
        avg_drift = (m.semantic_drift_sum / m.semantic_drift_count
                     if m.semantic_drift_count > 0 else 0)
        avg_conv = (1.0 - sum(d["dist"] for d in m.final_pairwise_distances) /
                    len(m.final_pairwise_distances)
                    if m.final_pairwise_distances else 0)

        sep = "═" * 70
        print(f"\n{sep}")
        print("   1337 METRICS REPORT — CONSCIOUSNESS DEBATE")
        print(sep)

        print(f"\n{'─'*35} VOLUME {'─'*26}")
        print(f"  Total messages           : {m.total_messages}")
        print(f"  Characters (raw text)    : {m.text_bytes_total:,} bytes")
        print(f"  COGON vectors created    : {m.cogon_vectors_total}")
        print(f"  Bytes via 1337           : {cogon_bytes:,} bytes  ({FIXED_DIMS}×f32/vector)")
        print(f"  Estimated tokens (input) : {m.total_tokens_raw_estimate:,}")

        print(f"\n{'─'*35} COMPRESSION {'─'*22}")
        print(f"  Text → COGON             : {compression:.2f}x")
        print(f"  (text/{cogon_bytes} bytes → vectors/{cogon_bytes} bytes)")
        pct_saved = (1 - 1 / compression) * 100 if compression > 1 else 0
        print(f"  Estimated reduction      : {pct_saved:.1f}%")
        print(f"  DELTA INTENTs            : {m.delta_intent_count}  (reused content)")
        print(f"  ASSERT INTENTs           : {m.assert_intent_count}")

        print(f"\n{'─'*35} SEMANTICS {'─'*24}")
        print(f"  Average semantic drift   : {avg_drift:.4f}  (0=identical, 1=orthogonal)")
        print(f"  Final convergence        : {avg_conv:.2%}")
        print(f"\n  Pairwise distances (final state):")
        for p in m.final_pairwise_distances:
            bar_len = int(p["dist"] * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"    {p['pair']:25} │{bar}│ {p['dist']:.4f}")

        print(f"\n{'─'*35} BY AGENT {'─'*25}")
        for name, s in m.agent_stats.items():
            efficiency = s["delta_count"] / max(s["messages"], 1) * 100
            print(f"  {name:14} {s['messages']:3} msgs | "
                  f"avg urgency: {s['avg_urgency']:.2f} | "
                  f"DELTA: {efficiency:.0f}%")

        print(f"\n{'─'*35} CONCEPTS {'─'*25}")
        for concept, hist in m.concept_history.items():
            print(f"  {concept:20} : {len(hist)} refinements")

        print(f"\n{'─'*35} RAW OBJECTS {'─'*22}")
        print(f"  Total RAW created : {len(m.raw_objects)}")
        for obj in m.raw_objects[:8]:
            print(f"    [{obj['id']}] {obj['type']:10} — {obj['topic']}")
        if len(m.raw_objects) > 8:
            print(f"    ... and {len(m.raw_objects)-8} more")

        return {
            "session_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "topic": "Debate da Consciência — Kant · Nietzsche · Schopenhauer · Hegel",
            "summary": {
                "total_messages": m.total_messages,
                "text_bytes": m.text_bytes_total,
                "cogon_bytes": cogon_bytes,
                "compression_ratio": round(compression, 4),
                "pct_saved": round(pct_saved, 1),
                "tokens_estimated": m.total_tokens_raw_estimate,
                "delta_intents": m.delta_intent_count,
                "assert_intents": m.assert_intent_count,
                "avg_semantic_drift": round(avg_drift, 4),
                "final_convergence": round(avg_conv, 4),
            },
            "agent_stats": m.agent_stats,
            "concept_evolution": {
                c: [
                    {"sender": h["sender"], "axes": h["top_axes"]}
                    for h in hist
                ]
                for c, hist in m.concept_history.items()
            },
            "pairwise_distances": m.final_pairwise_distances,
            "raw_objects": [
                {"id": o["id"], "type": o["type"], "topic": o["topic"]}
                for o in m.raw_objects
            ],
            "timeline": m.timeline,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def _heatmap(cogon: Cogon, n: int = 10) -> str:
    top = sorted(enumerate(cogon.sem), key=lambda x: x[1], reverse=True)[:n]
    lines = []
    for idx, val in top:
        if val < 0.2:
            break
        ax = AXES[idx]
        bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
        lines.append(f"    {ax['code']:3} {ax['name']:22} │{bar}│ {val:.2f}")
    return "\n".join(lines) or "    (no axis > 0.2)"


def run_consciencia_simulation(backend_name: str = "deepseek", rounds: int = 25) -> Dict:
    if rounds < 25:
        print(f"  ⚠  rounds={rounds} < 25 minimum — adjusting to 25.")
        rounds = 25

    print("=" * 70)
    print("   1337 — CONSCIOUSNESS DEBATE")
    print("   Kant · Nietzsche · Schopenhauer · Hegel · Pinóquio · Bolsonaro · Alan")
    print("=" * 70)
    print(f"\n  Backend : {backend_name}")
    print(f"  Agents  : {', '.join(a['name'] for a in CONSCIENCIA_SCENARIO['agents'])}")
    print(f"  Rounds  : {rounds}")
    print(f"  Tracked concepts: {', '.join(CONSCIENCIA_SCENARIO['concepts'])}")
    print()

    # ── setup ─────────────────────────────────────────────────────────────────
    backend = create_backend(backend_name)
    rust = RustBridge()
    monitor = DebateMonitor([a["name"] for a in CONSCIENCIA_SCENARIO["agents"]])
    net = Network1337(rust, backend)

    for ad in CONSCIENCIA_SCENARIO["agents"]:
        net.add_agent(ad["name"], ad["persona"])
        print(f"  ✓ {ad['name']} joined the debate")

    print(f"\n  Rust: {'active (' + rust.mode + ')' if rust.available() else 'pure Python'}")

    # ── handshake ─────────────────────────────────────────────────────────────
    print("\n  Handshake C5 (R20 — COGON_ZERO)...")
    net.handshake()

    # ── estímulo inicial ──────────────────────────────────────────────────────
    stimulus = CONSCIENCIA_SCENARIO["stimulus"]
    print(f"\n{'─'*70}")
    print("  MEDIATOR — Initial stimulus:")
    print(f'  "{stimulus[:120]}..."')
    print(f"{'─'*70}")

    stimulus_msg = net.human.text_to_msg(stimulus, "BROADCAST")
    monitor.record("Mediador", stimulus, stimulus_msg.payload, "ASSERT", 0)
    monitor.add_raw("Questão inicial", "EVIDENCE",
                    {"texto": stimulus[:200], "round": 0})
    net._log_msg(stimulus_msg, "Mediador", "BROADCAST")
    net._render_msg(stimulus_msg, "Mediador", "BROADCAST")

    # ── discursos iniciais (round 0) ──────────────────────────────────────────
    print(f"\n{'═'*70}")
    print("  INITIAL POSITIONS — Round 0")
    print(f"{'═'*70}")

    for agent in net.agents.values():
        responses = agent.receive_and_respond(stimulus_msg, net.all_participants)
        for resp in responses:
            text = resp.surface.get("_text", "")
            monitor.record(agent.name, text, resp.payload, resp.intent, 0)
            monitor.track_concept("Consciência", resp.payload, agent.name)

            raw = monitor.add_raw(
                f"Posição inicial de {agent.name}", "EVIDENCE",
                {"speaker": agent.name, "text": text[:150]}
            )
            net._log_msg(resp, agent.name, net._resolve_name(resp.receiver))
            net._render_msg(resp, agent.name, net._resolve_name(resp.receiver))

    # ── dialética — rounds ────────────────────────────────────────────────────
    print(f"\n{'═'*70}")
    print("  DIALECTIC — Questioning and Refinement")
    print(f"{'═'*70}")

    agent_list = list(net.agents.values())
    provocations = CONSCIENCIA_SCENARIO["provocations"]
    prev_cogons: Dict[str, Cogon] = {}

    for round_num in range(1, rounds + 1):
        print(f"\n{'─'*70}")
        print(f"  ROUND {round_num:02d}/{rounds:02d}", end="")

        # Injetar provocação do mediador a cada 5 rounds
        if round_num % 5 == 0:
            prov_idx = (round_num // 5 - 1) % len(provocations)
            provocation = provocations[prov_idx]
            print(f"  [MEDIATOR injects provocation]")
            print(f"  \"{provocation[:80]}...\"")
            prov_msg = net.human.text_to_msg(provocation, "BROADCAST")
            monitor.record("Mediador", provocation, prov_msg.payload, "ASSERT", round_num)
            monitor.add_raw(f"Provocação round {round_num}", "EVIDENCE",
                            {"texto": provocation[:150]})
            last_stimulus = prov_msg
        else:
            print()
            last_stimulus = None

        print(f"{'─'*70}")

        # Cada agente responde ao anterior (rotação circular)
        for i, agent in enumerate(agent_list):
            prev_agent = agent_list[(i - 1) % len(agent_list)]

            # Escolhe qual mensagem responder
            if last_stimulus and i == 0:
                src_msg = last_stimulus
            elif prev_agent.msg_log:
                src_msg = prev_agent.msg_log[-1]
            else:
                continue

            # Drift semântico
            if agent.history and src_msg.payload:
                drift = monitor.track_drift(agent.history[-1], src_msg.payload)

            responses = agent.receive_and_respond(src_msg, net.all_participants)

            for resp in responses:
                text = resp.surface.get("_text", "")
                monitor.record(agent.name, text, resp.payload, resp.intent, round_num)

                # Rastrear conceitos mencionados
                lower = text.lower()
                for concept in CONSCIENCIA_SCENARIO["concepts"]:
                    if concept.lower().split("(")[0].strip() in lower:
                        monitor.track_concept(concept, resp.payload, agent.name)

                # Criar RAW para objeções
                if any(kw in lower for kw in ["mas", "erro", "falso", "equívoco",
                                               "contradição", "objeto", "critico"]):
                    monitor.add_raw(
                        f"Objeção de {agent.name} → {prev_agent.name}",
                        "EVIDENCE",
                        {"round": round_num, "excerpt": text[:120]},
                    )

                net._log_msg(resp, agent.name, net._resolve_name(resp.receiver))
                net._render_msg(resp, agent.name, net._resolve_name(resp.receiver))

    # ── análise final ─────────────────────────────────────────────────────────
    print(f"\n{'═'*70}")
    print("  HEATMAPS — Final State of Each Philosopher")
    print(f"{'═'*70}")

    for agent in net.agents.values():
        if agent.history:
            print(f"\n  [{agent.name}]")
            print(_heatmap(agent.history[-1]))

    monitor.finalize_convergence(list(net.agents.values()))

    # ── relatório ─────────────────────────────────────────────────────────────
    report = monitor.print_report()

    # Salvar
    fname = f"consciencia_debate_{int(time.time())}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n  💾 Full report saved: {fname}")
    print(f"\n{'═'*70}")
    print(f"  Simulation complete — {rounds} rounds | {report['summary']['total_messages']} messages")
    print(f"  1337 compression: {report['summary']['compression_ratio']}x "
          f"({report['summary']['pct_saved']}% reduction)")
    print(f"{'═'*70}\n")

    return report


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="1337 — Consciousness Debate (Kant · Nietzsche · Schopenhauer · Hegel)"
    )
    parser.add_argument(
        "--backend",
        choices=["deepseek", "anthropic", "mock"],
        default="deepseek",
        help="LLM backend (default: deepseek)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=25,
        help="Dialectic rounds, minimum 25 (default: 25)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Alternative output JSON file",
    )
    args = parser.parse_args()

    # Verificar API keys
    if args.backend == "deepseek" and not os.environ.get("DEEPSEEK_API_KEY"):
        print("⚠  DEEPSEEK_API_KEY not set. Using mock.")
        args.backend = "mock"

    if args.backend == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠  ANTHROPIC_API_KEY not set. Using mock.")
        args.backend = "mock"

    try:
        report = run_consciencia_simulation(args.backend, args.rounds)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Report saved to: {args.output}")

    except KeyboardInterrupt:
        print("\n\n  ⛔ Simulation interrupted by user")
    except Exception as e:
        print(f"\n  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
