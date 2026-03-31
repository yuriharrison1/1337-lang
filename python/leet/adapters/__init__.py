"""IDE Adapters for 1337 — Integração com ferramentas de coding.

Este módulo fornece adaptadores para integrar o protocolo 1337 com
ferramentas de coding como Claude Code, Codex, Kimi e Aider.

Exemplo:
    >>> from leet.adapters import ClaudeCodeAdapter
    >>> adapter = ClaudeCodeAdapter()
    >>> await adapter.send_message("Analise este código", context={"file": "main.py"})

Os adaptadores convertem automaticamente:
- Texto natural → COGON (vetores semânticos 32D)
- COGON → Comandos da ferramenta IDE
- Respostas da IDE → COGON de volta

Suporte:
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
    """Factory function para criar adaptadores.
    
    Args:
        name: Nome do adaptador ('claude', 'codex', 'kimi', 'aider')
        **kwargs: Argumentos passados para o construtor do adaptador
        
    Returns:
        Instância do adaptador configurado
        
    Raises:
        ValueError: Se o nome do adaptador for inválido
        
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
        raise ValueError(f"Adaptador '{name}' não encontrado. "
                        f"Opções: {list(adapters.keys())}")
    
    return adapters[name_lower](**kwargs)


def list_adapters() -> list[str]:
    """Lista os adaptadores disponíveis."""
    return ['claude', 'codex', 'kimi', 'aider']
