//! PersonalStore — per-agent COGON storage with recall by cosine similarity.

use parking_lot::RwLock;
use std::collections::HashMap;
use std::sync::Arc;

/// A stored COGON record.
#[derive(Clone, Debug)]
pub struct StoredCogon {
    pub cogon_id: String,
    pub agent_id: String,
    pub sem: Vec<f32>,
    pub unc: Vec<f32>,
    pub stamp: i64,
}

/// Result record for recall queries.
#[derive(Clone, Debug)]
pub struct CogonRecord {
    pub cogon_id: String,
    pub sem: Vec<f32>,
    pub unc: Vec<f32>,
    pub dist: f32,
    pub stamp: i64,
}

/// Trait for COGON storage backends.
pub trait Store: Send + Sync {
    fn save(
        &self,
        agent_id: &str,
        cogon_id: &str,
        sem: Vec<f32>,
        unc: Vec<f32>,
        stamp: i64,
    ) -> Result<(), String>;

    fn recall(
        &self,
        agent_id: &str,
        query_sem: &[f32],
        k: usize,
    ) -> Result<Vec<CogonRecord>, String>;
}

/// Cosine similarity between two equal-length vectors.
fn cosine_dist(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 1.0;
    }
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        return 1.0;
    }
    let cosine = (dot / (norm_a * norm_b)).clamp(-1.0, 1.0);
    1.0 - cosine
}

/// In-memory store using a HashMap guarded by a RwLock.
pub struct MemoryStore {
    data: RwLock<HashMap<String, Vec<StoredCogon>>>,
}

impl MemoryStore {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            data: RwLock::new(HashMap::new()),
        })
    }
}

impl Default for MemoryStore {
    fn default() -> Self {
        Self {
            data: RwLock::new(HashMap::new()),
        }
    }
}

impl Store for MemoryStore {
    fn save(
        &self,
        agent_id: &str,
        cogon_id: &str,
        sem: Vec<f32>,
        unc: Vec<f32>,
        stamp: i64,
    ) -> Result<(), String> {
        let mut data = self.data.write();
        data.entry(agent_id.to_string())
            .or_default()
            .push(StoredCogon {
                cogon_id: cogon_id.to_string(),
                agent_id: agent_id.to_string(),
                sem,
                unc,
                stamp,
            });
        Ok(())
    }

    fn recall(
        &self,
        agent_id: &str,
        query_sem: &[f32],
        k: usize,
    ) -> Result<Vec<CogonRecord>, String> {
        let data = self.data.read();
        let empty = Vec::new();
        let agent_cogons = data.get(agent_id).unwrap_or(&empty);

        let mut scored: Vec<(f32, &StoredCogon)> = agent_cogons
            .iter()
            .map(|c| (cosine_dist(query_sem, &c.sem), c))
            .collect();

        scored.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));

        let results = scored
            .into_iter()
            .take(k)
            .map(|(dist, c)| CogonRecord {
                cogon_id: c.cogon_id.clone(),
                sem: c.sem.clone(),
                unc: c.unc.clone(),
                dist,
                stamp: c.stamp,
            })
            .collect();

        Ok(results)
    }
}

/// SQLite-backed store.
pub struct SqliteStore {
    path: String,
}

impl SqliteStore {
    pub fn new(path: &str) -> Result<Arc<Self>, String> {
        let store = Arc::new(Self {
            path: path.to_string(),
        });

        // Initialize the table
        let conn = rusqlite::Connection::open(&store.path)
            .map_err(|e| e.to_string())?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS cogons (
                cogon_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                sem BLOB NOT NULL,
                unc BLOB NOT NULL,
                stamp INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_agent ON cogons(agent_id);",
        )
        .map_err(|e| e.to_string())?;

        Ok(store)
    }

    fn floats_to_bytes(v: &[f32]) -> Vec<u8> {
        v.iter()
            .flat_map(|f| f.to_le_bytes())
            .collect()
    }

    fn bytes_to_floats(b: &[u8]) -> Vec<f32> {
        b.chunks_exact(4)
            .map(|chunk| {
                let arr = [chunk[0], chunk[1], chunk[2], chunk[3]];
                f32::from_le_bytes(arr)
            })
            .collect()
    }
}

impl Store for SqliteStore {
    fn save(
        &self,
        agent_id: &str,
        cogon_id: &str,
        sem: Vec<f32>,
        unc: Vec<f32>,
        stamp: i64,
    ) -> Result<(), String> {
        let conn = rusqlite::Connection::open(&self.path)
            .map_err(|e| e.to_string())?;

        let sem_bytes = Self::floats_to_bytes(&sem);
        let unc_bytes = Self::floats_to_bytes(&unc);

        conn.execute(
            "INSERT INTO cogons (cogon_id, agent_id, sem, unc, stamp) VALUES (?1, ?2, ?3, ?4, ?5)",
            rusqlite::params![cogon_id, agent_id, sem_bytes, unc_bytes, stamp],
        )
        .map_err(|e| e.to_string())?;

        Ok(())
    }

    fn recall(
        &self,
        agent_id: &str,
        query_sem: &[f32],
        k: usize,
    ) -> Result<Vec<CogonRecord>, String> {
        let conn = rusqlite::Connection::open(&self.path)
            .map_err(|e| e.to_string())?;

        let mut stmt = conn
            .prepare(
                "SELECT cogon_id, sem, unc, stamp FROM cogons WHERE agent_id = ?1",
            )
            .map_err(|e| e.to_string())?;

        let rows: Vec<StoredCogon> = stmt
            .query_map(rusqlite::params![agent_id], |row| {
                let cogon_id: String = row.get(0)?;
                let sem_bytes: Vec<u8> = row.get(1)?;
                let unc_bytes: Vec<u8> = row.get(2)?;
                let stamp: i64 = row.get(3)?;
                Ok(StoredCogon {
                    cogon_id,
                    agent_id: agent_id.to_string(),
                    sem: SqliteStore::bytes_to_floats(&sem_bytes),
                    unc: SqliteStore::bytes_to_floats(&unc_bytes),
                    stamp,
                })
            })
            .map_err(|e| e.to_string())?
            .filter_map(|r| r.ok())
            .collect();

        let mut scored: Vec<(f32, StoredCogon)> = rows
            .into_iter()
            .map(|c| {
                let d = cosine_dist(query_sem, &c.sem);
                (d, c)
            })
            .collect();

        scored.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));

        let results = scored
            .into_iter()
            .take(k)
            .map(|(dist, c)| CogonRecord {
                cogon_id: c.cogon_id,
                sem: c.sem,
                unc: c.unc,
                dist,
                stamp: c.stamp,
            })
            .collect();

        Ok(results)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_memory_store_save_recall() {
        let store = MemoryStore::default();
        let sem = vec![0.9_f32; 32];
        let unc = vec![0.1_f32; 32];
        store.save("agent1", "cogon-abc", sem.clone(), unc.clone(), 1000).unwrap();

        let results = store.recall("agent1", &sem, 5).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].cogon_id, "cogon-abc");
        assert!(results[0].dist < 0.01);
    }

    #[test]
    fn test_memory_store_empty_recall() {
        let store = MemoryStore::default();
        let query = vec![0.5_f32; 32];
        let results = store.recall("agent_unknown", &query, 5).unwrap();
        assert!(results.is_empty());
    }

    #[test]
    fn test_memory_store_ordered_by_dist() {
        let store = MemoryStore::default();
        let mut close = vec![0.5_f32; 32];
        close[0] = 0.9;
        let mut far = vec![0.5_f32; 32];
        far[0] = 0.1;
        let unc = vec![0.1_f32; 32];
        store.save("a1", "close", close.clone(), unc.clone(), 1).unwrap();
        store.save("a1", "far", far.clone(), unc.clone(), 2).unwrap();

        let query = close.clone();
        let results = store.recall("a1", &query, 5).unwrap();
        assert_eq!(results.len(), 2);
        // First result should be closer
        assert!(results[0].dist <= results[1].dist);
    }
}
