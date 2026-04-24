# leet-vm

VM de orquestração de agentes em Python. Gerencia projeção, memória semântica, sessões e roteamento de mensagens.

## Visão Geral

```
Input (text | JSON-RPC | MCP | REST)
     │
     ▼
LeetVM.process()
     ├── Adapter → Frame   (detecção e decode do protocolo)
     ├── Projector → Cogon (LocalProjector | ServiceProjector)
     ├── PersonalStore     (recall de contexto semântico)
     ├── SessionDAG        (delta de sessão)
     ├── Router            (despacha para o agente handler)
     └── SurfaceC4         (reconstituição de texto)
     │
     ▼
VMResult { text, cogon, tokens_saved, session_id }
```

## LeetVM

```python
from leet_vm.vm import LeetVM

vm = LeetVM(
    mode="auto",               # "auto" | "local" | "service"
    service_url="localhost:50051",
    store_backend="memory",    # "memory" | Redis URL
)
```

### Modos de Projeção

| Modo | Comportamento |
|------|---------------|
| `"local"` | Sempre usa `LocalProjector` (heurísticas, sem rede) |
| `"service"` | Sempre usa `ServiceProjector` (conecta ao leet-service gRPC) |
| `"auto"` | Tenta `ServiceProjector`; cai para `LocalProjector` se indisponível |

### Processamento

```python
result = await vm.process(
    input=texto_ou_frame,
    agent_id="meu-agente",
    session_id="sess-uuid",
    protocol="auto",        # "auto" | "text" | "json_rpc" | "mcp" | "rest"
    target_agent="",        # agente específico ou "" para default
)

print(result.text)           # texto reconstruído
print(result.tokens_saved)   # estimativa de tokens economizados
print(result.cogon)          # Cogon resultante
```

### Pipeline de Processamento (7 etapas)

1. **Detecção de protocolo** — identifica o formato do input
2. **Decode via Adapter** — extrai `Frame(method, params)`
3. **Projeção → COGON** — `Projector.project(text, agent_id)`
4. **Recall de contexto** — 5 COGONs mais próximos do `PersonalStore`
5. **DELTA de sessão** — apenas o que mudou desde o último request na sessão
6. **Roteamento** — despacha `(cogon, context)` ao handler registrado
7. **Persistência** — salva input e resultado no store e na sessão

### Registro de Agentes

```python
async def meu_handler(cogon: Cogon, context: list[Cogon]) -> Cogon:
    # processa e retorna cogon de resposta
    ...

vm.register_agent("agente-x", meu_handler)
vm.set_default_agent(meu_handler)  # handler para agentes não registrados
```

## Projectors

### LocalProjector

Projeção local via heurísticas de palavras-chave. Sem rede, sem API.

```python
from leet_vm.projector.local import LocalProjector

proj = LocalProjector()
cogon = await proj.project("texto", "agent-id")
text  = await proj.decode(cogon)
```

### ServiceProjector

Conecta ao `leet-service` gRPC. Usa `encode` e `decode` do serviço.

```python
from leet_vm.projector.service import ServiceProjector

proj = ServiceProjector("localhost:50051")
cogon = await proj.project("texto", "agent-id")
```

Cai graciosamente — se o serviço não responder, o `LeetVM` em modo `auto` substitui por `LocalProjector`.

## PersonalStore

Memória semântica persistente por agente. Suporta recall por similaridade cosseno.

```python
from leet_vm.store.personal import PersonalStore

store = PersonalStore("memory")   # ou Redis URL

await store.add(agent_id, cogon, text="hint opcional")
results = await store.recall(agent_id, cogon, k=5)
# results: list[(record_dict, dist_float)]

count = await store.count(agent_id)
```

## SessionDAG

Rastro de sessão — DAG de COGONs trocados na sessão atual. Permite calcular DELTA incremental.

```python
from leet_vm.store.session import SessionDAG

session = SessionDAG(session_id="uuid")
session.add(cogon)
prev_stamp = session.last_stamp()
delta = session.delta_since(prev_stamp)  # list[Cogon]
```

## Adapters

Detectam e decodificam diferentes formatos de input:

| Protocolo | Detecção |
|-----------|----------|
| `text` | string simples |
| `json_rpc` | `{"jsonrpc": "2.0", ...}` |
| `mcp` | `{"method": "tools/call", ...}` |
| `rest` | `{"path": ..., "body": ...}` |

```python
from leet_vm.adapters.registry import detect_protocol, ADAPTERS

protocol = detect_protocol(input_data)
frame = ADAPTERS[protocol].decode(input_data)
# frame.method, frame.params
```

## SurfaceC4

Reconstituição de texto para interface humana a partir de um COGON.

```python
from leet_vm.runtime.surface import SurfaceC4

surface = SurfaceC4()
text = surface.reconstruct(cogon)
```

## Router

Despacha COGONs para handlers registrados.

```python
from leet_vm.runtime.router import Router

router = Router()
router.register("agente-x", handler_x)
router.set_default(handler_default)

result = await router.route(cogon, context, target_agent="")
```

## Testes

```bash
cd leet-vm
python -m pytest      # todos os testes da VM
```

Testes cobrem: adapters, projectors (local e service mock), store (add/recall/count), VM end-to-end.
