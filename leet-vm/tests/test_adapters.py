import json
import pytest
from leet_vm.adapters.text     import TextAdapter
from leet_vm.adapters.json_rpc import JsonRpcAdapter
from leet_vm.adapters.mcp      import McpAdapter
from leet_vm.adapters.rest     import RestAdapter
from leet_vm.adapters.registry import detect_protocol
from leet_vm.types import Cogon

# ── helpers ──────────────────────────────────────────────────────────────────

def _dummy_cogon():
    sem = [0.5] * 32
    unc = [0.3] * 32
    return Cogon(sem=sem, unc=unc, id="test-id")

# ── TextAdapter ───────────────────────────────────────────────────────────────

def test_text_decode_string():
    a = TextAdapter()
    frame = a.decode("hello world")
    assert frame.method is None
    assert frame.params["text"] == "hello world"
    assert frame.corr_id is None

def test_text_decode_bytes():
    a = TextAdapter()
    frame = a.decode(b"hello bytes")
    assert frame.params["text"] == "hello bytes"

def test_text_encode():
    a = TextAdapter()
    out = a.encode(_dummy_cogon())
    assert isinstance(out, bytes)

def test_text_detect():
    a = TextAdapter()
    assert a.detect("plain text") is True
    assert a.detect('{"key":"val"}') is False

# ── JsonRpcAdapter ────────────────────────────────────────────────────────────

def test_jsonrpc_decode_basic():
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "analyze",
        "params": {"x": 1},
        "id": "r1",
    })
    a = JsonRpcAdapter()
    frame = a.decode(payload)
    assert frame.method == "analyze"
    assert frame.params == {"x": 1}
    assert frame.corr_id == "r1"
    assert frame.is_error is False

def test_jsonrpc_decode_list_params():
    payload = {"jsonrpc": "2.0", "method": "foo", "params": ["a", "b"], "id": 2}
    a = JsonRpcAdapter()
    frame = a.decode(payload)
    assert frame.params == {"0": "a", "1": "b"}

def test_jsonrpc_decode_error():
    payload = {"jsonrpc": "2.0", "error": {"code": -32600, "message": "bad"}, "id": "e1"}
    a = JsonRpcAdapter()
    frame = a.decode(payload)
    assert frame.is_error is True
    assert frame.params.get("message") == "bad"

def test_jsonrpc_encode():
    a = JsonRpcAdapter()
    out = a.encode(_dummy_cogon(), corr_id="r1")
    data = json.loads(out)
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "r1"
    assert "result" in data

def test_jsonrpc_detect():
    a = JsonRpcAdapter()
    assert a.detect({"jsonrpc": "2.0", "method": "x"}) is True
    assert a.detect({"type": "tool_use"}) is False

# ── McpAdapter ────────────────────────────────────────────────────────────────

def test_mcp_decode():
    payload = {"type": "tool_use", "name": "search", "input": {"q": "hello"}, "id": "m1"}
    a = McpAdapter()
    frame = a.decode(payload)
    assert frame.method == "search"
    assert frame.params == {"q": "hello"}
    assert frame.corr_id == "m1"

def test_mcp_encode():
    a = McpAdapter()
    out = a.encode(_dummy_cogon(), corr_id="m1")
    data = json.loads(out)
    assert data["type"] == "tool_result"
    assert data["tool_use_id"] == "m1"

def test_mcp_detect():
    a = McpAdapter()
    assert a.detect({"type": "tool_use", "name": "x"}) is True
    assert a.detect({"type": "tool_result"}) is False

# ── RestAdapter ───────────────────────────────────────────────────────────────

def test_rest_decode_with_path():
    payload = {"method": "GET", "path": "/items", "body": {"filter": "all"}}
    a = RestAdapter()
    frame = a.decode(payload)
    assert frame.method == "GET"
    assert frame.params == {"filter": "all"}

def test_rest_decode_unknown():
    payload = {"foo": "bar"}
    a = RestAdapter()
    frame = a.decode(payload)
    assert frame.method == "unknown"
    assert "foo" in frame.params

def test_rest_encode():
    a = RestAdapter()
    out = a.encode(_dummy_cogon())
    data = json.loads(out)
    assert data["status"] == 200
    assert "body" in data

# ── detect_protocol ───────────────────────────────────────────────────────────

def test_detect_jsonrpc():
    assert detect_protocol({"jsonrpc": "2.0", "method": "x"}) == "json-rpc"

def test_detect_mcp():
    assert detect_protocol({"type": "tool_use", "name": "x"}) == "mcp"

def test_detect_rest():
    assert detect_protocol({"path": "/foo"}) == "rest"

def test_detect_text():
    assert detect_protocol("just plain text") == "text"

def test_detect_text_invalid_json():
    assert detect_protocol(b"not json at all") == "text"
