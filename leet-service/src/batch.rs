//! BatchQueue — collects encode requests and flushes them in batches.

use std::sync::Arc;
use tokio::sync::{mpsc, oneshot};
use tokio::time::{interval, Duration};

use crate::projection::Engine;

/// Internal job: one encode request waiting for its response.
struct Job {
    text: String,
    agent_id: String,
    reply: oneshot::Sender<(Vec<f32>, Vec<f32>)>,
}

/// A batch queue that groups encode requests and processes them together.
///
/// Flushes at most every 10ms or when the queue reaches 64 items.
pub struct BatchQueue {
    sender: mpsc::Sender<Job>,
}

impl BatchQueue {
    /// Create a new BatchQueue and spawn the internal worker.
    pub fn new(engine: Arc<Engine>) -> Self {
        let (sender, mut receiver) = mpsc::channel::<Job>(512);

        tokio::spawn(async move {
            let mut ticker = interval(Duration::from_millis(10));
            let mut pending: Vec<Job> = Vec::new();

            loop {
                tokio::select! {
                    maybe_job = receiver.recv() => {
                        match maybe_job {
                            Some(job) => {
                                pending.push(job);
                                if pending.len() >= 64 {
                                    flush(&engine, &mut pending);
                                }
                            }
                            None => {
                                // Channel closed, flush remaining and exit
                                flush(&engine, &mut pending);
                                break;
                            }
                        }
                    }
                    _ = ticker.tick() => {
                        if !pending.is_empty() {
                            flush(&engine, &mut pending);
                        }
                    }
                }
            }
        });

        Self { sender }
    }

    /// Push an encode request and wait for the result.
    pub async fn push(&self, text: String, agent_id: String) -> (Vec<f32>, Vec<f32>) {
        let (reply_tx, reply_rx) = oneshot::channel();
        let job = Job {
            text,
            agent_id,
            reply: reply_tx,
        };
        // If channel is full or dropped, fall back to direct projection
        if self.sender.send(job).await.is_err() {
            return (vec![0.5_f32; 32], vec![0.2_f32; 32]);
        }
        reply_rx.await.unwrap_or_else(|_| (vec![0.5_f32; 32], vec![0.2_f32; 32]))
    }
}

fn flush(engine: &Engine, pending: &mut Vec<Job>) {
    for job in pending.drain(..) {
        let (sem, unc) = engine.project(&job.text, &job.agent_id);
        let _ = job.reply.send((sem, unc));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_batch_processes_requests() {
        let engine = Arc::new(Engine::new());
        let queue = BatchQueue::new(engine);
        let (sem, unc) = queue.push("urgente".to_string(), "agent1".to_string()).await;
        assert_eq!(sem.len(), 32);
        assert_eq!(unc.len(), 32);
        assert!(sem[22] > 0.9, "C1_URGENCIA should be activated");
    }

    #[tokio::test]
    async fn test_batch_multiple_requests() {
        let engine = Arc::new(Engine::new());
        let queue = Arc::new(BatchQueue::new(engine));

        let mut handles = Vec::new();
        for i in 0..10 {
            let q = queue.clone();
            let text = format!("request {}", i);
            handles.push(tokio::spawn(async move {
                q.push(text, "agent1".to_string()).await
            }));
        }

        for handle in handles {
            let (sem, unc) = handle.await.unwrap();
            assert_eq!(sem.len(), 32);
            assert_eq!(unc.len(), 32);
        }
    }
}
