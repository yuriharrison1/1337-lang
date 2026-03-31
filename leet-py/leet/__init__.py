import os
from leet.client  import LeetClient
from leet.network import AgentNetwork
from leet.agent   import agent, AgentContext
from leet_vm.types import Cogon


def connect(
    provider:  str,
    model:     str = None,
    base_url:  str = None,
    api_key:   str = None,
    service:   str = "auto",   # "auto" | gRPC URL | "local"
    store:     str = "auto",   # "auto" | Redis URL | "memory"
    agent_id:  str = "default",
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

    store_backend = "memory"
    if store != "auto":
        store_backend = store
    elif os.getenv("LEET_STORE"):
        store_backend = os.getenv("LEET_STORE")

    service_url = "localhost:50051"
    if service not in ("auto", "local"):
        service_url = service

    vm = LeetVM(
        mode=service if service in ("auto", "local") else "service",
        service_url=service_url,
        store_backend=store_backend,
    )

    return LeetClient(
        vm=vm,
        provider=provider_adapter,
        agent_id=agent_id,
    )


__all__ = ["connect", "LeetClient", "AgentNetwork", "agent", "AgentContext", "Cogon"]
