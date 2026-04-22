//! Integration tests for nl_translator — NL↔COGON round-trip verification.

use leet_bridge::nl_translator::{
    cogon_to_nl, infer_intent, nl_to_cogon,
    G8_URGENCIA, P3_ANOMALIA, P7_ACAO,
};
use leet_core::{Cogon, Intent};

// ── TASK 5 required tests ─────────────────────────────────────────────────────

/// "Qual é o status do sistema?" — intent Query, mild urgency from "status".
#[test]
fn test_nl_to_cogon_pt() {
    let text = "Qual é o status do sistema?";
    let cogon = nl_to_cogon(text, "pt");
    let intent = infer_intent(text);

    assert!(
        matches!(intent, Intent::Query),
        "expected Intent::Query, got {:?}",
        intent
    );

    assert!(
        cogon.sem[G8_URGENCIA] > 0.5,
        "expected G8_URGENCIA > 0.5, got {}",
        cogon.sem[G8_URGENCIA]
    );

    // Vectors must stay in [0, 1]
    for v in cogon.sem.iter() {
        assert!(*v >= 0.0 && *v <= 1.0, "out-of-range value: {}", v);
    }
}

/// "The system is critical" — P3_ANOMALIA > 0.7.
#[test]
fn test_nl_to_cogon_en() {
    let text = "The system is critical";
    let cogon = nl_to_cogon(text, "en");

    assert!(
        cogon.sem[P3_ANOMALIA] > 0.7,
        "expected P3_ANOMALIA > 0.7, got {}",
        cogon.sem[P3_ANOMALIA]
    );

    for v in cogon.sem.iter() {
        assert!(*v >= 0.0 && *v <= 1.0, "out-of-range value: {}", v);
    }
}

/// COGON with G8=0.9, P7=0.8 → NL (PT) contains "urgente" or "ação".
#[test]
fn test_cogon_to_nl() {
    let mut cogon = Cogon::zero();
    cogon.id = uuid::Uuid::new_v4();
    cogon.sem = [0.3_f32; 32];
    cogon.stamp = 1_000_000;

    cogon.sem[G8_URGENCIA] = 0.9;
    cogon.sem[P7_ACAO] = 0.8;

    let nl = cogon_to_nl(&cogon, "pt");
    let nl_lower = nl.to_lowercase();

    let has_urgency_word = nl_lower.contains("urgente") || nl_lower.contains("urgent");
    let has_action_word = nl_lower.contains("ação") || nl_lower.contains("acao") || nl_lower.contains("action");

    assert!(
        has_urgency_word || has_action_word,
        "expected 'urgente' or 'ação' in: {:?}",
        nl
    );
}

/// COGON_ZERO satisfies is_zero() and has correct v0.5.1 values.
#[test]
fn test_cogon_zero() {
    let z = Cogon::zero();
    assert!(z.is_zero(), "Cogon::zero() must satisfy is_zero()");
    assert_eq!(z.stamp, 0);
    assert!(z.raw.is_none());
    // v0.5.1: S1_ESSENCIA = 1.0, not all-ones
    assert_eq!(z.sem[0], 1.0, "S1_ESSENCIA must be 1.0");
}

/// NL → COGON → NL roundtrip preserves intent and dominant axes.
#[test]
fn test_roundtrip() {
    let text = "Sistema crítico! Ação imediata necessária!";

    let cogon = nl_to_cogon(text, "pt");
    let intent = infer_intent(text);

    assert!(
        matches!(intent, Intent::Anomaly),
        "expected Intent::Anomaly, got {:?}",
        intent
    );

    assert!(
        cogon.sem[P3_ANOMALIA] > 0.7,
        "P3_ANOMALIA expected > 0.7, got {}",
        cogon.sem[P3_ANOMALIA]
    );

    assert!(
        cogon.sem[P7_ACAO] > 0.7,
        "P7_ACAO expected > 0.7, got {}",
        cogon.sem[P7_ACAO]
    );

    assert!(
        cogon.sem[G8_URGENCIA] > 0.7,
        "G8_URGENCIA expected > 0.7, got {}",
        cogon.sem[G8_URGENCIA]
    );

    let nl = cogon_to_nl(&cogon, "pt");
    let nl_lower = nl.to_lowercase();
    let has_key_concept = nl_lower.contains("urgente")
        || nl_lower.contains("urgent")
        || nl_lower.contains("anomalia")
        || nl_lower.contains("ação")
        || nl_lower.contains("acao");

    assert!(
        has_key_concept,
        "roundtrip NL should contain key concepts, got: {:?}",
        nl
    );
}

// ── Additional coverage ───────────────────────────────────────────────────────

/// Rollback keyword → G4_REVERSIBILIDADE activated, P7_ACAO activated.
#[test]
fn test_rollback_axes() {
    let cogon = nl_to_cogon("precisamos fazer rollback do deploy", "pt");
    assert!(cogon.sem[leet_bridge::nl_translator::G4_REVERSIBILIDADE] > 0.7);
    assert!(cogon.sem[leet_bridge::nl_translator::P7_ACAO] > 0.7);
}

/// Past tense → G2_ANCORA_TEMPORAL near 0 (past).
#[test]
fn test_temporal_past() {
    let cogon = nl_to_cogon("ontem o servidor caiu", "pt");
    assert!(
        cogon.sem[leet_bridge::nl_translator::G2_ANCORA_TEMPORAL] < 0.4,
        "expected past orientation, got {}",
        cogon.sem[leet_bridge::nl_translator::G2_ANCORA_TEMPORAL]
    );
}

/// Future tense → G2_ANCORA_TEMPORAL near 1 (future).
#[test]
fn test_temporal_future() {
    let cogon = nl_to_cogon("o próximo deploy vai amanhã", "pt");
    assert!(
        cogon.sem[leet_bridge::nl_translator::G2_ANCORA_TEMPORAL] > 0.6,
        "expected future orientation, got {}",
        cogon.sem[leet_bridge::nl_translator::G2_ANCORA_TEMPORAL]
    );
}

/// Confirmed/verified keywords → D8_VERIFICABILIDADE high.
#[test]
fn test_verification() {
    let cogon = nl_to_cogon("foi confirmado e verificado pelos testes", "pt");
    assert!(cogon.sem[leet_bridge::nl_translator::D8_VERIFICABILIDADE] > 0.8);
}

/// English intent detection: question starters.
#[test]
fn test_intent_en_query() {
    assert!(matches!(infer_intent("What is the status?"), Intent::Query));
    assert!(matches!(infer_intent("How do we fix this?"), Intent::Query));
    assert!(matches!(infer_intent("Is the service running?"), Intent::Query));
}

/// Sync intent detection.
#[test]
fn test_intent_sync() {
    assert!(matches!(infer_intent("sync all agents now"), Intent::Sync));
    assert!(matches!(infer_intent("precisamos sincronizar"), Intent::Sync));
}

/// COGON_ZERO reconstruction produces the expected marker text.
#[test]
fn test_cogon_zero_nl() {
    let z = Cogon::zero();
    let nl = cogon_to_nl(&z, "pt");
    assert!(nl.contains("COGON_ZERO"), "expected [COGON_ZERO] marker in: {:?}", nl);

    let nl_en = cogon_to_nl(&z, "en");
    assert!(nl_en.contains("COGON_ZERO"));
}
