# PROMPT 07b — TYPES v0.5.1 (remover unc, ajustar Cogon)

Remover o campo `unc: SemVec` de `Cogon` e adaptar todos os 6 consumers externos que o referenciam. A incerteza deixa de existir como vetor separado — passa a viver dentro dos próprios eixos (`S5 ENTROPIA`, `P4 RUIDO`, `P6 CONFIANCA`).

**PRÉ-REQUISITOS**: PROMPT_07a executado e commitado. `cargo test --workspace` verde.

**ESCOPO FORA** (NÃO tocar):
- `codec.rs` (07c — ainda serializa unc[32], será tratado lá)
- `operators.rs` (07d — ainda usa unc internamente)
- `validate.rs`, `error.rs` (07e)
- `protocol.rs` (07f)
- `claude_1337_prompt.rs` (07g)

**IMPORTANTE**: 07c vai manter os 32 bytes de unc como `reserved[32]` de zeros no wire format. Então a REMOÇÃO em runtime (aqui em 07b) é independente da preservação em wire (07c).

**Taskwarrior**: `+prompt07b`, projeto `1337`.

---

## O QUE MUDA

Na v0.4 o `Cogon` tinha:
```rust
pub struct Cogon {
    pub id: Uuid,
    pub sem: SemVec,
    pub unc: SemVec,  // ← REMOVER
    pub stamp: i64,
    pub raw: Option<RawField>,
}
```

Na v0.5.1 o `Cogon` vira:
```rust
pub struct Cogon {
    pub id: Uuid,
    pub sem: SemVec,
    pub stamp: i64,
    pub raw: Option<RawField>,
}
```

A incerteza é consultada agora via eixos específicos:
- `sem[4]` (S5 ENTROPIA) — incerteza informacional intrínseca
- `sem[27]` (P4 RUIDO) — ruído vs sinal
- `sem[29]` (P6 CONFIANCA) — confiança global (0=zero, 1=certeza total)

**R5 vira**: low confidence triggered when `sem[29] < 0.1` (será formalizado em 07e).

---

## COGON_ZERO — VALORES EXATOS v0.5.1

Na v0.4 `Cogon::zero()` era `sem=[1]*32, unc=[0]*32`. Na v0.5.1 o COGON_ZERO tem valores específicos por eixo (seção 2 da spec). `Cogon::zero()` deve retornar esse vetor exato:

```
# Bloco S:  [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
# Bloco D:  [0.5, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0]
# Bloco G:  [1.0, 0.5, 1.0, 0.5, 0.5, 1.0, 0.1, 0.0]
# Bloco P:  [0.8, 0.0, 1.0, 0.0, 0.5, 1.0, 0.0, 0.0]
```

Isso é **diferente** de `axes::boot_vector()` (Pilar 4 — agente entrando na rede). São dois conceitos distintos e não se confundem.

---

## FILE 1 — `leet-core/src/types.rs`

Substituições cirúrgicas:

**(a)** Na struct `Cogon`, remover o campo `unc`:
```rust
// ANTES
pub struct Cogon {
    pub id: Uuid,
    pub sem: SemVec,
    pub unc: SemVec,      // ← DELETAR
    pub stamp: i64,
    pub raw: Option<RawField>,
}

// DEPOIS
pub struct Cogon {
    pub id: Uuid,
    pub sem: SemVec,
    pub stamp: i64,
    pub raw: Option<RawField>,
}
```

**(b)** Reescrever `Cogon::zero()` com os valores exatos v0.5.1 (adicionar helper privado):

```rust
/// The canonical COGON_ZERO vector (v0.5.1 spec § 2).
/// Distinct from axes::boot_vector() which is the Pilar 4 init for new agents.
const COGON_ZERO_SEM: [f32; 32] = [
    // S: INTENCAO, AMBIGUIDADE, CONTEXTO_LOCAL, CONTEXTO_GLOBAL,
    //    ENTROPIA, DENSIDADE, COERENCIA, ALINHAMENTO
    1.0, 0.0, 0.0, 0.0,   0.0, 1.0, 1.0, 1.0,
    // D: PESO_CONEXAO, TAXA_APRENDIZADO, DECAIMENTO, ESTABILIDADE,
    //    HISTERESE, PROPAGACAO, CAUSALIDADE, INERCIA
    0.5, 0.0, 0.0, 1.0,   0.0, 1.0, 1.0, 0.0,
    // G: MASSA, ANCORA_TEMPORAL, AFINIDADE, TEMPORALIDADE,
    //    CAMPO_LOCAL, CAMPO_GLOBAL, K_INTERACAO, GRADIENTE
    1.0, 0.5, 1.0, 0.5,   0.5, 1.0, 0.1, 0.0,
    // P: QUANTIZACAO, GRANULARIDADE, COMPRESSAO, RUIDO,
    //    RESOLUCAO, CONFIANCA, ACAO, LATENCIA
    0.8, 0.0, 1.0, 0.0,   0.5, 1.0, 0.0, 0.0,
];

impl Cogon {
    /// Construct COGON_ZERO per v0.5.1 spec § 2.
    pub fn zero() -> Self {
        Self {
            id: Uuid::nil(),
            sem: COGON_ZERO_SEM,
            stamp: 0,
            raw: None,
        }
    }

    /// True iff this is the canonical COGON_ZERO (id nil + stamp 0 + no raw + exact sem).
    pub fn is_zero(&self) -> bool {
        self.id == Uuid::nil()
            && self.stamp == 0
            && self.raw.is_none()
            && self.sem == COGON_ZERO_SEM
    }

    /// Low-confidence COGON per v0.5.1 R5 — P6_CONFIANCA below 0.1.
    pub fn is_low_confidence(&self) -> bool {
        self.sem[29] < 0.1
    }
}
```

Remover completamente `pub fn low_confidence_dims()` — obsoleto (era por-dimensão sobre unc).

**(c)** Tornar `COGON_ZERO_SEM` exportável se 07c ou 07f precisar. Se não for usado fora, mantém `const` privada.

---

## FILE 2 — `leet-cli/src/cmd/zero.rs`

Remover as referências a `zero.unc`:

```rust
// ANTES
println!("  unc:   [{}, ..., {}] (all 0.0, 32 dims)", zero.unc[0], zero.unc[31]);

// DEPOIS — remover essa linha inteira.
// Substituir por impressão do P6_CONFIANCA no vetor novo:
println!("  P6_CONFIANCA (sem[29]): {} (certeza total)", zero.sem[29]);
```

No teste do módulo:
```rust
// ANTES
assert!(z.unc.iter().all(|&v| v == 0.0));

// DEPOIS — remover. Substituir por:
assert_eq!(z.sem[29], 1.0, "COGON_ZERO has P6_CONFIANCA = 1.0");
assert!(z.is_zero());
```

---

## FILE 3 — `leet-cli/src/cmd/inspect.rs`

Localizar a linha que formata cada eixo:
```rust
// ANTES
let line = format!("  {:2}. {:28} = {:.4}  (unc={:.4})", rank + 1, label, v, cogon.unc[*i]);

// DEPOIS
let line = format!("  {:2}. {:28} = {:.4}", rank + 1, label, v);
```

Se houver `--show-unc` flag, remover a flag. Substituir (se fizer sentido contextualmente) por uma seção "Global confidence: P6 = {value}" no topo do output.

---

## FILE 4 — `leet-bridge/src/heuristics.rs`

Localizar a struct `Rule` (ou equivalente) que contém `unc_value`:

```rust
// ANTES
pub struct Rule {
    pub axis: usize,
    pub sem_value: f32,
    pub unc_value: f32,   // ← REMOVER
    // ... outros campos
}
```

Remover o campo `unc_value`. No builder/constructor, remover o argumento. Na aplicação:

```rust
// ANTES
unc[rule.axis] = rule.unc_value;

// DEPOIS — remover linha inteira.
```

Se houver lógica que decide o valor de P6_CONFIANCA baseado na qualidade do match da heurística, mover pra `sem[29]` com valor fixo (ex.: 0.7 para heurística de keyword matching — informativo mas não precisão máxima). Deixar comentário `// TODO(07d): review P6 injection once operators migrate`.

---

## FILE 5 — `leet-bridge/src/nl_translator.rs`

Três linhas identificadas (239, 352, 393):

**Linha 239** — application de rule:
```rust
// ANTES
unc[rule.axis] = rule.unc;

// DEPOIS — remover linha.
```

**Linha 352** — check condicional:
```rust
// ANTES
} else if cogon.sem[G4_REVERSIBILIDADE] < 0.2 && cogon.unc[G4_REVERSIBILIDADE] < 0.3 {

// DEPOIS — trocar unc check por P6 check:
} else if cogon.sem[G4_REVERSIBILIDADE] < 0.2 && cogon.sem[29] > 0.7 {
// (sem[29] = P6_CONFIANCA: só entra na branch se a confiança global é alta)
```

Nota: `G4_REVERSIBILIDADE` é nome v0.4. Em v0.5.1 o índice 19 é `G4_TEMPORALIDADE`. O comportamento desse branch provavelmente não faz mais sentido — adicionar comentário `// TODO(v0.6): revisit semantic intent of this branch under v0.5.1 axes`.

**Linha 393** — agregação de avg_unc:
```rust
// ANTES
let avg_unc: f32 = cogon.unc.iter().sum::<f32>() / 32.0;

// DEPOIS — substituir por confiança global:
let confidence: f32 = cogon.sem[29]; // P6_CONFIANCA
// E ajustar o uso subsequente: onde usava avg_unc > threshold, vira confidence < (1.0 - threshold).
```

Ajustar o callsite de `avg_unc` na função — a lógica pode precisar ser invertida (alta incerteza ↔ baixa confiança).

---

## FILE 6 — `leet-service/src/store.rs`

Duas linhas (127, 255):

```rust
// ANTES (ambas)
unc: c.unc.clone(),

// DEPOIS — remover linha inteira.
```

Remover o campo `unc` da struct que mantinha a cópia, se existir. Se o store tem schema/serialize customizado com `unc`, ajustar pra não emitir esse campo.

---

## FILE 7 — `leet-service/src/server.rs`

Duas linhas (99, 182):

**Linha 99** — chamada de reconstruct:
```rust
// ANTES
let text = self.engine.reconstruct(&req.sem, &req.unc, &req.lang);

// DEPOIS
let text = self.engine.reconstruct(&req.sem, &req.lang);
```

A assinatura de `reconstruct` precisa ser atualizada no engine (provavelmente em `leet-bridge` — se for, faz parte deste sub-prompt por dependência transitiva).

**Linha 182** — response building:
```rust
// ANTES
unc: r.unc,

// DEPOIS — remover.
```

Se os tipos `Request`/`Response` definidos em `proto/leet.proto` ainda tiverem `unc`, **NÃO tocar no .proto neste sub-prompt**. Fica como "pendente para 07c" porque está no wire format. Em vez disso, na conversão `proto → internal type` em server.rs, simplesmente ignora o campo `unc` do proto e não preenche nada no internal.

---

## VERIFICATION

```bash
# Gate principal
cargo build --workspace
cargo test -p leet-core --lib types
cargo test -p leet-core
cargo test --workspace

# Sanity
cargo run -p leet-cli --bin leet -- zero
cargo run -p leet-cli --bin leet -- zero | grep -i "P6_CONFIANCA"

# COGON_ZERO roundtrip JSON (deve ter sem, stamp, id, raw — nunca unc)
cargo run -p leet-cli --bin leet -- zero --json | jq 'keys'
# Esperado: ["id","raw","sem","stamp"]
```

Se `cargo test -p leet-bridge` falhar em testes de integração que esperavam `unc` populada, ajustar os asserts — esses testes estão testando um contrato que não existe mais.

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt07b "Remove unc from Cogon, adapt 6 downstream consumers"
task project:1337 +prompt07b start
# ... trabalho ...
task project:1337 +prompt07b done

git add leet-core/src/types.rs \
        leet-cli/src/cmd/zero.rs \
        leet-cli/src/cmd/inspect.rs \
        leet-bridge/src/heuristics.rs \
        leet-bridge/src/nl_translator.rs \
        leet-service/src/store.rs \
        leet-service/src/server.rs

git commit -m "refactor(types): remove unc[32] from Cogon (v0.5.1)

Uncertainty is no longer a separate vector — it lives inside semantic
axes: S5_ENTROPIA (informational), P4_RUIDO (noise), P6_CONFIANCA (global).

- Cogon struct: drop 'unc: SemVec' field entirely.
- Cogon::zero() now returns the canonical v0.5.1 COGON_ZERO vector
  (specific values per axis per spec § 2), not [1]*32.
- Cogon::is_low_confidence() checks sem[29] (P6) < 0.1 instead of per-dim unc.
- Removed Cogon::low_confidence_dims() — per-dim semantics no longer apply.
- Adapted 6 downstream consumers: leet-cli (zero, inspect), leet-bridge
  (heuristics, nl_translator), leet-service (store, server).
- The wire format still carries 32 bytes where unc used to live; 07c
  renames those to reserved[32] with zeros.
- Validate R5 still references unc — 07e rewrites it to use P6.

Part of Fase A, sub-prompt 07b."

git push origin main
```

---

**END OF PROMPT_07b**
