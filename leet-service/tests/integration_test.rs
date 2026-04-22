//! Integration tests for leet-service.
//! Tests instantiate LeetServiceImpl directly without binding a TCP port.

use std::sync::Arc;
use tonic::Request;

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
    assert!(resp.unc.is_empty()); // v0.5.1: unc not used at runtime
    assert!(!resp.cogon_id.is_empty());
}

#[tokio::test]
async fn test_encode_urgente_activates_g8() {
    let svc = make_service();
    let req = Request::new(EncodeRequest {
        text: "urgente agora".to_string(),
        agent_id: "agent1".to_string(),
        session_id: "sess1".to_string(),
    });
    let resp = svc.encode(req).await.unwrap().into_inner();
    assert!(resp.sem[23] > 0.9, "G8_URGENCIA should be activated, got {}", resp.sem[23]);
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
    assert!(resp.sem[26] > 0.8, "P3_ANOMALIA should be activated");
    assert!(resp.sem[8] > 0.8, "D1_ESTADO should be activated");
}

#[tokio::test]
async fn test_decode_returns_string() {
    let svc = make_service();
    let req = Request::new(DecodeRequest {
        sem: vec![0.5_f32; 32],
        unc: vec![], // ignored in v0.5.1
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
    let req = Request::new(DeltaRequest {
        sem_prev: vec![0.0_f32; 32],
        sem_curr: vec![1.0_f32; 32],
    });
    let resp = svc.delta(req).await.unwrap().into_inner();
    assert!(resp.magnitude > 0.0, "magnitude should be nonzero");
    assert!((resp.magnitude - 32.0_f32.sqrt()).abs() < 1e-4);
}

#[tokio::test]
async fn test_recall_empty_store() {
    let svc = make_service();
    let req = Request::new(RecallRequest {
        sem: vec![0.5_f32; 32],
        unc: vec![],
        agent_id: "agent_nobody".to_string(),
        k: 5,
    });
    let resp = svc.recall(req).await.unwrap().into_inner();
    assert!(resp.results.is_empty());
}

#[tokio::test]
async fn test_recall_returns_top_k() {
    let svc = make_service();

    for i in 0..5 {
        let enc_req = Request::new(EncodeRequest {
            text: format!("message number {}", i),
            agent_id: "recall_agent".to_string(),
            session_id: "s1".to_string(),
        });
        svc.encode(enc_req).await.unwrap();
    }

    let req = Request::new(RecallRequest {
        sem: vec![0.5_f32; 32],
        unc: vec![],
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

    svc.encode(Request::new(EncodeRequest {
        text: "urgente agora".to_string(),
        agent_id: "ord_agent".to_string(),
        session_id: "s1".to_string(),
    })).await.unwrap();

    svc.encode(Request::new(EncodeRequest {
        text: "hello world".to_string(),
        agent_id: "ord_agent".to_string(),
        session_id: "s2".to_string(),
    })).await.unwrap();

    let sem = leet_service::projection::project("urgente agora", "ord_agent");
    let req = Request::new(RecallRequest {
        sem,
        unc: vec![],
        agent_id: "ord_agent".to_string(),
        k: 5,
    });
    let resp = svc.recall(req).await.unwrap().into_inner();
    assert!(resp.results.len() >= 2);
    for i in 1..resp.results.len() {
        assert!(resp.results[i - 1].dist <= resp.results[i].dist);
    }
}

#[tokio::test]
async fn test_health_returns_ok() {
    let svc = make_service();
    let resp = svc.health(Request::new(HealthRequest {})).await.unwrap().into_inner();
    assert_eq!(resp.status, "ok");
    assert_eq!(resp.backend, "memory");
    assert!(resp.uptime >= 0);
}

#[tokio::test]
async fn test_memory_store_save_recall() {
    let store = MemoryStore::default();
    let sem = vec![0.9_f32; 32];
    store.save("a1", "cog1", sem.clone(), 1000).unwrap();

    let results = store.recall("a1", &sem, 5).unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].cogon_id, "cog1");
    assert!(results[0].dist < 0.01);
}

#[tokio::test]
async fn test_batch_processes_requests() {
    let engine = Arc::new(Engine::new());
    let queue = BatchQueue::new(engine);
    let sem = queue.push("urgente".to_string(), "a1".to_string()).await;
    assert_eq!(sem.len(), 32);
    assert!(sem[23] > 0.9, "G8_URGENCIA should be activated");
}

#[tokio::test]
async fn test_encode_batch_streaming() {
    let svc = make_service();
    let texts = ["alpha", "beta", "gamma", "urgente", "erro"];
    for text in &texts {
        let resp = svc.encode(Request::new(EncodeRequest {
            text: text.to_string(),
            agent_id: "batch_agent".to_string(),
            session_id: "batch_sess".to_string(),
        })).await.unwrap().into_inner();
        assert_eq!(resp.sem.len(), 32);
    }
}

#[tokio::test]
async fn test_encode_stores_in_recall() {
    let svc = make_service();

    let enc_resp = svc.encode(Request::new(EncodeRequest {
        text: "urgente pipeline caiu".to_string(),
        agent_id: "store_agent".to_string(),
        session_id: "s1".to_string(),
    })).await.unwrap().into_inner();
    let stored_cogon_id = enc_resp.cogon_id.clone();

    let recall_resp = svc.recall(Request::new(RecallRequest {
        sem: vec![0.5_f32; 32],
        unc: vec![],
        agent_id: "store_agent".to_string(),
        k: 5,
    })).await.unwrap().into_inner();
    assert!(!recall_resp.results.is_empty());
    let found = recall_resp.results.iter().any(|r| r.cogon_id == stored_cogon_id);
    assert!(found, "stored cogon should appear in recall results");
}

#[tokio::test]
async fn test_delta_partial_vectors() {
    let svc = make_service();
    let sem_prev = vec![0.0_f32; 32];
    let mut sem_curr = vec![0.0_f32; 32];
    sem_curr[23] = 0.9; // G8_URGENCIA

    let resp = svc.delta(Request::new(DeltaRequest { sem_prev, sem_curr })).await.unwrap().into_inner();
    assert!((resp.patch[23] - 0.9).abs() < 1e-5);
    assert!(resp.magnitude > 0.0);
}

#[tokio::test]
async fn test_decode_with_urgencia_sem() {
    let svc = make_service();
    let mut sem = vec![0.5_f32; 32];
    sem[23] = 0.95; // G8_URGENCIA
    let req = Request::new(DecodeRequest {
        sem,
        unc: vec![],
        lang: "en".to_string(),
    });
    let resp = svc.decode(req).await.unwrap().into_inner();
    assert!(!resp.text.is_empty());
    assert!(resp.text.contains("23") || resp.text.contains("URGENCIA") || resp.text.contains("cogon"));
}

#[tokio::test]
async fn test_health_uptime_increases() {
    let svc = make_service();

    let resp1 = svc.health(Request::new(HealthRequest {})).await.unwrap().into_inner();
    tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;
    let resp2 = svc.health(Request::new(HealthRequest {})).await.unwrap().into_inner();

    assert!(resp2.uptime >= resp1.uptime);
}

#[tokio::test]
async fn test_encode_deploy_activates_processo() {
    let svc = make_service();
    let resp = svc.encode(Request::new(EncodeRequest {
        text: "deploy do pipeline".to_string(),
        agent_id: "agent_d".to_string(),
        session_id: "s1".to_string(),
    })).await.unwrap().into_inner();
    assert!(resp.sem[9] > 0.8, "D2_PROCESSO should be activated");
}

#[tokio::test]
async fn test_encode_rollback_activates_reversibilidade() {
    let svc = make_service();
    let resp = svc.encode(Request::new(EncodeRequest {
        text: "reverter rollback desfazer".to_string(),
        agent_id: "agent_r".to_string(),
        session_id: "s1".to_string(),
    })).await.unwrap().into_inner();
    assert!(resp.sem[19] > 0.8, "G4_REVERSIBILIDADE should be activated");
    assert!(resp.sem[30] > 0.8, "P7_ACAO should be activated");
}

#[tokio::test]
async fn test_encode_tokens_saved_nonnegative() {
    let svc = make_service();
    let resp = svc.encode(Request::new(EncodeRequest {
        text: "this is a very long text that should save some tokens compared to raw storage".to_string(),
        agent_id: "agent_t".to_string(),
        session_id: "s1".to_string(),
    })).await.unwrap().into_inner();
    assert!(resp.tokens_saved >= 0);
}

#[tokio::test]
async fn test_recall_top_k_limit() {
    let svc = make_service();

    for i in 0..10 {
        svc.encode(Request::new(EncodeRequest {
            text: format!("item {}", i),
            agent_id: "limit_agent".to_string(),
            session_id: "s".to_string(),
        })).await.unwrap();
    }

    let resp = svc.recall(Request::new(RecallRequest {
        sem: vec![0.5_f32; 32],
        unc: vec![],
        agent_id: "limit_agent".to_string(),
        k: 3,
    })).await.unwrap().into_inner();
    assert!(resp.results.len() <= 3);
}

#[tokio::test]
async fn test_decode_empty_sem() {
    let svc = make_service();
    let resp = svc.decode(Request::new(DecodeRequest {
        sem: vec![],
        unc: vec![],
        lang: "en".to_string(),
    })).await.unwrap().into_inner();
    assert!(!resp.text.is_empty());
}
