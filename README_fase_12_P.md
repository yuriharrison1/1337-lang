# FASE 12-P — PUBLICAR

Quarto e último bloco de "fechar tudo". Foco: o repo está pronto pra ser publicado no crates.io, ter binários no GitHub Releases, e ser encontrado por outros desenvolvedores.

**Pré-requisito**: Fases 12-T, 12-U, 12-W executadas. Workspace 100% verde, sem warnings, todos os gates passando.

**Duração realista**: 1 semana focado.

---

## OS 3 PROMPTS DESTA FASE

| # | Arquivo | Foco | Tamanho |
|---|---|---|---|
| 12-P-01 | `PROMPT_12_P_01_cargo_metadata.md` | Cargo.toml polish + per-crate README.md + root README.md | médio |
| 12-P-02 | `PROMPT_12_P_02_completions_manpages.md` | Shell completion (bash/zsh/fish) + man pages | médio |
| 12-P-03 | `PROMPT_12_P_03_ci_release.md` | GitHub Actions CI + release workflow + CHANGELOG.md | grande |

Total: 3 prompts auto-contidos. Cada um incrementalmente publishable.

---

## ORDEM DE EXECUÇÃO

```
12-P-01 (metadata + READMEs)     ← fundação: crates.io sem rejeitar por campo faltando
   │
   ▼
12-P-02 (completions + manpages)  ← adiciona artefatos gerados; pode ir em paralelo com 01
   │
   ▼
12-P-03 (CI + release)           ← automatiza tudo; precisa do repo limpo dos anteriores
```

12-P-01 primeiro porque `cargo publish --dry-run` vai reclamar de campos faltando antes de qualquer outra coisa.

---

## ESTADO ATUAL (auditado)

| Item | Estado |
|---|---|
| `[workspace.package]` metadata | ✓ license, repository, homepage, description, keywords, categories presentes |
| Per-crate descriptions | ✓ cada crate tem `description` própria |
| `documentation` field por crate | ✗ ausente — crates.io não vai linkar pra docs.rs automaticamente |
| `readme = "README.md"` por crate | ✗ ausente |
| Per-crate `README.md` | ✗ ausente (só root tem, se tanto) |
| Root `README.md` | ? verificar |
| `publish = true` (explícito) | ✗ ausente — default true mas bom ser explícito |
| Shell completions | ✗ ausente |
| Man pages | ✗ ausente |
| `.github/workflows/ci.yml` | ✗ ausente |
| `.github/workflows/release.yml` | ✗ ausente |
| `CHANGELOG.md` | ✗ ausente |

---

## ORDEM DE PUBLISH NO CRATES.IO

Dependência interna: leet-core → leet-bridge → leet-mcp → leet-cli

```
1. leet-core    (sem deps internas)
2. leet-bridge  (depende de leet-core)
3. leet-mcp     (depende de leet-core, leet-bridge)
4. leet-cli     (depende de todos)
5. leet-service (separado; depende de leet-core, leet-bridge)
```

Cada um publicado com `cargo publish -p <crate>` na ordem acima com ~30s de intervalo (crates.io index delay).

---

## DECISÕES CRAVADAS NESTA FASE

| Decisão | Valor | Justificativa |
|---|---|---|
| Shell completions via subcommand | `leet completions <shell>` | Usuário cola no shell init; mais flexível que build.rs |
| Man pages via build.rs | `target/man/*.1` gerado em build | Não requer runtime dep; seguindo convenção Unix |
| CI: branches com PR | `main` protegido, PRs exigem CI verde | Standard para repos abertos |
| Release trigger | git tag `v*` | Semver; GitHub Releases automático |
| Publish order | core → bridge → mcp → cli → service | Topological sort das deps internas |
| `leet-service` publish | sim, separado | É um crate útil pra quem quer o servidor gRPC |
| CHANGELOG formato | Keep a Changelog (keepachangelog.com) | Padrão; parsável; semver-friendly |

---

## EXPERIÊNCIA RESULTANTE

### crates.io

Página do `leet-core` com:
- Badge CI verde
- README formatado
- Docs.rs link funcional
- Keywords/categories buscáveis

### Instalação

```
$ cargo install leet-cli
$ leet --version
leet 0.5.1

$ leet completions bash >> ~/.bash_completion.d/leet
$ leet completions zsh > ~/.zsh/completions/_leet
$ leet completions fish > ~/.config/fish/completions/leet.fish
```

### Release

```
$ git tag v0.5.1 && git push --tags
# → CI builds binaries for 5 targets
# → GitHub Release criado com assets
# → cargo publish rodado na ordem certa
```

---

## GATE GLOBAL DA FASE 12-P

```bash
# Dry-run de todos os crates
cargo publish --dry-run -p leet-core
cargo publish --dry-run -p leet-bridge
cargo publish --dry-run -p leet-mcp
cargo publish --dry-run -p leet-cli
# Esperado: nenhum retorna erro

# Completions geram output válido
./target/release/leet completions bash | head -5
# Esperado: bash completion script começa com '# '

./target/release/leet completions zsh | head -2
# Esperado: começa com '#compdef leet'

# Man pages existem
ls target/man/
# Esperado: leet.1, leet-encode.1, etc.

# CI workflow existe e é válido YAML
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
# Esperado: nenhum erro

# CHANGELOG tem entry para v0.5.1
grep -q "\[0.5.1\]" CHANGELOG.md
# Esperado: exit 0
```

---

## O QUE NÃO ESTÁ NESTA FASE

- **Site / landing page leetlang.org**: conteúdo real do site. 12-P só cria o README e links.
- **docs.rs custom theme ou inlining**: docs.rs gera automaticamente; customização é v1.x.
- **Instalador (brew tap, apt, etc)**: fora do escopo. Homebrew tap pode ser feito manualmente depois.
- **Windows CI**: cross-compile para `x86_64-pc-windows-gnu` está no release.yml mas teste real no Windows não está aqui.
- **i18n de mensagens**: mensagens em inglês. PT/ES em v1.x.

---

## ARQUIVOS DESTA FASE

- `PROMPT_12_P_01_cargo_metadata.md`
- `PROMPT_12_P_02_completions_manpages.md`
- `PROMPT_12_P_03_ci_release.md`
- `README_fase_12_P.md` (este arquivo)
