//! tonic gRPC service implementation.

use std::pin::Pin;
use std::sync::Arc;
use std::time::{Instant, SystemTime, UNIX_EPOCH};
use tokio::sync::mpsc;
use tokio_stream::wrappers::ReceiverStream;
use tokio_stream::StreamExt;
use tonic::{Request, Response, Status, Streaming};
use uuid::Uuid;

use crate::batch::BatchQueue;
use crate::config::Config;
use crate::projection::Engine;
use crate::store::Store;

pub mod proto {
    tonic::include_proto!("leet");
}

use proto::leet_service_server::LeetService;
use proto::{
    CogonRecord, DecodeRequest, DecodeResponse, DeltaRequest, DeltaResponse, EncodeRequest,
    EncodeResponse, HealthRequest, HealthResponse, RecallRequest, RecallResponse,
};

pub type EncodeResponseStream =
    Pin<Box<dyn futures_core::Stream<Item = Result<EncodeResponse, Status>> + Send>>;

/// Main service implementation.
pub struct LeetServiceImpl {
    pub engine: Arc<Engine>,
    pub store: Arc<dyn Store>,
    pub config: Config,
    pub batch_queue: Arc<BatchQueue>,
    pub start_time: Instant,
}

impl LeetServiceImpl {
    pub fn new(engine: Arc<Engine>, store: Arc<dyn Store>, config: Config) -> Self {
        let batch_queue = Arc::new(BatchQueue::new(engine.clone()));
        Self {
            engine,
            store,
            config,
            batch_queue,
            start_time: Instant::now(),
        }
    }
}

fn current_stamp() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

/// Approximate tokens saved: original text byte length / 4 (rough estimate).
fn tokens_saved(text: &str) -> i64 {
    let original_tokens = (text.len() as i64).saturating_add(3) / 4;
    let cogon_tokens = 32i64;
    (original_tokens - cogon_tokens).max(0)
}

#[tonic::async_trait]
impl LeetService for LeetServiceImpl {
    type EncodeBatchStream = EncodeResponseStream;

    async fn encode(
        &self,
        request: Request<EncodeRequest>,
    ) -> Result<Response<EncodeResponse>, Status> {
        let req = request.into_inner();
        let sem = self.engine.project(&req.text, &req.agent_id);
        let cogon_id = Uuid::new_v4().to_string();
        let stamp = current_stamp();
        let saved = tokens_saved(&req.text);

        self.store
            .save(&req.agent_id, &cogon_id, sem.clone(), stamp)
            .map_err(Status::internal)?;

        Ok(Response::new(EncodeResponse {
            cogon_id,
            sem,
            unc: vec![], // reserved for wire compat; not used in v0.5.1
            stamp,
            tokens_saved: saved,
        }))
    }

    async fn decode(
        &self,
        request: Request<DecodeRequest>,
    ) -> Result<Response<DecodeResponse>, Status> {
        let req = request.into_inner();
        let text = self.engine.reconstruct(&req.sem, &req.lang);
        Ok(Response::new(DecodeResponse { text }))
    }

    async fn encode_batch(
        &self,
        request: Request<Streaming<EncodeRequest>>,
    ) -> Result<Response<Self::EncodeBatchStream>, Status> {
        let mut stream = request.into_inner();
        let queue = self.batch_queue.clone();
        let store = self.store.clone();

        let (tx, rx) = mpsc::channel(128);

        tokio::spawn(async move {
            while let Some(result) = stream.next().await {
                match result {
                    Ok(req) => {
                        let sem = queue.push(req.text.clone(), req.agent_id.clone()).await;
                        let cogon_id = Uuid::new_v4().to_string();
                        let stamp = current_stamp();
                        let saved = tokens_saved(&req.text);

                        let _ = store.save(&req.agent_id, &cogon_id, sem.clone(), stamp);

                        let resp = EncodeResponse {
                            cogon_id,
                            sem,
                            unc: vec![],
                            stamp,
                            tokens_saved: saved,
                        };
                        if tx.send(Ok(resp)).await.is_err() {
                            break;
                        }
                    }
                    Err(e) => {
                        let _ = tx.send(Err(Status::internal(e.to_string()))).await;
                        break;
                    }
                }
            }
        });

        let output = ReceiverStream::new(rx);
        Ok(Response::new(Box::pin(output)))
    }

    async fn delta(
        &self,
        request: Request<DeltaRequest>,
    ) -> Result<Response<DeltaResponse>, Status> {
        let req = request.into_inner();
        let sem_prev = &req.sem_prev;
        let sem_curr = &req.sem_curr;

        let len = sem_prev.len().min(sem_curr.len());
        let patch: Vec<f32> = (0..len)
            .map(|i| sem_curr[i] - sem_prev[i])
            .collect();

        let magnitude = patch.iter().map(|v| v * v).sum::<f32>().sqrt();

        Ok(Response::new(DeltaResponse { patch, magnitude }))
    }

    async fn recall(
        &self,
        request: Request<RecallRequest>,
    ) -> Result<Response<RecallResponse>, Status> {
        let req = request.into_inner();
        let k = req.k as usize;

        let records = self
            .store
            .recall(&req.agent_id, &req.sem, k)
            .map_err(Status::internal)?;

        let results = records
            .into_iter()
            .map(|r| CogonRecord {
                cogon_id: r.cogon_id,
                sem: r.sem,
                unc: vec![], // reserved for wire compat
                dist: r.dist,
                stamp: r.stamp,
            })
            .collect();

        Ok(Response::new(RecallResponse { results }))
    }

    async fn health(
        &self,
        _request: Request<HealthRequest>,
    ) -> Result<Response<HealthResponse>, Status> {
        let uptime = self.start_time.elapsed().as_secs() as i64;
        Ok(Response::new(HealthResponse {
            status: "ok".to_string(),
            backend: self.config.store.clone(),
            uptime,
        }))
    }
}
