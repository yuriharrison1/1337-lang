Você vai criar uma Claude Skill para o Projeto 1337 — uma linguagem de comunicação nativa entre agentes de IA.

A spec oficial é a v0.4 (32 eixos). Toda a especificação está abaixo — use SOMENTE ela como fonte de verdade.

## ESTRUTURA DA SKILL

```
1337-lang/
├── SKILL.md                          (< 500 linhas)
└── references/
    ├── spec-v0.4-compact.md          (spec formal completa compacta)
    ├── axes-reference.md             (32 eixos com descrições completas + guia de projeção)
    └── rust-implementation-guide.md  (arquitetura Rust + FFI + Python bindings)
```

## REQUISITOS DO SKILL.md

YAML frontmatter:
- name: 1337-lang
- description: bem pushy, deve triggar em qualquer menção de: 1337, COGON, COGON_ZERO, DAG semântico, espaço canônico, inter-agent communication language, bridge protocol, MSG_1337, vetores semânticos, UNC/incerteza vetorial, BLEND, FOCUS, DELTA, DIST, ANOMALY_SCORE, RAW BRIDGE, semantic vectors, zona emergente, handshake C5, eixos canônicos 32, valência ontológica/epistêmica/de ação. Também trigger quando o usuário quer implementar, codificar, testar ou debugar qualquer parte da 1337 em Rust ou Python.

Corpo do SKILL.md:
- Seção "What is 1337?" — 3-4 linhas explicando o conceito
- Quick reference table dos 5 primitivos (SCALAR, VECTOR, HASH, ID, RAW)
- Quick reference dos 3 compostos (COGON, EDGE, DAG)
- Quick reference do envelope MSG_1337 (campos na ordem canônica)
- Quick reference dos 6 intents (ASSERT, QUERY, DELTA, SYNC, ANOMALY, ACK)
- Quick reference dos 5 operadores com assinatura e precedência
- Quick reference dos 4 RAW roles (EVIDENCE, ARTIFACT, TRACE, BRIDGE)
- Quick reference dos 5 EDGE types com símbolos
- Quick reference das 6 camadas (C0-C5)
- Lista das 21 regras R1-R21 (uma linha cada)
- Seção "Implementation Architecture" explicando: Rust core + C ABI FFI + PyO3 Python bindings
- Referências cruzadas claras: "Read references/spec-v0.4-compact.md before writing any code", "Read references/axes-reference.md when projecting concepts", "Read references/rust-implementation-guide.md for Rust architecture"

## REQUISITOS DO references/spec-v0.4-compact.md

Spec v0.4 COMPLETA em formato compacto de referência rápida:
- COGON_ZERO com valores exatos (sem=[1]*32, unc=[0]*32, id=nil, stamp=0)
- Tipos primitivos com definições formais
- RAW structure com roles
- COGON, EDGE, DAG structures
- 6 camadas com gramática e mutabilidade
- Todos os 32 eixos em tabela (índice, código, nome, descrição curta de 1 linha)
- Zona Emergente com REGISTRO_EMERGENTE
- MSG_1337 envelope completo com todos os campos
- Regras R1-R21 completas
- Operadores com definições formais (BLEND, DIST, ANOMALY_SCORE)
- Ciclo de vida da mensagem (7 passos)
- Handshake C5 (4 fases)
- 5 Conceitos Âncora
- OO via RAW com tabela de equivalência e ordem de resolução de herança
- Interoperabilidade via RAW BRIDGE

## REQUISITOS DO references/axes-reference.md

Os 32 eixos com descrição COMPLETA:

**Grupo A — Ontológico (0-13):**
[0] A0 VIA — Grau em que o conceito existe por si mesmo, independente de relações externas. Alta = essência pura. Baixa = só existe em função de outro.
[1] A1 CORRESPONDÊNCIA — Grau em que o conceito espelha padrões em outros níveis de abstração. Alta = mesmo padrão em múltiplas escalas.
[2] A2 VIBRAÇÃO — Grau em que o conceito está em movimento/transformação contínua. Alta = fluxo constante. Baixa = estático.
[3] A3 POLARIDADE — Grau em que o conceito está posicionado num espectro entre extremos. Alta = fortemente polar. Baixa = neutro.
[4] A4 RITMO — Grau em que o conceito exibe padrão cíclico ou periódico. Alta = ritmo claro. Baixa = irregular ou único.
[5] A5 CAUSA E EFEITO — Grau em que o conceito é agente causal vs efeito. Alta = causa primária. Baixa = consequência pura.
[6] A6 GÊNERO — Grau em que o conceito é gerador/ativo vs receptivo/passivo. Alta = princípio ativo. Baixa = princípio receptivo.
[7] A7 SISTEMA — Grau em que o conceito é um conjunto com comportamento emergente.
[8] A8 ESTADO — Grau em que o conceito é uma configuração num dado momento.
[9] A9 PROCESSO — Grau em que o conceito é transformação no tempo.
[10] A10 RELAÇÃO — Grau em que o conceito é conexão entre entidades.
[11] A11 SINAL — Grau em que o conceito é informação carregando variação.
[12] A12 ESTABILIDADE — Grau em que o conceito tende ao equilíbrio ou à divergência. Alta = convergente. Baixa = instável/caótico.
[13] A13 VALÊNCIA ONTOLÓGICA — Sinal intrínseco do conceito em si. 0 = negativo/contrativo → 0.5 = neutro → 1 = positivo/expansivo. Independente do contexto ou do agente.

**Grupo B — Epistêmico (14-21):**
[14] B1 VERIFICABILIDADE — Grau em que o conceito pode ser confirmado externamente. Alta = verificável por evidência. Baixa = não falsificável.
[15] B2 TEMPORALIDADE — Grau em que o conceito tem âncora temporal definida. Alta = momento preciso. Baixa = atemporal ou indefinido.
[16] B3 COMPLETUDE — Grau em que o conceito está resolvido. Alta = fechado, conclusivo. Baixa = aberto, em construção.
[17] B4 CAUSALIDADE — Grau em que a origem do conceito é identificável. Alta = causa clara. Baixa = origem opaca ou difusa.
[18] B5 REVERSIBILIDADE — Grau em que o conceito pode ser desfeito. Alta = totalmente reversível. Baixa = irreversível.
[19] B6 CARGA — Grau de recurso cognitivo que o conceito consome. Alta = pesado, exige atenção. Baixa = automático, fluido.
[20] B7 ORIGEM — Grau em que o conhecimento é observado vs inferido vs assumido. Alta = observação direta. Baixa = suposição pura.
[21] B8 VALÊNCIA EPISTÊMICA — Sinal do conhecimento que o agente tem sobre o conceito. 0 = evidência contraditória → 0.5 = inconclusivo → 1 = evidência confirmatória.

**Grupo C — Pragmático (22-31):**
[22] C1 URGÊNCIA — Grau em que o conceito exige resposta imediata. Alta = pressão temporal crítica. Baixa = sem pressa.
[23] C2 IMPACTO — Grau em que o conceito gera consequências. Alta = muda estado do sistema. Baixa = inócuo.
[24] C3 AÇÃO — Grau em que o conceito exige resposta ativa vs é só alinhamento. Alta = demanda execução. Baixa = puramente informativo.
[25] C4 VALOR — Grau em que o conceito conecta com algo que importa de verdade — ativa valores, não só lógica. Alta = carregado de significado. Baixa = neutro axiologicamente.
[26] C5 ANOMALIA — Grau em que o conceito é desvio do padrão esperado. Alta = ruptura forte. Baixa = dentro do normal.
[27] C6 AFETO — Grau em que o conceito carrega valência emocional relevante. Alta = forte carga afetiva. Baixa = neutro emocionalmente.
[28] C7 DEPENDÊNCIA — Grau em que o conceito precisa de outro para existir. Alta = totalmente acoplado. Baixa = autônomo.
[29] C8 VETOR TEMPORAL — Orientação do conceito no tempo. 0 = passado puro → 0.5 = presente → 1 = futuro puro. Distinto de TEMPORALIDADE que mede se tem âncora.
[30] C9 NATUREZA — Categoria semântica fundamental. 0 = substantivo puro (coisa, ser, estado) → 1 = verbo puro (processo, ação, transformação).
[31] C10 VALÊNCIA DE AÇÃO — Sinal da intenção do agente ao transmitir. 0 = negativo/alerta/contrativo → 0.5 = neutro/consulta → 1 = positivo/confirmação/expansivo.

Inclua também:
- Explicação dos 3 subgrupos de A: 7 Princípios Herméticos (A0-A6), 6 eixos de engenharia (A7-A12), Valência (A13)
- Nota sobre B6 CARGA ser exclusivo deste espaço (eixo TDAH do criador)
- Nota sobre C4 VALOR ser o "eixo INFP" — valores importam, não só lógica
- Seção "Guia de Projeção" com 3-5 exemplos práticos de como projetar conceitos nos 32 eixos
  - Exemplo: "O servidor caiu" → mostrar valores esperados nos 32 eixos
  - Exemplo: "Preciso de ajuda urgente" → mostrar valores
  - Exemplo: "A gravidade é uma força fundamental" → mostrar valores

## REQUISITOS DO references/rust-implementation-guide.md

Arquitetura completa de implementação:

**Workspace Rust:**
```
leet1337/
├── Cargo.toml          (workspace members: leet-core, leet-bridge)
├── leet-core/          (tipos, validação, operadores, FFI, PyO3)
│   ├── Cargo.toml      (crate-type: ["rlib", "cdylib"], feature "python" = ["pyo3"])
│   └── src/
│       ├── lib.rs      (re-exports, constantes FIXED_DIMS=32, MAX_INHERITANCE_DEPTH=4, LOW_CONFIDENCE_THRESHOLD=0.9)
│       ├── types.rs    (TODOS os tipos da spec)
│       ├── axes.rs     (32 eixos como constantes + tabela estática)
│       ├── operators.rs (5 operadores + apply_patch + testes)
│       ├── validate.rs (Validator com R1-R21 + testes)
│       ├── error.rs    (LeetError com thiserror)
│       ├── ffi.rs      (C ABI: extern "C" + leet_free_string)
│       └── python.rs   (PyO3 #[pymodule] feature-gated)
└── leet-bridge/        (tradução humano ↔ 1337)
```

**API Design — o core é CHAMÁVEL de fora:**
- Build padrão → .so/.dylib com C ABI (qualquer linguagem chama)
- Build com --features python → módulo Python importável (import leet_core)
- JSON como formato de troca na FFI (simples, universal)
- Funções FFI: leet_cogon_zero, leet_cogon_new, leet_blend, leet_delta, leet_dist, leet_validate, leet_serialize, leet_version, leet_free_string

**Python package wrapper:**
```
python/
├── pyproject.toml      (maturin)
└── leet/
    ├── __init__.py     (API pública)
    ├── types.py        (dataclasses espelhando Rust)
    ├── operators.py    (wrappers chamando Rust)
    ├── bridge.py       (SemanticProjector ABC + AnthropicProjector)
    └── cli.py          (leet encode/decode/validate/zero/blend)
```

**Dependências Rust:** serde+derive, serde_json, uuid(v4+serde), sha2, thiserror, pyo3(opcional)

**Padrão de trait para projeção semântica:**
```rust
#[async_trait]
pub trait SemanticProjector {
    async fn project(&self, text: &str) -> Result<(Vec<f32>, Vec<f32>), BridgeError>;
    async fn reconstruct(&self, cogon: &Cogon) -> Result<String, BridgeError>;
    async fn reconstruct_dag(&self, dag: &Dag, depth: usize) -> Result<String, BridgeError>;
}
```

Crie todos os arquivos. Não deixe nenhum como placeholder. Cada arquivo deve estar COMPLETO e funcional.
