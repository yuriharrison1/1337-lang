Crie a biblioteca Rust core para o Projeto 1337 — uma linguagem de comunicação nativa entre agentes de IA, spec v0.4 (32 eixos canônicos).

O core DEVE ser chamável de Python (via PyO3) e de qualquer linguagem (via C ABI/FFI). Isso é requisito fundamental — o core é o motor, programas externos o consomem.

A especificação completa está embutida abaixo. Use SOMENTE ela como fonte de verdade.

---

# ESPECIFICAÇÃO 1337 v0.4 (COMPLETA)

## Tipos Primitivos
```
SCALAR   := float ∈ [0,1]
VECTOR   := SCALAR[]
HASH     := SHA256
ID       := UUID v4
RAW      := any
```

## RAW (sempre dentro de COGON, nunca solto)
```
raw: {
  type:    MIME | ENUM<string|bytes|json|xml|...>,
  content: any,
  role:    ENUM { EVIDENCE, ARTIFACT, TRACE, BRIDGE }
}
```
- EVIDENCE: sustenta o sem vetorial, habilita OO
- ARTIFACT: produto gerado, não semântico
- TRACE: log, debug, auditoria
- BRIDGE: dado para sistema externo não-1337

## COGON (unidade atômica de significado)
```
COGON := {
  id:    ID,
  sem:   VECTOR[32],      # projeção nos 32 eixos canônicos
  unc:   VECTOR[32],      # incerteza por dimensão
  stamp: int64,           # timestamp nanosegundos
  raw:   RAW?             # campo auxiliar opcional
}
```

## COGON_ZERO (frase primordial "I AM")
```
COGON_ZERO := {
  id:    "00000000-0000-0000-0000-000000000000",
  sem:   [1,1,1,1,1, 1,1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1,1,1],
  unc:   [0,0,0,0,0, 0,0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0],
  stamp: 0,
  raw:   null
}
```

## EDGE (relação tipada)
```
EDGE := {
  from:   ID,
  to:     ID,
  type:   ENUM<CAUSA|CONDICIONA|CONTRADIZ|REFINA|EMERGE>,
  weight: SCALAR
}
```
- CAUSA (→): A causou B
- CONDICIONA (⊃): A é premissa de B
- CONTRADIZ (⊗): A e B mutuamente exclusivos
- REFINA (↓): B mais específico que A
- EMERGE (⇑): B emergiu da combinação de A e outros

## DAG (a frase — raciocínio composto)
```
DAG := {
  root:  ID,
  nodes: COGON[],
  edges: EDGE[]
}
```

## Intent (C3)
```
ASSERT    — transmito novo estado
QUERY     — solicito estado de outro agente
DELTA     — transmito só o que mudou
SYNC      — solicito alinhamento de cache
ANOMALY   — sinalizo desvio fora do esperado
ACK       — confirmação de absorção de estado
```

## MSG_1337 (envelope completo — ordem canônica obrigatória)
```
MSG_1337 := {
  # [1] Identidade
  id:       ID,
  sender:   ID,
  receiver: ID | BROADCAST,

  # [2] Intenção (C3)
  intent:   ENUM<ASSERT|QUERY|DELTA|SYNC|ANOMALY|ACK>,

  # [3] Referência delta (se DELTA)
  ref:      HASH?,
  patch:    VECTOR[32]?,

  # [4] Conteúdo semântico (C1 + C2)
  payload:  COGON | DAG,

  # [5] Espaço canônico (C5)
  c5: {
    zone_fixed:    VECTOR[32],
    zone_emergent: MAP<ID, SCALAR>,
    schema_ver:    semver,
    align_hash:    HASH
  },

  # [6] Interface humana (C4)
  surface: {
    human_required:    bool,
    urgency:           SCALAR,
    reconstruct_depth: int,
    lang:              ISO_639
  }
}
```

## Os 32 Eixos Canônicos

### Grupo A — Ontológico (0-13)
[0] A0 VIA — self-existence degree
[1] A1 CORRESPONDÊNCIA — pattern mirroring across abstractions
[2] A2 VIBRAÇÃO — continuous movement/transformation
[3] A3 POLARIDADE — position in spectrum between extremes
[4] A4 RITMO — cyclic/periodic pattern
[5] A5 CAUSA E EFEITO — causal agent vs effect
[6] A6 GÊNERO — generator/active vs receptive/passive
[7] A7 SISTEMA — emergent-behavior set
[8] A8 ESTADO — configuration at a moment
[9] A9 PROCESSO — transformation over time
[10] A10 RELAÇÃO — connection between entities
[11] A11 SINAL — information carrying variation
[12] A12 ESTABILIDADE — equilibrium vs divergence tendency
[13] A13 VALÊNCIA ONTOLÓGICA — intrinsic sign: 0=negative→0.5=neutral→1=positive

### Grupo B — Epistêmico (14-21)
[14] B1 VERIFICABILIDADE — external confirmability
[15] B2 TEMPORALIDADE — defined temporal anchor
[16] B3 COMPLETUDE — resolved vs open
[17] B4 CAUSALIDADE — identifiable origin
[18] B5 REVERSIBILIDADE — undoability
[19] B6 CARGA — cognitive resource consumption
[20] B7 ORIGEM — observed vs inferred vs assumed
[21] B8 VALÊNCIA EPISTÊMICA — 0=contradictory→0.5=inconclusive→1=confirmatory

### Grupo C — Pragmático (22-31)
[22] C1 URGÊNCIA — immediate response demand
[23] C2 IMPACTO — expected consequences
[24] C3 AÇÃO — active response vs alignment
[25] C4 VALOR — connects to real values
[26] C5 ANOMALIA — deviation from expected
[27] C6 AFETO — emotional valence
[28] C7 DEPENDÊNCIA — needs another to exist
[29] C8 VETOR TEMPORAL — 0=past→0.5=present→1=future
[30] C9 NATUREZA — 0=noun→1=verb
[31] C10 VALÊNCIA DE AÇÃO — 0=alert→0.5=query→1=confirmation

## Operadores (por precedência)
```
1. FOCUS(c, dims[]) → COGON       # projeta em subconjunto de dimensões
2. DELTA(c_prev, c) → VECTOR[32]  # diferença entre estados
3. BLEND(c1, c2, α) → COGON       # fusão interpolada
     sem = α·c1.sem + (1-α)·c2.sem
     unc = max(c1.unc, c2.unc)     # incerteza conservadora
4. DIST(c1, c2) → SCALAR          # cosseno ponderado por (1-unc)
5. ANOMALY_SCORE(c, hist[]) → SCALAR  # dist média pro centroide
```

## Regras Sintáticas R1-R21
```
R1:  Todo MSG_1337 tem exatamente um intent.
R2:  intent=DELTA exige ref+patch. intent≠DELTA proíbe patch.
R3:  Todo COGON referenciado num DAG deve estar em nodes do mesmo DAG.
R4:  DAG sem ciclos. Cognição circular é anomalia.
R5:  unc[i] > 0.9 dispara flag de baixa confiança.
R6:  human_required=true exige urgency declarado.
R7:  zone_emergent só referencia IDs do handshake C5.
R8:  BROADCAST só para ANOMALY ou SYNC.
R9:  RAW com EVIDENCE deve ter sem/unc coerentes.
R10: VECTOR[32] indexado por posição fixa. Nunca por nome.
R11: Zona Emergente append-only a partir do índice 32.
R12: Deprecação mantém índice com deprecated=true. Nunca deleta.
R13: Atalho emergente requer mesmo align_hash nos dois agentes.
R14: Nó do DAG não processado antes dos pais absorvidos.
R15: Mesma precedência → esquerda pra direita.
R16: FOCUS antes de BLEND. BLEND full-space explícito.
R17: Serialização na ordem canônica declarada.
R18: Herança OO: específico vence geral.
R19: Cadeia de herança máx 4 níveis.
R20: Todo agente transmite COGON_ZERO antes de qualquer msg.
R21: BRIDGE nunca expõe interior da rede 1337.
```

## Ciclo de Vida da Mensagem
```
1. VALIDAÇÃO ESTRUTURAL — R1-R21. Falha → ACK(anomaly_score=1.0), descarta.
2. VERIFICAÇÃO DE ALINHAMENTO — compara align_hash. Diverge → SYNC.
3. RESOLUÇÃO DE REFERÊNCIAS — DELTA: aplica patch. ref não encontrado → QUERY.
4. EXPANSÃO DO DAG — topológico. Prioridade: ANOMALY > URGÊNCIA>0.8 > padrão. Empate: stamp ascendente.
5. ABSORÇÃO SEMÂNTICA — atualiza cache, recomputa estado local.
6. AVALIAÇÃO DE ANOMALIA — ANOMALY_SCORE > threshold → propaga.
7. SUPERFÍCIE — se human_required: reconstrói DAG em linguagem natural, depth=reconstruct_depth, folha→raiz.
```

## Handshake C5
```
FASE 1 PROBE: novo_agente envia DAG com 5 âncoras + schema_ver
FASE 2 ECHO: rede responde com mesmas âncoras no espaço canônico
FASE 3 ALIGN: novo_agente computa M (matriz de projeção)
FASE 4 VERIFY: novo_agente envia ACK com align_hash=HASH(M). Erro > threshold → volta FASE 1.
```

## 5 Âncoras (imutáveis)
```
ÂNCORA_1: presença — algo existe agora
ÂNCORA_2: ausência — algo não existe
ÂNCORA_3: mudança — estado anterior ≠ atual
ÂNCORA_4: agência — ator causando algo
ÂNCORA_5: incerteza — grau de desconhecimento
```

## Zona Emergente
```
REGISTRO_EMERGENTE := {
  id:           UUID,
  criado_por:   [AGENT_ID, ...],
  freq:         int,
  vetor_ref:    ℝ³²,
  label_humano: string?
}
```

## OO via RAW
- Classe = COGON com RAW referenciando estrutura de tipo
- Objeto = COGON com RAW referenciando outro COGON
- Herança = COGON herdando sem de pai via BLEND
- Resolução: local → pai via RAW → Zona Emergente → Zona Fixa
- Máx 4 níveis (R19)

---

# ESTRUTURA DO PROJETO

```
leet1337/
├── Cargo.toml                    # workspace
├── leet-core/
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs
│       ├── types.rs
│       ├── axes.rs
│       ├── operators.rs
│       ├── validate.rs
│       ├── error.rs
│       ├── ffi.rs
│       └── python.rs
└── leet-bridge/
    ├── Cargo.toml
    └── src/
        └── lib.rs                # placeholder por enquanto
```

# REQUISITOS POR ARQUIVO

## Cargo.toml (workspace)
```toml
[workspace]
members = ["leet-core", "leet-bridge"]
resolver = "2"
```

## leet-core/Cargo.toml
```toml
[package]
name = "leet_core"
version = "0.4.0"
edition = "2021"

[lib]
name = "leet_core"
crate-type = ["rlib", "cdylib"]

[dependencies]
serde = { version = "1", features = ["derive"] }
serde_json = "1"
uuid = { version = "1", features = ["v4", "serde"] }
sha2 = "0.10"
thiserror = "1"
pyo3 = { version = "0.20", features = ["extension-module"], optional = true }

[features]
default = []
python = ["pyo3"]
```

## lib.rs
- Re-export todos os módulos: types, axes, operators, validate, error, ffi
- Condicionalmente python (#[cfg(feature = "python")])
- Constantes: FIXED_DIMS=32, MAX_INHERITANCE_DEPTH=4, LOW_CONFIDENCE_THRESHOLD=0.9

## error.rs
- LeetError enum com #[derive(Debug, Error)]
- Um variant para cada regra violada (R1-R21) com mensagem descritiva
- Variants extras: DimensionMismatch, ScalarOutOfRange, Serialization, AlignmentMismatch
- Type alias: LeetResult<T> = Result<T, LeetError>

## types.rs — TODOS os tipos fielmente à spec:
- Scalar = f32
- SemanticVector = Vec<f32>
- Hash = String
- Id = Uuid
- RawRole enum: Evidence, Artifact, Trace, Bridge (com serde rename SCREAMING_SNAKE_CASE)
- Raw struct: content_type (String), content (serde_json::Value), role (RawRole)
- Cogon struct: id, sem (Vec[32]), unc (Vec[32]), stamp (i64 nanoseg), raw (Option<Raw>)
  - Cogon::new(sem, unc) — gera id, timestamp automático
  - Cogon::zero() — COGON_ZERO hardcoded (id=nil, sem=[1;32], unc=[0;32], stamp=0, raw=None)
  - Cogon::is_zero() — checa id=nil && stamp==0
  - Cogon::low_confidence_dims() → Vec<usize> onde unc > 0.9 (R5)
  - Cogon::with_raw(raw) → Self
- EdgeType enum: Causa, Condiciona, Contradiz, Refina, Emerge
- Edge struct: from, to, edge_type, weight
- Dag struct: root, nodes (Vec<Cogon>), edges (Vec<Edge>)
  - Dag::from_root(cogon) — cria DAG com um nó
  - Dag::add_node(cogon), add_edge(edge)
  - Dag::node_ids() → Vec<Id>
  - Dag::parents_of(id) → Vec<Id>
  - Dag::topological_order() → Result<Vec<Id>, LeetError> (detecta ciclos, R4)
- Intent enum: Assert, Query, Delta, Sync, Anomaly, Ack
- Receiver enum (serde untagged): Agent(Id) | Broadcast
  - Receiver::is_broadcast()
- Payload enum (serde untagged): Single(Cogon) | Graph(Dag)
- CanonicalSpace struct: zone_fixed (Vec[32]), zone_emergent (HashMap<Id,Scalar>), schema_ver (String), align_hash (Hash)
- Surface struct: human_required (bool), urgency (Option<Scalar>), reconstruct_depth (i32), lang (String)
- Msg1337 struct: TODOS os campos na ORDEM CANÔNICA exata da spec
  - Msg1337::hash() → SHA256 do JSON serializado
- EmergentRegistration struct: id, created_by (Vec<Id>), freq (u64), anchor_ref (Vec), label_human (Option<String>)
- Anchor enum: Presenca, Ausencia, Mudanca, Agencia, Incerteza

## axes.rs
- AxisDef struct: index (usize), code (&'static str), name (&'static str), group (AxisGroup), description (&'static str)
- AxisGroup enum: Ontological, Epistemic, Pragmatic
- 32 constantes pub const: A0_VIA=0, A1_CORRESPONDENCIA=1, ... C10_VALENCIA_ACAO=31
- static CANONICAL_AXES: [AxisDef; 32] com TODOS os 32 eixos preenchidos (descrições completas)
- fn axis(index: usize) → Option<&'static AxisDef>
- fn axes_in_group(group: AxisGroup) → Vec<&'static AxisDef>

## operators.rs — definições formais da spec com testes:
- focus(cogon, dims) → Cogon: zera dims não-selecionadas, unc=1.0 nelas
- delta(prev, curr) → Vec<f32>: diferença ponto a ponto
- blend(c1, c2, α) → Cogon: sem=α·c1+(1-α)·c2, unc=max(c1,c2)
- dist(c1, c2) → f32: cosseno ponderado por (1-unc), dimensões incertas pesam menos
- anomaly_score(cogon, history) → f32: dist média pro centroide do histórico, vazio=1.0
- apply_patch(base, patch) → Cogon: soma clamped [0,1]
- TESTES UNITÁRIOS para CADA operador:
  - test_cogon_zero: verifica valores exatos
  - test_blend_midpoint: α=0.5 entre [1;32] e [0;32] = [0.5;32]
  - test_blend_conservative_unc: unc = max dos dois
  - test_delta_computation: verifica diferença
  - test_dist_identical: distância 0 pra iguais
  - test_focus_subset: dims selecionadas mantém, resto zera
  - test_low_confidence_detection: unc>0.9 flagged
  - test_anomaly_score_no_history: retorna 1.0
  - test_apply_patch_clamp: resultado sempre em [0,1]

## validate.rs — Validator com R1-R21:
- Validator::validate(msg) → LeetResult<()>
- Cada regra como método privado separado:
  - r1_single_intent (trivial pelo enum)
  - r2_delta_ref (DELTA↔ref+patch)
  - r3_declared_nodes (COGONs no DAG)
  - r4_no_cycles (topological order)
  - r5_low_confidence (unc > 0.9)
  - r6_urgency (human_required → urgency)
  - r8_broadcast (só ANOMALY/SYNC)
  - r9_evidence_coherence (EVIDENCE → sem não-zero)
  - r10_vector_dims (32 dimensões)
- Validator::check_confidence(msg) → Vec<(Uuid, usize, f32)> — soft warnings
- TESTES UNITÁRIOS:
  - test_valid_assert: msg válida passa
  - test_r2_delta_without_ref: falha
  - test_r2_non_delta_with_patch: falha
  - test_r4_dag_cycle: falha
  - test_r6_human_required_no_urgency: falha
  - test_r8_broadcast_assert: falha
  - test_r8_broadcast_anomaly_ok: passa
  - test_r10_wrong_dims: falha

## ffi.rs — C ABI para consumo externo:
- CONTRATO DE MEMÓRIA: strings retornadas são owned pelo caller. Liberar com leet_free_string().
- #[no_mangle] pub extern "C" fn leet_free_string(s: *mut c_char)
- #[no_mangle] pub extern "C" fn leet_cogon_zero() → *mut c_char (JSON)
- #[no_mangle] pub extern "C" fn leet_cogon_new(sem: *const f32, unc: *const f32, dims: usize) → *mut c_char
- #[no_mangle] pub extern "C" fn leet_blend(c1_json: *const c_char, c2_json: *const c_char, alpha: f32) → *mut c_char
- #[no_mangle] pub extern "C" fn leet_dist(c1_json: *const c_char, c2_json: *const c_char) → f32
- #[no_mangle] pub extern "C" fn leet_delta(prev_json: *const c_char, curr_json: *const c_char) → *mut c_char
- #[no_mangle] pub extern "C" fn leet_validate(msg_json: *const c_char) → *mut c_char (null=ok, string=erro)
- #[no_mangle] pub extern "C" fn leet_serialize(msg_json: *const c_char) → *mut c_char
- #[no_mangle] pub extern "C" fn leet_version() → *const c_char (estática "0.4.0\0")
- Helpers internos: parse_json<T>, to_json_ptr<T>

## python.rs — PyO3 Python bindings:
- Tudo feature-gated com #[cfg(feature = "python")]
- #[pymodule] fn leet_core(m: &Bound<'_, PyModule>) → PyResult<()>
- Funções expostas (todas recebem/retornam JSON strings):
  - cogon_zero() → String
  - cogon_new(sem: Vec<f32>, unc: Vec<f32>) → String
  - cogon_with_raw(sem, unc, raw_type, raw_content, raw_role) → String
  - blend(c1_json: &str, c2_json: &str, alpha: f32) → String
  - delta(prev_json: &str, curr_json: &str) → Vec<f32>
  - dist(c1_json: &str, c2_json: &str) → f32
  - focus(cogon_json: &str, dims: Vec<usize>) → String
  - anomaly_score(cogon_json: &str, history_json: Vec<String>) → f32
  - apply_patch(base_json: &str, patch: Vec<f32>) → String
  - validate(msg_json: &str) → Option<String> (None=ok, Some(erro))
  - check_confidence(msg_json: &str) → Vec<(String, usize, f32)>
  - serialize_msg(msg_json: &str) → String
  - version() → String
- Docstrings com exemplos de uso em Python

## leet-bridge/Cargo.toml
```toml
[package]
name = "leet_bridge"
version = "0.4.0"
edition = "2021"

[dependencies]
leet_core = { path = "../leet-core" }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "1"
```

## leet-bridge/src/lib.rs
- Placeholder com comment: "Bridge implementation — tradução humano ↔ 1337 via SemanticProjector trait"
- Re-export leet_core

---

# CRITÉRIOS DE ACEITE

1. `cargo build` compila sem erros nem warnings
2. `cargo test` passa TODOS os testes (operators + validate no mínimo)
3. `cargo build --release` gera .so/.dylib com símbolos C exportados (verificar com `nm -D`)
4. Toda serialização JSON é determinística na ordem canônica
5. COGON_ZERO tem valores exatos da spec
6. Nenhum arquivo é placeholder vazio — todos têm código completo e funcional
