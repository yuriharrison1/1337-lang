#!/usr/bin/env python3
"""
setup.py — Interactive configuration for the 1337 protocol.
Reads/writes .env and optionally updates docker-compose.yml.
"""

import os
import sys
import re
import shutil
from pathlib import Path

# ─── ANSI ────────────────────────────────────────────────────────────────────

NO_COLOR = not sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return text if NO_COLOR else f"\033[{code}m{text}\033[0m"

def bold(t):    return _c("1", t)
def dim(t):     return _c("2", t)
def cyan(t):    return _c("96", t)
def green(t):   return _c("92", t)
def yellow(t):  return _c("93", t)
def red(t):     return _c("91", t)
def magenta(t): return _c("95", t)

# ─── .env helpers ─────────────────────────────────────────────────────────────

ENV_FILE = Path(".env")

def load_env() -> dict:
    """Load .env file into dict (does NOT override current process env)."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env

def save_env(env: dict):
    """Write dict back to .env, preserving order and existing comments."""
    lines = []
    written = set()

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                lines.append(line)
                continue
            if "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                if k in env:
                    lines.append(f"{k}={env[k]}")
                    written.add(k)
                else:
                    lines.append(line)

    for k, v in env.items():
        if k not in written:
            lines.append(f"{k}={v}")

    ENV_FILE.write_text("\n".join(lines) + "\n")

def get(env: dict, key: str, default: str = "") -> str:
    """Return value from env dict, falling back to os.environ, then default."""
    return env.get(key) or os.environ.get(key, default)

# ─── Input helpers ────────────────────────────────────────────────────────────

def ask(prompt: str, current: str = "", hint: str = "") -> str:
    """Single-line prompt. Enter keeps current value."""
    display_current = dim(f"[{current}]") if current else dim("[empty]")
    hint_str = f"  {dim(hint)}" if hint else ""
    full_prompt = f"  {cyan('›')} {prompt} {display_current}{hint_str}: "
    try:
        val = input(full_prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return current
    return val if val else current

def ask_choice(prompt: str, options: list, current: str = "") -> str:
    """Present numbered options."""
    print(f"  {cyan('›')} {prompt}")
    for i, opt in enumerate(options, 1):
        marker = green("●") if opt == current else dim("○")
        print(f"    {marker} {i}. {opt}")
    display_current = dim(f"[{current}]") if current else ""
    try:
        raw = input(f"  Choose (number or Enter to keep {display_current}): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return current
    if not raw:
        return current
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return options[idx]
    except ValueError:
        if raw in options:
            return raw
    print(red("  Invalid option, keeping current value."))
    return current

def ask_secret(prompt: str, current: str = "") -> str:
    """Prompt for secret — shows masked current value."""
    masked = ("*" * min(len(current), 8) + current[-4:]) if len(current) > 4 else ("*" * len(current))
    display = dim(f"[{masked}]") if current else dim("[not configured]")
    full_prompt = f"  {cyan('›')} {prompt} {display}: "
    try:
        val = input(full_prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return current
    return val if val else current

def confirm(prompt: str, default: bool = True) -> bool:
    suffix = dim("Y/n") if default else dim("y/N")
    try:
        raw = input(f"  {cyan('?')} {prompt} [{suffix}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not raw:
        return default
    return raw in ("s", "sim", "y", "yes")

def header(title: str):
    print()
    w = 60
    print(bold(cyan("─" * w)))
    print(bold(cyan(f"  {title}")))
    print(bold(cyan("─" * w)))

def section(title: str):
    print()
    print(bold(f"  ▸ {title}"))

def ok(msg: str):
    print(green(f"  ✓ {msg}"))

def warn(msg: str):
    print(yellow(f"  ⚠ {msg}"))

def info(msg: str):
    print(dim(f"  · {msg}"))

# ─── Configuration sections ───────────────────────────────────────────────────

def configure_service(env: dict) -> dict:
    header("1337 SERVICE  (leet-service)")

    section("Network")
    env["LEET_PORT"] = ask("gRPC port", get(env, "LEET_PORT", "50051"))

    section("Compute backend")
    env["LEET_BACKEND"] = ask_choice(
        "Vector projection backend",
        ["simd", "cpu", "mock"],
        get(env, "LEET_BACKEND", "simd"),
    )

    section("Store")
    store_type = ask_choice(
        "Storage backend",
        ["memory", "redis", "sqlite"],
        "redis" if get(env, "LEET_STORE", "memory").startswith("redis") else
        "sqlite" if get(env, "LEET_STORE", "memory").startswith("sqlite") else "memory",
    )
    if store_type == "memory":
        env["LEET_STORE"] = "memory"
    elif store_type == "redis":
        env["LEET_STORE"] = ask(
            "Redis URL", get(env, "LEET_STORE", "redis://localhost:6379"),
            "e.g.: redis://localhost:6379"
        )
    else:
        env["LEET_STORE"] = ask(
            "SQLite URL", get(env, "LEET_STORE", "sqlite://./leet.db"),
            "e.g.: sqlite://./leet.db"
        )

    section("Encoding batch")
    env["LEET_BATCH_WINDOW"] = ask(
        "Batch window (ms)",
        get(env, "LEET_BATCH_WINDOW", "10"),
        "wait time to group calls together",
    )
    env["LEET_BATCH_MAX"] = ask(
        "Maximum batch size",
        get(env, "LEET_BATCH_MAX", "64"),
    )

    section("Logging")
    env["RUST_LOG"] = ask_choice(
        "Log level (Rust)",
        ["error", "warn", "info", "debug", "trace"],
        get(env, "RUST_LOG", "info"),
    )

    return env


def configure_embedding(env: dict) -> dict:
    header("EMBEDDING  (semantic projection model)")

    model = ask_choice(
        "Embedding model",
        ["mock", "openai"],
        get(env, "LEET_EMBED_MODEL", "mock"),
    )
    env["LEET_EMBED_MODEL"] = model

    if model == "openai":
        env["LEET_EMBED_URL"] = ask(
            "OpenAI embeddings endpoint URL",
            get(env, "LEET_EMBED_URL", "https://api.openai.com/v1/embeddings"),
        )
        env["LEET_EMBED_KEY"] = ask_secret(
            "OpenAI API key (LEET_EMBED_KEY)",
            get(env, "LEET_EMBED_KEY", ""),
        )

    section("W matrix")
    w_path = ask(
        "Path to W matrix file",
        get(env, "LEET_W_PATH", ""),
        "leave empty to use identity initialization",
    )
    if w_path:
        env["LEET_W_PATH"] = w_path
    elif "LEET_W_PATH" in env:
        del env["LEET_W_PATH"]

    return env


def configure_api_keys(env: dict) -> dict:
    header("API KEYS")

    providers = [
        ("DEEPSEEK_API_KEY",   "DeepSeek",   "sk-..."),
        ("ANTHROPIC_API_KEY",  "Anthropic",  "sk-ant-..."),
        ("OPENAI_API_KEY",     "OpenAI",     "sk-..."),
        ("GEMINI_API_KEY",     "Google Gemini", "AIza..."),
        ("MOONSHOT_API_KEY",   "Moonshot/Kimi", "sk-..."),
    ]

    for key, name, hint in providers:
        current = get(env, key, "")
        status = green("✓ configured") if current else yellow("not configured")
        print(f"\n  {bold(name)}  {status}")
        if current or confirm(f"Configure {name}?", default=not bool(current)):
            val = ask_secret(f"{name} key", current)
            if val:
                env[key] = val
            elif key in env:
                if confirm(f"Remove {name} key?", default=False):
                    del env[key]

    return env


def configure_python_sdk(env: dict) -> dict:
    header("PYTHON SDK  (leet-py / python/leet)")

    section("Service connection")
    env["LEET_SERVER_HOST"] = ask(
        "Service host", get(env, "LEET_SERVER_HOST", "localhost")
    )
    env["LEET_SERVER_PORT"] = ask(
        "Service port", get(env, "LEET_SERVER_PORT", "50051")
    )
    env["LEET_SERVER_TIMEOUT"] = ask(
        "Timeout (seconds)", get(env, "LEET_SERVER_TIMEOUT", "30.0")
    )

    section("Cache")
    env["LEET_CACHE_BACKEND"] = ask_choice(
        "SDK cache backend",
        ["memory", "redis", "sqlite"],
        get(env, "LEET_CACHE_BACKEND", "memory"),
    )
    env["LEET_CACHE_TTL_SECONDS"] = ask(
        "Cache TTL (seconds)", get(env, "LEET_CACHE_TTL_SECONDS", "3600")
    )

    section("Semantic projection")
    env["LEET_PROJECTION_BACKEND"] = ask_choice(
        "Projection backend",
        ["mock", "anthropic", "openai", "grpc"],
        get(env, "LEET_PROJECTION_BACKEND", "mock"),
    )

    section("Debug")
    debug_val = ask_choice(
        "Debug mode",
        ["false", "true"],
        get(env, "LEET_DEBUG", "false"),
    )
    env["LEET_DEBUG"] = debug_val

    env["LEET_LOG_LEVEL"] = ask_choice(
        "Python log level",
        ["DEBUG", "INFO", "WARNING", "ERROR"],
        get(env, "LEET_LOG_LEVEL", "INFO"),
    )

    return env


def configure_experiment(env: dict) -> dict:
    header("COMPARISON EXPERIMENT  (comparison_1337_vs_english.py)")

    section("Experiment parameters")
    env["LEET_EXP_ROUNDS"] = ask(
        "Number of rounds", get(env, "LEET_EXP_ROUNDS", "25")
    )
    env["LEET_EXP_TOPIC"] = ask(
        "Discussion topic", get(env, "LEET_EXP_TOPIC", "Eros (Amor)")
    )
    env["LEET_EXP_THRESHOLD"] = ask(
        "Semantic delta threshold", get(env, "LEET_EXP_THRESHOLD", "0.01"),
        "axes with |Δ| above this enter the SparseDelta",
    )
    env["LEET_EXP_WORKERS"] = ask(
        "Parallel workers (DeepSeek)", get(env, "LEET_EXP_WORKERS", "5")
    )

    env["LEET_EXP_REPORT_DIR"] = ask(
        "Reports directory", get(env, "LEET_EXP_REPORT_DIR", "./comparison_reports")
    )

    return env


def configure_claude_code(env: dict) -> dict:
    header("CLAUDE CODE  (leet-mcp + skill)")

    import subprocess

    # ── Check whether cargo is available ────────────────────────────────────────
    if not shutil.which("cargo"):
        warn("cargo not found in PATH. Install Rust before continuing.")
        return env

    # ── Build + install leet-mcp ───────────────────────────────────────────────
    section("Installing leet-mcp")
    info("cargo install --path leet-mcp --bin leet-mcp  (may take a while on first run)")
    result = subprocess.run(
        ["cargo", "install", "--path", "leet-mcp", "--bin", "leet-mcp"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        warn("Failed to install leet-mcp:")
        print(red(result.stderr[-800:] if result.stderr else "(no output)"))
        return env
    ok("leet-mcp installed at ~/.cargo/bin/leet-mcp")

    # ── Build + install leet CLI ───────────────────────────────────────────────
    section("Installing leet CLI")
    result = subprocess.run(
        ["cargo", "install", "--path", "leet-cli", "--bin", "leet"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        warn("Failed to install leet CLI:")
        print(red(result.stderr[-800:] if result.stderr else "(no output)"))
        return env
    ok("leet installed at ~/.cargo/bin/leet")

    # ── leet setup claude-code ─────────────────────────────────────────────────
    section("Configuring Claude Code")
    leet_bin = shutil.which("leet")
    if not leet_bin:
        # try ~/.cargo/bin directly
        candidate = Path.home() / ".cargo" / "bin" / "leet"
        leet_bin = str(candidate) if candidate.exists() else None

    if not leet_bin:
        warn("leet not found in PATH after installation. Add ~/.cargo/bin to your PATH and run:")
        print(dim("    leet setup claude-code"))
        return env

    result = subprocess.run([leet_bin, "setup", "claude-code"], capture_output=True, text=True)
    if result.returncode != 0:
        warn("Failed running 'leet setup claude-code':")
        print(red(result.stderr[-800:] if result.stderr else result.stdout[-800:]))
        return env

    # Show setup output (already compact)
    for line in result.stdout.splitlines():
        print(f"  {line}")

    print()
    info("Restart Claude Code for the MCP server to be loaded.")

    return env


def configure_docker(env: dict) -> dict:
    header("DOCKER  (docker-compose.yml)")

    compose_path = Path("docker-compose.yml")
    if not compose_path.exists():
        warn("docker-compose.yml not found, skipping.")
        return env

    print(f"\n  File: {dim(str(compose_path.resolve()))}")

    if not confirm("Update docker-compose.yml with the current settings?", default=False):
        return env

    # Backup
    backup = compose_path.with_suffix(".yml.bak")
    shutil.copy(compose_path, backup)
    ok(f"Backup saved at {backup}")

    content = compose_path.read_text()

    replacements = {
        "LEET_PORT":         get(env, "LEET_PORT", "50051"),
        "LEET_BACKEND":      get(env, "LEET_BACKEND", "simd"),
        "LEET_STORE":        get(env, "LEET_STORE", "memory"),
        "LEET_BATCH_WINDOW": get(env, "LEET_BATCH_WINDOW", "10"),
        "LEET_BATCH_MAX":    get(env, "LEET_BATCH_MAX", "64"),
        "LEET_EMBED_MODEL":  get(env, "LEET_EMBED_MODEL", "mock"),
        "RUST_LOG":          get(env, "RUST_LOG", "info"),
    }

    updated = 0
    for key, val in replacements.items():
        new_content, n = re.subn(
            rf"(- {re.escape(key)}=)[^\s\n]*",
            rf"\g<1>{val}",
            content,
        )
        if n:
            content = new_content
            updated += n

    compose_path.write_text(content)
    ok(f"docker-compose.yml updated ({updated} variables)")

    return env


# ─── Main menu ────────────────────────────────────────────────────────────────

MENU_ITEMS = [
    ("1", "1337 Service (port, backend, store, batch)"),
    ("2", "Embedding (model, URL, key, W matrix)"),
    ("3", "API Keys (DeepSeek, Anthropic, OpenAI, Gemini…)"),
    ("4", "Python SDK (host, cache, projection, log)"),
    ("5", "Comparison experiment (rounds, topic, threshold)"),
    ("6", "Docker (update docker-compose.yml)"),
    ("7", "Claude Code (install leet-mcp + skill)"),
    ("8", "Show current configuration"),
    ("s", "Save .env and exit"),
    ("q", "Exit without saving"),
]


def show_current(env: dict):
    header("CURRENT CONFIGURATION")
    sections = {
        "Service": ["LEET_PORT", "LEET_BACKEND", "LEET_STORE", "LEET_BATCH_WINDOW", "LEET_BATCH_MAX", "RUST_LOG"],
        "Embedding": ["LEET_EMBED_MODEL", "LEET_EMBED_URL", "LEET_W_PATH"],
        "API Keys": ["DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "MOONSHOT_API_KEY"],
        "Python SDK": ["LEET_SERVER_HOST", "LEET_SERVER_PORT", "LEET_CACHE_BACKEND", "LEET_PROJECTION_BACKEND", "LEET_DEBUG", "LEET_LOG_LEVEL"],
        "Experiment": ["LEET_EXP_ROUNDS", "LEET_EXP_TOPIC", "LEET_EXP_THRESHOLD", "LEET_EXP_WORKERS"],
    }
    secrets = {"DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "MOONSHOT_API_KEY", "LEET_EMBED_KEY"}

    for sec_name, keys in sections.items():
        print(f"\n  {bold(sec_name)}")
        for k in keys:
            v = get(env, k, "")
            if not v:
                print(f"    {dim(k):35s} {dim('—')}")
            elif k in secrets:
                masked = "*" * min(len(v), 8) + v[-4:] if len(v) > 4 else "*" * len(v)
                print(f"    {cyan(k):35s} {dim(masked)}")
            else:
                print(f"    {cyan(k):35s} {green(v)}")


def print_menu(env: dict):
    print()
    print(bold("  What would you like to configure?"))
    print()
    for key, label in MENU_ITEMS:
        print(f"    {bold(cyan(key))})  {label}")
    print()


HELP_TEXT = """\
setup.py — Interactive configuration for the 1337 protocol
============================================================

Generates and updates the .env file with all the variables needed
to run leet-service (Rust), the Python SDK, and the experiments.

USAGE
  python setup.py           Opens the interactive menu
  python setup.py --help    Shows this help
  python setup.py --show    Shows current configuration without entering the menu

MAIN MENU
  1  1337 Service          Configures leet-service (gRPC Rust)
                           Vars: LEET_PORT, LEET_BACKEND, LEET_STORE,
                                 LEET_BATCH_WINDOW, LEET_BATCH_MAX, RUST_LOG

  2  Embedding             Configures the semantic projection model
                           Vars: LEET_EMBED_MODEL, LEET_EMBED_URL,
                                 LEET_EMBED_KEY, LEET_W_PATH

  3  API Keys              Configures LLM provider keys
                           Vars: DEEPSEEK_API_KEY, ANTHROPIC_API_KEY,
                                 OPENAI_API_KEY, GEMINI_API_KEY, MOONSHOT_API_KEY

  4  Python SDK            Configures the Python SDK (python/leet and leet-py)
                           Vars: LEET_SERVER_HOST, LEET_SERVER_PORT,
                                 LEET_CACHE_BACKEND, LEET_PROJECTION_BACKEND,
                                 LEET_DEBUG, LEET_LOG_LEVEL

  5  Experiment            Configures defaults for the comparison benchmark
                           Vars: LEET_EXP_ROUNDS, LEET_EXP_TOPIC,
                                 LEET_EXP_THRESHOLD, LEET_EXP_WORKERS,
                                 LEET_EXP_REPORT_DIR

  6  Docker                Updates docker-compose.yml with the .env values
                           Creates an automatic backup at docker-compose.yml.bak

  7  Claude Code           Installs leet-mcp and the 1337 skill in Claude Code
                           Runs: cargo install leet-mcp + leet setup claude-code
                           Per-project state in .leet/store.bin (auto-created)

  8  Show                  Displays current configuration (keys masked)

  s  Save and exit         Writes .env, preserving comments and order
  q  Exit without saving   Discards unsaved changes

PROMPT BEHAVIOR
  › gRPC port [50051]:     Enter keeps the value shown in brackets
  › Key [********af41]:    Secret keys are always masked on screen
  ● 1. simd               The option marked with ● is the current one

USAGE EXAMPLES

  Minimal setup to run the benchmark with DeepSeek:
    python setup.py
    → choose 3  (API Keys)
    → configure DEEPSEEK_API_KEY
    → press s  (save)
    source .env
    python comparison_1337_vs_english.py --rounds 25 --deepseek

  Full production setup with Redis:
    python setup.py
    → choose 1  → LEET_STORE = redis://redis:6379
    → choose 2  → LEET_EMBED_MODEL = openai + key
    → choose 3  → configure all the required keys
    → choose 6  → update docker-compose.yml
    → press s
    docker compose up

  View current configuration without editing:
    python setup.py --show

GENERATED .env FILE
  Format: KEY=value (one per line, # for comments)
  Location: same directory as this script
  Compatible with: source .env | docker compose --env-file .env

FULL DOCUMENTATION
  See GUIDE.md for a detailed reference of all components,
  usage examples, and a description of each environment variable.
"""


def print_help():
    print(HELP_TEXT)


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print_help()
        return

    os.chdir(Path(__file__).parent)

    show_only = "--show" in sys.argv

    print()
    print(bold(cyan("════════════════════════════════════════════════════════════")))
    print(bold(cyan("  ⚙  1337 PROTOCOL CONFIGURATION")))
    print(bold(cyan("════════════════════════════════════════════════════════════")))

    env_path = ENV_FILE.resolve()
    if ENV_FILE.exists():
        ok(f".env loaded from {env_path}")
    else:
        info(f".env not found — it will be created at {env_path}")

    env = load_env()

    if show_only:
        show_current(env)
        return

    handlers = {
        "1": configure_service,
        "2": configure_embedding,
        "3": configure_api_keys,
        "4": configure_python_sdk,
        "5": configure_experiment,
        "6": configure_docker,
        "7": configure_claude_code,
        "8": lambda e: (show_current(e), e)[1],
    }

    while True:
        print_menu(env)
        try:
            choice = input(f"  {bold('Option')}: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            choice = "q"

        if choice in handlers:
            env = handlers[choice](env)
        elif choice == "s":
            save_env(env)
            ok(f".env saved at {env_path}")
            print()
            print(bold("  To apply to the Rust service:"))
            print(dim("    source .env && cargo run --release -p leet-service"))
            print(bold("  To apply with Docker:"))
            print(dim("    docker compose up --env-file .env"))
            print()
            break
        elif choice == "q":
            warn("Exiting without saving.")
            break
        else:
            warn("Invalid option.")


if __name__ == "__main__":
    main()
