import json
from typing import Optional
from leet_vm.adapters.base import AdapterFrame

class McpAdapter:
    protocol_id = "mcp"

    def decode(self, raw: bytes | str | dict) -> AdapterFrame:
        if isinstance(raw, (bytes, str)):
            data = json.loads(raw)
        else:
            data = raw

        method  = data.get("name")
        params  = data.get("input", {})
        corr_id = data.get("id")
        return AdapterFrame(
            method=method,
            params=params if isinstance(params, dict) else {"input": params},
            corr_id=str(corr_id) if corr_id is not None else None,
            raw_bytes=raw if isinstance(raw, bytes) else None,
        )

    def encode(self, cogon, corr_id: Optional[str] = None) -> bytes:
        if cogon.raw and isinstance(cogon.raw.content, str):
            content = cogon.raw.content
        else:
            # brief sem summary as content
            parts = [f"{v:.3f}" for v in cogon.sem[:8]]
            content = " ".join(parts)
        response = {
            "type": "tool_result",
            "tool_use_id": corr_id,
            "content": content,
        }
        return json.dumps(response).encode()

    def detect(self, raw: bytes | str | dict) -> bool:
        if isinstance(raw, (bytes, str)):
            try:
                data = json.loads(raw)
            except Exception:
                return False
        else:
            data = raw
        return isinstance(data, dict) and data.get("type") == "tool_use"
