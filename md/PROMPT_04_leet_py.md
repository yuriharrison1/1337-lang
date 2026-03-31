# PROMPT 04 — leet-py

Build the `leet-py` Python package — the public-facing SDK.
This is the ONLY package users install and import. Everything else is internal.
Zero configuration. Zero RAG. Zero history management. One line to connect any provider.

## Package structure

```
leet-py/
├── pyproject.toml
├── leet/
│   ├── __init__.py          ← exports: connect, Agent, Network, Cogon
│   ├── client.py            ← LeetClient (main user interface)
│   ├── network.py           ← AgentNetwork (multi-agent orchestration)
│   ├── agent.py             ← @agent decorator + AgentContext
│   ├── providers.py         ← ProviderAdapter (all LLM providers)
│   ├── response.py          ← Response dataclass
│   └── stats.py             ← Stats tracking
└── tests/
    ├── test_client.py
    ├── test_providers.py
    └── test_network.py
```

## pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "leet"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "leet-vm>=0.1.0",
    "openai>=1.12",
    "anthropic>=0.20",
    "httpx>=0.27",
    "pydantic>=2.5",
    "typing-extensions>=4.9",
]

[project.optional-dependencies]
service = ["grpcio>=1.60"]
dev     = ["pytest>=8", "pytest-asyncio>=0.23"]
```

## leet/__init__.py

```python
from leet.client  import LeetClient
from leet.network import AgentNetwork
from leet.agent   import agent, AgentContext
from leet_vm.types import Cogon

def connect(
    provider:  str,
    model:     str  = None,
    base_url:  str  = None,
    api_key:   str  = None,
    service:   str  = "auto",   # "auto" | gRPC URL | "local"
    store:     str  = "auto",   # "auto" | Redis URL | "memory"
    agent_id:  str  = "default",
) -> LeetClient:
    """
    Single entry point. Returns a ready-to-use LeetClient.

    Examples:
        leet.connect("anthropic")
        leet.connect("openai")
        leet.connect("deepseek")
        leet.connect("gemini")
        leet.connect("ollama", model="llama3")
        leet.connect("openai", base_url="https://api.deepseek.com", model="deepseek-chat")
    """
    from leet.providers import ProviderAdapter
    from leet_vm.vm import LeetVM

    provider_adapter = ProviderAdapter(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
    )

    # resolve store backend
    store_backend = "memory"
    if store != "auto":
        store_backend = store
    # else: check env LEET_STORE
    import os
    if store == "auto" and os.getenv("LEET_STORE"):
        store_backend = os.getenv("LEET_STORE")

    # resolve service URL
    service_url = "localhost:50051"
    if service not in ("auto", "local"):
        service_url = service

    vm = LeetVM(
        mode=service if service in ("auto", "local", "service") else "service",
        service_url=service_url,
        store_backend=store_backend,
    )

    return LeetClient(
        vm=vm,
        provider=provider_adapter,
        agent_id=agent_id,
    )

__all__ = ["connect", "LeetClient", "AgentNetwork", "agent", "AgentContext", "Cogon"]
```

## leet/response.py

```python
from dataclasses import dataclass
from leet_vm.types import Cogon
from typing import Optional

@dataclass
class Response:
    text:         str
    cogon:        Cogon
    tokens_saved: int    = 0
    model:        str    = ""
    provider:     str    = ""
    session_id:   str    = ""
    finish_reason: str   = "stop"

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return f"Response(text={self.text[:60]!r}..., tokens_saved={self.tokens_saved})"
```

## leet/stats.py

```python
from dataclasses import dataclass, field

@dataclass
class Stats:
    tokens_saved:   int = 0
    tokens_used:    int = 0
    cogons_stored:  int = 0
    sessions:       int = 0
    requests:       int = 0

    @property
    def savings_pct(self) -> float:
        total = self.tokens_saved + self.tokens_used
        if total == 0:
            return 0.0
        return round(self.tokens_saved / total * 100, 1)

    def __repr__(self) -> str:
        return (f"Stats(requests={self.requests}, "
                f"tokens_saved={self.tokens_saved} ({self.savings_pct}%), "
                f"cogons={self.cogons_stored})")
```

## leet/providers.py

ProviderAdapter wraps all LLM providers behind a single interface.

```python
import os
from typing import AsyncIterator, Optional
from leet_vm.types import Cogon, DAG

PROVIDER_PRESETS = {
    "anthropic": {
        "lib":     "anthropic",
        "model":   "claude-sonnet-4-6",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "lib":     "openai",
        "model":   "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "deepseek": {
        "lib":     "openai",
        "model":   "deepseek-chat",
        "base_url":"https://api.deepseek.com",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "gemini": {
        "lib":     "openai",
        "model":   "gemini-2.0-flash",
        "base_url":"https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
    },
    "ollama": {
        "lib":     "openai",
        "model":   "llama3",
        "base_url":"http://localhost:11434/v1",
        "env_key": None,
    },
    "mock": {
        "lib":     "mock",
        "model":   "mock-v1",
        "env_key": None,
    },
}

class ProviderAdapter:
    def __init__(self, provider: str, model: str = None,
                 base_url: str = None, api_key: str = None):
        preset = PROVIDER_PRESETS.get(provider, {
            "lib": "openai", "model": model or "gpt-4o-mini",
            "env_key": None
        })
        self.provider  = provider
        self.model     = model or preset.get("model", "gpt-4o-mini")
        self.base_url  = base_url or preset.get("base_url")
        self.lib       = preset.get("lib", "openai")
        env_key        = preset.get("env_key")
        self.api_key   = api_key or (os.getenv(env_key) if env_key else "ollama")
        self._client   = None

    def _get_client(self):
        if self._client:
            return self._client
        if self.lib == "anthropic":
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        elif self.lib == "openai":
            import openai
            kwargs = {"api_key": self.api_key or "dummy"}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        elif self.lib == "mock":
            self._client = "mock"
        return self._client

    def _dag_to_prompt(self, context_cogons: list, query_cogon: Cogon,
                       query_text: str) -> list[dict]:
        """
        Convert COGON context to minimal LLM messages.
        This is the key efficiency point: context arrives as DELTA,
        not full history. Only what changed is included.
        """
        messages = []

        # system message with context summary (compressed)
        if context_cogons:
            ctx_parts = []
            for c in context_cogons[:3]:  # top-3 most relevant
                from leet_vm.runtime.surface import SurfaceC4
                surface = SurfaceC4()
                ctx_parts.append(surface.reconstruct(c, depth=2))
            ctx_summary = "Context: " + " | ".join(ctx_parts)
            messages.append({"role": "system", "content": ctx_summary})

        # user message — just the query text, no history stuffing
        messages.append({"role": "user", "content": query_text})
        return messages

    async def complete(self, context_cogons: list, query_cogon: Cogon,
                       query_text: str) -> tuple[str, int]:
        """Returns (response_text, estimated_tokens_used)"""
        client = self._get_client()
        messages = self._dag_to_prompt(context_cogons, query_cogon, query_text)

        if self.lib == "mock" or client == "mock":
            resp_text = f"[mock response to: {query_text[:50]}]"
            return resp_text, len(query_text) // 4

        if self.lib == "anthropic":
            resp = await client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=messages,
            )
            text = resp.content[0].text
            tokens = resp.usage.input_tokens + resp.usage.output_tokens
            return text, tokens

        else:  # openai-compatible
            resp = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
            )
            text   = resp.choices[0].message.content
            tokens = resp.usage.total_tokens if resp.usage else len(query_text) // 4
            return text, tokens

    async def stream(self, context_cogons: list, query_cogon: Cogon,
                     query_text: str) -> AsyncIterator[str]:
        """Streaming token by token."""
        client = self._get_client()
        messages = self._dag_to_prompt(context_cogons, query_cogon, query_text)

        if self.lib == "mock" or client == "mock":
            for word in f"[mock stream: {query_text[:30]}]".split():
                yield word + " "
            return

        if self.lib == "anthropic":
            async with client.messages.stream(
                model=self.model, max_tokens=1024, messages=messages
            ) as s:
                async for text in s.text_stream:
                    yield text
        else:
            stream = await client.chat.completions.create(
                model=self.model, messages=messages,
                max_tokens=1024, stream=True
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
```

## leet/client.py — the main interface

```python
import time, uuid
from typing import AsyncIterator, Optional
from leet_vm.vm    import LeetVM
from leet_vm.types import Cogon
from leet.providers import ProviderAdapter
from leet.response  import Response
from leet.stats     import Stats

class LeetClient:
    def __init__(self, vm: LeetVM, provider: ProviderAdapter, agent_id: str = "default"):
        self._vm         = vm
        self._provider   = provider
        self._agent_id   = agent_id
        self._session_id = str(uuid.uuid4())
        self._stats      = Stats()
        self._last_stamp = 0

        # register the provider as the default agent in the VM
        self._vm.set_default_agent(self._llm_agent)

    async def _llm_agent(self, cogon: Cogon, context: list) -> Cogon:
        """The bridge between the 1337 runtime and the LLM provider."""
        # extract original text from raw bridge
        query_text = ""
        if cogon.raw and isinstance(cogon.raw.content, dict):
            query_text = str(cogon.raw.content)
        elif cogon.raw and isinstance(cogon.raw.content, str):
            query_text = cogon.raw.content

        resp_text, tokens_used = await self._provider.complete(context, cogon, query_text)
        self._stats.tokens_used += tokens_used

        # project response back to COGON
        proj  = await self._vm._get_projector()
        resp_cogon = await proj.project(resp_text, self._agent_id)
        # store original text in raw for Surface C4
        from leet_vm.types import RawField
        resp_cogon.raw = RawField(type="text/plain", content=resp_text, role="ARTIFACT")
        return resp_cogon

    async def chat(self, text: str) -> Response:
        """
        Send a message. Memory, context, and compression are automatic.
        Returns Response with .text and .tokens_saved.
        """
        result = await self._vm.process(
            input      = text,
            agent_id   = self._agent_id,
            session_id = self._session_id,
            protocol   = "text",
        )
        self._stats.tokens_saved += result.tokens_saved
        self._stats.requests     += 1
        self._stats.cogons_stored = await self._vm._store.count(self._agent_id)
        self._last_stamp = result.cogon.stamp

        return Response(
            text          = result.text,
            cogon         = result.cogon,
            tokens_saved  = result.tokens_saved,
            model         = self._provider.model,
            provider      = self._provider.provider,
            session_id    = self._session_id,
        )

    async def chat_stream(self, text: str) -> AsyncIterator[str]:
        """Streaming version of chat."""
        # project input first
        proj  = await self._vm._get_projector()
        cogon = await proj.project(text, self._agent_id)
        await self._vm._store.add(self._agent_id, cogon, text=text)

        # get context
        context_records = await self._vm._store.recall(self._agent_id, cogon, k=3)
        context_cogons  = [Cogon(sem=r["sem"], unc=r["unc"], id=r["cogon_id"])
                           for r, _ in context_records]

        async for token in self._provider.stream(context_cogons, cogon, text):
            yield token

    def agents(self, *agent_fns) -> "AgentNetwork":
        from leet.network import AgentNetwork
        net = AgentNetwork(vm=self._vm, provider=self._provider,
                           agent_id=self._agent_id)
        for fn in agent_fns:
            net.add(fn)
        return net

    async def recall(self, query: str, k: int = 5) -> list[dict]:
        """Semantic search in PersonalStore. No embedding setup needed."""
        proj   = await self._vm._get_projector()
        cogon  = await proj.project(query, self._agent_id)
        results = await self._vm._store.recall(self._agent_id, cogon, k=k)
        return [{"text": r.get("text",""), "dist": d,
                 "stamp": r["stamp"], "cogon_id": r["cogon_id"]}
                for r, d in results]

    async def remember(self, text: str) -> None:
        """Explicitly add to PersonalStore."""
        proj  = await self._vm._get_projector()
        cogon = await proj.project(text, self._agent_id)
        await self._vm._store.add(self._agent_id, cogon, text=text)
        self._stats.cogons_stored += 1

    async def encode(self, text: str) -> Cogon:
        proj = await self._vm._get_projector()
        return await proj.project(text, self._agent_id)

    async def decode(self, cogon: Cogon) -> str:
        proj = await self._vm._get_projector()
        return await proj.decode(cogon)

    @property
    def stats(self) -> Stats:
        return self._stats

    @property
    def session_id(self) -> str:
        return self._session_id

    def new_session(self) -> None:
        """Start a fresh session (DELTA resets)."""
        self._session_id = str(uuid.uuid4())
        self._last_stamp = 0
```

## leet/agent.py

```python
import functools
from typing import Callable
from leet_vm.types import Cogon
from leet_vm.store.personal import PersonalStore

class AgentContext:
    def __init__(self, agent_id: str, context: list, vm):
        self.agent_id = agent_id
        self.history  = context   # list of Cogon from PersonalStore recall
        self._vm      = vm

    def assert_(self, content) -> Cogon:
        """Build a response COGON from text or dict."""
        from leet_vm.types import RawField
        import asyncio
        proj  = asyncio.get_event_loop().run_until_complete(
            self._vm._get_projector())
        text  = content if isinstance(content, str) else str(content)
        cogon = asyncio.get_event_loop().run_until_complete(
            proj.project(text, self.agent_id))
        cogon.raw = RawField(type="text/plain", content=text, role="ARTIFACT")
        return cogon

def agent(name: str = "", backend: str = "default"):
    """
    Decorator to register a function as a 1337 agent.
    The function receives (cogon: Cogon, ctx: AgentContext) and returns Cogon.

    Usage:
        @agent(name="analisador")
        async def analisador(cogon: Cogon, ctx: AgentContext) -> Cogon:
            ...
            return ctx.assert_("resultado da análise")
    """
    def decorator(fn: Callable) -> Callable:
        fn._leet_agent = True
        fn._leet_name  = name or fn.__name__
        fn._leet_backend = backend

        @functools.wraps(fn)
        async def wrapper(cogon: Cogon, context: list, vm=None) -> Cogon:
            ctx = AgentContext(fn._leet_name, context, vm)
            return await fn(cogon, ctx)

        wrapper._leet_agent   = True
        wrapper._leet_name    = fn._leet_name
        wrapper._leet_backend = backend
        return wrapper
    return decorator
```

## leet/network.py

```python
from typing import Callable
from leet_vm.vm    import LeetVM
from leet_vm.types import Cogon
from leet.providers import ProviderAdapter
from leet.response  import Response

class AgentNetwork:
    def __init__(self, vm: LeetVM, provider: ProviderAdapter, agent_id: str):
        self._vm       = vm
        self._provider = provider
        self._agent_id = agent_id
        self._agents: dict[str, Callable] = {}

    def add(self, fn: Callable) -> "AgentNetwork":
        name = getattr(fn, "_leet_name", fn.__name__)
        # wrap so AgentContext gets the vm
        async def handler(cogon: Cogon, context: list) -> Cogon:
            return await fn(cogon, context, vm=self._vm)
        self._vm.register_agent(name, handler)
        self._agents[name] = fn
        return self

    async def run(self, text: str, to: str = "") -> Response:
        result = await self._vm.process(
            input       = text,
            agent_id    = self._agent_id,
            protocol    = "text",
            target_agent= to,
        )
        return Response(
            text        = result.text,
            cogon       = result.cogon,
            tokens_saved= result.tokens_saved,
        )

    async def inject(self, cogon: Cogon, to: str = "") -> Response:
        result_cogon = await self._vm._router.route(cogon, [], to)
        from leet_vm.runtime.surface import SurfaceC4
        text = SurfaceC4().reconstruct(result_cogon)
        return Response(text=text, cogon=result_cogon)
```

## Tests

**test_client.py**:
1. connect("mock") returns LeetClient.
2. await client.chat("hello") returns Response with non-empty text.
3. await client.chat("follow up") — second call, verify stats.requests == 2.
4. await client.recall("hello", k=3) returns list.
5. await client.remember("important fact") — no error.
6. await client.encode("test") returns Cogon with 32-dim sem.
7. client.stats shows tokens_saved >= 0.

**test_providers.py**:
1. ProviderAdapter("mock") — complete() returns ("mock response...", int).
2. ProviderAdapter("openai", api_key="sk-test", base_url="http://...") — preset resolved.
3. _dag_to_prompt with 2 context cogons returns list of messages.

**test_network.py**:
1. Define a mock @agent, add to AgentNetwork.
2. network.run("test message") returns Response.

## Install and test

```bash
cd leet-py
pip install -e ".[dev]"
python -m pytest tests/ -v

# smoke test
python -c "
import asyncio, leet
async def main():
    c = leet.connect('mock')
    r = await c.chat('hello 1337')
    print(r)
    print(c.stats)
asyncio.run(main())
"
```
