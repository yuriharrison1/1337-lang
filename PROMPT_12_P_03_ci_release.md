# PROMPT 12-P-03 — CI / GITHUB ACTIONS + CHANGELOG + RELEASE

Configurar GitHub Actions para CI contínuo e release automatizado; criar `CHANGELOG.md` no formato Keep a Changelog; documentar o processo de release manual (tag → CI faz o resto).

**PRÉ-REQUISITOS**: 12-P-01 e 12-P-02 executados. `cargo publish --dry-run` verde em todos os crates.

**ESCOPO**: 3 arquivos novos (`.github/workflows/ci.yml`, `.github/workflows/release.yml`, `CHANGELOG.md`) + criar `.github/` dir se não existir.

**Taskwarrior**: `+prompt12_P_03`.

---

## CI WORKFLOW — `.github/workflows/ci.yml`

Dispara em: push para `main`, qualquer PR.

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  CARGO_TERM_COLOR: always
  RUST_BACKTRACE: 1

jobs:
  test:
    name: Test (${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]

    steps:
      - uses: actions/checkout@v4

      - name: Install Rust toolchain
        uses: dtolnay/rust-toolchain@stable
        with:
          components: clippy, rustfmt

      - name: Cache Cargo registry
        uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            target
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}
          restore-keys: ${{ runner.os }}-cargo-

      - name: cargo fmt --check
        run: cargo fmt --all -- --check

      - name: cargo clippy
        run: cargo clippy --workspace --all-targets -- -D warnings

      - name: cargo build
        run: cargo build --workspace

      - name: cargo test
        run: cargo test --workspace

  # Minimal Windows check (build only — no test runner issues with temp dirs)
  windows-build:
    name: Build (windows-latest)
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - name: cargo build
        run: cargo build --workspace
```

---

## RELEASE WORKFLOW — `.github/workflows/release.yml`

Dispara em: push de tag `v*.*.*`.

Produz:
- Binários `leet` e `leet-mcp` para 5 targets
- GitHub Release com assets
- `cargo publish` em ordem topológica

```yaml
name: Release

on:
  push:
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+'

permissions:
  contents: write

env:
  CARGO_TERM_COLOR: always

jobs:
  build-binaries:
    name: Build ${{ matrix.target }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        include:
          - target: x86_64-unknown-linux-gnu
            os: ubuntu-latest
            archive: tar.gz
          - target: aarch64-unknown-linux-gnu
            os: ubuntu-latest
            archive: tar.gz
            cross: true
          - target: x86_64-apple-darwin
            os: macos-latest
            archive: tar.gz
          - target: aarch64-apple-darwin
            os: macos-latest
            archive: tar.gz
          - target: x86_64-pc-windows-gnu
            os: ubuntu-latest
            archive: zip
            cross: true

    steps:
      - uses: actions/checkout@v4

      - uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}

      - name: Install cross
        if: matrix.cross
        run: cargo install cross --git https://github.com/cross-rs/cross

      - name: Build (native)
        if: "!matrix.cross"
        run: cargo build --release --target ${{ matrix.target }} -p leet-cli -p leet-mcp

      - name: Build (cross)
        if: matrix.cross
        run: cross build --release --target ${{ matrix.target }} -p leet-cli -p leet-mcp

      - name: Package (tar.gz)
        if: matrix.archive == 'tar.gz'
        run: |
          TAG=${GITHUB_REF_NAME}
          NAME="leet-${TAG}-${{ matrix.target }}"
          mkdir -p dist/$NAME
          cp target/${{ matrix.target }}/release/leet dist/$NAME/
          cp target/${{ matrix.target }}/release/leet-mcp dist/$NAME/
          cp LICENSE dist/$NAME/
          tar -czf dist/${NAME}.tar.gz -C dist $NAME
          echo "ASSET=dist/${NAME}.tar.gz" >> $GITHUB_ENV

      - name: Package (zip)
        if: matrix.archive == 'zip'
        run: |
          TAG=${GITHUB_REF_NAME}
          NAME="leet-${TAG}-${{ matrix.target }}"
          mkdir -p dist/$NAME
          cp target/${{ matrix.target }}/release/leet.exe dist/$NAME/ 2>/dev/null || true
          cp target/${{ matrix.target }}/release/leet-mcp.exe dist/$NAME/ 2>/dev/null || true
          cp LICENSE dist/$NAME/
          cd dist && zip -r ${NAME}.zip $NAME
          echo "ASSET=dist/${NAME}.zip" >> $GITHUB_ENV

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: binary-${{ matrix.target }}
          path: ${{ env.ASSET }}

  create-release:
    name: Create GitHub Release
    needs: build-binaries
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: dist/
          merge-multiple: true

      - name: Extract changelog entry
        id: changelog
        run: |
          VERSION=${GITHUB_REF_NAME#v}
          NOTES=$(awk "/^## \[${VERSION}\]/{found=1; next} found && /^## \[/{exit} found{print}" CHANGELOG.md)
          echo "notes<<EOF" >> $GITHUB_OUTPUT
          echo "$NOTES" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

      - name: Create release
        uses: softprops/action-gh-release@v2
        with:
          body: ${{ steps.changelog.outputs.notes }}
          files: dist/*
          draft: false
          prerelease: ${{ contains(github.ref_name, '-') }}

  publish-crates:
    name: Publish to crates.io
    needs: create-release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable

      - name: Publish leet-core
        run: cargo publish -p leet-core --no-verify
        env:
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}

      - name: Wait for crates.io index
        run: sleep 30

      - name: Publish leet-bridge
        run: cargo publish -p leet-bridge --no-verify
        env:
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}

      - name: Wait for crates.io index
        run: sleep 30

      - name: Publish leet-mcp
        run: cargo publish -p leet-mcp --no-verify
        env:
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}

      - name: Wait for crates.io index
        run: sleep 30

      - name: Publish leet-cli
        run: cargo publish -p leet-cli --no-verify
        env:
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}

      - name: Wait for crates.io index
        run: sleep 30

      - name: Publish leet-service
        run: cargo publish -p leet-service --no-verify
        env:
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}
```

**GitHub secrets necessários**:
- `CARGO_REGISTRY_TOKEN` — token do crates.io com escopo `publish:update`

---

## CHANGELOG.md

Criar na raiz. Formato: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.1] — 2026-05-12

### Added
- `leet doctor` — system health check with 6 check categories (binaries, IDEs,
  skill, W matrix, project store, network); `--json`, `--auto-fix`, `--offline`
- `leet calibrate` — download and manage the W matrix (`--download`, `--status`, `--force`)
- `leet help` — categorized command overview with `--search` keyword filter
- `leet completions` — generate shell completion scripts (bash/zsh/fish/elvish)
- `UserFacingError` enum in `leet-core` — typed, actionable errors at CLI/MCP boundaries;
  `bail_user!` macro for ergonomic error construction
- Shell completions (`leet completions bash/zsh/fish/elvish`)
- Man pages generated via `build.rs` + `clap_mangen`
- Per-crate `README.md` files for crates.io display
- GitHub Actions CI (ubuntu + macos) and release workflows

### Changed
- All 32 axis names updated to v0.5.1 canonical names (S/D/G/P blocks);
  replaced v0.4-EN names (ESSENCE → INTENTION, CORRESPONDENCE → AMBIGUITY, etc.)
- `PersonalStore::open_or_create` now handles 7 real-world edge cases:
  path canonicalization, write probe, tail truncation, index desync detection,
  version mismatch, fsync error mapping
- `--help` on all 17 subcommands now includes `long_about` + examples + `See also`

### Fixed
- `leet setup uninstall` was orphaning `commands/leet-stats.md` (not removed when
  `skills/leet/` dir was removed)
- `WMatrix::load` now validates magic bytes and version; emits `WMatrixCorrupted`
  instead of generic I/O error

### Removed
- Orphaned experiment artifacts from root (`*.json`, `*.png`, `*.zip` generated
  by dev scripts); added to `.gitignore`

## [0.5.0] — 2026-04-15

### Added
- Initial public release
- 5-crate workspace: `leet-core`, `leet-bridge`, `leet-service`, `leet-cli`, `leet-mcp`
- 32-axis COGON protocol (S/D/G/P blocks)
- MCP server with `leet_recall`, `leet_remember`, `leet_encode`, `leet_decode`,
  `leet_dist`, `leet_recall_delta`
- Tiered consolidation pyramid (7→L1→L2→…)
- `leet setup claude-code/cursor/vscode`
- `leet absorb` — import Claude Code session history

[Unreleased]: https://github.com/leetlang/leet/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/leetlang/leet/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/leetlang/leet/releases/tag/v0.5.0
```

---

## PROCESSO DE RELEASE

Documentar em `RELEASING.md` (ou seção no root README):

```
1. Garantir que main está verde no CI
2. Atualizar versão em Cargo.toml [workspace.package] version
3. Atualizar CHANGELOG.md:
   - Mover itens de [Unreleased] para [X.Y.Z] com data
   - Adicionar link de diff no rodapé
4. Commit: "chore: release vX.Y.Z"
5. git tag vX.Y.Z
6. git push && git push --tags
7. GitHub Actions faz o resto (binaries → Release → cargo publish)
```

Antes do primeiro publish real: adicionar `CARGO_REGISTRY_TOKEN` nos secrets do repo GitHub.

---

## GATES

```bash
# Diretório criado
ls .github/workflows/
# Esperado: ci.yml release.yml

# YAML válido
python3 -c "
import yaml, sys
for f in ['.github/workflows/ci.yml', '.github/workflows/release.yml']:
    try:
        yaml.safe_load(open(f))
        print(f'OK: {f}')
    except Exception as e:
        print(f'FAIL: {f}: {e}')
        sys.exit(1)
"
# Esperado: OK para ambos

# CHANGELOG tem entry para versão atual
VERSION=$(cargo metadata --no-deps --format-version 1 | jq -r '.packages[0].version')
grep -q "\[${VERSION}\]" CHANGELOG.md && echo "OK" || echo "MISSING entry for $VERSION"
# Esperado: OK

# CI workflow menciona cargo test
grep -q "cargo test" .github/workflows/ci.yml
# Esperado: exit 0

# Release workflow menciona cargo publish
grep -q "cargo publish" .github/workflows/release.yml
# Esperado: exit 0

# Dry-run final de todos os crates
for crate in leet-core leet-bridge leet-mcp leet-cli leet-service; do
  echo -n "$crate: "
  cargo publish --dry-run -p $crate 2>&1 | tail -1
done
# Esperado: todos OK / Finished
```
