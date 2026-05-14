# leet-bridge

[![crates.io](https://img.shields.io/crates/v/leet-bridge.svg)](https://crates.io/crates/leet-bridge)
[![docs.rs](https://docs.rs/leet-bridge/badge.svg)](https://docs.rs/leet-bridge)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](../LICENSE)

NL↔1337 bridge layer: projects natural language text into COGON semantic vectors.

## What's here

- `project_text_simple(text)` — NL → `Cogon` (no API key, uses local hash-trigram provider)
- `WMatrix` — calibrated projection matrix; `load()`, `save()`, `project()`
- `default_user_w_path()` — XDG path where `leet calibrate --download` installs W.bin
- `EmbeddingProvider` trait — plug in OpenAI, sentence-transformers, or a mock
- `MockProjector` — deterministic keyword-based projector for tests (no network)

## Features

| Feature | Description |
|---|---|
| `keyword-fallback` | Fall back to heuristic rules when W.bin is unavailable |

## Usage

```toml
[dependencies]
leet-bridge = { version = "0.5", features = ["keyword-fallback"] }
```

```rust
use leet_bridge::projector::{project_text_simple, default_user_w_path, WMatrix};

// Project text → COGON (uses W matrix if available, else hash-trigram)
let cogon = project_text_simple("deploy failed in production")?;

// Load a calibrated W matrix explicitly
let w = WMatrix::load(default_user_w_path())?;
let sem = w.project(&embedding)?;
```

## W matrix format (v1)

```
Offset  Size   Content
──────────────────────────────────────
0       4      magic = b"LEET"
4       1      version = 0x01
5       3      reserved (zeros)
8       4      u32 LE rows (always 32)
12      4      u32 LE cols (embedding dim)
16      n×4    f32 LE data[rows × cols], row-major
```

Install the official W matrix: `leet calibrate --download`

## License

Apache-2.0. Part of the [1337 project](https://github.com/leetlang/leet).
