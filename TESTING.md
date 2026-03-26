# Guia de Testes - Projeto 1337 v0.4

Este documento descreve todos os procedimentos para testar o projeto 1337 completo.

---

## 📋 Pré-requisitos

```bash
# Rust (stable)
rustc --version  # >= 1.70
cargo --version

# Python (>= 3.10)
python --version

# Git
gh --version  # GitHub CLI (opcional)
```

---

## 🦀 1. Testes Rust

### 1.1 leet-core (Motor Principal)

```bash
cd leet1337

# Build e testes
cargo build
cargo test -p leet_core

# Release build (para FFI)
cargo build --release

# Verificar símbolos C exportados (Linux/Mac)
nm -D target/release/libleet_core.so 2>/dev/null | grep leet_
```

**Esperado:** 23 testes passando ✅

### 1.2 leet-bridge (Tradução Humano↔1337)

```bash
cd leet1337

# Testes
cargo test -p leet_bridge

# Testes com runtime async
cargo test -p leet_bridge --features tokio-runtime
```

**Esperado:** 12 testes passando ✅

### 1.3 Todos os crates Rust

```bash
cd leet1337
cargo test --all
```

**Esperado:** 35 testes passando (23 + 12) ✅

---

## 🐍 2. Testes Python

### 2.1 Instalação

```bash
cd python

# Instalar em modo desenvolvimento
pip install -e ".[dev]"

# Verificar instalação
python -c "import leet; print(f'leet {leet.__version__} backend={leet.BACKEND}')"
```

**Esperado:** `leet 0.4.0 backend=python` (ou `backend=rust` se PyO3 disponível)

### 2.2 Testes Unitários

```bash
cd python

# Todos os testes unitários
pytest tests/test_types.py tests/test_operators.py tests/test_validate.py \
       tests/test_bridge.py tests/test_cli.py -v

# Ou simplesmente
pytest tests/ -v --ignore=tests/test_e2e.py
```

**Esperado:** 43 testes passando ✅

### 2.3 Testes E2E (Integração)

```bash
cd python

# Testes end-to-end
pytest tests/test_e2e.py -v

# Com cobertura detalhada
pytest tests/test_e2e.py -v --tb=short
```

**Esperado:** 39 testes passando ✅

### 2.4 Todos os testes Python

```bash
cd python
pytest -v
```

**Esperado:** 82 testes passando (43 + 39) ✅

---

## 🖥️ 3. Testes da CLI

### 3.1 Comandos Básicos

```bash
# Verificar instalação da CLI
which leet

# Testar comandos
leet version        # Deve mostrar "1337 v0.4.0"
leet zero           # Deve mostrar COGON_ZERO JSON
leet axes           # Deve listar 32 eixos
leet axes --group A # Deve listar 14 eixos ontológicos
```

### 3.2 Encode/Decode

```bash
# Criar diretório temporário
cd /tmp

# Encode de texto
leet encode "O servidor caiu" > cogon1.json
cat cogon1.json | python -m json.tool  # Verificar JSON válido

# Verificar valores nos eixos corretos
python -c "
import json
data = json.load(open('cogon1.json'))
print(f'URGÊNCIA (C1): {data[\"sem\"][22]:.2f}')  # Deve ser > 0.7
print(f'ANOMALIA (C5): {data[\"sem\"][26]:.2f}')   # Deve ser > 0.7
"

# Decode (reconstrução)
leet decode cogon1.json  # Deve mostrar representação do COGON

# Cleanup
rm cogon1.json
```

### 3.3 Operadores CLI

```bash
cd /tmp

# Criar dois COGONs
leet encode "situação normal" > c1.json
leet encode "situação urgente" > c2.json

# BLEND (interpolação)
leet blend c1.json c2.json --alpha 0.5 > blended.json

# DIST (distância)
leet dist c1.json c2.json  # Deve mostrar valor > 0 (diferentes)

# Validar que distância de um COGON com ele mesmo é ~0
leet dist c1.json c1.json  # Deve ser ~0.0000

rm c1.json c2.json blended.json
```

### 3.4 Validação

```bash
cd /tmp

# Criar MSG_1337 válida
python -c "
from leet import *
msg = Msg1337(
    id='a'*36, sender='b'*36,
    receiver=Receiver(agent_id='c'*36),
    intent=Intent.ASSERT,
    payload=Cogon.new([0.5]*32, [0.1]*32),
    c5=CanonicalSpace([0.5]*32, {}, '0.4.0', 'abc'),
    surface=Surface(False, None, 3, 'pt')
)
open('valid_msg.json', 'w').write(msg.to_json())
"

# Validar
leet validate valid_msg.json  # Deve mostrar "✓ Valid MSG_1337"

# Criar MSG_1337 inválida (BROADCAST com ASSERT)
python -c "
from leet import *
msg = Msg1337(
    id='a'*36, sender='b'*36,
    receiver=Receiver.broadcast(),  # BROADCAST!
    intent=Intent.ASSERT,            # ASSERT não permitido com BROADCAST!
    payload=Cogon.new([0.5]*32, [0.1]*32),
    c5=CanonicalSpace([0.5]*32, {}, '0.4.0', 'abc'),
    surface=Surface(False, None, 3, 'pt')
)
open('invalid_msg.json', 'w').write(msg.to_json())
"

# Validar (deve falhar R8)
leet validate invalid_msg.json  # Deve mostrar erro R8

rm valid_msg.json invalid_msg.json
```

---

## 🌐 4. Testes da Rede Interativa (net1337.py)

### 4.1 Modo Mock (Sem API)

```bash
cd /home/yuri/Projetos/1337  # ou onde clonou o repo

# Cenário de incidente
python net1337.py --scenario incident --backend mock << 'EOF'
/status
/heatmap all
/dist 1 2
/quit
EOF
```

**Verificações:**
- ✅ Handshake C5 com COGON_ZERO
- ✅ Dois agentes (Engenheiro, Analista)
- ✅ Estímulo inicial processado
- ✅ Comandos /status, /heatmap, /dist funcionam

### 4.2 Modo Interativo

```bash
python net1337.py --scenario devops --backend mock

# Comandos para testar interativamente:
/inject Precisamos fazer rollback urgente
/talk 1 Qual é sua análise?
/agents chat 2
/heatmap 1
/delta 1
/blend 1 2
/export log.json
/quit
```

### 4.3 Com DeepSeek (se tiver API key)

```bash
export DEEPSEEK_API_KEY="sk-..."
python net1337.py --scenario anomaly --backend deepseek
```

### 4.4 Com Anthropic (se tiver API key)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python net1337.py --scenario brainstorm --backend anthropic
```

---

## 🔗 5. Testes de Integração Rust-Python

### 5.1 Compilar PyO3

```bash
cd leet1337

# Instalar maturin (se não tiver)
pip install maturin

# Build com feature Python
maturin develop --features python

# Verificar
python -c "import leet_core; print(leet_core.version())"
```

**Esperado:** `"0.4.0"` ✅

### 5.2 Testar com Backend Rust

```bash
cd python

# Verificar que detectou Rust
python -c "import leet; print(f'Backend: {leet.BACKEND}')"

# Deve mostrar: Backend: rust

# Rodar testes (agora usando Rust internamente)
pytest tests/ -v -k "not anthropic"
```

### 5.3 Verificar FFI (C ABI)

```bash
cd leet1337
cargo build --release

# Verificar biblioteca compilada
ls -la target/release/libleet_core.*

# Testar com ctypes (Python)
python -c "
import ctypes
import glob

lib_path = glob.glob('target/release/libleet_core.so')[0]
lib = ctypes.CDLL(lib_path)

lib.leet_cogon_zero.restype = ctypes.c_char_p
result = lib.leet_cogon_zero()
print('COGON_ZERO:', result.decode()[:100], '...')

lib.leet_version.restype = ctypes.c_char_p
print('Version:', lib.leet_version().decode())
"
```

---

## 🧪 6. Teste Completo (Script Único)

Execute este script para testar tudo de uma vez:

```bash
#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════"
echo "  TESTE COMPLETO - PROJETO 1337 v0.4"
echo "═══════════════════════════════════════════════════"

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Testar Rust
echo ""
echo "🦀 Testando Rust..."
cd leet1337
cargo test --all --quiet
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Rust: 35 testes passaram${NC}"
else
    echo -e "${RED}❌ Rust: Falhou${NC}"
    exit 1
fi

# Testar Python
echo ""
echo "🐍 Testando Python..."
cd ../python
pytest --tb=short -q
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python: 82 testes passaram${NC}"
else
    echo -e "${RED}❌ Python: Falhou${NC}"
    exit 1
fi

# Testar CLI
echo ""
echo "🖥️  Testando CLI..."
leet version > /dev/null
leet zero > /dev/null
leet axes > /dev/null
echo -e "${GREEN}✅ CLI funcionando${NC}"

# Testar net1337.py
echo ""
echo "🌐 Testando net1337.py..."
cd ..
echo "/status
/quit" | python net1337.py --scenario incident --backend mock > /dev/null 2>&1
echo -e "${GREEN}✅ net1337.py funcionando${NC}"

echo ""
echo "═══════════════════════════════════════════════════"
echo -e "${GREEN}  🎉 TODOS OS TESTES PASSARAM!${NC}"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Resumo:"
echo "  • Rust: 35 testes (leet-core: 23, leet-bridge: 12)"
echo "  • Python: 82 testes (unitários: 43, E2E: 39)"
echo "  • CLI: Comandos básicos OK"
echo "  • Rede: Simulação de agentes OK"
echo "  • Total: 117 testes ✅"
```

Salve como `test_all.sh` e execute:

```bash
chmod +x test_all.sh
./test_all.sh
```

---

## 📊 Tabela de Testes

| Componente | Comando | Testes | Crítico? |
|------------|---------|--------|----------|
| leet-core | `cargo test -p leet_core` | 23 | ⭐⭐⭐ |
| leet-bridge | `cargo test -p leet_bridge` | 12 | ⭐⭐⭐ |
| Python types | `pytest tests/test_types.py` | 15 | ⭐⭐⭐ |
| Python operators | `pytest tests/test_operators.py` | 11 | ⭐⭐⭐ |
| Python validate | `pytest tests/test_validate.py` | 9 | ⭐⭐ |
| Python bridge | `pytest tests/test_bridge.py` | 6 | ⭐⭐ |
| Python CLI | `pytest tests/test_cli.py` | 7 | ⭐ |
| E2E | `pytest tests/test_e2e.py` | 39 | ⭐⭐⭐ |
| CLI manual | `leet zero` | - | ⭐⭐ |
| Rede mock | `net1337.py --scenario incident` | - | ⭐⭐ |

---

## 🐛 Troubleshooting

### Problema: `cargo test` falha

```bash
# Limpar e rebuild
cargo clean
cargo build
cargo test
```

### Problema: `pytest` não encontra módulo

```bash
cd python
pip install -e ".[dev]"
python -m pytest tests/
```

### Problema: `leet` comando não encontrado

```bash
# Verificar se está no PATH
which leet

# Ou rodar como módulo
cd python
python -m leet.cli zero
```

### Problema: net1337.py falha com import

```bash
# Verificar Python path
cd /caminho/correto/do/projeto
python net1337.py --help
```

---

## ✅ Checklist Final

Antes de considerar o projeto pronto, verifique:

- [ ] `cargo test --all` passa (35 testes)
- [ ] `pytest` passa (82 testes)
- [ ] `leet version` funciona
- [ ] `leet zero` mostra COGON_ZERO
- [ ] `leet encode "teste"` gera JSON válido
- [ ] `net1337.py --scenario incident` roda sem erros
- [ ] `/status` no net1337 mostra agentes
- [ ] `/quit` sai gracefulmente

---

**Total de testes automatizados: 117** ✅
