import json
from typing import Optional
from leet_vm.adapters.base import AdapterFrame

class RestAdapter:
    protocol_id = "rest"

    def decode(self, raw: bytes | str | dict) -> AdapterFrame:
        if isinstance(raw, (bytes, str)):
            try:
                data = json.loads(raw)
            except Exception:
                data = {"text": raw if isinstance(raw, str) else raw.decode()}
        else:
            data = raw

        if isinstance(data, dict) and ("path" in data or "method" in data):
            method = data.get("method") or data.get("path")
            params = data.get("body", {})
            if not isinstance(params, dict):
                params = {"body": params}
            # include query params if present
            if "query" in data:
                params.update(data["query"] if isinstance(data["query"], dict)
                               else {"query": data["query"]})
        else:
            method = "unknown"
            params = data if isinstance(data, dict) else {"data": data}

        return AdapterFrame(
            method=method,
            params=params,
            corr_id=data.get("request_id") if isinstance(data, dict) else None,
            raw_bytes=raw if isinstance(raw, bytes) else None,
        )

    def encode(self, cogon, corr_id: Optional[str] = None) -> bytes:
        body = cogon.to_dict()
        response = {"status": 200, "body": body}
        if corr_id:
            response["request_id"] = corr_id
        return json.dumps(response).encode()

    def detect(self, raw: bytes | str | dict) -> bool:
        if isinstance(raw, (bytes, str)):
            try:
                data = json.loads(raw)
            except Exception:
                return False
        else:
            data = raw
        return isinstance(data, dict) and ("path" in data or "method" in data)
