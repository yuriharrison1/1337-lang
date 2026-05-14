# PROMPT 12-W-01 — W.BIN FORMAT HARDENING + PATH DISCOVERY

Endurecer o formato binário do W.bin (adicionar magic bytes + versão), adicionar `~/.local/share/leet/W.bin` ao search path, implementar `WMatrix::save()`, e melhorar mensagens de erro usando `UserFacingError`. Sem mudança de comportamento externo — só robustez.

**PRÉ-REQUISITOS**: Fase 12-U executada. Workspace verde com `UserFacingError` em uso.

**ESCOPO**: 1 arquivo (`leet-bridge/src/projector.rs`) + pequeno ajuste em `leet-cli/src/cmd/doctor.rs` pra usar path correto.

**Taskwarrior**: `+prompt12_W_01`.

---

## PROBLEMA ATUAL

`WMatrix::load()` em `leet-bridge/src/projector.rs` lê `[u32 rows][u32 cols][f32 * rows * cols]` sem qualquer magic bytes. Problemas:

1. Um arquivo qualquer com ≥8 bytes passa na verificação. Só falha no `read_exact` do corpo.
2. `WMatrixCorrupted` nunca é emitido — só `WLoadError` genérico.
3. `find_w_path()` não procura `~/.local/share/leet/W.bin` — caminho padrão pra usuário instalado.
4. `WMatrix::save()` não existe — calibrate vai precisar.

---

## NOVO FORMATO W.BIN

```
Offset  Size  Type    Value
──────────────────────────────────────────
0       4     bytes   magic = b"LEET"
4       1     u8      version = 0x01
5       3     bytes   reserved = 0x00 0x00 0x00
8       4     u32 LE  rows (must be 32)
12      4     u32 LE  cols (embedding dim, e.g. 768)
16      n*4   f32 LE  data[rows * cols], row-major
```

Header total: 16 bytes. Backwards-incompatível com qualquer W.bin existente (sem magic = arquivo antigo). `load()` rejeita sem magic com `WMatrixCorrupted`.

---

## EDITS EM `leet-bridge/src/projector.rs`

### Constantes

```rust
const W_MAGIC: &[u8; 4] = b"LEET";
const W_VERSION: u8 = 0x01;
const W_HEADER_SIZE: usize = 16;
```

### `WMatrix::load()` — novo

```rust
pub fn load<P: AsRef<Path>>(path: P) -> Result<Self, BridgeError> {
    let path = path.as_ref();
    let mut file = std::fs::File::open(path)
        .map_err(|e| BridgeError::WLoadError(format!("open {}: {e}", path.display())))?;

    let mut header = [0u8; W_HEADER_SIZE];
    file.read_exact(&mut header)
        .map_err(|_| BridgeError::WCorrupted(format!(
            "{}: header too short (not a W.bin?)", path.display()
        )))?;

    if &header[0..4] != W_MAGIC {
        return Err(BridgeError::WCorrupted(format!(
            "{}: invalid magic bytes (expected LEET, got {:?})",
            path.display(), &header[0..4]
        )));
    }
    if header[4] != W_VERSION {
        return Err(BridgeError::WCorrupted(format!(
            "{}: unsupported version {} (expected {})",
            path.display(), header[4], W_VERSION
        )));
    }

    let rows = u32::from_le_bytes(header[8..12].try_into().unwrap()) as usize;
    let cols = u32::from_le_bytes(header[12..16].try_into().unwrap()) as usize;

    if rows != 32 {
        return Err(BridgeError::WCorrupted(format!(
            "{}: expected 32 rows, got {rows}", path.display()
        )));
    }

    let n = rows * cols;
    let mut buf = vec![0u8; n * 4];
    file.read_exact(&mut buf)
        .map_err(|_| BridgeError::WCorrupted(format!(
            "{}: data truncated (expected {} floats)", path.display(), n
        )))?;

    let data = buf
        .chunks_exact(4)
        .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
        .collect();

    Ok(Self { rows, cols, data })
}
```

### `WMatrix::save()` — novo

```rust
pub fn save<P: AsRef<Path>>(&self, path: P) -> Result<(), BridgeError> {
    use std::io::Write as IoWrite;
    let path = path.as_ref();

    // Write to temp then rename (atomic).
    let tmp = path.with_extension("bin.tmp");
    let mut f = std::fs::File::create(&tmp)
        .map_err(|e| BridgeError::WLoadError(format!("create {}: {e}", tmp.display())))?;

    let mut header = [0u8; W_HEADER_SIZE];
    header[0..4].copy_from_slice(W_MAGIC);
    header[4] = W_VERSION;
    header[8..12].copy_from_slice(&(self.rows as u32).to_le_bytes());
    header[12..16].copy_from_slice(&(self.cols as u32).to_le_bytes());
    f.write_all(&header)
        .map_err(|e| BridgeError::WLoadError(format!("write header: {e}")))?;

    for &v in &self.data {
        f.write_all(&v.to_le_bytes())
            .map_err(|e| BridgeError::WLoadError(format!("write data: {e}")))?;
    }
    f.sync_all()
        .map_err(|e| BridgeError::WLoadError(format!("fsync: {e}")))?;
    drop(f);

    std::fs::rename(&tmp, path)
        .map_err(|e| BridgeError::WLoadError(format!("rename: {e}")))?;
    Ok(())
}
```

### `find_w_path()` — adicionar XDG user data dir

```rust
fn find_w_path() -> Option<PathBuf> {
    // 1. Env override
    if let Ok(p) = std::env::var("LEET_W_PATH") {
        let pb = PathBuf::from(p);
        if pb.exists() { return Some(pb); }
    }
    // 2. XDG user data dir (~/.local/share/leet/W.bin)
    if let Some(home) = dirs_or_home() {
        let p = home.join(".local/share/leet/W.bin");
        if p.exists() { return Some(p); }
    }
    // 3. Local workspace (dev/test)
    let local = PathBuf::from("calibration/data/W.bin");
    if local.exists() { return Some(local); }
    // 4. System install
    let system = PathBuf::from("/usr/share/leetlang/W.bin");
    if system.exists() { return Some(system); }
    None
}

fn dirs_or_home() -> Option<PathBuf> {
    // Try XDG_DATA_HOME first, then $HOME
    if let Ok(d) = std::env::var("XDG_DATA_HOME") {
        // XDG_DATA_HOME already *is* the data dir; W.bin lives at leet/W.bin
        let p = PathBuf::from(d).join("leet/W.bin");
        if p.parent().map_or(false, |pp| pp.exists()) {
            return p.parent().map(|pp| pp.parent().unwrap_or(pp).to_path_buf());
        }
    }
    // Fall back: $HOME
    std::env::var("HOME").ok().map(PathBuf::from)
}
```

Nota: como o `find_w_path` é interno, a mudança mais limpa é só adicionar o check do `~/.local/share/leet/W.bin` diretamente:

```rust
fn find_w_path() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("LEET_W_PATH") {
        let pb = PathBuf::from(p);
        if pb.exists() { return Some(pb); }
    }
    // XDG user data dir
    let xdg_home = std::env::var("XDG_DATA_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            std::env::var("HOME")
                .map(|h| PathBuf::from(h).join(".local/share"))
                .unwrap_or_else(|_| PathBuf::from("/tmp"))
        });
    let user_w = xdg_home.join("leet/W.bin");
    if user_w.exists() { return Some(user_w); }

    let local = PathBuf::from("calibration/data/W.bin");
    if local.exists() { return Some(local); }
    let installed = PathBuf::from("/usr/share/leetlang/W.bin");
    if installed.exists() { return Some(installed); }
    None
}
```

### Expor path padrão do usuário como função pública

```rust
/// Returns the canonical path where `leet calibrate --download` installs W.bin.
pub fn default_user_w_path() -> PathBuf {
    let xdg = std::env::var("XDG_DATA_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            std::env::var("HOME")
                .map(|h| PathBuf::from(h).join(".local/share"))
                .unwrap_or_else(|_| PathBuf::from("/tmp"))
        });
    xdg.join("leet/W.bin")
}
```

Usado pelo `leet calibrate --download` para saber onde salvar.

---

## AJUSTE EM `leet-bridge/src/error.rs`

Adicionar variante `WCorrupted` se não existir:

```rust
#[derive(Debug, thiserror::Error)]
pub enum BridgeError {
    #[error("W matrix not available — install via `leet calibrate --download`")]
    WMatrixNotAvailable,

    #[error("W matrix corrupted: {0}")]
    WCorrupted(String),

    #[error("W matrix load error: {0}")]
    WLoadError(String),

    #[error("Dimension mismatch: expected {expected}, got {got}")]
    DimensionMismatch { expected: usize, got: usize },
    // ... existing variants
}
```

---

## AJUSTE EM `leet-cli/src/cmd/doctor.rs`

`WMatrixCheck::find_w_paths()` deve usar o mesmo `find_w_path()` do bridge. Atualmente duplica lógica. Substituir por:

```rust
fn check_w_matrix() -> CheckResult {
    // Use bridge's canonical path list
    let search_paths = vec![
        std::env::var("LEET_W_PATH").ok().map(std::path::PathBuf::from),
        Some(leet_bridge::projector::default_user_w_path()),
        Some(std::path::PathBuf::from("calibration/data/W.bin")),
        Some(std::path::PathBuf::from("/usr/share/leetlang/W.bin")),
    ];
    // ... rest of existing logic using search_paths
}
```

Isso requer tornar `default_user_w_path()` `pub` em leet-bridge (já está no código acima).

---

## NOVOS TESTES

Em `leet-bridge/src/projector.rs`, bloco `#[cfg(test)] mod w_format`:

```rust
#[test]
fn save_load_roundtrip() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("W.bin");
    let original = WMatrix {
        rows: 32,
        cols: 4,
        data: (0..128).map(|i| i as f32 * 0.01).collect(),
    };
    original.save(&path).unwrap();
    let loaded = WMatrix::load(&path).unwrap();
    assert_eq!(loaded.rows, 32);
    assert_eq!(loaded.cols, 4);
    assert_eq!(loaded.data.len(), 128);
    for (a, b) in original.data.iter().zip(loaded.data.iter()) {
        assert!((a - b).abs() < 1e-6);
    }
}

#[test]
fn load_rejects_wrong_magic() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("bad.bin");
    let mut data = vec![0u8; 20];
    data[0..4].copy_from_slice(b"NOPE");
    std::fs::write(&path, &data).unwrap();
    assert!(matches!(WMatrix::load(&path), Err(BridgeError::WCorrupted(_))));
}

#[test]
fn load_rejects_truncated_data() {
    let tmp = tempfile::tempdir().unwrap();
    let path = tmp.path().join("trunc.bin");
    // Write valid header but no body
    let mut header = [0u8; 16];
    header[0..4].copy_from_slice(b"LEET");
    header[4] = 0x01;
    header[8..12].copy_from_slice(&32u32.to_le_bytes());
    header[12..16].copy_from_slice(&4u32.to_le_bytes());
    std::fs::write(&path, &header).unwrap();
    assert!(matches!(WMatrix::load(&path), Err(BridgeError::WCorrupted(_))));
}

#[test]
fn load_rejects_wrong_version() {
    let tmp = tempfile::tempdir().unwrap();
    let w = WMatrix { rows: 32, cols: 2, data: vec![0.5; 64] };
    let path = tmp.path().join("W.bin");
    w.save(&path).unwrap();
    // Corrupt version byte
    let mut bytes = std::fs::read(&path).unwrap();
    bytes[4] = 0xFF;
    std::fs::write(&path, &bytes).unwrap();
    assert!(matches!(WMatrix::load(&path), Err(BridgeError::WCorrupted(_))));
}
```

---

## GATES

```bash
# Testes do bridge
cargo test -p leet-bridge
# Esperado: todos OK, incluindo os 4 novos testes de formato

# Build sem warnings
cargo build --workspace 2>&1 | grep -c "^warning"
# Esperado: 0

# Smoke: load arquivo antigo sem magic falha humanamente
echo "old format no magic" > /tmp/bad_w.bin
LEET_W_PATH=/tmp/bad_w.bin ./target/debug/leet doctor 2>&1 | grep -q "corrupted\|invalid\|magic"
# Esperado: mensagem mencionando problema no W.bin
```
