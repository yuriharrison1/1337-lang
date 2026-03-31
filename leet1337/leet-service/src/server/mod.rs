use std::sync::Arc;
use std::time::{Instant, SystemTime, UNIX_EPOCH};
use tokio_stream::StreamExt;
use tonic::{transport::Server, Request, Response, Status, Streaming};
use tokio_stream::wrappers::ReceiverStream;

use crate::config::Config;
use crate::projection::{Engine, batch::BatchQueue};
use crate::store::{Store, CogonRecord};

pub mod proto {
    tonic::include_proto!("leet");
}

use proto::{
    leet_service_server::{LeetService, LeetServiceServer},
    CogonRecord as ProtoCogonRecord,
    DecodeRequest, DecodeResponse,
    DeltaRequest, DeltaResponse,
    EncodeRequest, EncodeResponse,
    HealthRequest, HealthResponse,
    RecallRequest, RecallResponse,
};

const AXIS_NAMES: [&str; 32] = [
    "via", "correspondencia", "vibracao", "polaridade", "ritmo", "causa_efeito", "genero",
    "sistema", "estado", "processo", "relacao", "sinal", "estabilidade", "valencia_ontologica",
    "verificabilidade", "temporalidade", "completude", "causalidade", "reversibilidade",
    "carga", "origem", "valencia_epistemica",
    "urgencia", "impacto", "acao", "valor", "anomalia", "afeto", "dependencia",
    "vetor_temporal", "natureza", "valencia_acao",
];

pub struct LeetServiceImpl {
    cfg:     Config,
    queue:   BatchQueue,
    store:   Arc<dyn Store>,
    started: Instant,
}

impl LeetServiceImpl {
    pub fn new(cfg: Config, engine: Arc<Engine>, store: Box<dyn Store>) -> Self {
        let queue = BatchQueue::new(engine, cfg.batch_window_ms, cfg.batch_max);
        Self {
            cfg,
            queue,
            store: Arc::from(store),
            started: Instant::now(),
        }
    }
}

fn now_nanos() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos() as i64)
        .unwrap_or(0)
}

fn tokens_saved(text: &str) -> i64 {
    let text_tokens = (text.len() / 4) as i64;
    let cogon_tokens = (32 * 2 / 100) as i64;
    (text_tokens - cogon_tokens).max(0)
}

async fn do_encode(
    queue: &BatchQueue,
    store: &Arc<dyn Store>,
    r: EncodeRequest,
) -> Result<EncodeResponse, Status> {
    let (sem, unc) = queue
        .encode(r.text.clone())
        .await
        .map_err(|e| Status::internal(e.to_string()))?;

    let cogon_id = uuid::Uuid::new_v4().to_string();
    let stamp = now_nanos();

    if !r.agent_id.is_empty() {
        let record = CogonRecord {
            cogon_id: cogon_id.clone(),
            sem,
            unc,
            stamp,
            text_raw: Some(r.text.clone()),
        };
        let store2 = store.clone();
        let agent_id = r.agent_id.clone();
        tokio::spawn(async move {
            if let Err(e) = store2.add(&agent_id, record).await {
                tracing::warn!("store.add failed: {}", e);
            }
        });
    }

    Ok(EncodeResponse {
        cogon_id,
        sem: sem.to_vec(),
        unc: unc.to_vec(),
        stamp,
        tokens_saved: tokens_saved(&r.text),
    })
}

#[tonic::async_trait]
impl LeetService for LeetServiceImpl {
    async fn encode(
        &self,
        req: Request<EncodeRequest>,
    ) -> Result<Response<EncodeResponse>, Status> {
        let r = req.into_inner();
        let resp = do_encode(&self.queue, &self.store, r).await?;
        Ok(Response::new(resp))
    }

    async fn decode(
        &self,
        req: Request<DecodeRequest>,
    ) -> Result<Response<DecodeResponse>, Status> {
        let r = req.into_inner();
        if r.sem.len() < 32 {
            return Err(Status::invalid_argument("sem must have 32 elements"));
        }
        let text = AXIS_NAMES
            .iter()
            .enumerate()
            .map(|(i, name)| format!("{}:{:.2}", name, r.sem[i]))
            .collect::<Vec<_>>()
            .join(" ");
        Ok(Response::new(DecodeResponse { text }))
    }

    type EncodeBatchStream = ReceiverStream<Result<EncodeResponse, Status>>;

    async fn encode_batch(
        &self,
        req: Request<Streaming<EncodeRequest>>,
    ) -> Result<Response<Self::EncodeBatchStream>, Status> {
        let mut stream = req.into_inner();
        let (tx, rx) = tokio::sync::mpsc::channel(64);
        let queue = self.queue.clone();
        let store = self.store.clone();

        tokio::spawn(async move {
            while let Some(item) = stream.next().await {
                match item {
                    Ok(r) => {
                        let result = do_encode(&queue, &store, r).await;
                        if tx.send(result).await.is_err() {
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

        Ok(Response::new(ReceiverStream::new(rx)))
    }

    async fn delta(
        &self,
        req: Request<DeltaRequest>,
    ) -> Result<Response<DeltaResponse>, Status> {
        let r = req.into_inner();
        if r.sem_prev.len() < 32 || r.sem_curr.len() < 32 {
            return Err(Status::invalid_argument("sem vectors must have 32 elements"));
        }
        let patch: Vec<f32> = (0..32)
            .map(|i| r.sem_curr[i] - r.sem_prev[i])
            .collect();
        let magnitude = patch.iter().map(|x| x * x).sum::<f32>().sqrt();
        Ok(Response::new(DeltaResponse { patch, magnitude }))
    }

    async fn recall(
        &self,
        req: Request<RecallRequest>,
    ) -> Result<Response<RecallResponse>, Status> {
        let r = req.into_inner();
        if r.sem.len() < 32 || r.unc.len() < 32 {
            return Err(Status::invalid_argument("sem and unc must have 32 elements"));
        }
        let mut sem = [0f32; 32];
        let mut unc = [0f32; 32];
        sem.copy_from_slice(&r.sem[..32]);
        unc.copy_from_slice(&r.unc[..32]);
        let k = r.k.max(1) as usize;

        let results = self
            .store
            .recall(&r.agent_id, &sem, &unc, k)
            .await
            .map_err(|e| Status::internal(e.to_string()))?;

        let proto_results = results
            .into_iter()
            .map(|(rec, dist)| ProtoCogonRecord {
                cogon_id: rec.cogon_id,
                sem: rec.sem.to_vec(),
                unc: rec.unc.to_vec(),
                dist,
                stamp: rec.stamp,
            })
            .collect();

        Ok(Response::new(RecallResponse { results: proto_results }))
    }

    async fn health(
        &self,
        _req: Request<HealthRequest>,
    ) -> Result<Response<HealthResponse>, Status> {
        Ok(Response::new(HealthResponse {
            status:  "ok".to_string(),
            backend: self.cfg.backend.clone(),
            uptime:  self.started.elapsed().as_secs() as i64,
        }))
    }
}

pub async fn run(cfg: Config, engine: Engine, store: Box<dyn Store>) -> anyhow::Result<()> {
    let addr = format!("0.0.0.0:{}", cfg.port).parse()?;
    let svc = LeetServiceImpl::new(cfg, Arc::new(engine), store);

    tracing::info!("listening on {}", addr);
    Server::builder()
        .add_service(LeetServiceServer::new(svc))
        .serve(addr)
        .await?;
    Ok(())
}
