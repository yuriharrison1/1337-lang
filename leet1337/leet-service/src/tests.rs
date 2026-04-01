/// Integration tests for leet-service components.
/// Covers: Config, Store, Engine/Projection, Wire format, batch logic.
#[cfg(test)]
mod tests {
    use crate::config::Config;
    use crate::store::{MemoryStore, CogonRecord, Store};
    use crate::projection::engine::Engine;
    use crate::projection::matrix::WMatrix;

    // ─── helpers ─────────────────────────────────────────────────────────────

    fn make_record(id: &str, val: f32) -> CogonRecord {
        CogonRecord {
            cogon_id: id.to_string(),
            sem:      [val; 32],
            unc:      [0.1; 32],
            stamp:    0,
            text_raw: None,
        }
    }

    fn default_config() -> Config {
        Config {
            port:            50051,
            backend:         "mock".to_string(),
            store_url:       "memory".to_string(),
            w_path:          None,
            batch_window_ms: 10,
            batch_max:       64,
            embed_model:     "mock".to_string(),
            embed_url:       None,
            embed_key:       None,
        }
    }

    // ─── Config tests ─────────────────────────────────────────────────────────

    #[test]
    fn test_config_defaults() {
        let cfg = default_config();
        assert_eq!(cfg.port, 50051);
        assert_eq!(cfg.backend, "mock");
        assert_eq!(cfg.store_url, "memory");
        assert_eq!(cfg.batch_window_ms, 10);
        assert_eq!(cfg.batch_max, 64);
        assert_eq!(cfg.embed_model, "mock");
        assert!(cfg.w_path.is_none());
        assert!(cfg.embed_url.is_none());
        assert!(cfg.embed_key.is_none());
    }

    #[test]
    fn test_config_from_env_uses_defaults_when_vars_absent() {
        // Remove vars to ensure defaults are used
        std::env::remove_var("LEET_PORT");
        std::env::remove_var("LEET_BACKEND");
        std::env::remove_var("LEET_STORE");
        let cfg = Config::from_env();
        assert_eq!(cfg.port, 50051);
        assert_eq!(cfg.backend, "simd");
        assert_eq!(cfg.store_url, "memory");
    }

    #[test]
    fn test_config_from_env_reads_vars() {
        std::env::set_var("LEET_PORT", "9000");
        std::env::set_var("LEET_BACKEND", "cpu");
        std::env::set_var("LEET_BATCH_MAX", "128");
        let cfg = Config::from_env();
        assert_eq!(cfg.port, 9000);
        assert_eq!(cfg.backend, "cpu");
        assert_eq!(cfg.batch_max, 128);
        // cleanup
        std::env::remove_var("LEET_PORT");
        std::env::remove_var("LEET_BACKEND");
        std::env::remove_var("LEET_BATCH_MAX");
    }

    // ─── MemoryStore tests ────────────────────────────────────────────────────

    #[tokio::test]
    async fn test_store_add_and_recall_single() {
        let store = MemoryStore::new();
        let rec = make_record("c001", 0.8);
        store.add("agent-a", rec.clone()).await.unwrap();

        let q_sem = [0.8f32; 32];
        let q_unc = [0.1f32; 32];
        let results = store.recall("agent-a", &q_sem, &q_unc, 5).await.unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].0.cogon_id, "c001");
    }

    #[tokio::test]
    async fn test_store_recall_top_k() {
        let store = MemoryStore::new();
        // Cosine distance measures direction, not magnitude.
        // Records with fewer aligned axes are further from the all-ones query.
        // c0: all 32 axes = 1.0  → identical direction → dist ≈ 0
        // c1: axes 0..16 = 1.0, rest = 0.0  → cos dist ≈ 1 - 1/√2 ≈ 0.29
        // c2: axes 0..8  = 1.0, rest = 0.0  → further
        // c3: axes 0..4  = 1.0, rest = 0.0  → further still
        // c4: axes 0..2  = 1.0, rest = 0.0  → furthest
        let make_sparse = |id: &str, n_hot: usize| -> CogonRecord {
            let mut sem = [0.0f32; 32];
            for i in 0..n_hot { sem[i] = 1.0; }
            CogonRecord { cogon_id: id.to_string(), sem, unc: [0.1; 32], stamp: 0, text_raw: None }
        };
        store.add("agent-b", make_sparse("c0", 32)).await.unwrap();
        store.add("agent-b", make_sparse("c1", 16)).await.unwrap();
        store.add("agent-b", make_sparse("c2",  8)).await.unwrap();
        store.add("agent-b", make_sparse("c3",  4)).await.unwrap();
        store.add("agent-b", make_sparse("c4",  2)).await.unwrap();

        let q_sem = [1.0f32; 32];
        let q_unc = [0.0f32; 32];
        let results = store.recall("agent-b", &q_sem, &q_unc, 3).await.unwrap();
        assert_eq!(results.len(), 3);
        // nearest should be c0 (identical direction → dist ≈ 0)
        assert_eq!(results[0].0.cogon_id, "c0");
        // distances must be non-decreasing
        for w in results.windows(2) {
            assert!(w[0].1 <= w[1].1);
        }
    }

    #[tokio::test]
    async fn test_store_empty_agent_returns_empty() {
        let store = MemoryStore::new();
        let q = [0.5f32; 32];
        let results = store.recall("nobody", &q, &q, 10).await.unwrap();
        assert!(results.is_empty());
    }

    #[tokio::test]
    async fn test_store_multiple_agents_isolated() {
        let store = MemoryStore::new();
        store.add("alice", make_record("a1", 0.9)).await.unwrap();
        store.add("bob",   make_record("b1", 0.1)).await.unwrap();

        let q = [0.9f32; 32];
        let unc = [0.0f32; 32];
        let alice_res = store.recall("alice", &q, &unc, 5).await.unwrap();
        let bob_res   = store.recall("bob",   &q, &unc, 5).await.unwrap();

        assert_eq!(alice_res.len(), 1);
        assert_eq!(bob_res.len(), 1);
        assert_eq!(alice_res[0].0.cogon_id, "a1");
        assert_eq!(bob_res[0].0.cogon_id,   "b1");
    }

    #[tokio::test]
    async fn test_store_recall_respects_k_limit() {
        let store = MemoryStore::new();
        for i in 0..10u32 {
            store.add("agent-k", make_record(&format!("r{i}"), 0.5)).await.unwrap();
        }
        let q = [0.5f32; 32];
        let results = store.recall("agent-k", &q, &q, 4).await.unwrap();
        assert_eq!(results.len(), 4, "recall must return exactly k records when k < total");
    }

    #[tokio::test]
    async fn test_store_session_delta_returns_empty_for_memory() {
        let store = MemoryStore::new();
        let results = store.get_session_delta("sess-123", 0).await.unwrap();
        assert!(results.is_empty());
    }

    // ─── WMatrix / Projection tests ───────────────────────────────────────────

    #[test]
    fn test_wmatrix_identity_init_shape() {
        let w = WMatrix::identity_init(32);
        // project should return 32 values
        let emb = vec![0.5f32; 32];
        let sem = w.project(&emb);
        assert_eq!(sem.len(), 32);
    }

    #[test]
    fn test_wmatrix_project_values_in_range() {
        let w = WMatrix::identity_init(64);
        let emb: Vec<f32> = (0..64).map(|i| i as f32 / 63.0).collect();
        let sem = w.project(&emb);
        assert_eq!(sem.len(), 32);
        for v in &sem {
            assert!(v.is_finite(), "projection value must be finite");
        }
    }

    #[test]
    fn test_wmatrix_batch_matches_serial() {
        let w = WMatrix::identity_init(32);
        let embs: Vec<Vec<f32>> = (0..4)
            .map(|i| vec![(i as f32) / 3.0; 32])
            .collect();

        let batch = w.project_batch(&embs);
        for (i, single_emb) in embs.iter().enumerate() {
            let serial = w.project(single_emb);
            for j in 0..32 {
                assert!((batch[i][j] - serial[j]).abs() < 1e-5,
                    "batch[{i}][{j}] = {} != serial = {}", batch[i][j], serial[j]);
            }
        }
    }

    // ─── Engine tests ─────────────────────────────────────────────────────────

    #[tokio::test]
    async fn test_engine_encode_returns_32_dims() {
        let cfg = default_config();
        let engine = Engine::new(&cfg).await.unwrap();
        let (sem, unc) = engine.encode("urgência crítica no sistema").await.unwrap();
        assert_eq!(sem.len(), 32);
        assert_eq!(unc.len(), 32);
        for v in sem.iter().chain(unc.iter()) {
            assert!(v.is_finite());
            assert!(*v >= 0.0 && *v <= 1.0, "value {v} out of [0,1]");
        }
    }

    #[tokio::test]
    async fn test_engine_encode_batch_consistent_with_single() {
        let cfg = default_config();
        let engine = Engine::new(&cfg).await.unwrap();
        let texts = vec![
            "amor é eterno".to_string(),
            "sistema instável".to_string(),
        ];

        let batch = engine.encode_batch(&texts).await.unwrap();
        assert_eq!(batch.len(), 2);

        for (i, text) in texts.iter().enumerate() {
            let (s_single, _) = engine.encode(text).await.unwrap();
            for j in 0..32 {
                assert!((batch[i].0[j] - s_single[j]).abs() < 1e-4,
                    "batch[{i}][{j}] mismatch vs single");
            }
        }
    }

    #[tokio::test]
    async fn test_engine_lru_cache_consistency() {
        let cfg = default_config();
        let engine = Engine::new(&cfg).await.unwrap();
        let text = "cached text for lru test";

        let (s1, u1) = engine.encode(text).await.unwrap();
        let (s2, u2) = engine.encode(text).await.unwrap(); // should hit cache

        assert_eq!(s1, s2);
        assert_eq!(u1, u2);
    }

    // ─── Wire format integration ──────────────────────────────────────────────

    #[test]
    fn test_unc_recompute_formula() {
        // unc[i] = (1 - |sem[i] - 0.5| * 2).clamp(0,1)
        let check = |sem: f32, expected_unc: f32| {
            let unc = (1.0 - (sem - 0.5).abs() * 2.0).clamp(0.0, 1.0);
            assert!((unc - expected_unc).abs() < 1e-6,
                "sem={sem} → unc={unc}, expected={expected_unc}");
        };
        check(0.5, 1.0); // centre → max uncertainty
        check(0.0, 0.0); // extreme → zero uncertainty
        check(1.0, 0.0); // extreme → zero uncertainty
        check(0.75, 0.5); // halfway → 0.5 uncertainty
    }
}
