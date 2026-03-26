#!/usr/bin/env python3
"""
1337 Rede Interativa — 2-4 agentes IA conversando em linguagem 1337.

Uso:
    python net1337.py --scenario incident          # Mock (sem API)
    DEEPSEEK_API_KEY=sk-... python net1337.py      # DeepSeek
    ANTHROPIC_API_KEY=sk-... python net1337.py     # Claude

Comandos interativos:
    /inject <texto>              Broadcast pra todos os agentes
    /talk <agente> <texto>       Fala direto com um agente
    /agents chat [N]             Agentes conversam N rounds entre si
    /status                      Estado de todos os agentes
    /heatmap <agente|all>        Heatmap ASCII dos 32 eixos
    /delta <agente>              O que mudou desde o último turno
    /dist <agente1> <agente2>    Distância semântica entre agentes
    /blend <agente1> <agente2>   Fusão hipotética dos estados
    /scenario <nome>             Carrega cenário (incident, brainstorm, anomaly, devops)
    /export [arquivo.json]       Exporta log
    /help                        Lista de comandos
    /quit                        Sai
"""

import argparse
import asyncio
import json
import os
import sys
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

FIXED_DIMS = 32

# Os 32 eixos canônicos
AXES = [
    {"idx": 0, "code": "A0", "name": "VIA", "group": "A"},
    {"idx": 1, "code": "A1", "name": "CORRESPONDÊNCIA", "group": "A"},
    {"idx": 2, "code": "A2", "name": "VIBRAÇÃO", "group": "A"},
    {"idx": 3, "code": "A3", "name": "POLARIDADE", "group": "A"},
    {"idx": 4, "code": "A4", "name": "RITMO", "group": "A"},
    {"idx": 5, "code": "A5", "name": "CAUSA_EFEITO", "group": "A"},
    {"idx": 6, "code": "A6", "name": "GÊNERO", "group": "A"},
    {"idx": 7, "code": "A7", "name": "SISTEMA", "group": "A"},
    {"idx": 8, "code": "A8", "name": "ESTADO", "group": "A"},
    {"idx": 9, "code": "A9", "name": "PROCESSO", "group": "A"},
    {"idx": 10, "code": "A10", "name": "RELAÇÃO", "group": "A"},
    {"idx": 11, "code": "A11", "name": "SINAL", "group": "A"},
    {"idx": 12, "code": "A12", "name": "ESTABILIDADE", "group": "A"},
    {"idx": 13, "code": "A13", "name": "VALÊNCIA_ONTOLÓGICA", "group": "A"},
    {"idx": 14, "code": "B1", "name": "VERIFICABILIDADE", "group": "B"},
    {"idx": 15, "code": "B2", "name": "TEMPORALIDADE", "group": "B"},
    {"idx": 16, "code": "B3", "name": "COMPLETUDE", "group": "B"},
    {"idx": 17, "code": "B4", "name": "CAUSALIDADE", "group": "B"},
    {"idx": 18, "code": "B5", "name": "REVERSIBILIDADE", "group": "B"},
    {"idx": 19, "code": "B6", "name": "CARGA", "group": "B"},
    {"idx": 20, "code": "B7", "name": "ORIGEM", "group": "B"},
    {"idx": 21, "code": "B8", "name": "VALÊNCIA_EPISTÊMICA", "group": "B"},
    {"idx": 22, "code": "C1", "name": "URGÊNCIA", "group": "C"},
    {"idx": 23, "code": "C2", "name": "IMPACTO", "group": "C"},
    {"idx": 24, "code": "C3", "name": "AÇÃO", "group": "C"},
    {"idx": 25, "code": "C4", "name": "VALOR", "group": "C"},
    {"idx": 26, "code": "C5", "name": "ANOMALIA", "group": "C"},
    {"idx": 27, "code": "C6", "name": "AFETO", "group": "C"},
    {"idx": 28, "code": "C7", "name": "DEPENDÊNCIA", "group": "C"},
    {"idx": 29, "code": "C8", "name": "VETOR_TEMPORAL", "group": "C"},
    {"idx": 30, "code": "C9", "name": "NATUREZA", "group": "C"},
    {"idx": 31, "code": "C10", "name": "VALÊNCIA_DE_AÇÃO", "group": "C"},
]

# Cenários pré-definidos
SCENARIOS = {
    "incident": {
        "name": "Incidente de Produção",
        "agents": [
            {"name": "Engenheiro", "persona": "Você é um engenheiro de sistemas sênior. Foco: estabilidade, causa raiz, ação corretiva. Direto e técnico. Sempre pensa em rollback e monitoramento."},
            {"name": "Analista", "persona": "Você é um analista de impacto de negócios. Foco: consequências, stakeholders, comunicação externa. Pensa em quem é afetado e como comunicar."},
        ],
        "stimulus": "O deploy das 14h causou timeout em cascata no serviço de pagamentos. 30% dos clientes não conseguem finalizar compras.",
    },
    "brainstorm": {
        "name": "Brainstorm de Feature",
        "agents": [
            {"name": "Produto", "persona": "Você é product manager visionário. Foco: valor pro usuário, priorização, validação. Pensa grande mas pragmático na execução."},
            {"name": "Arquiteto", "persona": "Você é arquiteto de software pragmático. Foco: viabilidade, trade-offs, escalabilidade. Busca a solução mais elegante e simples."},
        ],
        "stimulus": "Queremos adicionar colaboração em tempo real no editor. Múltiplos usuários editando ao mesmo tempo.",
    },
    "anomaly": {
        "name": "Detecção de Anomalia",
        "agents": [
            {"name": "Monitor", "persona": "Você é agente de monitoramento. Observa métricas, detecta desvios, alerta anomalias. Factual e preciso — reporta sem especular."},
            {"name": "Investigador", "persona": "Você é agente investigativo. Recebe alertas, busca causas raiz. Faz perguntas, cruza dados, propõe hipóteses."},
        ],
        "stimulus": "Latência do /api/users subiu de 50ms para 2300ms nos últimos 5 minutos. Sem deploy recente. CPU e memória normais.",
    },
    "devops": {
        "name": "War Room DevOps",
        "agents": [
            {"name": "SRE", "persona": "Você é SRE. Foco: disponibilidade, SLOs, automação. Pensa em 9s de uptime e blast radius."},
            {"name": "Dev", "persona": "Você é dev sênior do serviço afetado. Conhece o código. Foco: o que mudou, onde tá o bug, como fixar rápido."},
            {"name": "EM", "persona": "Você é engineering manager. Foco: coordenação, comunicação, priorização de pessoas. Gerencia o incidente."},
        ],
        "stimulus": "Alerta PagerDuty: serviço de autenticação retornando 503. Todos os logins falhando. Última mudança: migration de banco 2h atrás.",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# TIPOS BÁSICOS (inline para auto-contido)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Cogon:
    id: str
    sem: list[float]
    unc: list[float]
    stamp: int
    raw: Optional[dict] = None

    @classmethod
    def zero(cls) -> 'Cogon':
        return cls(
            id="00000000-0000-0000-0000-000000000000",
            sem=[1.0] * FIXED_DIMS,
            unc=[0.0] * FIXED_DIMS,
            stamp=0,
        )

    @classmethod
    def new(cls, sem: list[float], unc: list[float]) -> 'Cogon':
        return cls(
            id=str(uuid.uuid4()),
            sem=sem,
            unc=unc,
            stamp=int(datetime.now().timestamp() * 1e9),
        )

    def is_zero(self) -> bool:
        return self.id == "00000000-0000-0000-0000-000000000000" and self.stamp == 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sem": self.sem,
            "unc": self.unc,
            "stamp": self.stamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'Cogon':
        return cls(**d)


@dataclass
class Msg1337:
    sender: str
    receiver: str
    intent: str
    payload: 'Cogon'
    surface: dict
    ref_hash: Optional[str] = None
    patch: Optional[list[float]] = None

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "intent": self.intent,
            "payload": self.payload.to_dict(),
            "surface": self.surface,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRAÇÃO COM RUST (tenta PyO3, depois ctypes, depois fallback)
# ═══════════════════════════════════════════════════════════════════════════════

RUST_BACKEND = None
_rust = None
_lib = None

# Tentativa 1: PyO3
try:
    import leet_core as _rust
    RUST_BACKEND = "pyo3"
    print("✓ Rust backend: PyO3 (leet_core importado)")
except ImportError:
    pass

# Tentativa 2: ctypes FFI
if _rust is None:
    import ctypes
    import glob
    
    search_paths = [
        "leet1337/target/release/libleet_core.so",
        "leet1337/target/release/libleet_core.dylib",
        "../leet1337/target/release/libleet_core.so",
        "../leet1337/target/release/libleet_core.dylib",
    ]
    for path in search_paths:
        matches = glob.glob(path)
        if matches:
            try:
                _lib = ctypes.CDLL(matches[0])
                RUST_BACKEND = "ffi"
                print(f"✓ Rust backend: FFI ctypes ({matches[0]})")
                break
            except OSError:
                continue

if RUST_BACKEND is None:
    print("⚠ Rust backend NÃO disponível. Humano usará fallback pure-python.")
    print("  Para ativar Rust:")
    print("    PyO3:  cd leet1337 && maturin develop --features python")
    print("    FFI:   cd leet1337 && cargo build --release")


class RustBridge:
    """Bridge Rust unificado (PyO3 ou FFI)."""

    def __init__(self):
        self.mode = RUST_BACKEND

    def available(self) -> bool:
        return self.mode is not None

    def create_cogon(self, sem: list[float], unc: list[float]) -> str:
        """Cria COGON via Rust. Retorna JSON."""
        if self.mode == "pyo3" and _rust:
            return _rust.cogon_new(sem, unc)
        elif self.mode == "ffi" and _lib:
            c_sem = (ctypes.c_float * 32)(*sem)
            c_unc = (ctypes.c_float * 32)(*unc)
            _lib.leet_cogon_new.restype = ctypes.c_char_p
            result = _lib.leet_cogon_new(c_sem, c_unc, 32)
            return result.decode("utf-8") if result else None
        return None

    def cogon_zero(self) -> str:
        """COGON_ZERO via Rust."""
        if self.mode == "pyo3" and _rust:
            return _rust.cogon_zero()
        elif self.mode == "ffi" and _lib:
            _lib.leet_cogon_zero.restype = ctypes.c_char_p
            result = _lib.leet_cogon_zero()
            return result.decode("utf-8") if result else None
        return None

    def blend(self, c1_json: str, c2_json: str, alpha: float) -> str:
        """BLEND via Rust."""
        if self.mode == "pyo3" and _rust:
            return _rust.blend(c1_json, c2_json, alpha)
        elif self.mode == "ffi" and _lib:
            _lib.leet_blend.restype = ctypes.c_char_p
            _lib.leet_blend.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_float]
            result = _lib.leet_blend(c1_json.encode(), c2_json.encode(), alpha)
            return result.decode("utf-8") if result else None
        return None

    def dist(self, c1_json: str, c2_json: str) -> float:
        """DIST via Rust."""
        if self.mode == "pyo3" and _rust:
            return _rust.dist(c1_json, c2_json)
        elif self.mode == "ffi" and _lib:
            _lib.leet_dist.restype = ctypes.c_float
            _lib.leet_dist.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            return _lib.leet_dist(c1_json.encode(), c2_json.encode())
        return 0.0

    def version(self) -> str:
        if self.mode == "pyo3" and _rust:
            return _rust.version()
        elif self.mode == "ffi" and _lib:
            _lib.leet_version.restype = ctypes.c_char_p
            return _lib.leet_version().decode("utf-8")
        return "N/A"


# ═══════════════════════════════════════════════════════════════════════════════
# OPERADORES PYTHON (fallback quando Rust não disponível)
# ═══════════════════════════════════════════════════════════════════════════════

import math


def py_blend(c1: 'Cogon', c2: 'Cogon', alpha: float) -> 'Cogon':
    """Fusão semântica interpolada."""
    sem = [alpha * s1 + (1 - alpha) * s2 for s1, s2 in zip(c1.sem, c2.sem)]
    unc = [max(u1, u2) for u1, u2 in zip(c1.unc, c2.unc)]
    return Cogon.new(sem=sem, unc=unc)


def py_dist(c1: 'Cogon', c2: 'Cogon') -> float:
    """Distância cosseno ponderada por (1-unc)."""
    weights = [1 - max(u1, u2) for u1, u2 in zip(c1.unc, c2.unc)]
    dot = sum(w * s1 * s2 for w, s1, s2 in zip(weights, c1.sem, c2.sem))
    norm1 = math.sqrt(sum(w * s * s for w, s in zip(weights, c1.sem)))
    norm2 = math.sqrt(sum(w * s * s for w, s in zip(weights, c2.sem)))
    if norm1 == 0 or norm2 == 0:
        return 1.0
    cosine = max(-1.0, min(1.0, dot / (norm1 * norm2)))
    return 1.0 - cosine


def py_anomaly_score(cogon: 'Cogon', history: list['Cogon']) -> float:
    """Distância média do centroide histórico."""
    if not history:
        return 1.0
    n = len(history)
    centroid_sem = [sum(h.sem[i] for h in history) / n for i in range(FIXED_DIMS)]
    centroid_unc = [sum(h.unc[i] for h in history) / n for i in range(FIXED_DIMS)]
    centroid = Cogon.new(sem=centroid_sem, unc=centroid_unc)
    return py_dist(cogon, centroid)


# ═══════════════════════════════════════════════════════════════════════════════
# LLM BACKENDS
# ═══════════════════════════════════════════════════════════════════════════════

class LLMBackend(ABC):
    """Interface para backends de LLM."""

    @abstractmethod
    def call(self, system: str, user: str) -> str:
        """Chama o LLM e retorna texto."""
        pass

    @abstractmethod
    def project(self, text: str) -> tuple[list[float], list[float]]:
        """Projeta texto nos 32 eixos. Retorna (sem, unc)."""
        pass

    @abstractmethod
    def reconstruct(self, cogon: 'Cogon') -> str:
        """Reconstrói texto a partir de COGON."""
        pass


class MockBackend(LLMBackend):
    """Backend mock — heurísticas de keywords, sem API."""

    def call(self, system: str, user: str) -> str:
        # Respostas mock por tipo de persona
        if "engenheiro" in system.lower() or "SRE" in system:
            return "Verificando logs. Parece ser um problema de timeout na conexão com o banco. Sugiro rollback imediato."
        elif "analista" in system.lower():
            return "Isso afeta diretamente a receita. Precisamos comunicar os clientes e ativar o plano de contingência."
        elif "product" in system.lower():
            return "Isso aumenta muito o engajamento. Vamos precisar de Operações Transformadas para sincronização."
        elif "arquiteto" in system.lower():
            return "WebSockets com fallback para polling. CRDTs para resolução de conflitos."
        elif "monitor" in system.lower():
            return "ALERTA: Latência anômala detectada. Threshold excedido em 46x."
        elif "investigador" in system.lower():
            return "Sem deploy... suspeito de query N+1 ou dead lock. Vamos verificar slow query log."
        elif "dev" in system.lower():
            return "A migration pode ter deixado uma transação aberta. Vou verificar."
        elif "manager" in system.lower() or "EM" in system:
            return "Vamos focar em restaurar o serviço primeiro. Já acionei o war room."
        return "Entendido. Processando informação."

    def project(self, text: str) -> tuple[list[float], list[float]]:
        text_lower = text.lower()
        sem = [0.5] * 32
        unc = [0.2] * 32

        if "urgente" in text_lower or "urgência" in text_lower:
            sem[22] = 0.95  # C1_URGÊNCIA
            sem[24] = 0.9   # C3_AÇÃO

        if "caiu" in text_lower or "falhou" in text_lower or "erro" in text_lower or "down" in text_lower:
            sem[8] = 0.9    # A8_ESTADO
            sem[26] = 0.9   # C5_ANOMALIA
            sem[22] = 0.85  # C1_URGÊNCIA

        if "deploy" in text_lower or "processo" in text_lower:
            sem[9] = 0.85   # A9_PROCESSO
            sem[30] = 0.8   # C9_NATUREZA

        if "reverter" in text_lower or "rollback" in text_lower:
            sem[18] = 0.9   # B5_REVERSIBILIDADE

        return sem, unc

    def reconstruct(self, cogon: 'Cogon') -> str:
        # Encontra top 3 eixos
        top = sorted(range(32), key=lambda i: cogon.sem[i], reverse=True)[:3]
        parts = [f"{AXES[i]['name']}={cogon.sem[i]:.2f}" for i in top if cogon.sem[i] > 0.3]
        return f"[COGON: {', '.join(parts)}]"


class DeepSeekBackend(LLMBackend):
    """Backend DeepSeek API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            import openai
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            self.model = "deepseek-chat"
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

    def call(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=256,
        )
        return response.choices[0].message.content

    def project(self, text: str) -> tuple[list[float], list[float]]:
        # Simplificado: usa heurísticas mock para projeção
        mock = MockBackend()
        return mock.project(text)

    def reconstruct(self, cogon: 'Cogon') -> str:
        mock = MockBackend()
        return mock.reconstruct(cogon)


class AnthropicBackend(LLMBackend):
    """Backend Anthropic Claude API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = "claude-sonnet-4-20250514"
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

    def call(self, system: str, user: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    def project(self, text: str) -> tuple[list[float], list[float]]:
        mock = MockBackend()
        return mock.project(text)

    def reconstruct(self, cogon: 'Cogon') -> str:
        mock = MockBackend()
        return mock.reconstruct(cogon)


def create_backend(name: str) -> LLMBackend:
    """Factory para criar backends."""
    if name == "mock":
        return MockBackend()
    elif name == "deepseek":
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        return DeepSeekBackend(key)
    elif name == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        return AnthropicBackend(key)
    raise ValueError(f"Unknown backend: {name}")


# ═══════════════════════════════════════════════════════════════════════════════
# PARTICIPANTES DA REDE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HumanParticipant:
    """O humano na rede 1337."""

    id: str
    name: str = "Humano"
    rust: Optional[RustBridge] = None
    llm: Optional[LLMBackend] = None
    history: list['Cogon'] = field(default_factory=list)

    def __post_init__(self):
        if self.llm is None:
            self.llm = MockBackend()

    def text_to_msg(self, text: str, receiver: str = "BROADCAST") -> Msg1337:
        """Fluxo: LLM projeta → Rust valida (se disponível) → MSG_1337."""
        sem, unc = self.llm.project(text)

        # Usa Rust se disponível
        if self.rust and self.rust.available():
            cogon_json = self.rust.create_cogon(sem, unc)
            if cogon_json:
                print(f"  🦀 COGON criado via Rust ({self.rust.mode})")
                cogon = Cogon.from_dict(json.loads(cogon_json))
            else:
                cogon = Cogon.new(sem=sem, unc=unc)
                print(f"  🐍 COGON criado via Python (fallback)")
        else:
            cogon = Cogon.new(sem=sem, unc=unc)
            print(f"  🐍 COGON criado via Python (fallback)")

        self.history.append(cogon)

        msg = Msg1337(
            sender=self.id,
            receiver=receiver,
            intent="ASSERT",
            payload=cogon,
            surface={
                "human_required": False,
                "urgency": sem[22],
                "reconstruct_depth": 3,
                "lang": "pt",
                "_text": text,
            },
        )
        return msg


@dataclass
class Agent1337:
    """Agente IA na rede 1337."""

    id: str
    name: str
    persona: str
    backend: LLMBackend
    history: list['Cogon'] = field(default_factory=list)
    msg_log: list[Msg1337] = field(default_factory=list)
    response_texts: list[str] = field(default_factory=list)

    def announce(self) -> Msg1337:
        """R20: COGON_ZERO antes de tudo."""
        return Msg1337(
            sender=self.id,
            receiver="BROADCAST",
            intent="SYNC",
            payload=Cogon.zero(),
            surface={"human_required": False, "_text": "I AM"},
        )

    def receive_and_respond(self, msg: Msg1337, all_agents: dict) -> list[Msg1337]:
        """Recebe MSG, processa, responde."""
        received_cogon = msg.payload
        self.history.append(received_cogon)

        # Reconstruir texto
        received_text = msg.surface.get("_text", "")
        if not received_text:
            received_text = self.backend.reconstruct(received_cogon)

        # Gerar resposta
        sender_name = "Humano"
        for aid, agent in all_agents.items():
            if aid == msg.sender:
                sender_name = getattr(agent, 'name', 'Humano')
                break

        context = self.response_texts[-3:] if self.response_texts else []
        prompt = f"""Você é: {self.persona}

Mensagem recebida de [{sender_name}]:
"{received_text}"

Contexto das suas falas anteriores:
{chr(10).join(context) if context else '(primeira interação)'}

Responda em caráter. Uma ou duas frases concisas e diretas. Em português."""

        response_text = self.backend.call(
            "Responda em caráter conforme a persona. Máximo 2 frases. Português.",
            prompt
        )
        self.response_texts.append(response_text)

        # Projetar em 1337
        sem, unc = self.backend.project(response_text)
        response_cogon = Cogon.new(sem=sem, unc=unc)

        # DELTA ou ASSERT
        use_delta = len(self.history) > 1 and py_dist(self.history[-1], response_cogon) < 0.3
        intent = "DELTA" if use_delta else "ASSERT"

        msg_out = Msg1337(
            sender=self.id,
            receiver=msg.sender if msg.receiver != "BROADCAST" else "BROADCAST",
            intent=intent,
            payload=response_cogon,
            surface={
                "human_required": True,
                "urgency": sem[22],
                "reconstruct_depth": 3,
                "lang": "pt",
                "_text": response_text,
            },
        )

        self.msg_log.append(msg_out)
        self.history.append(response_cogon)
        return [msg_out]


# ═══════════════════════════════════════════════════════════════════════════════
# ORQUESTRADOR DA REDE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Network1337:
    """Rede 1337 com agentes + humano."""

    rust: RustBridge
    llm_backend: LLMBackend
    agents: dict[str, Agent1337] = field(default_factory=dict)
    log: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self.human = HumanParticipant(
            id=f"HUMAN-{uuid.uuid4().hex[:8]}",
            rust=self.rust,
            llm=self.llm_backend,
        )
        self.all_participants: dict[str, Any] = {self.human.id: self.human}

    def add_agent(self, name: str, persona: str) -> Agent1337:
        if len(self.agents) >= 8:
            print("⚠ Máximo 8 agentes.")
            return None
        agent = Agent1337(
            id=str(uuid.uuid4()),
            name=name,
            persona=persona,
            backend=self.llm_backend,
        )
        self.agents[agent.id] = agent
        self.all_participants[agent.id] = agent
        return agent

    def remove_agent(self, name: str):
        for aid, agent in list(self.agents.items()):
            if agent.name.lower() == name.lower():
                del self.agents[aid]
                del self.all_participants[aid]
                print(f"  Removido: {agent.name}")
                return
        print(f"  Agente '{name}' não encontrado.")

    def handshake(self):
        """C5: todos anunciam COGON_ZERO."""
        if self.rust.available():
            zero_json = self.rust.cogon_zero()
            print(f"  Humano: I AM 🦀 (via Rust)")
        else:
            print(f"  Humano: I AM 🐍")

        for agent in self.agents.values():
            msg = agent.announce()
            self._log_msg(msg, agent.name, "REDE")
            print(f"  {agent.name}: I AM ✓")

    def inject(self, text: str) -> list[dict]:
        """Humano injeta texto → todos os agentes reagem."""
        msg = self.human.text_to_msg(text, "BROADCAST")
        self._log_msg(msg, "Humano", "BROADCAST")
        self._render_msg(msg, "Humano", "BROADCAST")

        # Cada agente reage
        responses = []
        for agent in self.agents.values():
            agent_responses = agent.receive_and_respond(msg, self.all_participants)
            for resp in agent_responses:
                self._log_msg(resp, agent.name, self._resolve_name(resp.receiver))
                rendered = self._render_msg(resp, agent.name, self._resolve_name(resp.receiver))
                responses.append(rendered)
        return responses

    def talk(self, agent_name: str, text: str) -> str | None:
        """Humano fala diretamente com um agente."""
        agent = self._find_agent(agent_name)
        if not agent:
            print(f"  Agente '{agent_name}' não encontrado.")
            return None
        msg = self.human.text_to_msg(text, agent.id)
        self._log_msg(msg, "Humano", agent.name)

        responses = agent.receive_and_respond(msg, self.all_participants)
        for resp in responses:
            self._log_msg(resp, agent.name, "Humano")
            self._render_msg(resp, agent.name, "Humano")

    def agents_chat(self, rounds: int = 1):
        """Agentes conversam entre si. Humano observa."""
        agent_list = list(self.agents.values())
        if len(agent_list) < 2:
            print("  Precisa de pelo menos 2 agentes.")
            return

        for r in range(rounds):
            if rounds > 1:
                print(f"\n  ─── Round {r+1}/{rounds} ───")
            for i, agent in enumerate(agent_list):
                other = agent_list[(i + 1) % len(agent_list)]
                if other.msg_log:
                    last_msg = other.msg_log[-1]
                elif other.history:
                    last_msg = Msg1337(
                        sender=other.id,
                        receiver=agent.id,
                        intent="ASSERT",
                        payload=other.history[-1],
                        surface={"_text": other.response_texts[-1] if other.response_texts else "..."}
                    )
                else:
                    continue

                responses = agent.receive_and_respond(last_msg, self.all_participants)
                for resp in responses:
                    self._log_msg(resp, agent.name, self._resolve_name(resp.receiver))
                    self._render_msg(resp, agent.name, self._resolve_name(resp.receiver))

    def cmd_dist(self, name1: str, name2: str):
        """Distância semântica entre dois agentes."""
        a1 = self._find_agent(name1)
        a2 = self._find_agent(name2)
        if not a1 or not a2:
            return
        if not a1.history or not a2.history:
            print("  Agentes ainda não têm histórico.")
            return

        c1, c2 = a1.history[-1], a2.history[-1]

        if self.rust.available():
            d = self.rust.dist(json.dumps(c1.to_dict()), json.dumps(c2.to_dict()))
            src = "Rust"
        else:
            d = py_dist(c1, c2)
            src = "Python"

        label = "baixa" if d < 0.2 else "moderada" if d < 0.5 else "alta" if d < 0.8 else "extrema"
        print(f"  Distância ({src}): {d:.4f} ({label})")

    def cmd_blend(self, name1: str, name2: str, alpha: float = 0.5):
        """BLEND hipotético dos estados de dois agentes."""
        a1 = self._find_agent(name1)
        a2 = self._find_agent(name2)
        if not a1 or not a2 or not a1.history or not a2.history:
            return

        c1, c2 = a1.history[-1], a2.history[-1]

        if self.rust.available():
            result_json = self.rust.blend(json.dumps(c1.to_dict()), json.dumps(c2.to_dict()), alpha)
            result = Cogon.from_dict(json.loads(result_json)) if result_json else py_blend(c1, c2, alpha)
            src = "Rust"
        else:
            result = py_blend(c1, c2, alpha)
            src = "Python"

        print(f"  BLEND α={alpha} ({src}) — {a1.name} + {a2.name}:")
        print(render_heatmap(result))

    def cmd_heatmap(self, name: str):
        if name.lower() == "all":
            for agent in self.agents.values():
                if agent.history:
                    print(f"\n  [{agent.name}]")
                    print(render_heatmap(agent.history[-1]))
            return
        agent = self._find_agent(name)
        if agent and agent.history:
            print(f"  [{agent.name}] — Último COGON:")
            print(render_heatmap(agent.history[-1]))
        else:
            print(f"  Sem histórico.")

    def cmd_delta(self, name: str):
        agent = self._find_agent(name)
        if agent and len(agent.history) >= 2:
            print(f"  [{agent.name}] — Mudanças:")
            print(render_delta_diff(agent.history[-2], agent.history[-1]))
        else:
            print(f"  Precisa de pelo menos 2 turnos.")

    def cmd_status(self):
        for i, agent in enumerate(self.agents.values(), 1):
            a_score = py_anomaly_score(agent.history[-1], agent.history[:-1]) if len(agent.history) > 1 else 0.0
            print(f"  [{i}] {agent.name:15s}  history={len(agent.history):2d}  msgs={len(agent.msg_log):2d}  anomaly={a_score:.2f}")
        print(f"  [H] {'Humano':15s}  history={len(self.human.history):2d}  rust={'✓' if self.rust.available() else '✗'}")

    def cmd_history(self, name: str, n: int = 5):
        agent = self._find_agent(name)
        if not agent:
            return
        for cogon in agent.history[-n:]:
            top = sorted(range(32), key=lambda i: cogon.sem[i], reverse=True)[:3]
            top_str = ", ".join(f"{AXES[i]['name']}={cogon.sem[i]:.2f}" for i in top)
            print(f"  [{cogon.stamp}] {top_str}")

    def _find_agent(self, name: str) -> Agent1337 | None:
        for agent in self.agents.values():
            if agent.name.lower() == name.lower():
                return agent
        try:
            idx = int(name) - 1
            agents_list = list(self.agents.values())
            if 0 <= idx < len(agents_list):
                return agents_list[idx]
        except ValueError:
            pass
        print(f"  Agente '{name}' não encontrado. Use /agents pra listar.")
        return None

    def _resolve_name(self, participant_id: str) -> str:
        if participant_id == "BROADCAST":
            return "BROADCAST"
        if participant_id == self.human.id:
            return "Humano"
        for agent in self.agents.values():
            if agent.id == participant_id:
                return agent.name
        return participant_id[:8]

    def _log_msg(self, msg: Msg1337, sender_name: str, receiver_name: str):
        self.log.append({
            "sender": sender_name,
            "receiver": receiver_name,
            "intent": msg.intent,
            "text": msg.surface.get("_text", ""),
            "urgency": msg.surface.get("urgency", 0),
            "stamp": msg.payload.stamp,
        })

    def _render_msg(self, msg: Msg1337, sender_name: str, receiver_name: str):
        text = render_msg(msg, sender_name, receiver_name)
        print(text)
        return text

    def export(self, path: str):
        with open(path, "w") as f:
            json.dump(self.log, f, indent=2, default=str, ensure_ascii=False)
        print(f"  📁 Exportado: {path} ({len(self.log)} msgs)")


# ═══════════════════════════════════════════════════════════════════════════════
# RENDERERS
# ═══════════════════════════════════════════════════════════════════════════════

def render_msg(msg: Msg1337, sender: str, receiver: str) -> str:
    """Renderiza mensagem em box bonito."""
    text = msg.surface.get("_text", "")
    urgency = msg.surface.get("urgency", 0)
    intent = msg.intent

    # Ícone por intent
    icon = {
        "ASSERT": "◆",
        "QUERY": "?",
        "DELTA": "Δ",
        "SYNC": "↻",
        "ANOMALY": "⚠",
        "ACK": "✓",
    }.get(intent, "•")

    # Cor/destaque por urgência
    urgency_indicator = ""
    if urgency and urgency > 0.8:
        urgency_indicator = " 🔴"
    elif urgency and urgency > 0.5:
        urgency_indicator = " 🟡"

    lines = [
        f"┌─ {icon} [{sender}] → [{receiver}]{urgency_indicator}",
    ]
    
    # Quebra texto em linhas de 60 chars
    words = text.split()
    line = "│  "
    for word in words:
        if len(line) + len(word) > 62:
            lines.append(line)
            line = "│  " + word + " "
        else:
            line += word + " "
    if line.strip() != "│":
        lines.append(line)

    lines.append("└─" + "─" * 58)
    return "\n".join(lines)


def render_heatmap(cogon: 'Cogon', only_significant: bool = True) -> str:
    """Heatmap ASCII dos 32 eixos."""
    lines = []
    for ax in AXES:
        idx = ax["idx"]
        val = cogon.sem[idx]
        if only_significant and val < 0.6:
            continue
        # Barra ASCII
        bar_len = int(val * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        lines.append(f"  {ax['code']:3} {ax['name']:20} │{bar}│ {val:.2f}")
    return "\n".join(lines) if lines else "  (sem eixos significativos)"


def render_delta_diff(prev: 'Cogon', curr: 'Cogon') -> str:
    """Mostra eixos que mudaram > 0.1."""
    lines = []
    for ax in AXES:
        idx = ax["idx"]
        diff = curr.sem[idx] - prev.sem[idx]
        if abs(diff) > 0.1:
            arrow = "↑" if diff > 0 else "↓"
            lines.append(f"  {ax['code']:3} {ax['name']:20} {arrow} {diff:+.2f} ({prev.sem[idx]:.2f} → {curr.sem[idx]:.2f})")
    return "\n".join(lines) if lines else "  (sem mudanças significativas)"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def print_help():
    print("""
  CONVERSA:
    /inject <texto>              Broadcast pra todos os agentes
    /talk <agente> <texto>       Fala direto com um agente
    /agents chat [N]             Agentes conversam N rounds entre si
    (texto sem /)                Mesmo que /inject

  OBSERVAÇÃO:
    /status                      Estado de todos os agentes
    /heatmap <agente|all>        Heatmap ASCII dos 32 eixos
    /delta <agente>              O que mudou desde o último turno
    /dist <agente1> <agente2>    Distância semântica entre agentes
    /blend <agente1> <agente2>   Fusão hipotética dos estados
    /history <agente>            Últimos COGONs do agente
    /log [full]                  Log da conversa

  CONTROLE:
    /add <nome> <persona>        Adiciona agente (máx 4)
    /remove <nome>               Remove agente
    /scenario <nome>             Carrega cenário (incident, brainstorm, anomaly, devops)
    /agents                      Lista agentes ativos
    /export [arquivo.json]       Exporta log
    /verbose                     Toggle detalhes
    /rust                        Status do bridge Rust
    /help                        Esta lista
    /quit                        Sai
""")


def main():
    parser = argparse.ArgumentParser(description="1337 Rede Interativa")
    parser.add_argument("--backend", choices=["deepseek", "anthropic", "mock"], default=None,
                        help="LLM backend. Default: detecta pela API key presente.")
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    # Detectar backend
    if args.backend:
        backend_name = args.backend
    elif os.environ.get("DEEPSEEK_API_KEY"):
        backend_name = "deepseek"
    elif os.environ.get("ANTHROPIC_API_KEY"):
        backend_name = "anthropic"
    else:
        backend_name = "mock"

    try:
        backend = create_backend(backend_name)
    except (ValueError, ImportError) as e:
        print(f"Error: {e}")
        print("Falling back to mock backend.")
        backend = MockBackend()
        backend_name = "mock"

    # Inicializar Rust bridge
    rust = RustBridge()

    # Criar rede
    net = Network1337(rust, backend)

    # Carregar cenário ou modo interativo
    if args.scenario:
        sc = SCENARIOS[args.scenario]
        for ag in sc["agents"]:
            net.add_agent(ag["name"], ag["persona"])
        print(f"\n{'═'*60}")
        print(f"  1337 REDE — {sc['name']}")
        print(f"  Backend: {backend_name.upper()} | Rust: {'✓ ' + rust.mode if rust.available() else '✗ fallback Python'}")
        print(f"  Agentes: {', '.join(a.name for a in net.agents.values())}")
        print(f"{'═'*60}\n")
    else:
        print(f"\n{'═'*60}")
        print(f"  1337 REDE INTERATIVA")
        print(f"  Backend: {backend_name.upper()} | Rust: {'✓ ' + rust.mode if rust.available() else '✗ fallback Python'}")
        print(f"  Use /help pra ver comandos. /scenario <nome> pra carregar cenário.")
        print(f"{'═'*60}\n")

    # Handshake
    if net.agents:
        print("📡 Handshake C5...")
        net.handshake()
        print()

        # Estímulo inicial do cenário
        if args.scenario and "stimulus" in SCENARIOS[args.scenario]:
            print(f"💬 Estímulo inicial:")
            net.inject(SCENARIOS[args.scenario]["stimulus"])
            print()

    # Loop interativo
    while True:
        try:
            line = input("1337> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Saindo.")
            break

        if not line:
            continue

        if line.startswith("/"):
            parts = line.split(maxsplit=2)
            cmd = parts[0].lower()

            if cmd == "/quit" or cmd == "/exit":
                break
            elif cmd == "/help":
                print_help()
            elif cmd == "/status":
                net.cmd_status()
            elif cmd == "/agents" and len(parts) > 1 and parts[1] == "chat":
                rounds = int(parts[2]) if len(parts) > 2 else 1
                net.agents_chat(rounds)
            elif cmd == "/agents":
                for i, a in enumerate(net.agents.values(), 1):
                    print(f"  [{i}] {a.name}")
            elif cmd == "/inject" or cmd == "/broadcast":
                text = line.split(maxsplit=1)[1] if len(parts) > 1 else ""
                if text:
                    net.inject(text)
                else:
                    print("  Uso: /inject <texto>")
            elif cmd == "/talk" or cmd == "/ask":
                if len(parts) >= 3:
                    net.talk(parts[1], parts[2])
                else:
                    print("  Uso: /talk <agente> <texto>")
            elif cmd == "/heatmap":
                net.cmd_heatmap(parts[1] if len(parts) > 1 else "all")
            elif cmd == "/delta":
                if len(parts) > 1:
                    net.cmd_delta(parts[1])
                else:
                    print("  Uso: /delta <agente>")
            elif cmd == "/dist":
                if len(parts) >= 3:
                    net.cmd_dist(parts[1], parts[2])
                else:
                    print("  Uso: /dist <agente1> <agente2>")
            elif cmd == "/blend":
                if len(parts) >= 3:
                    net.cmd_blend(parts[1], parts[2])
                else:
                    print("  Uso: /blend <agente1> <agente2>")
            elif cmd == "/history":
                net.cmd_history(parts[1] if len(parts) > 1 else "all")
            elif cmd == "/add":
                if len(parts) >= 3:
                    net.add_agent(parts[1], parts[2])
                    print(f"  ✓ {parts[1]} adicionado.")
                else:
                    print("  Uso: /add <nome> <persona>")
            elif cmd == "/remove":
                if len(parts) > 1:
                    net.remove_agent(parts[1])
            elif cmd == "/scenario":
                if len(parts) > 1 and parts[1] in SCENARIOS:
                    sc = SCENARIOS[parts[1]]
                    net.agents.clear()
                    for ag in sc["agents"]:
                        net.add_agent(ag["name"], ag["persona"])
                    print(f"  ✓ Cenário '{sc['name']}' carregado com {len(sc['agents'])} agentes.")
                    net.handshake()
                else:
                    print(f"  Cenários: {', '.join(SCENARIOS.keys())}")
            elif cmd == "/log":
                entries = net.log
                for e in entries[-20:]:
                    print(f"  [{e['sender']}→{e['receiver']}] {e['intent']} | {e['text'][:80]}")
            elif cmd == "/export":
                if len(parts) > 1:
                    net.export(parts[1])
                else:
                    net.export("net1337_log.json")
            elif cmd == "/verbose":
                args.verbose = not args.verbose
                print(f"  Verbose: {'ON' if args.verbose else 'OFF'}")
            elif cmd == "/rust":
                if rust.available():
                    print(f"  Rust: ✓ {rust.mode} | versão: {rust.version()}")
                else:
                    print(f"  Rust: ✗ não disponível")
            else:
                print(f"  Comando desconhecido: {cmd}. /help pra listar.")
        else:
            # Texto sem / → injeta como broadcast
            if net.agents:
                net.inject(line)
            else:
                print("  Nenhum agente. Use /scenario ou /add primeiro.")


if __name__ == "__main__":
    main()
