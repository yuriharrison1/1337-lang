use std::sync::Arc;
use tokio::sync::{mpsc, oneshot};
use anyhow::Result;

use super::engine::Engine;

struct BatchItem {
    text:    String,
    resp_tx: oneshot::Sender<Result<([f32; 32], [f32; 32])>>,
}

/// Thread-safe, cloneable handle to the batch encoding queue.
#[derive(Clone)]
pub struct BatchQueue {
    tx: mpsc::Sender<BatchItem>,
}

impl BatchQueue {
    pub fn new(engine: Arc<Engine>, window_ms: u64, max_size: usize) -> Self {
        let (tx, rx) = mpsc::channel::<BatchItem>(1024);
        tokio::spawn(worker(rx, engine, window_ms, max_size));
        Self { tx }
    }

    pub async fn encode(&self, text: String) -> Result<([f32; 32], [f32; 32])> {
        let (resp_tx, resp_rx) = oneshot::channel();
        self.tx
            .send(BatchItem { text, resp_tx })
            .await
            .map_err(|_| anyhow::anyhow!("batch worker closed"))?;
        resp_rx.await.map_err(|_| anyhow::anyhow!("batch worker dropped sender"))?
    }
}

async fn worker(
    mut rx: mpsc::Receiver<BatchItem>,
    engine: Arc<Engine>,
    window_ms: u64,
    max_size: usize,
) {
    loop {
        // Block until at least one item arrives.
        let first = match rx.recv().await {
            Some(item) => item,
            None => return,
        };

        let mut batch = vec![first];
        let deadline = tokio::time::Instant::now()
            + tokio::time::Duration::from_millis(window_ms);

        // Drain remaining items within the time window.
        loop {
            if batch.len() >= max_size {
                break;
            }
            match tokio::time::timeout_at(deadline, rx.recv()).await {
                Ok(Some(item)) => batch.push(item),
                _ => break,
            }
        }

        // Collect all texts, then encode the whole batch in ONE GEMM call.
        let texts: Vec<String> = batch.iter().map(|item| item.text.clone()).collect();

        match engine.encode_batch(&texts).await {
            Ok(results) => {
                for (item, result) in batch.into_iter().zip(results) {
                    let _ = item.resp_tx.send(Ok(result));
                }
            }
            Err(e) => {
                // Propagate the error to all waiting callers.
                let msg = e.to_string();
                for item in batch {
                    let _ = item.resp_tx.send(Err(anyhow::anyhow!("{}", msg)));
                }
            }
        }
    }
}
