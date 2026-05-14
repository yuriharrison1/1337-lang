# FASE 12-T — TÉCNICO (zerar dívida pré-publicação)

Primeiro dos três blocos de "fechar tudo". Foco: deixar o workspace 100% verde, sem dívida residual, sem artefatos órfãos, sem labels divergentes da spec. Quando essa fase terminar, o repo passa pra Fase 12-U (usar) e depois 12-P (publicar).

---

## ESTADO ATUAL (auditado)

Estado real do repo no zip que tu mandou (auditado em sessão anterior):

| Item | Estado |
|---|---|
| `cargo build --workspace` | ✓ verde, 1 warning (unused_imports em types.rs) |
| `cargo test --workspace` | ✓ **247 testes verdes**, 0 falhas |
| `cargo clippy` | clippy não instalado no Ubuntu apt, mas sem clippy-only opt-out — fora do escopo |
| Stubs / `unimplemented!()` / TODO em produção | ✓ zero |
| Panics em produção | ✓ zero (1 falso positivo dentro de teste) |
| Unwraps de produção | 9 totais no workspace, todos contextualmente seguros |
| `leet-mcp` end-to-end | ✓ smoke test verde: initialize → tools/list → leet_remember×3 → leet_recall |
| `.leet/store.bin`, `.leet/index.bin` formato | ✓ bate exatamente com PROMPT_10b/11a |
| 15 subcomandos CLI funcionais | ✓ `leet <cmd> --help` todos respondem |

**Dívida real encontrada (apenas 2 itens críticos):**

1. **Nomes dos 32 eixos errados** — São v0.4 traduzidos pra inglês (ESSENCE, CORRESPONDENCE, etc) em vez dos v0.5.1 reais (INTENTION, AMBIGUITY, etc). Estrutura S/D/G/P está certa, valores numéricos do COGON_ZERO_SEM estão certos, só os labels divergem.
2. **Artefatos de experimento órfãos no root** — ~12 arquivos JSON/PNG/ZIP gerados por scripts Python ficaram tracked. `.leet_cache.db` no root também não devia estar lá.

**Outras notas (sem prompt dedicado):**
- 1 warning `unused_imports` em `leet-core/src/types.rs:175` — incluído no fix do PROMPT_12-T-01.

---

## OS PROMPTS DESTA FASE

| # | Arquivo | Escopo | Prazo |
|---|---|---|---|
| 12-T-01 | `PROMPT_12_T_01_axis_names.md` | Substituir os 32 nomes de eixo (v0.4-EN → v0.5.1 real). 9 arquivos. Inclui também o fix do warning. | 30-45 min |
| 12-T-02 | `PROMPT_12_T_02_orphan_artifacts.md` | Untrack artefatos órfãos + atualizar `.gitignore`. Cosmético mas necessário pra Fase 12-P. | 5 min |

São os únicos dois. Dividido por concern, não por tamanho.

---

## ORDEM DE EXECUÇÃO

12-T-01 **primeiro** — tem mais superfície de mudança, gates mais críticos. Se quebrar, é melhor descobrir primeiro.

12-T-02 depois — independente, low-risk, idempotente.

Cada um com `cargo test --workspace` verde antes de avançar. **Não pula gate.**

---

## GATE GLOBAL DA FASE 12-T

Após executar 01 + 02, validar:

```bash
# Build limpo
cargo build --workspace
# Esperado: 0 errors, 0 warnings.

# Testes verdes
cargo test --workspace 2>&1 | grep "test result" | awk '{ok+=$4; fail+=$6} END {print ok " passed, " fail " failed"}'
# Esperado: ≥247 passed, 0 failed

# Sanity humano
./target/debug/leet axes | head -10
# Esperado: "[0] S1 INTENTION ..." (não ESSENCE)

./target/debug/leet zero | head -8
# Esperado: linhas usando INTENTION, PROPAGATION, CONFIDENCE

# Repo limpo
git status
# Esperado: "nothing to commit, working tree clean"

git ls-files | grep -E "\.leet_cache|demo_log\.json|plato_1337_report_|files\.zip" | wc -l
# Esperado: 0

# Confirmação que nomes v0.4 sumiram do código (nos arquivos .rs ativos, não nos PROMPTs históricos)
grep -rn "ESSENCE\|VIBRATION\|GENERATIVITY\|REVERSIBILITY\|TEMPORAL_VECTOR\|ACTION_VALENCE\|ONTOLOGICAL_VALENCE\|EPISTEMIC_VALENCE" --include="*.rs" leet-* 2>/dev/null | wc -l
# Esperado: 0

# Smoke MCP end-to-end
rm -rf /tmp/leet-12t && mkdir /tmp/leet-12t
cat <<'EOF' | LEET_PROJECT_ROOT=/tmp/leet-12t ./target/debug/leet-mcp 2>/dev/null | tail -3
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"phase 12-T closed"}}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"leet_recall","arguments":{}}}
EOF
ls -la /tmp/leet-12t/.leet/
# Esperado: store.bin = 16 + 360 = 376 bytes, index.bin = 32 + 24 = 56 bytes
```

Se todos os gates batem, **Fase 12-T fechou**. Hora de Fase 12-U.

---

## QUANDO TERMINAR ESSA FASE — O QUE VEM DEPOIS

A próxima fase (**12-U: usar**) trata de fazer o sistema confortável de usar como produto pessoal. Eu **não escrevi os prompts da 12-U ainda** porque a lista deles depende de:

1. **Tu rodar 12-T-01 e 12-T-02 e me confirmar verde.**
2. Eu re-auditar o repo já com nomes corretos pra ver o que a Fase 12-T derruba ou expõe.
3. Tu usar uma sessão real de Claude Code com leet-mcp instalado e me dizer o que doeu.

A pauta provável (não fechada) da 12-U é: mensagens de erro humanas (não stack-trace `anyhow`), `leet doctor` que diagnostica setup completo, edge cases (dois projetos com mesmo basename, falha de fsync, store corrompido), `--help` decente em todos os subcomandos, doc inline mínima.

---

## ARQUIVOS DESTA FASE

- `PROMPT_12_T_01_axis_names.md` — substituição dos 32 nomes
- `PROMPT_12_T_02_orphan_artifacts.md` — limpeza de artefatos órfãos
- `README_fase_12_T.md` (este arquivo)
