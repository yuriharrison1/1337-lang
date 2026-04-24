# Primeiros Passos

## Pré-requisitos

- Rust 1.75+ (`rustup update`)
- Python 3.11+
- `cargo` e `pip`

## 1. Clonar e Compilar

```bash
git clone <repo>
cd 1337
cargo build --workspace --release
```

O binário principal estará em `target/release/leet`.

## 2. Verificar a Instalação

```bash
./target/release/leet version
./target/release/leet axes    # lista os 32 eixos canônicos
```

## 3. Primeiro COGON

```bash
# Encode: texto → vetor semântico
./target/release/leet encode "deploy urgente falhou em produção"
```

Saída típica:
```
G8  URGENCY          ████████████████████ 0.95
P3  ANOMALY          ███████████████████  0.90
D1  STATE            █████████████████    0.85
P7  ACTION           ████████████████     0.80
D2  PROCESS          ███████████████      0.75
...
```

## 4. Distância Semântica

```bash
./target/release/leet dist "urgente" "tranquilo"
# → 0.82 (muito diferentes)

./target/release/leet dist "deploy falhou" "falha no deploy"
# → 0.04 (semanticamente equivalentes — skip re-envio)
```

## 5. Blend de Contextos

```bash
./target/release/leet blend "sistema estável" "alerta crítico" --alpha 0.3
# 30% estável, 70% crítico
```

## 6. SDK Python

```bash
# Instalar dependências
pip install -e python/
pip install -e leet-vm/
pip install -e leet-py/

# Testar importação
python3 -c "import leet; print('OK')"
```

### Uso básico

```python
import asyncio
import leet

async def main():
    # Modo mock (sem API key necessária)
    client = leet.connect("mock")
    
    response = await client.chat("qual é o status?")
    print(response.text)
    print(f"Tokens economizados: {response.tokens_saved}")

asyncio.run(main())
```

### Com Anthropic

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

```python
client = leet.connect("anthropic")
response = await client.chat("resuma o contexto do projeto")
```

## 7. Suíte de Testes

```bash
# Rust
cargo test --workspace

# Python
cd python && python -m pytest
cd ../leet-vm && python -m pytest
cd ../leet-py && python -m pytest

# Auditoria completa (clippy + testes + PT names + CLI + Python)
bash test_all.sh
```

## 8. Verificar o MCP Server

Se estiver usando Claude Code, o MCP server já está configurado via `.claude/settings.json`.

```bash
# Verificar se o servidor arranca
python3 mcp/leet_mcp.py &

# No Claude Code, as tools estarão disponíveis:
# encode(), dist(), blend(), axes(), inspect()
```

## Próximos Passos

- [COGON](../COGON.md) — entender o vetor semântico e os 32 eixos
- [leet-cli](../crates/leet-cli.md) — todos os subcomandos
- [leet-py](../python/leet-py.md) — SDK Python completo
- [Claude Code / MCP](mcp-claude-code.md) — integração com Claude Code
- [Deploy](deployment.md) — rodar em produção com systemd
