#!/usr/bin/env python3
"""MCP server — 1337 semantic encoding tools for Claude Code.

Exposes leet-cli as MCP tools so Claude can compress context to COGON vectors,
check semantic distance before re-sending information, and communicate in the
1337 inter-agent protocol.

Usage (Claude Code picks this up via .claude/settings.json):
  python3 mcp/leet_mcp.py
"""

import re
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "leet-1337",
    description=(
        "1337 semantic encoding. Compress context to 32-axis COGON vectors "
        "to save ~90% tokens when passing state between agents."
    ),
)

_REPO = Path(__file__).resolve().parent.parent
_ANSI = re.compile(r"\x1B\[[0-9;]*[mGKHF]")


def _leet(*args: str, stdin: str | None = None) -> str:
    binary = None
    for candidate in [_REPO / "target/release/leet", _REPO / "target/debug/leet"]:
        if candidate.exists():
            binary = str(candidate)
            break
    if binary is None:
        return (
            "ERROR: leet binary not found. "
            "Run: cargo build --release -p leet-cli"
        )

    try:
        result = subprocess.run(
            [binary, *args],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return "ERROR: leet timed out"

    out = _ANSI.sub("", result.stdout).strip()
    if result.returncode != 0:
        err = _ANSI.sub("", result.stderr).strip()
        return f"ERROR: {err or out}"
    return out


@mcp.tool()
def encode(text: str) -> str:
    """Project text onto the 32-axis COGON space.

    Returns active axes (activation > 0.3) with their values. Use this to:
    - Summarise long context blocks (~90% token reduction)
    - Fingerprint a concept for later comparison via dist()
    - Produce a compact ⟨G8=0.95 P3=0.90⟩ summary token

    Example:
      encode("deploy urgente falhou")
      → G8_URGENCY 0.95 | P3_ANOMALY 0.90 | D1_STATE 0.85 | P7_ACTION 0.80
    """
    return _leet("encode", text)


@mcp.tool()
def dist(text_a: str, text_b: str) -> str:
    """Semantic cosine distance between two texts  [0 = identical · 1 = orthogonal].

    Rule: if dist < 0.05 the receiver already holds this information semantically —
    skip re-sending and save tokens. Show discordant axes to explain the gap.
    """
    return _leet("dist", text_a, text_b)


@mcp.tool()
def blend(text_a: str, text_b: str, alpha: float = 0.5) -> str:
    """Interpolate two semantic contexts.

    alpha=1.0 → all text_a  |  alpha=0.0 → all text_b  |  alpha=0.5 → equal blend.
    Useful for merging viewpoints or gradually shifting semantic focus between turns.
    """
    return _leet("blend", text_a, text_b, "--alpha", str(round(alpha, 3)))


@mcp.tool()
def axes() -> str:
    """Reference: all 32 canonical 1337 axes with code, name, block, description.

    Use when mapping a ⟨…⟩ COGON token back to human meaning, or when choosing
    which axes to activate in a compact summary.
    """
    return _leet("axes")


@mcp.tool()
def inspect(cogon_json: str) -> str:
    """Interpret a COGON JSON — top-10 activated axes with values.

    Pass the raw COGON JSON string (from a MSG_1337 payload) to get a concise
    semantic summary without reloading the original text.
    """
    return _leet("inspect", "-", stdin=cogon_json)


if __name__ == "__main__":
    mcp.run()
