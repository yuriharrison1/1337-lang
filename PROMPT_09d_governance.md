# PROMPT 09d — GOVERNANÇA MÍNIMA (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CHANGELOG)

Adicionar os arquivos de governança padrão que todo projeto OSS sério tem. Dual MIT/Apache-2.0 (alinhado com ecossistema Rust). Documentos curtos, funcionais, sem cerimônia.

**PRÉ-REQUISITOS**: nenhum. Pode rodar a qualquer momento.

**ESCOPO**: 6 arquivos novos na raiz + `.gitignore` revisado.

**Taskwarrior**: `+prompt09d`.

---

## ARQUIVO 1 — `LICENSE-MIT`

```text
MIT License

Copyright (c) 2026 Yuri Harrison

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## ARQUIVO 2 — `LICENSE-APACHE`

Texto completo da Apache License 2.0. Baixar de:
https://www.apache.org/licenses/LICENSE-2.0.txt

Adicionar no rodapé:
```text
Copyright 2026 Yuri Harrison
```

## ARQUIVO 3 — `LICENSE`

Pointer para os dois:

```text
Leetlang (1337) is dual-licensed under MIT OR Apache-2.0, at your option.

See LICENSE-MIT and LICENSE-APACHE for full license texts.

Contributions are accepted under the same dual license. By contributing,
you agree that your contributions may be distributed under either license.
```

---

## ARQUIVO 4 — `CONTRIBUTING.md`

```markdown
# Contributing to Leetlang (1337)

Thanks for your interest. This document covers the practical parts of
contributing.

## Before you start

- Read the spec: `docs/spec/en-US/` (or PT-BR if preferred)
- Check open issues and the project board
- For large changes, open an issue to discuss before coding

## Development setup

Requirements:
- Rust 1.75+
- Python 3.10+ (for calibration, bridge Python API)
- Taskwarrior (optional, for project tracking)

```bash
git clone https://github.com/leetlang/leet.git
cd leet
cargo build --workspace
cargo test --workspace
```

## Code style

- Rust: `cargo fmt` + `cargo clippy -- -D warnings`
- Python: `ruff check` + `black`
- Comments: English in code; Portuguese acceptable in scripts/experiments
- Axis names are canonical English (S1_INTENTION, P6_CONFIDENCE, ...);
  see `leet-core/src/axes.rs`

## Pull requests

- One change per PR — small and focused
- Include tests for behavioral changes
- Update CHANGELOG.md under `[Unreleased]`
- Update CONTRACT.md if you touch the task tracking structure
- CI gate: `cargo test --workspace` green

## Spec changes

Changes to the 32-axis canonical space, operators, rules (R1–R23), or
wire format require spec discussion first. Open an issue tagged `spec`.
The spec is versioned (v0.5.1, v0.6, ...); breaking changes bump minor.

## Licensing

Contributions are accepted under dual MIT/Apache-2.0. By submitting a PR,
you confirm your contribution can be distributed under either license.
```

---

## ARQUIVO 5 — `CODE_OF_CONDUCT.md`

Contributor Covenant 2.1 padrão:

```markdown
# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone, regardless of age, body
size, visible or invisible disability, ethnicity, sex characteristics, gender
identity and expression, level of experience, education, socio-economic status,
nationality, personal appearance, race, caste, color, religion, or sexual
identity and orientation.

We pledge to act and interact in ways that contribute to an open, welcoming,
diverse, inclusive, and healthy community.

## Our Standards

Examples of behavior that contributes to a positive environment:
- Demonstrating empathy and kindness toward other people
- Being respectful of differing opinions, viewpoints, and experiences
- Giving and gracefully accepting constructive feedback
- Accepting responsibility and apologizing to those affected by our mistakes
- Focusing on what is best for the overall community

Examples of unacceptable behavior:
- Sexualized language or imagery, and sexual attention or advances of any kind
- Trolling, insulting or derogatory comments, personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct reasonably considered inappropriate in a professional setting

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported to the project team at [contact@leetlang.org]. All complaints will
be reviewed and investigated promptly and fairly.

## Attribution

This Code of Conduct is adapted from the Contributor Covenant, version 2.1,
available at https://www.contributor-covenant.org/version/2/1/code_of_conduct.html
```

Ajustar o email de contato se já existir endereço oficial.

---

## ARQUIVO 6 — `SECURITY.md`

```markdown
# Security Policy

## Supported Versions

Leetlang is in v0.x — only the latest minor version is supported for
security fixes. After v1.0 we will adopt a formal support window.

| Version | Supported |
|---------|-----------|
| 0.5.x   | ✅        |
| < 0.5   | ❌        |

## Reporting a Vulnerability

Please report security issues privately to [security@leetlang.org].

Do **not** open public GitHub issues for security matters.

Expected response times:
- Acknowledgment: within 72 hours
- Initial assessment: within 7 days
- Patch or mitigation timeline: communicated after assessment

## Scope

In-scope:
- Buffer overflows, panics-as-DoS, arithmetic overflows in `leet-core`
- Wire format desync / parser bugs in `codec.rs`
- Auth/identity weaknesses in `compute_align_hash` or handshake
- Bridge layer: injection via RAW fields, rule bypasses

Out of scope:
- Vulnerabilities in third-party LLM providers
- Social engineering of agent impersonation at the application layer
- Denial of service from unbounded user-supplied DAGs (application-level
  rate limiting is caller's responsibility)

## Disclosure

After a fix is released, we will publish a CVE and security advisory on
GitHub with credit to the reporter, unless anonymity is requested.
```

---

## ARQUIVO 7 — `CHANGELOG.md`

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.1] - 2026

### Changed
- 32 canonical axes renamed to English (INTENTION, MASS, CONFIDENCE, ...).
  Short codes (S1..P8) unchanged.
- Canonical space restructured into 4 functional blocks:
  Semantics / Dynamics / Gravity / Precision (8 axes each).
- Three axis substitutions vs v0.5:
  D7 SATURATION → CAUSALITY
  G2 DISTANCE → TEMPORAL_ANCHOR
  P7 COST → ACTION

### Removed
- `unc[32]` vector removed from Cogon struct. Uncertainty now lives in
  three specific axes: S5_ENTROPY, P4_NOISE, P6_CONFIDENCE.

### Wire format
- Frame remains 96 bytes. The 32-byte region formerly holding `unc`
  is now `reserved[32]` and always written as zeros. VERSION stays at
  0x02; a future bump to 0x03 will signal new semantics in that region.
- v0.4 frames decode correctly on v0.5.1 (reserved data is dropped).

### Added
- BLEND operator: per-block rules (D4=min, G1=accumulate, G7=max, P6=min).
- DIST operator: weighted by (c1.P6 + c2.P6)/2 instead of per-dim (1-unc).
- ANOMALY_SCORE: centroid weighted by G1_MASS.
- Rules R22 (axis clamp [0,1]) and R23 (G7_K_INTERACTION normalized).
- Pilar 4 boot defaults: 4 axes deviate from 0.5 on boot
  (S7=1.0, G7=0.1, P1=0.8, P7=0.0).
- W matrix calibrated projector as primary embedding → sem[32] path.
  Keyword heuristics retained as opt-in fallback behind
  `keyword-fallback` feature flag.

### Governance
- Adopted dual MIT/Apache-2.0 license (standard Rust dual licensing).
- Added CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md.

### Internal
- Workspace-wide version alignment via `[workspace.package]`.
- Removed abandoned `leet1337/` experimental parallel workspace
  (preserved in branch `archive/leet1337-experimental`).

## [0.4.0] - 2026

### Added
- 32-axis canonical space across 3 philosophical groups (Ontological,
  Epistemic, Pragmatic) with three valence dimensions (A13, B8, C10).

### Changed
- Expanded from 20 axes (v0.3) to 32.

## Earlier versions

See git history for v0.1 (17 axes), v0.2 (20 axes), v0.3 (30 axes).
```

---

## ARQUIVO 8 — `.gitignore` (revisar e completar)

Sobrescrever ou mesclar com o existente:

```gitignore
# Rust
/target/
**/target/
Cargo.lock.bak

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.whl
dist/
build/
.venv/
venv/
.tox/

# Calibration artifacts (generated, large)
calibration/data/*.bin
calibration/data/*.npy
calibration/data/*.jsonl
# keep a README if present
!calibration/data/README.md

# IDE / editor
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logs and env
*.log
.env
.env.local
.env.*.local

# Taskwarrior / project artifacts
task-*.json
```

Ajustar se o `.gitignore` já tem convenções específicas do projeto; mesclar em vez de sobrescrever nesse caso.

---

## VERIFICATION

```bash
# Verificar que os arquivos estão presentes
ls LICENSE LICENSE-MIT LICENSE-APACHE CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md CHANGELOG.md

# `cargo publish --dry-run` valida que os Cargo.toml encontram a licença
cargo publish -p leet-core --dry-run 2>&1 | head -20
# Esperado: não reclamar de licença ausente

# Verificar .gitignore funcional
git status --ignored | head
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt09d "Add minimal governance: LICENSE (MIT/Apache2), CONTRIBUTING, CoC, SECURITY, CHANGELOG"
# work
task project:1337 +prompt09d done

git add LICENSE LICENSE-MIT LICENSE-APACHE CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md CHANGELOG.md .gitignore

git commit -m "chore: add minimal governance (dual MIT/Apache-2.0, CoC, security, changelog)

Standard OSS governance files for public release:
- LICENSE (dual MIT OR Apache-2.0, standard Rust convention)
- LICENSE-MIT, LICENSE-APACHE (full texts)
- CONTRIBUTING.md (dev setup, PR process, style)
- CODE_OF_CONDUCT.md (Contributor Covenant 2.1)
- SECURITY.md (disclosure policy, scope, response SLAs)
- CHANGELOG.md (v0.5.1 entry with full change list)
- .gitignore (Rust, Python, calibration artifacts, IDE)

Part of Fase A block 4 (support)."

git push origin main
```

---

**END OF PROMPT_09d — FASE A BLOCK 4 COMPLETE**
