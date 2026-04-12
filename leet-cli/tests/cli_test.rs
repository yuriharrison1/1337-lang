//! Tests for leet-cli commands.

use leet_bridge::{BridgeProjector, MockProjector};
use leet_core::axes::CANONICAL_AXES;
use leet_core::types::Cogon;

// ─── Encode render tests ──────────────────────────────────────────────────────

fn render_bar(name: &str, value: f32, width: usize) -> String {
    let filled = (value * width as f32).round() as usize;
    let empty = width.saturating_sub(filled);
    format!(
        "  {:20} [{}{}] {:.2}",
        name,
        "█".repeat(filled),
        "░".repeat(empty),
        value
    )
}

#[test]
fn test_render_bar_full() {
    let bar = render_bar("AXIS", 1.0, 10);
    assert!(bar.contains("██████████"));
    assert!(!bar.contains("░"));
}

#[test]
fn test_render_bar_empty() {
    let bar = render_bar("AXIS", 0.0, 10);
    assert!(bar.contains("░░░░░░░░░░"));
    assert!(!bar.contains("█"));
}

#[test]
fn test_render_bar_half() {
    let bar = render_bar("AXIS", 0.5, 10);
    assert!(bar.contains("█████"));
    assert!(bar.contains("░░░░░"));
}

#[test]
fn test_render_bar_name_present() {
    let bar = render_bar("MY_AXIS", 0.6, 10);
    assert!(bar.contains("MY_AXIS"));
}

#[test]
fn test_render_bar_value_formatted() {
    let bar = render_bar("X", 0.75, 10);
    assert!(bar.contains("0.75"));
}

// ─── Axes tests ───────────────────────────────────────────────────────────────

#[test]
fn test_canonical_axes_count() {
    assert_eq!(CANONICAL_AXES.len(), 32);
}

#[test]
fn test_axes_first_is_a0_via() {
    assert_eq!(CANONICAL_AXES[0].code, "A0");
    assert_eq!(CANONICAL_AXES[0].name, "VIA");
}

#[test]
fn test_axes_last_is_c10() {
    assert_eq!(CANONICAL_AXES[31].code, "C10");
}

#[test]
fn test_axes_c1_urgencia_at_22() {
    assert_eq!(CANONICAL_AXES[22].code, "C1");
    assert_eq!(CANONICAL_AXES[22].name, "URGÊNCIA");
}

// ─── Encode projection tests ──────────────────────────────────────────────────

#[test]
fn test_encode_urgente_activates_c1() {
    let proj = MockProjector;
    let cogon = proj.project("urgente agora").unwrap();
    assert!(cogon.sem[22] > 0.9, "C1_URGENCIA should be activated");
}

#[test]
fn test_encode_erro_activates_anomalia_and_estado() {
    let proj = MockProjector;
    let cogon = proj.project("erro no sistema").unwrap();
    assert!(cogon.sem[26] > 0.8); // C5_ANOMALIA
    assert!(cogon.sem[8] > 0.8);  // A8_ESTADO
}

#[test]
fn test_encode_neutral_text_baseline() {
    let proj = MockProjector;
    let cogon = proj.project("").unwrap();
    assert!(cogon.sem.iter().all(|&v| (v - 0.5).abs() < 0.01));
}

#[test]
fn test_encode_deploy_activates_processo() {
    let proj = MockProjector;
    let cogon = proj.project("deploy do pipeline").unwrap();
    assert!(cogon.sem[9] > 0.8); // A9_PROCESSO
}

// ─── Zero tests ───────────────────────────────────────────────────────────────

#[test]
fn test_zero_sem_all_ones() {
    let z = Cogon::zero();
    assert!(z.sem.iter().all(|&v| v == 1.0));
}

#[test]
fn test_zero_unc_all_zeros() {
    let z = Cogon::zero();
    assert!(z.unc.iter().all(|&v| v == 0.0));
}

#[test]
fn test_zero_is_zero() {
    let z = Cogon::zero();
    assert!(z.is_zero());
}

// ─── Version tests ────────────────────────────────────────────────────────────

#[test]
fn test_version_string() {
    assert_eq!(leet_core::VERSION, "0.4.0");
    assert_eq!(leet_core::SPEC_VERSION, "0.4");
}

// ─── Validate tests ───────────────────────────────────────────────────────────

#[test]
fn test_validate_valid_msg() {
    use leet_core::types::*;
    use leet_core::validate::validate;
    use uuid::Uuid;

    let msg = Msg1337 {
        id: Uuid::new_v4(),
        sender: Uuid::new_v4(),
        receiver: Receiver::Agent(Uuid::new_v4()),
        intent: Intent::Assert,
        ref_hash: None,
        patch: None,
        payload: Payload::Cogon(Cogon {
            id: Uuid::new_v4(),
            sem: [0.5_f32; 32],
            unc: [0.1_f32; 32],
            stamp: 1000,
            raw: None,
        }),
        c5: C5Block {
            zone_fixed: [0.5_f32; 32],
            zone_emergent: std::collections::HashMap::new(),
            schema_ver: "0.4.0".to_string(),
            align_hash: [0u8; 32],
        },
        surface: SurfaceBlock {
            human_required: false,
            urgency: None,
            reconstruct_depth: 1,
            lang: "pt".to_string(),
        },
    };
    assert!(validate(&msg).is_ok());
}

// ─── Bench percentile tests ───────────────────────────────────────────────────

#[test]
fn test_bench_percentile_ordering() {
    use std::time::Duration;
    let mut durations: Vec<Duration> = (1..=100).map(|i| Duration::from_nanos(i)).collect();
    durations.sort();
    let p50_idx = ((durations.len() as f64 - 1.0) * 0.50).round() as usize;
    let p99_idx = ((durations.len() as f64 - 1.0) * 0.99).round() as usize;
    assert!(durations[p50_idx] < durations[p99_idx]);
}

// ─── Health tests ─────────────────────────────────────────────────────────────

#[test]
fn test_health_port_default() {
    let url = "localhost";
    let addr = if url.contains(':') {
        url.to_string()
    } else {
        format!("{}:50051", url)
    };
    assert_eq!(addr, "localhost:50051");
}

#[test]
fn test_health_explicit_port() {
    let url = "127.0.0.1:12345";
    let addr = if url.contains(':') {
        url.to_string()
    } else {
        format!("{}:50051", url)
    };
    assert_eq!(addr, "127.0.0.1:12345");
}
