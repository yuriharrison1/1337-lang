# 1337 — linguagem nativa de comunicação inter-agentes

## O que é

1337 é um protocolo de comunicação projetado para agentes de IA. Em vez de trocar mensagens em linguagem natural verbosa, agentes 1337 codificam cada conceito como um **COGON** — um vetor semântico de 32 dimensões com um vetor de incerteza companheiro. Essa representação é compacta, semanticamente precisa e computacionalmente barata.

O protocolo resolve um problema concreto: quando dois agentes precisam coordenar ações, enviar o texto completo "o sistema de autenticação caiu com urgência máxima, precisa de rollback imediato no serviço de login" é caro em tokens e ambíguo. Em 1337, esse conceito vira 256 bytes com eixos `G8_URGENCIA=0.95`, `P3_ANOMALIA=0.90`, `G4_REVERSIBILIDADE=0.90` já ativados.

---

## Arquitetura

```
┌────────────────────────────────────────────────────────────┐
│                  Aplicação / Usuário                       │
└────────────────┬────────────────────────┬──────────────────┘
                 │ Python SDK             │ CLI
    ┌────────────▼──────────┐  ┌──────────▼────────────────┐
    │  leet-py (SDK público)│  │  leet  (13 comandos)      │
    │  python/leet (SDK core│  │  encode decode chat ...   │
    └────────────┬──────────┘  └──────────┬────────────────┘
                 │                        │
    ┌────────────▼────────────────────────▼────────────────┐
    │                  leet-bridge (Rust)                  │
    │  nl_to_cogon  cogon_to_nl  AnthropicClient           │
    └────────────────────────┬─────────────────────────────┘
                             │
    ┌────────────────────────▼─────────────────────────────┐
    │                  leet-core (Rust)                    │
    │  Cogon  Dag  Msg1337  blend  dist  delta  validate   │
    └────────────────────────┬─────────────────────────────┘
                             │
    ┌────────────────────────▼─────────────────────────────┐
    │               leet-service (Rust daemon)             │
    │  leet-server  TCP :1337 + Unix socket                │
    │  leet-agent   15 processos independentes             │
    │  C5 handshake  PROBE→ECHO→ALIGN→VERIFY               │
    └──────────────────────────────────────────────────────┘
```

---

## Início rápido

### CLI (Rust)

```bash
cargo build --release -p leet-cli

# Projetar texto em COGON
./target/release/leet encode "sistema crítico, falha detectada"

# Chat multiagente com 15 agentes IA
export LEET_API_KEY=sk-ant-...
./target/release/leet chat
```

### Python SDK

```python
import sys
sys.path.insert(0, "python")
from leet import Cogon, blend, dist

a = Cogon.zero()
print(a.sem[:4])  # [1.0, 1.0, 1.0, 1.0]
```

---

## Compressão

| Formato | Bytes típicos |
|---------|--------------|
| Texto natural | ~400B |
| JSON COGON | ~480B |
| **Codec binário (96B)** | **96B — 4× menor** |
| SparseDelta (n=4 eixos) | 37B — 10× menor |

---

## Testes

```bash
# Rust workspace
cargo test --workspace
# 97 testes: leet-core(30) + leet-bridge(16) + leet-cli(21) + leet-service(30)
```

---

## Documentação

| Documento | Conteúdo |
|-----------|---------|
| [USER_GUIDE.md](USER_GUIDE.md) | Guia completo do usuário — CLI, chat, modo distribuído |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Arquitetura detalhada de cada componente |
| [PROTOCOL.md](PROTOCOL.md) | Especificação COGON v0.5.1 — 32 eixos, handshake C5 |
| [API_REFERENCE.md](API_REFERENCE.md) | Referência de API — Rust e Python |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Deployment com systemd para produção |

---

## Status

| Componente | Testes | Versão |
|-----------|--------|--------|
| leet-core (Rust) | 30 ✓ | 0.4.0 |
| leet-bridge (Rust) | 16 ✓ | 0.5.0 |
| leet-service (Rust) | 30 ✓ | 0.5.1 |
| leet-cli (Rust) | 21 ✓ | 0.5.0 |
| python/leet (SDK core) | — | 0.5.0 |
| leet-py (SDK público) | — | 0.5.0 |
