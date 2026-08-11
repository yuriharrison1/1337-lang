#!/usr/bin/env python3
"""
1337 Integration Test - Verifies all components
"""

import sys
import subprocess

def run_test(name, command, cwd=None):
    """Runs a command and returns whether it succeeded."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd
        )
        if result.returncode == 0:
            print(f"✅ {name}")
            return True
        else:
            print(f"❌ {name}: {result.stderr[:100]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️  {name}: timeout")
        return False
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

print("═" * 70)
print("1337 INTEGRATION TEST")
print("═" * 70)

results = []

# ═══════════════════════════════════════════════════════════════════════════════
print("\n📦 1. PYTHON CORE SDK (leet1337)")
# ═══════════════════════════════════════════════════════════════════════════════
results.append(run_test(
    "Core tests (146)",
    "python -m pytest tests/ -q --tb=no",
    "/home/yuri/Projetos/1337/python"
))

# ═══════════════════════════════════════════════════════════════════════════════
print("\n📦 2. LEET-VM (Python VM)")
# ═══════════════════════════════════════════════════════════════════════════════
results.append(run_test(
    "VM tests (42)",
    "python -m pytest tests/ -q --tb=no",
    "/home/yuri/Projetos/1337/leet-vm"
))

# ═══════════════════════════════════════════════════════════════════════════════
print("\n📦 3. LEET-PY (Public SDK)")
# ═══════════════════════════════════════════════════════════════════════════════
results.append(run_test(
    "SDK tests (12)",
    "python -m pytest tests/ -q --tb=no",
    "/home/yuri/Projetos/1337/leet-py"
))

# ═══════════════════════════════════════════════════════════════════════════════
print("\n📦 4. RUST CLI (leet)")
# ═══════════════════════════════════════════════════════════════════════════════
results.append(run_test(
    "CLI version",
    "/home/yuri/Projetos/1337/leet1337/target/debug/leet version"
))

results.append(run_test(
    "CLI axes",
    "/home/yuri/Projetos/1337/leet1337/target/debug/leet axes"
))

# ═══════════════════════════════════════════════════════════════════════════════
print("\n📦 5. RUST SERVICE (leet-service)")
# ═══════════════════════════════════════════════════════════════════════════════
# Check whether the binary exists
import os
service_bin = "/home/yuri/Projetos/1337/leet1337/target/debug/leet-service"
if os.path.exists(service_bin):
    print(f"✅ Binary exists ({os.path.getsize(service_bin) / 1024 / 1024:.1f} MB)")
    results.append(True)
else:
    print("❌ Binary not found")
    results.append(False)

# ═══════════════════════════════════════════════════════════════════════════════
print("\n📦 6. CALIBRATION")
# ═══════════════════════════════════════════════════════════════════════════════
calibration_dir = "/home/yuri/Projetos/1337/calibration"
if os.path.exists(calibration_dir):
    files = ["train_w.py", "generate_dataset.py", "evaluate_w.py"]
    all_exist = all(os.path.exists(f"{calibration_dir}/{f}") for f in files)
    if all_exist:
        print("✅ Calibration scripts present")
        results.append(True)
    else:
        print("❌ Missing calibration scripts")
        results.append(False)
else:
    print("❌ Calibration directory not found")
    results.append(False)

# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 70)
print("SUMMARY")
print("═" * 70)

total = len(results)
passed = sum(results)
failed = total - passed

print(f"\nComponents: {total}")
print(f"✅ OK: {passed}")
print(f"❌ Failures: {failed}")

if failed == 0:
    print("\n🎉 All components are integrated and working!")
    sys.exit(0)
else:
    print(f"\n⚠️  {failed} component(s) with issues")
    sys.exit(1)
