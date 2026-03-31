from dataclasses import dataclass
from leet_vm.types import Cogon
from typing import Optional

@dataclass
class Response:
    text:          str
    cogon:         Cogon
    tokens_saved:  int  = 0
    model:         str  = ""
    provider:      str  = ""
    session_id:    str  = ""
    finish_reason: str  = "stop"

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return f"Response(text={self.text[:60]!r}..., tokens_saved={self.tokens_saved})"
