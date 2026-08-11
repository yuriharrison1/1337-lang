# leet-py — Public SDK

Public Python SDK for integrating any application with the 1337 protocol. High-level interface on top of `leet-vm`.

## Installation

```bash
pip install -e leet-py/
```

## Quick Start

```python
import leet

# Connect to an LLM provider
client = leet.connect("anthropic")

# Chat with automatic semantic memory
response = await client.chat("qual é o status do deploy?")
print(response.text)
print(f"Tokens saved: {response.tokens_saved}")
```

## `leet.connect()`

Single entry point. Returns a `LeetClient` ready to use.

```python
client = leet.connect(
    provider="anthropic",   # "anthropic" | "openai" | "deepseek" | "gemini" | "ollama" | "mock"
    model=None,             # specific model (None = provider default)
    base_url=None,          # custom base URL (e.g. OpenAI-compatible APIs)
    api_key=None,           # API key (None = reads from LEET_API_KEY or the provider's variable)
    service="auto",         # "auto" | gRPC URL | "local"
    store="auto",           # "auto" | Redis URL | "memory"
    agent_id="default",     # agent identifier
)
```

### Connection Examples

```python
leet.connect("anthropic")                                        # Claude via Anthropic
leet.connect("openai")                                           # GPT via OpenAI
leet.connect("deepseek")                                         # DeepSeek
leet.connect("gemini")                                           # Google Gemini
leet.connect("ollama", model="llama3")                           # local Ollama
leet.connect("openai", base_url="https://api.deepseek.com", model="deepseek-chat")
leet.connect("anthropic", service="localhost:50051")             # with leet-service
leet.connect("anthropic", store="redis://localhost:6379")        # Redis as store
```

## `LeetClient`

### `.chat(text)` → `Response`

Sends a message. Memory, semantic context, and compression are automatic.

```python
response = await client.chat("preciso de ajuda com o deploy")

response.text          # str — LLM response
response.cogon         # Cogon — semantic state of the response
response.tokens_saved  # int — estimated tokens saved
response.model         # str — model used
response.provider      # str — provider used
response.session_id    # str — current session UUID
```

### `.chat_stream(text)` → `AsyncIterator[str]`

Streaming version. Returns tokens as they arrive.

```python
async for token in client.chat_stream("explique o erro"):
    print(token, end="", flush=True)
```

### `.recall(query, k=5)` → `list[dict]`

Semantic search over the agent's memory.

```python
results = await client.recall("status do servidor", k=3)
for r in results:
    print(r["text"], r["dist"], r["stamp"])
```

### `.remember(text)` → `None`

Explicitly adds to the `PersonalStore`.

```python
await client.remember("deploy da versão 1.2 feito em 14/01")
```

### `.encode(text)` → `Cogon`

Projects text into COGON without generating a response.

```python
cogon = await client.encode("sistema instável")
```

### `.decode(cogon)` → `str`

Reconstructs text from a COGON.

```python
text = await client.decode(cogon)
```

### `.agents(*agent_fns)` → `AgentNetwork`

Creates a network of specialized agents.

```python
network = client.agents(resumidor, analista, executor)
response = await network.chat("analise este log de erro")
```

### `.new_session()`

Starts a new session (resets the incremental DELTA).

```python
client.new_session()
```

### `.stats`

Accumulated session statistics.

```python
stats = client.stats
stats.tokens_used    # int
stats.tokens_saved   # int
stats.requests       # int
stats.cogons_stored  # int
```

## `@agent` Decorator

Defines specialized agents with their own state:

```python
from leet import agent, AgentContext

@agent(name="resumidor", specialty="summarization")
async def resumidor(ctx: AgentContext) -> str:
    """Summarizes long documents."""
    return await ctx.complete(f"Resuma: {ctx.input}")

@agent(name="analista", specialty="error-analysis")
async def analista(ctx: AgentContext) -> str:
    """Analyzes errors and suggests fixes."""
    return await ctx.complete(f"Analise o erro: {ctx.input}")

# Create the network
network = client.agents(resumidor, analista)
```

`AgentContext` exposes:
- `ctx.input` — input text
- `ctx.cogon` — current COGON
- `ctx.context` — context COGONs
- `ctx.complete(prompt)` — calls the LLM provider

## `AgentNetwork`

Network of collaborating agents — distributes COGONs among registered agents.

```python
from leet import AgentNetwork

network = AgentNetwork(vm=vm, provider=provider, agent_id="equipe")
network.add(resumidor)
network.add(analista)

response = await network.chat("qual o problema?")
```

## Supported Providers

| Provider | Argument | API Key Variable |
|----------|-----------|---------------------|
| Anthropic | `"anthropic"` | `ANTHROPIC_API_KEY` |
| OpenAI | `"openai"` | `OPENAI_API_KEY` |
| DeepSeek | `"deepseek"` | `DEEPSEEK_API_KEY` |
| Google Gemini | `"gemini"` | `GEMINI_API_KEY` |
| Ollama | `"ollama"` | — (no key) |
| Mock | `"mock"` | — (no key, for testing) |

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

## Tests

```bash
cd leet-py
python -m pytest        # 12 tests: client, network, providers
```

All tests use the `mock` provider — no network calls.
