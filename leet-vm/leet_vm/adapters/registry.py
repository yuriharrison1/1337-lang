import json
from leet_vm.adapters.text     import TextAdapter
from leet_vm.adapters.json_rpc import JsonRpcAdapter
from leet_vm.adapters.mcp      import McpAdapter
from leet_vm.adapters.rest     import RestAdapter

ADAPTERS = {
    "text":     TextAdapter(),
    "json-rpc": JsonRpcAdapter(),
    "mcp":      McpAdapter(),
    "rest":     RestAdapter(),
}

def detect_protocol(raw: bytes | str | dict) -> str:
    """Returns: 'json-rpc' | 'mcp' | 'rest' | 'text'"""
    if isinstance(raw, (bytes, str)):
        try:
            data = json.loads(raw)
        except Exception:
            return "text"
    else:
        data = raw
    if isinstance(data, dict):
        if "jsonrpc" in data:
            return "json-rpc"
        if data.get("type") == "tool_use":
            return "mcp"
        if "path" in data or "method" in data:
            return "rest"
        return "rest"
    return "text"
