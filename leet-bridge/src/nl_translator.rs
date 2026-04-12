//! Natural language ↔ COGON translation with v0.5.1 canonical axes.
//!
//! Maps Portuguese and English text to the 32-dimensional semantic space.
//!
//! Axis layout (v0.5.1):
//!   Block S [0-7]:   ESSENCIA, CORRESPONDENCIA, VIBRACAO, POLARIDADE,
//!                    RITMO, CAUSA_EFEITO, GENERO, SISTEMA
//!   Block D [8-15]:  ESTADO, PROCESSO, RELACAO, SINAL,
//!                    ESTABILIDADE, VALENCIA_ONT, CAUSALIDADE, VERIFICABILIDADE
//!   Block G [16-23]: TEMPORALIDADE, ANCORA_TEMPORAL, COMPLETUDE, REVERSIBILIDADE,
//!                    CARGA, ORIGEM, VALENCIA_EPIST, URGENCIA
//!   Block P [24-31]: IMPACTO, VALOR, ANOMALIA, AFETO,
//!                    DEPENDENCIA, VETOR_TEMPORAL, ACAO, VALENCIA_ACAO

use leet_core::{Cogon, Intent, SemVec};
use uuid::Uuid;

// ── Axis index constants (v0.5.1) ─────────────────────────────────────────────

// Block S — Semantic
pub const S1_ESSENCIA: usize = 0;
pub const S2_CORRESPONDENCIA: usize = 1;
pub const S3_VIBRACAO: usize = 2;
pub const S4_POLARIDADE: usize = 3;
pub const S5_RITMO: usize = 4;
pub const S6_CAUSA_EFEITO: usize = 5;
pub const S7_GENERO: usize = 6;
pub const S8_SISTEMA: usize = 7;

// Block D — Dynamic
pub const D1_ESTADO: usize = 8;
pub const D2_PROCESSO: usize = 9;
pub const D3_RELACAO: usize = 10;
pub const D4_SINAL: usize = 11;
pub const D5_ESTABILIDADE: usize = 12;
pub const D6_VALENCIA_ONT: usize = 13; // 0=neg → 0.5=neutral → 1=pos
pub const D7_CAUSALIDADE: usize = 14;
pub const D8_VERIFICABILIDADE: usize = 15;

// Block G — Gravity
pub const G1_TEMPORALIDADE: usize = 16;
pub const G2_ANCORA_TEMPORAL: usize = 17; // 0=past → 0.5=present → 1=future
pub const G3_COMPLETUDE: usize = 18;      // 0=open → 1=resolved
pub const G4_REVERSIBILIDADE: usize = 19;
pub const G5_CARGA: usize = 20;
pub const G6_ORIGEM: usize = 21;          // 0=assumed → 0.5=inferred → 1=observed
pub const G7_VALENCIA_EPIST: usize = 22;  // 0=contradictory → 0.5=inconclusive → 1=confirmatory
pub const G8_URGENCIA: usize = 23;

// Block P — Precision
pub const P1_IMPACTO: usize = 24;
pub const P2_VALOR: usize = 25;
pub const P3_ANOMALIA: usize = 26;
pub const P4_AFETO: usize = 27;           // 0=neg → 0.5=neutral → 1=pos
pub const P5_DEPENDENCIA: usize = 28;
pub const P6_VETOR_TEMPORAL: usize = 29;  // 0=past-oriented → 1=future-oriented
pub const P7_ACAO: usize = 30;
pub const P8_VALENCIA_ACAO: usize = 31;   // 0=alert → 0.5=query → 1=confirmation

/// Valence axes whose baseline is 0.5 (neutral), not 0.3.
const VALENCE_AXES: &[usize] = &[
    D6_VALENCIA_ONT,
    G2_ANCORA_TEMPORAL,
    G7_VALENCIA_EPIST,
    P4_AFETO,
    P8_VALENCIA_ACAO,
];

// ── Keyword rules ─────────────────────────────────────────────────────────────

/// One keyword heuristic: if any keyword appears in the lowercased text,
/// apply `value` to `axis` and `unc` to the uncertainty companion.
struct Rule {
    keywords: &'static [&'static str],
    axis: usize,
    value: f32,
    unc: f32,
}

/// Complete rule table for all 32 axes. Rules are applied in order;
/// later rules for the same axis overwrite earlier ones.
const RULES: &[Rule] = &[
    // ── Block S ──────────────────────────────────────────────────────────────
    Rule { keywords: &["essência", "essencia", "identity", "identidade", "núcleo", "nucleo", "core", "essence"], axis: S1_ESSENCIA, value: 0.9, unc: 0.1 },
    Rule { keywords: &["similar", "análogo", "analogous", "parecido", "like", "resembles", "espelhado"], axis: S2_CORRESPONDENCIA, value: 0.8, unc: 0.15 },
    Rule { keywords: &["mudança", "mudanca", "change", "transformação", "transformacao", "evolução", "evolucao", "transition", "migração"], axis: S3_VIBRACAO, value: 0.85, unc: 0.1 },
    Rule { keywords: &["versus", " vs ", "oposto", "opposite", "extremo", "extreme", "espectro", "spectrum", "polaridade"], axis: S4_POLARIDADE, value: 0.75, unc: 0.15 },
    Rule { keywords: &["ciclo", "cycle", "periódico", "periodico", "periodic", "rotina", "routine", "padrão recorrente", "recurring"], axis: S5_RITMO, value: 0.8, unc: 0.1 },
    Rule { keywords: &["porque", "causa", "cause", "resultado de", "result of", "consequência", "consequencia", "therefore", "portanto", "logo"], axis: S6_CAUSA_EFEITO, value: 0.85, unc: 0.1 },
    Rule { keywords: &["gera ", "generates", "ativo ", "active", "iniciativa", "initiative", "proativo", "proactive"], axis: S7_GENERO, value: 0.75, unc: 0.15 },
    Rule { keywords: &["sistema", "system", "conjunto", "emergente", "emergent", "rede ", "network", "ecosistema", "ecossistema"], axis: S8_SISTEMA, value: 0.85, unc: 0.1 },

    // ── Block D ──────────────────────────────────────────────────────────────
    Rule { keywords: &["status", "estado", "state", "condição", "condicao", "condition", "health", "saúde", "saude", "situação", "situacao"], axis: D1_ESTADO, value: 0.85, unc: 0.1 },
    Rule { keywords: &["processo", "process", "deploy", "pipeline", "executando", "running", "rodando", "workflow", "fluxo"], axis: D2_PROCESSO, value: 0.85, unc: 0.1 },
    Rule { keywords: &["relacionado", "related", "conectado", "connected", "dependency", "dependência", "dependencia", "between", "entre "], axis: D3_RELACAO, value: 0.75, unc: 0.15 },
    Rule { keywords: &["sinal", "signal", "evento", "event", "alerta ", "alert", "notificação", "notificacao", "notification", "trigger"], axis: D4_SINAL, value: 0.8, unc: 0.1 },
    Rule { keywords: &["estável", "estavel", "stable", "equilíbrio", "equilibrio", "equilibrium", "instável", "instavel", "unstable", "oscilando"], axis: D5_ESTABILIDADE, value: 0.75, unc: 0.15 },
    // D6 valence — positive
    Rule { keywords: &["bom", "ótimo", "otimo", "good", "great", "excellent", "perfeito", "perfect", "funciona", "works", " ok ", "okay", "sucesso", "success"], axis: D6_VALENCIA_ONT, value: 0.85, unc: 0.1 },
    // D6 valence — negative (overrides positive if both match)
    Rule { keywords: &[" ruim", " mau ", "bad ", "horrible", "péssimo", "pessimo", "terrible", "errado", "wrong ", "falhou", "failed"], axis: D6_VALENCIA_ONT, value: 0.15, unc: 0.1 },
    Rule { keywords: &["origem", "source", "causado por", "caused by", "triggered by", "raiz", "root cause", "motivo", "reason"], axis: D7_CAUSALIDADE, value: 0.8, unc: 0.15 },
    Rule { keywords: &["confirmado", "confirmed", "verificado", "verified", "testado", "tested", "proven", "comprovado", "checked"], axis: D8_VERIFICABILIDADE, value: 0.9, unc: 0.05 },

    // ── Block G ──────────────────────────────────────────────────────────────
    Rule { keywords: &["quando", "when", "às ", "hora ", "horário", "horario", "data ", "date ", "schedule", "agendado", "timestamp"], axis: G1_TEMPORALIDADE, value: 0.85, unc: 0.1 },
    // G2 temporal anchor — past (lowers toward 0)
    Rule { keywords: &["ontem", "yesterday", "anteriormente", "previously", "antes ", "before ", "passado", "último", "ultimo", "last "], axis: G2_ANCORA_TEMPORAL, value: 0.1, unc: 0.1 },
    // G2 temporal anchor — future (raises toward 1)
    Rule { keywords: &["amanhã", "amanha", "tomorrow", "próximo", "proximo", "next ", "futuro", "future", " vai ", "will ", "deverá", "devera", "planned", "planejado"], axis: G2_ANCORA_TEMPORAL, value: 0.9, unc: 0.1 },
    // G3 completeness — resolved
    Rule { keywords: &["completo", "complete", "done", "finalizado", "finished", "resolvido", "resolved", "concluído", "concluido", "fechado", "closed"], axis: G3_COMPLETUDE, value: 0.9, unc: 0.05 },
    // G3 completeness — pending
    Rule { keywords: &["pendente", "pending", "incompleto", "incomplete", "em andamento", "in progress", "wip", "aberto", "open", "bloqueado", "blocked"], axis: G3_COMPLETUDE, value: 0.2, unc: 0.1 },
    // G4 reversibility — reversible
    Rule { keywords: &["reverter", "revert", "desfazer", "undo", "rollback", "voltar atrás", "restore", "restaurar"], axis: G4_REVERSIBILIDADE, value: 0.9, unc: 0.05 },
    // G4 reversibility — irreversible
    Rule { keywords: &["irreversível", "irreversivel", "irreversible", "definitivo", "permanent", "permanente", "deletado", "deleted"], axis: G4_REVERSIBILIDADE, value: 0.1, unc: 0.1 },
    Rule { keywords: &["complexo", "complex", "difícil", "dificil", "difficult", "complicado", "complicated", "pesado", "heavy", "trabalhoso"], axis: G5_CARGA, value: 0.85, unc: 0.1 },
    // G6 origin — observed
    Rule { keywords: &["observado", "observed", "detectado", "detected", "visto", "seen", "log ", "monitored", "medido", "measured"], axis: G6_ORIGEM, value: 0.9, unc: 0.05 },
    // G6 origin — inferred
    Rule { keywords: &["inferido", "inferred", "estimado", "estimated", "parece", "seems", "provavelmente", "probably"], axis: G6_ORIGEM, value: 0.5, unc: 0.2 },
    // G6 origin — assumed
    Rule { keywords: &["assumido", "assumed", "suposição", "suposicao", "assumption", "acredito", "believe"], axis: G6_ORIGEM, value: 0.1, unc: 0.2 },
    // G7 epistemic valence — confirmatory
    Rule { keywords: &["certamente", "certainly", "definitivamente", "definitely", "confirmado", "confirmed", "correto", "correct", "provado", "proven"], axis: G7_VALENCIA_EPIST, value: 0.9, unc: 0.05 },
    // G7 epistemic valence — inconclusive
    Rule { keywords: &["talvez", "maybe", "possibly", "possivelmente", "incerto", "uncertain", "dúvida", "duvida", "unclear"], axis: G7_VALENCIA_EPIST, value: 0.4, unc: 0.15 },
    // G7 epistemic valence — contradictory
    Rule { keywords: &["contraditório", "contraditorio", "contradictory", "conflito", "conflict", "inconsistente", "inconsistent", "diverge"], axis: G7_VALENCIA_EPIST, value: 0.1, unc: 0.1 },
    // G8 urgency — critical
    Rule { keywords: &["urgente", "urgent", "imediato", "immediate", "asap", "agora!", "now!", "emergência", "emergencia", "emergency"], axis: G8_URGENCIA, value: 0.95, unc: 0.05 },
    Rule { keywords: &["crítico", "critico", "critical", "severity", "severidade"], axis: G8_URGENCIA, value: 0.9, unc: 0.05 },
    // G8 urgency — moderate (monitoring/status implies some urgency)
    Rule { keywords: &["importante", "important", "atenção", "atencao", "attention", "prioridade", "priority"], axis: G8_URGENCIA, value: 0.7, unc: 0.1 },
    Rule { keywords: &["status", "monitorar", "monitor", "verificar", "check", "health"], axis: G8_URGENCIA, value: 0.55, unc: 0.15 },

    // ── Block P ──────────────────────────────────────────────────────────────
    Rule { keywords: &["impacto", "impact", "consequência", "consequencia", "consequence", "efeito", "effect", "resultado"], axis: P1_IMPACTO, value: 0.85, unc: 0.1 },
    Rule { keywords: &["valor", "value", "importa", "matters", "essencial", "essential", "fundamental", "relevante", "relevant"], axis: P2_VALOR, value: 0.85, unc: 0.1 },
    // P3 anomaly — error/failure
    Rule { keywords: &["erro", "error", "falha", "failure", "crash", "down", "problema", "problem", "bug", "issue", "quebrado", "broken"], axis: P3_ANOMALIA, value: 0.9, unc: 0.05 },
    Rule { keywords: &["anomalia", "anomaly", "incomum", "unusual", "estranho", "strange", "unexpected", "inesperado"], axis: P3_ANOMALIA, value: 0.75, unc: 0.1 },
    Rule { keywords: &["crítico", "critico", "critical"], axis: P3_ANOMALIA, value: 0.85, unc: 0.05 },
    // P4 affect — positive
    Rule { keywords: &["excelente", "excellent", "ótimo", "otimo", "happy", "feliz", "alegre", "joy", "animado"], axis: P4_AFETO, value: 0.9, unc: 0.1 },
    // P4 affect — negative
    Rule { keywords: &["preocupante", "concerning", "preocupado", "worried", "triste", "sad", "ansioso", "anxious", "frustrado"], axis: P4_AFETO, value: 0.15, unc: 0.1 },
    Rule { keywords: &["depende", "depends", "necessita", "needs", "precisa", "requires", "requer", "prerequisite", "prerequisito"], axis: P5_DEPENDENCIA, value: 0.85, unc: 0.1 },
    // P6 temporal vector — future-oriented
    Rule { keywords: &["futuro", "future", "próximo release", "next release", "planejado", "planned", "roadmap", "vai ser", "will be"], axis: P6_VETOR_TEMPORAL, value: 0.9, unc: 0.1 },
    // P6 temporal vector — past-oriented
    Rule { keywords: &["histórico", "historico", "history", "legado", "legacy", "versão antiga", "old version", "deprecated"], axis: P6_VETOR_TEMPORAL, value: 0.1, unc: 0.1 },
    // P7 action
    Rule { keywords: &["fazer", "do ", "executar", "execute", "run ", "implementar", "implement", "realizar", "perform", "ação", "acao", "action"], axis: P7_ACAO, value: 0.9, unc: 0.05 },
    Rule { keywords: &["verificar", "check", "analisar", "analyze", "investigar", "investigate", "examinar", "examine", "revisar", "review"], axis: P7_ACAO, value: 0.7, unc: 0.1 },
    // P8 action valence — confirmation
    Rule { keywords: &["confirmar", "confirm", "aprovado", "approved", "aceito", "accepted", " sim ", " yes ", "correto", "correct", "ok ", "done"], axis: P8_VALENCIA_ACAO, value: 0.9, unc: 0.05 },
    // P8 action valence — alert
    Rule { keywords: &["alerta", "alert", "aviso", "warning", "cuidado", "careful", "atenção urgente", "watch out"], axis: P8_VALENCIA_ACAO, value: 0.1, unc: 0.1 },
];

// ── Intent inference ──────────────────────────────────────────────────────────

/// Infer message intent from text patterns.
///
/// Priority order: Query > Anomaly > Sync > Delta > Assert
pub fn infer_intent(text: &str) -> Intent {
    let lower = text.to_lowercase();
    let trimmed = lower.trim_end();

    // Query: ends with "?" or starts with interrogative words
    if trimmed.ends_with('?') {
        return Intent::Query;
    }
    let query_starters: &[&str] = &[
        "qual ", "quando ", "como ", "onde ", "quem ", "por que ", "porque ",
        "what ", "when ", "how ", "where ", "who ", "why ",
        "is ", "are ", "do ", "does ", "did ", "has ", "have ",
        "pode ", "podem ", "can ", "could ", "would ", "should ",
        "existe ", "há ", "tem ",
    ];
    if query_starters.iter().any(|q| lower.starts_with(q)) {
        return Intent::Query;
    }

    // Anomaly: error/failure keywords
    let anomaly_keys: &[&str] = &[
        "erro", "error", "crash", "falha", "failure", "caiu", "down",
        "crítico", "critico", "critical", "problema crítico", "critical problem",
    ];
    if anomaly_keys.iter().any(|k| lower.contains(k)) {
        return Intent::Anomaly;
    }

    // Sync: synchronization keywords
    let sync_keys: &[&str] = &[
        "sync", "sincronizar", "sincronização", "sincronizacao", "alinhar", "align",
    ];
    if sync_keys.iter().any(|k| lower.contains(k)) {
        return Intent::Sync;
    }

    // Delta: change/update
    let delta_keys: &[&str] = &[
        "mudou", "changed", "atualizado", "updated", "alterado", "altered",
        "nova versão", "new version", "diff", "patch",
    ];
    if delta_keys.iter().any(|k| lower.contains(k)) {
        return Intent::Delta;
    }

    Intent::Assert
}

// ── NL → COGON ───────────────────────────────────────────────────────────────

/// Translate natural language text (Portuguese or English) into a COGON.
///
/// Uses keyword heuristics to populate the 32 axes. The `lang` parameter
/// controls output language in `cogon_to_nl`; it is not used here.
pub fn nl_to_cogon(text: &str, _lang: &str) -> Cogon {
    let lower = text.to_lowercase();

    // Baseline: low activation for most axes, neutral (0.5) for valence axes
    let mut sem: SemVec = [0.3_f32; 32];
    let mut unc: SemVec = [0.3_f32; 32];
    for &idx in VALENCE_AXES {
        sem[idx] = 0.5;
        unc[idx] = 0.2;
    }

    // Apply all keyword rules in order
    for rule in RULES {
        if rule.keywords.iter().any(|kw| lower.contains(kw)) {
            sem[rule.axis] = rule.value;
            unc[rule.axis] = rule.unc;
        }
    }

    // Negation: "não/not/sem/without" raises uncertainty across activated axes
    let negation_keys: &[&str] = &["não ", "nao ", "not ", "sem ", "without ", "nunca", "never"];
    if negation_keys.iter().any(|n| lower.contains(n)) {
        for u in unc.iter_mut() {
            *u = (*u + 0.15).min(0.9);
        }
    }

    // Hedging: "talvez/maybe/parece/seems" raises uncertainty globally
    let hedge_keys: &[&str] = &["talvez", "maybe", "possivelmente", "possibly", "parece ", "seems ", "pode ser", "might "];
    if hedge_keys.iter().any(|h| lower.contains(h)) {
        for u in unc.iter_mut() {
            *u = (*u + 0.2).min(0.9);
        }
    }

    // Short texts have higher overall uncertainty (fewer disambiguation cues)
    if text.split_whitespace().count() < 4 {
        for u in unc.iter_mut() {
            *u = (*u + 0.1).min(0.9);
        }
    }

    Cogon {
        id: Uuid::new_v4(),
        sem,
        unc,
        stamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos() as i64)
            .unwrap_or(0),
        raw: None,
    }
}

// ── COGON → NL ───────────────────────────────────────────────────────────────

/// Reconstruct natural language from a COGON.
///
/// Collects axes with significant activation (sem > 0.5 for regular axes,
/// deviation from 0.5 for valence axes) and builds a descriptive phrase.
/// Uncertainty qualifiers are added when average unc > 0.3.
pub fn cogon_to_nl(cogon: &Cogon, lang: &str) -> String {
    let is_pt = !lang.starts_with("en");

    if cogon.is_zero() {
        return if is_pt {
            "Eu existo. Presença plena. Certeza absoluta. [COGON_ZERO]".to_string()
        } else {
            "I exist. Full presence. Absolute certainty. [COGON_ZERO]".to_string()
        };
    }

    let mut parts: Vec<String> = Vec::new();

    // ── G8: urgency prefix ────────────────────────────────────────────────
    if cogon.sem[G8_URGENCIA] > 0.85 {
        parts.push(if is_pt { "[URGENTE]".to_string() } else { "[URGENT]".to_string() });
    } else if cogon.sem[G8_URGENCIA] > 0.65 {
        parts.push(if is_pt { "[IMPORTANTE]".to_string() } else { "[IMPORTANT]".to_string() });
    }

    // ── P3: anomaly ───────────────────────────────────────────────────────
    if cogon.sem[P3_ANOMALIA] > 0.7 {
        parts.push(if is_pt {
            "Anomalia detectada.".to_string()
        } else {
            "Anomaly detected.".to_string()
        });
    }

    // ── D1: current state ─────────────────────────────────────────────────
    if cogon.sem[D1_ESTADO] > 0.7 {
        parts.push(if is_pt {
            "Estado atual relevante.".to_string()
        } else {
            "Current state relevant.".to_string()
        });
    }

    // ── D2: active process ────────────────────────────────────────────────
    if cogon.sem[D2_PROCESSO] > 0.7 {
        parts.push(if is_pt {
            "Processo em andamento.".to_string()
        } else {
            "Process in progress.".to_string()
        });
    }

    // ── P7: action required ───────────────────────────────────────────────
    if cogon.sem[P7_ACAO] > 0.7 {
        parts.push(if is_pt {
            "Requer ação ativa.".to_string()
        } else {
            "Requires active action.".to_string()
        });
    }

    // ── D6: ontological valence ───────────────────────────────────────────
    let ont = cogon.sem[D6_VALENCIA_ONT];
    if ont > 0.75 {
        parts.push(if is_pt { "Valência positiva.".to_string() } else { "Positive valence.".to_string() });
    } else if ont < 0.25 {
        parts.push(if is_pt { "Valência negativa.".to_string() } else { "Negative valence.".to_string() });
    }

    // ── G4: reversibility ────────────────────────────────────────────────
    if cogon.sem[G4_REVERSIBILIDADE] > 0.75 {
        parts.push(if is_pt { "Reversível.".to_string() } else { "Reversible.".to_string() });
    } else if cogon.sem[G4_REVERSIBILIDADE] < 0.2 && cogon.unc[G4_REVERSIBILIDADE] < 0.3 {
        parts.push(if is_pt { "Irreversível.".to_string() } else { "Irreversible.".to_string() });
    }

    // ── G3: completeness ─────────────────────────────────────────────────
    if cogon.sem[G3_COMPLETUDE] > 0.8 {
        parts.push(if is_pt { "Resolvido.".to_string() } else { "Resolved.".to_string() });
    } else if cogon.sem[G3_COMPLETUDE] < 0.3 {
        parts.push(if is_pt { "Pendente.".to_string() } else { "Pending.".to_string() });
    }

    // ── G8 urgency phrase (if urgency present but action already added above, avoid duplication) ──
    if cogon.sem[G8_URGENCIA] > 0.8 && cogon.sem[P7_ACAO] <= 0.7 {
        parts.push(if is_pt {
            "Ação imediata necessária.".to_string()
        } else {
            "Immediate action required.".to_string()
        });
    }

    // ── Additional axes (limited to 5 total parts for readability) ─────────
    let secondary: &[(usize, &str, &str)] = &[
        (S8_SISTEMA,         "Comportamento sistêmico observado.", "Systemic behavior observed."),
        (D3_RELACAO,         "Relação entre entidades identificada.", "Relationship between entities identified."),
        (G5_CARGA,           "Alta carga cognitiva envolvida.", "High cognitive load involved."),
        (P1_IMPACTO,         "Alto impacto esperado.", "High expected impact."),
        (P5_DEPENDENCIA,     "Dependência crítica identificada.", "Critical dependency identified."),
        (G1_TEMPORALIDADE,   "Âncora temporal definida.", "Defined temporal anchor."),
        (D5_ESTABILIDADE,    "Estabilidade do sistema em questão.", "System stability in question."),
        (S6_CAUSA_EFEITO,    "Relação causal identificada.", "Causal relationship identified."),
        (D8_VERIFICABILIDADE,"Externamente verificável.", "Externally verifiable."),
        (P2_VALOR,           "Alto valor estratégico.", "High strategic value."),
    ];

    for &(idx, phrase_pt, phrase_en) in secondary {
        if cogon.sem[idx] > 0.72 && parts.len() < 6 {
            parts.push(if is_pt { phrase_pt.to_string() } else { phrase_en.to_string() });
        }
    }

    // ── Uncertainty qualifier ─────────────────────────────────────────────
    let avg_unc: f32 = cogon.unc.iter().sum::<f32>() / 32.0;
    if avg_unc > 0.55 {
        parts.push(if is_pt {
            "(alta incerteza)".to_string()
        } else {
            "(high uncertainty)".to_string()
        });
    } else if avg_unc > 0.35 {
        parts.push(if is_pt {
            "(incerteza moderada)".to_string()
        } else {
            "(moderate uncertainty)".to_string()
        });
    }

    if parts.is_empty() {
        if is_pt {
            "[cogon neutro — sem eixos dominantes]".to_string()
        } else {
            "[neutral cogon — no dominant axes]".to_string()
        }
    } else {
        parts.join(" ")
    }
}
