# Claude Code / MCP

O 1337 expõe suas operações semânticas como ferramentas MCP para o Claude Code, permitindo comunicação COGON-first dentro de sessões de desenvolvimento.

## Como Funciona

O servidor MCP (`mcp/leet_mcp.py`) invoca o binário `leet` (leet-cli) e expõe 5 tools:

| Tool | Descrição |
|------|-----------|
| `encode(text)` | Projeta texto → eixos ativos + valores |
| `dist(text_a, text_b)` | Distância cosseno; skip re-envio se < 0.05 |
| `blend(text_a, text_b, alpha)` | Interpola dois contextos semânticos |
| `axes()` | Referência dos 32 eixos canônicos |
| `inspect(cogon_json)` | Decodifica JSON de COGON → top-10 eixos |

## Configuração

O MCP já está configurado em `.claude/settings.json`. Ao abrir o projeto no Claude Code, o servidor é ativado automaticamente.

### Pré-requisito

O binário `leet` deve estar compilado:

```bash
cargo build --release -p leet-cli
# target/release/leet — o MCP detecta automaticamente (release antes de debug)
```

### Verificação Manual

```bash
python3 mcp/leet_mcp.py
# O servidor deve iniciar sem erros
```

## Skill `/leet`

O skill `/leet` ativa o modo de comunicação COGON-first para a sessão:

```
/leet
/leet <tarefa específica>
```

Em modo leet, o Claude:
- Usa `encode()` para fingerprinting semântico de contexto
- Verifica `dist()` antes de re-enviar informações (economia de tokens)
- Exibe resumos compactos `⟨G8=0.95 P3=0.90⟩` em vez de texto longo
- Usa `blend()` para fusão de contextos entre turnos

## Uso das Tools no Claude Code

### `encode`

```
encode("deploy urgente falhou em produção")
→ G8_URGENCY 0.95 | P3_ANOMALY 0.90 | D1_STATE 0.85 | P7_ACTION 0.80
```

Use para:
- Comprimir blocos de contexto longos (~90% redução de tokens)
- Fingerprinting de conceitos para comparação futura via `dist()`
- Gerar tokens de resumo `⟨G8=0.95 P3=0.90⟩`

### `dist`

```
dist("deploy falhou", "falha no deploy")
→ 0.04 — equivalentes semanticamente
```

Regra: se `dist < 0.05`, o receptor já tem essa informação — skip re-envio.

### `blend`

```
blend("sistema estável", "alerta crítico", alpha=0.3)
→ COGON mesclado: 30% estável, 70% crítico
```

Use para transições graduais de contexto entre turnos de conversa.

### `axes`

```
axes()
→ Lista completa dos 32 eixos com código, nome e descrição
```

Use quando precisar mapear um token `⟨…⟩` de volta para significado humano.

### `inspect`

```
inspect('{"id":"...","sem":[0.9,0.0,...]}')
→ Top-10 eixos com valores e interpretação
```

Use para decodificar payloads COGON recebidos de outros agentes.

## Protocolo de Comunicação COGON

Dentro de uma sessão com `/leet` ativo:

```
[turno 1]
  Agent A: encode("contexto longo aqui")
  → ⟨G8=0.72 D2=0.68 P7=0.61⟩

[turno 2]
  Agent B: dist("contexto anterior", "nova info")
  → 0.03 < 0.05 → skip, informação já presente
  → continua com delta apenas

[turno 3]
  blend(estado_anterior, novo_estado, alpha=0.6)
  → contexto atualizado suavemente
```

## Economia de Tokens

Estimativa de redução:

| Método | Tokens originais | Tokens COGON | Redução |
|--------|-----------------|--------------|---------|
| `encode()` | ~200 (bloco de contexto) | ~32 (vetor) | ~84% |
| `dist()` + skip | ~200 | 0 (skip) | ~100% |
| Notação `⟨…⟩` | ~50 (descrição) | ~10 (compacto) | ~80% |

## Troubleshooting

**MCP não aparece no Claude Code:**
- Verifique `.claude/settings.json` para a entrada do servidor `leet-1337`
- Rode `/hooks` no Claude Code para recarregar configurações
- Confirme que `target/release/leet` existe

**Tool retorna `ERROR: leet binary not found`:**
```bash
cargo build --release -p leet-cli
```

**Tool retorna `ERROR: leet timed out`:**
- Timeout padrão: 10 segundos
- Verifique se `LEET_W_PATH` está configurado corretamente se usando W matrix externa
