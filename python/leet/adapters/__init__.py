"""IDE Adapters for 1337 — Integration with coding tools.

This module provides adapters to integrate the 1337 protocol with
coding tools such as Claude Code, Codex, Kimi and Aider.

Example:
    >>> from leet.adapters import ClaudeCodeAdapter
    >>> adapter = ClaudeCodeAdapter()
    >>> await adapter.send_message("Analyze this code", context={"file": "main.py"})

The adapters automatically convert:
- Natural text → COGON (32D semantic vectors)
- COGON → IDE tool commands
- IDE responses → COGON, back

Support:
    - Claude Code (Anthropic)
    - Codex (OpenAI)
    - Kimi Code CLI (Moonshot)
    - Aider (multi-LLM)
"""

from .base import BaseIDEAdapter, AdapterContext, AdapterResponse, MessageRole
from .claude_code import ClaudeCodeAdapter
from .codex import CodexAdapter
from .kimi import KimiAdapter
from .aider import AiderAdapter

__version__ = "0.5.0"

__all__ = [
    # Base
    "BaseIDEAdapter",
    "AdapterContext",
    "AdapterResponse",
    "MessageRole",
    # Adapters
    "ClaudeCodeAdapter",
    "CodexAdapter",
    "KimiAdapter",
    "AiderAdapter",
    # Version
    "__version__",
]


def create_adapter(name: str, **kwargs) -> BaseIDEAdapter:
    """Factory function to create adapters.

    Args:
        name: Adapter name ('claude', 'codex', 'kimi', 'aider')
        **kwargs: Arguments passed to the adapter's constructor

    Returns:
        Configured adapter instance

    Raises:
        ValueError: If the adapter name is invalid

    Example:
        >>> adapter = create_adapter('claude', project_dir='/path/to/project')
        >>> adapter = create_adapter('kimi', api_key='sk-...')
    """
    adapters = {
        'claude': ClaudeCodeAdapter,
        'claude-code': ClaudeCodeAdapter,
        'codex': CodexAdapter,
        'kimi': KimiAdapter,
        'kimi-code': KimiAdapter,
        'aider': AiderAdapter,
    }

    name_lower = name.lower()
    if name_lower not in adapters:
        raise ValueError(f"Adapter '{name}' not found. "
                        f"Options: {list(adapters.keys())}")

    return adapters[name_lower](**kwargs)


def list_adapters() -> list[str]:
    """Lists the available adapters."""
    return ['claude', 'codex', 'kimi', 'aider']
