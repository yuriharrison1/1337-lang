# PROMPT 09b — LIMPEZA: DELETAR `leet1337/` (experimento abandonado)

Remover a pasta `leet1337/` do monorepo. Foi confirmado em análise prévia que é um experimento paralelo abandonado (v0.4 estagnada, contém `wire.rs` alternativo e bindings Python via PyO3 que nunca foram integrados). Preservar em branch archive antes de deletar, pra referência futura.

**PRÉ-REQUISITOS**: nenhum do bloco 1. Pode rodar a qualquer momento.

**ESCOPO**: apenas a pasta `leet1337/` + atualização de `.gitignore` se necessário.

**Taskwarrior**: `+prompt09b`.

---

## CONTEXTO

`leet1337/` é um sandbox que explorou:
1. Wire format compacto sem `unc` (prefigurando v0.5.1)
2. Bindings Python nativos via PyO3

Ficou estagnado em v0.4. As ideias boas (drop de unc) foram formalizadas na v0.5.1 de outra forma (P6_CONFIDENCE). Os bindings PyO3 não foram integrados ao `leet-py` oficial. A pasta é peso morto no repo.

---

## EXECUÇÃO

```bash
cd /path/to/1337-lang-main

# Confirmar estado da main
git status
# deve estar clean

# 1. Branch de archive preservando o experimento
git checkout -b archive/leet1337-experimental
git push -u origin archive/leet1337-experimental

# 2. Voltar para main e deletar
git checkout main
rm -rf leet1337/

# 3. Se houver referências ao diretório em .gitignore ou similar, remover.
grep -n "leet1337" .gitignore 2>/dev/null || true

# 4. Commit
git add -A
git commit -m "chore: remove leet1337/ (abandoned experimental parallel workspace)

leet1337/ was a sandbox exploring alternative wire format (drop unc)
and PyO3 Python bindings. Stagnated on v0.4. Its best insight (removing
unc from wire) is now formalized differently in v0.5.1 via P6_CONFIDENCE.
The PyO3 bindings were never integrated into leet-py.

Preserved in branch archive/leet1337-experimental for historical reference.

Part of Fase A block 4 (support)."

git push origin main

task add project:1337 +prompt09b "Delete leet1337/ abandoned experimental workspace"
task project:1337 +prompt09b done
```

---

## VERIFICATION

```bash
ls leet1337/ 2>&1 | grep -i "no such" && echo OK_DELETED
git branch -a | grep archive/leet1337-experimental && echo OK_ARCHIVED

# Build deve continuar passando (leet1337 não era member do workspace raiz)
cargo test --workspace
```

---

**END OF PROMPT_09b**
