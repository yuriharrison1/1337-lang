# leet-py — SDK Público

SDK público Python para integrar qualquer aplicação com o protocolo 1337. Interface de alto nível sobre `leet-vm`.

## Instalação

```bash
pip install -e leet-py/
```

## Início Rápido

```python
import leet

# Conectar com um provider LLM
client = leet.connect("anthropic")

# Chat com memória semântica automática
response = await client.chat("qual é o status do deploy?")
print(response.text)
print(f"Tokens economizados: {response.tokens_saved}")
```

## `leet.connect()`

Ponto de entrada único. Retorna um `LeetClient` pronto para uso.

```python
client = leet.connect(
    provider="anthropic",   # "anthropic" | "openai" | "deepseek" | "gemini" | "ollama" | "mock"
    model=None,             # modelo específico (None = padrão do provider)
    base_url=None,          # URL base customizada (ex: OpenAI-compatible APIs)
    api_key=None,           # API key (None = lê de LEET_API_KEY ou variável do provider)
    service="auto",         # "auto" | gRPC URL | "local"
    store="auto",           # "auto" | Redis URL | "memory"
    agent_id="default",     # identificador do agente
)
```

### Exemplos de Conexão

```python
leet.connect("anthropic")                                        # Claude via Anthropic
leet.connect("openai")                                           # GPT via OpenAI
leet.connect("deepseek")                                         # DeepSeek
leet.connect("gemini")                                           # Google Gemini
leet.connect("ollama", model="llama3")                           # Ollama local
leet.connect("openai", base_url="https://api.deepseek.com", model="deepseek-chat")
leet.connect("anthropic", service="localhost:50051")             # com leet-service
leet.connect("anthropic", store="redis://localhost:6379")        # Redis como store
```

## `LeetClient`

### `.chat(text)` → `Response`

Envia uma mensagem. Memória, contexto semântico e compressão são automáticos.

```python
response = await client.chat("preciso de ajuda com o deploy")

response.text          # str — resposta do LLM
response.cogon         # Cogon — estado semântico da resposta
response.tokens_saved  # int — estimativa de tokens economizados
response.model         # str — modelo usado
response.provider      # str — provider usado
response.session_id    # str — UUID da sessão atual
```

### `.chat_stream(text)` → `AsyncIterator[str]`

Versão streaming. Retorna tokens à medida que chegam.

```python
async for token in client.chat_stream("explique o erro"):
    print(token, end="", flush=True)
```

### `.recall(query, k=5)` → `list[dict]`

Busca semântica na memória do agente.

```python
results = await client.recall("status do servidor", k=3)
for r in results:
    print(r["text"], r["dist"], r["stamp"])
```

### `.remember(text)` → `None`

Adiciona explicitamente ao `PersonalStore`.

```python
await client.remember("deploy da versão 1.2 feito em 14/01")
```

### `.encode(text)` → `Cogon`

Projeta texto em COGON sem gerar resposta.

```python
cogon = await client.encode("sistema instável")
```

### `.decode(cogon)` → `str`

Reconstrói texto a partir de COGON.

```python
text = await client.decode(cogon)
```

### `.agents(*agent_fns)` → `AgentNetwork`

Cria uma rede de agentes especializados.

```python
network = client.agents(resumidor, analista, executor)
response = await network.chat("analise este log de erro")
```

### `.new_session()`

Inicia uma nova sessão (reseta o DELTA incremental).

```python
client.new_session()
```

### `.stats`

Estatísticas acumuladas da sessão.

```python
stats = client.stats
stats.tokens_used    # int
stats.tokens_saved   # int
stats.requests       # int
stats.cogons_stored  # int
```

## `@agent` Decorator

Define agentes especializados com estado próprio:

```python
from leet import agent, AgentContext

@agent(name="resumidor", specialty="summarization")
async def resumidor(ctx: AgentContext) -> str:
    """Resume documentos longos."""
    return await ctx.complete(f"Resuma: {ctx.input}")

@agent(name="analista", specialty="error-analysis")
async def analista(ctx: AgentContext) -> str:
    """Analisa erros e sugere correções."""
    return await ctx.complete(f"Analise o erro: {ctx.input}")

# Criar rede
network = client.agents(resumidor, analista)
```

`AgentContext` expõe:
- `ctx.input` — texto do input
- `ctx.cogon` — COGON atual
- `ctx.context` — COGONs de contexto
- `ctx.complete(prompt)` — chama o LLM provider

## `AgentNetwork`

Rede de agentes colaborativos — distribui COGONs entre agentes registrados.

```python
from leet import AgentNetwork

network = AgentNetwork(vm=vm, provider=provider, agent_id="equipe")
network.add(resumidor)
network.add(analista)

response = await network.chat("qual o problema?")
```

## Providers Suportados

| Provider | Argumento | Variável de API Key |
|----------|-----------|---------------------|
| Anthropic | `"anthropic"` | `ANTHROPIC_API_KEY` |
| OpenAI | `"openai"` | `OPENAI_API_KEY` |
| DeepSeek | `"deepseek"` | `DEEPSEEK_API_KEY` |
| Google Gemini | `"gemini"` | `GEMINI_API_KEY` |
| Ollama | `"ollama"` | — (sem key) |
| Mock | `"mock"` | — (sem key, para testes) |

## Response

```python
@dataclass
class Response:
    text:         str
    cogon:        Cogon
    tokens_saved: int
    model:        str
    provider:     str
    session_id:   str
```

## Testes

```bash
cd leet-py
python -m pytest        # 12 testes: client, network, providers
```

Todos os testes usam o provider `mock` — sem chamadas de rede.
