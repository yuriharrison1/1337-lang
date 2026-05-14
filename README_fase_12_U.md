# FASE 12-U — UX (USAR)

Segundo dos blocos de "fechar tudo". Foco: usuário random clona o repo, instala em 5 minutos, usa sem se irritar.

**Pré-requisito**: Fase 12-T executada (workspace verde, nomes corretos, repo limpo).

**Duração realista**: 2-3 semanas focado.

---

## OS 4 PROMPTS DESTA FASE

| # | Arquivo | Foco | Tamanho |
|---|---|---|---|
| 12-U-01 | `PROMPT_12_U_01_user_errors.md` | `UserFacingError` enum centralizado, mensagens orientadas a ação | grande |
| 12-U-02 | `PROMPT_12_U_02_doctor.md` | `leet doctor` — health check completo com auto-fix | grande |
| 12-U-03 | `PROMPT_12_U_03_help.md` | `--help` decente nos 17 subcomandos + `leet help` interativo | médio |
| 12-U-04 | `PROMPT_12_U_04_edge_cases.md` | 7 cenários reais (path collision, truncate, fsync, etc) | médio |

Total: 4 prompts auto-contidos. Cada um com gates explícitos, taskwarrior, smoke tests.

---

## ORDEM DE EXECUÇÃO

```
12-U-01 (UserFacingError)        ← fundação
   │
   ▼
12-U-02 (leet doctor)             ← usa UserFacingError
   │
   ▼
12-U-03 (--help)                  ← independente, pode ir em paralelo com 02
   │
   ▼
12-U-04 (edge cases)              ← usa UserFacingError + ajusta storage
```

12-U-01 **primeiro** porque define o tipo `UserFacingError` que os outros 3 usam. Depois disso, 12-U-02 e 12-U-03 podem ir em qualquer ordem (independentes). 12-U-04 fica por último porque mexe em storage e quer pipeline limpo.

Cada um com `cargo test --workspace` verde antes de avançar.

---

## DECISÕES CRAVADAS NESTA FASE

Aceitar antes de executar — vai aparecer em vários prompts:

| Decisão | Valor | Justificativa |
|---|---|---|
| Erros user-facing são tipos, não strings | `UserFacingError` enum | Compilador ajuda a localizar; testes ficam tipados |
| Internal code continua usando anyhow | sem alteração | Não vamos refatorar 100% do código por estilística |
| Boundary de conversão | CLI main + MCP server handler | Único ponto onde anyhow vira UserFacingError |
| Exit codes | 0 OK · 1 erro · 2 warning | Semver de exit codes virou contrato |
| `--auto-fix` do doctor | só conserta o mecânico | Nunca instala IDE ou seta API key |
| Strategy pra schema mismatch | bloquear, não auto-migrar | Migration explícita em comando dedicado |
| Path canonicalization | sempre, no open() | Resolver symlinks e relativize |

---

## EXPERIÊNCIA RESULTANTE

### Antes (estado pós-12-T)

```
$ leet setup claude-code
Error: opening /home/yuri/.claude/settings.json

Caused by:
    0: parsing /home/yuri/.claude/settings.json
    1: expected `,` or `}` at line 14 column 5
```

```
$ leet axes --help
Usage: leet axes [OPTIONS]

Options:
  -h, --help  Print help
```

```
$ # store.bin corrompido por crash
$ leet inspect
thread 'main' panicked at 'codec frame too short', store.rs:142:9
```

### Depois (estado pós-12-U)

```
$ leet setup claude-code

/home/yuri/.claude/settings.json contains invalid JSON.

What to do:
  Fix the JSON manually or back up the file:
    cp /home/yuri/.claude/settings.json /home/yuri/.claude/settings.json.bak
  Then re-run `leet setup`.
  Parser error: expected `,` or `}` at line 14 column 5

More info: https://docs.leetlang.org/integrations
```

```
$ leet axes --help

List the 32 canonical axes of the 1337 protocol.

Shows code (S1..P8), name, block, range semantics, and bipolar marker.
Useful as a reference while reading sem vectors or designing prompts
that target specific axes.

Usage: leet axes [OPTIONS]

Options:
      --json          Output as JSON
      --block <S|D|G|P>  Filter by functional block
  -h, --help         Print help

Examples:
  leet axes
  leet axes --json
  leet axes --block S

See also:
  leet zero    — print COGON_ZERO with axis values
  leet decode  — interpret a sem[32] in terms of these axes
```

```
$ leet doctor

leet doctor — system health check
════════════════════════════════════════════

✓ Binaries
   leet      v0.5.1   /home/yuri/.cargo/bin/leet
   leet-mcp  v0.5.1   /home/yuri/.cargo/bin/leet-mcp

✓ IDE integrations
   Claude Code   configured  ~/.claude/settings.json

✓ Skill installed
   Global  ~/.claude/skills/leet/SKILL.md (4842 bytes)

⚠ W matrix
   Status   missing
   Fallback hash-trigram (degraded quality)
   Hint     run `leet calibrate --download`

✗ Project state
   Index out of sync: store has 47 records, index has 30 entries
   Fix      Run `leet consolidate rebuild-index --yes`

────────────────────────────────────────────
Status: 1 error, 1 warning. Quick fixes shown above.
```

---

## GATE GLOBAL DA FASE 12-U

Após 12-U-01..04 executados:

```bash
# Build + tests
cargo build --workspace
cargo test --workspace 2>&1 | grep "test result" | awk '{ok+=$4; fail+=$6} END {print ok " passed, " fail " failed"}'
# Esperado: ≥ 254 passed (247 baseline + 7 edge cases), 0 failed

# Sem warning de unused
cargo build --workspace 2>&1 | grep -c "^warning"
# Esperado: 0

# UserFacingError em uso nos boundaries
grep -rn "UserFacingError" leet-cli/src/main.rs leet-mcp/src/server.rs
# Esperado: pelo menos 1 ocorrência em cada

# leet doctor existe e roda
./target/debug/leet doctor --json | jq -r .status
# Esperado: ok / warning / error (válido em qualquer)

# Cada subcomando tem about
for cmd in setup doctor version axes zero inspect encode decode dist blend validate; do
  ./target/debug/leet $cmd --help 2>&1 | head -1 | grep -q . || echo "FAIL: $cmd"
done
# Esperado: nada printado (todos OK)

# Smoke real: store corrompido detectado
mkdir -p /tmp/leet-12u-test/.leet
echo "this is not LEET" > /tmp/leet-12u-test/.leet/store.bin
LEET_PROJECT_ROOT=/tmp/leet-12u-test ./target/debug/leet doctor 2>&1 | grep -q "store"
# Esperado: detecta problema, mensagem humana
```

Se todos os gates passam, **Fase 12-U fechou**. Hora de Fase 12-W (W matrix calibrada).

---

## O QUE NÃO ESTÁ NESTA FASE

Coisas relacionadas a UX que ficam pra outras fases — pra evitar ambiguidade:

- **Tradução PT/EN de erros**: hoje todas as mensagens são EN. Usuário PT entende mas v1.x pode adicionar `LEET_LANG=pt`. **Não esta fase.**
- **Logging estruturado**: tracing já existe no código mas não tem config user-friendly. **12-W toca nisso ao calibrar.**
- **Tab completion**: bash/zsh/fish completion via `clap_complete`. **Trivial mas fica pra 12-P** (vai junto com release scripts).
- **Manpages**: gerar via clap_mangen. **12-P junto com docs.**
- **Mensagens de erro em PT** (i18n): v1.x.

---

## ARQUIVOS DESTA FASE

- `PROMPT_12_U_01_user_errors.md`
- `PROMPT_12_U_02_doctor.md`
- `PROMPT_12_U_03_help.md`
- `PROMPT_12_U_04_edge_cases.md`
- `README_fase_12_U.md` (este arquivo)
