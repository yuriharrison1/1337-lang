# /leet-stats — Relatório de economia de tokens com 1337

$ARGUMENTS

Execute os passos abaixo na ordem e apresente o relatório final.

## Passo 1 — Pirâmide do store

Use a ferramenta Bash para rodar:

```bash
leet consolidate inspect --json 2>/dev/null || ~/.cargo/bin/leet consolidate inspect --json 2>/dev/null
```

Se o projeto não tiver um store ainda, o comando vai informar. Nesse caso, mostre a mensagem:
"Store vazio — nenhum contexto foi salvo ainda. Use `leet_remember` para começar."
E encerre.

## Passo 2 — Estado atual do recall

Chame `leet_recall` com `limit=50` para obter todos os registros vivos e o rodapé de contagem.

## Passo 3 — Cálculo de economia

Use as estimativas conservadoras abaixo (baseadas em análise de sessões reais de Claude Code):

| Categoria | Estimativa |
|---|---|
| Tokens de contexto original por decisão lembrada | ~400 tokens |
| Tokens de um excerpt de recall (256 chars) | ~70 tokens |
| Tokens de um excerpt consolidado (L1+) | ~90 tokens (contém múltiplos) |
| Overhead fixo de `leet_recall` (cabeçalho + rodapé) | ~60 tokens |

**Cálculo:**

A partir do JSON do Passo 1:
- `total_records` = soma de todos os registros na pirâmide
- `consolidated` = soma dos campos `consolidated` de todos os níveis
- `live` = soma dos campos `live` de todos os níveis
- `bytes_store` = `store.bytes`

**Sem leet** (custo por sessão se colasse a história bruta):
```
tokens_sem_leet = total_records × 400
```

**Com leet** (custo real de um `leet_recall` típico com limit=5):
```
tokens_com_leet = min(live, 5) × 75 + 60
```

**Economia por sessão**:
```
economia = tokens_sem_leet - tokens_com_leet
pct = (economia / tokens_sem_leet) × 100
```

**Compressão acumulada** (todo o histórico já absorvido):
```
tokens_absorvidos = consolidated × 400
```

## Passo 4 — Apresentação

Mostre o relatório neste formato (adapte para português se o usuário fala português):

```
╔══════════════════════════════════════════╗
║       leet-stats · economia de tokens    ║
╚══════════════════════════════════════════╝

Store: <caminho>  (<bytes_store> bytes)

Pirâmide de memória:
  L0 (raw):  X registros vivos  (Y consolidados)
  L1:        X registros vivos  (Y consolidados)
  L2+:       X registros vivos  (Y consolidados)
  Total:     N registros  (V vivos · C absorvidos)

─────────────────────────────────────────────

Estimativa de custo por sessão nova:

  Sem leet  →  ~Z tokens   (colar a história bruta)
  Com leet  →  ~W tokens   (leet_recall com 5 entradas)

  Economia: ~(Z-W) tokens / sessão  (~pct%)

─────────────────────────────────────────────

Contexto já absorvido pela pirâmide:
  C decisões comprimidas  =  ~tokens_absorvidos tokens
  que nunca mais precisam entrar no contexto.

Último recall: <data do last_recall_at, ou "nunca">
```

Deixe claro que são estimativas conservadoras. Não exponha os números internos do COGON nem os detalhes de nível ao usuário comum — só se ele pedir mais detalhes.
