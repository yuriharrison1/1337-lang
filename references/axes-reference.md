# 1337 — 32 Canonical Axes Reference

## Group A — Ontological (0–13): What IS the concept?

| Idx | Code | Name | Range | Keywords |
|-----|------|------|-------|----------|
| 0 | A0 | VIA | 0=relational, 1=self-existent | essência, absoluto, per se |
| 1 | A1 | CORRESPONDÊNCIA | 0=unique, 1=mirrors other scales | padrão, fractal, análogo |
| 2 | A2 | VIBRAÇÃO | 0=static, 1=continuous flux | fluxo, transformação, dinâmico |
| 3 | A3 | POLARIDADE | 0=neutral, 1=strongly polar | extremo, oposto, dualidade |
| 4 | A4 | RITMO | 0=irregular, 1=clear cycle | ciclo, periódico, pulso |
| 5 | A5 | CAUSA E EFEITO | 0=pure effect, 1=prime cause | causa, gera, provoca |
| 6 | A6 | GÊNERO | 0=receptive, 1=active/generative | ativo, inicia, cria |
| 7 | A7 | SISTEMA | 0=isolated element, 1=emergent set | sistema, rede, conjunto |
| 8 | A8 | ESTADO | 0=undefined, 1=clear configuration | estado, condição, modo |
| 9 | A9 | PROCESSO | 0=static, 1=transformation-in-time | processo, evolui, muda |
| 10 | A10 | RELAÇÃO | 0=autonomous, 1=relational | relação, entre, conecta |
| 11 | A11 | SINAL | 0=no information, 1=information-rich | sinal, dados, indica |
| 12 | A12 | ESTABILIDADE | 0=chaotic/divergent, 1=stable/convergent | estável, equilíbrio, caos |
| 13 | A13 | VALÊNCIA ONTOLÓGICA | 0=negative/contractive, 0.5=neutral, 1=positive | positivo, negativo |

## Group B — Epistemic (14–21): What do we KNOW?

| Idx | Code | Name | Range | Keywords |
|-----|------|------|-------|----------|
| 14 | B1 | VERIFICABILIDADE | 0=unfalsifiable, 1=externally verifiable | provado, medido, verificado |
| 15 | B2 | TEMPORALIDADE | 0=timeless, 1=precise temporal anchor | agora, ontem, às 14h |
| 16 | B3 | COMPLETUDE | 0=open/building, 1=closed/conclusive | completo, resolvido, pendente |
| 17 | B4 | CAUSALIDADE | 0=opaque origin, 1=clear cause | porque, devido a, originou |
| 18 | B5 | REVERSIBILIDADE | 0=irreversible, 1=fully reversible | rollback, desfaz, permanente |
| 19 | B6 | CARGA | 0=automatic/fluid, 1=heavy cognitive load | complexo, difícil, simples |
| 20 | B7 | ORIGEM | 0=pure assumption, 1=direct observation | vi, medido, inferido |
| 21 | B8 | VALÊNCIA EPISTÊMICA | 0=contradictory, 0.5=inconclusive, 1=confirmatory | confirma, contradiz |

## Group C — Pragmatic (22–31): What to DO?

| Idx | Code | Name | Range | Keywords |
|-----|------|------|-------|----------|
| 22 | C1 | URGÊNCIA | 0=no rush, 1=critical emergency | urgente, agora, crítico, imediato |
| 23 | C2 | IMPACTO | 0=harmless, 1=high system impact | impacto, consequência, afeta |
| 24 | C3 | AÇÃO | 0=informational, 1=demands execution | faça, execute, implemente |
| 25 | C4 | VALOR | 0=axiologically neutral, 1=deeply meaningful | importante, valor, significado |
| 26 | C5 | ANOMALIA | 0=within norm, 1=strong rupture | anomalia, erro, falha, caiu |
| 27 | C6 | AFETO | 0=emotionally neutral, 1=high affective charge | amor, raiva, alegria, medo |
| 28 | C7 | DEPENDÊNCIA | 0=autonomous, 1=fully coupled | depende, precisa, requer |
| 29 | C8 | VETOR TEMPORAL | 0=past, 0.5=present, 1=future | ontem, agora, amanhã, futuro |
| 30 | C9 | NATUREZA | 0=noun/thing, 1=verb/action | fazer, ser, acontecer |
| 31 | C10 | VALÊNCIA AÇÃO | 0=alert/contractive, 0.5=neutral, 1=confirmation/expansive | confirma, alerta |

## MockProjector Keyword Mappings

```python
KEYWORD_MAP = {
    # Group C — most action-relevant
    "urgente|crítico|emergência|imediato|agora":  {22: 0.9},   # C1 URGÊNCIA
    "impacto|consequência|afeta|muda":            {23: 0.8},   # C2 IMPACTO
    "faça|execute|implemente|ação":               {24: 0.85},  # C3 AÇÃO
    "anomalia|erro|falha|caiu|bug":               {26: 0.9, 8: 0.8},  # C5 + A8
    "amor|afeto|sente|emoção":                    {27: 0.85}, # C6 AFETO
    "futuro|amanhã|planejado|próximo":            {29: 0.9},  # C8 vetor futuro
    "passado|ontem|histórico|anterior":           {29: 0.1},  # C8 vetor passado

    # Group A — ontological
    "sistema|rede|infraestrutura":                {7: 0.9},   # A7 SISTEMA
    "estado|status|condição|modo":                {8: 0.85},  # A8 ESTADO
    "processo|pipeline|fluxo|workflow":           {9: 0.85},  # A9 PROCESSO

    # Group B — epistemic
    "provado|verificado|medido|confirmado":       {14: 0.9},  # B1 VERIFICABILIDADE
    "porque|causa|motivo|devido":                 {17: 0.85}, # B4 CAUSALIDADE
    "rollback|reversível|desfaz":                 {18: 0.9},  # B5 REVERSIBILIDADE
}
```

## Rust Constants (axes.rs)
```rust
pub const A0_VIA: usize = 0;
pub const A1_CORRESPONDENCIA: usize = 1;
// ... (A2–A13)
pub const B1_VERIFICABILIDADE: usize = 14;
// ... (B2–B8)
pub const C1_URGENCIA: usize = 22;
pub const C2_IMPACTO: usize = 23;
pub const C3_ACAO: usize = 24;
pub const C4_VALOR: usize = 25;
pub const C5_ANOMALIA: usize = 26;
pub const C6_AFETO: usize = 27;
pub const C7_DEPENDENCIA: usize = 28;
pub const C8_VETOR_TEMPORAL: usize = 29;
pub const C9_NATUREZA: usize = 30;
pub const C10_VALENCIA_ACAO: usize = 31;
```
