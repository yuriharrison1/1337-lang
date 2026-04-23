# FASE A — BLOCOS 2, 3, 4 (sequência 08 + 09a–d)

Continuação do bloco 1 (07a–g, já executado). Estes prompts fecham a Fase A e deixam o projeto pronto pra Fase B (distribuição pública).

---

## MAPA

```
FASE A
├── BLOCO 1 — migração PT→v0.5.1 [✅ 07a–g executados]
├── BLOCO 2 — rename PT→EN       [⏳ PROMPT_08]
├── BLOCO 3 — spec .docx EN       [⏳ manual, ver nota abaixo]
└── BLOCO 4 — suporte paralelo    [⏳ PROMPT_09a–d, qualquer ordem]
```

---

## OS PROMPTS DESTE LOTE

| # | Arquivo | Escopo | Ordem |
|---|---|---|---|
| 08 | `PROMPT_08_rename_pt_en.md` | Rename PT→EN nos 32 eixos + API pública | depois de 07g |
| 09a | `PROMPT_09a_workspace_package.md` | `[workspace.package]` em Cargo.toml raiz | qualquer hora |
| 09b | `PROMPT_09b_delete_leet1337.md` | Deletar `leet1337/` via branch archive | qualquer hora |
| 09c | `PROMPT_09c_w_calibrada.md` | Plugar W.bin no projector, keyword-fallback opt-in | depois de PROMPT_06 |
| 09d | `PROMPT_09d_governance.md` | LICENSE, CONTRIBUTING, CoC, SECURITY, CHANGELOG | qualquer hora |

---

## ORDEM RECOMENDADA

Se tu quer progressão natural com gates atômicos:

1. **09a workspace.package** (5 min, sem risco) — deixa versões alinhadas em 0.5.1
2. **09b deletar leet1337/** (2 min, sem risco) — tira peso morto
3. **09d governança** (10 min, arquivos estáticos) — deixa o repo pronto pra ser público
4. **08 rename PT→EN** (núcleo, 30-60 min) — a mudança semanticamente relevante
5. **09c W calibrada** (mais denso, depende de W.bin existir) — melhora qualidade de projeção

Alternativa: se quer focar no resultado primeiro, **08 primeiro**, depois os 09*s em qualquer ordem.

---

## BLOCO 3 — SPEC .DOCX EM EN (nota)

Esse bloco não precisa de um prompt pra Claude Code — é mais útil eu mesmo gerar o arquivo `.docx` na próxima rodada de conversa, partindo do v0.5.1 PT que a gente já extraiu e aplicando a tabela-mestra PT→EN. Me avisa quando quiser que eu gere.

---

## GATES GLOBAIS DA FASE A

Ao final de 08 + 09a-d executados, validar:

```bash
# Tudo compila
cargo test --workspace
cargo clippy --workspace -- -D warnings

# Versão homogênea
cargo metadata --no-deps --format-version 1 \
  | jq '.packages[] | {name, version}'
# Esperado: 4 crates, todos "0.5.1"

# Sem nomes PT ativos (só em comentários históricos, keyword lists, scripts)
grep -rn "INTENCAO\|AMBIGUIDADE\|MASSA\|CONFIANCA\|CAUSALIDADE" \
  --include="*.rs" leet-core leet-cli leet-bridge leet-service
# Esperado: zero matches em axes.rs, operators.rs, validate.rs, protocol.rs

# Sem leet1337/
ls leet1337/ 2>&1 | grep -i "no such" && echo OK

# Governança presente
ls LICENSE LICENSE-MIT LICENSE-APACHE CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md CHANGELOG.md

# W plugada (feature flag off por default)
grep -A2 "\[features\]" leet-bridge/Cargo.toml
# Esperado: default = [] / keyword-fallback = []
```

Se tudo bate, **Fase A está completa** e o próximo movimento é a Fase B (distribuição pública: crates.io, PyPI, homebrew, winget).

---

## ARQUIVOS DESTE LOTE

- `PROMPT_08_rename_pt_en.md`
- `PROMPT_09a_workspace_package.md`
- `PROMPT_09b_delete_leet1337.md`
- `PROMPT_09c_w_calibrada.md`
- `PROMPT_09d_governance.md`
- `README_fase_a_blocos_2_3_4.md` (este arquivo)
