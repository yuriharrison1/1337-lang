# Prompts para Claude Code — Projeto 1337 v0.4

## Instruções

Cola cada prompt no Claude Code **na ordem**. Espera terminar um antes de colar o próximo.
Se algo falhar, conserta antes de ir pro próximo — cada prompt depende do anterior.

## Checklist

| # | Arquivo | O que cria | Critério de aceite |
|---|---------|-----------|-------------------|
| 1 | `01_skill.md` | Skill 1337 pro Claude (SKILL.md + references/) | Skill instalável, todos os arquivos completos |
| 2 | `02_rust_core.md` | leet-core Rust (tipos, operadores, validação, FFI, PyO3) | `cargo build` + `cargo test` passam |
| 3 | `03_bridge.md` | leet-bridge Rust (trait SemanticProjector, MockProjector, HumanBridge) | `cargo test -p leet_bridge` passa |
| 4 | `04_python.md` | Pacote Python leet1337 (types, operators, bridge, CLI) | `pip install .` + `pytest -v` + `leet zero` funciona |
| 5 | `05_e2e_tests.md` | Testes de integração end-to-end (25+ testes) | `pytest tests/test_e2e.py -v` tudo verde |
| 6 | `06_network.md` | Rede interativa: 2-4 agentes + humano via Rust bridge | `python net1337.py --scenario incident` roda |

## Cada prompt é AUTO-CONTIDO

A spec v0.4 completa está embutida nos prompts que precisam dela (1 e 2).
Não precisa de arquivo externo. Não precisa "ler a spec". Tá tudo dentro do prompt.

## Resultado final esperado

```
projeto-1337/
├── 1337-lang/                  # Skill Claude
│   ├── SKILL.md
│   └── references/
│       ├── spec-v0.4-compact.md
│       ├── axes-reference.md
│       └── rust-implementation-guide.md
├── leet1337/                   # Workspace Rust
│   ├── Cargo.toml
│   ├── leet-core/              # Motor: tipos, validação, operadores, FFI C, PyO3
│   │   ├── Cargo.toml
│   │   └── src/ (lib, types, axes, operators, validate, error, ffi, python)
│   └── leet-bridge/            # Tradução humano ↔ 1337
│       ├── Cargo.toml
│       └── src/ (lib, error, projector, human_to_1337, leet_to_human)
├── python/                     # Pacote Python
│   ├── pyproject.toml
│   ├── leet/
│   │   ├── __init__.py
│   │   ├── types.py
│   │   ├── axes.py
│   │   ├── operators.py
│   │   ├── validate.py
│   │   ├── bridge.py
│   │   └── cli.py
│   └── tests/
│       ├── test_types.py
│       ├── test_operators.py
│       ├── test_validate.py
│       ├── test_bridge.py
│       ├── test_cli.py
│       └── test_e2e.py
```

## API do sistema

Depois de tudo pronto, o 1337 é acessível de 3 formas:

1. **Rust nativo** — `use leet_core::*;`
2. **C ABI/FFI** — `leet_cogon_zero()`, `leet_blend()`, etc. (qualquer linguagem)
3. **Python** — `from leet import Cogon, blend, encode, decode` + CLI `leet encode "texto"`

## Rede interativa (Prompt 6)

Um único script `net1337.py` que sobe uma rede de 2-4 agentes conversando em 1337:

```
python net1337.py --scenario incident          # Mock (sem API)
DEEPSEEK_API_KEY=sk-... python net1337.py      # DeepSeek
ANTHROPIC_API_KEY=sk-... python net1337.py     # Claude
```

Arquitetura:
- **Humano** → texto passa pelo **bridge Rust** (PyO3/FFI) → COGON → rede
- **Agentes** → usam LLM (DeepSeek/Anthropic/Mock) pra projetar e reconstruir
- Comandos: `/inject`, `/talk <agente>`, `/agents chat`, `/heatmap`, `/dist`, `/blend`, etc.
- Cenários: incident, brainstorm, anomaly, devops (3 agentes)
