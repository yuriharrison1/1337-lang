#!/usr/bin/env python3
"""Tests API connectivity and shows detailed status."""

import os
import sys

def test_deepseek():
    """Tests the DeepSeek API."""
    print("=" * 60)
    print("🧪 TEST: DeepSeek API")
    print("=" * 60)

    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("❌ DEEPSEEK_API_KEY not set")
        return False

    print(f"✅ API key found: {key[:15]}...")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url="https://api.deepseek.com")

        print("🔄 Sending request...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{
                "role": "user",
                "content": "You are an SRE. The service is down. Answer in 1 sentence what to do."
            }],
            max_tokens=100
        )

        text = response.choices[0].message.content
        print(f"✅ Response received!")
        print(f"📤 Text: {text[:100]}...")
        return True

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False

def test_anthropic():
    """Tests the Anthropic API."""
    print("\n" + "=" * 60)
    print("🧪 TEST: Anthropic API")
    print("=" * 60)

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("⚠️  ANTHROPIC_API_KEY not set (optional)")
        return None

    print(f"✅ API key found: {key[:15]}...")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)

        print("🔄 Sending request...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": "You are an SRE. The service is down. Answer in 1 sentence."
            }]
        )

        text = response.content[0].text
        print(f"✅ Response received!")
        print(f"📤 Text: {text[:100]}...")
        return True

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False

def test_net1337():
    """Tests net1337.py with detailed diagnostics."""
    print("\n" + "=" * 60)
    print("🧪 TEST: net1337.py (1 round)")
    print("=" * 60)

    import subprocess
    import json

    # Create the test script
    test_script = '''
import sys
sys.path.insert(0, ".")

from net1337 import create_backend, Network1337, RustBridge, SCENARIOS
import os

key = os.environ.get("DEEPSEEK_API_KEY")
if not key:
    print("❌ No API key")
    sys.exit(1)

try:
    backend = create_backend("deepseek")
    print("✅ Backend created")
except Exception as e:
    print(f"❌ Error creating backend: {e}")
    sys.exit(1)

rust = RustBridge()
print(f"🦀 Rust: {rust.mode if rust.available() else 'unavailable'}")

net = Network1337(rust, backend)

# Add 2 agents
for ag in SCENARIOS["incident"]["agents"][:2]:
    net.add_agent(ag["name"], ag["persona"])

print(f"👥 Agents: {[a.name for a in net.agents.values()]}")

# Handshake
net.handshake()

# Send message
print("\\n💬 Sending message...")
try:
    responses = net.inject("Server went down, we need action")
    print(f"✅ {len(responses)} responses received")
    for i, resp in enumerate(responses):
        print(f"  {i+1}. {resp[:80]}...")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
'''

    result = subprocess.run(
        ["python3", "-c", test_script],
        capture_output=True,
        text=True,
        timeout=60
    )

    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
        return False
    return True

if __name__ == "__main__":
    print("🔍 1337 DIAGNOSTICS - APIs")
    print()

    # Test the APIs
    ds_ok = test_deepseek()

    if ds_ok:
        print("\n" + "=" * 60)
        print("✅ DeepSeek working! Testing net1337...")
        print("=" * 60)
        net_ok = test_net1337()

        if net_ok:
            print("\n🎉 EVERYTHING WORKS! You can run ./demo_auto.sh")
        else:
            print("\n⚠️  net1337.py had an issue. Check the errors above.")
    else:
        print("\n❌ DeepSeek is not working.")
        print("   Check: export DEEPSEEK_API_KEY=sk-...")
