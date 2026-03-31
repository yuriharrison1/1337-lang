"""1337 — Native inter-agent communication language. v0.5.0 (32 axes).

This is the Python SDK for the 1337 protocol, providing:
- Core types: COGON, DAG, MSG_1337
- Semantic operators: BLEND, DIST, DELTA, FOCUS
- Bridge: Text <-> Semantic vectors
- IDE Adapters: Claude Code, Codex, Kimi, Aider
"""

from leet.types import (
    Cogon, Edge, Dag, Msg1337, Raw, RawRole, Intent, 
    Receiver, Surface, CanonicalSpace, EdgeType
)
from leet.operators import blend, delta, dist, focus, anomaly_score, apply_patch
from leet.axes import Axis, AxisGroup, CANONICAL_AXES, axis, axes_in_group
from leet.bridge import SemanticProjector, MockProjector, encode, decode
from leet.context import (
    ContextProfile, ContextManager,
    get_context_manager, set_context_profile, adjust_with_context,
)
from leet.cache import (
    Cache, get_cache, set_cache,
    CacheBackend, MemoryCache, SQLiteCache, RedisCache, MongoCache,
)
from leet.config import LeetConfig, get_config, init_config
from leet.validate import validate, check_confidence

__version__ = "0.5.0"
FIXED_DIMS = 32
MAX_INHERITANCE_DEPTH = 4
LOW_CONFIDENCE_THRESHOLD = 0.9

# Tenta importar backend Rust. Se não disponível, usa pure-python.
try:
    import leet_core as _rust_backend
    BACKEND = "rust"
except ImportError:
    _rust_backend = None
    BACKEND = "python"

# IDE Adapters (lazy import para evitar dependências pesadas)
def _get_adapters():
    """Lazy import de adapters."""
    from leet import adapters
    return adapters

__all__ = [
    # Version
    "__version__",
    "FIXED_DIMS",
    "MAX_INHERITANCE_DEPTH", 
    "LOW_CONFIDENCE_THRESHOLD",
    "BACKEND",
    # Types
    "Cogon",
    "Edge",
    "Dag", 
    "Msg1337",
    "Raw",
    "RawRole",
    "Intent",
    "Receiver",
    "Surface",
    "CanonicalSpace",
    "EdgeType",
    # Operators
    "blend",
    "delta",
    "dist",
    "focus",
    "anomaly_score",
    "apply_patch",
    # Axes
    "Axis",
    "AxisGroup",
    "CANONICAL_AXES",
    "axis",
    "axes_in_group",
    # Bridge
    "SemanticProjector",
    "MockProjector",
    "encode",
    "decode",
    # Adapters namespace
    "adapters",
    # Context
    "ContextProfile",
    "ContextManager", 
    "get_context_manager",
    "set_context_profile",
    "adjust_with_context",
    # Cache
    "Cache",
    "get_cache",
    "set_cache",
    "CacheBackend",
    "MemoryCache",
    "SQLiteCache", 
    "RedisCache",
    "MongoCache",
    # Config
    "LeetConfig",
    "get_config",
    "init_config",
    # Validation
    "validate",
    "check_confidence",
]
