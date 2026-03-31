# PROJETO 1337 — Plano de Branch v0.5
**Versão 2 — Completo, sem retrocompatibilidade**

> Fonte de verdade: `1337_spec_v0.5.docx`
> Estado do SDK: documentação v0.5.0
> Escopo: corte limpo — nada da v0.4 é preservado por compatibilidade

---

## 1. Premissa e Princípios do Branch

### O que muda de paradigma
| Aspecto | v0.4 | v0.5 |
|---------|------|------|
| Espaço canônico | 32 eixos filosófico-ontológicos (A/B/C) | 32 eixos de campo dinâmico adaptativo (S/D/G/P) |
| Incerteza | Vetor `unc[32]` separado | Distribuída nos próprios eixos (S5, P4, P6, S7) |
| Comportamento | Espaço estático | Campo adaptativo com Pilares 4–8 |
| BLEND | Interpolação linear uniforme | Regras por bloco |
| DIST | Pondera por `(1 - max_unc)` | Pondera por `P6_CONFIANCA` média |
| Ciclo de vida | 7 passos | 8 passos (Passo 6 novo: update dinâmico) |
| Regras | R1–R21 | R1–R25 (R5 atualizada, R22–R25 novas) |

### Princípios de execução
- **Corte limpo**: sem shims, sem aliases deprecated, sem retrocompatibilidade
- **Sem `unc` em nenhum lugar**: removido de todos os tipos, operadores, wire, testes, docs
- **Espelhamento Python↔Rust**: toda mudança em `.py` tem mudança correspondente em `.rs`
- **Sem números mágicos**: todos os índices de eixo via constantes nomeadas

---

## 2. Os 32 Eixos v0.5 — Referência Completa

### Constantes (Python e Rust)

```
# BLOCO 1 — SEMÂNTICA [0–7]
S1_INTENCAO        = 0   # propósito direcional
S2_AMBIGUIDADE     = 1   # multiplicidade de interpretações
S3_CONTEXTO_LOCAL  = 2   # dependência do entorno imediato
S4_CONTEXTO_GLOBAL = 3   # ancoragem no histórico acumulado
S5_ENTROPIA        = 4   # incerteza informacional intrínseca
S6_DENSIDADE       = 5   # significado por unidade
S7_COERENCIA       = 6   # consistência lógica interna
S8_ALINHAMENTO     = 7   # entendimento compartilhado entre agentes

# BLOCO 2 — DINÂMICA [8–15]
D1_PESO_CONEXAO    = 8   # força do vínculo com outros COGONs
D2_TAXA_APRENDIZADO= 9   # plasticidade
D3_DECAIMENTO      = 10  # velocidade de perda de relevância
D4_ESTABILIDADE    = 11  # tendência ao equilíbrio
D5_HISTERESE       = 12  # memória de trajetória
D6_PROPAGACAO      = 13  # influência sobre vizinhos
D7_SATURACAO       = 14  # proximidade do limite de crescimento
D8_INERCIA         = 15  # resistência à mudança

# BLOCO 3 — GRAVIDADE [16–23]
G1_MASSA           = 16  # relevância e confiança acumulada
G2_DISTANCIA       = 17  # diferença semântica de referência
G3_AFINIDADE       = 18  # bipolar: repulsão(0) <-> atração(1)
G4_TEMPORALIDADE   = 19  # bipolar: passado(0) <-> futuro(1)
G5_CAMPO_LOCAL     = 20  # dominância no cluster
G6_CAMPO_GLOBAL    = 21  # centralidade na rede
G7_K_INTERACAO     = 22  # ganho adaptativo local (normalizado 0–1)
G8_GRADIENTE       = 23  # bipolar: desaceleração(0) <-> aceleração(1)

# BLOCO 4 — PRECISÃO [24–31]
P1_QUANTIZACAO     = 24  # nível de arredondamento (controlado por Pilar 6)
P2_GRANULARIDADE   = 25  # resolução decomponível
P3_COMPRESSAO      = 26  # grau de compressão
P4_RUIDO           = 27  # proporção de ruído vs sinal
P5_RESOLUCAO       = 28  # fineza adaptativa
P6_CONFIANCA       = 29  # confiança na representação (substitui unc global)
P7_CUSTO           = 30  # custo computacional
P8_LATENCIA        = 31  # atraso de atualização
```

Eixos bipolares (0.5 = neutro): G3_AFINIDADE [18], G4_TEMPORALIDADE [19], G8_GRADIENTE [23]

### COGON_ZERO — valores exatos

```python
SEM_ZERO = [
    # BLOCO 1 — SEMÂNTICA
    1.0,  # [0]  S1 INTENCAO        — propósito máximo
    0.0,  # [1]  S2 AMBIGUIDADE     — sentido único
    0.0,  # [2]  S3 CONTEXTO_LOCAL  — autônomo
    0.0,  # [3]  S4 CONTEXTO_GLOBAL — sem histórico ainda
    0.0,  # [4]  S5 ENTROPIA        — determinístico
    1.0,  # [5]  S6 DENSIDADE       — máxima compressão
    1.0,  # [6]  S7 COERENCIA       — totalmente consistente
    1.0,  # [7]  S8 ALINHAMENTO     — consenso total
    # BLOCO 2 — DINÂMICA
    0.5,  # [8]  D1 PESO_CONEXAO    — neutro
    0.0,  # [9]  D2 TAXA_APRENDIZADO— frozen (primordial)
    0.0,  # [10] D3 DECAIMENTO      — permanente
    1.0,  # [11] D4 ESTABILIDADE    — máxima
    0.0,  # [12] D5 HISTERESE       — sem histórico anterior
    1.0,  # [13] D6 PROPAGACAO      — influência máxima
    0.0,  # [14] D7 SATURACAO       — sem limite atingido
    0.0,  # [15] D8 INERCIA         — muda instantaneamente
    # BLOCO 3 — GRAVIDADE
    1.0,  # [16] G1 MASSA           — máxima relevância
    0.0,  # [17] G2 DISTANCIA       — é a origem do espaço
    1.0,  # [18] G3 AFINIDADE       — atração máxima
    0.5,  # [19] G4 TEMPORALIDADE   — presente
    0.5,  # [20] G5 CAMPO_LOCAL     — neutro
    1.0,  # [21] G6 CAMPO_GLOBAL    — hub global
    0.1,  # [22] G7 K_INTERACAO     — conservador no boot
    0.0,  # [23] G8 GRADIENTE       — estável
    # BLOCO 4 — PRECISÃO
    0.8,  # [24] P1 QUANTIZACAO     — conservador no boot
    0.0,  # [25] P2 GRANULARIDADE   — atômico
    1.0,  # [26] P3 COMPRESSAO      — máxima
    0.0,  # [27] P4 RUIDO           — sinal puro
    0.5,  # [28] P5 RESOLUCAO       — neutro
    1.0,  # [29] P6 CONFIANCA       — certeza total
    0.0,  # [30] P7 CUSTO           — gratuito
    0.0,  # [31] P8 LATENCIA        — tempo real
]
```

### Valores de inicialização padrão (Pilar 4)

```
init_default: todos os eixos → 0.5

Exceções:
  S7_COERENCIA        [6]  → 1.0
  S5_ENTROPIA         [4]  → 0.5
  P6_CONFIANCA        [29] → 0.5
  P1_QUANTIZACAO      [24] → 0.8
  D2_TAXA_APRENDIZADO [9]  → 0.5
  G7_K_INTERACAO      [22] → 0.1
```

### As 5 Âncoras C5 — valores exatos

Eixos não listados = 0.5 por padrão.

```
ANCORA_1 presenca:  S1=1.0  S5=0.0  S7=1.0  P6=1.0  G1=1.0  G4=0.5  D4=1.0  P4=0.0
ANCORA_2 ausencia:  S1=0.0  S5=0.0  S7=1.0  P6=1.0  G1=0.3  G4=0.5  D4=1.0  G3=0.0
ANCORA_3 mudanca:   S1=0.5  S5=0.5  D2=1.0  D4=0.0  D8=0.0  G8=1.0  G4=0.5  D3=0.7
ANCORA_4 agencia:   S1=1.0  S5=0.2  P6=0.8  G1=0.8  G3=0.8  D6=1.0  G8=0.7  D2=0.6
ANCORA_5 incerteza: S5=1.0  P4=0.8  P6=0.1  S7=0.2  D4=0.2  G7=0.1  P1=0.9  S6=0.2
```

---

## 3. Constantes e Fórmulas dos Pilares Dinâmicos

```
K_BASE = 0.1
K_MIN  = 0.01
K_MAX  = 2.0

# Pilar 5 — Gravidade
F(a,b) = K_real * (G1_a * G1_b) / DIST(a,b)^2
K_real = K_final * K_MAX

# Pilar 6 — Quantização dinâmica (ordem obrigatória R25)
P1_raw   = 1.0 - sigmoid(G1_MASSA * S6_DENSIDADE * K_final)
P1_novo  = (1 - D5) * P1_raw + D5 * P1_anterior    <- histerese ANTES
P1_final = clamp(P1_novo, 0.0, 1.0)

# Pilar 7 — K adaptativo
K_global = K_BASE * log(1 + total_interacoes)
K_local  = K_global * P6_CONFIANCA_regiao
K_final  = clamp(K_local, K_MIN, K_MAX)
G7_normalizado = K_final / K_MAX    <- valor que fica no eixo G7

# Pilar 8 — Estabilidade (4 mecanismos)
1. clamp([0,1]) em todos os eixos após cada update (R22)
2. decaimento: sem[i] *= exp(-D3 * delta_t_s)  — só eixos de magnitude, não bipolares
3. histerese:  novo = (1-D5)*calculado + D5*anterior  — aplicar R24: ANTES do update
4. smooth:     delta = sigmoid(raw_delta) * taxa_aprendizado
```

---

## 4. Mapa Completo de Impacto por Arquivo

### 4.1 REESCREVER COMPLETAMENTE

#### `python/leet/axes.py`
- Remove enum `AxisGroup` e função `axes_in_group()`
- Remove todas as constantes A0–C10
- Cria enum `AxisBlock` (SEMANTIC, DYNAMIC, GRAVITY, PRECISION)
- Cria função `axes_in_block(block: AxisBlock) -> list[AxisInfo]`
- Cria constantes S1_INTENCAO=0 ... P8_LATENCIA=31
- Cada `AxisInfo`: `index, code, name, description, block, axis_type`
  - `axis_type`: "magnitude" (0=min, 1=max) ou "bipolar" (0.5=neutro)
  - Bipolares: G3_AFINIDADE, G4_TEMPORALIDADE, G8_GRADIENTE
- Atualiza `CANONICAL_AXES` com os 32 novos eixos

#### `leet1337/leet-core/src/axes.rs`
- Espelha `axes.py`
- Remove `AxisGroup`, constantes A0–C10
- Cria `AxisBlock`, constantes `pub const S1_INTENCAO: usize = 0;` ... `pub const P8_LATENCIA: usize = 31;`
- `BIPOLAR_AXES: [usize; 3] = [18, 19, 23]` — usado pelo decay do Pilar 8

#### `python/leet/types.py`
- `Cogon`: remove campo `unc`
- `Cogon.new(sem: list[float])` — sem parâmetro unc
- `Cogon.zero()` — usa `SEM_ZERO` (32 valores específicos da seção 2)
- `Cogon.is_zero()` — compara com `SEM_ZERO`
- `Cogon.confidence` — property: `return self.sem[P6_CONFIANCA]`
- `Cogon.low_confidence()` — bool: `return self.sem[P6_CONFIANCA] < 0.1`
- Remove `Cogon.low_confidence_dims()`
- `Cogon.to_json()` / `from_json()` — sem campo unc
- `ANCHOR_VECTORS: dict[str, list[float]]` — 5 âncoras com valores exatos
- `get_anchor_cogons() -> list[Cogon]` — retorna COGONs das 5 âncoras
- Helper `_build_anchor(overrides: dict[int, float]) -> list[float]` — constrói vetor[32] com 0.5 + overrides

#### `leet1337/leet-core/src/types.rs`
- Struct `Cogon`: remove campo `unc: [f32; 32]`
- `Cogon::zero()` — usa SEM_ZERO com 32 valores
- Remove todos os métodos com `.unc`
- `fn confidence(&self) -> f32` — retorna `self.sem[P6_CONFIANCA]`
- `fn low_confidence(&self) -> bool` — `self.sem[P6_CONFIANCA] < 0.1`
- `ANCHOR_VECTORS` e `get_anchor_cogons()` espelhando Python

#### `python/leet/operators.py`
- `blend(c1, c2, alpha)` — regras por bloco:
  - Bloco S [0–7]: `alpha*c1[i] + (1-alpha)*c2[i]` (linear)
  - Bloco D [8–15]: linear exceto `D4_ESTABILIDADE [11] = min(c1[11], c2[11])`
  - Bloco G [16–23]: linear exceto:
    - `G1_MASSA [16] = clamp(c1[16] + c2[16], 0.0, 1.0)`
    - `G7_K_INTERACAO [22] = max(c1[22], c2[22])`
  - Bloco P [24–31]: linear exceto `P6_CONFIANCA [29] = min(c1[29], c2[29])`
  - Aplica `clamp_all()` ao final (R22)
- `dist(c1, c2)`:
  - `w = (c1.sem[P6_CONFIANCA] + c2.sem[P6_CONFIANCA]) / 2.0`
  - Distância cosseno ponderada por `w`
  - Remove referência a `.unc`
- `anomaly_score(c, history)`:
  - Centroide ponderado por `G1_MASSA = h.sem[G1_MASSA]` de cada COGON
  - Remove referência a `.unc`
- `apply_patch(base, patch)`:
  - Aplica `clamp_all()` ao final (R22)
- `focus(c, dims)`:
  - Eixos não selecionados: `sem=0.0` (sem unc)
- Remove qualquer referência a `.unc` em todas as funções

#### `leet1337/leet-core/src/operators.rs`
- Espelha todas as mudanças acima

---

### 4.2 MUDANÇA PARCIAL SIGNIFICATIVA

#### `python/leet/dynamics.py` — ARQUIVO NOVO
Implementa os Pilares 4–8 como módulo isolado:

```python
K_BASE: float = 0.1
K_MIN:  float = 0.01
K_MAX:  float = 2.0

def init_sem() -> list[float]:
    """Pilar 4 — sem[32] com defaults de boot."""
    # todos 0.5, exceto exceções listadas na seção 2

def compute_k(total_interactions: int, p6_regional: float) -> float:
    """Pilar 7 — K_final = clamp(K_BASE * log(1+n) * p6, K_MIN, K_MAX)"""

def normalize_k(k_final: float) -> float:
    """G7_normalizado = k_final / K_MAX"""

def gravitational_force(g1_a: float, g1_b: float,
                        dist_ab: float, k_final: float) -> float:
    """Pilar 5 — F = K_real * (G1_a * G1_b) / max(dist_ab, 1e-6)^2"""

def compute_quantization(g1_massa: float, s6_densidade: float,
                         k_final: float, p1_prev: float,
                         d5_histerese: float) -> float:
    """Pilar 6 — P1 dinâmico.
    1. P1_raw  = 1 - sigmoid(g1 * s6 * k)
    2. P1_novo = (1-d5)*P1_raw + d5*p1_prev   <- histerese (R24)
    3. return clamp(P1_novo, 0, 1)
    """

def apply_decay(sem: list[float], d3: float, delta_t_s: float) -> list[float]:
    """Pilar 8.2 — decaimento exponencial.
    Eixos bipolares [18, 19, 23] não decaem.
    Retorna nova lista (não modifica in-place).
    """

def apply_hysteresis(new_val: float, prev_val: float, d5: float) -> float:
    """(1 - d5) * new_val + d5 * prev_val"""

def apply_smooth_update(raw_delta: float, taxa: float) -> float:
    """sigmoid(raw_delta) * taxa"""

def clamp_all(sem: list[float]) -> list[float]:
    """R22 — clamp(v, 0.0, 1.0) para cada v. Retorna nova lista."""

def dynamic_update(cogon, total_interactions: int,
                   prev_sem: list[float] | None = None) -> "Cogon":
    """Passo 6 do ciclo de vida.
    Ordem obrigatória:
    1. compute_k -> k_final
    2. compute_quantization -> P1 novo
    3. apply_decay via D3
    4. G1_MASSA reforçado: clamp(G1 * (1 + 0.01 * k_final), 0, 1)
    5. clamp_all (R22)
    6. G7 = normalize_k(k_final)
    Retorna novo Cogon com mesmo id e stamp originais.
    """
```

#### `leet1337/leet-core/src/dynamics.rs` — ARQUIVO NOVO
Espelha `dynamics.py` em Rust. Usa constantes de `axes.rs`.

#### `python/leet/validate.py`
- R5: `sem[P6_CONFIANCA] < 0.1` (era `unc[i] > 0.9`)
- `check_confidence(msg) -> list[str]`: IDs de COGONs onde P6 < 0.1
- R10: remove menção a `unc` na mensagem de erro
- R22: valida `sem[i] ∈ [0.0, 1.0]` para todos i — erro se fora
- R23: valida `G7_K_INTERACAO ∈ [0.0, 1.0]` (normalizado)
- R24: COGON com `D5_HISTERESE > 0` deve ter `stamp != 0`
- R25: RAW EVIDENCE não pode setar `P1_QUANTIZACAO` (índice 24)
- Remove qualquer validação que menciona `unc`
- Atualiza mensagens de erro para nomes de eixos v0.5

#### `leet1337/leet-core/src/validate.rs`
- Espelha todas as mudanças de `validate.py`

#### `python/leet/bridge.py`
- Remove fórmula de recompute `unc`
- `MockProjector` — nova tabela keyword→eixo v0.5:
  ```
  SEMÂNTICA
  urgente, crítico, emergência   → S1↑0.9, S5↓0.2
  claro, definitivo, certeza     → S7↑0.9, P6↑0.8, S2↓0.1
  ambíguo, talvez, incerto       → S2↑0.8, S5↑0.7, P6↓0.2, P4↑0.6
  importante, essencial          → S6↑0.8, S1↑0.7
  complexo, múltiplo             → S2↑0.6, P2↑0.7

  DINÂMICA
  mudança, evolução, aprende     → D2↑0.8, D4↓0.3, G8↑0.7
  estável, permanente, fixo      → D4↑0.9, D3↓0.1, D8↑0.7
  rápido, imediato               → D8↓0.1, D2↑0.7, P8↓0.1
  devagar, gradual               → D8↑0.7, D5↑0.6
  anomalia, erro, falha          → D4↓0.2, S5↑0.7, G8↑0.8, P4↑0.6

  GRAVIDADE
  amor, afeto, conexão           → G3↑0.9, S6↑0.7, D6↑0.6
  rejeição, distância, oposto    → G3↓0.1, G2↑0.8
  causa, porque, origem          → G8↑0.7, D1↑0.7
  sistema, rede, protocolo       → D6↑0.8, G6↑0.7, G5↑0.6
  passado, histórico             → G4↓0.1, S4↑0.7
  futuro, plano                  → G4↑0.9, D2↑0.6

  PRECISÃO
  prova, verificável, dados      → P6↑0.8, P4↓0.1, S7↑0.7
  ruído, impreciso, estimativa   → P4↑0.7, P6↓0.3, P1↑0.6
  comprimido, resumo             → P3↑0.8, S6↑0.7
  detalhado, específico          → P2↑0.8, P5↑0.7
  caro, pesado, lento            → P7↑0.7, P8↑0.6
  ```
- `AnthropicProjector` — novo prompt interno:
  ```
  Analise o texto e projete em 32 eixos semânticos em 4 blocos.

  BLOCO 1 SEMÂNTICA [0–7]: INTENCAO, AMBIGUIDADE, CONTEXTO_LOCAL,
  CONTEXTO_GLOBAL, ENTROPIA, DENSIDADE, COERENCIA, ALINHAMENTO

  BLOCO 2 DINAMICA [8–15]: PESO_CONEXAO, TAXA_APRENDIZADO, DECAIMENTO,
  ESTABILIDADE, HISTERESE, PROPAGACAO, SATURACAO, INERCIA

  BLOCO 3 GRAVIDADE [16–23]: MASSA, DISTANCIA, AFINIDADE*,
  TEMPORALIDADE*, CAMPO_LOCAL, CAMPO_GLOBAL, K_INTERACAO, GRADIENTE*

  BLOCO 4 PRECISAO [24–31]: QUANTIZACAO, GRANULARIDADE, COMPRESSAO,
  RUIDO, RESOLUCAO, CONFIANCA, CUSTO, LATENCIA

  *Eixos bipolares: 0.0=extremo negativo, 0.5=neutro, 1.0=extremo positivo.
  Retorne APENAS JSON: {"sem": [32 floats entre 0.0 e 1.0]}
  ```
- `decode(cogon)` — reescreve lógica de reconstrução de texto:
  - Identifica 3–5 eixos com valores mais extremos (maior |sem[i] - 0.5|)
  - Para cada eixo dominante, gera fragmento descritivo baseado no bloco e valor
  - Concatena fragmentos em texto coerente
  - Exemplo: G1=0.9 → "altamente relevante"; S5=0.8 → "com alta incerteza informacional"; G3=0.1 → "com forte repulsão/diferenciação"

#### `python/leet/context.py`
- Remove referências a `unc` em `ContextManager`
- `get_context_cogon()` retorna `Cogon` sem unc
- `adjust_projection(sem, unc, alpha)` → `adjust_projection(sem, alpha)`
- Perfis embutidos v0.5:
  ```
  "technical":     dominant=[S7_COERENCIA, D4_ESTABILIDADE, P6_CONFIANCA, D6_PROPAGACAO, G6_CAMPO_GLOBAL]
  "emergency":     dominant=[S1_INTENCAO, G1_MASSA, G8_GRADIENTE, D2_TAXA_APRENDIZADO, D4_ESTABILIDADE]
  "philosophical": dominant=[S6_DENSIDADE, S7_COERENCIA, P2_GRANULARIDADE, G3_AFINIDADE, S4_CONTEXTO_GLOBAL]
  "planning":      dominant=[G4_TEMPORALIDADE, D2_TAXA_APRENDIZADO, S4_CONTEXTO_GLOBAL, D3_DECAIMENTO]
  "social":        dominant=[G3_AFINIDADE, S8_ALINHAMENTO, D6_PROPAGACAO, S6_DENSIDADE, G5_CAMPO_LOCAL]
  ```
  - Cada perfil tem `axis_weights[32]` com 0.5 padrão e overrides nos eixos dominantes (0.7–0.95)
- `detect_context_drift()`: usa DIST com nova ponderação P6

#### `python/leet/wire.py` e `leet1337/leet-core/src/wire.rs`
- Remove completamente a função de recompute unc
- `WireCogon.encode`: `id(16B) + sem[32×f32=128B] + stamp(8B)` = 152B — sem unc
- `WireCogon.decode`: retorna `Cogon` sem unc
- Remove qualquer struct/campo relacionado a unc
- `SparseDelta`: sem mudança — funciona sobre sem[32]
- Atualiza docstrings

#### `python/leet/client/agent.py`
- `Agent1337.__init__`: adiciona `self.total_interactions: int = 0`
- Novo método `_dynamic_update(cogon: Cogon) -> Cogon`:
  - Chama `dynamics.dynamic_update(cogon, self.total_interactions)`
  - Incrementa `self.total_interactions`
- Ciclo de recebimento: insere `_dynamic_update()` como Passo 6 (entre absorção e avaliação de anomalia)
- Remove referências a `.unc` na construção/inspeção de COGONs
- `send_assert/query/delta/anomaly/ack`: usa `Cogon.new(sem=...)` sem unc

#### `python/leet/__init__.py`
- Remove: constantes A0–C10, `AxisGroup`, `axes_in_group`
- Adiciona: constantes S1–P8, `AxisBlock`, `axes_in_block`
- Adiciona: `init_sem`, `dynamic_update`, `compute_k`, `clamp_all` de `dynamics`
- Atualiza `check_confidence` para nova assinatura (`list[str]` de IDs)
- Atualiza `get_anchor_cogons` se não estava exportada antes

#### `python/leet/cli.py`
- `leet axes --group A/B/C` → `leet axes --block S/D/G/P`
- `leet inspect`: remove campo unc do output
- `leet zero`: output do COGON_ZERO com 32 valores v0.5
- Help text e exemplos atualizados

#### `leet1337/leet-cli/src/main.rs`
- `leet axes --group` → `leet axes --block`
- Remove menções a unc no output de todos os comandos

#### `leet1337/leet-service/src/projection/engine.rs`
- Substitui índices hardcoded de eixos antigos por constantes de `axes.rs`
- Remove qualquer campo que retorna ou propaga unc
- Verifica: se `engine.rs` usa indices como 22 (C1_URGENCIA v0.4) → atualiza para constante v0.5 correta

#### `comparison_1337_vs_english.py`
- Substitui índices hardcoded por constantes v0.5:
  - `sem[22]` (C1_URGENCIA) → `sem[S1_INTENCAO]` (índice 0)
  - `sem[26]` (C5_ANOMALIA) → `sem[S5_ENTROPIA]` (índice 4)
  - `sem[27]` (C6_AFETO)    → `sem[G3_AFINIDADE]` (índice 18)
- Atualiza relatório de saída para mostrar nomes de eixos v0.5

#### `leet-py/leet/providers.py`
- Remove qualquer projeção interna que gera `.unc`
- Retorna `Cogon` sem unc em todos os providers
- Atualiza imports de constantes de eixo

#### `leet-py/leet/agent.py`
- Remove referências a `.unc` na construção de COGONs
- `AgentContext.cogon` — sem unc

#### `setup.py`
- Se exibe lista de eixos, atualiza para blocos S/D/G/P
- Remove menções a unc

---

### 4.3 SEM MUDANÇA (verificar apenas ausência de unc e índices antigos)

```
python/leet/cache.py
python/leet/batch.py
python/leet/metrics.py
python/leet/config.py
python/leet/adapters/ (todos os 5 arquivos)
leet-py/leet/__init__.py
leet-py/leet/client.py
leet-py/leet/network.py
leet-py/leet/response.py
leet-py/leet/stats.py
leet1337/leet-service/ (SIMD, BatchQueue, LRU — agnósticos)
docker-compose.yml
Dockerfile
```

---

## 5. Mudanças nos Testes

### Reescrever completamente
- `tests/test_axes.py`: 4 blocos S/D/G/P, constantes, `axes_in_block()`, eixos bipolares
- `tests/test_types.py`: `Cogon.new(sem)` sem unc, `Cogon.zero()` com SEM_ZERO exato, `confidence`, âncoras

### Atualizar
- `tests/test_operators.py`:
  - BLEND: testa G1 acumula, P6 conservador, D4 conservador, G7 máximo
  - DIST: testa ponderação por P6
  - ANOMALY_SCORE: testa ponderação por G1_MASSA
- `tests/test_validate.py`: R5 novo, R22–R25
- `tests/test_bridge.py`: MockProjector com novos índices v0.5
- `tests/test_wire.py`: sem campo unc no encode/decode

### Criar novo
`tests/test_dynamics.py`:
```
test_init_sem_defaults()
test_init_sem_all_in_range()
test_compute_k_zero_interactions_returns_k_min()
test_compute_k_grows_with_interactions()
test_compute_k_never_exceeds_k_max()
test_compute_k_never_below_k_min()
test_gravitational_force_proportional_to_mass()
test_gravitational_force_inverse_square_distance()
test_compute_quantization_high_mass_gives_low_p1()
test_compute_quantization_low_mass_gives_high_p1()
test_compute_quantization_applies_hysteresis()
test_apply_decay_reduces_magnitude_axes()
test_apply_decay_preserves_bipolar_axes()  <- G3[18], G4[19], G8[23]
test_apply_hysteresis_smooths_transition()
test_clamp_all_upper_boundary()
test_clamp_all_lower_boundary()
test_clamp_all_preserves_valid_values()
test_dynamic_update_returns_new_cogon_not_same_object()
test_dynamic_update_g7_normalized_in_range()
test_dynamic_update_p1_changes()
test_dynamic_update_clamp_applied_r22()
test_dynamic_update_g1_massa_increases_with_use()
test_anchor_vectors_all_five_present()
test_anchor_vectors_all_32_dims()
test_anchor_vectors_all_in_range()
test_anchor_presenca_s1_max()
test_anchor_incerteza_p6_low()
```

---

## 6. Documentação

### `README.md` (raiz)
- Seção "Features":
  - `"32 eixos canônicos em 3 grupos"` → `"32 eixos em 4 blocos: Semântica (S), Dinâmica (D), Gravidade (G), Precisão (P)"`
  - Remove menção a `unc[32]`
  - Adiciona: `"Pilares dinâmicos 4–8: gravidade adaptativa, quantização dinâmica, K adaptativo, estabilidade"`
- Seção "Conceitos — COGON":
  - Remove `unc[32]` da definição
  - Atualiza: "incerteza vive nos eixos S5_ENTROPIA, P4_RUIDO, P6_CONFIANCA, S7_COERENCIA"
- Seção "Os 32 Eixos Canônicos" (seção 12):
  - Substitui tabelas A/B/C pelas tabelas S/D/G/P
  - Adiciona coluna "Tipo" (magnitude/bipolar)
- Atualiza todos os exemplos de código:
  - `sem[22] = 0.95` (C1_URGENCIA) → `sem[S1_INTENCAO] = 0.9`
  - `sem[26] = 0.88` (C5_ANOMALIA) → `sem[S5_ENTROPIA] = 0.8`
  - `sem[27] = 0.88` (C6_AFETO)    → `sem[G3_AFINIDADE] = 0.9`
- Adiciona seção "Pilares Dinâmicos" com fórmulas e referência a `dynamics.py`
- Atualiza seção "Wire Format": remove menção ao recompute unc

### Docstrings internas
- `axes.py`: descrição completa por eixo com tipo e bloco
- `operators.py`: BLEND com nota das regras por bloco; DIST com nota de P6
- `validate.py`: R22–R25 inline
- `dynamics.py`: já especificadas na seção 5
- `types.py`: COGON_ZERO com comentário por linha; âncoras com referência ao spec

---

## 7. Ordem de Execução dos Prompts Claude Code

Dependências determinam a ordem obrigatória:

```
PROMPT_01: axes.py + axes.rs
           Tudo depende dos índices. Primeiro obrigatório.
           Entrega: constantes S1–P8, AxisBlock, axes_in_block(), BIPOLAR_AXES

PROMPT_02: types.py + types.rs
           Depende de axes (índices para SEM_ZERO e âncoras).
           Entrega: Cogon sem unc, COGON_ZERO, ANCHOR_VECTORS, get_anchor_cogons()

PROMPT_03: dynamics.py + dynamics.rs
           Depende de axes e types.
           Entrega: Pilares 4–8, init_sem, dynamic_update, compute_k, clamp_all

PROMPT_04: operators.py + operators.rs
           Depende de axes, types, dynamics (clamp_all).
           Entrega: BLEND por bloco, DIST por P6, ANOMALY_SCORE por G1_MASSA

PROMPT_05: validate.py + validate.rs
           Depende de axes e types.
           Entrega: R5 atualizada, R22–R25

PROMPT_06: bridge.py + context.py + wire.py + wire.rs
           Depende de tudo acima.
           Entrega: MockProjector v0.5, AnthropicProjector novo prompt,
                    perfis de contexto v0.5, wire sem unc

PROMPT_07: agent.py + __init__.py + cli.py + leet-cli/main.rs
           + comparison_1337_vs_english.py + leet-py patches
           + engine.rs (verificar índices hardcoded)
           Depende de tudo acima.
           Entrega: Passo 6 ciclo de vida, exports corretos, CLI atualizado

PROMPT_08: tests/ + README.md + docstrings
           Depende de tudo acima.
           Entrega: test_dynamics.py (25 testes), demais testes atualizados,
                    README com tabelas v0.5
```

---

## 8. Critérios de Conclusão do Branch

### Ausência de v0.4
- [ ] `grep -r "\.unc" python/ leet1337/` — zero resultados
- [ ] `grep -r "AxisGroup\|axes_in_group\|A0_VIA\|C1_URGENCIA\|C5_ANOMALIA" python/ leet1337/` — zero resultados
- [ ] `grep -r "unc\[" python/ leet1337/` — zero resultados

### Corretude estrutural
- [ ] `Cogon.zero().sem` == `SEM_ZERO` (32 valores exatos)
- [ ] `hasattr(Cogon.new([0.5]*32), 'unc')` == False
- [ ] `len(get_anchor_cogons())` == 5
- [ ] Cada âncora tem `len(sem)` == 32 e todo `sem[i] ∈ [0.0, 1.0]`

### Corretude dos operadores
- [ ] `blend(c1, c2, 0.5).sem[16]` == `min(c1.sem[16]+c2.sem[16], 1.0)` (G1 acumula)
- [ ] `blend(c1, c2, 0.5).sem[29]` == `min(c1.sem[29], c2.sem[29])` (P6 conservador)
- [ ] `blend(c1, c2, 0.5).sem[11]` == `min(c1.sem[11], c2.sem[11])` (D4 conservador)
- [ ] `blend(c1, c2, 0.5).sem[22]` == `max(c1.sem[22], c2.sem[22])` (G7 máximo)
- [ ] `dist(c1, c2)` usa P6 médio como peso — verificável via teste unitário

### Corretude dos pilares
- [ ] `compute_k(0, 0.5)` == `K_MIN` (log(1) = 0)
- [ ] `compute_k(10**6, 1.0)` == `K_MAX`
- [ ] `compute_quantization(0.9, 0.9, 1.0, 0.5, 0.0)` < 0.5
- [ ] `compute_quantization(0.1, 0.1, 0.01, 0.5, 0.0)` > 0.7
- [ ] `apply_decay(sem, 0.5, 1.0)[18]` == `sem[18]` (G3 bipolar não decai)
- [ ] `clamp_all([2.0, -0.5, 0.7])` == `[1.0, 0.0, 0.7]`

### Corretude das regras
- [ ] R5: `validate(msg_com_P6_zero)` retorna aviso
- [ ] R22: `validate(msg_com_sem_2_0)` retorna erro
- [ ] R25: validate rejeita RAW EVIDENCE com P1 setado

### Testes
- [ ] `pytest python/tests/ -q` — 0 failures
- [ ] `cargo test -p leet-core` — 0 failures
- [ ] `python -m pytest python/tests/test_dynamics.py -v` — >= 25 testes passando

---

## 9. Fora do Escopo

- W matrix calibration pipeline
- leet-service: BLAS/CUDA/Metal (não mexer)
- PersonalStore
- Novos adaptadores IDE
- Benchmark `comparison_1337_vs_english.py` completo (só atualiza índices hardcoded)

---

*Spec de referência: `1337_spec_v0.5.docx`*
*Próximo passo: geração de PROMPT_01–08 para Claude Code*
