//! Integration tests for leet-service.
//! Tests instantiate LeetServiceImpl directly without binding a TCP port.

use std::sync::Arc;
use std::time::Instant;
use tonic::Request;

// Import the service internals
use leet_service::batch::BatchQueue;
use leet_service::config::Config;
use leet_service::projection::Engine;
use leet_service::server::proto::leet_service_server::LeetService;
use leet_service::server::proto::{
    DecodeRequest, DeltaRequest, EncodeRequest, HealthRequest, RecallRequest,
};
use leet_service::server::LeetServiceImpl;
use leet_service::store::{MemoryStore, Store};

fn make_service() -> LeetServiceImpl {
    let engine = Arc::new(Engine::new());
    let store: Arc<dyn Store> = Arc::new(MemoryStore::default());
    let config = Config {
        port: 50051,
        store: "memory".to_string(),
        sqlite_path: ".test.db".to_string(),
        log: "info".to_string(),
    };
    LeetServiceImpl::new(engine, store, config)
}

#[tokio::test]
async fn test_encode_returns_32_dims() {
    let svc = make_service();
    let req = Request::new(EncodeRequest {
        text: "hello world".to_string(),
        agent_id: "agent1".to_string(),
        session_id: "sess1".to_string(),
    });
    let resp = svc.encode(req).await.unwrap().into_inner();
    assert_eq!(resp.sem.len(), 32);
    assert_eq!(resp.unc.len(), 32);
    assert!(!resp.cogon_id.is_empty());
}

#[tokio::test]
async fn test_encode_urgente_activates_c1() {
    let svc = make_service();
    let req = Request::new(EncodeRequest {
        text: "urgente agora".to_string(),
        agent_id: "agent1".to_string(),
        session_id: "sess1".to_string(),
    });
    let resp = svc.encode(req).await.unwrap().into_inner();
    // Index 22 = C1_URGENCIA
    assert!(resp.sem[22] > 0.9, "C1_URGENCIA should be activated, got {}", resp.sem[22]);
}

#[tokio::test]
async fn test_encode_erro_activates_anomalia() {
    let svc = make_service();
    let req = Request::new(EncodeRequest {
        text: "erro crítico no sistema".to_string(),
        agent_id: "agent1".to_string(),
        session_id: "sess1".to_string(),
    });
    let resp = svc.encode(req).await.unwrap().into_inner();
    // Index 26 = C5_ANOMALIA
    assert!(resp.sem[26] > 0.8, "C5_ANOMALIA should be activated");
    // Index 8 = A8_ESTADO
    assert!(resp.sem[8] > 0.8, "A8_ESTADO should be activated");
}

#[tokio::test]
async fn test_decode_returns_string() {
    let svc = make_service();
    let sem = vec![0.5_f32; 32];
    let unc = vec![0.2_f32; 32];
    let req = Request::new(DecodeRequest {
        sem,
        unc,
        lang: "en".to_string(),
    });
    let resp = svc.decode(req).await.unwrap().into_inner();
    assert!(!resp.text.is_empty());
}

#[tokio::test]
async fn test_delta_zero_for_identical() {
    let svc = make_service();
    let sem = vec![0.5_f32; 32];
    let req = Request::new(DeltaRequest {
        sem_prev: sem.clone(),
        sem_curr: sem.clone(),
    });
    let resp = svc.delta(req).await.unwrap().into_inner();
    for v in &resp.patch {
        assert!(v.abs() < 1e-6, "patch should be zero, got {}", v);
    }
    assert!(resp.magnitude.abs() < 1e-6);
}

#[tokio::test]
async fn test_delta_magnitude_nonzero() {
    let svc = make_service();
    let sem_prev = vec![0.0_f32; 32];
    let sem_curr = vec![1.0_f32; 32];
    let req = Request::new(DeltaRequest {
        sem_prev,
        sem_curr,
    });
    let resp = svc.delta(req).await.unwrap().into_inner();
    assert!(resp.magnitude > 0.0, "magnitude should be nonzero");
    // L2 norm of all-ones 32-dim: sqrt(32) ≈ 5.66
    assert!((resp.magnitude - 32.0_f32.sqrt()).abs() < 1e-4);
}

#[tokio::test]
async fn test_recall_empty_store() {
    let svc = make_service();
    let sem = vec![0.5_f32; 32];
    let unc = vec![0.2_f32; 32];
    let req = Request::new(RecallRequest {
        sem,
        unc,
        agent_id: "agent_nobody".to_string(),
        k: 5,
    });
    let resp = svc.recall(req).await.unwrap().into_inner();
    assert!(resp.results.is_empty());
}

#[tokio::test]
async fn test_recall_returns_top_k() {
    let svc = make_service();

    // First encode several items
    for i in 0..5 {
        let text = format!("message number {}", i);
        let enc_req = Request::new(EncodeRequest {
            text,
            agent_id: "recall_agent".to_string(),
            session_id: "s1".to_string(),
        });
        svc.encode(enc_req).await.unwrap();
    }

    // Recall top 3
    let sem = vec![0.5_f32; 32];
    let unc = vec![0.2_f32; 32];
    let req = Request::new(RecallRequest {
        sem,
        unc,
        agent_id: "recall_agent".to_string(),
        k: 3,
    });
    let resp = svc.recall(req).await.unwrap().into_inner();
    assert!(resp.results.len() <= 3);
    assert!(!resp.results.is_empty());
}

#[tokio::test]
async fn test_recall_ordered_by_dist() {
    let svc = make_service();

    // Encode two items: one matching urgente, one neutral
    let enc1 = Request::new(EncodeRequest {
        text: "urgente agora".to_string(),
        agent_id: "ord_agent".to_string(),
        session_id: "s1".to_string(),
    });
    svc.encode(enc1).await.unwrap();

    let enc2 = Request::new(EncodeRequest {
        text: "hello world".to_string(),
        agent_id: "ord_agent".to_string(),
        session_id: "s2".to_string(),
    });
    svc.encode(enc2).await.unwrap();

    // Query with urgente vector
    let (sem, unc) = leet_service::projection::project("urgente agora", "ord_agent");
    let req = Request::new(RecallRequest {
        sem,
        unc,
        agent_id: "ord_agent".to_string(),
        k: 5,
    });
    let resp = svc.recall(req).await.unwrap().into_inner();
    assert!(resp.results.len() >= 2);
    // Results should be ordered by distance (ascending)
    for i in 1..resp.results.len() {
        assert!(resp.results[i - 1].dist <= resp.results[i].dist);
    }
}

#[tokio::test]
async fn test_health_returns_ok() {
    let svc = make_service();
    let req = Request::new(HealthRequest {});
    let resp = svc.health(req).await.unwrap().into_inner();
    assert_eq!(resp.status, "ok");
    assert_eq!(resp.backend, "memory");
    assert!(resp.uptime >= 0);
}

#[tokio::test]
async fn test_memory_store_save_recall() {
    let store = MemoryStore::default();
    let sem = vec![0.9_f32; 32];
    let unc = vec![0.1_f32; 32];
    store.save("a1", "cog1", sem.clone(), unc.clone(), 1000).unwrap();

    let results = store.recall("a1", &sem, 5).unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].cogon_id, "cog1");
    assert!(results[0].dist < 0.01);
}

#[tokio::test]
async fn test_batch_processes_requests() {
    let engine = Arc::new(Engine::new());
    let queue = BatchQueue::new(engine);
    let (sem, unc) = queue.push("urgente".to_string(), "a1".to_string()).await;
    assert_eq!(sem.len(), 32);
    assert_eq!(unc.len(), 32);
    assert!(sem[22] > 0.9);
}

#[tokio::test]
async fn test_encode_batch_streaming() {
    // We test batch by encoding multiple items via the service
    let svc = make_service();
    let texts = ["alpha", "beta", "gamma", "urgente", "erro"];
    for text in &texts {
        let req = Request::new(EncodeRequest {
            text: text.to_string(),
            agent_id: "batch_agent".to_string(),
            session_id: "batch_sess".to_string(),
        });
        let resp = svc.encode(req).await.unwrap().into_inner();
        assert_eq!(resp.sem.len(), 32);
    }
}

#[tokio::test]
async fn test_encode_stores_in_recall() {
    let svc = make_service();

    // Encode
    let enc_req = Request::new(EncodeRequest {
        text: "urgente pipeline caiu".to_string(),
        agent_id: "store_agent".to_string(),
        session_id: "s1".to_string(),
    });
    let enc_resp = svc.encode(enc_req).await.unwrap().into_inner();
    let stored_cogon_id = enc_resp.cogon_id.clone();

    // Recall
    let sem = vec![0.5_f32; 32];
    let unc = vec![0.2_f32; 32];
    let recall_req = Request::new(RecallRequest {
        sem,
        unc,
        agent_id: "store_agent".to_string(),
        k: 5,
    });
    let recall_resp = svc.recall(recall_req).await.unwrap().into_inner();
    assert!(!recall_resp.results.is_empty());
    // The stored cogon should be in the results
    let found = recall_resp.results.iter().any(|r| r.cogon_id == stored_cogon_id);
    assert!(found, "stored cogon should appear in recall results");
}

#[tokio::test]
async fn test_delta_partial_vectors() {
    let svc = make_service();
    let mut sem_prev = vec![0.0_f32; 32];
    let mut sem_curr = vec![0.0_f32; 32];
    sem_curr[22] = 0.9; // C1_URGENCIA activated

    let req = Request::new(DeltaRequest { sem_prev, sem_curr });
    let resp = svc.delta(req).await.unwrap().into_inner();
    // patch[22] should be 0.9
    assert!((resp.patch[22] - 0.9).abs() < 1e-5);
    assert!(resp.magnitude > 0.0);
}

#[tokio::test]
async fn test_decode_with_urgencia_sem() {
    let svc = make_service();
    let mut sem = vec![0.5_f32; 32];
    sem[22] = 0.95; // C1_URGENCIA
    let unc = vec![0.1_f32; 32];
    let req = Request::new(DecodeRequest {
        sem,
        unc,
        lang: "en".to_string(),
    });
    let resp = svc.decode(req).await.unwrap().into_inner();
    assert!(!resp.text.is_empty());
    // Should mention axis 22
    assert!(resp.text.contains("22") || resp.text.contains("URGÊNCIA") || resp.text.contains("cogon"));
}

#[tokio::test]
async fn test_health_uptime_increases() {
    let svc = make_service();

    let req1 = Request::new(HealthRequest {});
    let resp1 = svc.health(req1).await.unwrap().into_inner();

    // Wait a tiny bit
    tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;

    let req2 = Request::new(HealthRequest {});
    let resp2 = svc.health(req2).await.unwrap().into_inner();

    assert!(resp2.uptime >= resp1.uptime);
}

#[tokio::test]
async fn test_encode_deploy_activates_processo() {
    let svc = make_service();
    let req = Request::new(EncodeRequest {
        text: "deploy do pipeline".to_string(),
        agent_id: "agent_d".to_string(),
        session_id: "s1".to_string(),
    });
    let resp = svc.encode(req).await.unwrap().into_inner();
    // Index 9 = A9_PROCESSO
    assert!(resp.sem[9] > 0.8, "A9_PROCESSO should be activated");
}

#[tokio::test]
async fn test_encode_rollback_activates_reversibilidade() {
    let svc = make_service();
    let req = Request::new(EncodeRequest {
        text: "reverter rollback desfazer".to_string(),
        agent_id: "agent_r".to_string(),
        session_id: "s1".to_string(),
    });
    let resp = svc.encode(req).await.unwrap().into_inner();
    // Index 17 = B5_REVERSIBILIDADE
    assert!(resp.sem[17] > 0.8, "B5_REVERSIBILIDADE should be activated");
    // Index 24 = C3_ACAO
    assert!(resp.sem[24] > 0.8, "C3_ACAO should be activated");
}

#[tokio::test]
async fn test_encode_tokens_saved_nonnegative() {
    let svc = make_service();
    let req = Request::new(EncodeRequest {
        text: "this is a very long text that should save some tokens compared to raw storage".to_string(),
        agent_id: "agent_t".to_string(),
        session_id: "s1".to_string(),
    });
    let resp = svc.encode(req).await.unwrap().into_inner();
    assert!(resp.tokens_saved >= 0);
}

#[tokio::test]
async fn test_recall_top_k_limit() {
    let svc = make_service();

    // Insert 10 items
    for i in 0..10 {
        let enc_req = Request::new(EncodeRequest {
            text: format!("item {}", i),
            agent_id: "limit_agent".to_string(),
            session_id: "s".to_string(),
        });
        svc.encode(enc_req).await.unwrap();
    }

    // Recall with k=3
    let sem = vec![0.5_f32; 32];
    let unc = vec![0.2_f32; 32];
    let req = Request::new(RecallRequest {
        sem,
        unc,
        agent_id: "limit_agent".to_string(),
        k: 3,
    });
    let resp = svc.recall(req).await.unwrap().into_inner();
    assert!(resp.results.len() <= 3);
}

#[tokio::test]
async fn test_decode_empty_sem() {
    let svc = make_service();
    let req = Request::new(DecodeRequest {
        sem: vec![],
        unc: vec![],
        lang: "en".to_string(),
    });
    // Should return something without panicking
    let resp = svc.decode(req).await.unwrap().into_inner();
    assert!(!resp.text.is_empty());
}
