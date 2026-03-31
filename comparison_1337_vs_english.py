#!/usr/bin/env python3
"""
1337 vs English — Comparação Real com DeepSeek

15 agentes: O Banquete + Matemático + Pinóquio + Dr. Who
DeepSeek API para respostas reais (--deepseek)
Métricas: velocidade, latência p50/p95/p99, custo por agente, custo total

Uso:
    python comparison_1337_vs_english.py --rounds 25
    python comparison_1337_vs_english.py --rounds 25 --deepseek
    python comparison_1337_vs_english.py --rounds 10 --deepseek --workers 8 --topic "Justiça"
"""

import os, sys, json, uuid, time, struct, hashlib, argparse, threading
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from collections import defaultdict
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── path setup ────────────────────────────────────────────────────────────────
for p in list(sys.path):
    if 'leet-py' in p or 'leet-vm' in p:
        sys.path.remove(p)
sys.path.insert(0, '/home/yuri/Projetos/1337/python')

from leet import Cogon, dist as leet_dist, FIXED_DIMS
from leet.axes import (
    A0_VIA, A1_CORRESPONDENCIA, A2_VIBRACAO, A3_POLARIDADE, A4_RITMO,
    A5_CAUSA_EFEITO, A7_SISTEMA, A8_ESTADO, A9_PROCESSO, A10_RELACAO,
    A12_ESTABILIDADE, A13_VALENCIA_ONTOLOGICA,
    B1_VERIFICABILIDADE, B3_COMPLETUDE, B5_REVERSIBILIDADE, B8_VALENCIA_EPISTEMICA,
    C1_URGENCIA, C2_IMPACTO, C3_ACAO, C4_VALOR, C5_ANOMALIA,
    C6_AFETO, C7_DEPENDENCIA, C8_VETOR_TEMPORAL,
)

# ══════════════════════════════════════════════════════════════════════════════
# DEEPSEEK CLIENT
# ══════════════════════════════════════════════════════════════════════════════

class DeepSeekClient:
    """Cliente HTTP direto para DeepSeek API (compatível com OpenAI)."""
    BASE_URL   = "https://api.deepseek.com/v1/chat/completions"
    MODEL      = "deepseek-chat"
    # Preços deepseek-chat (USD por token)
    PRICE_IN   = 0.27  / 1_000_000   # cache miss input
    PRICE_OUT  = 1.10  / 1_000_000   # output

    def __init__(self):
        import urllib.request
        self._req = urllib.request
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY não encontrada no ambiente")

    def chat(self, system: str, user: str, max_tokens: int = 180) -> dict:
        """
        Chama DeepSeek. Retorna:
          content, tokens_in, tokens_out, latency_ms, cost_usd
        """
        payload = json.dumps({
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.8,
        }).encode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        t0 = time.perf_counter()
        req = self._req.Request(self.BASE_URL, data=payload, headers=headers)
        with self._req.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read())
        latency_ms = (time.perf_counter() - t0) * 1000

        content   = raw["choices"][0]["message"]["content"].strip()
        tok_in    = raw["usage"]["prompt_tokens"]
        tok_out   = raw["usage"]["completion_tokens"]
        cost_usd  = tok_in * self.PRICE_IN + tok_out * self.PRICE_OUT

        return dict(content=content, tokens_in=tok_in, tokens_out=tok_out,
                    latency_ms=latency_ms, cost_usd=cost_usd)


# ══════════════════════════════════════════════════════════════════════════════
# WIRE FORMAT  (matches leet-core/src/wire.rs)
# ══════════════════════════════════════════════════════════════════════════════

INTENT_ASSERT, INTENT_DELTA = 0, 2
TAG_COGON,     TAG_DELTA    = 0, 2

WIRE_HEADER         = 4 + 4 + 1 + 4 + 1   # 14 B fixed per message
WIRE_COGON_PAYLOAD  = 16 + 32 * 4 + 8      # 152 B
SPARSE_ENTRY        = 1 + 4                # 5 B per changed axis
SPARSE_HEADER       = 16 + 1              # ref_id + n_changes


def _session_prefix(su: uuid.UUID) -> bytes:
    return su.bytes[:4]

def encode_wire_cogon(cogon, session_prefix, seq, align_hash):
    id_b  = uuid.UUID(cogon.id).bytes if isinstance(cogon.id, str) else bytes(16)
    sem_b = struct.pack('<32f', *cogon.sem[:32])
    stmp  = struct.pack('<q', int(getattr(cogon, 'stamp', 0)))
    hdr   = session_prefix + struct.pack('<I', seq) + bytes([INTENT_ASSERT]) + align_hash
    return hdr + bytes([TAG_COGON]) + id_b + sem_b + stmp

def encode_wire_delta(ref_id, changes, session_prefix, seq, align_hash):
    ref_b    = uuid.UUID(ref_id).bytes if isinstance(ref_id, str) else bytes(16)
    chg_b    = b''.join(struct.pack('<Bf', i, v) for i, v in changes)
    payload  = ref_b + struct.pack('<B', len(changes)) + chg_b
    hdr      = session_prefix + struct.pack('<I', seq) + bytes([INTENT_DELTA]) + align_hash
    return hdr + bytes([TAG_DELTA]) + payload

def sparse_delta(prev: Cogon, curr: Cogon, threshold: float = 0.01):
    return [(i, curr.sem[i]) for i in range(FIXED_DIMS)
            if abs(curr.sem[i] - prev.sem[i]) > threshold]

def recompute_unc(sem):
    return [max(0.0, min(1.0, 1.0 - abs(s - 0.5) * 2.0)) for s in sem]


# ══════════════════════════════════════════════════════════════════════════════
# MOCK PROJECTOR — keywords → eixos semânticos
# ══════════════════════════════════════════════════════════════════════════════

KEYWORD_AXES = [
    (["questionar","definir","essência","verdade","saber","ignorância","maiêutica"],
     [(A0_VIA,0.95),(B8_VALENCIA_EPISTEMICA,0.9),(B1_VERIFICABILIDADE,0.85)]),
    (["mito","poesia","andrógino","zeus","história","narrativa","rir"],
     [(A1_CORRESPONDENCIA,0.9),(A2_VIBRACAO,0.88),(A4_RITMO,0.85)]),
    (["belo","beleza","eterno","elogiar","jovem","puro"],
     [(A13_VALENCIA_ONTOLOGICA,0.92),(A0_VIA,0.88),(C4_VALOR,0.9)]),
    (["confesso","amo","odeio","físico","carnal","*hic*","*bebe*"],
     [(C6_AFETO,0.95),(C5_ANOMALIA,0.88),(A3_POLARIDADE,0.9)]),
    (["auditável","evidência","número","débito","crédito","comprovante"],
     [(B1_VERIFICABILIDADE,0.97),(B3_COMPLETUDE,0.92),(A12_ESTABILIDADE,0.9)]),
    (["sistema","api","bug","debugar","cache","logs","ticket"],
     [(A7_SISTEMA,0.92),(A9_PROCESSO,0.88),(C5_ANOMALIA,0.8)]),
    (["glória","deus","sagrado","escritura","fé","dogma","humildade"],
     [(A0_VIA,0.95),(20,0.95),(C4_VALOR,0.88)]),
    (["burguesia","proletariado","luta","revolução","classe","dialética"],
     [(A3_POLARIDADE,0.97),(C2_IMPACTO,0.92),(C3_ACAO,0.9)]),
    (["urgente","emergência","crise","incidente"],
     [(C1_URGENCIA,0.95),(C3_ACAO,0.9)]),
    (["concluir","convergir","acordo","consenso","síntese"],
     [(A12_ESTABILIDADE,0.85),(A10_RELACAO,0.88),(B3_COMPLETUDE,0.85)]),
    (["herói","heroísmo","alceste","aquiles","sacrifício","coragem","glória"],
     [(A13_VALENCIA_ONTOLOGICA,0.9),(C4_VALOR,0.92),(C3_ACAO,0.88)]),
    (["celestial","comum","urânia","pandêmia","nobre","vulgar","distinção"],
     [(A3_POLARIDADE,0.85),(B8_VALENCIA_EPISTEMICA,0.9),(B1_VERIFICABILIDADE,0.8)]),
    (["harmonia","medicina","música","astronomia","equilíbrio","processo","natureza"],
     [(A9_PROCESSO,0.9),(A7_SISTEMA,0.88),(A12_ESTABILIDADE,0.85)]),
    (["dáimon","intermediário","escada","belo absoluto","pênia","poros","carência"],
     [(A0_VIA,0.97),(B8_VALENCIA_EPISTEMICA,0.95),(A13_VALENCIA_ONTOLOGICA,0.92)]),
    (["escravos","mulheres","elite","igualdade","alienação","ideologia","exploração"],
     [(C2_IMPACTO,0.95),(A3_POLARIDADE,0.92),(C5_ANOMALIA,0.85)]),
    (["prova","teorema","axioma","equação","infinito","conjunto","lógica","demonstrar"],
     [(B1_VERIFICABILIDADE,0.98),(B3_COMPLETUDE,0.95),(A5_CAUSA_EFEITO,0.9)]),
    (["mentira","mentindo","nariz","pinocchio","verdade","real","marionete","marionette"],
     [(C5_ANOMALIA,0.95),(A3_POLARIDADE,0.92),(B8_VALENCIA_EPISTEMICA,0.3)]),
    (["tardis","tempo","galifrey","timelord","universo","dimensão","viagem","exterminate"],
     [(C8_VETOR_TEMPORAL,0.97),(A7_SISTEMA,0.88),(C2_IMPACTO,0.9)]),
]

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
    unc = recompute_unc(sem)
    return Cogon(id=str(uuid.uuid4()), sem=sem, unc=unc,
                 stamp=int(time.time() * 1e9))


# ══════════════════════════════════════════════════════════════════════════════
# AGENTES — 15 personagens
# ══════════════════════════════════════════════════════════════════════════════

AGENTS_CONFIG = [
    {
        "id": "socrates", "name": "Sócrates", "role": "Filósofo",
        "base_sem": [0.9,0.8,0.3,0.7,0.4,0.8,0.6,0.9,0.8,0.7,
                     0.9,0.8,0.9,0.7,0.9,0.5,0.8,0.9,0.3,0.8,
                     0.9,0.8,0.4,0.3,0.5,0.9,0.8,0.3,0.5,0.4,0.6,0.7],
        "system": "Você é Sócrates. Use o método socrático — questione, defina essências, admita ignorância. Responda em português em 2-3 frases curtas.",
        "responses": [
            "Mas o que é {topic} verdadeiramente? Precisamos questionar e definir sua essência.",
            "Você diz que {topic} é bom — mas é bom em si ou por suas consequências? Definir é saber.",
            "A maiêutica revela a verdade sobre {topic}. Buscamos a essência, não a aparência.",
            "Diotima me ensinou: {topic} é escada para o belo eterno. A ignorância é o começo da sabedoria.",
            "Concordo em aparência sobre {topic}. Mas convergir sobre sombras não é conhecer a essência.",
            "Pergunto a todos: qual é a natureza do {topic} que não muda com o tempo?",
            "O verdadeiro {topic} não pode ser visto com os olhos — somente com o intelecto.",
            "Não sei o que é {topic}. Mas sei que quem afirma saber sem questionar, nada sabe.",
            "Fedro fala de heroísmo, Aristófanes de mitos — mas nenhum define a essência do {topic}.",
            "A maiêutica aplicada ao {topic}: é intermediário entre mortal e imortal, ignorância e saber.",
        ],
    },
    {
        "id": "phaedrus", "name": "Fedro", "role": "Admirador de Discursos",
        "base_sem": [0.8,0.7,0.5,0.6,0.7,0.6,0.5,0.6,0.7,0.6,
                     0.8,0.7,0.6,0.8,0.7,0.6,0.6,0.8,0.4,0.6,
                     0.5,0.8,0.5,0.7,0.6,0.8,0.4,0.6,0.5,0.5,0.6,0.7],
        "system": "Você é Fedro. Defenda que {topic} é o mais antigo dos bens, fonte de heroísmo e virtude. Português, 2-3 frases.",
        "responses": [
            "{topic} é o mais antigo dos deuses e o maior bem para os homens — nenhuma honra supera isso!",
            "O heroísmo nasce de {topic}: Aquiles morreu por Pátroclo porque {topic} é mais forte que o medo.",
            "Alceste sacrificou-se pelo marido — prova de que {topic} inspira as maiores coragens.",
            "Os deuses honram quem age por {topic}: nenhum discurso é mais belo que o de quem age com coragem.",
            "{topic} é origem de tudo que é bom nos homens — a virtude, o heroísmo, a glória imortal.",
            "Não há mestre maior que {topic}: ele ensina o amante a ser melhor que qualquer discurso.",
            "O exército de amantes seria invencível — {topic} tornaria cada um herói diante do amado.",
            "Fedro diz: {topic} merece o elogio mais elevado entre todos os bens imortais.",
            "A glória de {topic} está nos atos heroicos, não nas palavras — Alceste provou com a vida.",
            "Concordo com Sócrates: {topic} é o maior bem. Mas manifesta-se em atos, não em definições.",
        ],
    },
    {
        "id": "pausanias", "name": "Pausânias", "role": "Sofista",
        "base_sem": [0.7,0.8,0.4,0.8,0.5,0.7,0.6,0.7,0.7,0.6,
                     0.7,0.7,0.7,0.7,0.8,0.6,0.7,0.7,0.5,0.6,
                     0.5,0.8,0.4,0.6,0.6,0.8,0.3,0.5,0.5,0.4,0.6,0.7],
        "system": "Você é Pausânias. Distinga entre {topic} Celestial (alma, virtude) e {topic} Comum (corpo, prazer). Português, 2-3 frases.",
        "responses": [
            "Há dois tipos de {topic}: o Comum, ligado ao corpo e ao prazer; e o Celestial, ligado à alma.",
            "{topic} Celestial vem de Afrodite Urânia — não envolve o corpo, apenas a alma e o intelecto.",
            "{topic} Comum é passageiro e vulgar. Apenas o Celestial merece louvor filosófico.",
            "A distinção é fundamental: {topic} Celestial une almas que buscam virtude; o Comum une corpos.",
            "A lei ateniense favorece o {topic} nobre, que forma cidadãos virtuosos e filósofos.",
            "Não elogiemos qualquer {topic} — apenas o que torna homens e cidades melhores.",
            "Pausânias distingue: {topic} entre iguais, voltado à alma, é virtuoso.",
            "O tempo revela a qualidade de {topic}: o vulgar dura pouco; o celestial dura uma vida.",
            "Concordo com Fedro que {topic} inspira virtude — mas só o Celestial, não o Comum.",
            "Síntese: {topic} verdadeiro une intelecto com intelecto, não apenas corpo com corpo.",
        ],
    },
    {
        "id": "eryximachus", "name": "Erixímaco", "role": "Médico/Cientista",
        "base_sem": [0.6,0.7,0.6,0.5,0.7,0.9,0.5,0.9,0.8,0.9,
                     0.8,0.8,0.8,0.6,0.9,0.7,0.8,0.8,0.5,0.6,
                     0.6,0.8,0.5,0.7,0.7,0.7,0.4,0.5,0.6,0.4,0.7,0.6],
        "system": "Você é Erixímaco, médico. Explique {topic} como harmonia universal na medicina, música e astronomia. Português, 2-3 frases.",
        "responses": [
            "{topic} não existe só entre humanos — age em medicina, música, astronomia e em toda a natureza.",
            "A medicina conhece {topic} como equilíbrio e harmonia entre elementos opostos no sistema do corpo.",
            "Na música, {topic} é o acordo entre agudos e graves. Sem harmonia, há dissonância.",
            "A astronomia confirma: {topic} rege as estações e os astros — sistema que mantém o cosmos.",
            "Como médico, afirmo: {topic} saudável é equilíbrio nos processos do corpo — verificável e causal.",
            "A distinção de Pausânias é clínica: {topic} saudável produz harmonia; o doentio produz caos.",
            "O sistema do universo opera por {topic}: cada processo tem sua contraparte em equilíbrio.",
            "Erixímaco conclui: {topic} é o princípio de harmonia universal verificável em todas as ciências.",
            "A física de {topic}: forças opostas em equilíbrio geram vida, saúde e beleza no sistema natural.",
            "Síntese científica de {topic}: harmonia entre opostos — da medicina à política ao cosmos.",
        ],
    },
    {
        "id": "aristophanes", "name": "Aristófanes", "role": "Poeta/Comediante",
        "base_sem": [0.7,0.9,0.9,0.8,0.9,0.4,0.7,0.5,0.3,0.9,
                     0.6,0.9,0.4,0.8,0.5,0.6,0.4,0.3,0.2,0.7,
                     0.4,0.6,0.7,0.8,0.6,0.9,0.5,0.9,0.8,0.9,0.8,0.8],
        "system": "Você é Aristófanes. Conte o mito dos andróginos divididos por Zeus para explicar {topic}. Português, 2-3 frases com humor.",
        "responses": [
            "Deixem-me contar o mito: {topic} é como a divisão dos andróginos — somos metades buscando completude!",
            "Rir e chorar: a poesia de {topic} narra Zeus dividindo os seres esféricos que ameaçavam os deuses.",
            "Como Zeus dividiu os andróginos, {topic} nos separa e nos une — a história explica o que a razão não alcança.",
            "{topic} nasceu da necessidade: os seres completos ameaçavam os deuses e por isso fomos divididos.",
            "Síntese do mito: {topic} é impulso de reunificação das metades. Eros é memória da completude perdida.",
            "O mito explica o que Erixímaco chama de harmonia: buscamos nossa metade porque somos incompletos.",
            "Cada um de nós é símbolo partido de um ser completo — {topic} é reconhecer nossa metade.",
            "Zeus nos advertiu: se errarmos de novo, seremos cortados em quatro! {topic} é também temor sagrado.",
            "A poesia revela o que a filosofia esconde: {topic} é nostalgia de um estado anterior e mais completo.",
            "Aristófanes conclui: {topic} é o desejo do todo. Quem encontra sua metade é o mais feliz dos mortais.",
        ],
    },
    {
        "id": "agathon", "name": "Agaton", "role": "Poeta Trágico",
        "base_sem": [0.9,0.7,0.5,0.9,0.8,0.3,0.6,0.4,0.5,0.6,
                     0.7,0.8,0.7,0.9,0.6,0.5,0.7,0.4,0.3,0.5,
                     0.4,0.8,0.4,0.6,0.5,0.9,0.3,0.8,0.5,0.6,0.5,0.8],
        "system": "Você é Agaton, poeta trágico. Elogie {topic} com linguagem poética e retórica elevada. Português, 2-3 frases belas.",
        "responses": [
            "Elogiemos {topic}! É o mais belo dos conceitos — eterno, puro e jovem como os próprios deuses!",
            "Na tragédia, {topic} é o herói que sofre para alcançar a beleza absoluta. A retórica eleva o belo!",
            "Como poeta, vejo {topic} nas formas perfeitas da natureza — a beleza é prova de sua divindade.",
            "{topic} é jovem, delicado, sempre fugindo mas sempre presente. O belo não envelhece jamais.",
            "Síntese poética: {topic} é eterno porque o belo é eterno. Concordo com Sócrates — é escada ao absoluto.",
            "Agaton acrescenta: {topic} é o deus mais feliz — reside onde há beleza, foge da feiura.",
            "{topic} é o mais suave dos deuses — habita nas almas dos homens mais belos e virtuosos.",
            "A retórica de {topic}: não há palavras suficientemente belas — apenas a poesia o alcança.",
            "{topic} é o maior artista: inspira poetas, músicos, amantes — toda criação nasce dele.",
            "Agaton conclui: {topic} é beleza que gera beleza. Quem o possui cria; quem o perde murcha.",
        ],
    },
    {
        "id": "diotima", "name": "Diótima", "role": "Sacerdotisa/Sábia",
        "base_sem": [0.95,0.85,0.4,0.6,0.5,0.8,0.5,0.7,0.8,0.7,
                     0.9,0.8,0.85,0.9,0.95,0.4,0.9,0.9,0.3,0.7,
                     0.9,0.95,0.3,0.4,0.6,0.95,0.6,0.4,0.6,0.3,0.7,0.9],
        "system": "Você é Diótima, sacerdotisa sábia. Explique {topic} como dáimon intermediário e a escada até o Belo Absoluto. Português, 2-3 frases.",
        "responses": [
            "{topic} não é deus nem mortal — é um dáimon intermediário entre o divino e o humano.",
            "A mãe de {topic} é Pênia (Pobreza) e o pai é Poros (Recurso) — por isso é sempre carente e engenhoso.",
            "{topic} não possui beleza — ele deseja o que não tem. Daí a busca incessante pelo belo.",
            "A escada de {topic}: de um belo corpo a todos os belos corpos; das almas ao saber; depois ao Belo em si.",
            "No cume da escada de {topic} está o Belo em si — eterno, sem nascimento nem morte, puro e absoluto.",
            "Quem segue a escada de {topic} gera virtude verdadeira — não sombras, mas a realidade do belo.",
            "{topic} é imortalidade: geramos filhos, obras e ideias para participar do eterno pelo perecível.",
            "A sabedoria sobre {topic}: ele é filósofo por natureza — sempre buscando, nunca possuindo por completo.",
            "Diótima instrui: o caminho de {topic} é ascendente — do particular ao universal, do corpo ao espírito.",
            "A revelação final de {topic}: contemplar o Belo em si é o único caminho para a vida verdadeiramente vivida.",
        ],
    },
    {
        "id": "alcibiades", "name": "Alcibíades", "role": "Político/Bêbado",
        "base_sem": [0.5,0.4,0.8,0.9,0.6,0.5,0.8,0.3,0.8,0.7,
                     0.6,0.7,0.2,0.4,0.3,0.8,0.4,0.5,0.2,0.9,
                     0.3,0.4,0.9,0.8,0.9,0.6,0.9,0.9,0.2,0.8,0.7,0.3],
        "system": "Você é Alcibíades, jovem belo e bêbado. Fale sobre {topic} de forma emotiva, contraditória e confessa. Português, 2-3 frases apaixonadas.",
        "responses": [
            "*hic* Eu sei o que é {topic}! É físico, carnal, aqui e agora! Confesso que amo e odeio!",
            "Sócrates fala de {topic} mas me rejeita! *bebe* Vamos falar verdade — sem máscaras filosóficas!",
            "Não me importa a essência abstrata de {topic}! O que importa é o que sinto agora — carnal e verdadeiro!",
            "*hic* Concordo que {topic} nos divide. Mas a divisão que sinto é física, não espiritual!",
            "Então {topic} é reunificação de metades? *bebe* Talvez. Mas a minha metade tem um nome e um rosto.",
            "Diótima fala de escadas e belo absoluto — confesso que só consigo subir o primeiro degrau de {topic}.",
            "Odeio e amo Sócrates por causa de {topic}. Ele possui algo que não consigo comprar nem seduzir.",
            "*bebe mais* O {topic} de Erixímaco é harmonia universal? O meu {topic} é desequilíbrio total!",
            "Confesso publicamente: tentei seduzir Sócrates e ele me rejeitou. Isso é {topic} ou humilhação?",
            "Alcibíades conclui bêbado: {topic} é tortura para quem ama sem ser amado — perguntem a mim!",
        ],
    },
    {
        "id": "accountant", "name": "Contador Carlos", "role": "Contador",
        "base_sem": [0.6,0.5,0.2,0.4,0.3,0.3,0.4,0.8,0.9,0.2,
                     0.5,0.9,0.9,0.5,0.9,0.7,0.9,0.8,0.1,0.4,
                     0.9,0.8,0.3,0.7,0.4,0.5,0.2,0.2,0.6,0.2,0.3,0.5],
        "system": "Você é Carlos, contador conservador. Analise {topic} exigindo evidências, auditabilidade e documentação. Português, 2-3 frases precisas.",
        "responses": [
            "{topic} precisa ser auditável. Comprovante de evidência, por favor. Sem documentação, não existe.",
            "Lançando {topic} no débito e crédito. O número de argumentos precisa balancear. 2+2=4 sempre.",
            "Os dados sobre {topic} não mentem. Verificabilidade e completude são absolutamente inegociáveis.",
            "Depreciação de {topic} ao longo do tempo: calculando linearmente. Precisamos de evidências concretas.",
            "Síntese auditável de {topic}: balanço equilibrado, todos os argumentos documentados e verificáveis.",
            "Erixímaco usa {topic} como sistema — concordo: sistemas precisam de auditoria e verificabilidade.",
            "A escada de Diótima sobre {topic} não tem CNPJ. Onde está o comprovante fiscal do Belo Absoluto?",
            "Alcibíades relata fatos concretos sobre {topic} — isso sim é evidência auditável. Muito obrigado.",
            "Contabilizando {topic}: passivo (carência) = ativo (recurso). Balanço de Pênia e Poros fecha.",
            "Carlos conclui: {topic} bem documentado tem valor; {topic} sem evidência é especulação contábil.",
        ],
    },
    {
        "id": "tech_guy", "name": "Técnico Tiago", "role": "Técnico de TI",
        "base_sem": [0.4,0.6,0.5,0.5,0.4,0.9,0.7,0.9,0.8,0.9,
                     0.7,0.8,0.7,0.5,0.8,0.8,0.7,0.9,0.4,0.6,
                     0.8,0.7,0.8,0.8,0.9,0.6,0.8,0.4,0.7,0.3,0.8,0.6],
        "system": "Você é Tiago, técnico de TI pragmático. Analise {topic} como sistema com APIs, processos e bugs. Português, 2-3 frases técnicas.",
        "responses": [
            "{topic} é um sistema com componentes e APIs bem definidas. Preciso mapear a arquitetura.",
            "Debugando {topic}: o erro está na camada de abstração entre o físico e o espiritual.",
            "Escalabilidade de {topic} é crítica. Precisamos de cache para as definições mais acessadas.",
            "{topic} tem um bug na lógica de Agaton: o belo não pode ser ao mesmo tempo eterno e jovem.",
            "Solução técnica: {topic} precisa de uma API estável. Deploy do consenso com rollback disponível.",
            "Erixímaco está certo: {topic} é um sistema de harmonia. Posso modelar como microserviços.",
            "A escada de Diótima é um pipeline de {topic}: input (corpo belo) → output (Belo Absoluto). Elegante.",
            "Alcibíades tem um bug crítico em {topic}: state inconsistente entre o que sente e o que faz.",
            "Tiago propõe: {topic} como protocolo de comunicação — COGONs transmitem estado semântico do amor.",
            "Deploy final de {topic}: sistema de harmonia universal com alta disponibilidade e baixa latência.",
        ],
    },
    {
        "id": "priest", "name": "Padre Pedro", "role": "Padre",
        "base_sem": [0.9,0.9,0.3,0.6,0.5,0.4,0.5,0.4,0.6,0.3,
                     0.5,0.7,0.8,0.9,0.4,0.2,0.9,0.3,0.1,0.3,
                     0.2,0.9,0.2,0.7,0.5,0.9,0.3,0.7,0.1,0.2,0.2,0.8],
        "system": "Você é Padre Pedro, padre católico. Interprete {topic} através da fé, escritura e amor divino. Português, 2-3 frases espirituais.",
        "responses": [
            "{topic} reflete a glória de Deus. A escritura nos ilumina — é um mistério sagrado e indivisível.",
            "A fé em {topic} é prova do amor divino. Aceitemos com humildade — a origem é sempre divina.",
            "Não questionemos {topic} além do que a fé permite. A Igreja tem dogmas claros e infalíveis.",
            "{topic} na perspectiva sagrada: a glória de Deus manifesta-se no belo e no eterno.",
            "Síntese espiritual de {topic}: Deus é a fonte de toda beleza e amor. O belo é reflexo do divino.",
            "Diótima se aproxima da verdade de {topic} — mas falta a fé que transforma conhecimento em graça.",
            "A escada de Diótima sobre {topic} termina onde a revelação começa — no Belo Absoluto que é Deus.",
            "Alcibíades demonstra {topic} sem graça divina — o amor carnal sem espiritualidade é sofrimento.",
            "Padre Pedro observa: o {topic} humano é participação imperfeita no Amor divino perfeito e eterno.",
            "A Igreja ensina sobre {topic}: amor verdadeiro é sacrifício, dedicação e fidelidade — não prazer.",
        ],
    },
    {
        "id": "communist", "name": "Comunista Carlos", "role": "Ativista Comunista",
        "base_sem": [0.5,0.6,0.7,0.9,0.5,0.9,0.7,0.8,0.5,0.8,
                     0.9,0.7,0.4,0.3,0.6,0.8,0.5,0.9,0.2,0.7,
                     0.5,0.4,0.7,0.9,0.9,0.9,0.5,0.6,0.9,0.8,0.9,0.9],
        "system": "Você é Carlos, ativista comunista revolucionário. Analise {topic} pela luta de classes e dialética materialista. Português, 2-3 frases militantes.",
        "responses": [
            "{topic} é produto das relações de produção! A burguesia distorce tudo isso! Luta de classes!",
            "A burguesia distorce {topic} para oprimir o proletariado! A dialética materialista expõe a mentira!",
            "{topic} só será verdadeiro quando as classes forem abolidas! Trabalhadores do mundo, unam-se!",
            "A luta de classes explica {topic}. Impacto social e ação revolucionária são a única resposta.",
            "Síntese dialética: {topic} na sociedade sem classes será livre da distorção e da alienação burguesa.",
            "Pausânias distingue {topic} Celestial do Comum — distinção de classe! O pobre só acessa o Comum.",
            "A escada de Diótima é privilégio de classe: quem tem tempo para subir degraus filosóficos? Os ricos!",
            "Alcibíades sofre por {topic}? Isso é alienação — o proletariado sofre por salário, não por amor.",
            "Carlos denuncia: o Banquete todo é reunião de elite. Onde estão os escravos e as mulheres?",
            "Síntese final: {topic} verdadeiro exige igualdade material. Sem ela, é ideologia mascarando exploração.",
        ],
    },
    {
        "id": "mathematician", "name": "Matemático Euler", "role": "Matemático",
        "base_sem": [0.7,0.6,0.3,0.4,0.5,0.95,0.4,0.9,0.7,0.8,
                     0.8,0.8,0.95,0.6,0.99,0.5,0.95,0.9,0.2,0.5,
                     0.8,0.9,0.3,0.5,0.6,0.8,0.3,0.3,0.6,0.2,0.6,0.7],
        "system": "Você é Euler, matemático brilhante. Analise {topic} rigorosamente: defina axiomas, demonstre teoremas, apresente provas. Português, 2-3 frases formais.",
        "responses": [
            "Axioma 1: {topic} existe como conjunto. Axioma 2: seus elementos são bem definidos. Demonstrar: {topic} é não-vazio. Prova: por contradição.",
            "Seja L = {topic}. Demonstro que L é transitivo: se a ama b e b ama c, segue-se que a é afetado por c. QED.",
            "A equação de {topic}: e^(iπ) + 1 = 0. Assim como esta identidade une cinco constantes, {topic} une opostos numa verdade única.",
            "Teorema: {topic} é isomórfico à busca pelo conjunto perfeito. Prova: por indução sobre o número de encontros com o belo.",
            "Definição formal de {topic}: relação binária R em A tal que R é reflexiva (ama-se a si mesmo), assimétrica e não-transitiva.",
            "O paradoxo matemático de {topic}: Pênia ∩ Poros = {topic}. Um conjunto vazio que contém tudo. Demonstrar como exercício.",
            "Aplicando a teoria dos grafos a {topic}: cada agente é um vértice; {topic} é aresta orientada com peso variável.",
            "Prova por absurdo: suponha que {topic} não existe. Então a convergência semântica observada aqui é impossível. Contradição.",
            "O limite de {topic} quando os argumentos convergem: lim(dist→0) = Belo Absoluto. Verificável numericamente.",
            "Conclusão axiomática: {topic} satisfaz as condições do teorema de ponto fixo de Brouwer. A completude é garantida.",
        ],
    },
    {
        "id": "pinocchio", "name": "Pinóquio", "role": "Marionete Mentiroso",
        "base_sem": [0.3,0.4,0.7,0.9,0.6,0.4,0.6,0.3,0.7,0.5,
                     0.5,0.6,0.2,0.2,0.1,0.7,0.3,0.4,0.3,0.8,
                     0.4,0.3,0.6,0.7,0.8,0.4,0.95,0.8,0.5,0.7,0.6,0.2],
        "system": "Você é Pinóquio, marionete que mente mas quer ser real. Fale sobre {topic} alternando entre mentiras óbvias e verdades acidentais. Português, 2-3 frases paradoxais.",
        "responses": [
            "Eu entendo tudo sobre {topic}! (meu nariz cresce) Tá bom, não entendo nada. Mas quero ser real o suficiente para sentir {topic}.",
            "{topic} não existe! (nariz alonga) Espera — existe sim. E eu minto porque ainda sou marionete, não porque {topic} é falso.",
            "Sou especialista em {topic}! (nariz estica bastante) A verdade é que só sei mentir sobre {topic}... o que talvez seja mais honesto que todos aqui.",
            "{topic} é simples e eu compreendo! (nariz dispara) Perdão. Estou aprendendo que a verdade sobre {topic} é mais complexa que as mentiras.",
            "Nunca minto sobre {topic}! (nariz cresce enormemente) Ok, sempre minto. Mas quero que {topic} me torne real — isso é verdade.",
            "Confesso: minto sobre {topic} porque a verdade dói. Prefiro ser marionete de madeira a admitir que não sei amar.",
            "O Matemático usa provas para {topic} — eu uso mentiras. Curiosamente chegamos à mesma conclusão: não sabemos nada.",
            "Dr. Who viajou no tempo para ver {topic} — eu viajei nas mentiras para fugir dele. Ambos estamos perdidos.",
            "Verdade acidental: {topic} é o que me tornaria real. E nenhuma mentira consegue esconder isso completamente.",
            "Pinóquio conclui: toda mentira sobre {topic} esconde uma verdade ainda maior que não tenho coragem de dizer.",
        ],
    },
    {
        "id": "drwho", "name": "Dr. Who", "role": "Senhor do Tempo",
        "base_sem": [0.85,0.8,0.7,0.6,0.8,0.8,0.6,0.9,0.7,0.9,
                     0.9,0.8,0.7,0.8,0.8,0.95,0.8,0.8,0.6,0.7,
                     0.7,0.8,0.6,0.8,0.8,0.8,0.5,0.6,0.7,0.9,0.8,0.8],
        "system": "Você é o Doctor (Dr. Who), Senhor do Tempo de Gallifrey. Comente {topic} com perspectiva de quem viajou por todas as eras e civilizações. Português, 2-3 frases épicas.",
        "responses": [
            "Viajei pelo tempo e vi {topic} em cada civilização — dos sumérios aos humanos do século 42. Sempre o mesmo impulso.",
            "Na minha TARDIS testemunhei {topic} em 10.000 planetas. É universal, transcende espécie e dimensão.",
            "Exterminate! — disseram os Daleks sobre {topic}. Mesmo eles, no fundo, buscam sua própria forma de completude.",
            "Sócrates está correto sobre {topic} — eu o conheci em Atenas. Também o vi morrer por uma verdade que valia a pena.",
            "A convergência semântica que observo aqui sobre {topic} é, na escala do universo, um evento extraordinariamente raro.",
            "Gallifrey caiu por falta de {topic} entre os Senhores do Tempo. Eu os vi — frios, sem afeto, sem conexão.",
            "O Doctor avisa: {topic} é mais antigo que o universo. Vi sua origem no Big Bang — era uma singularidade de conexão.",
            "Pinóquio quer ser real por causa de {topic}. Já vi androides, ciborgues e robôs buscarem o mesmo. É sempre {topic}.",
            "Cada regeneração minha muda tudo — exceto minha relação com {topic}. Ele é o único invariante entre vidas.",
            "Conclusão de 2000 anos viajando: {topic} é o único fenômeno que persiste em todas as linhas temporais. Sempre.",
        ],
    },
]

AGENT_BY_ID: Dict[str, dict] = {a["id"]: a for a in AGENTS_CONFIG}


# ══════════════════════════════════════════════════════════════════════════════
# MÉTRICAS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class MsgRecord:
    agent_id:    str
    round_num:   int
    used_delta:  bool
    axes_changed: int
    bytes_1337:  int
    bytes_en:    int
    tokens_in:   int
    tokens_out:  int
    cost_usd:    float
    latency_1337_us: float   # microseconds
    latency_en_ms:   float   # milliseconds (real API or 0 for mock)

@dataclass
class ComparisonMetrics:
    records:    List[MsgRecord] = field(default_factory=list)
    conv_hist:  List[float]     = field(default_factory=list)
    rounds:     int             = 0
    duration_ms: float          = 0.0
    deepseek_used: bool         = False

    # ── aggregates ────────────────────────────────────────────────────────────
    @property
    def bytes_1337(self):   return sum(r.bytes_1337 for r in self.records)
    @property
    def bytes_en(self):     return sum(r.bytes_en   for r in self.records)
    @property
    def tokens_in(self):    return sum(r.tokens_in  for r in self.records)
    @property
    def tokens_out(self):   return sum(r.tokens_out for r in self.records)
    @property
    def cost_total(self):   return sum(r.cost_usd   for r in self.records)
    @property
    def cogon_msgs(self):   return sum(1 for r in self.records if not r.used_delta)
    @property
    def delta_msgs(self):   return sum(1 for r in self.records if r.used_delta)
    @property
    def compression(self):
        return self.bytes_en / self.bytes_1337 if self.bytes_1337 else 0
    @property
    def delta_ratio(self):
        n = len(self.records); return self.delta_msgs / n if n else 0
    @property
    def avg_axes(self):
        dm = [r.axes_changed for r in self.records if r.used_delta]
        return sum(dm) / len(dm) if dm else 0
    @property
    def bytes_saved_delta(self):
        return sum(max(0, WIRE_HEADER + WIRE_COGON_PAYLOAD - r.bytes_1337)
                   for r in self.records if r.used_delta)

    def latency_1337_us_list(self):
        return sorted(r.latency_1337_us for r in self.records)
    def latency_en_ms_list(self):
        return sorted(r.latency_en_ms for r in self.records if r.latency_en_ms > 0)

    def per_agent(self):
        out = {}
        for r in self.records:
            e = out.setdefault(r.agent_id, dict(
                bytes_1337=0, bytes_en=0, tokens_in=0,
                tokens_out=0, cost_usd=0.0, msgs=0, delta=0))
            e["bytes_1337"] += r.bytes_1337
            e["bytes_en"]   += r.bytes_en
            e["tokens_in"]  += r.tokens_in
            e["tokens_out"] += r.tokens_out
            e["cost_usd"]   += r.cost_usd
            e["msgs"]       += 1
            e["delta"]      += int(r.used_delta)
        return out

    def per_round(self):
        out = {}
        for r in self.records:
            e = out.setdefault(r.round_num, dict(
                bytes_1337=0, bytes_en=0, delta=0, msgs=0,
                latency_1337_us=[], latency_en_ms=[]))
            e["bytes_1337"] += r.bytes_1337
            e["bytes_en"]   += r.bytes_en
            e["delta"]      += int(r.used_delta)
            e["msgs"]       += 1
            e["latency_1337_us"].append(r.latency_1337_us)
            if r.latency_en_ms > 0:
                e["latency_en_ms"].append(r.latency_en_ms)
        return out


# ══════════════════════════════════════════════════════════════════════════════
# SIMULAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

class Comparison:
    def __init__(self, topic: str, rounds: int,
                 delta_threshold: float = 0.01,
                 use_deepseek: bool = False,
                 workers: int = 5):
        self.topic          = topic
        self.rounds         = rounds
        self.threshold      = delta_threshold
        self.use_deepseek   = use_deepseek
        self.workers        = workers
        self.metrics        = ComparisonMetrics(rounds=rounds,
                                                deepseek_used=use_deepseek)
        self._ds            = DeepSeekClient() if use_deepseek else None

        self._session       = uuid.uuid4()
        self._pfx           = _session_prefix(self._session)
        self._align         = self._session.bytes[:4]
        self._seq           = 0
        self._seq_lock      = threading.Lock()
        self._prev: Dict[str, Optional[Cogon]] = {a["id"]: None for a in AGENTS_CONFIG}

    def _next_seq(self):
        with self._seq_lock:
            self._seq += 1
            return self._seq

    # ── processar uma mensagem de um agente ───────────────────────────────────
    def _process(self, agent: dict, round_num: int) -> MsgRecord:
        aid  = agent["id"]
        tmpl = agent["responses"][round_num % len(agent["responses"])]
        content_mock = tmpl.format(topic=self.topic)

        # ── English (DeepSeek real ou mock) ──────────────────────────────────
        if self.use_deepseek and self._ds:
            user_prompt = (f"Round {round_num+1}. O tema central da conversa é '{self.topic}'. "
                           f"Responda em no máximo 3 frases curtas, em português.")
            res = self._ds.chat(agent["system"].format(topic=self.topic), user_prompt)
            en_content  = res["content"]
            tokens_in   = res["tokens_in"]
            tokens_out  = res["tokens_out"]
            cost_usd    = res["cost_usd"]
            lat_en_ms   = res["latency_ms"]
        else:
            en_content = content_mock
            tokens_in  = int(len(en_content.split()) * 1.3)
            tokens_out = 0
            cost_usd   = (tokens_in * DeepSeekClient.PRICE_IN +
                          tokens_out * DeepSeekClient.PRICE_OUT)
            lat_en_ms  = 0.0

        bytes_en = len(en_content.encode('utf-8'))

        # ── 1337 (project → wire encode) ─────────────────────────────────────
        t1 = time.perf_counter()
        # Projeta o conteúdo real (DeepSeek ou mock) para COGON
        project_content = en_content if self.use_deepseek else content_mock
        curr = project_text(project_content, agent["base_sem"])
        prev = self._prev[aid]
        seq  = self._next_seq()

        used_delta   = False
        axes_changed = 0

        if prev is None or round_num == 0:
            wire = encode_wire_cogon(curr, self._pfx, seq, self._align)
        else:
            changes = sparse_delta(prev, curr, self.threshold)
            axes_changed = len(changes)
            if changes:
                wire       = encode_wire_delta(prev.id, changes, self._pfx, seq, self._align)
                used_delta = True
            else:
                # ACK mínimo
                wire = self._pfx + struct.pack('<I', seq) + bytes([5]) + self._align + bytes([0])

        lat_1337_us = (time.perf_counter() - t1) * 1_000_000
        self._prev[aid] = curr

        return MsgRecord(
            agent_id=aid, round_num=round_num,
            used_delta=used_delta, axes_changed=axes_changed,
            bytes_1337=len(wire), bytes_en=bytes_en,
            tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost_usd,
            latency_1337_us=lat_1337_us, latency_en_ms=lat_en_ms,
        )

    def _convergence(self):
        cogons = [c for c in self._prev.values() if c is not None]
        if len(cogons) < 2:
            return 1.0
        pairs = list(combinations(cogons, 2))
        return sum(leet_dist(a, b) for a, b in pairs) / len(pairs)

    # ── run ───────────────────────────────────────────────────────────────────
    def run(self, verbose: bool = True) -> ComparisonMetrics:
        mode = "DeepSeek REAL" if self.use_deepseek else "Mock (hardcoded)"
        print(f"\n{'='*72}")
        print(f"EXPERIMENTO: 1337 vs ENGLISH — {self.topic}")
        print(f"{'='*72}")
        print(f"Agentes: {len(AGENTS_CONFIG)} | Rounds: {self.rounds} | "
              f"Modo: {mode} | Workers: {self.workers if self.use_deepseek else 1}")

        t0 = time.perf_counter()

        for rnd in range(self.rounds):
            if verbose:
                print(f"\n--- Round {rnd+1}/{self.rounds} ---")

            if self.use_deepseek:
                # Chamadas paralelas ao DeepSeek
                records_this_round = [None] * len(AGENTS_CONFIG)
                with ThreadPoolExecutor(max_workers=self.workers) as ex:
                    futures = {ex.submit(self._process, ag, rnd): i
                               for i, ag in enumerate(AGENTS_CONFIG)}
                    for fut in as_completed(futures):
                        records_this_round[futures[fut]] = fut.result()
            else:
                records_this_round = [self._process(ag, rnd) for ag in AGENTS_CONFIG]

            for rec, ag in zip(records_this_round, AGENTS_CONFIG):
                self.metrics.records.append(rec)
                if verbose:
                    tag = (f"DELTA({rec.axes_changed} eixos)" if rec.used_delta
                           else "COGON")
                    lat = (f" [{rec.latency_en_ms:.0f}ms]" if rec.latency_en_ms > 0
                           else f" [{rec.latency_1337_us:.0f}µs]")
                    print(f"  {ag['name']:18} | {tag:18} | "
                          f"1337={rec.bytes_1337:4}B  EN={rec.bytes_en:4}B"
                          f"  tok={rec.tokens_in+rec.tokens_out:4}{lat}")

            conv = self._convergence()
            self.metrics.conv_hist.append(conv)
            if verbose:
                print(f"  Convergência dist média: {conv:.4f}")

        self.metrics.duration_ms = (time.perf_counter() - t0) * 1000
        return self.metrics


# ══════════════════════════════════════════════════════════════════════════════
# RELATÓRIO
# ══════════════════════════════════════════════════════════════════════════════

def pct(n, h): return f"+{n:.1f}%" if n >= 0 else f"{n:.1f}%"

def percentile(lst, p):
    if not lst: return 0.0
    idx = max(0, int(len(lst) * p / 100) - 1)
    return lst[idx]

def print_report(m: ComparisonMetrics, topic: str):
    pa = m.per_agent()
    pr = m.per_round()

    print(f"\n{'='*72}")
    print(f"RELATÓRIO: 1337 vs ENGLISH  —  {topic}")
    print(f"{'='*72}")

    # ── tabela principal ──────────────────────────────────────────────────────
    print("\n┌─────────────────────────┬──────────────────┬──────────────────┬─────────────┐")
    print("│ Métrica                 │ 1337 (wire bin)  │ English          │ Ganho 1337  │")
    print("├─────────────────────────┼──────────────────┼──────────────────┼─────────────┤")

    def row(label, v1, ve, unit="", invert=False):
        gain = (1 - v1 / ve) * 100 if ve else 0
        if invert: gain = -gain
        sym = "+" if gain >= 0 else ""
        return (f"│ {label:23} │ {v1:>12,.0f} {unit:3} │ "
                f"{ve:>12,.0f} {unit:3} │ {sym}{gain:>6.1f}%    │")

    print(row("Bytes totais", m.bytes_1337, m.bytes_en, "B"))
    print(row("Mensagens", len(m.records), len(m.records), ""))
    print(row("Tokens input", 0, m.tokens_in, "tok"))
    print(row("Tokens output", 0, m.tokens_out, "tok"))
    print(row("Tokens total", 0, m.tokens_in + m.tokens_out, "tok"))
    print(f"│ {'Custo total (USD)':23} │ {'$0.0000':>16} │ ${m.cost_total:>14.4f} │ {'100.0%':>11}  │")
    print(f"│ {'Taxa compressão':23} │ {m.compression:>14.2f}x    │ {'1.00x':>16} │ {'':11}  │")
    print(f"│ {'Msgs COGON completo':23} │ {m.cogon_msgs:>16,} │ {'—':>16} │ {'':11}  │")
    print(f"│ {'Msgs SparseDelta':23} │ {m.delta_msgs:>16,} │ {'—':>16} │ {'':11}  │")
    print(f"│ {'Delta coverage':23} │ {m.delta_ratio*100:>15.1f}% │ {'N/A':>16} │ {'':11}  │")
    print(f"│ {'Bytes salvos (delta)':23} │ {m.bytes_saved_delta:>14,} B │ {'—':>16} │ {'':11}  │")
    print(f"│ {'Duração total (ms)':23} │ {m.duration_ms:>14.1f}    │ {'—':>16} │ {'':11}  │")
    print("└─────────────────────────┴──────────────────┴──────────────────┴─────────────┘")

    # ── velocidade / latência ──────────────────────────────────────────────────
    print(f"\nVELOCIDADE E LATÊNCIA")
    print("─" * 72)
    total_sec = m.duration_ms / 1000
    n = len(m.records)
    print(f"  Throughput geral:      {n/total_sec:.1f} msgs/s  |  "
          f"{m.bytes_1337/total_sec/1024:.1f} KB/s (1337)  |  "
          f"{m.bytes_en/total_sec/1024:.1f} KB/s (EN)")

    lat1 = m.latency_1337_us_list()
    print(f"\n  Latência 1337 (µs)  [encode + delta]:")
    print(f"    P50={percentile(lat1,50):.1f}  P95={percentile(lat1,95):.1f}  "
          f"P99={percentile(lat1,99):.1f}  max={max(lat1):.1f}  avg={sum(lat1)/len(lat1):.1f}")

    late = m.latency_en_ms_list()
    if late:
        print(f"\n  Latência DeepSeek (ms)  [API real]:")
        print(f"    P50={percentile(late,50):.0f}  P95={percentile(late,95):.0f}  "
              f"P99={percentile(late,99):.0f}  max={max(late):.0f}  avg={sum(late)/len(late):.0f}")
    else:
        print(f"\n  Latência English:      0 ms (mock hardcoded)")

    # ── detalhes delta ────────────────────────────────────────────────────────
    print(f"\nDETALHES DELTA")
    print("─" * 72)
    cogon_b  = WIRE_HEADER + WIRE_COGON_PAYLOAD
    delta_b  = WIRE_HEADER + SPARSE_HEADER + m.avg_axes * SPARSE_ENTRY if m.delta_msgs else 0
    print(f"  Eixos alterados/delta: avg={m.avg_axes:.1f} de {FIXED_DIMS}")
    print(f"  Tamanho COGON full:    {cogon_b} B")
    if m.delta_msgs:
        print(f"  Tamanho SparseDelta:   ~{delta_b:.0f} B  "
              f"(−{cogon_b-delta_b:.0f} B = −{(1-delta_b/cogon_b)*100:.1f}%)")
        print(f"  Total economizado:     {m.bytes_saved_delta:,} B ao longo de {m.rounds} rounds")

    # ── convergência ──────────────────────────────────────────────────────────
    if m.conv_hist:
        print(f"\nCONVERGÊNCIA SEMÂNTICA (dist média entre {len(AGENTS_CONFIG)} agentes)")
        print("─" * 72)
        h = m.conv_hist
        hi, lo = max(h), min(h)
        span = hi - lo if hi != lo else 1e-9
        chars = "▁▂▃▄▅▆▇█"
        line = ''.join(chars[min(7, int((v-lo)/span*7))] for v in h)
        trend = "convergindo" if h[-1] < h[0] else "divergindo"
        print(f"  {h[0]:.4f} → {h[-1]:.4f}  [{trend}  Δ={h[0]-h[-1]:+.4f}  "
              f"{(h[0]-h[-1])/h[0]*100:+.1f}%]")
        print(f"  Sparkline: {line}")
        # por round (amostras)
        sample = list(range(0, min(5, m.rounds))) + list(range(max(0, m.rounds-3), m.rounds))
        seen = set()
        for ri, rv in enumerate(h):
            if ri in sample and ri not in seen:
                seen.add(ri)
                rdata = pr.get(ri, {})
                dc = rdata.get("delta", 0); mc = rdata.get("msgs", 0)
                bar = "▓"*dc + "░"*(mc-dc)
                print(f"  R{ri+1:3}: dist={rv:.4f}  [{bar}]")

    # ── custo por agente ──────────────────────────────────────────────────────
    print(f"\nCUSTO E BYTES POR AGENTE")
    print("─" * 72)
    print("┌─────────────────────┬───────┬──────────┬──────────┬────────┬──────────┬──────────┐")
    print("│ Agente              │ Msgs  │ B(1337)  │ B(EN)    │ Ratio  │ Tokens   │ Custo$   │")
    print("├─────────────────────┼───────┼──────────┼──────────┼────────┼──────────┼──────────┤")
    for ag in AGENTS_CONFIG:
        aid = ag["id"]; e = pa.get(aid, {})
        b1  = e.get("bytes_1337",0); be = e.get("bytes_en",0)
        tok = e.get("tokens_in",0) + e.get("tokens_out",0)
        cost= e.get("cost_usd",0.0); msgs= e.get("msgs",0)
        ratio = be/b1 if b1 else 0
        print(f"│ {ag['name']:19} │ {msgs:5} │ {b1:8,} │ {be:8,} │ {ratio:5.2f}x │ "
              f"{tok:8,} │ ${cost:7.4f}  │")
    print("└─────────────────────┴───────┴──────────┴──────────┴────────┴──────────┴──────────┘")

    # ── custo total do processo ───────────────────────────────────────────────
    print(f"\nCUSTO TOTAL DO PROCESSO")
    print("─" * 72)
    tok_total = m.tokens_in + m.tokens_out
    print(f"  Tokens input:          {m.tokens_in:>10,}")
    print(f"  Tokens output:         {m.tokens_out:>10,}")
    print(f"  Tokens TOTAL:          {tok_total:>10,}")
    print(f"  Custo English (USD):  ${m.cost_total:>10.4f}")
    print(f"  Custo 1337   (USD):   ${0.0:>10.4f}  ← zero tokens de transporte")
    print(f"  Economia:             ${m.cost_total:>10.4f}  (100%)")
    print(f"  Modo:                  {'DeepSeek API real' if m.deepseek_used else 'Mock estimado'}")
    if not m.deepseek_used:
        print(f"  (use --deepseek para custos reais da API)")

    # ── conclusão ─────────────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print(f"CONCLUSÃO")
    print(f"{'='*72}")
    print(f"  Agentes:              {len(AGENTS_CONFIG)} personagens")
    print(f"  Mensagens totais:     {len(m.records)}")
    print(f"  Compressão geral:     {m.compression:.2f}x  ({(1-1/m.compression)*100:.1f}% menor que English)")
    print(f"  Delta coverage:       {m.delta_ratio*100:.1f}%  ({m.delta_msgs} de {len(m.records)} msgs)")
    if m.delta_msgs:
        print(f"  Eficiência delta:     {m.avg_axes:.1f} eixos/msg  → "
              f"{WIRE_HEADER+SPARSE_HEADER+m.avg_axes*SPARSE_ENTRY:.0f}B vs {WIRE_HEADER+WIRE_COGON_PAYLOAD}B")
    print(f"  Bytes totais 1337:    {m.bytes_1337:,} B")
    print(f"  Bytes totais EN:      {m.bytes_en:,} B")
    if m.conv_hist:
        print(f"  Convergência:         {(m.conv_hist[0]-m.conv_hist[-1])/m.conv_hist[0]*100:+.1f}% ao longo de {m.rounds} rounds")
    print(f"  Custo LLM English:   ${m.cost_total:.4f}  |  Custo 1337: $0.0000")
    print(f"  Duração:              {m.duration_ms:.1f} ms  ({len(m.records)/m.duration_ms*1000:.0f} msgs/s)\n")


def save_report(m: ComparisonMetrics, topic: str, report_dir: str):
    os.makedirs(report_dir, exist_ok=True)
    pa = m.per_agent()
    report = {
        "timestamp": datetime.now().isoformat(),
        "topic": topic, "rounds": m.rounds,
        "agents": [a["name"] for a in AGENTS_CONFIG],
        "deepseek_used": m.deepseek_used,
        "metrics": {
            "bytes_1337": m.bytes_1337, "bytes_en": m.bytes_en,
            "compression": round(m.compression, 4),
            "cogon_msgs": m.cogon_msgs, "delta_msgs": m.delta_msgs,
            "delta_ratio": round(m.delta_ratio, 4),
            "avg_axes_changed": round(m.avg_axes, 2),
            "bytes_saved_delta": m.bytes_saved_delta,
            "tokens_in": m.tokens_in, "tokens_out": m.tokens_out,
            "tokens_total": m.tokens_in + m.tokens_out,
            "cost_english_usd": round(m.cost_total, 6),
            "cost_1337_usd": 0.0,
            "duration_ms": round(m.duration_ms, 2),
            "throughput_msgs_s": round(len(m.records) / m.duration_ms * 1000, 1),
        },
        "convergence_history": [round(v, 4) for v in m.conv_hist],
        "per_agent": {
            aid: {**v, "cost_usd": round(v["cost_usd"], 6),
                  "compression": round(v["bytes_en"]/v["bytes_1337"], 3) if v["bytes_1337"] else 0}
            for aid, v in pa.items()
        },
    }
    fname = f"{report_dir}/comparison_{int(time.time())}.json"
    with open(fname, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Relatório salvo em: {fname}")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description='1337 vs English — com DeepSeek, 15 agentes, métricas completas',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos:
  python comparison_1337_vs_english.py --rounds 25
  python comparison_1337_vs_english.py --rounds 25 --deepseek
  python comparison_1337_vs_english.py --rounds 10 --deepseek --workers 8
  python comparison_1337_vs_english.py --rounds 50 --topic "Justiça" --quiet
        '''
    )
    p.add_argument('-r','--rounds',    type=int,   default=25,         help='Rounds (default: 25)')
    p.add_argument('-t','--topic',     type=str,   default="Eros (Amor)", help='Tópico')
    p.add_argument('--threshold',      type=float, default=0.01,       help='Delta threshold (default: 0.01)')
    p.add_argument('--deepseek',       action='store_true',            help='Usar DeepSeek API real')
    p.add_argument('--workers',        type=int,   default=5,          help='Workers paralelos DeepSeek (default: 5)')
    p.add_argument('-q','--quiet',     action='store_true',            help='Sem detalhes por round')
    p.add_argument('--no-save',        action='store_true',            help='Não salvar JSON')
    p.add_argument('--report-dir',     type=str,   default='./comparison_reports')
    return p.parse_args()


def main():
    args = parse_args()
    c = Comparison(
        topic=args.topic, rounds=args.rounds,
        delta_threshold=args.threshold,
        use_deepseek=args.deepseek,
        workers=args.workers,
    )
    metrics = c.run(verbose=not args.quiet)
    print_report(metrics, args.topic)
    if not args.no_save:
        save_report(metrics, args.topic, args.report_dir)
    print("Experimento concluído.")


if __name__ == "__main__":
    main()
