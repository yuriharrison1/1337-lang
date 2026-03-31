use std::time::Duration;
use tokio::time::sleep;
use tonic::transport::Channel;

// Include proto types
mod proto {
    tonic::include_proto!("leet");
}

use proto::{
    leet_service_client::LeetServiceClient,
    DecodeRequest, DeltaRequest, EncodeRequest, HealthRequest, RecallRequest,
};

async fn start_server(port: u16) {
    let cfg = leet_service::config::Config {
        port,
        backend: "cpu".to_string(),
        store_url: "memory".to_string(),
        w_path: None,
        batch_window_ms: 5,
        batch_max: 64,
        embed_model: "mock".to_string(),
        embed_url: None,
        embed_key: None,
    };

    let store = leet_service::store::build(&cfg).await.unwrap();
    let engine = leet_service::projection::Engine::new(&cfg).await.unwrap();

    tokio::spawn(leet_service::server::run(cfg, engine, store));
    sleep(Duration::from_millis(100)).await;
}

async fn client(port: u16) -> LeetServiceClient<Channel> {
    let endpoint = format!("http://127.0.0.1:{}", port);
    LeetServiceClient::connect(endpoint).await.unwrap()
}

#[tokio::test]
async fn test_encode() {
    let port = 50100;
    start_server(port).await;
    let mut c = client(port).await;

    let resp = c
        .encode(EncodeRequest {
            text: "Hello semantic world".to_string(),
            agent_id: "test-agent".to_string(),
            session_id: "s1".to_string(),
        })
        .await
        .unwrap()
        .into_inner();

    assert_eq!(resp.sem.len(), 32, "sem must have 32 elements");
    assert_eq!(resp.unc.len(), 32, "unc must have 32 elements");
    for &v in &resp.sem {
        assert!(v >= 0.0 && v <= 1.0, "sem value {} out of [0,1]", v);
    }
    for &v in &resp.unc {
        assert!(v >= 0.0 && v <= 1.0, "unc value {} out of [0,1]", v);
    }
    assert!(!resp.cogon_id.is_empty());
    assert!(resp.stamp > 0);
}

#[tokio::test]
async fn test_encode_batch() {
    let port = 50101;
    start_server(port).await;
    let mut c = client(port).await;

    let requests: Vec<EncodeRequest> = vec!["alpha", "beta", "gamma", "delta", "epsilon"]
        .into_iter()
        .map(|t| EncodeRequest {
            text: t.to_string(),
            agent_id: "batch-agent".to_string(),
            session_id: "s2".to_string(),
        })
        .collect();
    let expected = requests.len();
    let req_stream = futures_util::stream::iter(requests);

    let mut stream = c.encode_batch(req_stream).await.unwrap().into_inner();
    let mut count = 0usize;
    while let Some(resp) = stream.message().await.unwrap() {
        assert_eq!(resp.sem.len(), 32);
        count += 1;
    }
    assert_eq!(count, expected, "expected {} responses", expected);
}

#[tokio::test]
async fn test_delta() {
    let port = 50102;
    start_server(port).await;
    let mut c = client(port).await;

    // Encode two different texts
    let r1 = c
        .encode(EncodeRequest {
            text: "first concept".to_string(),
            agent_id: String::new(),
            session_id: String::new(),
        })
        .await
        .unwrap()
        .into_inner();

    let r2 = c
        .encode(EncodeRequest {
            text: "second concept completely different".to_string(),
            agent_id: String::new(),
            session_id: String::new(),
        })
        .await
        .unwrap()
        .into_inner();

    let delta = c
        .delta(DeltaRequest {
            sem_prev: r1.sem.clone(),
            sem_curr: r2.sem.clone(),
        })
        .await
        .unwrap()
        .into_inner();

    assert_eq!(delta.patch.len(), 32);
    assert!(delta.magnitude >= 0.0);
    // Patch should equal sem_curr - sem_prev
    for i in 0..32 {
        let expected = r2.sem[i] - r1.sem[i];
        assert!(
            (delta.patch[i] - expected).abs() < 1e-5,
            "patch[{}] mismatch",
            i
        );
    }
}

#[tokio::test]
async fn test_health() {
    let port = 50103;
    start_server(port).await;
    let mut c = client(port).await;

    let resp = c
        .health(HealthRequest {})
        .await
        .unwrap()
        .into_inner();

    assert_eq!(resp.status, "ok");
    assert!(!resp.backend.is_empty());
    assert!(resp.uptime >= 0);
}

#[tokio::test]
async fn test_recall() {
    let port = 50104;
    start_server(port).await;
    let mut c = client(port).await;

    // Add 3 cogons via encode
    for text in &["concept A", "concept B", "concept C"] {
        c.encode(EncodeRequest {
            text: text.to_string(),
            agent_id: "recall-agent".to_string(),
            session_id: "s3".to_string(),
        })
        .await
        .unwrap();
    }

    // Give store time to persist
    sleep(Duration::from_millis(50)).await;

    // Encode a query
    let query = c
        .encode(EncodeRequest {
            text: "concept A".to_string(),
            agent_id: String::new(),
            session_id: String::new(),
        })
        .await
        .unwrap()
        .into_inner();

    let recall_resp = c
        .recall(RecallRequest {
            sem: query.sem,
            unc: query.unc,
            agent_id: "recall-agent".to_string(),
            k: 2,
        })
        .await
        .unwrap()
        .into_inner();

    assert!(
        recall_resp.results.len() <= 2,
        "recall returned more than k=2 results"
    );
    assert!(
        !recall_resp.results.is_empty(),
        "recall returned no results after adding 3 cogons"
    );
    for r in &recall_resp.results {
        assert_eq!(r.sem.len(), 32);
        assert!(r.dist >= 0.0);
    }
}
