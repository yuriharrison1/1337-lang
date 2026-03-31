# PROMPT 04 — LEET-PY (SDK Público · LeetClient · Providers · Agents)

Build `leet-py` — the public Python SDK. What end users touch.
One-line setup: `leet.connect("anthropic")`. That's it.

**PREREQUISITES**: PROMPT_01 + PROMPT_02 + PROMPT_03 completed.

**IMPORTANT**: At the end, update CONTRACT.md and Taskwarrior.

---

## STRUCTURE

```
leet-py/
├── pyproject.toml
├── leet_sdk/
│   ├── __init__.py          # re-exports: connect, LeetClient, agent, AgentNetwork
│   ├── connect.py           # leet.connect("anthropic") factory
│   ├── client.py            # LeetClient — main user-facing class
│   ├── stats.py             # Stats dataclass
│   ├── agent.py             # @agent decorator + AgentNetwork
│   └── providers/
│       ├── __init__.py
│       ├── base.py          # BaseProvider ABC
│       ├── anthropic.py     # AnthropicProvider
│       ├── openai.py        # OpenAIProvider
│       ├── deepseek.py      # DeepSeekProvider
│       └── mock.py          # MockProvider (for testing)
├── tests/
│   ├── test_client.py
│   ├── test_providers.py
│   ├── test_agent.py
│   └── test_connect.py
└── examples/
    ├── quickstart.py
    └── multi_agent.py
```

**pyproject.toml:**
```toml
[project]
name = "leet-sdk"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["leet1337>=0.4.0", "leet-vm>=0.1.0"]

[project.optional-dependencies]
anthropic = ["anthropic>=0.40"]
openai = ["openai>=1.0"]
deepseek = ["openai>=1.0"]   # DeepSeek uses OpenAI-compatible API
all = ["anthropic>=0.40", "openai>=1.0"]
dev = ["pytest>=8", "pytest-asyncio"]
```

---

## DETAILED SPECS

### connect.py
```python
def connect(provider: str = "mock", **kwargs) -> 'LeetClient':
    """Factory. One line to get started.
    
    Usage:
        client = leet.connect("anthropic")
        client = leet.connect("openai", model="gpt-4o")
        client = leet.connect("deepseek")
        client = leet.connect("mock")  # no API key needed
        client = leet.connect("custom", base_url="https://my-llm.com/v1", api_key="...")
    
    Kwargs passed through to provider constructor.
    """
```

Provider presets:
- "anthropic" → AnthropicProvider(model="claude-sonnet-4-20250514")
- "openai" → OpenAIProvider(model="gpt-4o")
- "deepseek" → DeepSeekProvider (uses openai lib with base_url="https://api.deepseek.com")
- "mock" → MockProvider (no network, no API key)
- "custom" → requires base_url + api_key

### client.py
```python
class LeetClient:
    """Main user-facing class."""
    
    def __init__(self, provider: BaseProvider, vm: LeetVM): ...
    
    async def chat(self, text: str, **kwargs) -> Response:
        """Send message, get response. Full 1337 pipeline underneath.
        
        Returns Response(text=str, cogon=Cogon, tokens_saved=int, latency_ms=float)
        """
    
    async def recall(self, query: str, k: int = 5) -> list[dict]:
        """Search PersonalStore for semantically similar past interactions."""
    
    async def remember(self, text: str) -> None:
        """Explicitly persist to PersonalStore."""
    
    async def forget(self, query: str) -> int:
        """Remove similar COGONs from PersonalStore. Returns count removed."""
    
    async def encode(self, text: str) -> Cogon:
        """Text → COGON. For advanced use."""
    
    async def decode(self, cogon: Cogon) -> str:
        """COGON → text. For advanced use."""
    
    @property
    def stats(self) -> Stats:
        """Cumulative session stats."""
    
    def reset(self) -> None:
        """Reset session state (not PersonalStore)."""

@dataclass
class Response:
    text: str
    cogon: Cogon
    tokens_saved: int
    latency_ms: float
    intent: str
```

### stats.py
```python
@dataclass
class Stats:
    tokens_sent: int = 0
    tokens_received: int = 0
    tokens_saved: int = 0        # estimate of tokens saved by 1337 compression
    cogons_created: int = 0
    cogons_stored: int = 0       # in PersonalStore
    sessions: int = 0
    avg_latency_ms: float = 0.0
    
    @property
    def compression_ratio(self) -> float:
        """Ratio of tokens saved vs what would have been sent without 1337."""
```

### providers/base.py
```python
class BaseProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, context: list[Cogon] | None = None, **kwargs) -> str:
        """Generate text response given prompt and optional semantic context."""
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def model(self) -> str: ...
```

### providers/anthropic.py
Uses `anthropic` library. Constructs messages with system prompt that includes
1337 context (compressed as COGON descriptions, not raw vectors).
Model default: claude-sonnet-4-20250514. API key from env ANTHROPIC_API_KEY.

### providers/openai.py
Uses `openai` library. Same pattern. Model default: gpt-4o.
API key from env OPENAI_API_KEY.

### providers/deepseek.py
Uses `openai` library with `base_url="https://api.deepseek.com"`.
Model default: deepseek-chat. API key from env DEEPSEEK_API_KEY.

### providers/mock.py
No network. Returns deterministic responses based on input keywords.
For testing and development. Always available.

### agent.py
```python
def agent(name: str = None, personality: list[float] = None):
    """Decorator to create a 1337 native agent.
    
    @agent(name="Catalogador", personality=[0.8, 0.3, ...])  # sem bias
    async def catalogador(cogon: Cogon, context: list[Cogon]) -> Cogon:
        # process and return response cogon
        ...
    """

class AgentNetwork:
    """Multi-agent network with shared semantic bus."""
    
    def __init__(self): ...
    def register(self, agent_fn) -> None: ...
    async def broadcast(self, cogon: Cogon) -> list[Cogon]: ...
    async def send(self, target: str, cogon: Cogon) -> Cogon: ...
    
    @property
    def agents(self) -> list[str]: ...
```

### examples/quickstart.py
```python
import asyncio
import leet_sdk as leet

async def main():
    client = leet.connect("mock")
    resp = await client.chat("explica controle preditivo MPC")
    print(resp.text)
    print(f"tokens economizados: {client.stats.tokens_saved}")

asyncio.run(main())
```

### examples/multi_agent.py
```python
import asyncio
import leet_sdk as leet
from leet_sdk import agent, AgentNetwork

@agent(name="Pesquisador")
async def pesquisador(cogon, context):
    # Research-focused agent
    ...

@agent(name="Analista")
async def analista(cogon, context):
    # Analysis-focused agent
    ...

async def main():
    net = AgentNetwork()
    net.register(pesquisador)
    net.register(analista)
    
    client = leet.connect("mock")
    initial = await client.encode("impacto da IA na educação")
    responses = await net.broadcast(initial)
    
    for r in responses:
        print(await client.decode(r))

asyncio.run(main())
```

---

## TESTS (minimum 20)

- connect("mock") returns functional LeetClient
- connect("anthropic") initializes without error (doesn't call API)
- connect("custom", base_url=...) works
- LeetClient.chat() returns Response with all fields
- LeetClient.recall() returns relevant results
- LeetClient.remember() increases store size
- LeetClient.forget() removes entries
- LeetClient.encode()/decode() roundtrip
- LeetClient.stats accumulates correctly
- LeetClient.reset() clears session but not store
- MockProvider.generate() returns deterministic result
- @agent decorator creates callable agent
- AgentNetwork.register() adds agent
- AgentNetwork.broadcast() returns responses from all agents
- AgentNetwork.send() targets specific agent
- Stats.compression_ratio computed correctly
- Response dataclass has all fields
- Provider name/model properties correct
- Error handling: connect with invalid provider name
- Error handling: chat with empty text

---

## TASKWARRIOR + CONTRACT UPDATE

```bash
task project:1337 +prompt04 status:pending done

sed -i 's/| leet-py (SDK público) | PROMPT_04 | `\[ \]` PENDENTE/| leet-py (SDK público) | PROMPT_04 | `[x]` CONCLUÍDO/' CONTRACT.md
sed -i "s/Última atualização: .*/Última atualização: $(date +%Y-%m-%d)/" CONTRACT.md

git add -A
git commit -m "feat(prompt-04): leet-py SDK — LeetClient, providers, agents

- leet.connect('anthropic') one-liner
- LeetClient: chat, recall, remember, encode, decode, forget
- Providers: Anthropic, OpenAI, DeepSeek, Mock, Custom
- @agent decorator + AgentNetwork for multi-agent
- Stats tracking with compression ratio
- Examples: quickstart.py, multi_agent.py
- CONTRACT.md + Taskwarrior updated"

git push origin main
```

**END OF PROMPT_04**
