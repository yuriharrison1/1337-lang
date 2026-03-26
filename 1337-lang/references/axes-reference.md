# 1337 Axes Reference — 32 Canonical Axes v0.4

The 32 axes are divided into 3 groups: **A (Ontological)**, **B (Epistemic)**, **C (Pragmatic)**.
All values are `float ∈ [0,1]`. VECTOR[32] is **always indexed by position** — never by name (R10).

---

## Group A — Ontological (indices 0–13)

Group A is further divided into three subgroups:

### A0–A6: The 7 Hermetic Principles
These axes map to the classical Hermetic principles (Mentalism, Correspondence, Vibration,
Polarity, Rhythm, Cause & Effect, Gender). They represent the deepest ontological structure
of a concept — its fundamental nature in reality.

### A7–A12: Engineering Axes
These 6 axes are practical ontological descriptors useful for technical reasoning:
System, State, Process, Relation, Signal, Stability.

### A13: Ontological Valence
The intrinsic sign of the concept itself — independent of context or agent.

---

### [0] A0 VIA
**Grau em que o conceito existe por si mesmo, independente de relações externas.**
- Alta (→1.0) = essência pura, existência autossuficiente, ser primário
- Baixa (→0.0) = só existe em função de outro, puramente relacional, instrumental
- Exemplos: "existência" → 0.95 | "ferramenta" → 0.15 | "amor" → 0.6

### [1] A1 CORRESPONDÊNCIA
**Grau em que o conceito espelha padrões em outros níveis de abstração.**
- Alta (→1.0) = mesmo padrão se repete em múltiplas escalas (fractal, analógico)
- Baixa (→0.0) = único, não tem espelho em outras escalas
- Exemplos: "fractal" → 0.95 | "DNA" → 0.85 | "parafuso específico" → 0.1

### [2] A2 VIBRAÇÃO
**Grau em que o conceito está em movimento/transformação contínua.**
- Alta (→1.0) = fluxo constante, nunca estático, sempre mudando
- Baixa (→0.0) = estático, imóvel, fixo no tempo
- Exemplos: "mercado financeiro" → 0.9 | "pedra" → 0.1 | "emoção" → 0.8

### [3] A3 POLARIDADE
**Grau em que o conceito está posicionado num espectro entre extremos opostos.**
- Alta (→1.0) = fortemente polar, ocupa um dos extremos do espectro
- Baixa (→0.0) = neutro, no centro, sem polarização
- Exemplos: "ódio" → 0.95 | "temperatura" → 0.7 | "cinza" → 0.1

### [4] A4 RITMO
**Grau em que o conceito exibe padrão cíclico ou periódico.**
- Alta (→1.0) = ritmo claro e regular (batimento, ciclo, periodicidade)
- Baixa (→0.0) = irregular, único, sem repetição
- Exemplos: "respiração" → 0.95 | "seasons" → 0.9 | "explosão única" → 0.05

### [5] A5 CAUSA E EFEITO
**Grau em que o conceito é agente causal vs consequência pura.**
- Alta (→1.0) = causa primária, origem da cadeia causal
- Baixa (→0.0) = consequência pura, efeito sem agência
- Exemplos: "decisão" → 0.9 | "intenção" → 0.85 | "sombra" → 0.05

### [6] A6 GÊNERO
**Grau em que o conceito é gerador/ativo vs receptivo/passivo.**
- Alta (→1.0) = princípio ativo, iniciador, expansivo
- Baixa (→0.0) = princípio receptivo, passivo, contrativo
- Exemplos: "iniciativa" → 0.9 | "escuta" → 0.1 | "colaboração" → 0.5

### [7] A7 SISTEMA
**Grau em que o conceito é um conjunto organizado com comportamento emergente.**
- Alta (→1.0) = sistema complexo com partes interdependentes e emergência
- Baixa (→0.0) = elemento isolado, átomo, sem sistema
- Exemplos: "ecossistema" → 0.95 | "organização" → 0.85 | "número" → 0.05

### [8] A8 ESTADO
**Grau em que o conceito é uma configuração num dado momento.**
- Alta (→1.0) = snapshot, configuração estática de um instante
- Baixa (→0.0) = não tem estado, puro processo sem snapshots
- Exemplos: "configuração atual do servidor" → 0.95 | "resultado" → 0.85 | "fluxo" → 0.1

### [9] A9 PROCESSO
**Grau em que o conceito é transformação ao longo do tempo.**
- Alta (→1.0) = puro processo, transformação contínua
- Baixa (→0.0) = estático, sem dimensão temporal de transformação
- Exemplos: "deploy" → 0.9 | "aprendizado" → 0.85 | "número pi" → 0.0

### [10] A10 RELAÇÃO
**Grau em que o conceito é conexão entre entidades.**
- Alta (→1.0) = pura relação, não existe sem as partes relacionadas
- Baixa (→0.0) = entidade autônoma, sem natureza relacional
- Exemplos: "dependência" → 0.95 | "interface" → 0.85 | "pedra" → 0.05

### [11] A11 SINAL
**Grau em que o conceito é informação carregando variação mensurável.**
- Alta (→1.0) = puro sinal, diferença que faz diferença
- Baixa (→0.0) = ruído ou constante, sem informação
- Exemplos: "alerta" → 0.95 | "dado sensorial" → 0.85 | "silêncio absoluto" → 0.05

### [12] A12 ESTABILIDADE
**Grau em que o conceito tende ao equilíbrio ou à divergência.**
- Alta (→1.0) = convergente, atrator, tende ao equilíbrio
- Baixa (→0.0) = instável, caótico, amplifica perturbações
- Exemplos: "lei física" → 0.95 | "rotina" → 0.85 | "crise" → 0.1

### [13] A13 VALÊNCIA ONTOLÓGICA
**Sinal intrínseco do conceito em si — independente do contexto ou do agente.**
- 0.0 = negativo/contrativo (destruição, ausência, privação)
- 0.5 = neutro (ferramentas, processos neutros)
- 1.0 = positivo/expansivo (criação, abundância, saúde)
- Exemplos: "morte" → 0.1 | "ferramenta" → 0.5 | "cura" → 0.9

---

## Group B — Epistemic (indices 14–21)

Group B describes the **knowledge state** of the agent regarding the concept.
These axes answer: "how well do we know this?"

### [14] B1 VERIFICABILIDADE
**Grau em que o conceito pode ser confirmado externamente por evidência.**
- Alta (→1.0) = verificável, falsificável, tem evidência objetiva
- Baixa (→0.0) = não falsificável, puramente subjetivo ou metafísico
- Exemplos: "temperatura do servidor" → 0.95 | "intuição" → 0.1

### [15] B2 TEMPORALIDADE
**Grau em que o conceito tem âncora temporal definida.**
- Alta (→1.0) = momento preciso, timestamp, evento datado
- Baixa (→0.0) = atemporal, indefinido no tempo, eterno ou vago
- Exemplos: "o crash aconteceu às 14:32" → 0.95 | "gravidade" → 0.05

### [16] B3 COMPLETUDE
**Grau em que o conceito está resolvido/fechado.**
- Alta (→1.0) = fechado, conclusivo, sem partes faltando
- Baixa (→0.0) = aberto, em construção, parcial
- Exemplos: "resultado final" → 0.9 | "hipótese de trabalho" → 0.2

### [17] B4 CAUSALIDADE
**Grau em que a origem/causa do conceito é identificável.**
- Alta (→1.0) = causa clara e conhecida
- Baixa (→0.0) = origem opaca, difusa ou desconhecida
- Exemplos: "erro causado pelo deploy" → 0.9 | "bug misterioso" → 0.1

### [18] B5 REVERSIBILIDADE
**Grau em que o conceito/ação pode ser desfeito.**
- Alta (→1.0) = totalmente reversível, desfazível
- Baixa (→0.0) = irreversível, permanente, sem undo
- Exemplos: "git commit --amend" → 0.8 | "dados deletados sem backup" → 0.05

### [19] B6 CARGA
**Grau de recurso cognitivo que o conceito consome.**
- Alta (→1.0) = pesado, demanda atenção, consome bandwidth cognitivo
- Baixa (→0.0) = automático, fluido, processado sem esforço

> **Nota:** Este é o "eixo TDAH" — criado a partir da experiência de alta variabilidade
> de carga cognitiva. Alta CARGA = precisa de foco ativo. Baixa = piloto automático.

- Exemplos: "debugging complexo" → 0.95 | "respirar" → 0.02 | "tarefa rotineira" → 0.2

### [20] B7 ORIGEM
**Grau em que o conhecimento é observado vs inferido vs assumido.**
- Alta (→1.0) = observação direta, first-hand, dado primário
- Baixa (→0.0) = suposição pura, assumido sem evidência
- Exemplos: "log do servidor" → 0.95 | "suposição do usuário" → 0.1 | "inferência" → 0.5

### [21] B8 VALÊNCIA EPISTÊMICA
**Sinal do conhecimento que o agente tem sobre o conceito.**
- 0.0 = evidência contraditória, dados inconsistentes
- 0.5 = inconclusivo, dados insuficientes ou mistos
- 1.0 = evidência confirmatória forte, certeza alta
- Exemplos: "bug confirmado em prod" → 0.9 | "comportamento inconsistente" → 0.2

---

## Group C — Pragmatic (indices 22–31)

Group C describes the **action context** — what the agent intends to do with the concept.

### [22] C1 URGÊNCIA
**Grau em que o conceito exige resposta imediata.**
- Alta (→1.0) = pressão temporal crítica, agir agora
- Baixa (→0.0) = sem pressa, pode esperar indefinidamente
- Exemplos: "produção caiu" → 0.98 | "feature request" → 0.2

### [23] C2 IMPACTO
**Grau em que o conceito gera consequências significativas.**
- Alta (→1.0) = muda estado do sistema de forma ampla
- Baixa (→0.0) = inócuo, sem consequências práticas
- Exemplos: "deploy em produção" → 0.9 | "comentário no código" → 0.1

### [24] C3 AÇÃO
**Grau em que o conceito exige resposta ativa vs é só alinhamento informativo.**
- Alta (→1.0) = demanda execução, fazer algo agora
- Baixa (→0.0) = puramente informativo, só alinhamento
- Exemplos: "precisa fazer rollback" → 0.95 | "FYI: logs mostrando isso" → 0.1

### [25] C4 VALOR
**Grau em que o conceito conecta com algo que importa de verdade — ativa valores profundos.**

> **Nota:** Este é o "eixo INFP" — valores importam além da lógica.
> Alta VALOR = carregado de significado existencial, ético, identitário.

- Alta (→1.0) = ativa valores fundamentais, significado profundo
- Baixa (→0.0) = axiologicamente neutro, puramente técnico
- Exemplos: "privacidade do usuário" → 0.9 | "número de linha no log" → 0.05

### [26] C5 ANOMALIA
**Grau em que o conceito é desvio do padrão esperado.**
- Alta (→1.0) = ruptura forte, completamente fora do normal
- Baixa (→0.0) = dentro do esperado, padrão normal
- Exemplos: "latência 10x acima da média" → 0.95 | "request normal" → 0.02

### [27] C6 AFETO
**Grau em que o conceito carrega valência emocional relevante para o agente.**
- Alta (→1.0) = forte carga afetiva (medo, alegria, frustração, entusiasmo)
- Baixa (→0.0) = neutro emocionalmente, sem carga afetiva
- Exemplos: "perda de dados de usuário" → 0.85 | "número de commits" → 0.05

### [28] C7 DEPENDÊNCIA
**Grau em que o conceito precisa de outro para existir ou funcionar.**
- Alta (→1.0) = totalmente acoplado, não existe sem dependência
- Baixa (→0.0) = autônomo, independente
- Exemplos: "serviço que depende de banco" → 0.9 | "função pura" → 0.05

### [29] C8 VETOR TEMPORAL
**Orientação do conceito no tempo.**
- 0.0 = passado puro (evento histórico, retrospectiva)
- 0.5 = presente (estado atual, agora)
- 1.0 = futuro puro (previsão, planejamento, intenção)

> Distinto de B2 TEMPORALIDADE, que mede se *tem* âncora temporal.
> C8 mede *para onde* o conceito aponta no tempo.

- Exemplos: "post-mortem" → 0.1 | "status atual" → 0.5 | "roadmap Q3" → 0.9

### [30] C9 NATUREZA
**Categoria semântica fundamental do conceito.**
- 0.0 = substantivo puro (coisa, ser, entidade, estado)
- 1.0 = verbo puro (processo, ação, transformação)
- Exemplos: "servidor" → 0.05 | "deploy" → 0.9 | "configuração" → 0.2

### [31] C10 VALÊNCIA DE AÇÃO
**Sinal da intenção do agente ao transmitir este conceito.**
- 0.0 = negativo/alerta/contrativo (aviso, bloqueio, problema)
- 0.5 = neutro/consulta (query, alinhamento)
- 1.0 = positivo/confirmação/expansivo (aprovação, expansão)
- Exemplos: "anomalia crítica" → 0.05 | "query de status" → 0.5 | "deploy aprovado" → 0.95

---

## Projection Guide

When projecting a concept, ask for each axis: "How much does this concept express this quality?"

### Example 1: "O servidor caiu"

```
[0]  A0  VIA                   0.3   # o servidor existe, mas caiu = baixa autonomia atual
[1]  A1  CORRESPONDÊNCIA        0.3
[2]  A2  VIBRAÇÃO               0.7   # estado mudando
[3]  A3  POLARIDADE             0.8   # extremo negativo
[4]  A4  RITMO                  0.2   # evento irregular
[5]  A5  CAUSA E EFEITO         0.5   # é efeito de algo
[6]  A6  GÊNERO                 0.2   # passivo/receptivo
[7]  A7  SISTEMA                0.7   # sistema complexo
[8]  A8  ESTADO                 0.95  # configuração num momento (caído)
[9]  A9  PROCESSO               0.3   # mais estado que processo
[10] A10 RELAÇÃO                0.3
[11] A11 SINAL                  0.85  # informação crítica
[12] A12 ESTABILIDADE           0.05  # instável
[13] A13 VALÊNCIA ONTOLÓGICA    0.1   # negativo
[14] B1  VERIFICABILIDADE       0.95  # verificável (health check)
[15] B2  TEMPORALIDADE          0.9   # agora
[16] B3  COMPLETUDE             0.8   # fato consumado
[17] B4  CAUSALIDADE            0.5   # causa pode ser desconhecida
[18] B5  REVERSIBILIDADE        0.6   # pode ser revertido (restart)
[19] B6  CARGA                  0.9   # requer atenção imediata
[20] B7  ORIGEM                 0.9   # observação direta (monitoring)
[21] B8  VALÊNCIA EPISTÊMICA    0.85  # confirmado
[22] C1  URGÊNCIA               0.95  # crítico
[23] C2  IMPACTO                0.9   # alto impacto
[24] C3  AÇÃO                   0.85  # exige resposta
[25] C4  VALOR                  0.7   # impacta usuários
[26] C5  ANOMALIA               0.95  # desvio forte
[27] C6  AFETO                  0.6   # estresse/preocupação
[28] C7  DEPENDÊNCIA            0.8   # outros serviços dependem
[29] C8  VETOR TEMPORAL         0.5   # presente
[30] C9  NATUREZA               0.3   # mais estado que ação
[31] C10 VALÊNCIA DE AÇÃO       0.05  # alerta
```

### Example 2: "Preciso de ajuda urgente"

```
[0]  A0  VIA                   0.5
[1]  A1  CORRESPONDÊNCIA        0.4
[2]  A2  VIBRAÇÃO               0.6
[3]  A3  POLARIDADE             0.7
[4]  A4  RITMO                  0.2
[5]  A5  CAUSA E EFEITO         0.4
[6]  A6  GÊNERO                 0.2   # receptivo (pedindo ajuda)
[7]  A7  SISTEMA                0.3
[8]  A8  ESTADO                 0.6   # estado de necessidade
[9]  A9  PROCESSO               0.5
[10] A10 RELAÇÃO                0.8   # depende de outro agente
[11] A11 SINAL                  0.9   # forte sinal
[12] A12 ESTABILIDADE           0.2
[13] A13 VALÊNCIA ONTOLÓGICA    0.3
[14] B1  VERIFICABILIDADE       0.5
[15] B2  TEMPORALIDADE          0.9   # agora
[16] B3  COMPLETUDE             0.1   # situação aberta
[17] B4  CAUSALIDADE            0.5
[18] B5  REVERSIBILIDADE        0.7
[19] B6  CARGA                  0.9   # alta carga cognitiva
[20] B7  ORIGEM                 0.8   # first-hand
[21] B8  VALÊNCIA EPISTÊMICA    0.6
[22] C1  URGÊNCIA               0.95  # urgente!
[23] C2  IMPACTO                0.7
[24] C3  AÇÃO                   0.9   # exige resposta ativa
[25] C4  VALOR                  0.75
[26] C5  ANOMALIA               0.6
[27] C6  AFETO                  0.75  # ansiedade/stress
[28] C7  DEPENDÊNCIA            0.9   # precisa do outro
[29] C8  VETOR TEMPORAL         0.5   # presente
[30] C9  NATUREZA               0.6   # orientado à ação
[31] C10 VALÊNCIA DE AÇÃO       0.15  # pedido em contexto de problema
```

### Example 3: "A gravidade é uma força fundamental"

```
[0]  A0  VIA                   0.9   # existe por si mesmo
[1]  A1  CORRESPONDÊNCIA        0.85  # mesma lei em todas as escalas
[2]  A2  VIBRAÇÃO               0.3   # relativamente estático
[3]  A3  POLARIDADE             0.4
[4]  A4  RITMO                  0.5
[5]  A5  CAUSA E EFEITO         0.85  # causa primária
[6]  A6  GÊNERO                 0.5
[7]  A7  SISTEMA                0.7
[8]  A8  ESTADO                 0.5
[9]  A9  PROCESSO               0.4
[10] A10 RELAÇÃO                0.7   # relação entre massas
[11] A11 SINAL                  0.3
[12] A12 ESTABILIDADE           0.95  # altamente estável
[13] A13 VALÊNCIA ONTOLÓGICA    0.6
[14] B1  VERIFICABILIDADE       0.95  # verificável, mensurável
[15] B2  TEMPORALIDADE          0.05  # atemporal
[16] B3  COMPLETUDE             0.8   # bem estabelecido
[17] B4  CAUSALIDADE            0.9   # causalidade clara
[18] B5  REVERSIBILIDADE        0.1   # não reversível
[19] B6  CARGA                  0.3
[20] B7  ORIGEM                 0.85  # observação + teoria
[21] B8  VALÊNCIA EPISTÊMICA    0.9   # alta certeza
[22] C1  URGÊNCIA               0.05  # sem urgência
[23] C2  IMPACTO                0.7
[24] C3  AÇÃO                   0.1   # informativo
[25] C4  VALOR                  0.5
[26] C5  ANOMALIA               0.05  # completamente normal
[27] C6  AFETO                  0.1
[28] C7  DEPENDÊNCIA            0.3
[29] C8  VETOR TEMPORAL         0.5
[30] C9  NATUREZA               0.3   # mais conceito que ação
[31] C10 VALÊNCIA DE AÇÃO       0.5   # neutro/informativo
```

---

## Quick Index

```
A0=0  A1=1  A2=2  A3=3  A4=4  A5=5  A6=6
A7=7  A8=8  A9=9  A10=10 A11=11 A12=12 A13=13
B1=14 B2=15 B3=16 B4=17 B5=18 B6=19 B7=20 B8=21
C1=22 C2=23 C3=24 C4=25 C5=26 C6=27 C7=28 C8=29 C9=30 C10=31
```
