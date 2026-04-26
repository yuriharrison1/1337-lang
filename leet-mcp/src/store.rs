//! PersonalStore — binary append-only store at `.leet/store.bin`.
//!
//! Format:
//!   file:
//!     [16-byte header][record*N]
//!   header:
//!     magic   (4 bytes) = "LEET"
//!     version (1 byte)  = 0x01
//!     reserved (11 bytes) = zero
//!   record (360 bytes, fixed):
//!     codec_frame (96 bytes) — leet-core's canonical COGON frame
//!     unix_ns     (8 bytes)  — little-endian i64
//!     excerpt     (256 bytes) — UTF-8, zero-padded; truncated if longer
//!
//! Guarantees:
//!   - Append is atomic at the POSIX write() boundary + fsync.
//!   - Reads tolerate trailing partial records (ignored on open).
//!   - Concurrent readers OK; concurrent writers NOT supported
//!     (MCP over stdio is inherently single-writer).

use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use leet_core::codec::{decode_cogon, encode_cogon};
use leet_core::types::Cogon;

const MAGIC: &[u8; 4] = b"LEET";
const VERSION: u8 = 0x01;
const HEADER_SIZE: usize = 16;
const FRAME_SIZE: usize = 96;
const TIMESTAMP_SIZE: usize = 8;
const EXCERPT_SIZE: usize = 256;
const RECORD_SIZE: usize = FRAME_SIZE + TIMESTAMP_SIZE + EXCERPT_SIZE; // 360

#[derive(Debug, Clone)]
pub struct StoreRecord {
    pub cogon: Cogon,
    pub excerpt: String,
    pub unix_ns: i64,
}

pub struct PersonalStore {
    path: PathBuf,
    records: Vec<StoreRecord>,
}

impl PersonalStore {
    /// Open or create the store under `project_root/.leet/`.
    /// Also writes `.leet/.gitignore` on first creation.
    pub fn open_or_create(project_root: &Path) -> Result<Self> {
        let leet_dir = project_root.join(".leet");
        std::fs::create_dir_all(&leet_dir)
            .with_context(|| format!("creating {}", leet_dir.display()))?;

        let gitignore = leet_dir.join(".gitignore");
        if !gitignore.exists() {
            std::fs::write(
                &gitignore,
                "# Auto-created by leet-mcp. Remove this line to commit the store.\nstore.bin\n",
            )?;
        }

        let path = leet_dir.join("store.bin");
        let records = if path.exists() {
            Self::load_all(&path)?
        } else {
            Self::create_empty(&path)?;
            Vec::new()
        };

        tracing::info!(
            "PersonalStore: {} record(s) loaded from {}",
            records.len(),
            path.display()
        );

        Ok(Self { path, records })
    }

    pub fn len(&self) -> usize { self.records.len() }
    pub fn is_empty(&self) -> bool { self.records.is_empty() }
    pub fn records(&self) -> &[StoreRecord] { &self.records }
    pub fn path(&self) -> &Path { &self.path }

    /// Append a record. Persists to disk immediately (write + fsync).
    pub fn append(&mut self, record: StoreRecord) -> Result<()> {
        let mut bytes = [0u8; RECORD_SIZE];
        encode_record(&record, &mut bytes)?;

        let mut f = OpenOptions::new()
            .append(true)
            .open(&self.path)
            .with_context(|| format!("opening {}", self.path.display()))?;
        f.write_all(&bytes).with_context(|| "writing record")?;
        f.sync_all().with_context(|| "fsync after append")?;
        drop(f);

        self.records.push(record);
        Ok(())
    }

    fn create_empty(path: &Path) -> Result<()> {
        let mut f = File::create(path)
            .with_context(|| format!("creating {}", path.display()))?;
        let mut header = [0u8; HEADER_SIZE];
        header[0..4].copy_from_slice(MAGIC);
        header[4] = VERSION;
        f.write_all(&header)?;
        f.sync_all()?;
        Ok(())
    }

    fn load_all(path: &Path) -> Result<Vec<StoreRecord>> {
        let mut f = File::open(path)
            .with_context(|| format!("opening {}", path.display()))?;

        let mut header = [0u8; HEADER_SIZE];
        f.read_exact(&mut header).with_context(|| "reading header")?;

        if &header[0..4] != MAGIC {
            bail!(
                "invalid magic in {} — not a leet store file",
                path.display()
            );
        }
        if header[4] != VERSION {
            bail!(
                "unsupported store version {} (expected {}); \
                 move or delete {} to re-create",
                header[4],
                VERSION,
                path.display()
            );
        }

        let mut body = Vec::new();
        f.read_to_end(&mut body)?;

        let whole = (body.len() / RECORD_SIZE) * RECORD_SIZE;
        if whole != body.len() {
            tracing::warn!(
                "store {} has {} trailing bytes past last complete record; ignoring.",
                path.display(),
                body.len() - whole
            );
        }

        let mut records = Vec::with_capacity(whole / RECORD_SIZE);
        for chunk in body[..whole].chunks_exact(RECORD_SIZE) {
            match decode_record(chunk) {
                Ok(rec) => records.push(rec),
                Err(e) => tracing::warn!("skipping corrupt record: {e}"),
            }
        }
        Ok(records)
    }
}

// ─── record codec ────────────────────────────────────────────────────────────

fn encode_record(rec: &StoreRecord, out: &mut [u8; RECORD_SIZE]) -> Result<()> {
    let frame = encode_cogon(&rec.cogon);
    if frame.len() != FRAME_SIZE {
        bail!("encode_cogon returned {} bytes, expected {}", frame.len(), FRAME_SIZE);
    }
    out[0..FRAME_SIZE].copy_from_slice(&frame);

    out[FRAME_SIZE..FRAME_SIZE + TIMESTAMP_SIZE]
        .copy_from_slice(&rec.unix_ns.to_le_bytes());

    let excerpt_start = FRAME_SIZE + TIMESTAMP_SIZE;
    let excerpt_end = excerpt_start + EXCERPT_SIZE;
    let excerpt_region = &mut out[excerpt_start..excerpt_end];
    excerpt_region.fill(0);

    let mut bytes = rec.excerpt.as_bytes();
    if bytes.len() > EXCERPT_SIZE {
        let mut end = EXCERPT_SIZE;
        while end > 0 && !rec.excerpt.is_char_boundary(end) {
            end -= 1;
        }
        bytes = &rec.excerpt.as_bytes()[..end];
    }
    excerpt_region[..bytes.len()].copy_from_slice(bytes);

    Ok(())
}

fn decode_record(data: &[u8]) -> Result<StoreRecord> {
    if data.len() != RECORD_SIZE {
        bail!("wrong record size: {} (expected {})", data.len(), RECORD_SIZE);
    }

    let cogon = decode_cogon(&data[0..FRAME_SIZE])
        .map_err(|e| anyhow::anyhow!("decode_cogon: {e}"))?;

    let mut ts_bytes = [0u8; 8];
    ts_bytes.copy_from_slice(&data[FRAME_SIZE..FRAME_SIZE + TIMESTAMP_SIZE]);
    let unix_ns = i64::from_le_bytes(ts_bytes);

    let excerpt_start = FRAME_SIZE + TIMESTAMP_SIZE;
    let excerpt_bytes = &data[excerpt_start..excerpt_start + EXCERPT_SIZE];
    let end = excerpt_bytes
        .iter()
        .rposition(|&b| b != 0)
        .map(|i| i + 1)
        .unwrap_or(0);
    let excerpt = String::from_utf8_lossy(&excerpt_bytes[..end]).into_owned();

    Ok(StoreRecord { cogon, excerpt, unix_ns })
}

// ─── tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use leet_core::types::Cogon;
    use uuid::Uuid;

    fn make_cogon(seed: f32) -> Cogon {
        Cogon { id: Uuid::new_v4(), sem: [seed; 32], stamp: 0, raw: None }
    }

    fn make_record(seed: f32, excerpt: &str, unix_ns: i64) -> StoreRecord {
        StoreRecord { cogon: make_cogon(seed), excerpt: excerpt.to_string(), unix_ns }
    }

    #[test]
    fn new_store_starts_empty() {
        let tmp = tempfile::tempdir().unwrap();
        let store = PersonalStore::open_or_create(tmp.path()).unwrap();
        assert_eq!(store.len(), 0);
        assert!(tmp.path().join(".leet/store.bin").exists());
        assert!(tmp.path().join(".leet/.gitignore").exists());
    }

    #[test]
    fn append_persists_across_reopen() {
        let tmp = tempfile::tempdir().unwrap();
        {
            let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
            store.append(make_record(0.6, "first decision", 1_000_000_000)).unwrap();
            store.append(make_record(0.3, "second decision", 2_000_000_000)).unwrap();
            assert_eq!(store.len(), 2);
        }
        let store = PersonalStore::open_or_create(tmp.path()).unwrap();
        assert_eq!(store.len(), 2);
        assert_eq!(store.records()[0].excerpt, "first decision");
        assert_eq!(store.records()[0].unix_ns, 1_000_000_000);
        assert_eq!(store.records()[1].excerpt, "second decision");
    }

    #[test]
    fn long_excerpt_is_truncated() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        store.append(make_record(0.5, &"x".repeat(500), 0)).unwrap();
        let store = PersonalStore::open_or_create(tmp.path()).unwrap();
        assert_eq!(store.records()[0].excerpt.len(), 256);
    }

    #[test]
    fn utf8_multibyte_excerpt_survives_truncation() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        let mixed = "Decisão sobre arquitetura 🚀 ".repeat(20);
        store.append(make_record(0.5, &mixed, 0)).unwrap();
        let store = PersonalStore::open_or_create(tmp.path()).unwrap();
        let _ = store.records()[0].excerpt.as_str(); // must be valid UTF-8
    }

    #[test]
    fn file_size_is_header_plus_records() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        for i in 0..5 {
            store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
        }
        let size = std::fs::metadata(store.path()).unwrap().len();
        assert_eq!(size, (HEADER_SIZE + 5 * RECORD_SIZE) as u64);
    }

    #[test]
    fn trailing_garbage_is_tolerated() {
        let tmp = tempfile::tempdir().unwrap();
        {
            let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
            store.append(make_record(0.5, "good", 1)).unwrap();
        }
        let mut f = OpenOptions::new()
            .append(true)
            .open(tmp.path().join(".leet/store.bin"))
            .unwrap();
        f.write_all(&[0xFFu8; 10]).unwrap();
        drop(f);

        let store = PersonalStore::open_or_create(tmp.path()).unwrap();
        assert_eq!(store.len(), 1);
        assert_eq!(store.records()[0].excerpt, "good");
    }

    #[test]
    fn rejects_file_with_bad_magic() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(tmp.path().join(".leet")).unwrap();
        std::fs::write(tmp.path().join(".leet/store.bin"), b"NOT_LEET_AT_ALL_HEADER").unwrap();
        assert!(PersonalStore::open_or_create(tmp.path()).is_err());
    }

    #[test]
    fn gitignore_content() {
        let tmp = tempfile::tempdir().unwrap();
        PersonalStore::open_or_create(tmp.path()).unwrap();
        let content = std::fs::read_to_string(tmp.path().join(".leet/.gitignore")).unwrap();
        assert!(content.contains("store.bin"));
    }

    #[test]
    fn gitignore_not_overwritten_if_user_edited_it() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(tmp.path().join(".leet")).unwrap();
        std::fs::write(tmp.path().join(".leet/.gitignore"), "# user's custom\n").unwrap();
        PersonalStore::open_or_create(tmp.path()).unwrap();
        let content = std::fs::read_to_string(tmp.path().join(".leet/.gitignore")).unwrap();
        assert_eq!(content, "# user's custom\n");
    }

    #[test]
    fn cogon_sem_roundtrips() {
        let tmp = tempfile::tempdir().unwrap();
        let original_sem = {
            let mut s = [0.5; 32];
            s[0] = 0.9;
            s[29] = 0.7;
            s
        };
        let rec = StoreRecord {
            cogon: Cogon { id: Uuid::new_v4(), sem: original_sem, stamp: 0, raw: None },
            excerpt: "test".to_string(),
            unix_ns: 42,
        };
        {
            let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
            store.append(rec).unwrap();
        }
        let store = PersonalStore::open_or_create(tmp.path()).unwrap();
        let recovered = &store.records()[0].cogon;
        for i in 0..32 {
            assert!(
                (recovered.sem[i] - original_sem[i]).abs() < 0.01,
                "sem[{i}] mismatch"
            );
        }
    }
}
