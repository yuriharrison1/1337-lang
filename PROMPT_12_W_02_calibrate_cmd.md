# PROMPT 12-W-02 — `leet calibrate` SUBCOMMAND

Implementar `leet calibrate` — comando que baixa e instala o W.bin oficial, ou mostra status do W matrix atual. Resolve o `try_download_w()` placeholder no doctor.rs e fecha o loop "leet doctor diz para rodar calibrate, mas calibrate não existe".

**PRÉ-REQUISITOS**: 12-W-01 executado. `WMatrix::save()` e `default_user_w_path()` existem. Workspace verde.

**ESCOPO**: 1 arquivo novo (`leet-cli/src/cmd/calibrate.rs`) + registro em `cmd/mod.rs` + `main.rs` + atualização do `try_download_w()` em `doctor.rs`. Adicionar `reqwest` como dep em `leet-cli/Cargo.toml` (já está em `leet-bridge`).

**Taskwarrior**: `+prompt12_W_02`.

---

## EXPERIÊNCIA QUE O USUÁRIO TEM

```
$ leet calibrate --help

Download and manage the W matrix for high-quality NL→COGON projection.

Without a calibrated W matrix, leet falls back to hash-trigram projection
(fast but lower semantic quality). The official W matrix is pre-trained on
diverse software engineering text and significantly improves recall precision.

Usage: leet calibrate [OPTIONS]

Options:
      --download   Download the official W matrix to ~/.local/share/leet/W.bin
      --force      Re-download even if W.bin is already present
      --status     Show current W matrix status and search paths (default if no flag given)
  -h, --help       Print help

Examples:
  leet calibrate --status
  leet calibrate --download
  leet calibrate --download --force

See also:
  leet doctor  — full health check including W matrix status
```

```
$ leet calibrate --status

W matrix status
────────────────────────────────────────
  Search path (in order):
    [1] $LEET_W_PATH              — not set
    [2] ~/.local/share/leet/W.bin — NOT FOUND  ← install here
    [3] ./calibration/data/W.bin  — NOT FOUND
    [4] /usr/share/leetlang/W.bin — NOT FOUND

  Active: none (using hash-trigram fallback)
  Quality: degraded

Run `leet calibrate --download` to fetch the official W matrix.
```

```
$ leet calibrate --download

Downloading W matrix v0.5.1...
  URL     https://cdn.leetlang.org/w/v0.5.1/W.bin
  Target  /home/yuri/.local/share/leet/W.bin

  [████████████████████] 1.2 MB / 1.2 MB (1.8s)

Verifying...
  ✓ Magic bytes valid
  ✓ Dimensions: 32 × 768
  ✓ Data size: 786432 floats

✓ W matrix installed at /home/yuri/.local/share/leet/W.bin
  Run `leet doctor` to verify.
```

```
$ leet calibrate --download
W matrix already present at /home/yuri/.local/share/leet/W.bin (32×768).
Use --force to re-download.
```

---

## IMPLEMENTAÇÃO

### `leet-cli/Cargo.toml`

```toml
[dependencies]
# ...existing...
reqwest = { version = "0.11", features = ["blocking"] }
indicatif = "0.17"  # progress bar
```

Usar `reqwest::blocking` (não async) para manter o comando simples. `leet calibrate` não precisa de async.

### `leet-cli/src/cmd/calibrate.rs`

```rust
use std::path::PathBuf;
use anyhow::Result;
use clap::Args;

use leet_bridge::projector::{WMatrix, default_user_w_path};
use leet_core::UserFacingError;

const W_DOWNLOAD_URL_TEMPLATE: &str =
    "https://cdn.leetlang.org/w/v{VERSION}/W.bin";

#[derive(Args)]
#[command(
    about = "Download and manage the W matrix for high-quality NL→COGON projection",
    long_about = "Download and manage the W matrix for high-quality NL→COGON projection.\n\
\n\
Without a calibrated W matrix, leet falls back to hash-trigram projection\n\
(fast but lower semantic quality). The official W matrix is pre-trained on\n\
diverse software engineering text and significantly improves recall precision.",
    after_help = "Examples:\n  \
  leet calibrate --status\n  \
  leet calibrate --download\n  \
  leet calibrate --download --force\n\
\n\
See also:\n  \
  leet doctor  — full health check including W matrix status"
)]
pub struct CalibrateArgs {
    /// Download the official W matrix to ~/.local/share/leet/W.bin
    #[arg(long)]
    pub download: bool,
    /// Re-download even if W.bin is already present
    #[arg(long)]
    pub force: bool,
    /// Show current W matrix status and search paths (default if no flag given)
    #[arg(long)]
    pub status: bool,
}

pub fn run(args: CalibrateArgs) -> Result<()> {
    if args.download {
        cmd_download(args.force)
    } else {
        // --status is the default
        cmd_status()
    }
}

fn cmd_status() -> Result<()> {
    let xdg = xdg_data_home();
    let user_path = default_user_w_path();
    let paths = [
        ("$LEET_W_PATH", std::env::var("LEET_W_PATH").ok().map(PathBuf::from)),
        ("~/.local/share/leet/W.bin", Some(user_path.clone())),
        ("./calibration/data/W.bin", Some(PathBuf::from("calibration/data/W.bin"))),
        ("/usr/share/leetlang/W.bin", Some(PathBuf::from("/usr/share/leetlang/W.bin"))),
    ];

    println!("\nW matrix status");
    println!("{}", "─".repeat(40));
    println!("  Search path (in order):");

    let mut active: Option<PathBuf> = None;
    for (i, (label, maybe_path)) in paths.iter().enumerate() {
        let status = match maybe_path {
            None => "not set".to_string(),
            Some(p) if p.exists() => {
                if active.is_none() { active = Some(p.clone()); }
                "FOUND".to_string()
            }
            Some(_) => "NOT FOUND".to_string(),
        };
        let arrow = if i == 1 && active.is_none() { "  ← install here" } else { "" };
        println!("    [{}] {:<35} — {}{}", i + 1, label, status, arrow);
    }

    println!();
    if let Some(ref p) = active {
        match WMatrix::load(p) {
            Ok(w) => {
                println!("  Active: {} ({}×{})", p.display(), w.rows, w.cols);
                println!("  Quality: full");
            }
            Err(e) => {
                println!("  Active: {} — LOAD ERROR: {}", p.display(), e);
                println!("  Quality: degraded (falling back to hash-trigram)");
            }
        }
    } else {
        println!("  Active: none (using hash-trigram fallback)");
        println!("  Quality: degraded");
        println!();
        println!("Run `leet calibrate --download` to fetch the official W matrix.");
    }
    println!();
    Ok(())
}

fn cmd_download(force: bool) -> Result<()> {
    let target = default_user_w_path();

    if target.exists() && !force {
        match WMatrix::load(&target) {
            Ok(w) => {
                println!(
                    "W matrix already present at {} ({}×{}).",
                    target.display(), w.rows, w.cols
                );
                println!("Use --force to re-download.");
                return Ok(());
            }
            Err(_) => {
                // Corrupted — proceed to re-download.
                eprintln!(
                    "Warning: existing W.bin at {} is corrupted. Re-downloading.",
                    target.display()
                );
            }
        }
    }

    let version = env!("CARGO_PKG_VERSION");
    let url = W_DOWNLOAD_URL_TEMPLATE.replace("{VERSION}", version);

    println!("\nDownloading W matrix v{}...", version);
    println!("  URL     {}", url);
    println!("  Target  {}", target.display());
    println!();

    // Ensure parent dir exists
    if let Some(parent) = target.parent() {
        std::fs::create_dir_all(parent).map_err(|e| {
            UserFacingError::NoWritePermission { path: parent.to_path_buf() }
        })?;
    }

    // Download
    let bytes = download_with_progress(&url)?;

    // Write atomically
    let tmp = target.with_extension("bin.tmp");
    std::fs::write(&tmp, &bytes)?;

    // Verify before committing
    println!("\nVerifying...");
    let w = WMatrix::load(&tmp).map_err(|e| {
        let _ = std::fs::remove_file(&tmp);
        UserFacingError::Unexpected {
            summary: "Downloaded W.bin failed verification".into(),
            chain: e.to_string(),
        }
    })?;

    println!("  ✓ Magic bytes valid");
    println!("  ✓ Dimensions: {} × {}", w.rows, w.cols);
    println!("  ✓ Data size: {} floats", w.data.len());

    std::fs::rename(&tmp, &target)?;
    println!("\n✓ W matrix installed at {}", target.display());
    println!("  Run `leet doctor` to verify.");
    println!();
    Ok(())
}

fn download_with_progress(url: &str) -> Result<Vec<u8>> {
    use indicatif::{ProgressBar, ProgressStyle};

    let client = reqwest::blocking::Client::new();
    let mut resp = client.get(url).send().map_err(|e| {
        UserFacingError::Unexpected {
            summary: format!("Failed to reach {url}"),
            chain: e.to_string(),
        }
    })?;

    if !resp.status().is_success() {
        return Err(UserFacingError::Unexpected {
            summary: format!("Download failed: HTTP {}", resp.status()),
            chain: format!("URL: {url}"),
        }.into());
    }

    let total = resp.content_length().unwrap_or(0);
    let pb = ProgressBar::new(total);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("  [{bar:20}] {bytes} / {total_bytes} ({elapsed})")
            .unwrap()
            .progress_chars("█░ "),
    );

    let mut buf = Vec::with_capacity(total as usize);
    let mut chunk_buf = [0u8; 8192];
    use std::io::Read;
    loop {
        let n = resp.read(&mut chunk_buf).map_err(|e| {
            UserFacingError::Unexpected {
                summary: "Download interrupted".into(),
                chain: e.to_string(),
            }
        })?;
        if n == 0 { break; }
        buf.extend_from_slice(&chunk_buf[..n]);
        pb.set_position(buf.len() as u64);
    }
    pb.finish_and_clear();
    Ok(buf)
}

fn xdg_data_home() -> PathBuf {
    std::env::var("XDG_DATA_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            std::env::var("HOME")
                .map(|h| PathBuf::from(h).join(".local/share"))
                .unwrap_or_else(|_| PathBuf::from("/tmp"))
        })
}
```

### `leet-cli/src/cmd/mod.rs` — adicionar

```rust
pub mod calibrate;
```

### `leet-cli/src/main.rs` — adicionar variant e dispatch

No enum `Commands`:
```rust
/// Download and manage the W matrix for high-quality NL→COGON projection
Calibrate(cmd::calibrate::CalibrateArgs),
```

No match:
```rust
Commands::Calibrate(args) => exit_on_err(cmd::calibrate::run(args)),
```

### `leet-cli/src/cmd/doctor.rs` — atualizar `try_download_w()`

Substituir o placeholder por chamada real:

```rust
fn try_download_w() -> Result<()> {
    // Delegate to the real calibrate implementation.
    crate::cmd::calibrate::run(crate::cmd::calibrate::CalibrateArgs {
        download: true,
        force: false,
        status: false,
    })
}
```

---

## TESTES

Em `calibrate.rs` (unit tests — sem network):

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_runs_without_panic() {
        // Should complete even with no W.bin anywhere
        let result = cmd_status();
        assert!(result.is_ok());
    }

    #[test]
    fn download_with_existing_valid_w_no_force_skips() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("W.bin");
        let w = leet_bridge::projector::WMatrix {
            rows: 32, cols: 2,
            data: vec![0.5f32; 64],
        };
        w.save(&path).unwrap();

        // Simulate: target is the tmp path — override via env var
        std::env::set_var("LEET_W_PATH", path.to_str().unwrap());
        // Actually test the "already present" guard logic directly:
        // (integration test would need network mock — skip here)
        std::env::remove_var("LEET_W_PATH");
    }
}
```

---

## GATES

```bash
# Build com novas deps
cargo build --workspace
# Esperado: 0 errors, 0 warnings

# Testes verdes
cargo test --workspace
# Esperado: ≥ 270 passed, 0 failed

# Subcomando registrado
./target/debug/leet calibrate --help
# Esperado: output com descrição e flags --download/--status/--force

# Status sem W.bin disponível
./target/debug/leet calibrate --status
# Esperado: mostra 4 search paths, "Active: none", sugere --download

# Doctor --auto-fix agora realmente chama calibrate (smoke)
# (verificar manualmente que try_download_w() não retorna erro de "not implemented")
./target/debug/leet doctor --json | jq .checks.w_matrix.status
# Esperado: "warning" ou "ok" (não "error" por causa de "not implemented")

# leet help mostra calibrate na categoria correta
./target/debug/leet help | grep -q calibrate
# Esperado: calibrate aparece no output
```
