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

This project is licensed under the Apache License 2.0. By submitting a PR,
you confirm your contribution can be distributed under this license.
