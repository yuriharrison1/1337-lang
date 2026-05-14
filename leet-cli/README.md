# leet-cli

[![crates.io](https://img.shields.io/crates/v/leet-cli.svg)](https://crates.io/crates/leet-cli)
[![docs.rs](https://docs.rs/leet-cli/badge.svg)](https://docs.rs/leet-cli)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](../LICENSE)

Command-line toolkit for the 1337 semantic protocol.

## Install

```bash
cargo install leet-cli
```

This installs both `leet` (CLI) and `leet-mcp` (MCP server for IDE integration).

## Quick start

```bash
# Check your setup
leet doctor

# Set up IDE integration
leet setup claude-code    # or: cursor / vscode

# Download the calibrated W matrix (improves projection quality)
leet calibrate --download

# Encode text to a COGON sem vector
leet encode "Deploy failed in production"

# List the 32 canonical axes
leet axes
```

## Commands

### Setup & diagnostics
| Command | Description |
|---|---|
| `leet setup` | Configure IDE integrations (Claude Code, Cursor, VS Code) |
| `leet doctor` | System health check: binaries, IDEs, W matrix, project store |
| `leet calibrate` | Download and manage the W matrix |
| `leet version` | Print version information for all components |

### Project memory
| Command | Description |
|---|---|
| `leet absorb` | Bulk-import Claude Code session history into the store |
| `leet consolidate` | Inspect, force, or rebuild the consolidation pyramid |

### COGON algebra
| Command | Description |
|---|---|
| `leet encode` | Text → sem[32] vector |
| `leet decode` | sem[32] → top-axis narrative |
| `leet dist` | Cosine distance between two COGONs |
| `leet blend` | Blend two COGONs (BLEND operator) |
| `leet validate` | Validate a 1337 message against R1–R25 |
| `leet inspect` | Storage statistics for a project |

### Protocol reference
| Command | Description |
|---|---|
| `leet axes` | List the 32 canonical axes |
| `leet zero` | Print COGON_ZERO (canonical boot vector) |

### Shell completions
```bash
leet completions bash  >> ~/.bash_completion.d/leet
leet completions zsh   > ~/.zsh/completions/_leet
leet completions fish  > ~/.config/fish/completions/leet.fish
```

Run `leet <command> --help` for details on any command, or `leet help` for a
categorized overview.

## License

Apache-2.0. Part of the [1337 project](https://github.com/leetlang/leet).
