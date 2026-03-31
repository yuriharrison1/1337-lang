# Phase 3 — IDE Adapters (v0.5.0)

Adaptadores para integração do protocolo 1337 com ferramentas de coding populares.

## 🚀 Adapters Implementados

### 1. Claude Code Adapter ✅

**Arquivo:** `python/leet/adapters/claude_code.py`

Integração com a CLI oficial da Anthropic.

```python
from leet.adapters import ClaudeCodeAdapter

adapter = ClaudeCodeAdapter(
    project_dir="/path/to/project",
    model="claude-sonnet-4-20250514",
    auto_accept=False  # Requer aprovação
)

if adapter.is_available():
    response = await adapter.send_message(
        "Explique este código",
        context=AdapterContext(file_path="main.py")
    )
    print(response.text)
```

**Features:**
- Modo não-interativo (`--output`)
- Contexto de arquivos automático
- Integração git
- Extração de arquivos modificados
- Projeção 1337 automática

---

### 2. Codex Adapter ✅

**Arquivo:** `python/leet/adapters/codex.py`

Integração com OpenAI Codex CLI.

```python
from leet.adapters import CodexAdapter

adapter = CodexAdapter(
    project_dir="/path/to/project",
    model="gpt-4o",
    approval_mode="suggest"  # full/suggest/none
)

response = await adapter.send_message(
    "Refatore esta função",
    image_paths=["screenshot.png"]  # Suporte a imagens
)
```

**Features:**
- Múltiplos modos de aprovação
- Suporte a imagens
- Análise de código
- Geração de testes

---

### 3. Kimi Adapter ✅

**Arquivo:** `python/leet/adapters/kimi.py`

Integração com Kimi Code CLI (Moonshot AI).

```python
from leet.adapters import KimiAdapter

adapter = KimiAdapter(
    project_dir="/path/to/project",
    model="kimi-k1.5",
    temperature=0.7
)

# Fallback automático para API se CLI não disponível
response = await adapter.send_message("Analise este projeto")

# Streaming nativo via API
async for chunk in adapter.stream_message("Long analysis..."):
    print(chunk, end='')
```

**Features:**
- Contexto longo (200K+ tokens)
- Fallback CLI → API
- Streaming nativo
- Suporte multilíngue

---

### 4. Aider Adapter ✅

**Arquivo:** `python/leet/adapters/aider.py`

Integração com Aider (multi-LLM coding assistant).

```python
from leet.adapters import AiderAdapter

adapter = AiderAdapter(
    project_dir="/path/to/project",
    model="gpt-4o",
    editor_model="gpt-4o-mini",  # Modelo para edições
    auto_commit=True,
    test_cmd="pytest",
    lint_cmd="ruff check ."
)

# Envia mensagem
response = await adapter.send_message(
    "Adicione tratamento de erro",
    files=["api.py"],
    read_only=["models.py"]  # Contexto só leitura
)

# Comandos específicos
await adapter.lint()
await adapter.test()
await adapter.commit("Mensagem do commit")
await adapter.undo()  # Desfaz última mudança
```

**Features:**
- Múltiplos modelos (principal/editor/weak)
- Commit automático
- Testes e linting integrados
- Mapa de repositório
- Undo/Reset

---

## 🛠️ CLI Unificado

**Arquivo:** `python/leet/adapters/cli.py`

Entry point: `leet-ide`

```bash
# Instalar
pip install leet1337[all]

# Listar adaptadores
leet-ide --list
# Output: claude, codex, kimi, aider

# Verificar disponibilidade
leet-ide --check
# Output:
# ✅ claude   0.2.14
# ✅ codex    1.0.0
# ✅ kimi     1.2.0
# ✅ aider    0.60.0

# Usar Claude Code
leet-ide claude "Explique main.py" --file main.py --project .

# Usar Codex
leet-ide codex "Refatore" --file utils.py --approval-mode suggest

# Kimi com streaming
leet-ide kimi "Analise projeto" --stream

# Aider com auto-commit
leet-ide aider "Fix bug" --auto-commit --file bug.py

# Auto-detectar adaptador disponível
leet-ide auto "Mensagem" --file code.py

# Exportar sessão
leet-ide claude "Mensagem" --export session.json
```

---

## 📊 Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI (leet-ide)                          │
├─────────────────────────────────────────────────────────────┤
│  BaseIDEAdapter (abstract)                                  │
│  ├── AdapterContext (file, selection, etc)                  │
│  ├── AdapterResponse (text, cogon, files)                   │
│  └── SemanticProjector (text → COGON)                       │
├─────────────────────────────────────────────────────────────┤
│  Implementações                                             │
│  ├── ClaudeCodeAdapter ──▶ claude CLI                       │
│  ├── CodexAdapter ───────▶ codex CLI                        │
│  ├── KimiAdapter ────────▶ kimi CLI / API                   │
│  └── AiderAdapter ───────▶ aider CLI                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testes

**Arquivo:** `python/tests/test_adapters.py`

```bash
cd python
pytest tests/test_adapters.py -v
```

Cobertura:
- Testes unitários de cada adapter
- Testes de contexto e projeção
- Testes de integração
- Testes do CLI

---

## 📦 Instalação

```bash
# Básico (sem adapters pesados)
pip install leet1337

# Com suporte a todos os adapters
pip install leet1337[all]

# Específico
pip install leet1337[anthropic]   # Claude
pip install leet1337[openai]      # Codex
```

---

## 🔌 Uso Programático

```python
import asyncio
from leet.adapters import create_adapter, AdapterContext

async def main():
    # Cria adapter
    adapter = create_adapter('claude', project_dir='.')
    
    # Verifica disponibilidade
    if not adapter.is_available():
        print("Claude Code não instalado")
        return
    
    # Contexto
    ctx = AdapterContext(
        file_path="main.py",
        selection="def problematic():",
        language="python"
    )
    
    # Envia mensagem
    response = await adapter.send_message(
        "Corrija esta função",
        context=ctx
    )
    
    # Resultado
    print(f"Texto: {response.text}")
    print(f"Arquivos: {response.files_modified}")
    print(f"Sucesso: {response.success}")
    
    # COGON da resposta (se auto_project=True)
    if response.cogon:
        print(f"Semântica: {response.cogon.sem[:5]}")
    
    # Convergência da sessão
    score = adapter.get_convergence_score()
    print(f"Convergência: {score:.2f}")

asyncio.run(main())
```

---

## 🔄 Integração com 1337

Cada mensagem é automaticamente projetada em um COGON:

```python
# Projeção do input
input_cogon = await adapter.project_to_cogon("Mensagem do usuário")

# Projeção da resposta
output_cogon = await adapter.project_to_cogon(response.text)

# Computa delta
delta = adapter.compute_delta(input_cogon, output_cogon)

# Distância semântica
from leet import dist
distance = dist(input_cogon, output_cogon)
```

Isso permite:
- Análise de convergência da conversa
- Compressão delta entre mensagens
- Busca semântica no histórico
- Detecção de anomalias

---

## 🗺️ Roadmap Futuro

- [ ] VS Code Extension
- [ ] Neovim Plugin
- [ ] JetBrains Plugin
- [ ] Sublime Text Plugin
- [ ] Emaccs Integration
- [ ] GitHub Copilot Adapter
- [ ] Continue.dev Adapter

---

**Versão:** 0.5.0  
**Total de linhas:** ~1,500 (Python)  
**Testes:** 30+ testes automatizados
