# Projeto 1337 — Sistema de Build via Claude Code

## Visão Geral

7 prompts self-contained que constroem o SDK completo do 1337.
Cada prompt é alimentado ao Claude Code com `--dangerously-skip-permissions`.

## Infraestrutura de Tracking

- **CONTRACT.md** — Documento mestre com todas as tarefas. Todo prompt atualiza ao finalizar.
- **Taskwarrior** — Projeto `1337` com tags por prompt (`+prompt01`, `+prompt02`, etc.)
- **Git** — Cada prompt faz commit + push ao finalizar.

## Prompts

| # | Arquivo | Componente | Linguagem | Tarefas |
|---|---------|-----------|-----------|---------|
| 0 | `PROMPT_00_git_setup.md` | Git + Contract + Taskwarrior | bash | 8 |
| 1 | `PROMPT_01_foundation.md` | leet-core + bridge + Python + net1337 | Rust + Python | 22 |
| 2 | `PROMPT_02_leet_service.md` | gRPC service + batch + SIMD | Rust | 13 |
| 3 | `PROMPT_03_leet_vm.md` | VM: adapters + projector + store | Python | 19 |
| 4 | `PROMPT_04_leet_py.md` | SDK público + providers + agents | Python | 14 |
| 5 | `PROMPT_05_leet_cli.md` | Debug tools + bench + inspect | Rust | 15 |
| 6 | `PROMPT_06_calibration.md` | W matrix pipeline | Python | 10 |

**Total: 101 tarefas**

## Uso

```bash
# Build completo (recomendado para primeira vez)
chmod +x run.sh
./run.sh

# Só o setup do git (fazer PRIMEIRO se repo já existe)
./run.sh 0

# Foundation + service
./run.sh 1 2

# Retomar do prompt 3
./run.sh --from 3

# Ver progresso
./run.sh --status

# Plano sem executar
./run.sh --dry-run
```

## Ordem de Execução

```
0 (git setup) → 1 (core) → 2 (service) → 3 (VM) → 4 (SDK) → 5 (CLI) → 6 (calibração)
```

Cada prompt depende dos anteriores. **Não pule etapas.**

## Verificação Rápida

Depois do build completo:

```bash
# Rust
cargo test --workspace

# Python
cd python && pytest tests/ -v
cd ../leet-vm && pytest tests/ -v
cd ../leet-py && pytest tests/ -v

# CLI
leet version && leet zero && leet axes

# Service
cargo run -p leet-service &
leet health
kill %1

# Simulador
python examples/net1337.py

# SDK
python -c "
import asyncio, leet_sdk as leet
async def main():
    c = leet.connect('mock')
    r = await c.chat('hello 1337')
    print(r.text, f'| saved {r.tokens_saved} tokens')
asyncio.run(main())
"

# Calibração
cd calibration && python run_pipeline.py

# Taskwarrior
task project:1337 summary
```

## Spec

A spec v0.4 (32 eixos, R1–R21, MSG_1337) está embutida dentro do PROMPT_01.
Demais prompts referenciam o código gerado pelo prompt anterior.
