# Primeiros Passos com 1337

## Pré-requisitos

| Cenário | Requisitos |
|---------|-----------|
| Python SDK puro | Python 3.10+ |
| CLI + chat | Rust 1.75+, `LEET_API_KEY` |
| Modo distribuído | Rust 1.75+, `LEET_API_KEY`, systemd (Linux) |

---

## Instalação

### CLI Rust (recomendado para começar)

```bash
git clone <repo>
cd 1337
cargo build --release -p leet-cli
```

Adicione ao PATH:
```bash
export PATH="$PWD/target/release:$PATH"
```

Verificar:
```bash
leet version
# leet 0.5.0 | spec v0.5.1
```

### Python SDK

```bash
cd 1337
pip install -e python/       # SDK core
pip install -e leet-py/      # SDK público simplificado
```

---

## 5 minutos com a CLI

### 1. Projetar um texto

```bash
leet encode "sistema crítico, falha detectada"
```

Você verá barras coloridas representando cada um dos 32 eixos semânticos. Os eixos mais ativos serão os de anomalia (P3), urgência (G8) e ação (P7).

### 2. Ver os eixos ativos

```bash
leet inspect "$(leet encode 'sistema crítico' | cat)"
# ou pipeline direto:
leet encode "sistema crítico" | leet inspect
```

### 3. Medir distância semântica

```bash
leet dist "sistema estável" "sistema crítico"
# 0.782 — semanticamente distantes

leet dist "falha" "erro"
# 0.143 — semanticamente próximos
```

### 4. Misturar dois conceitos

```bash
leet blend "urgente" "rotineiro" --alpha 0.7
# COGON 70% "urgente", 30% "rotineiro"
```

### 5. Ver todos os eixos

```bash
leet axes
# Tabela com os 32 eixos canônicos, grupos e descrições
```

### 6. COGON_ZERO

```bash
leet zero
# Imprime o COGON de identidade — handshake inicial do protocolo
```

---

## Primeiro chat multiagente

### 1. Configurar a chave

```bash
# Usando pass
export LEET_API_KEY=$(pass show anthropic/minha-chave | tr -d '[:space:]')

# Ou diretamente
export LEET_API_KEY=sk-ant-...
```

### 2. Iniciar o chat

```bash
leet chat
```

Você verá o banner de boas-vindas e o prompt `YURI ›`. Digite qualquer coisa em português.

### 3. Exemplo de sessão

```
 Connecting to Anthropic... OK
 COGON_ZERO transmitted ✓
────────────────────────────────────────────

 YURI › qual é o status do nosso sistema de autenticação?

  ↳ ~9 tokens | 48B NL | 256B COGON | 5.3x NL size

  PULSE  "Todos os endpoints de autenticação respondem dentro do SLA. Zero erros 5xx nas últimas 2h."
  RAVEN  "Sem anomalias no padrão de login. Taxa de sucesso: 99.7%."
  CIPHER "Nenhuma tentativa de força bruta detectada. Certificados TLS válidos por mais 89 dias."

  latência: 2.8s | ~52 tok/s | 3 agentes responderam

────────────────────────────────────────────
```

---

## Python SDK — primeiros passos

### Tipos básicos

```python
from leet import Cogon, blend, dist

# COGON_ZERO
zero = Cogon.zero()
print(zero.sem[:4])  # [1.0, 1.0, 1.0, 1.0]
print(zero.unc[:4])  # [0.0, 0.0, 0.0, 0.0]

# Criar COGON manual
import uuid, time
cogon = Cogon(
    id=str(uuid.uuid4()),
    sem=[0.5] * 32,
    unc=[0.1] * 32,
    stamp=int(time.time() * 1e9),
)
```

### Operadores

```python
from leet import blend, delta, dist, focus, anomaly_score

a = Cogon(id=str(uuid.uuid4()), sem=[0.2]*32, unc=[0.1]*32, stamp=0)
b = Cogon(id=str(uuid.uuid4()), sem=[0.8]*32, unc=[0.1]*32, stamp=0)

print(dist(a, b))            # distância cosseno
print(blend(a, b, 0.5).sem)  # ponto médio
```

### Validação

```python
from leet import Msg1337, validate_msg

msg = Msg1337(
    id=str(uuid.uuid4()),
    sender=str(uuid.uuid4()),
    receiver="all",
    intent="ASSERT",
    payload=Cogon.zero(),
)

result = validate_msg(msg)
print(result)  # True ou descrição do erro
```

### leet-py (SDK simplificado)

```python
import sys
sys.path.insert(0, "leet-py")
import leet

# Mock (sem API key, para desenvolvimento)
client = leet.connect("mock")
result = client.encode("sistema crítico")
print(result.sem[26])  # P3_ANOMALIA

# Anthropic
client = leet.connect("anthropic")  # lê LEET_PROJECTION_ANTHROPIC_API_KEY
```

---

## Modo distribuído — início rápido

```bash
# Terminal 1: servidor
cargo build --release -p leet-service
./target/release/leet-server

# Terminal 2: 3 agentes
for a in ATLAS RAVEN PULSE; do
    LEET_API_KEY=$LEET_API_KEY \
    ./target/release/leet-agent --name $a --llm anthropic &
done

# Terminal 3: chat via servidor
leet chat --connect 127.0.0.1:1337
```

---

## Próximos passos

- [USER_GUIDE.md](USER_GUIDE.md) — todos os comandos CLI com exemplos
- [PROTOCOL.md](PROTOCOL.md) — especificação dos 32 eixos e handshake C5
- [API_REFERENCE.md](API_REFERENCE.md) — API completa Rust e Python
- [DEPLOYMENT.md](DEPLOYMENT.md) — produção com systemd
