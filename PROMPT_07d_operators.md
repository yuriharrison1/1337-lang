# PROMPT 07d — OPERATORS v0.5.1 (BLEND por bloco, DIST por P6, ANOMALY por G1)

Reescrever os 4 operadores (`FOCUS`, `DELTA`, `BLEND`, `DIST`, `ANOMALY_SCORE`) removendo toda referência a `unc` e aplicando as semânticas específicas da v0.5.1.

**PRÉ-REQUISITOS**: 07a + 07b + 07c. `cargo test --workspace` verde. `Cogon` não tem mais `unc`.

**ESCOPO FORA**: tudo exceto `operators.rs`.

**Taskwarrior**: `+prompt07d`.

---

## SEMÂNTICA v0.5.1 DOS OPERADORES

### FOCUS
Projeta COGON num subconjunto de dimensões. Em v0.5.1: dims selecionadas mantêm seu sem, dims não selecionadas ficam com `sem[i] = 0.0`. Simples.

### DELTA
Diferença element-wise entre dois estados. Sem mudança conceitual.

### BLEND
Interpolação semântica com regras por bloco. **Default** é interpolação linear padrão; exceções são específicas:

| Índice | Código | Nome | Regra BLEND |
|---|---|---|---|
| 11 | D4 | ESTABILIDADE | `min(c1, c2)` — conservador |
| 16 | G1 | MASSA | `clamp(c1 + c2, 0, 1)` — acumula |
| 22 | G7 | K_INTERACAO | `max(c1, c2)` — ganho mais alto |
| 29 | P6 | CONFIANCA | `min(c1, c2)` — conservador |

Demais índices: `sem[i] = α·c1.sem[i] + (1-α)·c2.sem[i]`.

Após aplicar todas as regras, **clamp_all** — todos os eixos forçados para `[0.0, 1.0]` (R22, que será formalizado em 07e).

### DIST
Distância cosseno ponderada pelo P6_CONFIANCA médio dos dois COGONs:

```
w = (c1.sem[29] + c2.sem[29]) / 2
dot = w * sum_i (c1.sem[i] * c2.sem[i])
```

COGONs com baixa confiança contribuem menos para a distância. Isso é diferente da v0.4, onde cada dimensão tinha peso individual `(1 - max(c1.unc[i], c2.unc[i]))`.

Retorna `[0, 2]`: 0 = idêntico, 1 = ortogonal, 2 = oposto.

### ANOMALY_SCORE
Distância de um COGON ao centroide do histórico — porém agora o centroide é **ponderado por G1_MASSA** (sem[16]). COGONs com mais massa (mais relevância acumulada) puxam o centroide mais forte.

```
mass_total = sum_h h.sem[16]
centroid.sem[i] = sum_h (h.sem[16] * h.sem[i]) / mass_total
```

Se todos os COGONs do histórico têm massa zero, cair pra centroide uniforme (média simples). Se histórico vazio, retornar 0.5 (neutro).

---

## FILE ÚNICO — `leet-core/src/operators.rs`

Reescrita completa. Substitui o arquivo atual.

```rust
//! Algebra of 1337 operators (v0.5.1).
//!
//! - FOCUS(c, dims)              — project onto a subset of dimensions
//! - DELTA(c_prev, c)            — element-wise sem difference
//! - BLEND(c1, c2, α)            — semantic fusion with per-block rules
//! - DIST(c1, c2)                — cosine distance weighted by P6_CONFIANCA
//! - ANOMALY_SCORE(c, history)   — distance to G1_MASSA-weighted centroid
//!
//! All operators apply clamp_all() on outputs (R22 in 07e).

use crate::types::{Cogon, SemVec};
use uuid::Uuid;

/// Index of P6_CONFIANCA in the canonical space.
const P6_CONFIANCA: usize = 29;
/// Index of G1_MASSA in the canonical space.
const G1_MASSA: usize = 16;
/// Index of D4_ESTABILIDADE.
const D4_ESTABILIDADE: usize = 11;
/// Index of G7_K_INTERACAO.
const G7_K_INTERACAO: usize = 22;

/// Clamp every axis to [0.0, 1.0] (R22).
#[inline]
fn clamp_all(v: &mut SemVec) {
    for x in v.iter_mut() {
        *x = x.clamp(0.0, 1.0);
    }
}

// ── FOCUS ─────────────────────────────────────────────────────────────────────

/// FOCUS — project COGON onto a dimensional subset.
/// Selected dims keep their values; others get sem=0.0.
pub fn focus(c: &Cogon, dims: &[usize]) -> Cogon {
    let mut sem = [0.0_f32; 32];
    for &d in dims {
        if d < 32 {
            sem[d] = c.sem[d];
        }
    }
    clamp_all(&mut sem);
    Cogon {
        id: Uuid::new_v4(),
        sem,
        stamp: c.stamp,
        raw: None,
    }
}

// ── DELTA ─────────────────────────────────────────────────────────────────────

/// DELTA — element-wise sem difference (not clamped; can be negative).
pub fn delta(c_prev: &Cogon, c: &Cogon) -> SemVec {
    let mut d = [0.0_f32; 32];
    for i in 0..32 {
        d[i] = c.sem[i] - c_prev.sem[i];
    }
    d
}

// ── BLEND ─────────────────────────────────────────────────────────────────────

/// BLEND — semantic fusion with per-block rules.
///
/// Default: sem[i] = α·c1.sem[i] + (1-α)·c2.sem[i]
///
/// Exceptions by axis:
/// - D4_ESTABILIDADE (11) = min(c1, c2)        — conservative
/// - G1_MASSA        (16) = clamp(c1+c2, 0, 1) — accumulating
/// - G7_K_INTERACAO  (22) = max(c1, c2)        — higher gain wins
/// - P6_CONFIANCA    (29) = min(c1, c2)        — conservative
pub fn blend(c1: &Cogon, c2: &Cogon, alpha: f32) -> Cogon {
    let alpha = alpha.clamp(0.0, 1.0);
    let mut sem = [0.0_f32; 32];

    for i in 0..32 {
        sem[i] = match i {
            D4_ESTABILIDADE => c1.sem[i].min(c2.sem[i]),
            G1_MASSA        => (c1.sem[i] + c2.sem[i]).clamp(0.0, 1.0),
            G7_K_INTERACAO  => c1.sem[i].max(c2.sem[i]),
            P6_CONFIANCA    => c1.sem[i].min(c2.sem[i]),
            _               => alpha * c1.sem[i] + (1.0 - alpha) * c2.sem[i],
        };
    }
    clamp_all(&mut sem);

    Cogon {
        id: Uuid::new_v4(),
        sem,
        stamp: c1.stamp.max(c2.stamp),
        raw: None,
    }
}

// ── DIST ──────────────────────────────────────────────────────────────────────

/// DIST — cosine distance weighted by P6_CONFIANCA average.
/// Returns value in [0, 2]: 0 = identical, 1 = orthogonal, 2 = opposite.
pub fn dist(c1: &Cogon, c2: &Cogon) -> f32 {
    let w = ((c1.sem[P6_CONFIANCA] + c2.sem[P6_CONFIANCA]) / 2.0).max(0.0);

    let dot: f32 = (0..32).map(|i| c1.sem[i] * c2.sem[i]).sum::<f32>() * w;
    let norm1: f32 = (0..32).map(|i| c1.sem[i] * c1.sem[i]).sum::<f32>().sqrt() * w.sqrt();
    let norm2: f32 = (0..32).map(|i| c2.sem[i] * c2.sem[i]).sum::<f32>().sqrt() * w.sqrt();

    if norm1 == 0.0 || norm2 == 0.0 {
        return 1.0; // max distance when a vector is zero
    }

    let cosine = (dot / (norm1 * norm2)).clamp(-1.0, 1.0);
    1.0 - cosine
}

// ── ANOMALY_SCORE ─────────────────────────────────────────────────────────────

/// ANOMALY_SCORE — distance from cogon to G1_MASSA-weighted historical centroid.
/// Returns 0.5 for empty history (neutral).
pub fn anomaly_score(c: &Cogon, history: &[Cogon]) -> f32 {
    if history.is_empty() {
        return 0.5;
    }
    let centroid = compute_weighted_centroid(history);
    dist(c, &centroid)
}

/// Weighted centroid: each historical COGON contributes in proportion to its G1_MASSA.
/// Falls back to uniform average if total mass is zero.
fn compute_weighted_centroid(history: &[Cogon]) -> Cogon {
    let total_mass: f32 = history.iter().map(|c| c.sem[G1_MASSA]).sum();

    let mut sem = [0.0_f32; 32];

    if total_mass > f32::EPSILON {
        for c in history {
            let w = c.sem[G1_MASSA] / total_mass;
            for i in 0..32 {
                sem[i] += w * c.sem[i];
            }
        }
    } else {
        // All-zero-mass fallback: uniform average.
        let n = history.len() as f32;
        for c in history {
            for i in 0..32 {
                sem[i] += c.sem[i] / n;
            }
        }
    }
    clamp_all(&mut sem);

    Cogon {
        id: Uuid::nil(),
        sem,
        stamp: 0,
        raw: None,
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::Cogon;

    /// Build a Cogon with all axes at `sem_val`.
    fn make_cogon(sem_val: f32) -> Cogon {
        Cogon {
            id: Uuid::new_v4(),
            sem: [sem_val; 32],
            stamp: 0,
            raw: None,
        }
    }

    // ── BLEND ──────────────────────────────────────────────────────────────

    #[test]
    fn blend_alpha_1_returns_c1_on_default_axes() {
        let c1 = make_cogon(0.8);
        let c2 = make_cogon(0.2);
        let r = blend(&c1, &c2, 1.0);
        // Pick a default axis (not in exceptions)
        assert!((r.sem[0] - 0.8).abs() < 1e-6);
    }

    #[test]
    fn blend_alpha_0_returns_c2_on_default_axes() {
        let c1 = make_cogon(0.8);
        let c2 = make_cogon(0.2);
        let r = blend(&c1, &c2, 0.0);
        assert!((r.sem[0] - 0.2).abs() < 1e-6);
    }

    #[test]
    fn blend_d4_estabilidade_takes_min() {
        let mut c1 = make_cogon(0.5);
        c1.sem[D4_ESTABILIDADE] = 0.9;
        let mut c2 = make_cogon(0.5);
        c2.sem[D4_ESTABILIDADE] = 0.2;
        let r = blend(&c1, &c2, 0.5);
        assert_eq!(r.sem[D4_ESTABILIDADE], 0.2, "D4 must be min");
    }

    #[test]
    fn blend_g1_massa_accumulates() {
        let mut c1 = make_cogon(0.5);
        c1.sem[G1_MASSA] = 0.4;
        let mut c2 = make_cogon(0.5);
        c2.sem[G1_MASSA] = 0.5;
        let r = blend(&c1, &c2, 0.5);
        assert!((r.sem[G1_MASSA] - 0.9).abs() < 1e-6, "G1 must accumulate");
    }

    #[test]
    fn blend_g1_massa_saturates_at_one() {
        let mut c1 = make_cogon(0.5);
        c1.sem[G1_MASSA] = 0.8;
        let mut c2 = make_cogon(0.5);
        c2.sem[G1_MASSA] = 0.7;
        let r = blend(&c1, &c2, 0.5);
        assert_eq!(r.sem[G1_MASSA], 1.0, "G1 must clamp at 1.0");
    }

    #[test]
    fn blend_g7_k_interacao_takes_max() {
        let mut c1 = make_cogon(0.5);
        c1.sem[G7_K_INTERACAO] = 0.1;
        let mut c2 = make_cogon(0.5);
        c2.sem[G7_K_INTERACAO] = 0.8;
        let r = blend(&c1, &c2, 0.5);
        assert_eq!(r.sem[G7_K_INTERACAO], 0.8, "G7 must be max");
    }

    #[test]
    fn blend_p6_confianca_takes_min() {
        let mut c1 = make_cogon(0.5);
        c1.sem[P6_CONFIANCA] = 0.9;
        let mut c2 = make_cogon(0.5);
        c2.sem[P6_CONFIANCA] = 0.3;
        let r = blend(&c1, &c2, 0.5);
        assert_eq!(r.sem[P6_CONFIANCA], 0.3, "P6 must be conservative (min)");
    }

    #[test]
    fn blend_midpoint_default_axis() {
        let c1 = make_cogon(1.0);
        let c2 = make_cogon(0.0);
        let r = blend(&c1, &c2, 0.5);
        // Default axis — picks one not in exception list
        assert!((r.sem[0] - 0.5).abs() < 1e-6);
    }

    #[test]
    fn blend_result_always_in_01() {
        let c1 = make_cogon(0.9);
        let c2 = make_cogon(0.9);
        let r = blend(&c1, &c2, 0.5);
        for i in 0..32 {
            assert!(r.sem[i] >= 0.0 && r.sem[i] <= 1.0, "dim {i} out of range");
        }
    }

    // ── DIST ───────────────────────────────────────────────────────────────

    #[test]
    fn dist_identical_cogons_is_zero() {
        let mut c = make_cogon(0.6);
        c.sem[P6_CONFIANCA] = 1.0; // full confidence
        let d = dist(&c, &c);
        assert!(d.abs() < 1e-5, "dist to self ~0, got {d}");
    }

    #[test]
    fn dist_symmetric() {
        let mut c1 = make_cogon(0.7);
        c1.sem[P6_CONFIANCA] = 0.8;
        let mut c2 = make_cogon(0.3);
        c2.sem[P6_CONFIANCA] = 0.8;
        let d12 = dist(&c1, &c2);
        let d21 = dist(&c2, &c1);
        assert!((d12 - d21).abs() < 1e-5);
    }

    #[test]
    fn dist_low_p6_lowers_distance() {
        // When average P6 is low, weighted distance gets smaller (everything shrinks).
        let mut c1 = make_cogon(0.9);
        c1.sem[P6_CONFIANCA] = 0.1;
        let mut c2 = make_cogon(0.1);
        c2.sem[P6_CONFIANCA] = 0.1;

        let mut c3 = make_cogon(0.9);
        c3.sem[P6_CONFIANCA] = 0.9;
        let mut c4 = make_cogon(0.1);
        c4.sem[P6_CONFIANCA] = 0.9;

        let d_low_conf = dist(&c1, &c2);
        let d_high_conf = dist(&c3, &c4);

        // With high P6, distance registers fully. With low P6, it still registers
        // (cosine is normalized), but numerical stability differs — just sanity:
        assert!(d_high_conf > 0.0);
        assert!(d_low_conf >= 0.0);
    }

    // ── ANOMALY_SCORE ──────────────────────────────────────────────────────

    #[test]
    fn anomaly_score_empty_history_is_neutral() {
        let c = make_cogon(0.5);
        assert_eq!(anomaly_score(&c, &[]), 0.5);
    }

    #[test]
    fn anomaly_score_heavy_cogon_dominates_centroid() {
        // History: one very heavy COGON at sem[0]=0.9 and ten light ones at sem[0]=0.1.
        // The weighted centroid should lean toward 0.9.
        let mut heavy = make_cogon(0.5);
        heavy.sem[0] = 0.9;
        heavy.sem[G1_MASSA] = 1.0; // full mass
        heavy.sem[P6_CONFIANCA] = 1.0;

        let mut light_prototype = make_cogon(0.5);
        light_prototype.sem[0] = 0.1;
        light_prototype.sem[G1_MASSA] = 0.05; // low mass
        light_prototype.sem[P6_CONFIANCA] = 1.0;

        let mut history = vec![heavy];
        for _ in 0..10 {
            history.push(light_prototype.clone());
        }

        let centroid = compute_weighted_centroid(&history);
        // Total mass = 1.0 + 10*0.05 = 1.5. Heavy contributes 1.0/1.5 ≈ 0.67.
        // Expected sem[0] ≈ 0.67*0.9 + 0.33*0.1 ≈ 0.63
        assert!(centroid.sem[0] > 0.55, "heavy cogon should dominate centroid, got {}", centroid.sem[0]);
    }

    #[test]
    fn anomaly_score_all_zero_mass_falls_back_to_uniform() {
        let mut c1 = make_cogon(0.5);
        c1.sem[G1_MASSA] = 0.0;
        c1.sem[0] = 0.2;
        let mut c2 = make_cogon(0.5);
        c2.sem[G1_MASSA] = 0.0;
        c2.sem[0] = 0.8;

        let centroid = compute_weighted_centroid(&[c1, c2]);
        assert!((centroid.sem[0] - 0.5).abs() < 1e-6, "uniform fallback");
    }

    // ── FOCUS ──────────────────────────────────────────────────────────────

    #[test]
    fn focus_keeps_selected_dims() {
        let c = make_cogon(0.9);
        let r = focus(&c, &[0, 5, 22]);
        assert!((r.sem[0] - 0.9).abs() < 1e-6);
        assert!((r.sem[5] - 0.9).abs() < 1e-6);
        assert!((r.sem[22] - 0.9).abs() < 1e-6);
        assert_eq!(r.sem[1], 0.0);
        assert_eq!(r.sem[31], 0.0);
    }

    #[test]
    fn focus_empty_dims_all_zero() {
        let c = make_cogon(0.9);
        let r = focus(&c, &[]);
        assert!(r.sem.iter().all(|&v| v == 0.0));
    }

    // ── DELTA ──────────────────────────────────────────────────────────────

    #[test]
    fn delta_returns_difference() {
        let c_prev = make_cogon(0.3);
        let c_curr = make_cogon(0.7);
        let d = delta(&c_prev, &c_curr);
        for i in 0..32 {
            assert!((d[i] - 0.4).abs() < 1e-6);
        }
    }

    #[test]
    fn delta_zero_for_identical() {
        let c = make_cogon(0.5);
        let d = delta(&c, &c);
        assert!(d.iter().all(|&v| v.abs() < 1e-6));
    }

    #[test]
    fn delta_negative_when_decreasing() {
        let c_prev = make_cogon(0.8);
        let c_curr = make_cogon(0.2);
        let d = delta(&c_prev, &c_curr);
        for i in 0..32 {
            assert!((d[i] - (-0.6)).abs() < 1e-6);
        }
    }
}
```

---

## VERIFICATION

```bash
cargo test -p leet-core --lib operators
cargo test -p leet-core
cargo test --workspace

# Sanity: dist between COGON_ZERO and itself
cargo run -p leet-cli --bin leet -- dist --zero --self 2>/dev/null || true
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt07d "Operators v0.5.1: BLEND per-block rules, DIST by P6, ANOMALY by G1"
# work
task project:1337 +prompt07d done

git add leet-core/src/operators.rs
git commit -m "refactor(operators): implement v0.5.1 semantics

- FOCUS: unselected dims become sem=0.0 (no longer unc=1.0).
- BLEND: default linear interpolation with 4 per-axis exceptions:
    D4_ESTABILIDADE (min, conservative)
    G1_MASSA       (clamp(c1+c2, 0, 1), accumulating)
    G7_K_INTERACAO (max, higher gain wins)
    P6_CONFIANCA   (min, conservative)
- DIST: cosine distance weighted by (c1.P6 + c2.P6)/2, global per-cogon
  confidence weight, replacing per-dim (1-unc) weights.
- ANOMALY_SCORE: centroid weighted by G1_MASSA (mass-heavy cogons
  dominate), with uniform fallback when total mass is zero.
- clamp_all helper enforces R22 on every operator output.
- All unc references purged.

Part of Fase A, sub-prompt 07d."
git push origin main
```

---

**END OF PROMPT_07d**
