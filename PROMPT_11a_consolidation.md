# PROMPT 11a — HIERARCHICAL CONSOLIDATION (auto-trigger via BLEND_N + index.bin)

Add a sidecar metadata file `.leet/index.bin` that tracks per-record `level` plus a `last_recall_at` cursor, and implement automatic consolidation: when 7 COGONs accumulate at the same level, BLEND them (hybrid: G1-weighted centroid + per-block rules) into one level+1 COGON appended to the same store.

**PRE-REQUISITES**: PROMPTs 10a–e landed. `cargo test --workspace` green. `.leet/store.bin` works end-to-end.

**SCOPE**: 3 files in `leet-mcp/`: new `index.rs`, modified `store.rs` (consolidation hooks on append), modified `tools.rs` (recall reads index). No CLI changes here — that's PROMPT_11c.

**Taskwarrior**: `+prompt11a`.

---

## WHY

`leet_recall` today returns N raw COGONs verbatim. Each is ~800 tokens of NL when reconstructed. After 30 sessions, the store has 30 records — recalling them all wastes context.

Hierarchical consolidation turns this into a **memory pyramid**:

```
level 0: ●●●●●●●  ●●●●●●●  ●●●●●●●  ●●●●●●●  ●●●●●●●           (raw, 7 → 1 each)
                ↘     ↘      ↘     ↘     ↘
level 1:        ▲     ▲      ▲     ▲     ▲                       (consolidated)
                  ↘    ↘     ↘   ↙   ↙
level 2:            ▲▲▲▲▲▲▲▲▲                                    (super-consolidated)
                              ↘
level 3:                       ◆                                  (eventually)
```

Recall becomes "send the 1 level-2 entry + the 4 level-1 entries created since + the 3 raw level-0 entries since the last consolidation." Total stays bounded as the project grows.

**Today's deliverable** (this prompt): the consolidation engine and the index file. Recall changes happen in PROMPT_11b.

---

## ARCHITECTURE

### File layout after this prompt

```
.leet/
  ├── store.bin       ← unchanged 16-byte header + 360-byte records, append-only
  ├── index.bin       ← NEW sidecar: per-record metadata + cursors
  └── .gitignore
```

### `index.bin` format

Fixed-size header + array of fixed-size entries, mirroring store.bin's discipline:

```
HEADER (32 bytes):
  bytes 0..4    "LIDX"               magic
  bytes 4..5    0x01                 version
  bytes 5..8    reserved (zero)
  bytes 8..16   last_recall_at: i64  unix_ns of last leet_recall call
  bytes 16..24  record_count: u64    cached count (reconstructible from store.bin)
  bytes 24..32  reserved (zero)

ENTRY (24 bytes per store.bin record):
  bytes 0..1    level: u8            0 = raw, 1 = consolidated, 2 = super, ...
  bytes 1..2    flags: u8            bit 0 = consolidated_into_higher (skip in recall)
  bytes 2..8    reserved (zero)
  bytes 8..16   consolidates_from_first_offset: u64  byte offset in store.bin
  bytes 16..24  consolidates_from_last_offset:  u64  byte offset in store.bin
                                     (zero if level=0)
```

**Total**: 32-byte header + N * 24-byte entries. For 1000 records = 24KB. Tiny.

**Invariants**:
- `index.bin` always has `record_count` entries matching the number of records in `store.bin`.
- If absent (deleted by user), is rebuilt from `store.bin` on open: every record gets `level=0, flags=0`. Lossy but recoverable — old levels would be inferred from heuristics, but we don't bother in v1.
- Append-only on `store.bin` ⇒ append-only on `index.bin`. Same crash-safety story (write + fsync).

### Consolidation trigger

When `append()` is called:
1. Append the raw record at level 0 (as before).
2. Count how many **non-consolidated, non-flagged** records exist at level 0.
3. If that count ≥ 7, take exactly the **oldest 7**, consolidate them into one level-1 record, append it to store.bin (and to index.bin with `level=1`), and mark the 7 sources with `flags |= 0b0000_0001` ("consolidated into higher").
4. Repeat at level 1: if 7 non-flagged level-1 records exist, consolidate to level 2. Cascade up.

Consolidation is bounded — for N=7 the depth is `log_7(record_count)`, max realistic depth is 4 (which would be 7^4 = 2401 raw records).

### Hybrid BLEND_N (G1-weighted centroid + per-block rules)

For consolidating N COGONs `cs[0..N]`:

```
total_mass = Σ cs[i].sem[16]              // G1_MASS
if total_mass > 0:
    centroid[k] = Σ (cs[i].sem[16] / total_mass) * cs[i].sem[k]
else:
    centroid[k] = mean(cs[i].sem[k])      // uniform fallback

# Apply per-block rules to specific indices, overriding the centroid:
result[k] = match k:
  D4_STABILITY (11)    → min(cs[i].sem[11])    # conservative
  G1_MASS (16)         → clamp(Σ cs[i].sem[16], 0.0, 1.0)  # accumulate (saturates)
  G7_K_INTERACTION (22) → max(cs[i].sem[22])    # higher gain wins
  P6_CONFIDENCE (29)   → min(cs[i].sem[29])    # conservative
  _                     → centroid[k]

result = clamp_all(result, 0.0, 1.0)       # R22
```

This generalizes BLEND from 2 → N COGONs, ordered-independent for the centroid axes, and respects the same special-case rules.

The consolidated record gets:
- `id`: new Uuid::new_v4()
- `sem`: result above
- `stamp`: most-recent stamp among the N
- `unix_ns`: most-recent unix_ns among the N
- `excerpt`: synthesized — concatenation of the 7 source excerpts, prefixed with `"[L1×7] "`, truncated to 256 bytes char-safe

---

## FILE 1 — `leet-mcp/src/index.rs` (new)

```rust
//! Sidecar index file for `.leet/store.bin`. Tracks per-record level + cursors.
//! Append-only and crash-safe in the same style as the store itself.

use std::fs::{File, OpenOptions};
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};

const MAGIC: &[u8; 4] = b"LIDX";
const VERSION: u8 = 0x01;
pub const HEADER_SIZE: usize = 32;
pub const ENTRY_SIZE: usize = 24;

/// One entry in index.bin — one per record in store.bin.
#[derive(Debug, Clone, Copy, Default)]
pub struct IndexEntry {
    pub level: u8,
    pub flags: u8,
    pub consolidates_from_first: u64, // byte offset in store.bin (0 if level==0)
    pub consolidates_from_last: u64,
}

impl IndexEntry {
    /// Bit 0 set ⇒ this record was consolidated into a higher-level record;
    /// recall must skip it.
    pub const FLAG_CONSOLIDATED: u8 = 0b0000_0001;

    pub fn is_consolidated(&self) -> bool {
        self.flags & Self::FLAG_CONSOLIDATED != 0
    }
}

/// In-memory mirror of the index file.
pub struct Index {
    path: PathBuf,
    pub last_recall_at: i64,
    pub entries: Vec<IndexEntry>,
}

impl Index {
    /// Open or create `<leet_dir>/index.bin`. If absent, creates a fresh one
    /// with `entries.len() == store_record_count` (all level 0).
    pub fn open_or_create(leet_dir: &Path, store_record_count: usize) -> Result<Self> {
        let path = leet_dir.join("index.bin");

        if !path.exists() {
            return Self::create_fresh(&path, store_record_count);
        }

        // Load existing.
        let mut f = File::open(&path)?;
        let mut header = [0u8; HEADER_SIZE];
        f.read_exact(&mut header)
            .with_context(|| format!("reading {} header", path.display()))?;

        if &header[0..4] != MAGIC {
            bail!("invalid magic in {} — not a leet index", path.display());
        }
        if header[4] != VERSION {
            bail!("unsupported index version {} in {}", header[4], path.display());
        }

        let last_recall_at = i64::from_le_bytes(header[8..16].try_into().unwrap());
        let recorded_count = u64::from_le_bytes(header[16..24].try_into().unwrap()) as usize;

        let mut body = Vec::new();
        f.read_to_end(&mut body)?;
        let n = body.len() / ENTRY_SIZE;

        if n != recorded_count || n != store_record_count {
            // Mismatch: index drifted from store. Rebuild conservatively.
            tracing::warn!(
                "index.bin out of sync (index has {n} entries, header says {recorded_count}, \
                 store has {store_record_count}); rebuilding fresh.",
            );
            return Self::create_fresh(&path, store_record_count);
        }

        let mut entries = Vec::with_capacity(n);
        for chunk in body.chunks_exact(ENTRY_SIZE) {
            entries.push(decode_entry(chunk));
        }

        Ok(Self { path, last_recall_at, entries })
    }

    fn create_fresh(path: &Path, store_record_count: usize) -> Result<Self> {
        let entries = vec![IndexEntry::default(); store_record_count];
        let me = Self {
            path: path.to_path_buf(),
            last_recall_at: 0,
            entries,
        };
        me.flush()?;
        Ok(me)
    }

    /// Persist the entire index to disk atomically (write tempfile + rename + fsync).
    pub fn flush(&self) -> Result<()> {
        let tmp = self.path.with_extension("bin.tmp");
        let mut f = File::create(&tmp)?;

        let mut header = [0u8; HEADER_SIZE];
        header[0..4].copy_from_slice(MAGIC);
        header[4] = VERSION;
        header[8..16].copy_from_slice(&self.last_recall_at.to_le_bytes());
        header[16..24].copy_from_slice(&(self.entries.len() as u64).to_le_bytes());
        f.write_all(&header)?;

        let mut buf = [0u8; ENTRY_SIZE];
        for e in &self.entries {
            encode_entry(e, &mut buf);
            f.write_all(&buf)?;
        }
        f.sync_all()?;
        drop(f);

        std::fs::rename(&tmp, &self.path)?;
        Ok(())
    }

    /// Append one new entry (corresponding to a freshly-appended store record).
    pub fn push(&mut self, e: IndexEntry) {
        self.entries.push(e);
    }

    /// Mark records as consolidated into a higher level.
    pub fn mark_consolidated(&mut self, store_indices: &[usize]) {
        for &i in store_indices {
            if let Some(e) = self.entries.get_mut(i) {
                e.flags |= IndexEntry::FLAG_CONSOLIDATED;
            }
        }
    }

    /// Update last_recall_at cursor.
    pub fn touch_recall(&mut self, unix_ns: i64) {
        self.last_recall_at = unix_ns;
    }

    /// Indices (in store order) where the entry is at `level` and not consolidated.
    pub fn live_indices_at_level(&self, level: u8) -> Vec<usize> {
        self.entries
            .iter()
            .enumerate()
            .filter(|(_, e)| e.level == level && !e.is_consolidated())
            .map(|(i, _)| i)
            .collect()
    }
}

fn encode_entry(e: &IndexEntry, out: &mut [u8; ENTRY_SIZE]) {
    out.fill(0);
    out[0] = e.level;
    out[1] = e.flags;
    // bytes 2..8 reserved (zero)
    out[8..16].copy_from_slice(&e.consolidates_from_first.to_le_bytes());
    out[16..24].copy_from_slice(&e.consolidates_from_last.to_le_bytes());
}

fn decode_entry(data: &[u8]) -> IndexEntry {
    IndexEntry {
        level: data[0],
        flags: data[1],
        consolidates_from_first: u64::from_le_bytes(data[8..16].try_into().unwrap()),
        consolidates_from_last: u64::from_le_bytes(data[16..24].try_into().unwrap()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fresh_index_has_zero_entries_for_empty_store() {
        let tmp = tempfile::tempdir().unwrap();
        let idx = Index::open_or_create(tmp.path(), 0).unwrap();
        assert_eq!(idx.entries.len(), 0);
        assert_eq!(idx.last_recall_at, 0);
    }

    #[test]
    fn fresh_index_creates_default_entries_for_existing_store() {
        let tmp = tempfile::tempdir().unwrap();
        let idx = Index::open_or_create(tmp.path(), 5).unwrap();
        assert_eq!(idx.entries.len(), 5);
        for e in &idx.entries {
            assert_eq!(e.level, 0);
            assert_eq!(e.flags, 0);
        }
    }

    #[test]
    fn flush_then_reload_roundtrip() {
        let tmp = tempfile::tempdir().unwrap();
        {
            let mut idx = Index::open_or_create(tmp.path(), 3).unwrap();
            idx.entries[0].level = 1;
            idx.entries[1].flags = IndexEntry::FLAG_CONSOLIDATED;
            idx.entries[2].consolidates_from_first = 42;
            idx.entries[2].consolidates_from_last = 99;
            idx.last_recall_at = 1_700_000_000_000_000_000;
            idx.flush().unwrap();
        }
        let idx = Index::open_or_create(tmp.path(), 3).unwrap();
        assert_eq!(idx.entries[0].level, 1);
        assert!(idx.entries[1].is_consolidated());
        assert_eq!(idx.entries[2].consolidates_from_first, 42);
        assert_eq!(idx.entries[2].consolidates_from_last, 99);
        assert_eq!(idx.last_recall_at, 1_700_000_000_000_000_000);
    }

    #[test]
    fn mismatch_triggers_fresh_rebuild() {
        let tmp = tempfile::tempdir().unwrap();
        {
            let mut idx = Index::open_or_create(tmp.path(), 5).unwrap();
            idx.entries[0].level = 2;
            idx.flush().unwrap();
        }
        // Now reopen claiming 8 records — mismatch.
        let idx = Index::open_or_create(tmp.path(), 8).unwrap();
        assert_eq!(idx.entries.len(), 8);
        // Rebuild was fresh — old level=2 is gone.
        assert_eq!(idx.entries[0].level, 0);
    }

    #[test]
    fn live_indices_at_level_filters_consolidated() {
        let tmp = tempfile::tempdir().unwrap();
        let mut idx = Index::open_or_create(tmp.path(), 5).unwrap();
        idx.entries[0].level = 0;
        idx.entries[1].level = 0;
        idx.entries[1].flags = IndexEntry::FLAG_CONSOLIDATED;
        idx.entries[2].level = 0;
        idx.entries[3].level = 1;
        idx.entries[4].level = 0;

        let live_l0 = idx.live_indices_at_level(0);
        assert_eq!(live_l0, vec![0, 2, 4]);
        let live_l1 = idx.live_indices_at_level(1);
        assert_eq!(live_l1, vec![3]);
    }

    #[test]
    fn rejects_bad_magic() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(tmp.path().join("index.bin"), b"NOPE_NOT_LIDX_AT_ALL_HEADERX").unwrap();
        assert!(Index::open_or_create(tmp.path(), 0).is_err());
    }
}
```

---

## FILE 2 — `leet-mcp/src/store.rs` (modify — add consolidation logic)

Replace the current `append` and `open_or_create` with the augmented versions below. Keep `StoreRecord` and the codec helpers (`encode_record`, `decode_record`) untouched.

```rust
// Add at top of file:
use crate::index::{Index, IndexEntry};

/// Threshold for auto-consolidation: when 7 live records exist at a level,
/// merge the oldest 7 into one level+1 record.
const CONSOLIDATE_THRESHOLD: usize = 7;

/// Block-special axis indices (must match leet-core::operators).
const D4_STABILITY: usize = 11;
const G1_MASS: usize = 16;
const G7_K_INTERACTION: usize = 22;
const P6_CONFIDENCE: usize = 29;
```

Then change `PersonalStore`:

```rust
pub struct PersonalStore {
    path: PathBuf,
    records: Vec<StoreRecord>,
    pub index: Index,                         // NEW
}

impl PersonalStore {
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

    /// Append a record at level 0, then auto-consolidate if threshold reached.
    pub fn append(&mut self, record: StoreRecord) -> Result<()> {
        self.append_at_level(record, 0, IndexEntry::default())?;
        self.maybe_consolidate(0)?;
        // Cascade: each consolidation may bump up a level.
        let mut level = 1u8;
        while self.maybe_consolidate(level)? {
            level += 1;
            if level > 10 {
                break; // safety: 7^10 = ~282M, far past anything realistic
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
        f.write_all(&bytes)?;
        f.sync_all()?;
        drop(f);

        self.records.push(record);
        let mut entry = meta;
        entry.level = level;
        self.index.push(entry);
        Ok(())
    }

    /// If `level` has ≥ 7 live records, consolidate the oldest 7 into level+1.
    /// Returns true if a consolidation happened.
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

        // Compute byte offsets for the index entry.
        let header_size = 16u64;
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

    // Existing methods (len, is_empty, records, path, create_empty, load_all,
    // encode_record, decode_record) stay the same.
}

// ─── Hybrid BLEND_N: G1-weighted centroid + per-block rules ──────────────────

fn blend_n_records(records: &[&StoreRecord], source_level: u8) -> StoreRecord {
    use leet_core::types::Cogon;
    use uuid::Uuid;

    let n = records.len();
    debug_assert!(n > 0);

    // Centroid (G1-weighted, with uniform fallback when total mass = 0).
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

    // Per-block rules override centroid for the four special axes.
    sem[D4_STABILITY] = records
        .iter()
        .map(|r| r.cogon.sem[D4_STABILITY])
        .fold(f32::INFINITY, f32::min); // min, conservative

    let mass_sum: f32 = records.iter().map(|r| r.cogon.sem[G1_MASS]).sum();
    sem[G1_MASS] = mass_sum.clamp(0.0, 1.0); // accumulate, saturating

    sem[G7_K_INTERACTION] = records
        .iter()
        .map(|r| r.cogon.sem[G7_K_INTERACTION])
        .fold(f32::NEG_INFINITY, f32::max); // max, higher gain wins

    sem[P6_CONFIDENCE] = records
        .iter()
        .map(|r| r.cogon.sem[P6_CONFIDENCE])
        .fold(f32::INFINITY, f32::min); // min, conservative

    // R22: clamp every axis.
    for v in sem.iter_mut() {
        *v = v.clamp(0.0, 1.0);
    }

    // Derived metadata.
    let stamp = records.iter().map(|r| r.cogon.stamp).max().unwrap_or(0);
    let unix_ns = records.iter().map(|r| r.unix_ns).max().unwrap_or(0);

    let prefix = format!("[L{}×{}] ", source_level + 1, n);
    let parts: Vec<&str> = records.iter().map(|r| r.excerpt.as_str()).collect();
    let joined = format!("{prefix}{}", parts.join(" · "));
    let excerpt = truncate_utf8(&joined, 256);

    StoreRecord {
        cogon: Cogon {
            id: Uuid::new_v4(),
            sem,
            stamp,
            raw: None,
        },
        excerpt,
        unix_ns,
    }
}

fn truncate_utf8(s: &str, max_bytes: usize) -> String {
    if s.as_bytes().len() <= max_bytes {
        return s.to_string();
    }
    let mut end = max_bytes.saturating_sub(3); // room for "…"
    while end > 0 && !s.is_char_boundary(end) {
        end -= 1;
    }
    let mut out = s[..end].to_string();
    out.push('…');
    out
}
```

Add module declaration at top of `lib.rs`-equivalent (probably `main.rs` since this is a binary crate):

```rust
mod index;
```

If `index` already declared, skip.

### Tests to add to the `tests` module of `store.rs`

```rust
#[test]
fn append_below_threshold_does_not_consolidate() {
    let tmp = tempfile::tempdir().unwrap();
    let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
    for i in 0..6 {
        store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
    }
    assert_eq!(store.len(), 6);
    // All level 0, none consolidated.
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
    // First 7 marked consolidated, last one is the level-1 result.
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
    // 7^2 = 49 raw records → 7 level-1 records → 1 level-2 record + the leftovers.
    for i in 0..49 {
        store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
    }
    // Total records on disk: 49 raw + 7 level-1 + 1 level-2 = 57
    assert_eq!(store.len(), 57);
    // The very last record must be level 2.
    let last = store.index.entries.last().unwrap();
    assert_eq!(last.level, 2);
}

#[test]
fn consolidation_preserves_g1_accumulation() {
    let tmp = tempfile::tempdir().unwrap();
    let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
    // Each raw record has G1=0.1; consolidated should saturate near 0.7 (clamped to 1.0 if more).
    for i in 0..7 {
        let mut rec = make_record(0.5, &format!("rec{i}"), i);
        rec.cogon.sem[G1_MASS] = 0.1;
        store.append(rec).unwrap();
    }
    let consolidated = &store.records()[7];
    // 7 * 0.1 = 0.7, no saturation yet
    assert!((consolidated.cogon.sem[G1_MASS] - 0.7).abs() < 0.05);
}

#[test]
fn consolidation_p6_takes_min() {
    let tmp = tempfile::tempdir().unwrap();
    let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
    let p6_values = [0.9, 0.8, 0.3, 0.95, 0.7, 0.6, 0.85];
    for (i, &p6) in p6_values.iter().enumerate() {
        let mut rec = make_record(0.5, &format!("rec{i}"), i as i64);
        rec.cogon.sem[P6_CONFIDENCE] = p6;
        store.append(rec).unwrap();
    }
    let consolidated = &store.records()[7];
    // P6 takes min → 0.3
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
    // Delete index.bin → store should still open.
    std::fs::remove_file(tmp.path().join(".leet/index.bin")).unwrap();

    let store = PersonalStore::open_or_create(tmp.path()).unwrap();
    assert_eq!(store.len(), 8);
    // Lossy rebuild: all entries default to level 0, none consolidated.
    // Recall would treat them as 8 raw records — degraded but functional.
    for e in &store.index.entries {
        assert_eq!(e.level, 0);
        assert!(!e.is_consolidated());
    }
}
```

---

## FILE 3 — `leet-mcp/src/tools.rs` (minor: track `last_recall_at`)

In `leet_recall`, after computing the recall response, touch the cursor and flush:

```rust
pub async fn leet_recall(args: Value, store: &mut PersonalStore) -> Result<crate::protocol::ToolResult> {
    // ... existing recall logic stays exactly the same ...

    // Update cursor so PROMPT_11b can later send only post-recall deltas.
    store.index.touch_recall(now_ns());
    let _ = store.index.flush(); // best-effort; recall still succeeds if flush fails

    Ok(crate::protocol::ToolResult::text(out))
}
```

Note the change: `store: &PersonalStore` becomes `store: &mut PersonalStore` — propagate this through `server.rs` (`leet_recall` dispatch already has `&mut store` available since 10a).

The recall **logic itself** isn't changed yet — that's PROMPT_11b. This prompt only sets up the index and the consolidation engine.

---

## VERIFICATION

```bash
cargo build --workspace
cargo test -p leet-mcp --lib index
cargo test -p leet-mcp --lib store
cargo test --workspace

# End-to-end smoke
rm -rf /tmp/leet-consol && mkdir /tmp/leet-consol
LEET_PROJECT_ROOT=/tmp/leet-consol cargo run -p leet-mcp <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"a"}}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"b"}}}
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"c"}}}
{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"d"}}}
{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"e"}}}
{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"f"}}}
{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"g"}}}
EOF

ls -la /tmp/leet-consol/.leet/
# store.bin should be 16 + 8*360 = 2896 bytes (7 raw + 1 consolidated)
# index.bin should be 32 + 8*24 = 224 bytes

# Sanity: the 8th store record is the consolidated one
xxd /tmp/leet-consol/.leet/index.bin | head
# Should show level=1 in the entry at offset 32 + 7*24 = 200
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt11a "Hierarchical consolidation: index.bin sidecar + auto-trigger BLEND_N at threshold 7"
# work
task project:1337 +prompt11a done

git add leet-mcp/src/index.rs leet-mcp/src/store.rs leet-mcp/src/tools.rs leet-mcp/src/main.rs
git commit -m "feat(mcp): hierarchical consolidation via .leet/index.bin sidecar

When 7 live records accumulate at the same level, BLEND_N merges the
oldest 7 into one record at level+1. Cascades automatically — at scale
the store becomes a memory pyramid (level 0 raw, level 1 batches of 7,
level 2 batches of 49, etc).

BLEND_N is hybrid:
  - default axes: G1_MASS-weighted centroid (uniform fallback if total
    mass is zero)
  - D4_STABILITY: min (conservative)
  - G1_MASS: clamp(sum, 0, 1) (accumulate, saturating)
  - G7_K_INTERACTION: max
  - P6_CONFIDENCE: min (conservative)

This generalizes BLEND from 2→N COGONs while preserving the per-block
semantics codified in v0.5.1 operators.

New file: .leet/index.bin (32-byte header + 24-byte entries)
  - level: u8
  - flags: u8 (bit 0 = consolidated)
  - consolidates_from_first/last: u64 byte offsets in store.bin
  - last_recall_at: i64 in header (used by PROMPT_11b)

Crash-safety: index flushed atomically (tempfile + rename + fsync).
If index.bin is missing or out of sync, rebuilds fresh (lossy: all
records degrade to level=0, but recall still works).

Recall logic unchanged in this PR — PROMPT_11b changes how recall
filters records by level and uses the last_recall_at cursor.

Part of token-optimization phase, sub-prompt 11a."
git push origin main
```

---

**END OF PROMPT_11a**
