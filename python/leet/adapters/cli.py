#!/usr/bin/env python3
"""Unified CLI for IDE Adapters.

Lets you use any adapter from the command line:

    # Claude Code
    leet-ide claude "Explain this code" --file main.py

    # Codex
    leet-ide codex "Refactor this function" --file utils.py

    # Kimi
    leet-ide kimi "Analyze the project" --project .

    # Aider
    leet-ide aider "Add error handling" --file api.py

Features:
    - Auto-detection of available adapter
    - 1337 integration (COGON projection)
    - Response streaming
    - Session export
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

from . import create_adapter, list_adapters
from .base import AdapterContext, ToolNotFoundError


def detect_project_dir() -> Optional[str]:
    """Detects the current project directory."""
    current = Path.cwd()

    # Look for common markers
    markers = ['.git', 'pyproject.toml', 'package.json', 'Cargo.toml', 'go.mod']

    for path in [current] + list(current.parents):
        for marker in markers:
            if (path / marker).exists():
                return str(path)

    return str(current)


def create_parser() -> argparse.ArgumentParser:
    """Creates the argument parser."""
    parser = argparse.ArgumentParser(
        prog="leet-ide",
        description="1337 IDE Adapters — unified CLI for coding assistants",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use Claude Code
  leet-ide claude "Explain main.py"

  # Use Codex with context
  leet-ide codex "Refactor" --file utils.py --selection "problematic function"

  # Kimi with streaming
  leet-ide kimi "Analyze project" --stream

  # Aider with auto-commit
  leet-ide aider "Fix bug" --auto-commit --file bug.py

  # Auto-detect adapter
  leet-ide auto "Message" --file code.py

  # List available adapters
  leet-ide --list
        """
    )

    parser.add_argument(
        'adapter',
        help='Adapter to use (claude, codex, kimi, aider, auto)'
    )

    parser.add_argument(
        'message',
        nargs='?',
        help='Message for the assistant'
    )

    parser.add_argument(
        '--file', '-f',
        help='Context file'
    )

    parser.add_argument(
        '--project', '-p',
        help='Project directory (auto-detected if omitted)'
    )

    parser.add_argument(
        '--selection', '-s',
        help='Text selected in the editor'
    )

    parser.add_argument(
        '--language', '-l',
        help='Programming language'
    )

    parser.add_argument(
        '--model', '-m',
        help='Specific model'
    )

    parser.add_argument(
        '--stream',
        action='store_true',
        help='Enable response streaming'
    )

    parser.add_argument(
        '--no-cogon',
        action='store_true',
        help='Disable 1337 (COGON) projection'
    )

    parser.add_argument(
        '--export', '-e',
        help='Export session to a JSON file'
    )

    parser.add_argument(
        '--auto-commit',
        action='store_true',
        help='(Aider) Automatic commit'
    )

    parser.add_argument(
        '--approval-mode',
        choices=['full', 'suggest', 'none'],
        default='suggest',
        help='(Codex) Approval mode'
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version='%(prog)s 0.5.0'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List available adapters'
    )

    parser.add_argument(
        '--check',
        action='store_true',
        help='Check adapter availability'
    )

    return parser


def check_adapters():
    """Checks the availability of all adapters."""
    print("Checking adapters...\n")

    for name in list_adapters():
        try:
            adapter = create_adapter(name)
            available = adapter.is_available()
            version = adapter.get_version() or "N/A"

            status = "✅" if available else "❌"
            print(f"{status} {name:10s} {version}")

            if available:
                config = adapter.get_config()
                print(f"   └─ Model: {config.get('model', 'default')}")
        except Exception as e:
            print(f"❌ {name:10s} Error: {e}")


async def run_adapter(
    adapter_name: str,
    message: str,
    args: argparse.Namespace
) -> int:
    """Runs an adapter with a message.

    Returns:
        Exit code
    """
    project_dir = args.project or detect_project_dir()

    # Adapter-specific settings
    adapter_kwargs = {
        'project_dir': project_dir,
        'auto_project': not args.no_cogon,
    }

    if args.model:
        adapter_kwargs['model'] = args.model

    if adapter_name == 'aider':
        adapter_kwargs['auto_commit'] = args.auto_commit
    elif adapter_name == 'codex':
        adapter_kwargs['approval_mode'] = args.approval_mode

    try:
        adapter = create_adapter(adapter_name, **adapter_kwargs)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not adapter.is_available():
        print(
            f"❌ {adapter_name} is not installed or configured.",
            file=sys.stderr
        )
        print(f"   See: https://docs.1337.dev/adapters/{adapter_name}", file=sys.stderr)
        return 1

    # Create context
    context = AdapterContext(
        file_path=args.file,
        project_dir=project_dir,
        selection=args.selection,
        language=args.language,
    )

    print(f"🚀 {adapter_name}: {message[:60]}...")
    print(f"   Project: {project_dir}")
    if args.file:
        print(f"   File: {args.file}")
    print()

    try:
        if args.stream:
            # Streaming
            print("─" * 60)
            async for chunk in adapter.stream_message(message, context):
                print(chunk, end='', flush=True)
            print("\n" + "─" * 60)
        else:
            # Normal
            response = await adapter.send_message(message, context)

            print("─" * 60)
            print(response.text)
            print("─" * 60)

            if response.files_modified:
                print(f"\n📁 Modified files:")
                for f in response.files_modified:
                    print(f"   • {f}")

            if response.cogon:
                # Show dominant axes
                top_indices = sorted(
                    range(32),
                    key=lambda i: response.cogon.sem[i],
                    reverse=True
                )[:5]
                print(f"\n🧠 Dominant semantic axes:")
                from leet.axes import CANONICAL_AXES
                for idx in top_indices:
                    axis = CANONICAL_AXES[idx]
                    val = response.cogon.sem[idx]
                    print(f"   {axis.code}: {axis.name:20s} = {val:.2f}")

        # Export session if requested
        if args.export:
            session_data = {
                'adapter': adapter_name,
                'project_dir': project_dir,
                'message': message,
                'history': [r.to_dict() for r in adapter._history],
            }
            with open(args.export, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
            print(f"\n💾 Session exported: {args.export}")

        return 0

    except ToolNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


async def main_async() -> int:
    """Async entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Special flags
    if args.list:
        print("Available adapters:")
        for name in list_adapters():
            print(f"  • {name}")
        return 0

    if args.check:
        check_adapters()
        return 0

    if not args.message:
        parser.print_help()
        return 1

    adapter_name = args.adapter.lower()

    # Auto-detect
    if adapter_name == 'auto':
        for name in list_adapters():
            try:
                adapter = create_adapter(name)
                if adapter.is_available():
                    adapter_name = name
                    print(f"Auto-detected: {name}\n")
                    break
            except:
                continue
        else:
            print("No adapter found.", file=sys.stderr)
            return 1

    return await run_adapter(adapter_name, args.message, args)


def main() -> int:
    """Entry point."""
    return asyncio.run(main_async())


if __name__ == '__main__':
    sys.exit(main())
