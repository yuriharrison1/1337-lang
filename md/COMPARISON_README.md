# Comparação 1337 vs English

Script de comparação completa entre comunicação via Protocolo 1337 e texto puro (English/Português).

## 🎯 Objetivo

Demonstrar as vantagens e diferenças entre:
- **Protocolo 1337**: Comunicação estruturada com COGONs, MSG_1337, RAW objects
- **Texto Puro**: Comunicação em linguagem natural (baseline)

## 🚀 Execução

### Básico (25 rodadas - padrão)
```bash
python comparison_1337_vs_english.py
```

### Avançado
```bash
# 50 rodadas
python comparison_1337_vs_english.py --rounds 50

# Tópico customizado
python comparison_1337_vs_english.py --topic "Justiça" --rounds 30

# Modo silencioso (apenas estatísticas)
python comparison_1337_vs_english.py --rounds 100 --quiet

# Sem salvar relatório
python comparison_1337_vs_english.py --rounds 25 --no-save

# Com Redis cache
python comparison_1337_vs_english.py --rounds 50 --cache redis

# Contexto técnico
python comparison_1337_vs_english.py --rounds 25 --context technical

# Ajuda completa
python comparison_1337_vs_english.py --help
```

## 🎭 Cenário

**Tópico**: O Amor (Eros) no Banquete de Platão

**Agentes** (8 personagens multidisciplinares):

| Agente | Perfil | Base Semântica |
|--------|--------|----------------|
| Sócrates | Filósofo (Maiêutica) | Alta epistemologia |
| Aristófanes | Poeta/Comediante | Alta vibração/poesia |
| Agaton | Poeta Trágico | Alta beleza/eloquência |
| Alcibíades | Político/Bêbado | Alta anomalia/afeto |
| Contador Carlos | Contador | Alta verificabilidade |
| Técnico Tiago | TI/Sistemas | Sistemas/processos |
| Padre Pedro | Religioso | Fé/divino |
| Comunista Carlos | Ativista | Polarity/impacto social |

## 📊 Métricas Comparadas

### Performance
- Tempo de processamento total
- Latência por mensagem (P50, P90, P99 se 25+ rodadas)
- Taxa de mensagens/segundo

### Eficiência
- Tokens utilizados (input/output)
- Custo estimado (USD)
- Taxa de compressão
- Bytes economizados

### Qualidade 1337
- RAW Objects criados (EVIDENCE, ARTIFACT, TRACE, BRIDGE)
- Validação estrutural (R1-R21)
- Herança OO
- Profundidade máxima de herança
- Distribuição de intents (gráfico ASCII se 25+ rodadas)

### Efetividade
- Convergência semântica
- Detecção de anomalias
- Evolução de conceitos
- Contribuições por agente

## 📁 Saída

### Console
- Tabela comparativa lado a lado
- Análise de efetividade
- Contribuições por agente
- Timeline detalhada
- Conclusão com vantagens

### Arquivo JSON
Relatório completo salvo em:
```
./comparison_reports/comparison_<timestamp>.json
```

Contém:
- Configuração do experimento
- Todas as métricas detalhadas
- Timeline completa
- Contribuições por agente

## 🧪 Configurações

Edite via linha de comando:

```bash
# Padrão recomendado para análise estatística
python comparison_1337_vs_english.py --rounds 25

# Análise em larga escala
python comparison_1337_vs_english.py --rounds 100 --quiet
```

Ou edite `ComparisonConfig` no script:

```python
config = ComparisonConfig(
    rounds=25,                   # Número de rounds (mínimo recomendado: 25)
    backend_1337="local",        # Backend: local, grpc, mock
    cache_type="memory",         # Cache: memory, sqlite, redis
    context_profile="philosophical",  # Perfil: technical, emergency, etc
    track_raw_objects=True,      # Rastrear OO/RAW
    track_inheritance=True,      # Rastrear herança
    track_compression=True,      # Calcular compressão
    save_reports=True,           # Salvar JSON
    verbose=True                 # Output detalhado
)
```

## 📈 Resultados Esperados

### Vantagens do 1337
- ✅ Objetos tipados (RAW EVIDENCE, ARTIFACT, etc)
- ✅ Validação estrutural (R1-R21)
- ✅ Semântica precisa (32 eixos)
- ✅ Herança OO
- ✅ Compressão em grandes volumes

### Trade-offs
- ⚠️ Overhead de processamento
- ⚠️ Menos eficiente para mensagens muito curtas

## 🔧 Requisitos

```bash
# Python 3.11+
# Pacotes já instalados no projeto:
# - leet1337 (core SDK)
# - leet-vm (VM layer) - opcional
# - leet-py (public SDK) - opcional
```

## 📈 Estatísticas Avançadas (25+ rodadas)

Quando você executa com 25 ou mais rodadas, o script mostra estatísticas adicionais:

```
📈 ESTATÍSTICAS AVANÇADAS (25+ rodadas)

⏱️  Latência 1337 (ms):
   Média: 0.41
   Mediana (P50): 0.40
   P90: 0.47
   P99: 0.60
   Min: 0.32
   Max: 0.66

📊 Distribuição de Intents:
   ASSERT          │ ████████████████████ 240 (100.0%)

📈 Mensagens por rodada:
   Total: 240 mensagens em 30 rodadas
   Média: 8.0 mensagens/rodada
   Taxa: 2152.4 msgs/segundo
```

## 🎯 Recomendações de Uso

| Cenário | Rodadas | Modo | Objetivo |
|---------|---------|------|----------|
| Demo rápida | 10 | verbose | Ver funcionamento |
| Análise estatística | 25-50 | quiet | Métricas confiáveis |
| Benchmark | 100+ | quiet | Performance em larga escala |
| Debug | 5 | verbose | Verificar erros |

## 📊 Interpretando Resultados

### Compressão
- **Ratio > 1.0x**: 1337 é mais compacto que texto
- **Ratio < 1.0x**: Texto é mais compacto (comum em mensagens curtas)
- **Vantagem do 1337 cresce** com o volume de mensagens

### Tokens
- Economia de ~0.2% é típica para mensagens curtas
- Com 100+ rodadas, economia pode chegar a 1-2%

### RAW Objects
- Cada mensagem 1337 cria 1 objeto RAW tipado
- Permite rastreabilidade e herança
- Não disponível em texto puro

## 📊 Exemplo de Saída

```
📊 RELATÓRIO COMPARATIVO: 1337 vs ENGLISH

┌─────────────────────────┬──────────────────┬──────────────────┬──────────────┐
│ Métrica                 │ 1337 Protocol    │ English (Text)   │ Diferença    │
├─────────────────────────┼──────────────────┼──────────────────┼──────────────┤
│ Duração Total (ms)      │            23.41 │             1.41 │ 🔴 +1558.9% │
│ Tokens Input            │           533.00 │           548.00 │ 🟢   -2.7% │
│ Tokens Total            │          6533.00 │          6548.00 │ 🟢   -0.2% │
│ Custo Estimado ($)      │             0.01 │             0.01 │ 🟢   -0.2% │
│ Compressão Ratio        │             0.48x │ N/A              │ 🟢 Único     │
│ RAW Evidence            │               40 │ 0                │ 🟢 OO        │
│ Erros Validação         │                0 │ N/A              │ ⚪ Check     │
└─────────────────────────┴──────────────────┴──────────────────┴──────────────┘
```

## 📝 Notas

- Para mensagens pequenas, o overhead do 1337 (32 floats = 128 bytes) pode ser maior que o texto
- A vantagem do 1337 cresce com:
  - Volume de mensagens
  - Necessidade de semântica precisa
  - Validação estrutural
  - Rastreabilidade (RAW objects)
  - Herança de conceitos

## 🔗 Referências

- `plato_discussion.py` - Simulação filosófica original
- `net1337.py` - Rede interativa de agentes
- `leet/validate.py` - Regras R1-R21
