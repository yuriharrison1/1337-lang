# PROMPT 12-U-04 — EDGE CASES REAIS

Tornar leet robusto contra situações que vão acontecer no uso real: 2 projetos com mesmo basename, store corrompido mid-write, fsync falhou, sem permissão de escrita, conflito de schema entre versões, `LEET_PROJECT_ROOT` apontando pra dir inexistente. Cada caso tem comportamento previsível, mensagem útil (via `UserFacingError`), e teste cobrindo o cenário.

**PRÉ-REQUISITOS**: 12-U-01, 12-U-02, 12-U-03 executados. Workspace verde com `UserFacingError` em uso.

**ESCOPO**: edits cirúrgicos em `leet-mcp/src/store.rs`, `leet-mcp/src/index.rs`, `leet-cli/src/cmd/setup.rs`, e adição de testes específicos.

**Taskwarrior**: `+prompt12_U_04`.

---

## OS 7 CENÁRIOS COBERTOS

| # | Cenário | Comportamento esperado |
|---|---|---|
| 1 | Dois projetos com mesmo basename (`/a/myapp` e `/b/myapp`) | Stores isolados via path absoluto canonicalizado |
| 2 | `store.bin` truncado mid-write (crash entre append+fsync) | Trunca tail incompleto silenciosamente, log warn |
| 3 | `index.bin` desincronizado de `store.bin` | Erro claro + sugestão `consolidate rebuild-index` |
| 4 | fsync falhou (disco cheio, permissão) | Erro humano via `UserFacingError`, não panic |
| 5 | Sem permissão de escrita em `.leet/` | `NoWritePermission` específico, não anyhow genérico |
| 6 | Schema mismatch (store v0.5.0 + binário v1.0) | `StoreVersionMismatch`, sugestão de migração |
| 7 | `LEET_PROJECT_ROOT` aponta pra dir inexistente | Erro humano, não silenciosamente cria lá |

Cada um tem teste cobrindo. Nenhum tem comportamento "panic" — todos retornam `UserFacingError`.

---

## CENÁRIO 1 — DOIS PROJETOS COM MESMO BASENAME

### Problema

Hoje, internamente, `PersonalStore::open_or_create(path)` aceita o path do projeto e cria `<path>/.leet/store.bin`. Bom. Mas a **identidade do projeto** é só o path. Se o usuário tem `/home/yuri/code/myapp` e `/tmp/exp/myapp`, e por algum motivo as paths colapsam (link simbólico, mount, etc), os stores podem confundir.

### Solução

Sempre canonicalizar o path antes de usar como identidade. `std::fs::canonicalize` resolve symlinks e relativize.

### Edit em `leet-mcp/src/store.rs`

```rust
impl PersonalStore {
    pub fn open_or_create(project_root: &Path) -> Result<Self> {
        // Canonicalize the project root. If it doesn't exist, that's an error.
        let canonical_root = project_root.canonicalize()
            .map_err(|e| {
                if e.kind() == std::io::ErrorKind::NotFound {
                    anyhow::Error::new(
                        leet_core::UserFacingError::NotInProject {
                            cwd: project_root.to_path_buf(),
                        }
                    )
                } else {
                    anyhow::Error::new(e).context(format!(
                        "canonicalizing project root {}", project_root.display()
                    ))
                }
            })?;

        let leet_dir = canonical_root.join(".leet");
        // ... rest unchanged ...
    }
}
```

### Teste

```rust
#[test]
fn canonicalizes_project_root() {
    let tmp = tempfile::tempdir().unwrap();
    let real = tmp.path().join("real-project");
    std::fs::create_dir_all(&real).unwrap();

    let symlink = tmp.path().join("link-to-project");
    std::os::unix::fs::symlink(&real, &symlink).unwrap();

    let s1 = PersonalStore::open_or_create(&real).unwrap();
    let s2 = PersonalStore::open_or_create(&symlink).unwrap();
    // Should resolve to same .leet directory
    assert_eq!(s1.leet_dir(), s2.leet_dir());
}

#[test]
fn nonexistent_project_root_fails_humanly() {
    let nonexistent = std::path::PathBuf::from("/tmp/leet-does-not-exist-xyz123");
    let result = PersonalStore::open_or_create(&nonexistent);
    assert!(result.is_err());
    let err = result.unwrap_err();
    let user_err = err.downcast_ref::<leet_core::UserFacingError>();
    assert!(matches!(user_err, Some(leet_core::UserFacingError::NotInProject { .. })));
}
```

(Se `PersonalStore` não tem `leet_dir()` exposto, adiciona simples getter `pub fn leet_dir(&self) -> &Path`.)

---

## CENÁRIO 2 — STORE TRUNCADO MID-WRITE

### Problema

Append: `O_APPEND write 360 bytes → fsync → push to in-memory vec`. Se o crash acontece entre os 360 bytes escritos e o fsync, ou durante a escrita parcial, o `store.bin` pode terminar com 350 bytes pendentes (não múltiplo de 360).

### Solução

Na abertura, detectar tail incompleto:

```rust
let store_size = std::fs::metadata(&store_path)?.len();
const HEADER_SIZE: u64 = 16;
const RECORD_SIZE: u64 = 360;

if store_size > HEADER_SIZE {
    let after_header = store_size - HEADER_SIZE;
    let trailing_bytes = after_header % RECORD_SIZE;
    if trailing_bytes != 0 {
        let truncate_to = HEADER_SIZE + (after_header / RECORD_SIZE) * RECORD_SIZE;
        tracing::warn!(
            "store.bin has {} trailing bytes (incomplete record); \
             truncating to {} bytes (likely from a previous crash)",
            trailing_bytes, truncate_to
        );
        let f = std::fs::OpenOptions::new().write(true).open(&store_path)?;
        f.set_len(truncate_to)?;
        f.sync_all()?;
    }
}
```

Coloca essa lógica no início de `PersonalStore::open_or_create`, antes da leitura dos records.

### Teste

```rust
#[test]
fn truncates_incomplete_tail_silently() {
    let tmp = tempfile::tempdir().unwrap();

    // Create a store with 1 valid record + 100 bytes of garbage trailing
    let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
    store.append(make_test_record("real entry")).unwrap();
    drop(store);

    let store_path = tmp.path().join(".leet/store.bin");
    let original_size = std::fs::metadata(&store_path).unwrap().len();
    assert_eq!(original_size, 16 + 360);

    // Append garbage (simulate crash during write)
    {
        use std::io::Write;
        let mut f = std::fs::OpenOptions::new()
            .append(true).open(&store_path).unwrap();
        f.write_all(&[0xff; 100]).unwrap();
    }

    // Reopen — should truncate silently
    let store = PersonalStore::open_or_create(tmp.path()).unwrap();
    assert_eq!(store.len(), 1);
    let final_size = std::fs::metadata(&store_path).unwrap().len();
    assert_eq!(final_size, 16 + 360);
}
```

---

## CENÁRIO 3 — INDEX DESINCRONIZADO

### Problema

Se store tem 47 records mas index tem 30 entries, leet vai pensar que só existem 30 records relevantes. Pode acontecer se alguém deleta `index.bin` manualmente, ou se uma versão antiga rodou um append sem atualizar index.

### Solução

Detectar mismatch na abertura e **falhar** com erro claro pedindo `consolidate rebuild-index`. Não tentar adivinhar — usuário decide se quer regenerar (lossy) ou se quer investigar manualmente.

### Edit em `leet-mcp/src/store.rs`

Após carregar records e index, validar:

```rust
if self.records.len() != self.index.entries.len() {
    return Err(anyhow::Error::new(leet_core::UserFacingError::IndexOutOfSync {
        store_path: store_path.clone(),
        index_path: index_path.clone(),
        store_count: self.records.len(),
        index_count: self.index.entries.len(),
    }));
}
```

### Teste

```rust
#[test]
fn detects_index_mismatch() {
    let tmp = tempfile::tempdir().unwrap();
    let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
    for i in 0..3 {
        store.append(make_test_record(&format!("rec{i}"))).unwrap();
    }
    drop(store);

    // Truncate index.bin to remove last entry (simulate desync)
    let index_path = tmp.path().join(".leet/index.bin");
    let size = std::fs::metadata(&index_path).unwrap().len();
    let new_size = size - 24; // remove 1 entry
    let f = std::fs::OpenOptions::new().write(true).open(&index_path).unwrap();
    f.set_len(new_size).unwrap();

    // Reopen — should fail with IndexOutOfSync
    let result = PersonalStore::open_or_create(tmp.path());
    assert!(result.is_err());
    let err = result.unwrap_err();
    let user_err = err.downcast_ref::<leet_core::UserFacingError>();
    assert!(matches!(user_err, Some(leet_core::UserFacingError::IndexOutOfSync { .. })));
}
```

---

## CENÁRIO 4 — FSYNC FALHOU

### Problema

`fsync` pode falhar por: disco cheio, sistema de arquivos quebrado, permissão revogada após open, hardware fault. Hoje a falha sobe como `std::io::Error` genérico.

### Solução

Encapsular fsync em helper que detecta o subset de erros relevantes e gera `UserFacingError` específico. Restantes propagam como `Unexpected`.

### Edit em `leet-mcp/src/store.rs`

```rust
fn fsync_or_user_error(file: &std::fs::File, target_path: &Path) -> Result<()> {
    file.sync_all().map_err(|e| {
        match e.kind() {
            std::io::ErrorKind::PermissionDenied => {
                anyhow::Error::new(leet_core::UserFacingError::NoWritePermission {
                    path: target_path.to_path_buf(),
                })
            }
            std::io::ErrorKind::Other if e.raw_os_error() == Some(28) => {
                // ENOSPC — disk full
                anyhow::Error::new(leet_core::UserFacingError::Unexpected {
                    summary: format!("Disk full while writing to {}", target_path.display()),
                    chain: format!("ENOSPC: {}", e),
                })
            }
            _ => anyhow::Error::new(e).context(format!(
                "fsync on {}", target_path.display()
            )),
        }
    })
}
```

Usar essa função em todos os call-sites de `sync_all()` em store.rs e index.rs.

### Teste

Testar fsync failure exige nivel kernel ou mock. Pular teste real, mas adicionar **teste de unidade do mapper**:

```rust
#[test]
fn fsync_permission_denied_maps_to_user_error() {
    let mock_err = std::io::Error::new(std::io::ErrorKind::PermissionDenied, "denied");
    // Pseudocódigo (depende do helper estar exposto):
    // let mapped = map_fsync_error(mock_err, Path::new("/x"));
    // assert!(matches!(mapped, UserFacingError::NoWritePermission { .. }));
}
```

(Ajustar conforme estrutura final do helper.)

---

## CENÁRIO 5 — SEM PERMISSÃO DE ESCRITA

### Problema

Usuário tenta `leet setup` ou `leet_remember` em diretório onde não tem permissão (root-owned, mounted read-only, etc). Hoje propaga `Permission denied` cru.

### Solução

Já está parcialmente coberto pelo cenário 4 (fsync). Adicionalmente, **detectar antes** quando possível: ao abrir `.leet/`, testar permissão com um touch.

### Edit em `leet-mcp/src/store.rs::open_or_create`

```rust
// After ensuring leet_dir exists:
let test_file = leet_dir.join(".write_test");
if std::fs::File::create(&test_file).is_err() {
    return Err(anyhow::Error::new(leet_core::UserFacingError::NoWritePermission {
        path: leet_dir.clone(),
    }));
}
let _ = std::fs::remove_file(&test_file); // best-effort cleanup
```

Esse check é barato (microsegundos) e early-fails com mensagem clara em vez de stack trace longe.

### Teste

```rust
#[test]
#[cfg(unix)]
fn no_write_permission_fails_humanly() {
    use std::os::unix::fs::PermissionsExt;
    let tmp = tempfile::tempdir().unwrap();
    let project = tmp.path().join("readonly");
    std::fs::create_dir_all(&project).unwrap();

    // Make readonly
    let mut perms = std::fs::metadata(&project).unwrap().permissions();
    perms.set_mode(0o555);
    std::fs::set_permissions(&project, perms).unwrap();

    let result = PersonalStore::open_or_create(&project);
    assert!(result.is_err());
    let err = result.unwrap_err();
    let user_err = err.downcast_ref::<leet_core::UserFacingError>();
    // Either NoWritePermission OR error from canonicalize, depending on
    // exactly what fails first. Both are acceptable as long as it's a UserFacingError.
    assert!(user_err.is_some(), "expected UserFacingError, got {:?}", err);

    // Restore permissions for cleanup
    let mut perms = std::fs::metadata(&project).unwrap().permissions();
    perms.set_mode(0o755);
    std::fs::set_permissions(&project, perms).unwrap();
}
```

---

## CENÁRIO 6 — SCHEMA VERSION MISMATCH

### Problema

`store.bin` header tem byte de versão (offset 4). Hoje é hardcoded 0x01. Se v2.0 mudar pra 0x02 e o usuário rodar v1.0 binário num store v2.0, o que acontece? Hoje provavelmente lê garbage.

### Solução

Detectar version byte e falhar humanly se diferir.

### Edit em `leet-mcp/src/store.rs`

```rust
const STORE_VERSION: u8 = 0x01;

// On open, after reading header:
let version_in_file = header[4];
if version_in_file != STORE_VERSION {
    return Err(anyhow::Error::new(leet_core::UserFacingError::StoreVersionMismatch {
        path: store_path.clone(),
        found_version: version_in_file,
        expected_version: STORE_VERSION,
    }));
}
```

Mesma lógica em `index.rs` para `INDEX_VERSION`.

### Teste

```rust
#[test]
fn store_version_mismatch_fails_humanly() {
    let tmp = tempfile::tempdir().unwrap();
    let leet_dir = tmp.path().join(".leet");
    std::fs::create_dir_all(&leet_dir).unwrap();

    // Write a store header with version=99
    let mut header = [0u8; 16];
    header[0..4].copy_from_slice(b"LEET");
    header[4] = 0x99;
    std::fs::write(leet_dir.join("store.bin"), header).unwrap();

    let result = PersonalStore::open_or_create(tmp.path());
    assert!(result.is_err());
    let err = result.unwrap_err();
    let user_err = err.downcast_ref::<leet_core::UserFacingError>();
    assert!(matches!(user_err, Some(leet_core::UserFacingError::StoreVersionMismatch { .. })));
}
```

---

## CENÁRIO 7 — LEET_PROJECT_ROOT INEXISTENTE

### Problema

Usuário define `LEET_PROJECT_ROOT=/path/que/nao/existe` por engano (typo, ou rodou em diretório que foi deletado depois). Hoje é provável que crie a pasta silenciosamente, levando a "store em lugar errado e ninguém percebeu".

### Solução

Já coberto parcialmente pelo cenário 1 (canonicalize falha). Aprofundar: verificar **antes** de tentar abrir.

### Edit em `leet-mcp/src/main.rs` ou onde a env var é lida

```rust
fn resolve_project_root() -> Result<PathBuf> {
    let raw = std::env::var("LEET_PROJECT_ROOT")
        .or_else(|_| std::env::current_dir().map(|p| p.to_string_lossy().into_owned()).map_err(|e| std::env::VarError::NotPresent))
        .unwrap_or_else(|_| ".".to_string());

    let path = PathBuf::from(&raw);
    if !path.exists() {
        return Err(anyhow::Error::new(leet_core::UserFacingError::NotInProject {
            cwd: path,
        }));
    }
    Ok(path)
}
```

(O exato pathway depende de como o main reads env vars hoje. Ajustar.)

### Teste

```rust
#[test]
fn nonexistent_project_root_env_fails() {
    // Indirect: test the helper, not the full main path
    std::env::set_var("LEET_PROJECT_ROOT", "/tmp/leet-definitely-nonexistent-xyz999");
    // ... call resolve_project_root() and assert UserFacingError::NotInProject
    std::env::remove_var("LEET_PROJECT_ROOT");
}
```

---

## ESTRATÉGIA DE EXECUÇÃO

Os 7 cenários têm dependências cruzadas — mexem todos em `store.rs`/`index.rs`. Sugestão de ordem ao Claude Code:

1. **Cenário 6** primeiro (version check): trivial, valida o pipeline `UserFacingError` em uso
2. **Cenário 5** (write permission test no init): early check, falha rápido
3. **Cenário 1** (canonicalize): muda assinatura interna, cascateia
4. **Cenário 2** (truncate tail): adiciona robustez sem quebrar nada
5. **Cenário 3** (index sync): o check em si é trivial; impacta abertura
6. **Cenário 4** (fsync map): helper utility usado em vários lugares
7. **Cenário 7** (env var resolve): main-level, isolado

Cada um com `cargo test --workspace` verde antes de avançar pro próximo.

---

## VERIFICATION

```bash
cargo build --workspace
cargo test --workspace 2>&1 | tail -20
# Esperado: contagem de testes ≥ 247 + 7 novos (= 254+); 0 falhando

# Smoke manual: dois projetos com mesmo basename
mkdir -p /tmp/dir1/myapp /tmp/dir2/myapp
LEET_PROJECT_ROOT=/tmp/dir1/myapp ./target/debug/leet-mcp <<EOF 2>/dev/null > /dev/null
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"in dir1"}}}
EOF
LEET_PROJECT_ROOT=/tmp/dir2/myapp ./target/debug/leet-mcp <<EOF 2>/dev/null > /dev/null
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"in dir2"}}}
EOF

# Verificar que stores são separados
ls -la /tmp/dir1/myapp/.leet/store.bin /tmp/dir2/myapp/.leet/store.bin
# Esperado: ambos com 376 bytes, conteúdo diferente

# Smoke: env var pra dir inexistente
LEET_PROJECT_ROOT=/tmp/nao-existe-xyz ./target/debug/leet-mcp <<EOF 2>&1 | head
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
EOF
# Esperado: erro humano, não panic

# Smoke: corrupted store
echo -n "garbage" > /tmp/test-corrupted/.leet/store.bin
mkdir -p /tmp/test-corrupted/.leet
echo "this is not a valid header" > /tmp/test-corrupted/.leet/store.bin
LEET_PROJECT_ROOT=/tmp/test-corrupted ./target/debug/leet doctor 2>&1 | tail
# Esperado: doctor reporta error claro, sugere rebuild
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt12_U_04 "Edge cases: same-basename, truncated store, index desync, fsync, permissions, version, env var"
task project:1337 +prompt12_U_04 done

git add leet-mcp/src/store.rs leet-mcp/src/index.rs leet-mcp/src/main.rs leet-mcp/src/lib.rs

git commit -m "feat(robustness): handle 7 real-world edge cases gracefully

Each scenario now produces a UserFacingError with actionable suggestion
instead of silent corruption, panic, or anyhow stack trace:

  1. Two projects with same basename: paths now canonicalized; symlinks
     and relative paths resolve to same .leet/.

  2. Store truncated mid-write: open() detects trailing bytes that aren't
     a multiple of 360 and truncates silently with a warn log.

  3. Index desynced from store: detected on open() with explicit error
     and suggestion to run consolidate rebuild-index.

  4. fsync failed: helper maps PermissionDenied → NoWritePermission and
     ENOSPC → human 'Disk full' message. Other kinds propagate normally.

  5. No write permission in .leet/: early write probe at open() catches
     this before any record write; returns NoWritePermission with chmod
     suggestion.

  6. Schema version mismatch: header version byte checked; future-version
     stores fail with StoreVersionMismatch and migration hint.

  7. LEET_PROJECT_ROOT pointing nowhere: detected in env-resolution
     before store open; NotInProject error.

All 7 scenarios have unit tests verifying the error variant. Uses the
UserFacingError type introduced in 12-U-01 — no new error machinery.

Part of Phase 12-U (UX) closing: leet now degrades gracefully under
all realistic failure modes encountered during user operation."
git push origin main
```

---

**END OF PROMPT_12-U-04**
