#!/usr/bin/env python3
"""Testa conexão com APIs e mostra status detalhado."""

import os
import sys

def test_deepseek():
    """Testa API DeepSeek."""
    print("=" * 60)
    print("🧪 TESTE: DeepSeek API")
    print("=" * 60)
    
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("❌ DEEPSEEK_API_KEY não definida")
        return False
    
    print(f"✅ API Key encontrada: {key[:15]}...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
        
        print("🔄 Enviando requisição...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{
                "role": "user", 
                "content": "Você é um SRE. O serviço está down. Responda em 1 frase o que fazer."
            }],
            max_tokens=100
        )
        
        text = response.choices[0].message.content
        print(f"✅ Resposta recebida!")
        print(f"📤 Texto: {text[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Erro: {type(e).__name__}: {e}")
        return False

def test_anthropic():
    """Testa API Anthropic."""
    print("\n" + "=" * 60)
    print("🧪 TESTE: Anthropic API")
    print("=" * 60)
    
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("⚠️  ANTHROPIC_API_KEY não definida (opcional)")
        return None
    
    print(f"✅ API Key encontrada: {key[:15]}...")
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        
        print("🔄 Enviando requisição...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": "Você é um SRE. O serviço está down. Responda em 1 frase."
            }]
        )
        
        text = response.content[0].text
        print(f"✅ Resposta recebida!")
        print(f"📤 Texto: {text[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Erro: {type(e).__name__}: {e}")
        return False

def test_net1337():
    """Testa net1337.py com diagnóstico detalhado."""
    print("\n" + "=" * 60)
    print("🧪 TESTE: net1337.py (1 round)")
    print("=" * 60)
    
    import subprocess
    import json
    
    # Criar script de teste
    test_script = '''
import sys
sys.path.insert(0, ".")

from net1337 import create_backend, Network1337, RustBridge, SCENARIOS
import os

key = os.environ.get("DEEPSEEK_API_KEY")
if not key:
    print("❌ Sem API key")
    sys.exit(1)

try:
    backend = create_backend("deepseek")
    print("✅ Backend criado")
except Exception as e:
    print(f"❌ Erro criando backend: {e}")
    sys.exit(1)

rust = RustBridge()
print(f"🦀 Rust: {rust.mode if rust.available() else 'indisponível'}")

net = Network1337(rust, backend)

# Adicionar 2 agentes
for ag in SCENARIOS["incident"]["agents"][:2]:
    net.add_agent(ag["name"], ag["persona"])

print(f"👥 Agentes: {[a.name for a in net.agents.values()]}")

# Handshake
net.handshake()

# Enviar mensagem
print("\\n💬 Enviando mensagem...")
try:
    responses = net.inject("Servidor caiu, precisamos de ação")
    print(f"✅ {len(responses)} respostas recebidas")
    for i, resp in enumerate(responses):
        print(f"  {i+1}. {resp[:80]}...")
except Exception as e:
    print(f"❌ Erro: {type(e).__name__}: {e}")
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
    print("🔍 DIAGNÓSTICO 1337 - APIs")
    print()
    
    # Testar APIs
    ds_ok = test_deepseek()
    
    if ds_ok:
        print("\n" + "=" * 60)
        print("✅ DeepSeek funcionando! Testando net1337...")
        print("=" * 60)
        net_ok = test_net1337()
        
        if net_ok:
            print("\n🎉 TUDO FUNCIONANDO! Pode rodar ./demo_auto.sh")
        else:
            print("\n⚠️  net1337.py teve problema. Verifique erros acima.")
    else:
        print("\n❌ DeepSeek não está funcionando.")
        print("   Verifique: export DEEPSEEK_API_KEY=sk-...")
