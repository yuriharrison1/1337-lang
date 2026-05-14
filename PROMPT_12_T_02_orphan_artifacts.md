# PROMPT 12-T-02 — LIMPEZA DE ARTEFATOS ÓRFÃOS NO ROOT DO REPO

Remover ou ignorar arquivos que vazaram pro repo durante experimentos e nunca foram limpos. Tornar `git status` limpo num clone fresco. Atualizar `.gitignore` para bloquear regerações futuras.

**PRÉ-REQUISITOS**: nenhum técnico. Pode rodar antes ou depois do PROMPT_12-T-01.

**ESCOPO**: 1 commit que remove ~10 arquivos do tracking + atualiza `.gitignore`.

**Taskwarrior**: `+prompt12_T_02`.

---

## ARTEFATOS IDENTIFICADOS NA AUDITORIA

| Arquivo | Tamanho | O que é | Decisão |
|---|---|---|---|
| `.leet_cache.db` | 16KB | SQLite gerado por `python/leet/` durante uso | **Remover do tracking + adicionar ao .gitignore** |
| `consciencia_debate_1775018485.json` | 172KB | Output de experimento `consciencia_debate.py` | Remover |
| `demo_log.json`, `demo_log_1774512078.json` | 4KB cada | Output de `run_demo.sh` | Remover |
| `dual_book_report_1774512131.json` | 200KB | Output de `dual_book_simulation.py` | Remover |
| `dual_delta_report_1774509759.json`, `dual_delta_report_1774509768.json` | 1KB cada | Output de `dual_book_delta.py` | Remover |
| `plato_1337_report_177*.json` (4 arquivos) | total ~149KB | Output de `plato_discussion.py` | Remover |
| `compressao_1337_teoria.png` | 200KB | Imagem gerada por `compression_analysis.py` | Remover |
| `report_1337.html`, `report_1337.txt` | ~16KB total | Output de `generate_report.py` | Remover |
| `Cargo.lock.bak` (caso exista) | varia | Backup deixado durante migrações | Já no .gitignore atual ✓ |
| `files.zip`, `files-11.zip` | ~80KB total | Arquivos auxiliares de algum experimento | Remover (são ruído) |

Nenhum desses tem valor referencial — todos são saídas reproduzíveis dos scripts Python que estão no repo.

**Não tocar em**:
- `calibration/data/*` (já protegido pelo .gitignore atual)
- `target/` (já protegido)
- Os scripts Python que **geram** esses arquivos (`*.py` ficam, são código)
- `Cargo.lock` real (commitado intencionalmente, é a prática Rust)

---

## EXECUÇÃO

```bash
cd /path/to/1337-lang-main

# 1. Confirmar repo limpo antes
git status

# 2. Remover do tracking + filesystem
git rm --cached .leet_cache.db
git rm consciencia_debate_*.json
git rm demo_log*.json
git rm dual_book_report_*.json
git rm dual_delta_report_*.json
git rm plato_1337_report_*.json
git rm compressao_1337_teoria.png
git rm report_1337.html report_1337.txt
git rm files.zip files-11.zip

# (Caso algum dos rm acima falhe porque o arquivo não tá tracked,
#  é OK — pode pular. O fonte da verdade aqui é o `git rm`.)

# 3. Adicionar ao .gitignore — appendar, não sobrescrever
cat >> .gitignore <<'EOF'

# Generated experiment outputs (Python scripts at root)
.leet_cache.db
consciencia_debate_*.json
demo_log.json
demo_log_*.json
dual_book_report_*.json
dual_delta_report_*.json
plato_1337_report_*.json
compressao_*.png
report_1337.html
report_1337.txt

# Demo / experiment artifacts
files.zip
files-11.zip

# Per-project leet store (lives next to user code, never in this repo)
.leet/
EOF

# 4. Commit
git add .gitignore
git commit -m "chore: untrack experiment outputs and tighten .gitignore

Removes generated artifacts that accumulated in the repo root during
exploratory experiments. None have referential value — all are
reproducible by re-running the corresponding Python script.

Removed from tracking (kept on local filesystem if desired by the user
who runs git rm; deleted otherwise):
  .leet_cache.db                       (SQLite from python/leet)
  consciencia_debate_*.json            (consciencia_debate.py output)
  demo_log{,_*}.json                   (run_demo.sh output)
  dual_book_report_*.json              (dual_book_simulation.py output)
  dual_delta_report_*.json             (dual_book_delta.py output)
  plato_1337_report_*.json             (plato_discussion.py output)
  compressao_1337_teoria.png           (compression_analysis.py output)
  report_1337.html, report_1337.txt    (generate_report.py output)
  files.zip, files-11.zip              (incidental archives)

.gitignore appended with patterns to prevent regeneration noise. Also
adds .leet/ — the per-project leet store should never live in this
upstream repo (it's user data, generated locally).

The Python scripts themselves are NOT removed — they remain reproducible
references in the repo.

Part of Phase 12-T (técnico): canonical-state cleanup."

# 5. Verificar
git status
# Esperado: working tree clean

git ls-files | grep -E "\.leet_cache|demo_log\.json|plato_1337_report_|files\.zip|report_1337\.(html|txt)"
# Esperado: ZERO matches
```

---

## VERIFICATION

```bash
# Repo está limpo de artefatos?
git status                         # → "nothing to commit, working tree clean"
git ls-files | wc -l               # caiu por ~12 arquivos vs antes do commit

# Reroda um demo — repo deve continuar limpo (gitignore funcionando)?
./demo_auto.sh 2>/dev/null || true
git status
# Esperado: ainda "nothing to commit". Os outputs gerados ficam ignorados.

# Workspace ainda compila/testa?
cargo build --workspace
cargo test --workspace
# Esperado: idêntico ao antes do commit (esses arquivos não eram inputs de build).
```

---

**END OF PROMPT_12-T-02**
