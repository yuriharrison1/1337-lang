from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

@dataclass
class AdapterFrame:
    method:    Optional[str]         # JSON-RPC method, REST endpoint, etc.
    params:    dict                  # extracted parameters
    corr_id:   Optional[str]         # request ID for round-trip correlation
    is_error:  bool = False
    raw_bytes: Optional[bytes] = None   # original payload preserved

@runtime_checkable
class Adapter(Protocol):
    protocol_id: str

    def decode(self, raw: bytes | str | dict) -> AdapterFrame: ...
    def encode(self, cogon, corr_id: Optional[str] = None) -> bytes: ...
    def detect(self, raw: bytes | str | dict) -> bool: ...
