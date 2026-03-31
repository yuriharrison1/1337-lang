use std::collections::HashMap;
use std::sync::Arc;
use async_trait::async_trait;
use anyhow::Result;
use tokio::sync::RwLock;

use crate::config::Config;

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct CogonRecord {
    pub cogon_id: String,
    pub sem:      [f32; 32],
    pub unc:      [f32; 32],
    pub stamp:    i64,
    pub text_raw: Option<String>,
}

#[async_trait]
pub trait Store: Send + Sync {
    async fn add(&self, agent_id: &str, record: CogonRecord) -> Result<()>;
    async fn recall(
        &self,
        agent_id: &str,
        query_sem: &[f32; 32],
        query_unc: &[f32; 32],
        k: usize,
    ) -> Result<Vec<(CogonRecord, f32)>>;
    async fn get_session_delta(
        &self,
        session_id: &str,
        since: i64,
    ) -> Result<Vec<CogonRecord>>;
}

// ─── DIST formula ────────────────────────────────────────────────────────────

fn weighted_dist(
    sem1: &[f32; 32],
    unc1: &[f32; 32],
    sem2: &[f32; 32],
    unc2: &[f32; 32],
) -> f32 {
    let mut dot = 0f32;
    let mut norm1 = 0f32;
    let mut norm2 = 0f32;
    for i in 0..32 {
        let w = (1.0 - unc1[i]) * (1.0 - unc2[i]);
        dot   += sem1[i] * sem2[i] * w;
        norm1 += sem1[i] * sem1[i] * w;
        norm2 += sem2[i] * sem2[i] * w;
    }
    let similarity = dot / (norm1.sqrt() * norm2.sqrt() + 1e-8);
    1.0 - similarity
}

// ─── Memory store ─────────────────────────────────────────────────────────────

pub struct MemoryStore {
    data: Arc<RwLock<HashMap<String, Vec<CogonRecord>>>>,
}

impl MemoryStore {
    pub fn new() -> Self {
        Self { data: Arc::new(RwLock::new(HashMap::new())) }
    }
}

#[async_trait]
impl Store for MemoryStore {
    async fn add(&self, agent_id: &str, record: CogonRecord) -> Result<()> {
        self.data
            .write()
            .await
            .entry(agent_id.to_string())
            .or_default()
            .push(record);
        Ok(())
    }

    async fn recall(
        &self,
        agent_id: &str,
        query_sem: &[f32; 32],
        query_unc: &[f32; 32],
        k: usize,
    ) -> Result<Vec<(CogonRecord, f32)>> {
        let map = self.data.read().await;
        let records = match map.get(agent_id) {
            Some(r) => r,
            None => return Ok(vec![]),
        };
        let mut scored: Vec<(CogonRecord, f32)> = records
            .iter()
            .map(|r| {
                let d = weighted_dist(query_sem, query_unc, &r.sem, &r.unc);
                (r.clone(), d)
            })
            .collect();
        scored.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
        scored.truncate(k);
        Ok(scored)
    }

    async fn get_session_delta(&self, _session_id: &str, _since: i64) -> Result<Vec<CogonRecord>> {
        // session-level retrieval not yet implemented for memory store
        Ok(vec![])
    }
}

// ─── Redis store ──────────────────────────────────────────────────────────────

pub struct RedisStore {
    client: redis::Client,
}

impl RedisStore {
    pub fn new(url: &str) -> Result<Self> {
        let client = redis::Client::open(url)?;
        Ok(Self { client })
    }

    fn key(agent_id: &str) -> String {
        format!("leet:store:{}", agent_id)
    }
}

#[async_trait]
impl Store for RedisStore {
    async fn add(&self, agent_id: &str, record: CogonRecord) -> Result<()> {
        use redis::AsyncCommands;
        let mut conn = self.client.get_async_connection().await?;
        let json = serde_json::to_string(&record)?;
        conn.rpush::<_, _, ()>(Self::key(agent_id), json).await?;
        Ok(())
    }

    async fn recall(
        &self,
        agent_id: &str,
        query_sem: &[f32; 32],
        query_unc: &[f32; 32],
        k: usize,
    ) -> Result<Vec<(CogonRecord, f32)>> {
        use redis::AsyncCommands;
        let mut conn = self.client.get_async_connection().await?;
        let raw: Vec<String> = conn.lrange(Self::key(agent_id), 0, -1).await?;
        let records: Vec<CogonRecord> = raw
            .iter()
            .filter_map(|s| serde_json::from_str(s).ok())
            .collect();
        let mut scored: Vec<(CogonRecord, f32)> = records
            .into_iter()
            .map(|r| {
                let d = weighted_dist(query_sem, query_unc, &r.sem, &r.unc);
                (r, d)
            })
            .collect();
        scored.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
        scored.truncate(k);
        Ok(scored)
    }

    async fn get_session_delta(&self, _session_id: &str, _since: i64) -> Result<Vec<CogonRecord>> {
        Ok(vec![])
    }
}

// ─── Factory ──────────────────────────────────────────────────────────────────

pub async fn build(cfg: &Config) -> Result<Box<dyn Store>> {
    let url = cfg.store_url.as_str();
    if url == "memory" {
        Ok(Box::new(MemoryStore::new()))
    } else if url.starts_with("redis://") || url.starts_with("rediss://") {
        let store = RedisStore::new(url)?;
        Ok(Box::new(store))
    } else if url.starts_with("sqlite://") {
        tracing::warn!("SQLite backend not yet implemented — falling back to memory store");
        Ok(Box::new(MemoryStore::new()))
    } else {
        tracing::warn!("Unknown store URL '{}' — falling back to memory store", url);
        Ok(Box::new(MemoryStore::new()))
    }
}
