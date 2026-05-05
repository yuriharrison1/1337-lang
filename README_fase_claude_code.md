# FASE CLAUDE CODE — INTEGRAÇÃO ZERO-FRICÇÃO (PROMPT 10a–e)

Esta fase cria a integração completa entre 1337 (Leetlang) e Claude Code. O usuário roda `leet setup claude-code` **uma vez** e nunca mais precisa pensar em setup, init, hooks ou configuração. Toda sessão do Claude Code, em qualquer projeto, ganha memória persistente via 1337.

---

## ARQUITETURA FINAL

```
┌──────────────────────────────────────────────────────────────────┐
│                         Claude Code UI                            │
│                                                                    │
│   usuário conversa ─────► Claude lê skill `leet` (global)         │
│                                  │                                 │
│                                  ▼                                 │
│                          Claude decide chamar                     │
│                   leet_recall / leet_remember / etc                │
└─────────────────────────────────┬────────────────────────────────┘
                                   │ (stdio JSON-RPC)
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  leet-mcp (subprocess spawned by Claude Code)                     │
│  LEET_PROJECT_ROOT=${workspaceFolder}                             │
│                                                                    │
│  ├─ protocol.rs    ← JSON-RPC 2.0 + MCP types                     │
│  ├─ server.rs      ← main loop, tools/list, tools/call dispatch   │
│  ├─ tools.rs       ← 5 tools (recall/remember/encode/decode/dist) │
│  └─ store.rs       ← PersonalStore (binary append-only)           │
└─────────────────────────────────┬────────────────────────────────┘
                                   │
                                   ▼
                    <project>/.leet/store.bin
                    (16-byte header + 360-byte records)
                    .leet/.gitignore (auto-created)
```

---

## OS PROMPTS DESTA FASE

| # | Arquivo | Escopo | Ordem | Ger. arquivos |
|---|---|---|---|---|
| 10a | `PROMPT_10a_leet_mcp.md` | Crate `leet-mcp` com 5 tools MCP e stdio transport | 1º | 8 arquivos |
| 10b | `PROMPT_10b_personal_store.md` | PersonalStore binário real (substitui stubs de 10a) | 2º | 1 arquivo |
| 10c | `PROMPT_10c_leet_setup.md` | `leet setup claude-code` zero-fricção, idempotente | 3º | 2 arquivos |
| 10d | `PROMPT_10d_skill.md` | Conteúdo real da `~/.claude/skills/leet/SKILL.md` | 4º | 2 arquivos |
| 10e | `PROMPT_10e_leet_absorb.md` | `leet absorb` safety net (importa Claude Code histórico) | 5º ou paralelo | 2 arquivos |

---

## ORDEM DE EXECUÇÃO

Estritamente sequencial pros 4 primeiros porque cada um depende do anterior:

```
10a (cria leet-mcp stubs)
  │
  ▼
10b (PersonalStore real, substitui stubs)
  │
  ▼
10c (leet setup claude-code, usa leet-mcp já funcional)
  │
  ▼
10d (conteúdo real da SKILL.md)
  │
  ▼
10e (safety net — pode rodar em paralelo com 10d se quiser)
```

Cada um com gate `cargo test --workspace` verde antes de avançar.

---

## O QUE O USUÁRIO VAI VIVER

### Instalação única

```bash
# Uma vez na vida:
$ cargo install --path leet-cli
$ cargo install --path leet-mcp
$ leet setup claude-code
  ✓ leet-mcp binary at /home/yuri/.cargo/bin/leet-mcp
  ✓ Detected Claude Code at /home/yuri/.claude
  ✓ Registered MCP server in /home/yuri/.claude/settings.json
  ✓ Installed global skill at /home/yuri/.claude/skills/leet

  All set. Open any project with Claude Code — 1337 recall is live.
```

### Uso diário

```bash
$ cd meu-projeto-qualquer
# Abre Claude Code

[Dia 1]
> "Vamos começar um app de finanças pessoais"
[conversa rola, Claude chama leet_remember quando detecta decisões:
  "usar FastAPI", "SQLite pra começar", "dashboard em Streamlit"]
[fecha Claude Code]

[Dia 2]
> "Continua de onde paramos"
[Claude chama leet_recall silenciosamente, lê 5 COGONs, retoma contexto]
[conversa flui como se Claude tivesse lembrado]
```

### Safety net (raro)

```bash
$ cd projeto-que-ja-usei-antes
$ leet absorb --since last-week
  · Sessions found: 12
  · Absorbed: 12
  · Skipped (dupes): 0
```

---

## GANHO REALISTA DE TOKENS

Baseado no protocolo:

| Cenário | Sem leet | Com leet | Economia |
|---|---|---|---|
| Primeira sessão de um projeto | baseline | baseline + ~500 tokens (skill) | -500 |
| Retomando sessão do dia anterior | colar 2000-4000 tokens de contexto | leet_recall + 5 entries ~= 800 tokens | **~60%** no recall |
| Projeto com 30 sessões | quase impossível lembrar tudo | leet_recall filtrado por DIST | **contexto inédito** |
| Durante a sessão | sem gravação | 1 leet_remember por decisão ~= 200 tokens | +custo leve |

**Tradeoff honesto:** pagamos ~500 tokens/sessão em `leet_remember` calls pra ganhar 2000-4000 tokens no `leet_recall` da próxima sessão. Net positivo em projetos com 3+ sessões.

---

## GATE GLOBAL DA FASE (após os 5)

```bash
# Compila tudo
cargo build --workspace
cargo test --workspace
cargo clippy --workspace -- -D warnings

# Binários instaláveis
cargo install --path leet-cli --force
cargo install --path leet-mcp --force
which leet leet-mcp
# Esperado: ambos em ~/.cargo/bin/

# Setup funcional
leet setup claude-code
cat ~/.claude/settings.json | jq '.mcpServers.leet'
# Esperado: objeto com command + args + env.LEET_PROJECT_ROOT

ls ~/.claude/skills/leet/SKILL.md
wc -l ~/.claude/skills/leet/SKILL.md
# Esperado: >100 linhas, front-matter com name: leet

# Smoke end-to-end: simulate Claude Code calling tools
cd /tmp && mkdir smoke && cd smoke
leet-mcp <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"testing 123"}}}
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"leet_recall","arguments":{}}}
EOF
# Esperado: 4 responses JSON-RPC, a última listando o record de "testing 123"

ls -la .leet/
# Esperado: store.bin (376 bytes = 16 header + 360 um record) + .gitignore

# Status
leet setup status
# Esperado:
#   Claude Code:    ✓ configured
#   leet-mcp:       ✓ ~/.cargo/bin/leet-mcp
#   Global skill:   ✓ ~/.claude/skills/leet/SKILL.md
```

Se tudo bate, **integração Claude Code está completa**. Usuário pronto pra usar no dia-a-dia.

---

## PRÓXIMAS FASES SUGERIDAS

Depois que essa funcionar, fazem sentido naturalmente:

1. **Calibração melhorada** — hash-based embedding é placeholder. Substituir por embeddings reais (sentence-transformers via Python sidecar, ou provider API externo configurável).
2. **Mundo A (orquestração multi-agente)** — sub-agentes Claude conversando entre si em 1337. Mais arriscado, mais upside.
3. **Integração Kimi e Aider** — seguindo o padrão `leet setup kimi` / `leet setup aider`. Menos importante que Claude Code porque adoção menor, mas vale pra ecosystem.
4. **Distribuição pública (Fase B)** — crates.io, PyPI, Homebrew, winget.

---

## ARQUIVOS DESTA FASE

- `PROMPT_10a_leet_mcp.md` — crate `leet-mcp` (8 arquivos novos)
- `PROMPT_10b_personal_store.md` — PersonalStore real (1 arquivo)
- `PROMPT_10c_leet_setup.md` — `leet setup claude-code` (2 arquivos)
- `PROMPT_10d_skill.md` — SKILL.md real (2 arquivos)
- `PROMPT_10e_leet_absorb.md` — `leet absorb` (2 arquivos)
- `README_fase_claude_code.md` (este arquivo)

Total: ~5200 linhas de prompt cirúrgico.
