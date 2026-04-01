"""
Orchestrator: full calibration pipeline.

Steps:
  1. generate  — Create dataset via scoring (slow if using real LLM)
  2. train     — Ridge regression embedding→sem[32]  (fast, local)
  3. evaluate  — Coherence benchmarks                (fast, local)
  4. export    — Copy W.bin for leet-service

Usage:
    python run_pipeline.py                      # all steps, mock provider
    python run_pipeline.py --step train         # skip generate
    python run_pipeline.py --skip-generate      # same as above
    python run_pipeline.py --config config.yaml --step all
"""

import os
import sys
import subprocess
import time

import click
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: str | None = None) -> int:
    """Run a subprocess, streaming stdout/stderr. Returns exit code."""
    click.echo(f"\n$ {' '.join(cmd)}")
    t0 = time.perf_counter()
    result = subprocess.run(cmd, cwd=cwd)
    elapsed = time.perf_counter() - t0
    click.echo(f"  → exit {result.returncode}  ({elapsed:.1f}s)")
    return result.returncode


def _load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option(
    "--config", default="config.yaml", show_default=True,
    help="Path to config.yaml",
)
@click.option(
    "--step",
    default="all",
    type=click.Choice(["all", "generate", "train", "evaluate", "export"]),
    show_default=True,
    help="Pipeline step to run.",
)
@click.option(
    "--skip-generate", is_flag=True, default=False,
    help="Skip the generate step even when --step all.",
)
@click.option(
    "--provider",
    default=None,
    type=click.Choice(["mock", "openai", "anthropic"]),
    help="Override LLM provider from config (generate step only).",
)
@click.option(
    "--n", default=None, type=int,
    help="Override dataset size from config (generate step only).",
)
def main(config: str, step: str, skip_generate: bool, provider: str | None, n: int | None) -> None:
    """Run the 1337 W-matrix calibration pipeline."""

    # Resolve config relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_abs = os.path.join(script_dir, config) if not os.path.isabs(config) else config

    if not os.path.exists(config_abs):
        click.echo(f"ERROR: config file not found: {config_abs}", err=True)
        sys.exit(1)

    cfg = _load_config(config_abs)
    llm_provider = provider or cfg.get("llm", {}).get("provider", "mock")
    dataset_size = n or cfg.get("dataset", {}).get("size", 100)

    click.echo("=" * 60)
    click.echo("  1337 Calibration Pipeline")
    click.echo(f"  config   : {config_abs}")
    click.echo(f"  step     : {step}")
    click.echo(f"  provider : {llm_provider}")
    click.echo("=" * 60)

    python = sys.executable
    errors: list[str] = []

    def run_step(name: str, cmd: list[str]) -> bool:
        code = _run(cmd, cwd=script_dir)
        if code != 0:
            errors.append(f"{name} failed (exit {code})")
            return False
        return True

    # ── Step 1: generate ────────────────────────────────────────────────
    if step in ("all", "generate") and not skip_generate:
        ok = run_step("generate", [
            python, "generate_dataset.py",
            "--provider", llm_provider,
            "--n", str(dataset_size),
        ])
        if not ok and step == "generate":
            sys.exit(1)

    # ── Step 2: train ────────────────────────────────────────────────────
    if step in ("all", "train"):
        ok = run_step("train", [python, "train_w.py"])
        if not ok and step == "train":
            sys.exit(1)

    # ── Step 3: evaluate ─────────────────────────────────────────────────
    if step in ("all", "evaluate"):
        ok = run_step("evaluate", [python, "evaluate_w.py"])
        if not ok and step == "evaluate":
            sys.exit(1)

    # ── Step 4: export ───────────────────────────────────────────────────
    if step in ("all", "export"):
        service_path = cfg.get("export", {}).get("service_path", "../leet1337/leet-service/W.bin")
        ok = run_step("export", [python, "export_w.py", "--dest", service_path])
        if not ok and step == "export":
            sys.exit(1)

    # ── Summary ──────────────────────────────────────────────────────────
    click.echo("\n" + "=" * 60)
    if errors:
        click.echo(f"  PIPELINE COMPLETED WITH {len(errors)} ERROR(S):")
        for e in errors:
            click.echo(f"    • {e}")
        click.echo("=" * 60)
        sys.exit(1)
    else:
        click.echo("  PIPELINE COMPLETE — all steps succeeded")
        click.echo("=" * 60)


if __name__ == "__main__":
    main()
