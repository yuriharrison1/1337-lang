# FASE 12-W — W MATRIX CALIBRADA

Terceiro dos blocos de "fechar tudo". Foco: projeção NL→COGON de qualidade real. Hoje o leet usa hash-trigram como fallback — funciona para DIST relativo mas a qualidade semântica é pobre para usuários que nunca fizeram calibração.

**Pré-requisito**: Fase 12-U executada (workspace verde, UserFacingError em uso, leet doctor rodando).

**Duração realista**: 1-2 semanas focado.

---

## OS 2 PROMPTS DESTA FASE

| # | Arquivo | Foco | Tamanho |
|---|---|---|---|
| 12-W-01 | `PROMPT_12_W_01_w_format.md` | Hardening do formato W.bin (magic + versão) + path discovery (`~/.local/share/leet/`) | médio |
| 12-W-02 | `PROMPT_12_W_02_calibrate_cmd.md` | `leet calibrate` subcomando (`--download`, `--status`, `--force`) | grande |

Total: 2 prompts auto-contidos. Calibração local (`--local`) fica para fase futura — requer training data do usuário.

---

## ORDEM DE EXECUÇÃO

```
12-W-01 (formato + path)    ← fundação: salvar/carregar W.bin corretamente
   │
   ▼
12-W-02 (leet calibrate)    ← usa infraestrutura de 12-W-01
```

12-W-01 **primeiro** porque define o formato binário com magic/versão e o método `WMatrix::save()` que o comando calibrate precisa.

---

## ESTADO ATUAL (auditado)

| Item | Estado |
|---|---|
| `WMatrix` struct (leet-bridge/src/projector.rs) | ✓ exists — load/project funcionam |
| Formato W.bin | ⚠ sem magic bytes — não detecta arquivo errado |
| `find_w_path()` | ⚠ procura `LEET_W_PATH`, `./calibration/data/W.bin`, `/usr/share/leetlang/W.bin` — **missing `~/.local/share/leet/W.bin`** |
| `WMatrix::save()` | ✗ não existe |
| `leet calibrate` subcomando | ✗ não existe |
| `try_download_w()` em doctor.rs | ⚠ placeholder que retorna erro imediato |
| `UserFacingError::WMatrixMissing / WMatrixCorrupted` | ✓ definidos em leet-core |

---

## DECISÕES CRAVADAS NESTA FASE

| Decisão | Valor | Justificativa |
|---|---|---|
| Magic bytes no W.bin | `LEET` (4 bytes) + version byte | Detecta arquivo truncado/errado sem ambiguidade |
| Path padrão do usuário | `~/.local/share/leet/W.bin` | XDG Base Dir Spec; coerente com Linux e emulado no macOS |
| URL de download | `https://cdn.leetlang.org/w/v{VERSION}/W.bin` | CDN dedicado; versão no path para compatibilidade |
| Formato de calibração local | Adiado (Phase 12-W-future) | Requer training data — escopo não cabe nesta fase |
| `--download` sem API key | sim — W.bin é público | Não requer autenticação |
| Integração com doctor | `try_download_w()` chama o mesmo código do calibrate | DRY; doctor --auto-fix funciona |

---

## EXPERIÊNCIA RESULTANTE

### Antes (pós-12-U)

```
$ leet doctor
⚠ W matrix
   Status   missing
   Fallback hash-trigram (degraded quality)
   Hint     run `leet calibrate --download`
```

```
$ leet calibrate --download
error: unrecognized subcommand 'calibrate'
```

### Depois (pós-12-W)

```
$ leet calibrate --status

W matrix status
────────────────────────────────────────
  Search path (in order):
    [1] $LEET_W_PATH              — not set
    [2] ~/.local/share/leet/W.bin — NOT FOUND
    [3] ./calibration/data/W.bin  — NOT FOUND
    [4] /usr/share/leetlang/W.bin — NOT FOUND

  Active: none (using hash-trigram fallback)
  Quality: degraded

Run `leet calibrate --download` to fetch the official W matrix.
```

```
$ leet calibrate --download

Downloading W matrix v0.5.1...
  URL     https://cdn.leetlang.org/w/v0.5.1/W.bin
  Saving  ~/.local/share/leet/W.bin
  ████████████████████ 100% — 1.2 MB in 0.8s

✓ W matrix installed
  Path    ~/.local/share/leet/W.bin
  Rows    32
  Cols    768
  Version 1

Run `leet doctor` to verify everything is working.
```

```
$ leet doctor
✓ W matrix
   Status   loaded
   Path     ~/.local/share/leet/W.bin
   Dims     32 × 768
```

---

## GATE GLOBAL DA FASE 12-W

Após 12-W-01 e 12-W-02 executados:

```bash
# Build limpo
cargo build --workspace
# Esperado: 0 errors, 0 warnings

# Testes verdes
cargo test --workspace 2>&1 | grep "test result" | awk '{ok+=$4; fail+=$6} END {print ok " passed, " fail " failed"}'
# Esperado: ≥ 270 passed, 0 failed

# W.bin tem magic correto
cargo test -p leet-bridge -- w_tests
# Esperado: todos OK

# Subcomando existe
./target/debug/leet calibrate --help | head -1
# Esperado: linha não vazia com descrição

# Status roda sem crash
./target/debug/leet calibrate --status
# Esperado: output mostrando caminhos e status "none" ou "loaded"

# Formato round-trip
cargo test -p leet-bridge -- w_format
# Esperado: load(save(W)) == W

# doctor --auto-fix w_matrix agora realmente baixa
# (testar manualmente ou mockar URL em teste de integração)
```

---

## O QUE NÃO ESTÁ NESTA FASE

- **Calibração local (`--local <data-dir>`)**: requer training data do usuário e um solver de regressão linear. Escopo grande demais para esta fase.
- **Embedding providers alternativos**: OpenAI, sentence-transformers, etc. Ficam para v1.x.
- **Quantização do W.bin**: f16 ou int8 para reduzir tamanho. Futura otimização.
- **Atualização automática**: não há auto-update do W.bin. Usuário roda `leet calibrate --download` manualmente.

---

## ARQUIVOS DESTA FASE

- `PROMPT_12_W_01_w_format.md`
- `PROMPT_12_W_02_calibrate_cmd.md`
- `README_fase_12_W.md` (este arquivo)
