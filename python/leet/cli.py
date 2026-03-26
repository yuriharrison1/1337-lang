"""CLI for 1337 — leet command."""

import argparse
import json
import asyncio
import sys
from pathlib import Path

from leet import Cogon, blend, dist, delta, focus, anomaly_score
from leet.types import Msg1337, Receiver, Surface, CanonicalSpace, Intent
from leet.axes import CANONICAL_AXES, AxisGroup, axes_in_group
from leet.validate import validate


def cmd_zero(args):
    """Print COGON_ZERO."""
    zero = Cogon.zero()
    print(zero.to_json())


def cmd_version(args):
    """Print version."""
    from leet import __version__
    print(f"1337 v{__version__}")


def cmd_axes(args):
    """List canonical axes."""
    if args.group:
        group_map = {
            "A": AxisGroup.ONTOLOGICAL,
            "B": AxisGroup.EPISTEMIC,
            "C": AxisGroup.PRAGMATIC,
        }
        axes = axes_in_group(group_map[args.group])
    else:
        axes = CANONICAL_AXES
    
    for ax in axes:
        print(f"[{ax.index:2d}] {ax.code:3} {ax.name:25} ({ax.group.value})")


async def cmd_encode_async(args):
    """Encode text → COGON JSON."""
    from leet.bridge import MockProjector, AnthropicProjector, encode
    
    if args.projector == "anthropic":
        try:
            projector = AnthropicProjector()
        except (ValueError, ImportError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        projector = MockProjector()
    
    cogon = await encode(args.text, projector)
    print(cogon.to_json())


def cmd_encode(args):
    asyncio.run(cmd_encode_async(args))


async def cmd_decode_async(args):
    """Decode COGON JSON → text."""
    from leet.bridge import MockProjector, AnthropicProjector, decode
    
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    cogon = Cogon.from_json(path.read_text())
    
    if args.projector == "anthropic":
        try:
            projector = AnthropicProjector()
        except (ValueError, ImportError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        projector = MockProjector()
    
    text = await decode(cogon, projector)
    print(text)


def cmd_decode(args):
    asyncio.run(cmd_decode_async(args))


def cmd_validate(args):
    """Validate MSG_1337 JSON."""
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        msg = Msg1337.from_json(path.read_text())
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    
    result = validate(msg)
    if result is None:
        print("✓ Valid MSG_1337")
    else:
        print(f"✗ Validation error: {result}")
        sys.exit(1)


def cmd_blend_cli(args):
    """BLEND two COGONs."""
    p1 = Path(args.c1)
    p2 = Path(args.c2)
    
    if not p1.exists():
        print(f"Error: File not found: {args.c1}", file=sys.stderr)
        sys.exit(1)
    if not p2.exists():
        print(f"Error: File not found: {args.c2}", file=sys.stderr)
        sys.exit(1)
    
    c1 = Cogon.from_json(p1.read_text())
    c2 = Cogon.from_json(p2.read_text())
    
    result = blend(c1, c2, args.alpha)
    print(result.to_json())


def cmd_dist_cli(args):
    """DIST between two COGONs."""
    p1 = Path(args.c1)
    p2 = Path(args.c2)
    
    if not p1.exists():
        print(f"Error: File not found: {args.c1}", file=sys.stderr)
        sys.exit(1)
    if not p2.exists():
        print(f"Error: File not found: {args.c2}", file=sys.stderr)
        sys.exit(1)
    
    c1 = Cogon.from_json(p1.read_text())
    c2 = Cogon.from_json(p2.read_text())
    
    d = dist(c1, c2)
    print(f"{d:.4f}")


def main():
    parser = argparse.ArgumentParser(prog="leet", description="1337 Language CLI")
    sub = parser.add_subparsers(dest="command")

    # leet zero
    sub.add_parser("zero", help="Print COGON_ZERO (I AM)")

    # leet version
    sub.add_parser("version", help="Print version")

    # leet encode "texto"
    enc = sub.add_parser("encode", help="Encode text → COGON JSON")
    enc.add_argument("text", help="Text to encode")
    enc.add_argument("--projector", choices=["mock", "anthropic"], default="mock")

    # leet decode cogon.json
    dec = sub.add_parser("decode", help="Decode COGON JSON → text")
    dec.add_argument("file", help="Path to COGON JSON file")
    dec.add_argument("--projector", choices=["mock", "anthropic"], default="mock")

    # leet validate msg.json
    val = sub.add_parser("validate", help="Validate MSG_1337 JSON")
    val.add_argument("file", help="Path to MSG_1337 JSON file")

    # leet blend c1.json c2.json --alpha 0.5
    bl = sub.add_parser("blend", help="BLEND two COGONs")
    bl.add_argument("c1", help="Path to COGON 1 JSON")
    bl.add_argument("c2", help="Path to COGON 2 JSON")
    bl.add_argument("--alpha", type=float, default=0.5)

    # leet dist c1.json c2.json
    di = sub.add_parser("dist", help="DIST between two COGONs")
    di.add_argument("c1", help="Path to COGON 1 JSON")
    di.add_argument("c2", help="Path to COGON 2 JSON")

    # leet axes [--group A|B|C]
    ax = sub.add_parser("axes", help="List canonical axes")
    ax.add_argument("--group", choices=["A", "B", "C"], help="Filter by group")

    args = parser.parse_args()

    if args.command == "zero":
        cmd_zero(args)
    elif args.command == "version":
        cmd_version(args)
    elif args.command == "axes":
        cmd_axes(args)
    elif args.command == "encode":
        cmd_encode(args)
    elif args.command == "decode":
        cmd_decode(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "blend":
        cmd_blend_cli(args)
    elif args.command == "dist":
        cmd_dist_cli(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
