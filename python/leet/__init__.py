"""1337 — Native inter-agent communication language. v0.4 (32 axes)."""

from leet.types import (
    Cogon, Edge, Dag, Msg1337, Raw, RawRole, Intent, 
    Receiver, Surface, CanonicalSpace, EdgeType
)
from leet.operators import blend, delta, dist, focus, anomaly_score, apply_patch
from leet.axes import Axis, AxisGroup, CANONICAL_AXES, axis, axes_in_group
from leet.bridge import SemanticProjector, MockProjector, encode, decode

__version__ = "0.4.0"
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
]
