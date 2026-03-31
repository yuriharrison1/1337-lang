import json
from typing import Optional
from leet_vm.adapters.base import AdapterFrame

class JsonRpcAdapter:
    protocol_id = "json-rpc"

    def decode(self, raw: bytes | str | dict) -> AdapterFrame:
        if isinstance(raw, (bytes, str)):
            data = json.loads(raw)
        else:
            data = raw

        is_error = "error" in data
        if is_error:
            params = data.get("error", {})
            if not isinstance(params, dict):
                params = {"error": params}
        else:
            params = data.get("params", {})
            if isinstance(params, list):
                params = {str(i): v for i, v in enumerate(params)}

        return AdapterFrame(
            method=data.get("method"),
            params=params,
            corr_id=str(data["id"]) if "id" in data else None,
            is_error=is_error,
            raw_bytes=raw if isinstance(raw, bytes) else None,
        )

    def encode(self, cogon, corr_id: Optional[str] = None) -> bytes:
        if cogon.raw and getattr(cogon.raw, "role", None) == "BRIDGE":
            result = cogon.raw.content
        else:
            result = cogon.to_dict()
        response = {"jsonrpc": "2.0", "result": result, "id": corr_id}
        return json.dumps(response).encode()

    def detect(self, raw: bytes | str | dict) -> bool:
        if isinstance(raw, (bytes, str)):
            try:
                data = json.loads(raw)
            except Exception:
                return False
        else:
            data = raw
        return isinstance(data, dict) and "jsonrpc" in data
