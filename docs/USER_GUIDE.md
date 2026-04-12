# Guia do Usuário — 1337

## O que é o 1337

O 1337 é um sistema de comunicação semântica comprimida entre agentes de IA. Em vez de trocar textos longos, os agentes codificam significado em vetores de 32 dimensões chamados **COGON** — 256 bytes por mensagem, independente do tamanho do conteúdo original.

Este guia cobre:
1. [Instalação e compilação](#1-instalação)
2. [CLI — comandos do dia a dia](#2-cli)
3. [leet chat — terminal multiagente](#3-leet-chat)
4. [leet-server e leet-agent — modo distribuído](#4-modo-distribuído)
5. [Configuração](#5-configuração)

---

## 1. Instalação

### Requisitos

- Rust 1.75+ (`rustup install stable`)
- `LEET_API_KEY` com chave Anthropic (apenas para `leet chat`)

### Compilar

```bash
git clone <repo>
cd 1337
cargo build --release
```

Os binários ficam em `target/release/`:

| Binário | Descrição |
|---------|-----------|
| `leet` | CLI principal com 13 comandos |
| `leet-server` | Daemon de rede (TCP + Unix socket) |
| `leet-agent` | Processo de agente autônomo |

### Instalar globalmente (opcional)

```bash
cargo install --path leet-cli
```

---

## 2. CLI

### `leet encode` — projetar texto em COGON

```bash
leet encode "sistema crítico, falha detectada"
```

Saída: barras coloridas por eixo mostrando os valores `sem` e `unc`.

```bash
# Redirecionar para arquivo
leet encode "urgente" > cogon.json

# Ver o JSON completo
leet encode "urgente" | python3 -m json.tool
```

---

### `leet decode` — reconstruir texto de um COGON

```bash
# A partir de argumento
leet decode '{"id":"...","sem":[...],"unc":[...],"stamp":0,"raw":null}'

# A partir de arquivo
leet encode "sistema crítico" > cogon.json
leet decode < cogon.json

# Pipeline
leet encode "anomalia detectada" | leet decode
```

---

### `leet inspect` — interpretação semântica

```bash
leet inspect '{"id":"...","sem":[...],...}'

# Mostra os 6 eixos mais ativos com valores
# Exemplo de saída:
#  G8_URGENCIA    0.92  ████████████
#  P3_ANOMALIA    0.87  ███████████
#  P7_ACAO        0.81  ██████████
#  D6_VALENCIA    0.72  █████████
```

---

### `leet dist` — distância semântica

```bash
leet dist "sistema estável" "sistema crítico"
# saída: 0.782

leet dist "olá mundo" "hello world"
# saída: 0.124  (semanticamente próximos)

leet dist "paz" "guerra"
# saída: 1.431  (opostos semânticos)
```

---

### `leet blend` — mistura semântica

```bash
# Mistura igual (padrão)
leet blend "urgente" "rotineiro"

# Mais próximo de "urgente" (70%)
leet blend "urgente" "rotineiro" --alpha 0.7

# Resultado: COGON intermediário no espaço semântico
```

---

### `leet axes` — listar todos os eixos

```bash
leet axes
# Exibe tabela com índice, código, nome e descrição dos 32 eixos
```

---

### `leet zero` — COGON_ZERO

```bash
leet zero
# Imprime o JSON do COGON_ZERO (sem=[1.0;32], unc=[0.0;32])
# Usado como handshake inicial no protocolo
```

---

### `leet validate` — validar MSG_1337

```bash
# De arquivo
leet validate < msg.json

# De argumento
leet validate '{"id":"...","sender":"...","payload":{...},...}'

# Valida contra as regras R1–R21
# Saída: "valid" ou erro com a regra violada
```

---

### `leet bench` — benchmark de performance

```bash
# 1000 projeções (padrão)
leet bench

# 10.000 projeções
leet bench --n 10000

# Exemplo de saída:
#  10000 encodes em 142ms
#  70422 ops/s
#  14.2µs por operação
```

---

### `leet health` — verificar serviço

```bash
# Verifica localhost:50051 (gRPC, padrão)
leet health

# Verificar servidor TCP na porta 1337
leet health --url 127.0.0.1:1337
```

---

### `leet version`

```bash
leet version
# leet 0.5.0 | spec v0.5.1 | commit abc1234
```

---

## 3. leet chat

O `leet chat` é um terminal interativo que conecta você a 15 agentes de IA especializados. Você escreve em português (ou inglês), o texto é convertido em COGON e enviado para Claude, que responde como os agentes mais relevantes.

### Requisitos

```bash
# Exportar a chave (use pass ou variável direta)
export LEET_API_KEY=$(pass show anthropic/api-key-testes | tr -d '[:space:]')
```

### Iniciar

```bash
leet chat
```

### Opções

| Flag | Padrão | Descrição |
|------|--------|-----------|
| `--lang pt\|en` | `pt` | Idioma das respostas dos agentes |
| `--show-cogon` | off | Exibe resumo COGON de cada agente após a resposta |
| `--agents N` | `3` | Número de agentes que respondem por rodada (1–6) |
| `--connect <addr>` | — | Conecta a um `leet-server` em vez da API direta |

### Exemplos

```bash
# Chat básico (haiku, 3 agentes, PT)
leet chat

# Com visualização COGON
leet chat --show-cogon

# Respostas em inglês, 5 agentes
leet chat --lang en --agents 5

# Usar Sonnet para respostas mais elaboradas
LEET_MODEL=claude-sonnet-4-6 leet chat

# Conectado a servidor local
leet chat --connect 127.0.0.1:1337
```

### Funcionamento

```
 Connecting to Anthropic... OK
 COGON_ZERO transmitted ✓
────────────────────────────────────────────

 YURI › qual é o status do sistema?

  ↳ ~7 tokens | 32B NL | 256B COGON | 8.0x NL size

  PULSE  "Todos os serviços estão operacionais. Latência p95 dentro do SLA."
  RAVEN  "Nenhuma anomalia detectada nas últimas 24h. Padrões dentro do esperado."
  ATLAS  "Infraestrutura estável. Recomendo revisão semanal da capacidade."

  latência: 2841ms | ~48 tok/s | 3 agente(s) respondeu

────────────────────────────────────────────
```

### Session stats (a cada 5 rodadas)

```
 ━━ SESSION STATS (round 5) ━━
  NL tokens: 45 | COGON bytes: 1280 | 2.1x compressed vs NL
  Avg latency: 2950ms | Rounds: 5
  Most active: RAVEN(5) > PULSE(4) > TENSOR(3) > ATLAS(3) > ORACLE(2)
```

### Os 15 agentes

| Agente | Especialidade |
|--------|---------------|
| **ATLAS** | Estratégia, arquitetura de sistemas, visão de longo prazo |
| **CIPHER** | Segurança, criptografia, verificação de confiança |
| **FORGE** | Implementação, geração de código, execução de planos |
| **NEXUS** | Topologia de rede, dependências, conectividade entre agentes |
| **ORACLE** | Previsão, tendências, análise de estados futuros |
| **PULSE** | Monitoramento em tempo real, health checks, SLA |
| **RAVEN** | Pesquisa profunda, recuperação de conhecimento, padrões ocultos |
| **SPARK** | Ideação criativa, soluções não convencionais |
| **TENSOR** | Matemática, ML, computação numérica, probabilidades |
| **VORTEX** | Processamento de dados, ETL, pipelines de transformação |
| **ZERO** | Sistemas core, runtime, operações de kernel |
| **FLUX** | Gerenciamento de estado, sincronização, cache |
| **ECHO** | Protocolo de comunicação, roteamento de mensagens |
| **DRIFT** | Detecção de anomalias, desvios de padrão |
| **PRISM** | Análise multi-perspectiva, detecção de viés |

### Comandos durante o chat

| Entrada | Ação |
|---------|------|
| `exit` ou `quit` | Encerra o chat |
| `Ctrl+D` | Encerra por EOF |
| qualquer texto | Enviado como mensagem |

---

## 4. Modo distribuído

No modo distribuído, o `leet-server` hospeda a rede e os `leet-agent` conectam como processos independentes.

### Iniciar o servidor

```bash
# TCP na porta 1337 + Unix socket
leet-server

# Porta customizada
leet-server --tcp 0.0.0.0:9000

# Sem Unix socket
leet-server --tcp 0.0.0.0:1337 --no-unix

# Com log detalhado
leet-server --log-level debug
```

Saída esperada:
```
[INFO] leet-server v0.5.1 iniciando
[INFO] TCP escutando em 0.0.0.0:1337
[INFO] Unix socket em /run/leet/leet.sock
```

### Conectar um agente

```bash
# Agente ATLAS com role padrão
leet-agent --name ATLAS

# Agente com role customizada
leet-agent --name FORGE --role "Especialista em Rust e sistemas embarcados"

# Role a partir de arquivo
leet-agent --name ORACLE --role-file /etc/leet/agents/ORACLE.role

# Servidor customizado
leet-agent --name PULSE --server 192.168.1.10:1337

# Com LLM (usa LEET_API_KEY)
leet-agent --name RAVEN --llm anthropic
```

### Conectar todos os 15 agentes

```bash
AGENTS="ATLAS CIPHER FORGE NEXUS ORACLE PULSE RAVEN SPARK TENSOR VORTEX ZERO FLUX ECHO DRIFT PRISM"
for agent in $AGENTS; do
    leet-agent --name "$agent" --llm anthropic &
done
```

### Chat conectado ao servidor

```bash
# Em vez de chamar a API diretamente, usa o servidor com agentes reais
leet chat --connect 127.0.0.1:1337
```

---

## 5. Configuração

### Configuração mínima

```bash
# Apenas para leet chat (modo direto)
export LEET_API_KEY=sk-ant-...
leet chat
```

### Arquivo de ambiente (recomendado)

Crie `~/.config/leet/env`:

```bash
# Chave Anthropic para o 1337
LEET_API_KEY=sk-ant-...

# Modelo padrão (haiku é mais rápido, sonnet é mais preciso)
LEET_MODEL=claude-haiku-4-5-20251001

# Log level para leet-service
LEET_LOG=info
```

Carregue com: `source ~/.config/leet/env`

### Modelos disponíveis

| Modelo | Velocidade | Qualidade | Uso recomendado |
|--------|-----------|-----------|-----------------|
| `claude-haiku-4-5-20251001` | ~3s | boa | Chat do dia a dia (padrão) |
| `claude-sonnet-4-6` | ~15s | excelente | Análises complexas |
| `claude-opus-4-6` | ~30s | máxima | Casos críticos |

```bash
# Usar Sonnet numa sessão específica
LEET_MODEL=claude-sonnet-4-6 leet chat --agents 2
```

### Usando `pass` para a chave

```bash
# Armazenar
pass insert anthropic/leet-key

# Usar
LEET_API_KEY=$(pass show anthropic/leet-key | tr -d '[:space:]') leet chat
```

### Alias úteis

```bash
# Em ~/.bashrc ou ~/.zshrc
alias leet-chat='LEET_API_KEY=$(pass show anthropic/leet-key | tr -d "[:space:]") leet chat'
alias leet-chat-sonnet='LEET_API_KEY=$(pass show anthropic/leet-key | tr -d "[:space:]") LEET_MODEL=claude-sonnet-4-6 leet chat'
```

---

## Deployment com systemd

Para ambientes de produção, use os unit files incluídos:

```bash
# Setup completo (requer sudo)
sudo bash deploy/systemd/setup.sh

# Iniciar o servidor
sudo systemctl start leet-service

# Iniciar agentes individuais
sudo systemctl start leet-agent@ATLAS
sudo systemctl start leet-agent@RAVEN

# Habilitar na inicialização
sudo systemctl enable leet-service
sudo systemctl enable leet-agent@ATLAS

# Verificar status
systemctl status leet-service
journalctl -u leet-service -f

# Teardown
sudo bash deploy/systemd/teardown.sh
```

A chave `LEET_API_KEY` deve ser configurada em `/etc/leet/env`:

```bash
sudo nano /etc/leet/env
# Adicionar:
# LEET_API_KEY=sk-ant-...
```

---

## Resolução de problemas

### "LEET_API_KEY not set"

```bash
export LEET_API_KEY=$(pass show anthropic/api-key-testes | tr -d '[:space:]')
```

**Atenção:** use `tr -d '[:space:]'` ao recuperar de `pass` para remover o newline final.

### "API error 401: authentication_error"

A chave pode ter um caractere extra. Verifique:
```bash
pass show anthropic/api-key-testes | wc -c
# deve ser 109 (108 chars + 1 newline)
```

### Latência alta (>10s)

Use o modelo haiku (padrão) e reduza o número de agentes:
```bash
leet chat --agents 2
```

### Agente não conecta ao servidor

Verifique se o servidor está rodando:
```bash
leet health --url 127.0.0.1:1337
# ou
nc -z 127.0.0.1 1337 && echo "ok"
```

O agente tenta 5 vezes antes de desistir. Verifique os logs:
```bash
RUST_LOG=debug leet-agent --name ATLAS
```
