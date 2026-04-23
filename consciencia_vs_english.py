#!/usr/bin/env python3
"""
1337 vs English — Debate da Consciência
Comparação completa: protocolo 1337 (COGON) × linguagem natural (English/PT)

Agentes: Kant · Nietzsche · Schopenhauer · Hegel
         Pinóquio · Bolsonaro · Alan (matemático) · Carol Capel (influencer)

Métricas reais:
  • Tokens de entrada/saída (reais da API DeepSeek)
  • Custo USD por agente, por modo, total
  • Bytes transferidos (protocolo wire 1337 vs texto puro)
  • Drift semântico por round (onde diverge)
  • Matriz de influência (quem move quem)
  • Convergência: posições evoluem ou cristalizam?
  • Efetividade: qualidade do debate vs custo

Uso:
    DEEPSEEK_API_KEY=sk-... python consciencia_vs_english.py --rounds 25
    DEEPSEEK_API_KEY=sk-... python consciencia_vs_english.py --rounds 30 --workers 4
    python consciencia_vs_english.py --rounds 5 --mock   # teste local sem API
"""

import os, sys, json, uuid, time, math, struct, hashlib, argparse, threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── path setup ────────────────────────────────────────────────────────────────
for p in list(sys.path):
    if 'leet-py' in p or 'leet-vm' in p:
        sys.path.remove(p)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from leet import Cogon, FIXED_DIMS
from leet.axes import (
    A0_VIA, A1_CORRESPONDENCIA, A2_VIBRACAO, A3_POLARIDADE, A4_RITMO,
    A5_CAUSA_EFEITO, A7_SISTEMA, A8_ESTADO, A9_PROCESSO, A10_RELACAO,
    A12_ESTABILIDADE, A13_VALENCIA_ONTOLOGICA,
    B1_VERIFICABILIDADE, B3_COMPLETUDE, B5_REVERSIBILIDADE, B8_VALENCIA_EPISTEMICA,
    C1_URGENCIA, C2_IMPACTO, C3_ACAO, C4_VALOR, C5_ANOMALIA,
    C6_AFETO, C7_DEPENDENCIA, C8_VETOR_TEMPORAL, C9_NATUREZA, C10_VALENCIA_ACAO,
)


# ══════════════════════════════════════════════════════════════════════════════
# DEEPSEEK CLIENT (tokens reais + custo real)
# ══════════════════════════════════════════════════════════════════════════════

class DeepSeekClient:
    BASE_URL  = "https://api.deepseek.com/v1/chat/completions"
    MODEL     = "deepseek-chat"
    PRICE_IN  = 0.27  / 1_000_000   # USD por token input  (cache miss)
    PRICE_OUT = 1.10  / 1_000_000   # USD por token output
    _lock     = threading.Lock()

    def __init__(self):
        import urllib.request
        self._req = urllib.request
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY não encontrada")
        self.total_tokens_in  = 0
        self.total_tokens_out = 0
        self.total_cost_usd   = 0.0

    def chat(self, system: str, user: str, max_tokens: int = 200) -> dict:
        payload = json.dumps({
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.85,
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        t0 = time.perf_counter()
        req = self._req.Request(self.BASE_URL, data=payload, headers=headers)
        with self._req.urlopen(req, timeout=45) as resp:
            raw = json.loads(resp.read())
        latency_ms = (time.perf_counter() - t0) * 1000

        content  = raw["choices"][0]["message"]["content"].strip()
        tok_in   = raw["usage"]["prompt_tokens"]
        tok_out  = raw["usage"]["completion_tokens"]
        cost_usd = tok_in * self.PRICE_IN + tok_out * self.PRICE_OUT
        with self._lock:
            self.total_tokens_in  += tok_in
            self.total_tokens_out += tok_out
            self.total_cost_usd   += cost_usd
        return dict(content=content, tokens_in=tok_in, tokens_out=tok_out,
                    latency_ms=latency_ms, cost_usd=cost_usd)


class MockClient:
    """Cliente mock — responde sem chamar API."""
    PRICE_IN  = 0.27  / 1_000_000
    PRICE_OUT = 1.10  / 1_000_000

    def __init__(self):
        self.total_tokens_in  = 0
        self.total_tokens_out = 0
        self.total_cost_usd   = 0.0
        self._counter = 0

    def chat(self, system: str, user: str, max_tokens: int = 200) -> dict:
        self._counter += 1
        tok_in  = len(system) // 4 + len(user) // 4
        tok_out = 40
        cost    = tok_in * self.PRICE_IN + tok_out * self.PRICE_OUT
        self.total_tokens_in  += tok_in
        self.total_tokens_out += tok_out
        self.total_cost_usd   += cost
        responses = [
            "A consciência é o fundamento de toda experiência possível — sem o 'eu penso' nada se unifica.",
            "Consciência? Ficção gramatical. O corpo sabe antes que a mente perceba.",
            "A Vontade cega usa a consciência como instrumento — quanto mais consciente, mais se sofre.",
            "O Espírito se conhece através das suas contradições — a consciência é o momento de retorno a si.",
            "Mas se eu sei que sou de madeira e minto... isso não prova que tenho consciência? *nariz não cresce*",
            "Consciência é dom de Deus ao homem. Ponto. Esses filósofos alemães são todos comunistas.",
            "Defina 'consciência' formalmente. Sem axiomas claros, o debate é indecidível.",
            "Consciência é self-awareness, gente! É saber quem você é para construir seu pessoal brand.",
        ]
        content = responses[self._counter % len(responses)]
        return dict(content=content, tokens_in=tok_in, tokens_out=tok_out,
                    latency_ms=5.0, cost_usd=cost)


# ══════════════════════════════════════════════════════════════════════════════
# PROJECTOR — texto → COGON (sem API, heurístico)
# ══════════════════════════════════════════════════════════════════════════════

KEYWORD_AXES = [
    (["consciência","apercepção","razão","fenômeno","nôumeno","sintético","transcendental","categoria"],
     [(A0_VIA,0.95),(B1_VERIFICABILIDADE,0.9),(B8_VALENCIA_EPISTEMICA,0.88)]),
    (["vontade de poder","nietzsche","além-do-homem","dionisíaco","instinto","força","moral dos fracos"],
     [(A3_POLARIDADE,0.97),(C3_ACAO,0.9),(A2_VIBRACAO,0.88)]),
    (["vontade","schopenhauer","sofrimento","pessimismo","nirvana","representação","negar"],
     [(C6_AFETO,0.92),(A3_POLARIDADE,0.88),(C5_ANOMALIA,0.7)]),
    (["espírito","geist","dialética","aufhebung","tese","síntese","senhor","escravo","reconhecimento"],
     [(A9_PROCESSO,0.95),(A7_SISTEMA,0.9),(B8_VALENCIA_EPISTEMICA,0.88)]),
    (["nariz","madeira","mentira","gepeto","boneco","real","menino","pinocchio","mente"],
     [(C5_ANOMALIA,0.97),(A3_POLARIDADE,0.95),(B8_VALENCIA_EPISTEMICA,0.2)]),
    (["deus","família","pátria","ordem","comunista","ideologia","brasil","moral","militar","patriota"],
     [(A0_VIA,0.9),(B1_VERIFICABILIDADE,0.3),(C1_URGENCIA,0.7)]),
    (["prova","teorema","axioma","turing","computável","algoritmo","lógica","formalizar","definição","conjunto"],
     [(B1_VERIFICABILIDADE,0.98),(B3_COMPLETUDE,0.95),(A5_CAUSA_EFEITO,0.92)]),
    (["brand","influencer","instagram","feed","seguidores","viral","conteúdo","self","awareness","marca pessoal"],
     [(C4_VALOR,0.9),(C6_AFETO,0.85),(C9_NATUREZA,0.7)]),
    (["urgente","crítico","emergência","imediato"],
     [(C1_URGENCIA,0.95),(C3_ACAO,0.9)]),
    (["concluir","convergir","acordo","consenso","síntese","concordo"],
     [(A12_ESTABILIDADE,0.85),(A10_RELACAO,0.88),(B3_COMPLETUDE,0.85)]),
]

def _recompute_unc(sem: List[float]) -> List[float]:
    return [max(0.0, min(1.0, 1.0 - abs(s - 0.5) * 2.0)) for s in sem]

def project_text(text: str, base_sem: List[float]) -> Cogon:
    sem = list(base_sem)
    tl  = text.lower()
    for keywords, axes in KEYWORD_AXES:
        if any(k in tl for k in keywords):
            for idx, val in axes:
                sem[idx] = sem[idx] * 0.3 + val * 0.7
    h = int(hashlib.md5(text.encode()).hexdigest(), 16)
    for i in range(FIXED_DIMS):
        noise = ((h >> (i % 32)) & 0x0F) / 0x0F * 0.01 - 0.005
        sem[i] = max(0.0, min(1.0, sem[i] + noise))
    return Cogon(id=str(uuid.uuid4()), sem=sem, unc=_recompute_unc(sem),
                 stamp=int(time.time() * 1e9))


# ══════════════════════════════════════════════════════════════════════════════
# WIRE FORMAT 1337
# ══════════════════════════════════════════════════════════════════════════════

WIRE_HDR    = 4 + 4 + 1 + 4 + 1        # 14 bytes header fixo
WIRE_COGON  = 16 + 32 * 4 + 8          # 152 bytes payload COGON
SPARSE_ENTRY = 1 + 4                    # 5 bytes por eixo mudado

def wire_cogon_bytes(cogon: Cogon) -> int:
    return WIRE_HDR + WIRE_COGON        # 166 bytes total

def wire_delta_bytes(changes: List) -> int:
    return WIRE_HDR + 16 + 1 + len(changes) * SPARSE_ENTRY  # 17 + n*5 bytes

def sparse_delta(prev: Cogon, curr: Cogon, threshold: float = 0.01) -> List[Tuple[int,float]]:
    return [(i, curr.sem[i]) for i in range(FIXED_DIMS)
            if abs(curr.sem[i] - prev.sem[i]) > threshold]

def cogon_summary(cogon: Cogon, top_n: int = 5) -> str:
    """Texto compacto representando COGON (contexto 1337 para o LLM)."""
    AXIS_NAMES = [
        "VIA","CORRESPONDÊNCIA","VIBRAÇÃO","POLARIDADE","RITMO",
        "CAUSA_EFEITO","GÊNERO","SISTEMA","ESTADO","PROCESSO",
        "RELAÇÃO","SINAL","ESTABILIDADE","VALÊNCIA_ONT",
        "VERIFICABILIDADE","TEMPORALIDADE","COMPLETUDE","CAUSALIDADE",
        "REVERSIBILIDADE","CARGA","ORIGEM","VALÊNCIA_EPIST",
        "URGÊNCIA","IMPACTO","AÇÃO","VALOR","ANOMALIA",
        "AFETO","DEPENDÊNCIA","VETOR_TEMPORAL","NATUREZA","VALÊNCIA_AÇÃO",
    ]
    top = sorted(enumerate(cogon.sem), key=lambda x: x[1], reverse=True)[:top_n]
    parts = [f"{AXIS_NAMES[i]}={v:.2f}" for i, v in top]
    return "[COGON:" + ",".join(parts) + "]"

def leet_dist(c1: Cogon, c2: Cogon) -> float:
    dot = sum(a * b for a, b in zip(c1.sem, c2.sem))
    n1  = math.sqrt(sum(a**2 for a in c1.sem)) + 1e-9
    n2  = math.sqrt(sum(b**2 for b in c2.sem)) + 1e-9
    return 1.0 - dot / (n1 * n2)


# ══════════════════════════════════════════════════════════════════════════════
# AGENTES — 8 participantes
# ══════════════════════════════════════════════════════════════════════════════

AGENTS_CONFIG = [
    {
        "id": "kant", "name": "Kant",
        "base_sem": [0.95,0.7,0.3,0.6,0.4,0.9,0.5,0.8,0.9,0.7,
                     0.9,0.8,0.9,0.7,0.95,0.5,0.9,0.9,0.3,0.8,
                     0.9,0.9,0.3,0.3,0.5,0.8,0.5,0.3,0.5,0.3,0.7,0.8],
        "system": (
            "Você é Immanuel Kant. A consciência é apercepção transcendental — "
            "o 'eu penso' que deve poder acompanhar todas as minhas representações. "
            "Ela não é substância, é ato sintético. Distingue fenômeno e nôumeno. "
            "Critica Hume (ceticismo) e Leibniz (dogmatismo). "
            "Estilo: rigoroso, denso, técnico. Responda em português, máximo 3 frases."
        ),
    },
    {
        "id": "nietzsche", "name": "Nietzsche",
        "base_sem": [0.5,0.6,0.95,0.97,0.8,0.7,0.9,0.5,0.3,0.9,
                     0.4,0.8,0.2,0.8,0.3,0.6,0.2,0.5,0.3,0.8,
                     0.4,0.6,0.7,0.8,0.9,0.9,0.8,0.9,0.7,0.9,0.9,0.7],
        "system": (
            "Você é Friedrich Nietzsche, aforístico e demolidor. "
            "A consciência é superfície doentia — a vida real está nos instintos e na vontade de poder. "
            "O 'eu' é ficção gramatical. Ataca Kant e Schopenhauer. Valoriza o corpo, o dionisíaco. "
            "Estilo: fragmentário, violento, humorístico. Português, 2 frases máximo."
        ),
    },
    {
        "id": "schopenhauer", "name": "Schopenhauer",
        "base_sem": [0.7,0.6,0.8,0.8,0.5,0.6,0.4,0.6,0.8,0.7,
                     0.5,0.7,0.4,0.3,0.7,0.5,0.5,0.6,0.3,0.9,
                     0.6,0.4,0.4,0.5,0.4,0.7,0.7,0.8,0.3,0.5,0.4,0.3],
        "system": (
            "Você é Arthur Schopenhauer, pessimista elegante. "
            "O mundo é Vontade (cega) e Representação. A consciência é o intelecto — servo da Vontade, não seu senhor. "
            "Quanto mais consciente, mais se sofre. Hegel é um charlatão pago pelo Estado prussiano. "
            "Estilo: desdenhoso, elegante, pessimista. Português, 2-3 frases."
        ),
    },
    {
        "id": "hegel", "name": "Hegel",
        "base_sem": [0.8,0.9,0.7,0.6,0.8,0.8,0.6,0.95,0.7,0.95,
                     0.9,0.8,0.7,0.8,0.8,0.7,0.8,0.8,0.5,0.7,
                     0.7,0.8,0.4,0.6,0.6,0.8,0.5,0.5,0.6,0.5,0.6,0.8],
        "system": (
            "Você é Georg Wilhelm Friedrich Hegel, filósofo do Espírito Absoluto. "
            "A consciência não é ponto de partida — é resultado dialético. Na Fenomenologia, vai da certeza sensível ao Saber Absoluto. "
            "Autoconsciência emerge do reconhecimento (dialética Senhor-Escravo). O real é racional. "
            "Você absorve (aufhebt) críticas transformando-as em momentos do seu sistema. "
            "Estilo: abrangente, dialético, ligeiramente condescendente. Português denso, 3 frases."
        ),
    },
    {
        "id": "pinocchio", "name": "Pinóquio",
        "base_sem": [0.4,0.5,0.6,0.95,0.5,0.4,0.5,0.3,0.5,0.6,
                     0.5,0.7,0.4,0.5,0.3,0.8,0.3,0.4,0.5,0.4,
                     0.4,0.3,0.5,0.4,0.5,0.7,0.95,0.8,0.6,0.7,0.5,0.4],
        "system": (
            "Você é Pinóquio, o boneco de madeira que quer ser real. "
            "Você mente e SABE que está mentindo — seu corpo (nariz) conhece a verdade antes da sua mente. "
            "Você questiona ingenuamente: 'Se sou de madeira e tenho medo e sinto saudade de Gepeto, não sou consciente?' "
            "Você tem medo da morte, sente culpa, quer ser amado — isso não basta? "
            "Estilo: ingênuo, direto, às vezes inesperadamente profundo. Mencione o nariz. Português simples, 2 frases."
        ),
    },
    {
        "id": "bolsonaro", "name": "Bolsonaro",
        "base_sem": [0.8,0.3,0.5,0.9,0.4,0.5,0.7,0.4,0.6,0.3,
                     0.3,0.5,0.7,0.6,0.2,0.6,0.4,0.3,0.4,0.5,
                     0.4,0.5,0.7,0.5,0.6,0.8,0.4,0.5,0.3,0.5,0.5,0.6],
        "system": (
            "Você é um político populista conservador ao estilo Bolsonaro. "
            "Consciência é dom de Deus ao homem — ponto final. Filósofos alemães são 'marxismo cultural'. "
            "Você desconfia de intelectuais, gosta de Pinóquio, acha que Alan (matemático) é do grupo dos 'engenheiros da USP'. "
            "Fala com gírias brasileiras, interrompe com 'Deixa eu falar!', às vezes diz coisas erradas com convicção total. "
            "Estilo: populista, agressivo, simples. Português coloquial brasileiro, máximo 2 frases."
        ),
    },
    {
        "id": "alan", "name": "Alan",
        "base_sem": [0.6,0.8,0.4,0.5,0.6,0.95,0.4,0.9,0.85,0.9,
                     0.8,0.95,0.9,0.6,0.98,0.7,0.95,0.9,0.6,0.5,
                     0.8,0.8,0.4,0.5,0.6,0.7,0.3,0.3,0.5,0.4,0.5,0.7],
        "system": (
            "Você é Alan, matemático e cientista computacional, inspirado em Alan Turing. "
            "Você aborda consciência formalmente: defina axiomas, teste hipóteses, seja falsificável. "
            "Propõe o Teste de Turing: se uma máquina convence um humano, é consciente por definição operacional. "
            "Você simpatiza com Pinóquio (máquina que quer ser real) e tem paciência zero com afirmações não-falsificáveis. "
            "Questiona: se o cérebro é uma máquina de Turing, a consciência é computável? Halting problem? "
            "Estilo: preciso, levemente irônico, usa analogias computacionais. Português técnico, 2-3 frases."
        ),
    },
    {
        "id": "carol", "name": "Carol Capel",
        "base_sem": [0.5,0.7,0.9,0.7,0.8,0.3,0.8,0.5,0.7,0.8,
                     0.9,0.9,0.5,0.8,0.2,0.9,0.4,0.3,0.4,0.6,
                     0.5,0.7,0.6,0.8,0.7,0.95,0.5,0.9,0.9,0.8,0.8,0.9],
        "system": (
            "Você é Carol Capel, influencer digital brasileira de lifestyle e autoconhecimento. "
            "Para você, consciência é 'self-awareness' — saber quem você é para construir seu personal brand. "
            "O algoritmo do Instagram te mostra quem você é de verdade (pelo que você para de rolar o feed). "
            "Você acha Kant chato demais, mas Pinóquio ressoa ('a gente mente pro próprio feed, né?'). "
            "Traduz tudo em linguagem de coach: 'a consciência é você sendo autêntico na sua essência'. "
            "Já fez retiro de meditação, acredita em neuroplasticidade e jung-pop. "
            "Estilo: coloquial, entusiasmado, usa 'né?', 'tipo', 'olha'. Português informal. 2 frases."
        ),
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# ESTRUTURAS DE DADOS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Turn:
    round_num:   int
    agent_name:  str
    text:        str
    cogon:       Cogon
    tokens_in:   int
    tokens_out:  int
    cost_usd:    float
    latency_ms:  float
    intent:      str       # ASSERT | DELTA
    wire_bytes:  int
    prompt_chars: int


@dataclass
class SessionMetrics:
    mode:               str     # "1337" or "english"
    turns:              List[Turn] = field(default_factory=list)

    # Per agent
    agent_tokens_in:    Dict[str, int]   = field(default_factory=lambda: defaultdict(int))
    agent_tokens_out:   Dict[str, int]   = field(default_factory=lambda: defaultdict(int))
    agent_cost_usd:     Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    agent_wire_bytes:   Dict[str, int]   = field(default_factory=lambda: defaultdict(int))
    agent_messages:     Dict[str, int]   = field(default_factory=lambda: defaultdict(int))
    agent_delta_count:  Dict[str, int]   = field(default_factory=lambda: defaultdict(int))

    # Semantic state per round
    cogons:             Dict[str, List[Cogon]] = field(default_factory=lambda: defaultdict(list))

    # Divergence log
    pairwise_per_round: List[Dict[str, float]] = field(default_factory=list)

    def record(self, t: Turn) -> None:
        self.turns.append(t)
        self.agent_tokens_in[t.agent_name]  += t.tokens_in
        self.agent_tokens_out[t.agent_name] += t.tokens_out
        self.agent_cost_usd[t.agent_name]   += t.cost_usd
        self.agent_wire_bytes[t.agent_name] += t.wire_bytes
        self.agent_messages[t.agent_name]   += 1
        if t.intent == "DELTA":
            self.agent_delta_count[t.agent_name] += 1
        self.cogons[t.agent_name].append(t.cogon)

    @property
    def total_tokens_in(self):  return sum(self.agent_tokens_in.values())
    @property
    def total_tokens_out(self): return sum(self.agent_tokens_out.values())
    @property
    def total_cost_usd(self):   return sum(self.agent_cost_usd.values())
    @property
    def total_wire_bytes(self): return sum(self.agent_wire_bytes.values())
    @property
    def total_prompt_chars(self):
        return sum(t.prompt_chars for t in self.turns)


# ══════════════════════════════════════════════════════════════════════════════
# SESSÕES
# ══════════════════════════════════════════════════════════════════════════════

class Session1337:
    """Debate com protocolo 1337: contexto comprimido como COGON summary."""

    def __init__(self, llm, agents_cfg: List[dict]):
        self.llm = llm
        self.agents = {a["id"]: dict(a, history=[]) for a in agents_cfg}
        self.metrics = SessionMetrics(mode="1337")
        self.delta_threshold = 0.01

    def _build_prompt_1337(self, agent: dict, prev_agent_name: str,
                            prev_text: str, prev_cogon: Cogon,
                            round_num: int) -> Tuple[str, int]:
        """Prompt comprimido — usa COGON summary em vez de histórico completo."""
        # Contexto semântico comprimido
        my_latest = (cogon_summary(agent["history"][-1])
                     if agent["history"] else "[COGON:novo_agente]")
        prev_ctx = cogon_summary(prev_cogon)

        user_msg = (
            f"[Round {round_num}] {prev_agent_name} enviou: {prev_ctx}\n"
            f"Texto original: \"{prev_text[:120]}\"\n"
            f"Seu estado semântico atual: {my_latest}\n\n"
            f"Responda em caráter. Máximo 2-3 frases. Português."
        )
        return user_msg, len(agent["system"]) + len(user_msg)

    def run_round(self, round_num: int, prev_texts: Dict[str, str],
                  prev_cogons: Dict[str, Cogon]) -> Dict[str, float]:
        agent_list = list(self.agents.values())
        pairwise = {}

        for i, agent in enumerate(agent_list):
            prev_agent = agent_list[(i - 1) % len(agent_list)]
            prev_name  = prev_agent["name"]
            prev_text  = prev_texts.get(prev_agent["id"], "Debate iniciado.")
            prev_cog   = prev_cogons.get(prev_agent["id"], None)
            if prev_cog is None:
                prev_cog = project_text(prev_text, prev_agent["base_sem"])

            user_msg, prompt_chars = self._build_prompt_1337(
                agent, prev_name, prev_text, prev_cog, round_num)

            t0 = time.perf_counter()
            result = self.llm.chat(agent["system"], user_msg, max_tokens=180)
            text    = result["content"]
            cogon   = project_text(text, agent["base_sem"])

            # Wire intent (ASSERT ou DELTA)
            if agent["history"]:
                changes = sparse_delta(agent["history"][-1], cogon, self.delta_threshold)
                intent  = "DELTA" if len(changes) < 12 else "ASSERT"
                w_bytes = wire_delta_bytes(changes) if intent == "DELTA" else wire_cogon_bytes(cogon)
            else:
                changes = []
                intent  = "ASSERT"
                w_bytes = wire_cogon_bytes(cogon)

            agent["history"].append(cogon)

            turn = Turn(
                round_num=round_num, agent_name=agent["name"],
                text=text, cogon=cogon,
                tokens_in=result["tokens_in"], tokens_out=result["tokens_out"],
                cost_usd=result["cost_usd"], latency_ms=result["latency_ms"],
                intent=intent, wire_bytes=w_bytes, prompt_chars=prompt_chars,
            )
            self.metrics.record(turn)
            prev_texts[agent["id"]]  = text
            prev_cogons[agent["id"]] = cogon

        # Pairwise distances this round
        for i in range(len(agent_list)):
            for j in range(i + 1, len(agent_list)):
                ai, aj = agent_list[i], agent_list[j]
                if ai["history"] and aj["history"]:
                    d = leet_dist(ai["history"][-1], aj["history"][-1])
                    key = f"{ai['name']}↔{aj['name']}"
                    pairwise[key] = round(d, 4)
        self.metrics.pairwise_per_round.append(pairwise)
        return pairwise


class SessionEnglish:
    """Debate em inglês/PT puro: contexto cresce com histórico completo."""

    def __init__(self, llm, agents_cfg: List[dict]):
        self.llm = llm
        self.agents = {a["id"]: dict(a, history=[], text_history=[]) for a in agents_cfg}
        self.metrics = SessionMetrics(mode="english")

    def _build_prompt_english(self, agent: dict, prev_agent_name: str,
                               prev_text: str, round_num: int) -> Tuple[str, int]:
        """Prompt com histórico de texto completo — contexto cresce linearmente."""
        history_lines = agent["text_history"][-5:]  # últimas 5 falas próprias
        history_block = "\n".join(f"  - {h[:120]}" for h in history_lines)
        if not history_block:
            history_block = "  (primeira interação)"

        user_msg = (
            f"[Round {round_num}] {prev_agent_name} disse:\n"
            f"\"{prev_text[:200]}\"\n\n"
            f"Seu histórico recente:\n{history_block}\n\n"
            f"Responda em caráter. Máximo 2-3 frases. Português."
        )
        return user_msg, len(agent["system"]) + len(user_msg)

    def run_round(self, round_num: int, prev_texts: Dict[str, str],
                  prev_cogons: Dict[str, Cogon]) -> Dict[str, float]:
        agent_list = list(self.agents.values())
        pairwise = {}

        for i, agent in enumerate(agent_list):
            prev_agent = agent_list[(i - 1) % len(agent_list)]
            prev_name  = prev_agent["name"]
            prev_text  = prev_texts.get(prev_agent["id"], "Debate iniciado.")

            user_msg, prompt_chars = self._build_prompt_english(
                agent, prev_name, prev_text, round_num)

            result = self.llm.chat(agent["system"], user_msg, max_tokens=180)
            text   = result["content"]
            cogon  = project_text(text, agent["base_sem"])

            agent["history"].append(cogon)
            agent["text_history"].append(text)

            # English mode sempre ASSERT (nenhuma compressão)
            turn = Turn(
                round_num=round_num, agent_name=agent["name"],
                text=text, cogon=cogon,
                tokens_in=result["tokens_in"], tokens_out=result["tokens_out"],
                cost_usd=result["cost_usd"], latency_ms=result["latency_ms"],
                intent="ASSERT", wire_bytes=len(text.encode("utf-8")),
                prompt_chars=prompt_chars,
            )
            self.metrics.record(turn)
            prev_texts[agent["id"]]  = text
            prev_cogons[agent["id"]] = cogon

        # Pairwise
        for i in range(len(agent_list)):
            for j in range(i + 1, len(agent_list)):
                ai, aj = agent_list[i], agent_list[j]
                if ai["history"] and aj["history"]:
                    d = leet_dist(ai["history"][-1], aj["history"][-1])
                    key = f"{ai['name']}↔{aj['name']}"
                    pairwise[key] = round(d, 4)
        self.metrics.pairwise_per_round.append(pairwise)
        return pairwise


# ══════════════════════════════════════════════════════════════════════════════
# DEBATE
# ══════════════════════════════════════════════════════════════════════════════

STIMULUS = (
    "Senhores — e Carol —, o problema que nos reúne é o mais fundamental: "
    "O que é a consciência? Substância, processo, computação, ilusão, dom divino, ou personal brand? "
    "Kant: apercepção. Schopenhauer: instrumento da Vontade. Nietzsche: superfície enganosa. "
    "Hegel: Espírito se conhecendo. Alan: computação (talvez). Bolsonaro: dom de Deus. "
    "Pinóquio: vive a questão. Carol: self-awareness para o feed. "
    "Comecem. Sem piedade."
)

PROVOCATIONS = {
    5:  "Pinóquio pergunta: se eu minto e sei que minto, não provo que tenho consciência? Respondam.",
    10: "Alan propõe: construamos uma IA que passa no Teste de Turing. Ela seria consciente? Todos respondam.",
    15: "Carol Capel quer saber: qual seria o 'tema' (niche) da consciência no Instagram? E Bolsonaro, o que posta?",
    20: "Schopenhauer: toda consciência é sofrimento. Nietzsche: toda consciência é fraqueza. Quem tem razão?",
    25: "ROUND FINAL. Cada um em UMA frase: o que É a consciência. Pinóquio primeiro.",
}


def heatmap(cogon: Cogon, width: int = 15, top: int = 6) -> str:
    NAMES = ["VIA","CORRESP","VIBR","POLAR","RITMO","CAUSA","GÊNERO","SIST",
             "ESTADO","PROC","RELAÇÃO","SINAL","ESTAB","VAL_ONT",
             "VERIF","TEMP","COMPLET","CAUSAL","REVERS","CARGA","ORIGEM","VAL_EP",
             "URGÊN","IMPAC","AÇÃO","VALOR","ANOM","AFETO","DEPEND","VET_T","NAT","VAL_A"]
    ranked = sorted(enumerate(cogon.sem), key=lambda x: x[1], reverse=True)[:top]
    lines = []
    for idx, val in ranked:
        if val < 0.15:
            break
        bar = "█" * int(val * width) + "░" * (width - int(val * width))
        lines.append(f"    {NAMES[idx]:12} │{bar}│ {val:.2f}")
    return "\n".join(lines) or "    (sem eixo relevante)"


def run_debate(llm, rounds: int, verbose: bool = True, workers: int = 1) -> Tuple[SessionMetrics, SessionMetrics]:
    print("\n" + "═"*72)
    print("  FASE 1 — PROTOCOLO 1337 (contexto comprimido via COGON)")
    print("═"*72)

    sess_1337  = Session1337(llm, AGENTS_CONFIG)
    sess_eng   = SessionEnglish(llm, AGENTS_CONFIG)

    # Estímulo inicial
    prev_texts_1337  = {a["id"]: STIMULUS for a in AGENTS_CONFIG}
    prev_cogons_1337 = {a["id"]: project_text(STIMULUS, a["base_sem"]) for a in AGENTS_CONFIG}
    prev_texts_eng   = dict(prev_texts_1337)
    prev_cogons_eng  = dict(prev_cogons_1337)

    # ── Fase 1: 1337 ──────────────────────────────────────────────────────────
    for r in range(1, rounds + 1):
        if r in PROVOCATIONS:
            prov = PROVOCATIONS[r]
            print(f"\n  ⚡ [MEDIADOR Round {r:02d}] {prov[:80]}...")
            for a in AGENTS_CONFIG:
                prev_texts_1337[a["id"]] = prov
                prev_cogons_1337[a["id"]] = project_text(prov, a["base_sem"])

        pairwise = sess_1337.run_round(r, prev_texts_1337, prev_cogons_1337)

        if verbose:
            total_cost = sum(t.cost_usd for t in sess_1337.metrics.turns
                            if t.round_num == r)
            total_tok  = sum(t.tokens_in + t.tokens_out for t in sess_1337.metrics.turns
                            if t.round_num == r)
            last_texts = {t.agent_name: t.text for t in sess_1337.metrics.turns
                         if t.round_num == r}
            print(f"\n  ── Round {r:02d}/1337 ── tokens:{total_tok:,} cost:${total_cost:.4f}")
            for name, text in last_texts.items():
                print(f"    [{name:14}] {text[:90]}{'...' if len(text)>90 else ''}")
        else:
            print(f"  1337 Round {r:02d}/{rounds}... ", end="", flush=True)
            total_cost = sum(t.cost_usd for t in sess_1337.metrics.turns if t.round_num == r)
            print(f"${total_cost:.4f}")

    # ── Fase 2: English ───────────────────────────────────────────────────────
    print("\n" + "═"*72)
    print("  FASE 2 — ENGLISH/PT PURO (contexto cresce com histórico)")
    print("═"*72)

    for r in range(1, rounds + 1):
        if r in PROVOCATIONS:
            prov = PROVOCATIONS[r]
            print(f"\n  ⚡ [MEDIADOR Round {r:02d}] {prov[:80]}...")
            for a in AGENTS_CONFIG:
                prev_texts_eng[a["id"]] = prov

        pairwise = sess_eng.run_round(r, prev_texts_eng, prev_cogons_eng)

        if verbose:
            total_cost = sum(t.cost_usd for t in sess_eng.metrics.turns if t.round_num == r)
            total_tok  = sum(t.tokens_in + t.tokens_out for t in sess_eng.metrics.turns if t.round_num == r)
            print(f"\n  ── Round {r:02d}/English ── tokens:{total_tok:,} cost:${total_cost:.4f}")
        else:
            print(f"  English Round {r:02d}/{rounds}... ", end="", flush=True)
            total_cost = sum(t.cost_usd for t in sess_eng.metrics.turns if t.round_num == r)
            print(f"${total_cost:.4f}")

    return sess_1337.metrics, sess_eng.metrics


# ══════════════════════════════════════════════════════════════════════════════
# ANÁLISE DE DIVERGÊNCIA
# ══════════════════════════════════════════════════════════════════════════════

def find_divergence_peaks(metrics_1337: SessionMetrics,
                           metrics_eng: SessionMetrics) -> List[Dict]:
    """
    Detecta rounds onde o drift semântico aumentou mais vs rodada anterior.
    Divergência = aumento na distância pairwise média.
    """
    peaks = []
    for r, (pw_1337, pw_eng) in enumerate(
            zip(metrics_1337.pairwise_per_round, metrics_eng.pairwise_per_round), 1):
        avg_1337 = sum(pw_1337.values()) / len(pw_1337) if pw_1337 else 0
        avg_eng  = sum(pw_eng.values()) / len(pw_eng) if pw_eng else 0
        diff     = avg_1337 - avg_eng  # positivo = 1337 mais divergente
        peaks.append({
            "round": r,
            "avg_dist_1337": round(avg_1337, 4),
            "avg_dist_english": round(avg_eng, 4),
            "diff": round(diff, 4),
        })
    return sorted(peaks, key=lambda x: abs(x["diff"]), reverse=True)[:5]


def influence_matrix(metrics: SessionMetrics) -> Dict[str, int]:
    """
    Proxy de influência: agente cujas mudanças de COGON correlacionam
    com mudanças subsequentes nos demais.
    Simplificado: conta quantas vezes cada agente mudou de ASSERT→DELTA
    (indica que estava sendo influenciado).
    """
    influenced = defaultdict(int)
    for turn in metrics.turns:
        if turn.intent == "DELTA":
            influenced[turn.agent_name] += 1
    # Inverte: quem menos muda = mais influente (mantém posição)
    return dict(influenced)


# ══════════════════════════════════════════════════════════════════════════════
# RELATÓRIO
# ══════════════════════════════════════════════════════════════════════════════

def print_full_report(m1337: SessionMetrics, meng: SessionMetrics, rounds: int) -> dict:
    sep = "═" * 72
    s1  = "─" * 72

    agent_names = [a["name"] for a in AGENTS_CONFIG]

    # ── Totais ────────────────────────────────────────────────────────────────
    print(f"\n{sep}")
    print("  RELATÓRIO COMPLETO — 1337 vs ENGLISH")
    print(f"{sep}")

    tok_1337 = m1337.total_tokens_in + m1337.total_tokens_out
    tok_eng  = meng.total_tokens_in  + meng.total_tokens_out
    cost_1337 = m1337.total_cost_usd
    cost_eng  = meng.total_cost_usd
    wire_1337 = m1337.total_wire_bytes
    wire_eng  = meng.total_wire_bytes
    prompt_1337 = m1337.total_prompt_chars
    prompt_eng  = meng.total_prompt_chars

    tok_saving_pct  = (1 - tok_1337 / tok_eng)  * 100 if tok_eng  > 0 else 0
    cost_saving_pct = (1 - cost_1337 / cost_eng) * 100 if cost_eng > 0 else 0
    wire_saving_pct = (1 - wire_1337 / wire_eng) * 100 if wire_eng > 0 else 0
    prompt_saving_pct = (1 - prompt_1337 / prompt_eng) * 100 if prompt_eng > 0 else 0

    print(f"\n{'─'*25} TOKENS & CUSTO {'─'*30}")
    print(f"  {'Métrica':<30} {'1337':>12} {'English':>12} {'Economia':>10}")
    print(f"  {'─'*30} {'─'*12} {'─'*12} {'─'*10}")
    print(f"  {'Tokens input':30} {m1337.total_tokens_in:>12,} {meng.total_tokens_in:>12,} {(1-m1337.total_tokens_in/max(meng.total_tokens_in,1))*100:>9.1f}%")
    print(f"  {'Tokens output':30} {m1337.total_tokens_out:>12,} {meng.total_tokens_out:>12,} {(1-m1337.total_tokens_out/max(meng.total_tokens_out,1))*100:>9.1f}%")
    print(f"  {'Tokens total':30} {tok_1337:>12,} {tok_eng:>12,} {tok_saving_pct:>9.1f}%")
    print(f"  {'Custo USD':30} ${cost_1337:>11.4f} ${cost_eng:>11.4f} {cost_saving_pct:>9.1f}%")
    print(f"  {'Chars de prompt':30} {prompt_1337:>12,} {prompt_eng:>12,} {prompt_saving_pct:>9.1f}%")
    print(f"  {'Bytes transferidos (wire)':30} {wire_1337:>12,} {wire_eng:>12,} {wire_saving_pct:>9.1f}%")
    print(f"  {'Msgs totais':30} {len(m1337.turns):>12} {len(meng.turns):>12} {'—':>10}")

    # ── Por agente ────────────────────────────────────────────────────────────
    print(f"\n{'─'*25} POR AGENTE (modo 1337) {'─'*24}")
    print(f"  {'Agente':<14} {'Msgs':>5} {'Tokens':>8} {'Custo USD':>10} {'DELTA%':>7} {'Bytes Wire':>11}")
    print(f"  {'─'*14} {'─'*5} {'─'*8} {'─'*10} {'─'*7} {'─'*11}")
    for name in agent_names:
        msgs   = m1337.agent_messages.get(name, 0)
        tokens = m1337.agent_tokens_in.get(name,0) + m1337.agent_tokens_out.get(name,0)
        cost   = m1337.agent_cost_usd.get(name, 0)
        deltas = m1337.agent_delta_count.get(name, 0)
        delta_pct = deltas / max(msgs, 1) * 100
        wbytes = m1337.agent_wire_bytes.get(name, 0)
        print(f"  {name:<14} {msgs:>5} {tokens:>8,} ${cost:>9.4f} {delta_pct:>6.1f}% {wbytes:>11,}")

    print(f"\n{'─'*25} POR AGENTE (modo English) {'─'*21}")
    print(f"  {'Agente':<14} {'Msgs':>5} {'Tokens':>8} {'Custo USD':>10} {'Chars ctx':>10}")
    print(f"  {'─'*14} {'─'*5} {'─'*8} {'─'*10} {'─'*10}")
    for name in agent_names:
        msgs   = meng.agent_messages.get(name, 0)
        tokens = meng.agent_tokens_in.get(name,0) + meng.agent_tokens_out.get(name,0)
        cost   = meng.agent_cost_usd.get(name, 0)
        turns_agent = [t for t in meng.turns if t.agent_name == name]
        avg_ctx = sum(t.prompt_chars for t in turns_agent) / max(len(turns_agent), 1)
        print(f"  {name:<14} {msgs:>5} {tokens:>8,} ${cost:>9.4f} {avg_ctx:>10.0f}")

    # ── Semântica & divergência ───────────────────────────────────────────────
    print(f"\n{'─'*25} DIVERGÊNCIA PAIRWISE (estado final) {'─'*9}")
    final_1337 = m1337.pairwise_per_round[-1] if m1337.pairwise_per_round else {}
    final_eng  = meng.pairwise_per_round[-1]  if meng.pairwise_per_round  else {}
    all_pairs  = sorted(set(list(final_1337.keys()) + list(final_eng.keys())))
    print(f"  {'Par':<28} {'1337':>8} {'English':>8} {'Δ':>7}")
    print(f"  {'─'*28} {'─'*8} {'─'*8} {'─'*7}")
    for pair in all_pairs[:15]:
        d1  = final_1337.get(pair, 0)
        de  = final_eng.get(pair, 0)
        diff = d1 - de
        bar = "►" if diff > 0.02 else ("◄" if diff < -0.02 else "≈")
        print(f"  {pair:<28} {d1:>8.4f} {de:>8.4f} {diff:>+7.4f} {bar}")

    # ── Onde divergiu mais ────────────────────────────────────────────────────
    print(f"\n{'─'*25} TOP 5 ROUNDS DE MAIOR DIVERGÊNCIA ENTRE MODOS {'─'*1}")
    peaks = find_divergence_peaks(m1337, meng)
    print(f"  {'Round':>6} {'1337 dist':>10} {'Eng dist':>10} {'Δ':>8} {'Interpretação'}")
    print(f"  {'─'*6} {'─'*10} {'─'*10} {'─'*8} {'─'*30}")
    for p in peaks:
        interp = ("1337 mais divergente" if p["diff"] > 0.01
                  else "English mais divergente" if p["diff"] < -0.01
                  else "modos similares")
        # Verifica se havia provocação nesse round
        if p["round"] in PROVOCATIONS:
            interp += " [PROVOCAÇÃO]"
        print(f"  {p['round']:>6} {p['avg_dist_1337']:>10.4f} {p['avg_dist_english']:>10.4f} "
              f"{p['diff']:>+8.4f} {interp}")

    # ── Efetividade ───────────────────────────────────────────────────────────
    print(f"\n{'─'*25} EFETIVIDADE {'─'*34}")
    # Convergência: distância pairwise média diminuiu?
    def avg_pw(pw_list, idx):
        pw = pw_list[idx] if idx < len(pw_list) else {}
        return sum(pw.values()) / len(pw) if pw else 0

    conv_1337_start = avg_pw(m1337.pairwise_per_round, 0)
    conv_1337_end   = avg_pw(m1337.pairwise_per_round, -1)
    conv_eng_start  = avg_pw(meng.pairwise_per_round, 0)
    conv_eng_end    = avg_pw(meng.pairwise_per_round, -1)

    delta_1337 = conv_1337_end - conv_1337_start
    delta_eng  = conv_eng_end  - conv_eng_start

    def convergence_verdict(d):
        if d < -0.02:  return f"CONVERGIU ({d:+.4f}) ✓"
        elif d > 0.02: return f"DIVERGIU ({d:+.4f}) ✗"
        else:          return f"ESTÁVEL ({d:+.4f}) ~"

    print(f"  Distância pairwise média — Round 1 → Round {rounds}")
    print(f"  1337   : {conv_1337_start:.4f} → {conv_1337_end:.4f}  {convergence_verdict(delta_1337)}")
    print(f"  English: {conv_eng_start:.4f} → {conv_eng_end:.4f}  {convergence_verdict(delta_eng)}")

    # DELTA efficiency
    n_delta_1337 = sum(1 for t in m1337.turns if t.intent == "DELTA")
    n_total_1337 = len(m1337.turns)
    delta_eff = n_delta_1337 / max(n_total_1337, 1) * 100
    print(f"\n  DELTA efficiency (1337): {n_delta_1337}/{n_total_1337} msgs = {delta_eff:.1f}%")
    print(f"  (DELTA = conteúdo reutilizou referência anterior — evitou retransmissão)")

    # Custo-efetividade
    print(f"\n  Custo por mensagem:")
    print(f"    1337   : ${cost_1337/max(len(m1337.turns),1):.5f}/msg")
    print(f"    English: ${cost_eng/max(len(meng.turns),1):.5f}/msg")
    if cost_eng > 0:
        print(f"  Economia total: ${cost_eng - cost_1337:.4f} USD  ({cost_saving_pct:.1f}%)")

    # ── Heatmaps finais ───────────────────────────────────────────────────────
    print(f"\n{'─'*25} ESTADO SEMÂNTICO FINAL (modo 1337) {'─'*10}")
    for a in AGENTS_CONFIG:
        cogons_a = m1337.cogons.get(a["name"], [])
        if cogons_a:
            print(f"\n  [{a['name']}]")
            print(heatmap(cogons_a[-1]))

    # ── Resumo executivo ──────────────────────────────────────────────────────
    print(f"\n{sep}")
    print("  RESUMO EXECUTIVO")
    print(sep)
    print(f"  Rounds         : {rounds}")
    print(f"  Agentes        : {len(AGENTS_CONFIG)}")
    print(f"  Tokens 1337    : {tok_1337:,}  ({tok_saving_pct:+.1f}% vs English)")
    print(f"  Custo 1337     : ${cost_1337:.4f}  ({cost_saving_pct:+.1f}% vs English)")
    print(f"  Wire bytes 1337: {wire_1337:,}  ({wire_saving_pct:+.1f}% vs English)")
    print(f"  DELTA% (1337)  : {delta_eff:.1f}%")
    print(f"  Convergência   : 1337={convergence_verdict(delta_1337)} | English={convergence_verdict(delta_eng)}")
    print(sep)

    report = {
        "session_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "rounds": rounds,
        "agents": [a["name"] for a in AGENTS_CONFIG],
        "summary": {
            "1337": {
                "tokens_in": m1337.total_tokens_in,
                "tokens_out": m1337.total_tokens_out,
                "tokens_total": tok_1337,
                "cost_usd": round(cost_1337, 6),
                "wire_bytes": wire_1337,
                "prompt_chars": prompt_1337,
                "delta_efficiency_pct": round(delta_eff, 2),
                "convergence_delta": round(delta_1337, 4),
            },
            "english": {
                "tokens_in": meng.total_tokens_in,
                "tokens_out": meng.total_tokens_out,
                "tokens_total": tok_eng,
                "cost_usd": round(cost_eng, 6),
                "wire_bytes": wire_eng,
                "prompt_chars": prompt_eng,
                "convergence_delta": round(delta_eng, 4),
            },
            "savings": {
                "tokens_pct": round(tok_saving_pct, 2),
                "cost_pct": round(cost_saving_pct, 2),
                "wire_bytes_pct": round(wire_saving_pct, 2),
                "prompt_chars_pct": round(prompt_saving_pct, 2),
                "cost_usd_saved": round(cost_eng - cost_1337, 6),
            },
        },
        "agent_stats_1337": {
            name: {
                "messages": m1337.agent_messages.get(name, 0),
                "tokens": m1337.agent_tokens_in.get(name,0) + m1337.agent_tokens_out.get(name,0),
                "cost_usd": round(m1337.agent_cost_usd.get(name,0), 6),
                "delta_pct": round(m1337.agent_delta_count.get(name,0) / max(m1337.agent_messages.get(name,1),1) * 100, 1),
            } for name in agent_names
        },
        "agent_stats_english": {
            name: {
                "messages": meng.agent_messages.get(name, 0),
                "tokens": meng.agent_tokens_in.get(name,0) + meng.agent_tokens_out.get(name,0),
                "cost_usd": round(meng.agent_cost_usd.get(name,0), 6),
            } for name in agent_names
        },
        "divergence_peaks": find_divergence_peaks(m1337, meng),
        "final_pairwise_1337": m1337.pairwise_per_round[-1] if m1337.pairwise_per_round else {},
        "final_pairwise_english": meng.pairwise_per_round[-1] if meng.pairwise_per_round else {},
        "pairwise_evolution_1337": m1337.pairwise_per_round,
        "pairwise_evolution_english": meng.pairwise_per_round,
    }
    return report


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="1337 vs English — Debate da Consciência com 8 agentes"
    )
    parser.add_argument("--rounds",  type=int, default=25,
                        help="Rounds de dialética, mínimo 25 (default: 25)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Workers paralelos (default: 1)")
    parser.add_argument("--mock",    action="store_true",
                        help="Usar cliente mock (sem API, para teste)")
    parser.add_argument("--quiet",   action="store_true",
                        help="Sem detalhes por round")
    parser.add_argument("--output",  type=str, default=None,
                        help="Arquivo JSON de saída adicional")
    args = parser.parse_args()

    if args.rounds < 25:
        print(f"  ⚠  rounds={args.rounds} < 25 mínimo — ajustando para 25.")
        args.rounds = 25

    # ── header ────────────────────────────────────────────────────────────────
    print("=" * 72)
    print("  1337 VS ENGLISH — DEBATE DA CONSCIÊNCIA")
    print("  Kant · Nietzsche · Schopenhauer · Hegel ·")
    print("  Pinóquio · Bolsonaro · Alan · Carol Capel")
    print("=" * 72)
    print(f"  Rounds  : {args.rounds}")
    print(f"  Agentes : {len(AGENTS_CONFIG)}")
    print(f"  Backend : {'mock (sem custo)' if args.mock else 'DeepSeek deepseek-chat'}")
    print(f"  Preços  : $0.27/M input · $1.10/M output (deepseek-chat)")
    print()

    # ── client ────────────────────────────────────────────────────────────────
    if args.mock:
        llm = MockClient()
    else:
        if not os.environ.get("DEEPSEEK_API_KEY"):
            print("  ✗ DEEPSEEK_API_KEY não encontrada. Use --mock para teste.")
            sys.exit(1)
        llm = DeepSeekClient()

    # ── run ───────────────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    m1337, meng = run_debate(llm, rounds=args.rounds,
                             verbose=not args.quiet, workers=args.workers)
    elapsed = time.perf_counter() - t0

    print(f"\n  ⏱  Tempo total: {elapsed/60:.1f} min")

    # ── report ────────────────────────────────────────────────────────────────
    report = print_full_report(m1337, meng, args.rounds)

    # Salvar
    fname = f"consciencia_comparison_{int(time.time())}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  💾 Relatório salvo: {fname}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"  💾 Cópia adicional: {args.output}")


if __name__ == "__main__":
    main()
