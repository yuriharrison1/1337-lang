Crie UM ÚNICO arquivo Python chamado `net1337.py` — uma rede interativa de 2 a 4 agentes de IA conversando entre si na linguagem 1337, com o humano participando via bridge Rust.

O script é 100% auto-contido para tipos/operadores/eixos (tudo inline). Mas a tradução do HUMANO obrigatoriamente tenta usar o core Rust compilado (leet_core via PyO3 ou ctypes). Se o Rust não estiver disponível, avisa e cai pro fallback pure-python.

---

# ARQUITETURA

```
                        HUMANO
                          │
                    ┌─────┴──────┐
                    │ BRIDGE RUST │  ← leet_core (PyO3 ou ctypes FFI)
                    │ texto→COGON │  ← operadores em Rust (BLEND, DIST, etc)
                    │ COGON→texto │  ← validação R1-R21 em Rust
                    └─────┬──────┘
                          │ MSG_1337
                          ▼
               ┌─── REDE 1337 ───┐
               │                 │
          ┌────┴────┐      ┌────┴────┐
          │ Agente 1│◄────►│ Agente 2│     (2 a 4 agentes)
          │ (LLM)   │      │ (LLM)   │
          └────┬────┘      └────┬────┘
               │                │
          DeepSeek /       DeepSeek /
          Anthropic /      Anthropic /
          Mock             Mock
```

**Regra fundamental:** O humano SEMPRE passa pelo Rust. Os agentes SEMPRE passam pelo LLM.
Isso demonstra as duas vias de entrada na rede 1337.

---

# INTEGRAÇÃO COM RUST (leet_core)

O script tenta 3 caminhos pra carregar o Rust, nesta ordem:

```python
# ═══════════════════════════════════════════════
# TENTATIVA 1: PyO3 (import direto)
# Funciona se: maturin develop --features python
# ═══════════════════════════════════════════════
try:
    import leet_core as _rust
    RUST_BACKEND = "pyo3"
    print("✓ Rust backend: PyO3 (leet_core importado)")
except ImportError:
    _rust = None

# ═══════════════════════════════════════════════
# TENTATIVA 2: ctypes FFI (carrega .so/.dylib)
# Funciona se: cargo build --release
# ═══════════════════════════════════════════════
if _rust is None:
    import ctypes
    import glob
    _lib = None
    # Procura a lib compilada
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
    if _lib is None:
        RUST_BACKEND = None
        print("⚠ Rust backend NÃO disponível. Humano usará fallback pure-python.")
        print("  Para ativar Rust:")
        print("    PyO3:  cd leet1337 && maturin develop --features python")
        print("    FFI:   cd leet1337 && cargo build --release")
```

## Classe RustBridge (wrapper unificado)

```python
class RustBridge:
    """
    Bridge Rust pra tradução do humano.
    Unifica PyO3 e ctypes num interface única.
    Usado EXCLUSIVAMENTE pra input/output do humano.
    """

    def __init__(self):
        self.mode = RUST_BACKEND  # "pyo3", "ffi", ou None

    def available(self) -> bool:
        return self.mode is not None

    def project(self, text: str) -> tuple[list[float], list[float]]:
        """
        Texto humano → (sem[32], unc[32]) via Rust.

        Se PyO3: chama leet_core.project_text(text) se existir,
                 ou usa leet_core como validador e o LLM pra projeção.
        Se FFI:  chama leet_cogon_new + monta via C ABI.

        NOTA: O core Rust não tem LLM embutido. O Rust faz:
        - Validação dos vetores (dimensão, range [0,1])
        - Operadores (BLEND, DIST, DELTA, FOCUS, ANOMALY_SCORE)
        - Serialização canônica
        - Criação de COGON_ZERO

        A projeção semântica (texto → vetor) ainda precisa de LLM.
        Então o fluxo real do humano é:
        1. Texto → LLM projeta nos 32 eixos → sem[], unc[]
        2. sem[], unc[] → Rust valida e cria COGON
        3. Rust aplica operadores se necessário
        4. Rust serializa MSG_1337

        O diferencial é que operadores/validação/serialização rodam em Rust nativo.
        """
        ...

    def create_cogon(self, sem: list[float], unc: list[float]) -> str:
        """Cria COGON via Rust. Retorna JSON."""
        if self.mode == "pyo3":
            return _rust.cogon_new(sem, unc)
        elif self.mode == "ffi":
            # Converte pra ctypes arrays, chama leet_cogon_new
            c_sem = (ctypes.c_float * 32)(*sem)
            c_unc = (ctypes.c_float * 32)(*unc)
            _lib.leet_cogon_new.restype = ctypes.c_char_p
            result = _lib.leet_cogon_new(c_sem, c_unc, 32)
            return result.decode("utf-8") if result else None

    def cogon_zero(self) -> str:
        """COGON_ZERO via Rust."""
        if self.mode == "pyo3":
            return _rust.cogon_zero()
        elif self.mode == "ffi":
            _lib.leet_cogon_zero.restype = ctypes.c_char_p
            result = _lib.leet_cogon_zero()
            return result.decode("utf-8") if result else None

    def validate(self, msg_json: str) -> str | None:
        """Valida MSG_1337 via Rust. None = ok."""
        if self.mode == "pyo3":
            return _rust.validate(msg_json)
        elif self.mode == "ffi":
            _lib.leet_validate.restype = ctypes.c_char_p
            _lib.leet_validate.argtypes = [ctypes.c_char_p]
            result = _lib.leet_validate(msg_json.encode("utf-8"))
            return result.decode("utf-8") if result else None

    def blend(self, c1_json: str, c2_json: str, alpha: float) -> str:
        """BLEND via Rust."""
        if self.mode == "pyo3":
            return _rust.blend(c1_json, c2_json, alpha)
        elif self.mode == "ffi":
            _lib.leet_blend.restype = ctypes.c_char_p
            _lib.leet_blend.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_float]
            result = _lib.leet_blend(c1_json.encode(), c2_json.encode(), alpha)
            return result.decode("utf-8") if result else None

    def dist(self, c1_json: str, c2_json: str) -> float:
        """DIST via Rust."""
        if self.mode == "pyo3":
            return _rust.dist(c1_json, c2_json)
        elif self.mode == "ffi":
            _lib.leet_dist.restype = ctypes.c_float
            _lib.leet_dist.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            return _lib.leet_dist(c1_json.encode(), c2_json.encode())

    def version(self) -> str:
        if self.mode == "pyo3":
            return _rust.version()
        elif self.mode == "ffi":
            _lib.leet_version.restype = ctypes.c_char_p
            return _lib.leet_version().decode("utf-8")
        return "N/A"
```

---

# FLUXO DO HUMANO vs FLUXO DO AGENTE

```python
class HumanParticipant:
    """
    O humano na rede 1337.
    Tradução via Rust bridge (com fallback LLM pra projeção semântica).
    """

    def __init__(self, rust_bridge: RustBridge, llm_backend):
        self.id = "HUMAN-" + str(uuid4())[:8]
        self.name = "Humano"
        self.rust = rust_bridge
        self.llm = llm_backend  # precisa do LLM pra projeção texto→vetor
        self.history: list[Cogon] = []

    def text_to_msg(self, text: str, receiver: str = "BROADCAST") -> Msg1337:
        """
        Fluxo completo do humano:
        1. LLM projeta texto nos 32 eixos → sem[], unc[]
        2. Rust cria e valida o COGON (se disponível)
        3. Rust constrói MSG_1337 validada
        """
        # Passo 1: Projeção via LLM (o Rust não tem LLM)
        sem, unc = self.llm.project(text)

        # Passo 2: COGON via Rust (se disponível)
        if self.rust.available():
            cogon_json = self.rust.create_cogon(sem, unc)
            cogon = Cogon.from_dict(json.loads(cogon_json)) if cogon_json else Cogon(sem=sem, unc=unc)
            print(f"  🦀 COGON criado via Rust ({self.rust.mode})")
        else:
            cogon = Cogon(sem=sem, unc=unc)
            print(f"  🐍 COGON criado via Python (fallback)")

        self.history.append(cogon)

        # Passo 3: MSG_1337
        msg = Msg1337(
            sender=self.id, receiver=receiver, intent="ASSERT",
            payload=cogon,
            c5={"schema_ver": "0.4.0", "align_hash": "human"},
            surface={"human_required": False, "urgency": sem[22],
                     "reconstruct_depth": 3, "lang": "pt", "_text": text}
        )

        # Passo 4: Validação via Rust (se disponível)
        if self.rust.available():
            err = self.rust.validate(json.dumps(msg_to_dict(msg)))
            if err:
                print(f"  ⚠ Validação Rust: {err}")
            else:
                print(f"  🦀 MSG_1337 validada via Rust ✓")

        return msg


class Agent1337:
    """
    Agente IA na rede 1337.
    Tradução via LLM backend (DeepSeek / Anthropic / Mock).
    NÃO usa Rust — o agente é nativo da rede.
    """

    def __init__(self, name: str, persona: str, backend):
        self.id = str(uuid4())
        self.name = name
        self.persona = persona
        self.backend = backend  # DeepSeek / Anthropic / Mock
        self.history: list[Cogon] = []
        self.msg_log: list[Msg1337] = []
        self.response_texts: list[str] = []

    def announce(self) -> Msg1337:
        """R20: COGON_ZERO antes de tudo."""
        return Msg1337(sender=self.id, receiver="BROADCAST", intent="SYNC",
                       payload=Cogon.zero(),
                       surface={"human_required": False, "_text": "I AM"})

    def receive_and_respond(self, msg: Msg1337, all_agents: dict) -> list[Msg1337]:
        """
        Recebe MSG, processa, responde.
        Pode responder ao sender E/OU broadcast pra rede.
        Retorna lista de MSGs (0, 1, ou mais).
        """
        received_cogon = msg.payload
        self.history.append(received_cogon)

        # Reconstruir texto recebido
        received_text = msg.surface.get("_text", "") if msg.surface else ""
        if not received_text:
            received_text = self.backend.reconstruct(received_cogon)

        # Gerar resposta
        if isinstance(self.backend, MockBackend):
            response_text = self.backend.generate_response(
                received_text, self.persona, self.response_texts
            )
        else:
            sender_name = "Humano"
            for aid, agent in all_agents.items():
                if aid == msg.sender:
                    sender_name = agent.name if hasattr(agent, 'name') else "Humano"
                    break

            context_lines = self.response_texts[-3:] if self.response_texts else []
            prompt = f"""Você é: {self.persona}

Mensagem recebida de [{sender_name}]:
"{received_text}"

Contexto das suas falas anteriores:
{chr(10).join(context_lines) if context_lines else '(primeira interação)'}

Responda em caráter. Uma ou duas frases concisas e diretas. Em português."""

            response_text = self.backend.call(
                "Responda em caráter conforme a persona. Máximo 2 frases. Português.",
                prompt
            )

        self.response_texts.append(response_text)

        # Projetar resposta em 1337
        sem, unc = self.backend.project(response_text)
        response_cogon = Cogon(sem=sem, unc=unc)

        # DELTA ou ASSERT
        use_delta = len(self.history) > 1 and py_dist(self.history[-1], response_cogon) < 0.3
        intent = "DELTA" if use_delta else "ASSERT"
        patch = py_compute_delta(self.history[-1], response_cogon) if use_delta else None

        msg_out = Msg1337(
            sender=self.id,
            receiver=msg.sender if msg.receiver != "BROADCAST" else "BROADCAST",
            intent=intent, payload=response_cogon,
            ref_hash=msg.id if use_delta else None,
            patch=patch,
            c5={"schema_ver": "0.4.0", "align_hash": "agent"},
            surface={
                "human_required": True, "urgency": sem[22],
                "reconstruct_depth": 3, "lang": "pt",
                "_text": response_text,
            }
        )

        self.msg_log.append(msg_out)
        self.history.append(response_cogon)
        return [msg_out]
```

---

# REDE: ORCHESTRADOR

```python
class Network1337:
    """Rede 1337 com agentes + humano."""

    def __init__(self, rust_bridge: RustBridge, llm_backend):
        self.agents: dict[str, Agent1337] = {}  # agent_id → Agent1337
        self.human = HumanParticipant(rust_bridge, llm_backend)
        self.all_participants: dict[str, any] = {}  # id → Agent ou Human
        self.log: list[dict] = []
        self.rust = rust_bridge

    def add_agent(self, name: str, persona: str, backend) -> Agent1337:
        if len(self.agents) >= 4:
            print("⚠ Máximo 4 agentes.")
            return None
        agent = Agent1337(name, persona, backend)
        self.agents[agent.id] = agent
        self.all_participants[agent.id] = agent
        self.all_participants[self.human.id] = self.human
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
        # Humano anuncia via Rust
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
        results = self._render_msg(msg, "Humano", "BROADCAST")

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
                # Pega o último msg de outro agente como estímulo
                other = agent_list[(i + 1) % len(agent_list)]
                if other.msg_log:
                    last_msg = other.msg_log[-1]
                elif other.history:
                    # Fabrica msg do estado atual
                    last_msg = Msg1337(
                        sender=other.id, receiver=agent.id, intent="ASSERT",
                        payload=other.history[-1] if other.history else Cogon(),
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

        # Tenta via Rust primeiro
        if self.rust.available():
            d = self.rust.dist(c1.to_json(), c2.to_json())
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
            result_json = self.rust.blend(c1.to_json(), c2.to_json(), alpha)
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
        # Tenta por número
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

    def _log_msg(self, msg, sender_name, receiver_name):
        self.log.append({
            "sender": sender_name, "receiver": receiver_name,
            "intent": msg.intent, "text": msg.surface.get("_text", "") if msg.surface else "",
            "urgency": msg.surface.get("urgency", 0) if msg.surface else 0,
            "msg": msg_to_dict(msg), "stamp": msg.payload.stamp if hasattr(msg.payload, 'stamp') else 0,
        })

    def _render_msg(self, msg, sender_name, receiver_name):
        print(render_msg(msg, sender_name, receiver_name))

    def export(self, path: str):
        with open(path, "w") as f:
            json.dump(self.log, f, indent=2, default=str, ensure_ascii=False)
        print(f"  📁 Exportado: {path} ({len(self.log)} msgs)")
```

---

# CENÁRIOS PRÉ-DEFINIDOS

```python
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
```

---

# LLM BACKENDS (DeepSeek, Anthropic, Mock)

Implemente os 3 backends como no prompt anterior:

**DeepSeekBackend**: usa lib `openai` com base_url="https://api.deepseek.com", model="deepseek-chat"
**AnthropicBackend**: usa lib `anthropic`, model="claude-sonnet-4-20250514"
**MockBackend**: zero API, heurística de keywords (com generate_response por persona)

Cada backend tem: `.call(system, user) → str`, `.project(text) → (sem, unc)`, `.reconstruct(cogon) → str`

O MockBackend adicional tem `.generate_response(text, persona, history) → str` com respostas por tipo de persona.

---

# OPERADORES PYTHON (fallback quando Rust não disponível)

Implementar inline: `py_blend`, `py_compute_delta`, `py_apply_patch`, `py_dist`, `py_anomaly_score`, `py_focus`
Mesmas fórmulas da spec (BLEND: sem=α·c1+(1-α)·c2, unc=max; DIST: cosseno ponderado por 1-unc; etc.)

---

# SURFACE RENDERER (funções inline)

- `render_msg(msg, sender, receiver) → str`: box bonito com texto, eixos dominantes, intent, urgência
- `render_heatmap(cogon, only_significant=True) → str`: ASCII bars dos eixos > 0.6
- `render_delta_diff(prev, curr) → str`: eixos que mudaram > 0.1

---

# OS 32 EIXOS (lista AXES inline completa)

Todos os 32 com idx, code, name, group, desc — copiar exatamente da spec v0.4.

---

# MAIN — LOOP INTERATIVO

```python
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

    backend = create_backend(backend_name)  # factory

    # Inicializar Rust bridge
    rust = RustBridge()

    # Criar rede
    net = Network1337(rust, backend)

    # Carregar cenário ou modo interativo
    if args.scenario:
        sc = SCENARIOS[args.scenario]
        for ag in sc["agents"]:
            net.add_agent(ag["name"], ag["persona"], backend)
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
                    net.add_agent(parts[1], parts[2], backend)
                    print(f"  ✓ {parts[1]} adicionado. Anunciando...")
                    # announce
                else:
                    print("  Uso: /add <nome> <persona>")
            elif cmd == "/remove":
                if len(parts) > 1:
                    net.remove_agent(parts[1])
            elif cmd == "/scenario":
                if len(parts) > 1 and parts[1] in SCENARIOS:
                    sc = SCENARIOS[parts[1]]
                    # Limpa e recarrega
                    net.agents.clear()
                    for ag in sc["agents"]:
                        net.add_agent(ag["name"], ag["persona"], backend)
                    print(f"  ✓ Cenário '{sc['name']}' carregado com {len(sc['agents'])} agentes.")
                    net.handshake()
                else:
                    print(f"  Cenários: {', '.join(SCENARIOS.keys())}")
            elif cmd == "/log":
                full = len(parts) > 1 and parts[1] == "full"
                entries = net.log if full else net.log[-20:]
                for e in entries:
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
```

---

# USO

```bash
# Mock (zero dependências, testa mecânica)
python net1337.py --scenario incident

# DeepSeek
export DEEPSEEK_API_KEY="sk-..."
python net1337.py --scenario devops

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
python net1337.py --backend anthropic --scenario brainstorm

# Modo livre (sem cenário, adiciona agentes manualmente)
python net1337.py
1337> /add Engenheiro "SRE sênior focado em estabilidade"
1337> /add PM "Product manager focado em usuários"
1337> /inject Precisamos reescrever o serviço de busca
```

---

# CRITÉRIOS DE ACEITE

1. `python net1337.py --scenario incident --backend mock` roda 100% sem API, sem Rust
2. Com Rust compilado, humano usa Rust pra COGON/validação (🦀 aparece no output)
3. Sem Rust, humano usa fallback Python com aviso (🐍 aparece)
4. `/inject`, `/talk`, `/agents chat` funcionam
5. `/heatmap`, `/delta`, `/dist`, `/blend` funcionam e usam Rust quando disponível
6. `/add` e `/remove` funcionam em runtime (2-4 agentes)
7. 4 cenários prontos: incident, brainstorm, anomaly, devops (devops tem 3 agentes)
8. DeepSeek funciona com DEEPSEEK_API_KEY
9. Anthropic funciona com ANTHROPIC_API_KEY
10. Handshake C5 com COGON_ZERO (R20) antes de qualquer conversa
11. DELTA compression usado quando COGONs são similares
12. Output é bonito e legível com boxes Unicode
13. `/export` gera JSON válido
14. `/rust` mostra status do bridge
15. Texto digitado sem / é tratado como broadcast automático
16. Script é UM ÚNICO ARQUIVO .py (auto-contido exceto lib do LLM)
