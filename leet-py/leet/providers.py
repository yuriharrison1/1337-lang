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
        "base_url": "https://api.deepseek.com",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "gemini": {
        "lib":     "openai",
        "model":   "gemini-2.0-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
    },
    "ollama": {
        "lib":     "openai",
        "model":   "llama3",
        "base_url": "http://localhost:11434/v1",
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
            "env_key": None,
        })
        self.provider = provider
        self.model    = model or preset.get("model", "gpt-4o-mini")
        self.base_url = base_url or preset.get("base_url")
        self.lib      = preset.get("lib", "openai")
        env_key       = preset.get("env_key")
        self.api_key  = api_key or (os.getenv(env_key) if env_key else "ollama")
        self._client  = None

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
        Context arrives as DELTA — only what changed is included.
        """
        messages = []

        if context_cogons:
            ctx_parts = []
            for c in context_cogons[:3]:
                from leet_vm.runtime.surface import SurfaceC4
                surface = SurfaceC4()
                ctx_parts.append(surface.reconstruct(c, depth=2))
            ctx_summary = "Context: " + " | ".join(ctx_parts)
            messages.append({"role": "system", "content": ctx_summary})

        messages.append({"role": "user", "content": query_text})
        return messages

    async def complete(self, context_cogons: list, query_cogon: Cogon,
                       query_text: str) -> tuple[str, int]:
        """Returns (response_text, estimated_tokens_used)."""
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
            text   = resp.content[0].text
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
                max_tokens=1024, stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
