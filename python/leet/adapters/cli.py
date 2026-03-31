#!/usr/bin/env python3
"""CLI unificado para IDE Adapters.

Permite usar qualquer adaptador via linha de comando:

    # Claude Code
    leet-ide claude "Explique este código" --file main.py
    
    # Codex
    leet-ide codex "Refatore esta função" --file utils.py
    
    # Kimi
    leet-ide kimi "Analise o projeto" --project .
    
    # Aider
    leet-ide aider "Adicione tratamento de erro" --file api.py

Features:
    - Auto-detecção de adaptador disponível
    - Integração 1337 (COGON projection)
    - Streaming de resposta
    - Export de sessão
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
    """Detecta diretório do projeto atual."""
    current = Path.cwd()
    
    # Procura por marcadores comuns
    markers = ['.git', 'pyproject.toml', 'package.json', 'Cargo.toml', 'go.mod']
    
    for path in [current] + list(current.parents):
        for marker in markers:
            if (path / marker).exists():
                return str(path)
    
    return str(current)


def create_parser() -> argparse.ArgumentParser:
    """Cria parser de argumentos."""
    parser = argparse.ArgumentParser(
        prog="leet-ide",
        description="1337 IDE Adapters — CLI unificado para coding assistants",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Usar Claude Code
  leet-ide claude "Explique main.py"
  
  # Usar Codex com contexto
  leet-ide codex "Refatore" --file utils.py --selection "função problemática"
  
  # Kimi com streaming
  leet-ide kimi "Analise projeto" --stream
  
  # Aider com auto-commit
  leet-ide aider "Fix bug" --auto-commit --file bug.py
  
  # Auto-detectar adaptador
  leet-ide auto "Mensagem" --file code.py
  
  # Listar adaptadores disponíveis
  leet-ide --list
        """
    )
    
    parser.add_argument(
        'adapter',
        help='Adaptador a usar (claude, codex, kimi, aider, auto)'
    )
    
    parser.add_argument(
        'message',
        nargs='?',
        help='Mensagem para o assistente'
    )
    
    parser.add_argument(
        '--file', '-f',
        help='Arquivo de contexto'
    )
    
    parser.add_argument(
        '--project', '-p',
        help='Diretório do projeto (auto-detectado se omitido)'
    )
    
    parser.add_argument(
        '--selection', '-s',
        help='Texto selecionado no editor'
    )
    
    parser.add_argument(
        '--language', '-l',
        help='Linguagem de programação'
    )
    
    parser.add_argument(
        '--model', '-m',
        help='Modelo específico'
    )
    
    parser.add_argument(
        '--stream',
        action='store_true',
        help='Habilitar streaming de resposta'
    )
    
    parser.add_argument(
        '--no-cogon',
        action='store_true',
        help='Desabilitar projeção 1337 (COGON)'
    )
    
    parser.add_argument(
        '--export', '-e',
        help='Exportar sessão para arquivo JSON'
    )
    
    parser.add_argument(
        '--auto-commit',
        action='store_true',
        help='(Aider) Commit automático'
    )
    
    parser.add_argument(
        '--approval-mode',
        choices=['full', 'suggest', 'none'],
        default='suggest',
        help='(Codex) Modo de aprovação'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='%(prog)s 0.5.0'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='Listar adaptadores disponíveis'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Verificar disponibilidade dos adaptadores'
    )
    
    return parser


def check_adapters():
    """Verifica disponibilidade de todos os adaptadores."""
    print("Verificando adaptadores...\n")
    
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
            print(f"❌ {name:10s} Erro: {e}")


async def run_adapter(
    adapter_name: str,
    message: str,
    args: argparse.Namespace
) -> int:
    """Executa adaptador com mensagem.
    
    Returns:
        Exit code
    """
    project_dir = args.project or detect_project_dir()
    
    # Configurações específicas por adaptador
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
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    
    if not adapter.is_available():
        print(
            f"❌ {adapter_name} não está instalado ou configurado.",
            file=sys.stderr
        )
        print(f"   Veja: https://docs.1337.dev/adapters/{adapter_name}", file=sys.stderr)
        return 1
    
    # Cria contexto
    context = AdapterContext(
        file_path=args.file,
        project_dir=project_dir,
        selection=args.selection,
        language=args.language,
    )
    
    print(f"🚀 {adapter_name}: {message[:60]}...")
    print(f"   Projeto: {project_dir}")
    if args.file:
        print(f"   Arquivo: {args.file}")
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
                print(f"\n📁 Arquivos modificados:")
                for f in response.files_modified:
                    print(f"   • {f}")
            
            if response.cogon:
                # Mostra eixos dominantes
                top_indices = sorted(
                    range(32),
                    key=lambda i: response.cogon.sem[i],
                    reverse=True
                )[:5]
                print(f"\n🧠 Eixos semânticos dominantes:")
                from leet.axes import CANONICAL_AXES
                for idx in top_indices:
                    axis = CANONICAL_AXES[idx]
                    val = response.cogon.sem[idx]
                    print(f"   {axis.code}: {axis.name:20s} = {val:.2f}")
        
        # Exporta sessão se solicitado
        if args.export:
            session_data = {
                'adapter': adapter_name,
                'project_dir': project_dir,
                'message': message,
                'history': [r.to_dict() for r in adapter._history],
            }
            with open(args.export, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
            print(f"\n💾 Sessão exportada: {args.export}")
        
        return 0
        
    except ToolNotFoundError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Erro inesperado: {e}", file=sys.stderr)
        return 1


async def main_async() -> int:
    """Entry point async."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Flags especiais
    if args.list:
        print("Adaptadores disponíveis:")
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
                    print(f"Auto-detectado: {name}\n")
                    break
            except:
                continue
        else:
            print("Nenhum adaptador encontrado.", file=sys.stderr)
            return 1
    
    return await run_adapter(adapter_name, args.message, args)


def main() -> int:
    """Entry point."""
    return asyncio.run(main_async())


if __name__ == '__main__':
    sys.exit(main())
