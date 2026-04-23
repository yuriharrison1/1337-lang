# PROMPT 07a — AXES v0.5.1 (migração cirúrgica, bloco 1 da Fase A)

Reescrever `leet-core/src/axes.rs` de v0.4 (grupos A/B/C ontológico-epistêmico-pragmático) para v0.5.1 (4 blocos funcionais S/D/G/P). Adaptar os dois únicos consumers que quebrariam o build: `leet-cli/src/cmd/axes.rs` e `leet-cli/tests/cli_test.rs`.

**PRÉ-REQUISITOS**: repo na main, `cargo test --workspace` verde no estado v0.4, commit limpo.

**ESCOPO FORA** (NÃO tocar):
- `leet-core/src/types.rs` (07b)
- `leet-core/src/codec.rs` (07c)
- `leet-core/src/operators.rs` (07d)
- `leet-core/src/validate.rs`, `error.rs` (07e)
- `leet-core/src/protocol.rs` (07f)
- `leet-core/src/claude_1337_prompt.rs` se existir (07g)
- `leet-bridge/*`, `leet-service/*`, `python/*`, `leet-py/*`, `leet-vm/*`, `calibration/*`
- **Os nomes dos eixos ficam em português nesta fase** — tradução PT→EN é o PROMPT_08 (bloco 2 da Fase A).

**IMPORTANTE**: Ao finalizar, atualizar CONTRACT.md e Taskwarrior (projeto `1337`, tag `+prompt07a`).

---

## CONTEXTO — O QUE MUDA DE v0.4 PARA v0.5.1

A spec v0.5.1 reorganiza o espaço canônico de 32 eixos em **4 blocos funcionais** (não mais 3 grupos filosóficos):

| Bloco | Índices | Função | Variante Rust |
|---|---|---|---|
| S — Semântica | 0–7 | Significado intrínseco e qualidade representacional | `Semantic` |
| D — Dinâmica | 8–15 | Como o conceito evolui, aprende e resiste a mudança | `Dynamic` |
| G — Gravidade | 16–23 | Atração, repulsão e organização no espaço semântico | `Gravity` |
| P — Precisão | 24–31 | Qualidade e fidelidade da representação | `Precision` |

**Três substituições históricas da v0.5 → v0.5.1 (já refletidas na tabela abaixo)**:
- D7 SATURACAO → **CAUSALIDADE** (rastreamento de origem em DAGs)
- G2 DISTANCIA → **ANCORA_TEMPORAL** (distância vira operador DIST, não eixo)
- P7 CUSTO → **ACAO** (fecha loop pragmático)

---

## ESPAÇO CANÔNICO v0.5.1 — OS 32 EIXOS

**Colunas**: índice | código | nome (PT) | normalização | boot_default (Pilar 4) | descrição

### Bloco 1 — SEMÂNTICA [0–7]

| # | Código | Nome | Normalização | Boot | Descrição |
|---|---|---|---|---|---|
| 0 | S1 | INTENCAO | 0=sem propósito · 1=propósito máximo | 0.5 | Grau em que o conceito carrega propósito direcional |
| 1 | S2 | AMBIGUIDADE | 0=sentido único · 1=completamente ambíguo | 0.5 | Multiplicidade de interpretações possíveis |
| 2 | S3 | CONTEXTO_LOCAL | 0=autônomo · 1=totalmente dependente | 0.5 | Dependência do entorno imediato |
| 3 | S4 | CONTEXTO_GLOBAL | 0=sem histórico · 1=profundamente ancorado | 0.5 | Ancoragem no histórico acumulado do sistema |
| 4 | S5 | ENTROPIA | 0=determinístico · 1=máxima incerteza | 0.5 | Incerteza informacional intrínseca |
| 5 | S6 | DENSIDADE | 0=vazio · 1=máxima compressão | 0.5 | Significado comprimido por unidade |
| 6 | S7 | COERENCIA | 0=contraditório · 1=totalmente consistente | **1.0** | Consistência lógica interna |
| 7 | S8 | ALINHAMENTO | 0=divergência total · 1=consenso pleno | 0.5 | Entendimento compartilhado entre agentes |

### Bloco 2 — DINÂMICA [8–15]

| # | Código | Nome | Normalização | Boot | Descrição |
|---|---|---|---|---|---|
| 8 | D1 | PESO_CONEXAO | 0=link fraco · 1=link forte | 0.5 | Força do vínculo com outros COGONs |
| 9 | D2 | TAXA_APRENDIZADO | 0=frozen · 1=máxima plasticidade | 0.5 | Velocidade de absorção de novos dados |
| 10 | D3 | DECAIMENTO | 0=permanente · 1=decay máximo | 0.5 | Velocidade de perda de relevância sem reforço |
| 11 | D4 | ESTABILIDADE | 0=caótico · 1=totalmente estável | 0.5 | Tendência ao equilíbrio vs instabilidade |
| 12 | D5 | HISTERESE | 0=sem memória · 1=alta dependência histórica | 0.5 | Dependência do estado anterior |
| 13 | D6 | PROPAGACAO | 0=isolado · 1=influência máxima | 0.5 | Grau de influência sobre vizinhos |
| 14 | D7 | CAUSALIDADE | 0=origem opaca · 1=causa identificável | 0.5 | Grau em que a origem do conceito é identificável |
| 15 | D8 | INERCIA | 0=muda instantaneamente · 1=resistência máxima | 0.5 | Resistência à mudança de estado |

### Bloco 3 — GRAVIDADE [16–23]

| # | Código | Nome | Normalização | Boot | Descrição |
|---|---|---|---|---|---|
| 16 | G1 | MASSA | 0=irrelevante · 1=alta relevância | 0.5 | Relevância e confiança acumulada do COGON |
| 17 | G2 | ANCORA_TEMPORAL | 0=atemporal · 1=momento preciso definido | 0.5 | Grau em que o conceito tem âncora temporal |
| 18 | G3 | AFINIDADE | 0=repulsão · 0.5=neutro · 1=atração (bipolar) | 0.5 | Associação negativa vs positiva com o entorno |
| 19 | G4 | TEMPORALIDADE | 0=passado · 0.5=presente · 1=futuro (bipolar) | 0.5 | Orientação temporal da interação |
| 20 | G5 | CAMPO_LOCAL | 0=periférico · 1=dominante | 0.5 | Dominância dentro do cluster semântico |
| 21 | G6 | CAMPO_GLOBAL | 0=periférico · 1=hub global | 0.5 | Centralidade na rede global |
| 22 | G7 | K_INTERACAO | 0=K_min · 1=K_max (normalizado) | **0.1** | Ganho adaptativo local — sensibilidade do campo |
| 23 | G8 | GRADIENTE | 0=desaceleração · 0.5=estável · 1=aceleração (bipolar) | 0.5 | Direção e intensidade de mudança do campo |

### Bloco 4 — PRECISÃO [24–31]

| # | Código | Nome | Normalização | Boot | Descrição |
|---|---|---|---|---|---|
| 24 | P1 | QUANTIZACAO | 0=precisão máxima · 1=arredondamento máximo | **0.8** | Nível de arredondamento (controlado pelo Pilar 6) |
| 25 | P2 | GRANULARIDADE | 0=atômico · 1=altamente decomponível | 0.5 | Resolução decomponível do conceito |
| 26 | P3 | COMPRESSAO | 0=expandido · 1=máxima compressão | 0.5 | Grau de compressão da representação |
| 27 | P4 | RUIDO | 0=sinal puro · 1=dominado por ruído | 0.5 | Proporção de ruído vs sinal |
| 28 | P5 | RESOLUCAO | 0=grosseiro · 1=alta resolução | 0.5 | Fineza da representação adaptativa |
| 29 | P6 | CONFIANCA | 0=zero confiança · 1=certeza total | 0.5 | Confiança na fidelidade — substitui unc[32] da v0.4 |
| 30 | P7 | ACAO | 0=puramente informativo · 1=exige execução | **0.0** | Demanda de resposta ativa do receptor |
| 31 | P8 | LATENCIA | 0=tempo real · 1=atualização atrasada | 0.5 | Atraso de atualização da representação |

**Boot exceções (Pilar 4)** — apenas 4 eixos saem de 0.5:
- S7_COERENCIA → 1.0 (assume consistente até prova em contrário)
- G7_K_INTERACAO → 0.1 (ganho baixo, evita explosão no boot)
- P1_QUANTIZACAO → 0.8 (arredondamento conservador no boot)
- P7_ACAO → 0.0 (default: não demanda ação)

---

## FILE 1 — `leet-core/src/axes.rs` (REESCRITA COMPLETA)

Substituir o conteúdo inteiro pelo seguinte. Texto do código em inglês, nomes dos eixos mantidos em português.

```rust
//! Canonical 32-axis space v0.5.1.
//!
//! Four functional blocks (not philosophical groups):
//!   S — Semantic   [0..8)   meaning & representational quality
//!   D — Dynamic    [8..16)  evolution, learning, resistance to change
//!   G — Gravity    [16..24) attraction, repulsion, semantic organization
//!   P — Precision  [24..32) fidelity & representation quality
//!
//! Axis names preserved in Portuguese; English rename is PROMPT_08.
//! Indexed by position (R10). Three v0.5.1 substitutions vs v0.5:
//!   D7 SATURACAO   → CAUSALIDADE
//!   G2 DISTANCIA   → ANCORA_TEMPORAL
//!   P7 CUSTO       → ACAO

/// Functional block of a canonical axis (v0.5.1).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AxisBlock {
    Semantic,   // [0..8)
    Dynamic,    // [8..16)
    Gravity,    // [16..24)
    Precision,  // [24..32)
}

impl AxisBlock {
    /// Short single-letter tag: S / D / G / P.
    pub fn tag(&self) -> &'static str {
        match self {
            AxisBlock::Semantic  => "S",
            AxisBlock::Dynamic   => "D",
            AxisBlock::Gravity   => "G",
            AxisBlock::Precision => "P",
        }
    }

    /// Human-readable block title (PT, matches spec).
    pub fn title(&self) -> &'static str {
        match self {
            AxisBlock::Semantic  => "Bloco 1 — SEMÂNTICA",
            AxisBlock::Dynamic   => "Bloco 2 — DINÂMICA",
            AxisBlock::Gravity   => "Bloco 3 — GRAVIDADE",
            AxisBlock::Precision => "Bloco 4 — PRECISÃO",
        }
    }

    /// Inclusive start / exclusive end of this block's index range.
    pub fn range(&self) -> (usize, usize) {
        match self {
            AxisBlock::Semantic  => (0, 8),
            AxisBlock::Dynamic   => (8, 16),
            AxisBlock::Gravity   => (16, 24),
            AxisBlock::Precision => (24, 32),
        }
    }
}

/// Metadata for one canonical axis.
#[derive(Debug, Clone)]
pub struct AxisInfo {
    pub index: usize,
    /// Short code (S1..P8). Language-agnostic — never translated.
    pub code: &'static str,
    /// Canonical name (PT until PROMPT_08 renames to EN).
    pub name: &'static str,
    pub block: AxisBlock,
    pub description: &'static str,
    /// Human-readable normalization hint (e.g. "0=past · 0.5=present · 1=future").
    pub normalization: &'static str,
    /// Pilar 4 boot initialization value.
    pub boot_default: f32,
    /// Whether this axis is bipolar (neutral at 0.5) — matters for BLEND (07d).
    pub bipolar: bool,
}

/// All 32 canonical axes in index order (R10 — indexed by position).
pub const CANONICAL_AXES: [AxisInfo; 32] = [
    // ── Bloco 1 — SEMÂNTICA (0..8) ────────────────────────────────────────
    AxisInfo {
        index: 0, code: "S1", name: "INTENCAO", block: AxisBlock::Semantic,
        description: "Grau em que o conceito carrega propósito direcional",
        normalization: "0=sem propósito · 1=propósito máximo",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 1, code: "S2", name: "AMBIGUIDADE", block: AxisBlock::Semantic,
        description: "Multiplicidade de interpretações possíveis",
        normalization: "0=sentido único · 1=completamente ambíguo",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 2, code: "S3", name: "CONTEXTO_LOCAL", block: AxisBlock::Semantic,
        description: "Dependência do entorno imediato para ser compreendido",
        normalization: "0=autônomo · 1=totalmente dependente",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 3, code: "S4", name: "CONTEXTO_GLOBAL", block: AxisBlock::Semantic,
        description: "Ancoragem no histórico acumulado do sistema",
        normalization: "0=sem histórico · 1=profundamente ancorado",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 4, code: "S5", name: "ENTROPIA", block: AxisBlock::Semantic,
        description: "Incerteza informacional intrínseca ao conceito",
        normalization: "0=determinístico · 1=máxima incerteza",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 5, code: "S6", name: "DENSIDADE", block: AxisBlock::Semantic,
        description: "Quantidade de significado comprimido por unidade",
        normalization: "0=vazio · 1=máxima compressão",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 6, code: "S7", name: "COERENCIA", block: AxisBlock::Semantic,
        description: "Consistência lógica interna do conceito",
        normalization: "0=contraditório · 1=totalmente consistente",
        boot_default: 1.0, bipolar: false,
    },
    AxisInfo {
        index: 7, code: "S8", name: "ALINHAMENTO", block: AxisBlock::Semantic,
        description: "Entendimento compartilhado entre agentes sobre este conceito",
        normalization: "0=divergência total · 1=consenso pleno",
        boot_default: 0.5, bipolar: false,
    },
    // ── Bloco 2 — DINÂMICA (8..16) ────────────────────────────────────────
    AxisInfo {
        index: 8, code: "D1", name: "PESO_CONEXAO", block: AxisBlock::Dynamic,
        description: "Força do vínculo com outros COGONs na rede",
        normalization: "0=link fraco · 1=link forte",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 9, code: "D2", name: "TAXA_APRENDIZADO", block: AxisBlock::Dynamic,
        description: "Plasticidade — velocidade de absorção de novos dados",
        normalization: "0=frozen · 1=máxima plasticidade",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 10, code: "D3", name: "DECAIMENTO", block: AxisBlock::Dynamic,
        description: "Velocidade com que o conceito perde relevância sem reforço",
        normalization: "0=permanente · 1=decay máximo",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 11, code: "D4", name: "ESTABILIDADE", block: AxisBlock::Dynamic,
        description: "Tendência ao equilíbrio vs instabilidade caótica",
        normalization: "0=caótico · 1=totalmente estável",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 12, code: "D5", name: "HISTERESE", block: AxisBlock::Dynamic,
        description: "Dependência do estado anterior — memória de trajetória",
        normalization: "0=sem memória · 1=alta dependência histórica",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 13, code: "D6", name: "PROPAGACAO", block: AxisBlock::Dynamic,
        description: "Grau de influência sobre COGONs vizinhos",
        normalization: "0=isolado · 1=influência máxima",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 14, code: "D7", name: "CAUSALIDADE", block: AxisBlock::Dynamic,
        description: "Grau em que a origem do conceito é identificável (v0.5.1: substitui SATURACAO)",
        normalization: "0=origem opaca · 1=causa identificável",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 15, code: "D8", name: "INERCIA", block: AxisBlock::Dynamic,
        description: "Resistência à mudança de estado",
        normalization: "0=muda instantaneamente · 1=resistência máxima",
        boot_default: 0.5, bipolar: false,
    },
    // ── Bloco 3 — GRAVIDADE (16..24) ──────────────────────────────────────
    AxisInfo {
        index: 16, code: "G1", name: "MASSA", block: AxisBlock::Gravity,
        description: "Relevância e confiança acumulada do COGON no sistema",
        normalization: "0=irrelevante · 1=alta relevância",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 17, code: "G2", name: "ANCORA_TEMPORAL", block: AxisBlock::Gravity,
        description: "Grau em que o conceito tem âncora temporal definida (v0.5.1: substitui DISTANCIA)",
        normalization: "0=atemporal · 1=momento preciso definido",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 18, code: "G3", name: "AFINIDADE", block: AxisBlock::Gravity,
        description: "Associação negativa vs positiva com o entorno (bipolar)",
        normalization: "0=repulsão · 0.5=neutro · 1=atração",
        boot_default: 0.5, bipolar: true,
    },
    AxisInfo {
        index: 19, code: "G4", name: "TEMPORALIDADE", block: AxisBlock::Gravity,
        description: "Orientação temporal da interação entre COGONs (bipolar)",
        normalization: "0=passado · 0.5=presente · 1=futuro",
        boot_default: 0.5, bipolar: true,
    },
    AxisInfo {
        index: 20, code: "G5", name: "CAMPO_LOCAL", block: AxisBlock::Gravity,
        description: "Dominância do COGON dentro do seu cluster semântico",
        normalization: "0=periférico · 1=dominante",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 21, code: "G6", name: "CAMPO_GLOBAL", block: AxisBlock::Gravity,
        description: "Centralidade do COGON na rede global",
        normalization: "0=periférico · 1=hub global",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 22, code: "G7", name: "K_INTERACAO", block: AxisBlock::Gravity,
        description: "Ganho adaptativo local — sensibilidade do campo nesta região",
        normalization: "0=K_min · 1=K_max (normalizado)",
        boot_default: 0.1, bipolar: false,
    },
    AxisInfo {
        index: 23, code: "G8", name: "GRADIENTE", block: AxisBlock::Gravity,
        description: "Direção e intensidade de mudança do campo gravitacional (bipolar)",
        normalization: "0=desaceleração · 0.5=estável · 1=aceleração",
        boot_default: 0.5, bipolar: true,
    },
    // ── Bloco 4 — PRECISÃO (24..32) ───────────────────────────────────────
    AxisInfo {
        index: 24, code: "P1", name: "QUANTIZACAO", block: AxisBlock::Precision,
        description: "Nível de arredondamento aplicado (controlado pelos Pilares 6 e 7)",
        normalization: "0=precisão máxima · 1=arredondamento máximo",
        boot_default: 0.8, bipolar: false,
    },
    AxisInfo {
        index: 25, code: "P2", name: "GRANULARIDADE", block: AxisBlock::Precision,
        description: "Resolução decomponível do conceito",
        normalization: "0=atômico · 1=altamente decomponível",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 26, code: "P3", name: "COMPRESSAO", block: AxisBlock::Precision,
        description: "Grau de compressão da representação",
        normalization: "0=expandido · 1=máxima compressão",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 27, code: "P4", name: "RUIDO", block: AxisBlock::Precision,
        description: "Proporção de ruído vs sinal na representação",
        normalization: "0=sinal puro · 1=dominado por ruído",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 28, code: "P5", name: "RESOLUCAO", block: AxisBlock::Precision,
        description: "Fineza da representação adaptativa",
        normalization: "0=grosseiro · 1=alta resolução",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 29, code: "P6", name: "CONFIANCA", block: AxisBlock::Precision,
        description: "Confiança na fidelidade da representação (substitui o unc[32] da v0.4)",
        normalization: "0=zero confiança · 1=certeza total",
        boot_default: 0.5, bipolar: false,
    },
    AxisInfo {
        index: 30, code: "P7", name: "ACAO", block: AxisBlock::Precision,
        description: "Grau em que o conceito demanda resposta ativa do receptor (v0.5.1: substitui CUSTO)",
        normalization: "0=puramente informativo · 1=exige execução imediata",
        boot_default: 0.0, bipolar: false,
    },
    AxisInfo {
        index: 31, code: "P8", name: "LATENCIA", block: AxisBlock::Precision,
        description: "Atraso de atualização da representação",
        normalization: "0=tempo real · 1=atualização máxima atrasada",
        boot_default: 0.5, bipolar: false,
    },
];

/// All axes belonging to a block.
pub fn axes_by_block(block: AxisBlock) -> Vec<&'static AxisInfo> {
    CANONICAL_AXES.iter().filter(|ax| ax.block == block).collect()
}

/// Axis by zero-based index, or None if out of range.
pub fn axis_by_index(index: usize) -> Option<&'static AxisInfo> {
    CANONICAL_AXES.get(index)
}

/// Axis by code (case-insensitive, e.g. "S1", "p8").
pub fn axis_by_code(code: &str) -> Option<&'static AxisInfo> {
    let up = code.to_uppercase();
    CANONICAL_AXES.iter().find(|ax| ax.code == up)
}

/// Boot vector from Pilar 4 (v0.5.1): all axes at boot_default.
/// Used by 07b (Cogon::zero) and 07f (protocol anchors).
pub fn boot_vector() -> [f32; 32] {
    let mut v = [0.5_f32; 32];
    for ax in CANONICAL_AXES.iter() {
        v[ax.index] = ax.boot_default;
    }
    v
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_32_axes_present() {
        assert_eq!(CANONICAL_AXES.len(), 32);
    }

    #[test]
    fn indices_are_sequential() {
        for (i, ax) in CANONICAL_AXES.iter().enumerate() {
            assert_eq!(ax.index, i, "axis at position {} has wrong index", i);
        }
    }

    #[test]
    fn block_semantic_has_8_axes() {
        assert_eq!(axes_by_block(AxisBlock::Semantic).len(), 8);
    }

    #[test]
    fn block_dynamic_has_8_axes() {
        assert_eq!(axes_by_block(AxisBlock::Dynamic).len(), 8);
    }

    #[test]
    fn block_gravity_has_8_axes() {
        assert_eq!(axes_by_block(AxisBlock::Gravity).len(), 8);
    }

    #[test]
    fn block_precision_has_8_axes() {
        assert_eq!(axes_by_block(AxisBlock::Precision).len(), 8);
    }

    #[test]
    fn block_ranges_cover_0_to_32_without_overlap() {
        let mut seen = [false; 32];
        for block in [AxisBlock::Semantic, AxisBlock::Dynamic, AxisBlock::Gravity, AxisBlock::Precision] {
            let (start, end) = block.range();
            for i in start..end {
                assert!(!seen[i], "index {} covered twice", i);
                seen[i] = true;
            }
        }
        assert!(seen.iter().all(|&x| x), "some index not covered");
    }

    #[test]
    fn axis_by_code_s1_is_intencao() {
        let ax = axis_by_code("S1").unwrap();
        assert_eq!(ax.index, 0);
        assert_eq!(ax.name, "INTENCAO");
        assert_eq!(ax.block, AxisBlock::Semantic);
    }

    #[test]
    fn axis_by_code_p8_is_latencia() {
        let ax = axis_by_code("P8").unwrap();
        assert_eq!(ax.index, 31);
        assert_eq!(ax.name, "LATENCIA");
        assert_eq!(ax.block, AxisBlock::Precision);
    }

    #[test]
    fn axis_by_code_case_insensitive() {
        assert!(axis_by_code("g7").is_some());
        assert!(axis_by_code("G7").is_some());
    }

    #[test]
    fn axis_by_code_not_found() {
        assert!(axis_by_code("Z99").is_none());
        assert!(axis_by_code("A0").is_none(), "v0.4 codes must not resolve");
    }

    #[test]
    fn axis_by_index_out_of_range() {
        assert!(axis_by_index(32).is_none());
    }

    #[test]
    fn v051_substitutions_in_place() {
        // D7 is CAUSALIDADE (not SATURACAO)
        assert_eq!(axis_by_index(14).unwrap().name, "CAUSALIDADE");
        // G2 is ANCORA_TEMPORAL (not DISTANCIA)
        assert_eq!(axis_by_index(17).unwrap().name, "ANCORA_TEMPORAL");
        // P7 is ACAO (not CUSTO)
        assert_eq!(axis_by_index(30).unwrap().name, "ACAO");
    }

    #[test]
    fn boot_exceptions_match_pilar_4() {
        let v = boot_vector();
        assert_eq!(v[6],  1.0, "S7_COERENCIA boot = 1.0");
        assert_eq!(v[22], 0.1, "G7_K_INTERACAO boot = 0.1");
        assert_eq!(v[24], 0.8, "P1_QUANTIZACAO boot = 0.8");
        assert_eq!(v[30], 0.0, "P7_ACAO boot = 0.0");
        // Everything else defaults to 0.5
        for i in [0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                  16, 17, 18, 19, 20, 21, 23, 25, 26, 27, 28, 29, 31] {
            assert_eq!(v[i], 0.5, "axis {} should boot at 0.5", i);
        }
    }

    #[test]
    fn bipolar_flags_match_spec() {
        let bipolar_codes = ["G3", "G4", "G8"];
        for ax in CANONICAL_AXES.iter() {
            let expected = bipolar_codes.contains(&ax.code);
            assert_eq!(ax.bipolar, expected, "axis {} bipolar flag mismatch", ax.code);
        }
    }

    #[test]
    fn block_tags_are_short() {
        assert_eq!(AxisBlock::Semantic.tag(),  "S");
        assert_eq!(AxisBlock::Dynamic.tag(),   "D");
        assert_eq!(AxisBlock::Gravity.tag(),   "G");
        assert_eq!(AxisBlock::Precision.tag(), "P");
    }
}
```

**Check após escrever**: `cargo test -p leet-core --lib axes` verde. Se algo além de `axes.rs` no leet-core ainda importar `AxisGroup`, **NÃO** criar alias de compatibilidade — o build vai quebrar em outros crates e é isso que os próximos arquivos vão corrigir.

---

## FILE 2 — `leet-cli/src/cmd/axes.rs` (ADAPTAÇÃO MÍNIMA)

O CLI imprime a tabela de eixos com cabeçalhos e cores por grupo. Trocar `AxisGroup` por `AxisBlock`, cabeçalhos de "Group A/B/C" para os títulos dos 4 blocos, cores reatribuídas.

```rust
use anyhow::Result;
use colored::Colorize;
use leet_core::axes::{AxisBlock, CANONICAL_AXES};

/// Print all 32 canonical axes grouped by block.
pub fn run(json: bool) -> Result<()> {
    if json {
        return run_json();
    }

    let mut current_block: Option<AxisBlock> = None;
    for axis in CANONICAL_AXES.iter() {
        // Print block header whenever the block changes.
        if current_block != Some(axis.block) {
            println!();
            println!("{}", axis.block.title().bold());
            current_block = Some(axis.block);
        }

        let code_colored = match axis.block {
            AxisBlock::Semantic  => axis.code.cyan().to_string(),
            AxisBlock::Dynamic   => axis.code.yellow().to_string(),
            AxisBlock::Gravity   => axis.code.magenta().to_string(),
            AxisBlock::Precision => axis.code.green().to_string(),
        };

        println!(
            "  [{:2}] {:3} {:<20} {}",
            axis.index, code_colored, axis.name, axis.description
        );
    }
    println!();
    Ok(())
}

fn run_json() -> Result<()> {
    let axes: Vec<serde_json::Value> = CANONICAL_AXES
        .iter()
        .map(|a| {
            serde_json::json!({
                "index":         a.index,
                "code":          a.code,
                "name":          a.name,
                "block":         a.block.tag(),
                "description":   a.description,
                "normalization": a.normalization,
                "boot_default":  a.boot_default,
                "bipolar":       a.bipolar,
            })
        })
        .collect();
    println!("{}", serde_json::to_string_pretty(&axes)?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_axes_have_unique_codes() {
        let mut seen = std::collections::HashSet::new();
        for axis in CANONICAL_AXES.iter() {
            assert!(seen.insert(axis.code), "duplicate code: {}", axis.code);
        }
        assert_eq!(seen.len(), 32);
    }

    #[test]
    fn all_axes_have_description() {
        for axis in CANONICAL_AXES.iter() {
            assert!(!axis.description.is_empty());
        }
    }
}
```

**Se o módulo tinha o subcomando `leet axes --group A`** (filtrar por grupo no CLI, via `clap`), renomear a flag para `--block <S|D|G|P>` no `leet-cli/src/cmd/mod.rs` ou onde estiver o parser — ajustar apenas se o parser existir, não criar flag nova se não existia.

---

## FILE 3 — `leet-cli/tests/cli_test.rs` (ATUALIZAR ASSERTS)

Substituir apenas os asserts que referenciam códigos/nomes v0.4. Manter tudo o resto do arquivo intacto.

```rust
// Asserts que mudam:
//   antes: assert_eq!(CANONICAL_AXES[0].code, "A0");
//   depois:
assert_eq!(CANONICAL_AXES[0].code, "S1");
assert_eq!(CANONICAL_AXES[0].name, "INTENCAO");

//   antes: assert_eq!(CANONICAL_AXES[31].code, "C10");
//   depois:
assert_eq!(CANONICAL_AXES[31].code, "P8");
assert_eq!(CANONICAL_AXES[31].name, "LATENCIA");

//   antes: assert_eq!(CANONICAL_AXES[22].code, "C1");
//          assert_eq!(CANONICAL_AXES[22].name, "URGÊNCIA");
//   depois (índice 22 em v0.5.1 é G7_K_INTERACAO):
assert_eq!(CANONICAL_AXES[22].code, "G7");
assert_eq!(CANONICAL_AXES[22].name, "K_INTERACAO");

// Qualquer assert sobre tamanho do Group A/B/C:
//   antes: assert_eq!(group_a.len(), 14);
//   depois: remover; novos testes de bloco já estão em axes.rs
```

Se houver testes checando `axes_by_group`, remover — a função não existe mais. Os novos testes de tamanho por bloco já estão cobertos em `leet-core/src/axes.rs::tests`.

---

## VERIFICATION

```bash
# Gate principal do sub-prompt
cargo test -p leet-core --lib axes
cargo test -p leet-cli
cargo test --workspace            # tem que ficar verde inteiro

# Sanity visual
cargo run -p leet-cli --bin leet -- axes
cargo run -p leet-cli --bin leet -- axes --json | jq '.[0], .[31]'

# Esperado: primeiro item tem code "S1" / name "INTENCAO",
# último tem code "P8" / name "LATENCIA".
```

Se algum teste em outro crate (leet-bridge, leet-service, python, etc.) quebrar por conta do axes.rs, **NÃO consertar aqui** — esses crates ainda estão em v0.4 e vão ser migrados via 07b-g e blocos posteriores. Registrar o que quebrou em CONTRACT.md na seção "pending after 07a" e seguir.

**Exceção**: se leet-core em si não compilar (por `unc` removido mas ainda referenciado), isso é problema de 07b — não tocar aqui.

---

## GIT + TASKWARRIOR

```bash
# Taskwarrior
task add project:1337 +prompt07a "Migrate axes.rs to v0.5.1 (blocks S/D/G/P, 32 axes PT)"
task project:1337 +prompt07a start

# Após testes verdes:
task project:1337 +prompt07a done

# Git
git add leet-core/src/axes.rs \
        leet-cli/src/cmd/axes.rs \
        leet-cli/tests/cli_test.rs

git commit -m "refactor(axes): migrate leet-core to v0.5.1 block structure

- axes.rs: 4 functional blocks (Semantic/Dynamic/Gravity/Precision) replace
  3 philosophical groups (Ontological/Epistemic/Pragmatic).
- 32 axes with v0.5.1 substitutions: D7 SATURACAO→CAUSALIDADE,
  G2 DISTANCIA→ANCORA_TEMPORAL, P7 CUSTO→ACAO.
- AxisInfo extended with normalization hint, boot_default (Pilar 4),
  bipolar flag (informs 07d BLEND).
- Added boot_vector() for use in 07b (Cogon::zero) and 07f (anchors).
- CLI updated (colors per block, --json emits extended metadata).
- Names kept in Portuguese — PT→EN rename is PROMPT_08.

Part of Fase A, sub-prompt 07a. See PROMPT_07b next (types.rs)."

git push origin main
```

---

## CONTRACT.md UPDATE

Adicionar sob a seção da Fase A:

```markdown
### 07a — axes.rs v0.5.1 (COMPLETED)
- leet-core/src/axes.rs reescrito com 4 blocos S/D/G/P
- AxisBlock enum (Semantic/Dynamic/Gravity/Precision)
- AxisInfo com normalization + boot_default + bipolar
- boot_vector() helper (usado por 07b e 07f)
- leet-cli adaptado (cores por bloco, --json emite metadata completa)
- Gate: cargo test --workspace verde
- Pendente após 07a: types.rs ainda tem unc[32] (07b); codec.rs ainda
  serializa unc (07c); operators.rs ainda usa unc (07d); validate.rs ainda
  tem R5 baseado em unc (07e); protocol.rs ainda cria âncoras com unc (07f).
```

---

**END OF PROMPT_07a — READY TO FEED CLAUDE CODE**
