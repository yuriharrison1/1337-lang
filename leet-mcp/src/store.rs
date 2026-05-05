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
//! Alongside store.bin, `.leet/index.bin` is maintained as a sidecar that
//! tracks the consolidation level and flags for each record. See index.rs.

use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use leet_core::codec::{decode_cogon, encode_cogon};
use leet_core::types::Cogon;
use uuid::Uuid;

use crate::index::{Index, IndexEntry};

const MAGIC: &[u8; 4] = b"LEET";
const VERSION: u8 = 0x01;
const HEADER_SIZE: usize = 16;
const FRAME_SIZE: usize = 96;
const TIMESTAMP_SIZE: usize = 8;
const EXCERPT_SIZE: usize = 256;
pub const RECORD_SIZE: usize = FRAME_SIZE + TIMESTAMP_SIZE + EXCERPT_SIZE; // 360

/// Threshold for auto-consolidation: when 7 live records exist at a level,
/// merge the oldest 7 into one level+1 record.
pub const CONSOLIDATE_THRESHOLD: usize = 7;

/// Block-special axis indices (must match leet-core canonical ordering).
const D4_STABILITY: usize = 11;
const G1_MASS: usize = 16;
const G7_K_INTERACTION: usize = 22;
const P6_CONFIDENCE: usize = 29;

#[derive(Debug, Clone)]
pub struct StoreRecord {
    pub cogon: Cogon,
    pub excerpt: String,
    pub unix_ns: i64,
}

pub struct PersonalStore {
    path: PathBuf,
    records: Vec<StoreRecord>,
    pub index: Index,
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
                "# Auto-created by leet-mcp. Remove this line to commit the store.\n\
                 store.bin\nindex.bin\n",
            )?;
        }

        let path = leet_dir.join("store.bin");
        let records = if path.exists() {
            Self::load_all(&path)?
        } else {
            Self::create_empty(&path)?;
            Vec::new()
        };

        let index = Index::open_or_create(&leet_dir, records.len())?;

        tracing::info!(
            "PersonalStore: {} record(s), index loaded ({} entries)",
            records.len(),
            index.entries.len()
        );

        Ok(Self { path, records, index })
    }

    pub fn len(&self) -> usize { self.records.len() }
    pub fn is_empty(&self) -> bool { self.records.is_empty() }
    pub fn records(&self) -> &[StoreRecord] { &self.records }
    pub fn path(&self) -> &Path { &self.path }

    /// Append a record at level 0, then auto-consolidate if threshold reached.
    pub fn append(&mut self, record: StoreRecord) -> Result<()> {
        self.append_at_level(record, 0, IndexEntry::default())?;
        self.maybe_consolidate(0)?;
        let mut level = 1u8;
        while self.maybe_consolidate(level)? {
            level += 1;
            if level > 10 {
                break; // safety: 7^10 is far past anything realistic
            }
        }
        self.index.flush()?;
        Ok(())
    }

    /// Append at a specific level with provided index metadata. Internal use.
    fn append_at_level(
        &mut self,
        record: StoreRecord,
        level: u8,
        meta: IndexEntry,
    ) -> Result<()> {
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
        let mut entry = meta;
        entry.level = level;
        self.index.push(entry);
        Ok(())
    }

    /// If `level` has ≥ CONSOLIDATE_THRESHOLD live records, consolidate the
    /// oldest batch into one level+1 record. Returns true if consolidation happened.
    fn maybe_consolidate(&mut self, level: u8) -> Result<bool> {
        let live = self.index.live_indices_at_level(level);
        if live.len() < CONSOLIDATE_THRESHOLD {
            return Ok(false);
        }

        let to_merge: Vec<usize> = live.into_iter().take(CONSOLIDATE_THRESHOLD).collect();
        let merged = blend_n_records(
            &to_merge.iter().map(|&i| &self.records[i]).collect::<Vec<_>>(),
            level,
        );

        let header_size = HEADER_SIZE as u64;
        let first_offset = header_size + (to_merge[0] as u64) * (RECORD_SIZE as u64);
        let last_offset =
            header_size + (*to_merge.last().unwrap() as u64) * (RECORD_SIZE as u64);

        let entry = IndexEntry {
            level: level + 1,
            flags: 0,
            consolidates_from_first: first_offset,
            consolidates_from_last: last_offset,
        };
        self.append_at_level(merged, level + 1, entry)?;
        self.index.mark_consolidated(&to_merge);

        tracing::info!(
            "consolidated {} records at level {level} → 1 record at level {}",
            to_merge.len(),
            level + 1
        );
        Ok(true)
    }

    /// Public wrapper for `force` CLI: consolidates at `level` if at least `min`
    /// live records exist there. Returns true if consolidation happened.
    pub fn force_consolidate_at(
        &mut self,
        level: u8,
        min: usize,
        cap: usize,
    ) -> Result<bool> {
        let live = self.index.live_indices_at_level(level);
        if live.len() < min {
            return Ok(false);
        }

        let take = live.len().min(cap);
        let to_merge: Vec<usize> = live.into_iter().take(take).collect();

        let merged = blend_n_records(
            &to_merge.iter().map(|&i| &self.records[i]).collect::<Vec<_>>(),
            level,
        );

        let header_size = HEADER_SIZE as u64;
        let first_offset = header_size + (to_merge[0] as u64) * (RECORD_SIZE as u64);
        let last_offset =
            header_size + (*to_merge.last().unwrap() as u64) * (RECORD_SIZE as u64);

        let entry = IndexEntry {
            level: level + 1,
            flags: 0,
            consolidates_from_first: first_offset,
            consolidates_from_last: last_offset,
        };
        self.append_at_level(merged, level + 1, entry)?;
        self.index.mark_consolidated(&to_merge);
        self.index.flush()?;

        tracing::info!(
            "force_consolidate_at: merged {} records at level {level} → level {}",
            to_merge.len(),
            level + 1
        );
        Ok(true)
    }

    /// Canonical centroid (G1-weighted) of all live records with unix_ns ≤ cursor_ns.
    /// If cursor_ns is 0 or no records match, returns the boot vector.
    pub fn centroid_up_to(&self, cursor_ns: i64) -> [f32; 32] {
        let eligible: Vec<&StoreRecord> = self
            .records
            .iter()
            .enumerate()
            .filter(|(i, _)| !self.index.entries[*i].is_consolidated())
            .map(|(_, r)| r)
            .filter(|r| cursor_ns == 0 || r.unix_ns <= cursor_ns)
            .collect();

        if eligible.is_empty() {
            return leet_core::axes::boot_vector();
        }

        let total_mass: f32 = eligible.iter().map(|r| r.cogon.sem[G1_MASS]).sum();
        let mut sem = [0.0_f32; 32];

        if total_mass > f32::EPSILON {
            for r in &eligible {
                let w = r.cogon.sem[G1_MASS] / total_mass;
                for k in 0..32 {
                    sem[k] += w * r.cogon.sem[k];
                }
            }
        } else {
            let inv_n = 1.0 / eligible.len() as f32;
            for r in &eligible {
                for k in 0..32 {
                    sem[k] += r.cogon.sem[k] * inv_n;
                }
            }
        }

        for v in sem.iter_mut() {
            *v = v.clamp(0.0, 1.0);
        }
        sem
    }

    /// Live records added strictly after `cursor_ns`. Oldest to newest.
    pub fn live_records_after(&self, cursor_ns: i64) -> Vec<usize> {
        self.records
            .iter()
            .enumerate()
            .filter(|(i, r)| {
                !self.index.entries[*i].is_consolidated() && r.unix_ns > cursor_ns
            })
            .map(|(i, _)| i)
            .collect()
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

// ─── Hybrid BLEND_N: G1-weighted centroid + per-block rules ──────────────────

fn blend_n_records(records: &[&StoreRecord], source_level: u8) -> StoreRecord {
    let n = records.len();
    debug_assert!(n > 0);

    let total_mass: f32 = records.iter().map(|r| r.cogon.sem[G1_MASS]).sum();
    let mut sem = [0.0_f32; 32];

    if total_mass > f32::EPSILON {
        for r in records {
            let w = r.cogon.sem[G1_MASS] / total_mass;
            for k in 0..32 {
                sem[k] += w * r.cogon.sem[k];
            }
        }
    } else {
        let inv_n = 1.0 / n as f32;
        for r in records {
            for k in 0..32 {
                sem[k] += r.cogon.sem[k] * inv_n;
            }
        }
    }

    // Per-block overrides.
    sem[D4_STABILITY] = records
        .iter()
        .map(|r| r.cogon.sem[D4_STABILITY])
        .fold(f32::INFINITY, f32::min);

    let mass_sum: f32 = records.iter().map(|r| r.cogon.sem[G1_MASS]).sum();
    sem[G1_MASS] = mass_sum.clamp(0.0, 1.0);

    sem[G7_K_INTERACTION] = records
        .iter()
        .map(|r| r.cogon.sem[G7_K_INTERACTION])
        .fold(f32::NEG_INFINITY, f32::max);

    sem[P6_CONFIDENCE] = records
        .iter()
        .map(|r| r.cogon.sem[P6_CONFIDENCE])
        .fold(f32::INFINITY, f32::min);

    for v in sem.iter_mut() {
        *v = v.clamp(0.0, 1.0);
    }

    let stamp = records.iter().map(|r| r.cogon.stamp).max().unwrap_or(0);
    let unix_ns = records.iter().map(|r| r.unix_ns).max().unwrap_or(0);

    let prefix = format!("[L{}×{}] ", source_level + 1, n);
    let parts: Vec<&str> = records.iter().map(|r| r.excerpt.as_str()).collect();
    let joined = format!("{prefix}{}", parts.join(" · "));
    let excerpt = truncate_utf8(&joined, 256);

    StoreRecord {
        cogon: Cogon { id: Uuid::new_v4(), sem, stamp, raw: None },
        excerpt,
        unix_ns,
    }
}

fn truncate_utf8(s: &str, max_bytes: usize) -> String {
    if s.as_bytes().len() <= max_bytes {
        return s.to_string();
    }
    let mut end = max_bytes.saturating_sub(3);
    while end > 0 && !s.is_char_boundary(end) {
        end -= 1;
    }
    let mut out = s[..end].to_string();
    out.push('…');
    out
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

    // ─── existing tests ───────────────────────────────────────────────────────

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
        // 5 records < 7 → no consolidation, store.bin has exactly 5 records
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
        assert!(content.contains("index.bin"));
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

    // ─── consolidation tests ──────────────────────────────────────────────────

    #[test]
    fn append_below_threshold_does_not_consolidate() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        for i in 0..6 {
            store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
        }
        assert_eq!(store.len(), 6);
        for e in &store.index.entries {
            assert_eq!(e.level, 0);
            assert!(!e.is_consolidated());
        }
    }

    #[test]
    fn append_at_threshold_triggers_one_consolidation() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        for i in 0..7 {
            store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
        }
        // 7 raw + 1 consolidated = 8 records total.
        assert_eq!(store.len(), 8);
        for i in 0..7 {
            assert_eq!(store.index.entries[i].level, 0);
            assert!(store.index.entries[i].is_consolidated());
        }
        assert_eq!(store.index.entries[7].level, 1);
        assert!(!store.index.entries[7].is_consolidated());
    }

    #[test]
    fn consolidation_cascades_at_higher_levels() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        // 7^2 = 49 raw records → 7 level-1 records → 1 level-2 record.
        for i in 0..49 {
            store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
        }
        // 49 raw + 7 level-1 + 1 level-2 = 57
        assert_eq!(store.len(), 57);
        let last = store.index.entries.last().unwrap();
        assert_eq!(last.level, 2);
    }

    #[test]
    fn consolidation_preserves_g1_accumulation() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        for i in 0..7 {
            let mut rec = make_record(0.5, &format!("rec{i}"), i);
            rec.cogon.sem[G1_MASS] = 0.1;
            store.append(rec).unwrap();
        }
        let consolidated = &store.records()[7];
        // 7 * 0.1 = 0.7, no saturation
        assert!((consolidated.cogon.sem[G1_MASS] - 0.7).abs() < 0.05);
    }

    #[test]
    fn consolidation_p6_takes_min() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        let p6_values = [0.9_f32, 0.8, 0.3, 0.95, 0.7, 0.6, 0.85];
        for (i, &p6) in p6_values.iter().enumerate() {
            let mut rec = make_record(0.5, &format!("rec{i}"), i as i64);
            rec.cogon.sem[P6_CONFIDENCE] = p6;
            store.append(rec).unwrap();
        }
        let consolidated = &store.records()[7];
        assert!((consolidated.cogon.sem[P6_CONFIDENCE] - 0.3).abs() < 0.01);
    }

    #[test]
    fn consolidation_excerpt_starts_with_level_prefix() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        for i in 0..7 {
            store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
        }
        let consolidated = &store.records()[7];
        assert!(consolidated.excerpt.starts_with("[L1×7]"));
    }

    #[test]
    fn index_persists_across_reopen() {
        let tmp = tempfile::tempdir().unwrap();
        {
            let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
            for i in 0..7 {
                store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
            }
        }
        let store = PersonalStore::open_or_create(tmp.path()).unwrap();
        assert_eq!(store.len(), 8);
        assert_eq!(store.index.entries[7].level, 1);
        for i in 0..7 {
            assert!(store.index.entries[i].is_consolidated());
        }
    }

    #[test]
    fn missing_index_is_rebuilt_lossy_on_reopen() {
        let tmp = tempfile::tempdir().unwrap();
        {
            let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
            for i in 0..7 {
                store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
            }
        }
        std::fs::remove_file(tmp.path().join(".leet/index.bin")).unwrap();

        let store = PersonalStore::open_or_create(tmp.path()).unwrap();
        assert_eq!(store.len(), 8);
        // Lossy rebuild: all entries default to level 0, none consolidated.
        for e in &store.index.entries {
            assert_eq!(e.level, 0);
            assert!(!e.is_consolidated());
        }
    }
}
