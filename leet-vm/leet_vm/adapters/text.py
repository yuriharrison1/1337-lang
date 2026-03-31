import json
from typing import Optional
from leet_vm.adapters.base import AdapterFrame

class TextAdapter:
    protocol_id = "text"

    def decode(self, raw: bytes | str | dict) -> AdapterFrame:
        if isinstance(raw, bytes):
            text = raw.decode("utf-8", errors="replace")
        elif isinstance(raw, dict):
            text = json.dumps(raw)
        else:
            text = str(raw)
        return AdapterFrame(
            method=None,
            params={"text": text},
            corr_id=None,
            raw_bytes=raw if isinstance(raw, bytes) else None,
        )

    def encode(self, cogon, corr_id: Optional[str] = None) -> bytes:
        # Surface C4 reconstruction is done in vm.py; here we emit raw sem summary
        if cogon.raw and isinstance(cogon.raw.content, str):
            return cogon.raw.content.encode()
        parts = [f"{v:.3f}" for v in cogon.sem[:8]]
        return (" ".join(parts)).encode()

    def detect(self, raw: bytes | str | dict) -> bool:
        if isinstance(raw, (bytes, str)):
            try:
                json.loads(raw)
                return False
            except Exception:
                return True
        return False
