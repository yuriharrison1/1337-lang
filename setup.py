#!/usr/bin/env python3
"""
setup.py — Configuração interativa do protocolo 1337.
Lê/salva em .env e opcionalmente atualiza docker-compose.yml.
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
    display_current = dim(f"[{current}]") if current else dim("[vazio]")
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
        raw = input(f"  Escolha (número ou Enter para manter {display_current}): ").strip()
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
    print(red("  Opção inválida, mantendo valor atual."))
    return current

def ask_secret(prompt: str, current: str = "") -> str:
    """Prompt for secret — shows masked current value."""
    masked = ("*" * min(len(current), 8) + current[-4:]) if len(current) > 4 else ("*" * len(current))
    display = dim(f"[{masked}]") if current else dim("[não configurado]")
    full_prompt = f"  {cyan('›')} {prompt} {display}: "
    try:
        val = input(full_prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return current
    return val if val else current

def confirm(prompt: str, default: bool = True) -> bool:
    suffix = dim("S/n") if default else dim("s/N")
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
    header("SERVIÇO 1337  (leet-service)")

    section("Rede")
    env["LEET_PORT"] = ask("Porta gRPC", get(env, "LEET_PORT", "50051"))

    section("Backend de computação")
    env["LEET_BACKEND"] = ask_choice(
        "Backend de projeção vetorial",
        ["simd", "cpu", "mock"],
        get(env, "LEET_BACKEND", "simd"),
    )

    section("Store")
    store_type = ask_choice(
        "Backend de armazenamento",
        ["memory", "redis", "sqlite"],
        "redis" if get(env, "LEET_STORE", "memory").startswith("redis") else
        "sqlite" if get(env, "LEET_STORE", "memory").startswith("sqlite") else "memory",
    )
    if store_type == "memory":
        env["LEET_STORE"] = "memory"
    elif store_type == "redis":
        env["LEET_STORE"] = ask(
            "URL Redis", get(env, "LEET_STORE", "redis://localhost:6379"),
            "ex: redis://localhost:6379"
        )
    else:
        env["LEET_STORE"] = ask(
            "URL SQLite", get(env, "LEET_STORE", "sqlite://./leet.db"),
            "ex: sqlite://./leet.db"
        )

    section("Batch de encoding")
    env["LEET_BATCH_WINDOW"] = ask(
        "Janela de batch (ms)",
        get(env, "LEET_BATCH_WINDOW", "10"),
        "tempo de espera para agrupar chamadas",
    )
    env["LEET_BATCH_MAX"] = ask(
        "Tamanho máximo do batch",
        get(env, "LEET_BATCH_MAX", "64"),
    )

    section("Logging")
    env["RUST_LOG"] = ask_choice(
        "Nível de log (Rust)",
        ["error", "warn", "info", "debug", "trace"],
        get(env, "RUST_LOG", "info"),
    )

    return env


def configure_embedding(env: dict) -> dict:
    header("EMBEDDING  (modelo de projeção semântica)")

    model = ask_choice(
        "Modelo de embedding",
        ["mock", "openai"],
        get(env, "LEET_EMBED_MODEL", "mock"),
    )
    env["LEET_EMBED_MODEL"] = model

    if model == "openai":
        env["LEET_EMBED_URL"] = ask(
            "URL do endpoint OpenAI embeddings",
            get(env, "LEET_EMBED_URL", "https://api.openai.com/v1/embeddings"),
        )
        env["LEET_EMBED_KEY"] = ask_secret(
            "Chave API OpenAI (LEET_EMBED_KEY)",
            get(env, "LEET_EMBED_KEY", ""),
        )

    section("Matriz W")
    w_path = ask(
        "Caminho para arquivo da matriz W",
        get(env, "LEET_W_PATH", ""),
        "deixe vazio para usar inicialização identidade",
    )
    if w_path:
        env["LEET_W_PATH"] = w_path
    elif "LEET_W_PATH" in env:
        del env["LEET_W_PATH"]

    return env


def configure_api_keys(env: dict) -> dict:
    header("CHAVES DE API")

    providers = [
        ("DEEPSEEK_API_KEY",   "DeepSeek",   "sk-..."),
        ("ANTHROPIC_API_KEY",  "Anthropic",  "sk-ant-..."),
        ("OPENAI_API_KEY",     "OpenAI",     "sk-..."),
        ("GEMINI_API_KEY",     "Google Gemini", "AIza..."),
        ("MOONSHOT_API_KEY",   "Moonshot/Kimi", "sk-..."),
    ]

    for key, name, hint in providers:
        current = get(env, key, "")
        status = green("✓ configurado") if current else yellow("não configurado")
        print(f"\n  {bold(name)}  {status}")
        if current or confirm(f"Configurar {name}?", default=not bool(current)):
            val = ask_secret(f"Chave {name}", current)
            if val:
                env[key] = val
            elif key in env:
                if confirm(f"Remover chave {name}?", default=False):
                    del env[key]

    return env


def configure_python_sdk(env: dict) -> dict:
    header("PYTHON SDK  (leet-py / python/leet)")

    section("Conexão com o serviço")
    env["LEET_SERVER_HOST"] = ask(
        "Host do serviço", get(env, "LEET_SERVER_HOST", "localhost")
    )
    env["LEET_SERVER_PORT"] = ask(
        "Porta do serviço", get(env, "LEET_SERVER_PORT", "50051")
    )
    env["LEET_SERVER_TIMEOUT"] = ask(
        "Timeout (segundos)", get(env, "LEET_SERVER_TIMEOUT", "30.0")
    )

    section("Cache")
    env["LEET_CACHE_BACKEND"] = ask_choice(
        "Backend de cache do SDK",
        ["memory", "redis", "sqlite"],
        get(env, "LEET_CACHE_BACKEND", "memory"),
    )
    env["LEET_CACHE_TTL_SECONDS"] = ask(
        "TTL do cache (segundos)", get(env, "LEET_CACHE_TTL_SECONDS", "3600")
    )

    section("Projeção semântica")
    env["LEET_PROJECTION_BACKEND"] = ask_choice(
        "Backend de projeção",
        ["mock", "anthropic", "openai", "grpc"],
        get(env, "LEET_PROJECTION_BACKEND", "mock"),
    )

    section("Debug")
    debug_val = ask_choice(
        "Modo debug",
        ["false", "true"],
        get(env, "LEET_DEBUG", "false"),
    )
    env["LEET_DEBUG"] = debug_val

    env["LEET_LOG_LEVEL"] = ask_choice(
        "Nível de log Python",
        ["DEBUG", "INFO", "WARNING", "ERROR"],
        get(env, "LEET_LOG_LEVEL", "INFO"),
    )

    return env


def configure_experiment(env: dict) -> dict:
    header("EXPERIMENTO DE COMPARAÇÃO  (comparison_1337_vs_english.py)")

    section("Parâmetros do experimento")
    env["LEET_EXP_ROUNDS"] = ask(
        "Número de rounds", get(env, "LEET_EXP_ROUNDS", "25")
    )
    env["LEET_EXP_TOPIC"] = ask(
        "Tópico de discussão", get(env, "LEET_EXP_TOPIC", "Eros (Amor)")
    )
    env["LEET_EXP_THRESHOLD"] = ask(
        "Threshold delta semântico", get(env, "LEET_EXP_THRESHOLD", "0.01"),
        "eixos com |Δ| acima disso entram no SparseDelta",
    )
    env["LEET_EXP_WORKERS"] = ask(
        "Workers paralelos (DeepSeek)", get(env, "LEET_EXP_WORKERS", "5")
    )

    env["LEET_EXP_REPORT_DIR"] = ask(
        "Diretório de relatórios", get(env, "LEET_EXP_REPORT_DIR", "./comparison_reports")
    )

    return env


def configure_docker(env: dict) -> dict:
    header("DOCKER  (docker-compose.yml)")

    compose_path = Path("docker-compose.yml")
    if not compose_path.exists():
        warn("docker-compose.yml não encontrado, pulando.")
        return env

    print(f"\n  Arquivo: {dim(str(compose_path.resolve()))}")

    if not confirm("Atualizar docker-compose.yml com as configurações atuais?", default=False):
        return env

    # Backup
    backup = compose_path.with_suffix(".yml.bak")
    shutil.copy(compose_path, backup)
    ok(f"Backup salvo em {backup}")

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
    ok(f"docker-compose.yml atualizado ({updated} variáveis)")

    return env


# ─── Main menu ────────────────────────────────────────────────────────────────

MENU_ITEMS = [
    ("1", "Serviço 1337 (porta, backend, store, batch)"),
    ("2", "Embedding (modelo, URL, chave, matriz W)"),
    ("3", "Chaves de API (DeepSeek, Anthropic, OpenAI, Gemini…)"),
    ("4", "Python SDK (host, cache, projeção, log)"),
    ("5", "Experimento de comparação (rounds, tópico, threshold)"),
    ("6", "Docker (atualizar docker-compose.yml)"),
    ("7", "Mostrar configuração atual"),
    ("s", "Salvar .env e sair"),
    ("q", "Sair sem salvar"),
]


def show_current(env: dict):
    header("CONFIGURAÇÃO ATUAL")
    sections = {
        "Serviço": ["LEET_PORT", "LEET_BACKEND", "LEET_STORE", "LEET_BATCH_WINDOW", "LEET_BATCH_MAX", "RUST_LOG"],
        "Embedding": ["LEET_EMBED_MODEL", "LEET_EMBED_URL", "LEET_W_PATH"],
        "API Keys": ["DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "MOONSHOT_API_KEY"],
        "Python SDK": ["LEET_SERVER_HOST", "LEET_SERVER_PORT", "LEET_CACHE_BACKEND", "LEET_PROJECTION_BACKEND", "LEET_DEBUG", "LEET_LOG_LEVEL"],
        "Experimento": ["LEET_EXP_ROUNDS", "LEET_EXP_TOPIC", "LEET_EXP_THRESHOLD", "LEET_EXP_WORKERS"],
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
    print(bold("  O que deseja configurar?"))
    print()
    for key, label in MENU_ITEMS:
        print(f"    {bold(cyan(key))})  {label}")
    print()


HELP_TEXT = """\
setup.py — Configuração interativa do protocolo 1337
=====================================================

Gera e atualiza o arquivo .env com todas as variáveis necessárias
para rodar o leet-service (Rust), o Python SDK e os experimentos.

USO
  python setup.py           Abre o menu interativo
  python setup.py --help    Exibe esta ajuda
  python setup.py --show    Mostra configuração atual sem entrar no menu

MENU PRINCIPAL
  1  Serviço 1337          Configura o leet-service (gRPC Rust)
                           Vars: LEET_PORT, LEET_BACKEND, LEET_STORE,
                                 LEET_BATCH_WINDOW, LEET_BATCH_MAX, RUST_LOG

  2  Embedding             Configura o modelo de projeção semântica
                           Vars: LEET_EMBED_MODEL, LEET_EMBED_URL,
                                 LEET_EMBED_KEY, LEET_W_PATH

  3  Chaves de API         Configura chaves dos providers LLM
                           Vars: DEEPSEEK_API_KEY, ANTHROPIC_API_KEY,
                                 OPENAI_API_KEY, GEMINI_API_KEY, MOONSHOT_API_KEY

  4  Python SDK            Configura o SDK Python (python/leet e leet-py)
                           Vars: LEET_SERVER_HOST, LEET_SERVER_PORT,
                                 LEET_CACHE_BACKEND, LEET_PROJECTION_BACKEND,
                                 LEET_DEBUG, LEET_LOG_LEVEL

  5  Experimento           Configura defaults do benchmark de comparação
                           Vars: LEET_EXP_ROUNDS, LEET_EXP_TOPIC,
                                 LEET_EXP_THRESHOLD, LEET_EXP_WORKERS,
                                 LEET_EXP_REPORT_DIR

  6  Docker                Atualiza docker-compose.yml com os valores do .env
                           Faz backup automático em docker-compose.yml.bak

  7  Mostrar               Exibe configuração atual (chaves mascaradas)

  s  Salvar e sair         Grava .env preservando comentários e ordem
  q  Sair sem salvar       Descarta alterações não salvas

COMPORTAMENTO DAS PROMPTS
  › Porta gRPC [50051]:    Enter mantém o valor entre colchetes
  › Chave [********af41]:  Chaves secretas sempre mascaradas na tela
  ● 1. simd               Opção marcada com ● é a atual

EXEMPLOS DE USO

  Configuração mínima para rodar o benchmark com DeepSeek:
    python setup.py
    → escolha 3  (Chaves de API)
    → configure DEEPSEEK_API_KEY
    → pressione s  (salvar)
    source .env
    python comparison_1337_vs_english.py --rounds 25 --deepseek

  Configuração completa para produção com Redis:
    python setup.py
    → escolha 1  → LEET_STORE = redis://redis:6379
    → escolha 2  → LEET_EMBED_MODEL = openai + chave
    → escolha 3  → configure todas as chaves necessárias
    → escolha 6  → atualizar docker-compose.yml
    → pressione s
    docker compose up

  Ver configuração atual sem editar:
    python setup.py --show

ARQUIVO .env GERADO
  Formato: CHAVE=valor (uma por linha, # para comentários)
  Localização: mesmo diretório deste script
  Compatível com: source .env | docker compose --env-file .env

DOCUMENTAÇÃO COMPLETA
  Consulte GUIDE.md para referência detalhada de todos os componentes,
  exemplos de uso e descrição de cada variável de ambiente.
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
    print(bold(cyan("  ⚙  CONFIGURAÇÃO DO PROTOCOLO 1337")))
    print(bold(cyan("════════════════════════════════════════════════════════════")))

    env_path = ENV_FILE.resolve()
    if ENV_FILE.exists():
        ok(f".env carregado de {env_path}")
    else:
        info(f".env não encontrado — será criado em {env_path}")

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
        "7": lambda e: (show_current(e), e)[1],
    }

    while True:
        print_menu(env)
        try:
            choice = input(f"  {bold('Opção')}: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            choice = "q"

        if choice in handlers:
            env = handlers[choice](env)
        elif choice == "s":
            save_env(env)
            ok(f".env salvo em {env_path}")
            print()
            print(bold("  Para aplicar ao serviço Rust:"))
            print(dim("    source .env && cargo run --release -p leet-service"))
            print(bold("  Para aplicar com Docker:"))
            print(dim("    docker compose up --env-file .env"))
            print()
            break
        elif choice == "q":
            warn("Saindo sem salvar.")
            break
        else:
            warn("Opção inválida.")


if __name__ == "__main__":
    main()
