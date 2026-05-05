//! Sidecar index file for `.leet/store.bin`. Tracks per-record level + cursors.
//! Append-only and crash-safe in the same style as the store itself.

use std::fs::File;
use std::io::{Read, Write};
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
        // Reopen claiming 8 records — mismatch.
        let idx = Index::open_or_create(tmp.path(), 8).unwrap();
        assert_eq!(idx.entries.len(), 8);
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
