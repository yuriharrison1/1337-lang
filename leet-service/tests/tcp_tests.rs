//! Integration tests for the v0.5.1 TCP server + agent client.

use std::sync::Arc;
use std::time::Duration;
use tokio::time::timeout;
use uuid::Uuid;

use leet_service::{
    agent_client::AgentClient,
    tcp_server::LeetServer,
};

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Start a server on a random port, return (server, port).
async fn start_test_server() -> (Arc<LeetServer>, u16) {
    let server = LeetServer::new();
    let addr = server
        .clone()
        .start_background("127.0.0.1:0")
        .await
        .expect("failed to start test server");
    let port = addr.port();
    (server, port)
}

/// Connect a named agent and complete handshake.
async fn connect_agent(name: &str, role: &str, port: u16) -> AgentClient {
    let addr = format!("127.0.0.1:{}", port);
    let mut client = AgentClient::new(Uuid::new_v4(), name, role);
    timeout(Duration::from_secs(5), client.connect(&addr))
        .await
        .expect("connect timed out")
        .expect("handshake failed");
    client
}

// ── TASK 8 required tests ─────────────────────────────────────────────────────

/// Server accepts connection and C5 handshake completes successfully.
#[tokio::test]
async fn test_handshake() {
    let (server, port) = start_test_server().await;

    let client = connect_agent("ATLAS", "Strategic planner", port).await;

    assert!(client.is_connected(), "client should be connected after handshake");
    assert!(!client.id.is_nil(), "server should assign a non-nil UUID");

    // Give server a moment to register the agent
    tokio::time::sleep(Duration::from_millis(50)).await;
    assert_eq!(server.agent_count().await, 1, "server should have 1 agent");

    let names = server.agent_names().await;
    assert!(names.contains(&"ATLAS".to_string()), "ATLAS should be registered");
}

/// Message from one agent is broadcast and received by others.
#[tokio::test]
async fn test_broadcast() {
    let (server, port) = start_test_server().await;

    // Connect sender and receiver
    let mut sender = connect_agent("FORGE", "Builder", port).await;
    let mut receiver = connect_agent("PULSE", "Monitor", port).await;

    // Wait for both to register
    tokio::time::sleep(Duration::from_millis(100)).await;
    assert_eq!(server.agent_count().await, 2);

    // Sender broadcasts a message
    sender.send_nl("sistema está operacional").await.expect("send_nl failed");

    // Receiver should get the message within 3s
    let msg = timeout(Duration::from_secs(3), receiver.recv())
        .await
        .expect("recv timed out")
        .expect("recv error")
        .expect("connection closed");

    // Verify it has content
    use leet_core::types::Payload;
    if let Payload::Cogon(cogon) = &msg.payload {
        // Should have some activated axes
        assert!(cogon.sem.iter().any(|&v| v > 0.5), "sem should have some activation");
    }
}

/// NL→COGON translation roundtrip preserves semantic meaning.
#[tokio::test]
async fn test_translation_roundtrip() {
    use leet_bridge::nl_translator::{nl_to_cogon, cogon_to_nl};

    let text = "sistema crítico precisa de ação imediata";
    let cogon = nl_to_cogon(text, "pt");

    // P3 anomaly should be activated
    assert!(cogon.sem[leet_bridge::nl_translator::P3_ANOMALIA] > 0.7);
    // P7 action should be activated
    assert!(cogon.sem[leet_bridge::nl_translator::P7_ACAO] > 0.7);

    // Reconstruct NL and verify key concepts survive
    let reconstructed = cogon_to_nl(&cogon, "pt");
    let lower = reconstructed.to_lowercase();
    let has_key = lower.contains("anomalia") || lower.contains("urgente") || lower.contains("ação");
    assert!(has_key, "roundtrip should preserve key concepts, got: {:?}", reconstructed);

    // Now test through server: send NL, receive broadcast, verify cogon
    let (_, port) = start_test_server().await;
    let mut sender = connect_agent("ECHO", "Relay", port).await;
    let mut watcher = connect_agent("DRIFT", "Anomaly detector", port).await;
    tokio::time::sleep(Duration::from_millis(100)).await;

    sender.send_nl(text).await.expect("send failed");

    let received = timeout(Duration::from_secs(3), watcher.recv())
        .await
        .expect("recv timed out")
        .expect("recv error")
        .expect("closed");

    if let leet_core::types::Payload::Cogon(c) = received.payload {
        assert!(c.sem[leet_bridge::nl_translator::P3_ANOMALIA] > 0.5,
            "P3_ANOMALIA should survive roundtrip through server");
    } else {
        panic!("expected Cogon payload");
    }
}

/// Metrics increment as messages flow through the server.
#[tokio::test]
async fn test_metrics_accumulation() {
    let (server, port) = start_test_server().await;

    let mut sender = connect_agent("VORTEX", "Data pipeline", port).await;
    let mut _watcher = connect_agent("NEXUS", "Network", port).await;
    tokio::time::sleep(Duration::from_millis(100)).await;

    // Confirm zero at start
    {
        let m = server.metrics.lock().await;
        assert_eq!(m.total_messages, 0);
    }

    // Send a few messages
    for i in 0..3 {
        sender.send_nl(&format!("mensagem número {}", i)).await.expect("send failed");
    }
    tokio::time::sleep(Duration::from_millis(200)).await;

    // Metrics should have incremented
    {
        let m = server.metrics.lock().await;
        assert!(m.total_messages >= 3, "total_messages should be ≥ 3, got {}", m.total_messages);
        assert!(m.total_cogon_bytes > 0, "total_cogon_bytes should be > 0");
    }
}

/// Five agents connect simultaneously; all complete handshake.
#[tokio::test]
async fn test_concurrent_agents() {
    let (server, port) = start_test_server().await;

    let agent_names = ["ATLAS", "CIPHER", "FORGE", "NEXUS", "ORACLE"];

    // Spawn all connections concurrently
    let tasks: Vec<_> = agent_names
        .iter()
        .map(|name| {
            let n = name.to_string();
            let p = port;
            tokio::spawn(async move {
                connect_agent(&n, "test agent", p).await
            })
        })
        .collect();

    // Wait for all to complete
    let mut clients = Vec::new();
    for task in tasks {
        let client = timeout(Duration::from_secs(10), task)
            .await
            .expect("task timed out")
            .expect("task panicked");
        assert!(client.is_connected(), "all agents should connect successfully");
        clients.push(client);
    }

    // Give server time to register all
    tokio::time::sleep(Duration::from_millis(200)).await;

    let count = server.agent_count().await;
    assert_eq!(count, 5, "all 5 agents should be registered, got {}", count);

    let names = server.agent_names().await;
    for expected in &agent_names {
        assert!(
            names.contains(&expected.to_string()),
            "agent {} should be in server registry",
            expected
        );
    }

    // Check peak metrics
    let m = server.metrics.lock().await;
    assert!(m.agents_peak >= 5, "peak should be ≥ 5, got {}", m.agents_peak);
}

// ── Additional coverage ───────────────────────────────────────────────────────

/// Agent disconnection is handled gracefully.
#[tokio::test]
async fn test_agent_disconnect() {
    let (server, port) = start_test_server().await;

    {
        // Connect then drop (disconnect)
        let _client = connect_agent("SPARK", "Creative", port).await;
        tokio::time::sleep(Duration::from_millis(100)).await;
        assert_eq!(server.agent_count().await, 1);
    } // client dropped here

    // Server should clean up after EOF
    tokio::time::sleep(Duration::from_millis(200)).await;
    assert_eq!(server.agent_count().await, 0, "disconnected agent should be removed");
}

/// COGON_ZERO anchor assertions are valid.
#[tokio::test]
async fn test_anchor_cogons() {
    use leet_core::protocol::{all_anchors, ANCHOR_NAMES};

    let anchors = all_anchors();
    assert_eq!(anchors.len(), 5);

    for (i, cogon) in anchors.iter().enumerate() {
        // All anchor values in range
        for &v in cogon.sem.iter().chain(cogon.unc.iter()) {
            assert!(v >= 0.0 && v <= 1.0, "anchor {} value out of range: {}", i, v);
        }
        // Each anchor has the correct label in raw
        let raw = cogon.raw.as_ref().expect("anchor must have raw");
        let label = raw.content.as_str().expect("raw content must be string");
        assert_eq!(label, ANCHOR_NAMES[i]);
    }

    // Presence anchor has high S1_ESSENCIA
    assert!(anchors[0].sem[0] > 0.8, "presence: S1 should be > 0.8");
    // Change anchor has high S3_VIBRACAO
    assert!(anchors[2].sem[2] > 0.8, "change: S3 should be > 0.8");
}

/// Wrong align_hash is rejected by server.
#[tokio::test]
async fn test_bad_align_hash_rejected() {
    use leet_service::tcp_server::WireMsg;
    use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
    use tokio::net::TcpStream;

    let (_, port) = start_test_server().await;
    let addr = format!("127.0.0.1:{}", port);

    let stream = TcpStream::connect(&addr).await.unwrap();
    let (r, mut w) = stream.into_split();
    let mut reader = BufReader::new(r);

    // Send Register
    let reg = WireMsg::Register { name: "BAD_AGENT".to_string(), role: "test".to_string() };
    w.write_all((serde_json::to_string(&reg).unwrap() + "\n").as_bytes()).await.unwrap();

    // Read Registered
    let mut line = String::new();
    reader.read_line(&mut line).await.unwrap();
    let msg: WireMsg = serde_json::from_str(line.trim()).unwrap();
    assert!(matches!(msg, WireMsg::Registered { .. }));

    // Send WRONG hash
    let bad_align = WireMsg::Align { hash: "deadbeef".repeat(8) };
    w.write_all((serde_json::to_string(&bad_align).unwrap() + "\n").as_bytes()).await.unwrap();

    // Should receive Error, not Ready
    line.clear();
    reader.read_line(&mut line).await.unwrap();
    let response: WireMsg = serde_json::from_str(line.trim()).unwrap();
    assert!(
        matches!(response, WireMsg::Error { .. }),
        "bad hash should be rejected, got: {:?}", response
    );
}
