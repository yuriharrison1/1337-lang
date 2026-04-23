# PROMPT 09a — WORKSPACE.PACKAGE v0.5.1 (alinhamento de versão)

Alinhar todos os 4 crates do workspace numa versão única `0.5.1` via `[workspace.package]` no `Cargo.toml` raiz. Elimina drift entre crates e simplifica bumps futuros.

**PRÉ-REQUISITOS**: bloco 1 da Fase A executado (07a–07g). `cargo test --workspace` verde. PROMPT_08 pode ou não ter rodado — 09a é independente.

**ESCOPO**: 5 arquivos `Cargo.toml` (raiz + 4 crates).

**Taskwarrior**: `+prompt09a`.

---

## O QUE MUDA

Hoje o `Cargo.toml` raiz é minimal:
```toml
[workspace]
members = ["leet-core", "leet-bridge", "leet-service", "leet-cli"]
resolver = "2"
```

Cada crate declara a própria versão dentro do seu `Cargo.toml`. Isso gera drift inevitável — um crate fica em 0.4.2, outro em 0.5.0, outro em 0.1.0.

Solução: `[workspace.package]` no raiz define campos compartilhados, e cada crate herda via `version.workspace = true`.

---

## ARQUIVO 1 — `Cargo.toml` (raiz)

```toml
[workspace]
members = ["leet-core", "leet-bridge", "leet-service", "leet-cli"]
resolver = "2"

[workspace.package]
version = "0.5.1"
edition = "2021"
rust-version = "1.75"
authors = ["Yuri Harrison <yuri@leetlang.org>"]
license = "MIT OR Apache-2.0"
repository = "https://github.com/leetlang/leet"
homepage = "https://leetlang.org"
description = "1337 — semantic communication protocol for AI agents"
keywords = ["ai", "agents", "semantic", "protocol", "nlp"]
categories = ["science", "data-structures"]

[workspace.dependencies]
# Rust deps compartilhadas entre crates — opcional, mas ajuda muito.
# Listar só as que múltiplos crates usam.
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
uuid = { version = "1", features = ["v4", "serde"] }
sha2 = "0.10"
thiserror = "1"
anyhow = "1"
```

Ajustar o `authors` email e `repository` URL se diferir da intenção real.

A seção `[workspace.dependencies]` é opcional aqui — listo só como facilitador futuro. Se preferir não mexer em deps agora, pode pular e deixar pra outro commit.

---

## ARQUIVOS 2–5 — `leet-core/Cargo.toml`, `leet-bridge/Cargo.toml`, `leet-service/Cargo.toml`, `leet-cli/Cargo.toml`

Em cada um, substituir o bloco `[package]` pelo padrão:

```toml
# ANTES (exemplo leet-core)
[package]
name = "leet-core"
version = "0.4.2"
edition = "2021"

# DEPOIS
[package]
name = "leet-core"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
authors.workspace = true
license.workspace = true
repository.workspace = true
homepage.workspace = true
description = "Core types and algebra for the 1337 semantic protocol"
keywords.workspace = true
categories.workspace = true
```

O campo `description` permanece específico por crate (cada crate tem sua descrição). Os outros herdam do workspace.

Descrições sugeridas por crate:

| Crate | description |
|---|---|
| leet-core | "Core types and algebra for the 1337 semantic protocol" |
| leet-bridge | "NL↔1337 bridge layer: projector, heuristics, Claude adapter" |
| leet-service | "gRPC service exposing leet-core over network" |
| leet-cli | "Command-line tools for debugging, inspecting, and benchmarking 1337" |

---

## VERIFICATION

```bash
cargo check --workspace
cargo test --workspace

# Confirmar versão homogênea
grep -rn "^version" Cargo.toml leet-*/Cargo.toml
# Esperado no raiz: version = "0.5.1"
# Esperado em cada crate: version.workspace = true

cargo metadata --format-version 1 --no-deps \
  | jq '.packages[] | {name, version}'
# Esperado: todos os 4 crates com "version": "0.5.1"
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt09a "Align all crates to v0.5.1 via [workspace.package]"
# work
task project:1337 +prompt09a done

git add Cargo.toml leet-core/Cargo.toml leet-bridge/Cargo.toml leet-service/Cargo.toml leet-cli/Cargo.toml
git commit -m "chore(workspace): pin all crates to v0.5.1 via workspace.package

- Introduce [workspace.package] in root Cargo.toml: version=0.5.1,
  edition=2021, rust-version=1.75, dual MIT/Apache-2.0 license.
- Each crate inherits version/edition/authors/license via .workspace = true.
- Per-crate description kept specific.
- Added [workspace.dependencies] for common deps (serde, tokio, uuid, ...).

Eliminates version drift across the 4 crates. Future bumps now happen
in one place.

Part of Fase A block 4 (support)."
git push origin main
```

---

**END OF PROMPT_09a**
