use anyhow::Result;
use async_trait::async_trait;
use sha2::{Digest, Sha256};

#[async_trait]
pub trait Embedder: Send + Sync {
    async fn embed(&self, text: &str) -> Result<Vec<f32>>;
    fn dim(&self) -> usize;
}

// ─── Mock embedder ───────────────────────────────────────────────────────────

pub struct MockEmbedder;

#[async_trait]
impl Embedder for MockEmbedder {
    async fn embed(&self, text: &str) -> Result<Vec<f32>> {
        let hash = Sha256::digest(text.as_bytes());
        let bytes = hash.as_slice();
        // Expand 32 hash bytes to 128 floats by cycling
        let floats: Vec<f32> = (0..128)
            .map(|i| bytes[i % 32] as f32 / 255.0)
            .collect();
        Ok(floats)
    }

    fn dim(&self) -> usize {
        128
    }
}

// ─── OpenAI embedder ─────────────────────────────────────────────────────────

pub struct OpenAIEmbedder {
    url:    String,
    key:    String,
    client: reqwest::Client,
}

impl OpenAIEmbedder {
    pub fn new(url: Option<String>, key: String) -> Self {
        Self {
            url: url.unwrap_or_else(|| "https://api.openai.com/v1/embeddings".to_string()),
            key,
            client: reqwest::Client::new(),
        }
    }
}

#[async_trait]
impl Embedder for OpenAIEmbedder {
    async fn embed(&self, text: &str) -> Result<Vec<f32>> {
        let body = serde_json::json!({
            "model": "text-embedding-3-small",
            "input": text,
        });

        let resp = self
            .client
            .post(&self.url)
            .bearer_auth(&self.key)
            .json(&body)
            .send()
            .await?
            .error_for_status()?
            .json::<serde_json::Value>()
            .await?;

        let embedding = resp["data"][0]["embedding"]
            .as_array()
            .ok_or_else(|| anyhow::anyhow!("missing embedding in response"))?
            .iter()
            .map(|v| v.as_f64().unwrap_or(0.0) as f32)
            .collect();

        Ok(embedding)
    }

    fn dim(&self) -> usize {
        1536
    }
}
