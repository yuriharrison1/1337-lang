"""Tests for leet.cli module."""

import json
import subprocess
import sys
from pathlib import Path
import tempfile
import pytest

# Tests for CLI require the package to be installed
# These are basic smoke tests


class TestCliZero:
    def test_cli_zero(self):
        """Saída = COGON_ZERO JSON."""
        # Run as module
        result = subprocess.run(
            [sys.executable, "-m", "leet.cli", "zero"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        # If package not installed, skip
        if result.returncode != 0 and "No module named" in result.stderr:
            pytest.skip("Package not installed")
        
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["id"] == "00000000-0000-0000-0000-000000000000"
        assert data["stamp"] == 0

    def test_cli_version(self):
        """Print version."""
        result = subprocess.run(
            [sys.executable, "-m", "leet.cli", "version"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        if result.returncode != 0 and "No module named" in result.stderr:
            pytest.skip("Package not installed")
        
        assert result.returncode == 0
        import leet
        assert leet.__version__ in result.stdout

    def test_cli_axes(self):
        """Lista 32 eixos."""
        result = subprocess.run(
            [sys.executable, "-m", "leet.cli", "axes"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        if result.returncode != 0 and "No module named" in result.stderr:
            pytest.skip("Package not installed")
        
        assert result.returncode == 0
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        assert len(lines) == 32

    def test_cli_axes_group_a(self):
        """Filtra grupo A."""
        result = subprocess.run(
            [sys.executable, "-m", "leet.cli", "axes", "--group", "A"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        if result.returncode != 0 and "No module named" in result.stderr:
            pytest.skip("Package not installed")
        
        assert result.returncode == 0
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        assert len(lines) == 14  # Grupo A tem 14 eixos


class TestCliEncode:
    def test_cli_encode(self):
        """Texto → JSON válido."""
        result = subprocess.run(
            [sys.executable, "-m", "leet.cli", "encode", "teste"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        if result.returncode != 0 and "No module named" in result.stderr:
            pytest.skip("Package not installed")
        
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "sem" in data
        assert "unc" in data
        assert len(data["sem"]) == 32


class TestCliBlend:
    def test_cli_blend(self):
        """BLEND dois COGONs."""
        from leet import Cogon
        
        with tempfile.TemporaryDirectory() as tmpdir:
            c1 = Cogon.new(sem=[1.0] * 32, unc=[0.0] * 32)
            c2 = Cogon.new(sem=[0.0] * 32, unc=[0.0] * 32)
            
            p1 = Path(tmpdir) / "c1.json"
            p2 = Path(tmpdir) / "c2.json"
            p1.write_text(c1.to_json())
            p2.write_text(c2.to_json())
            
            result = subprocess.run(
                [sys.executable, "-m", "leet.cli", "blend", str(p1), str(p2), "--alpha", "0.5"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            if result.returncode != 0 and "No module named" in result.stderr:
                pytest.skip("Package not installed")
            
            assert result.returncode == 0
            data = json.loads(result.stdout)
            # α=0.5 entre 1.0 e 0.0 = 0.5
            assert abs(data["sem"][0] - 0.5) < 0.01
