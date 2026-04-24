# leet-cli

Toolkit de linha de comando para o protocolo 1337. Subcomandos para encode, decode, distância semântica, blend, inspeção e chat multi-agente.

## Instalação

```bash
cargo build --release -p leet-cli
# Binário em: target/release/leet
```

## Subcomandos

### `encode`

Projeta texto em um COGON e exibe os eixos ativados com barras visuais.

```bash
leet encode "deploy urgente falhou em produção"
```

Saída: lista de eixos com valor > 0, com barra de ativação proporcional.

---

### `decode`

Reconstrói texto a partir de um COGON JSON.

```bash
# Passa JSON como argumento
leet decode '{"id":"...","sem":[...],"stamp":0}'

# Lê de stdin
cat cogon.json | leet decode -
leet decode  # lê stdin se não houver argumento
```

---

### `dist`

Distância cosseno semântica entre dois textos. Retorna valor em `[0, 2]`.

```bash
leet dist "urgente" "tranquilo"
leet dist "deploy falhou" "sistema em produção"
```

Interpretação:
- `< 0.05` → informação semanticamente equivalente, skip re-envio
- `0.0–0.3` → muito próximos
- `0.3–0.7` → relacionados
- `> 0.7` → diferentes

---

### `blend`

Interpola dois contextos semânticos.

```bash
leet blend "sistema estável" "alerta crítico" --alpha 0.7
# 70% "sistema estável", 30% "alerta crítico"

leet blend "texto A" "texto B"           # alpha padrão: 0.5
leet blend "texto A" "texto B" --alpha 0.3
```

---

### `axes`

Lista os 32 eixos canônicos com código, nome, bloco e descrição.

```bash
leet axes
```

---

### `zero`

Exibe o COGON_ZERO (estado inicial canônico).

```bash
leet zero
```

---

### `validate`

Valida um MSG_1337 JSON contra as regras R1–R23.

```bash
leet validate '{"id":"...","sender":"...",...}'
cat msg.json | leet validate -
leet validate  # stdin
```

Retorna exit code 0 se válido, 1 se inválido (com descrição do erro).

---

### `inspect`

Interpreta um COGON JSON — exibe os top-10 eixos ativados com valores.

```bash
leet inspect '{"id":"...","sem":[...]}'
cat cogon.json | leet inspect -
leet inspect  # stdin
```

---

### `bench`

Benchmark de performance de encode.

```bash
leet bench          # 1000 encodes (padrão)
leet bench -n 5000  # 5000 encodes
```

---

### `health`

Verifica se o leet-service está acessível.

```bash
leet health                            # localhost:50051
leet health --url 192.168.1.10:50051   # host remoto
```

---

### `version`

Exibe versão do CLI e do protocolo.

```bash
leet version
```

---

### `chat`

Chat multi-agente interativo. Requer `LEET_API_KEY` ou `--connect`.

```bash
# Modo API direta (chama Anthropic)
export LEET_API_KEY=sk-ant-...
leet chat

# Com opções
leet chat --lang en --show-cogon --agents 4

# Conecta a um leet-server em execução
leet chat --connect 127.0.0.1:1337
leet chat --connect /run/leet/leet.sock
```

Flags:

| Flag | Padrão | Descrição |
|------|--------|-----------|
| `--lang` | `pt` | Idioma de saída (`pt` ou `en`) |
| `--show-cogon` | false | Exibe resumo COGON inline com cada mensagem |
| `--agents` | `3` | Máximo de agentes por rodada (1–6) |
| `--connect` | — | Endereço TCP ou socket Unix do leet-server |

---

## Leitura de Stdin

Os subcomandos `decode`, `validate` e `inspect` aceitam:
- JSON como argumento direto
- `-` explícito para stdin
- Nenhum argumento → lê stdin automaticamente

```bash
echo '{"id":"..."}' | leet inspect
leet inspect - < cogon.json
```

## Variáveis de Ambiente

| Variável | Uso |
|----------|-----|
| `LEET_API_KEY` | Chave para modo `chat` direto à API |
| `LEET_W_PATH` | Caminho da W matrix de calibração |
