use std::num::NonZeroUsize;
use std::sync::Mutex;

use anyhow::Result;
use lru::LruCache;

use crate::config::Config;
use super::embed::{Embedder, MockEmbedder, OpenAIEmbedder};
use super::matrix::WMatrix;

pub struct Engine {
    embedder: Box<dyn Embedder>,
    w:        WMatrix,
    /// LRU cache: text → raw embedding vector.
    /// Avoids repeated embedding calls for identical text (common in broadcasts/topics).
    cache:    Mutex<LruCache<String, Vec<f32>>>,
}

impl Engine {
    pub async fn new(cfg: &Config) -> Result<Self> {
        let embedder: Box<dyn Embedder> = match cfg.embed_model.as_str() {
            "openai" => {
                let key = cfg.embed_key.clone().unwrap_or_default();
                Box::new(OpenAIEmbedder::new(cfg.embed_url.clone(), key))
            }
            _ => Box::new(MockEmbedder),
        };

        let w = if let Some(ref path) = cfg.w_path {
            match WMatrix::load(path) {
                Ok(m) => {
                    tracing::info!("W matrix loaded from {}", path);
                    m
                }
                Err(e) => {
                    tracing::warn!("Failed to load W from {}: {}. Using identity init.", path, e);
                    WMatrix::identity_init(embedder.dim())
                }
            }
        } else {
            WMatrix::identity_init(embedder.dim())
        };

        let cache = Mutex::new(LruCache::new(NonZeroUsize::new(1024).unwrap()));

        Ok(Self { embedder, w, cache })
    }

    /// Get embedding for `text`, checking the LRU cache first.
    async fn get_embedding(&self, text: &str) -> Result<Vec<f32>> {
        // Check cache — lock briefly, clone if hit.
        {
            let mut guard = self.cache.lock().unwrap();
            if let Some(emb) = guard.get(text) {
                return Ok(emb.clone());
            }
        }
        // Cache miss: call embedder (potentially an HTTP request).
        let emb = self.embedder.embed(text).await?;
        {
            let mut guard = self.cache.lock().unwrap();
            guard.put(text.to_string(), emb.clone());
        }
        Ok(emb)
    }

    /// Encode a single text → (sem[32], unc[32]).
    pub async fn encode(&self, text: &str) -> Result<([f32; 32], [f32; 32])> {
        let emb = self.get_embedding(text).await?;
        let sem = self.w.project(&emb);
        let unc = estimate_unc(&sem);
        Ok((sem, unc))
    }

    /// Encode N texts in a single batch GEMM.
    /// Cache is checked per text before stacking embeddings.
    /// All embeddings are then projected together in one matrix multiply.
    pub async fn encode_batch(&self, texts: &[String]) -> Result<Vec<([f32; 32], [f32; 32])>> {
        // Resolve embeddings (cache-aware, serial — embedding calls are already I/O bound)
        let mut embeddings = Vec::with_capacity(texts.len());
        for text in texts {
            embeddings.push(self.get_embedding(text).await?);
        }

        // Single GEMM for all N embeddings
        let sems = self.w.project_batch(&embeddings);

        Ok(sems
            .into_iter()
            .map(|sem| {
                let unc = estimate_unc(&sem);
                (sem, unc)
            })
            .collect())
    }
}

/// Compute uncertainty from sem values.
/// Deterministic — allows receiver to recompute without transmitting unc.
fn estimate_unc(sem: &[f32; 32]) -> [f32; 32] {
    let mut unc = [0f32; 32];
    for i in 0..32 {
        let distance_from_center = (sem[i] - 0.5).abs() * 2.0;
        unc[i] = (1.0 - distance_from_center).clamp(0.0, 1.0);
    }
    unc
}
