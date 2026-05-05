# FASE 11 — TOKEN OPTIMIZATION (CONSOLIDAÇÃO HIERÁRQUICA + INTENT=DELTA)

Esta fase resolve o problema que tu apontou: "comunicação não acaba com o fato de ter sempre que carregar todo o contexto novamente. Modificando só o delta e aí acaba economizando tokens."

A resposta tem dois lados, ambos cobertos aqui:

1. **Consolidação hierárquica** (PROMPT_11a–11d): a cada 7 COGONs no mesmo nível, BLEND_N comprime em 1 COGON do próximo nível. Recall lê do nível mais alto pra baixo. **Custo de recall fica logarítmico em relação ao tamanho do projeto** — 5000 records gastam aproximadamente os mesmos tokens que 50.

2. **Intent=DELTA** (PROMPT_11e): a interface formal da spec § 8 que entrega só o patch entre dois estados. Útil pra agentes nativos 1337 no futuro; presente agora pra compliance e pra avalanche de uso futura.

---

## OS 5 PROMPTS DESTA FASE

| # | Arquivo | Escopo |
|---|---|---|
| 11a | `PROMPT_11a_consolidation.md` | `.leet/index.bin` sidecar + auto-trigger BLEND_N (threshold 7) |
| 11b | `PROMPT_11b_recall_delta_aware.md` | `leet_recall` retorna foundation + mid + raw |
| 11c | `PROMPT_11c_consolidate_cli.md` | `leet consolidate {inspect, force, rebuild-index}` CLI |
| 11d | `PROMPT_11d_skill_update.md` | Skill atualizada: como ler tiered recall |
| 11e | `PROMPT_11e_intent_delta.md` | `leet_recall_delta` tool spec-compliant (opt-in) |

---

## ORDEM DE EXECUÇÃO

```
11a (consolidação + index.bin)        ← fundação
   │
   ▼
11b (recall delta-aware)              ← lê o que 11a produz
   │
   ▼
11c (CLI manual)                      ← depende de leet-mcp ter [lib]; reusa funções de 11a
   │
   ▼
11d (skill update)                    ← ensina Claude a interpretar 11b
   │
   ▼
11e (intent=DELTA, opt-in)            ← independente; só requer 11a
```

11d e 11e podem ir em paralelo (11d depende de 11b ter aterrissado, mas não de 11c ou 11e).

Cada um com `cargo test --workspace` verde antes de avançar.

---

## DECISÕES CRAVADAS (REGISTRO PRA POSTERIDADE)

Tu escolheu, durante o planejamento, isso aqui:

| Pergunta | Resposta cravada |
|---|---|
| Quantos COGONs disparam consolidação | **N = 7** (mais detalhe preservado) |
| Estratégia BLEND_N | **Híbrido**: G1-weighted centroid + per-block rules (D4 min, G1 acumula, G7 max, P6 min) |
| Onde mora a metadata | **`.leet/index.bin`** paralelo (separa concerns, store.bin imutável) |
| Caminho da otimização | **Ambos**: consolidação agora + intent=DELTA depois |
| Quando consolidar | **Automático** ao atingir N |

---

## EXPERIÊNCIA RESULTANTE

### Antes (pós-fase 10)

```
Sessão #50:
  leet_recall →  [5 entries]  ~800 tokens
  Conversa rola normalmente.
  leet_remember × 3 ao longo do dia →  3 records novos
  Store: 50 records, todos no mesmo nível.

Sessão #100:
  leet_recall →  [5 entries]  ~800 tokens
  ...mas tu sabe que existem 100 records que não são considerados.
  Recall pode estar "perdendo" decisões importantes.
```

### Depois (pós-fase 11)

```
Sessão #50 (com auto-consolidação):
  Após o 7º remember: store consolida 7 raw em 1 L1.
  Após 49 remembers: 7 L1s consolidam em 1 L2.
  Store agora tem 1 L2 + 6 L1 + ≤6 raw = ≤13 live records.

  leet_recall →
    [0] L2 — "[L2×7] [L1×7] arquitetura inicial: FastAPI..."
    [1] L1 — "[L1×7] Auth: JWT, refresh tokens..."
    [2] raw — "Login endpoint working"
    [3] raw — "JWT validation pending"
    ...
  Total: ~1200 tokens, mas agora cobre 49+ decisões em vez de 5.

Sessão #100:
  Mesma estrutura, mesmo budget de tokens.
  log_7(100) ≈ 2.4 → quase nada muda em relação à sessão 50.
```

**O ganho assimptótico:** projeto que dura ano inteiro tem o mesmo custo de recall que projeto de uma semana.

---

## GATE GLOBAL DA FASE

Após executar 11a–e:

```bash
# Build + tests
cargo build --workspace
cargo test --workspace
cargo clippy --workspace -- -D warnings

# Smoke do pipeline inteiro
mkdir /tmp/leet-fase11 && cd /tmp/leet-fase11
for i in $(seq 1 50); do
  echo "{\"jsonrpc\":\"2.0\",\"id\":$i,\"method\":\"tools/call\",\"params\":{\"name\":\"leet_remember\",\"arguments\":{\"text\":\"decision $i\"}}}"
done | leet-mcp 2>/dev/null > /dev/null

# Inspect: deveria ter cascateado pra L2
leet consolidate inspect
# Esperado:
#   Pyramid:
#     L2: 1 live  (1 total, 0 consolidated)
#     L1: 0 live  (7 total, 7 consolidated)
#     L0: 1 live  (49 total, 48 consolidated)

# Recall normal (humano)
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"leet_recall","arguments":{"limit":10}}}' \
  | leet-mcp 2>/dev/null | jq -r '.result.content[0].text' | head -20
# Esperado: L2 + raw recente, output < 4KB

# Recall delta (spec-compliant)
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"leet_recall_delta","arguments":{}}}' \
  | leet-mcp 2>/dev/null | jq '.result.content[0].text' | jq -r .
# Esperado: { "intent": "DELTA", "patch": [32 floats], ... }
```

Se tudo bate, fase 11 está completa. O usuário agora tem:

- ✅ Memória persistente (fase 10)
- ✅ Memória que escala log com tamanho do projeto (fase 11a, 11b)
- ✅ Ferramentas pra debug e operação (fase 11c)
- ✅ Claude entendendo a hierarquia (fase 11d)
- ✅ Spec compliance pra futuro Mundo A (fase 11e)

---

## O QUE NÃO ESTÁ NESTA FASE

Coisas tentadoras que ficam fora do escopo de propósito:

- **Decay temporal**: COGONs antigos perderem peso automaticamente ao longo do tempo. A spec já tem D3_DECAY como axis, mas não é usado em consolidação. Decisão: deixar pra Fase 12 quando dados reais mostrarem se vale.
- **Recall cross-projeto**: store global agregando insights de múltiplos projetos. Decisão: violaria privacidade implícita; cada projeto é uma ilha por design.
- **Compactação dos próprios L2/L3**: hoje só level→level+1 cascateia. Recompactar L2s velhos com novos L2s seria um nível 4. Acontece automaticamente quando 7 L3s existirem (provavelmente nunca em projetos humanos), mas nada extra.
- **GC**: store.bin nunca encolhe. Decisão consciente — recuperação histórica completa é uma feature. `du -h .leet/` é ~360 bytes/record; um projeto de 5 anos pesa megabytes, não gigabytes.

---

## ARQUIVOS DESTA FASE

- `PROMPT_11a_consolidation.md`
- `PROMPT_11b_recall_delta_aware.md`
- `PROMPT_11c_consolidate_cli.md`
- `PROMPT_11d_skill_update.md`
- `PROMPT_11e_intent_delta.md`
- `README_fase_11.md` (este arquivo)
