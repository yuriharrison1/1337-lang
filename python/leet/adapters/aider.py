"""Aider Adapter — Integração com Aider (multi-LLM coding assistant).

Aider é uma ferramenta popular que permite editar código em paralelo com LLMs,
suportando múltiplos modelos (GPT-4, Claude, etc).
Documentação: https://aider.chat/
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from .base import AdapterContext, AdapterResponse, BaseIDEAdapter, MessageRole, ToolNotFoundError


class AiderAdapter(BaseIDEAdapter):
    """Adaptador para Aider.
    
    Aider é único porque:
    - Suporta múltiplos LLMs (OpenAI, Anthropic, OpenRouter, etc)
    - Edita arquivos diretamente no editor
    - Integração com git automática
    - Mapa de repostório para contexto
    - Suporte a testes automáticos
    
    Features:
        - Chat com contexto de arquivos
        - Edição direta de código
        - Commit automático
        - Testes (pytest, etc)
    
    Example:
        >>> adapter = AiderAdapter(
        ...     project_dir="/path",
        ...     model="gpt-4o",
        ...     auto_commit=True
        ... )
        >>> resp = await adapter.send_message("Adicione validação de email")
    
    Configuração:
        Requer OPENAI_API_KEY, ANTHROPIC_API_KEY, ou outra key
        dependendo do modelo escolhido.
    """
    
    name = "aider"
    version_command = ("aider", "--version")
    
    MODELOS_POPULARES = [
        "gpt-4o",
        "gpt-4o-mini",
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "deepseek-chat",
    ]
    
    def __init__(
        self,
        project_dir: Optional[str] = None,
        model: str = "gpt-4o",
        editor_model: Optional[str] = None,
        weak_model: Optional[str] = None,
        auto_commit: bool = True,
        test_cmd: Optional[str] = None,
        lint_cmd: Optional[str] = None,
        **kwargs
    ):
        """Inicializa adaptador Aider.
        
        Args:
            project_dir: Diretório do projeto (obrigatório)
            model: Modelo principal
            editor_model: Modelo para edições (default=model)
            weak_model: Modelo para tarefas simples
            auto_commit: Commit automático após mudanças
            test_cmd: Comando para rodar testes
            lint_cmd: Comando para linting
        """
        super().__init__(project_dir=project_dir, **kwargs)
        self.model = model
        self.editor_model = editor_model or model
        self.weak_model = weak_model
        self.auto_commit = auto_commit
        self.test_cmd = test_cmd
        self.lint_cmd = lint_cmd
        
        if not self.project_dir:
            raise ValueError("Aider requer project_dir")
        
        self._check_project()
    
    def _check_project(self):
        """Verifica se o diretório do projeto é válido."""
        if not Path(self.project_dir).exists():
            raise ValueError(f"Diretório do projeto não existe: {self.project_dir}")
        
        # Verifica se é um repo git (recomendado)
        git_dir = Path(self.project_dir) / ".git"
        self.is_git_repo = git_dir.exists()
    
    def is_available(self) -> bool:
        """Verifica se 'aider' está instalado."""
        try:
            result = subprocess.run(
                ["aider", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _build_command(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        files: Optional[list[str]] = None,
        read_only: Optional[list[str]] = None
    ) -> list[str]:
        """Constrói comando aider com argumentos."""
        cmd = ["aider"]
        
        # Modelos
        cmd.extend(["--model", self.model])
        if self.editor_model != self.model:
            cmd.extend(["--editor-model", self.editor_model])
        if self.weak_model:
            cmd.extend(["--weak-model", self.weak_model])
        
        # Auto-commit
        if self.auto_commit:
            cmd.append("--auto-commits")
        else:
            cmd.append("--no-auto-commits")
        
        # Comandos de teste/lint
        if self.test_cmd:
            cmd.extend(["--test-cmd", self.test_cmd])
        if self.lint_cmd:
            cmd.extend(["--lint-cmd", self.lint_cmd])
        
        # Mensagem
        cmd.extend(["--message", message])
        
        # Arquivos para editar
        if files:
            for f in files:
                cmd.append(f)
        
        # Arquivos read-only (contexto)
        if read_only:
            for f in read_only:
                cmd.extend(["--read", f])
        
        # Arquivo de contexto
        if context and context.file_path:
            if context.file_path not in (files or []):
                cmd.append(context.file_path)
        
        return cmd
    
    async def send_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        files: Optional[list[str]] = None,
        read_only: Optional[list[str]] = None,
        **kwargs
    ) -> AdapterResponse:
        """Envia mensagem para Aider.
        
        Args:
            message: Texto da mensagem
            context: Contexto
            files: Arquivos para editar
            read_only: Arquivos só para leitura (contexto)
            
        Returns:
            AdapterResponse
        """
        if not self.is_available():
            raise ToolNotFoundError(
                "Aider não encontrado. "
                "Instale: pip install aider-chat"
            )
        
        cmd = self._build_command(message, context, files, read_only)
        
        try:
            proc = await __import__('asyncio').create_subprocess_exec(
                *cmd,
                stdout=__import__('asyncio').subprocess.PIPE,
                stderr=__import__('asyncio').subprocess.PIPE,
                cwd=self.project_dir
            )
            
            stdout, stderr = await __import__('asyncio').wait_for(
                proc.communicate(),
                timeout=180.0  # Aider pode demorar mais
            )
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            success = proc.returncode == 0
            text = output if success else f"{output}\n{error}"
            
            # Extrai arquivos modificados
            files_modified = self._extract_file_changes(text)
            
            # Detecta commits
            commits = self._extract_commits(text)
            
            # Projeta em COGON
            cogon = None
            if self.auto_project:
                cogon = await self.project_to_cogon(text)
            
            response = AdapterResponse(
                text=text.strip(),
                cogon=cogon,
                role=MessageRole.ASSISTANT,
                files_modified=files_modified,
                exit_code=proc.returncode,
                command_executed=f"aider --message '{message[:50]}...'",
                metadata={
                    "model": self.model,
                    "editor_model": self.editor_model,
                    "auto_commit": self.auto_commit,
                    "commits": commits,
                    "is_git_repo": self.is_git_repo,
                    "has_error": not success,
                }
            )
            
            self._add_to_history(response)
            return response
            
        except __import__('asyncio').TimeoutError:
            return AdapterResponse(
                text="Timeout: Aider demorou mais de 180s",
                exit_code=-1
            )
        except Exception as e:
            return AdapterResponse(
                text=f"Erro executando Aider: {e}",
                exit_code=-1
            )
    
    async def add_files(self, files: list[str]) -> AdapterResponse:
        """Adiciona arquivos ao contexto do Aider.
        
        Args:
            files: Lista de caminhos de arquivos
            
        Returns:
            AdapterResponse
        """
        cmd = ["aider", "--add"] + files
        return await self.execute_command(cmd[0], cmd[1:], cwd=self.project_dir)
    
    async def drop_files(self, files: list[str]) -> AdapterResponse:
        """Remove arquivos do contexto do Aider."""
        cmd = ["aider", "--drop"] + files
        return await self.execute_command(cmd[0], cmd[1:], cwd=self.project_dir)
    
    async def lint(self) -> AdapterResponse:
        """Roda linting nos arquivos modificados."""
        if not self.lint_cmd:
            return AdapterResponse(
                text="Lint não configurado. Defina lint_cmd."
            )
        return await self.send_message("/lint")
    
    async def test(self) -> AdapterResponse:
        """Roda testes."""
        if not self.test_cmd:
            return AdapterResponse(
                text="Testes não configurados. Defina test_cmd."
            )
        return await self.send_message("/test")
    
    async def commit(self, message: Optional[str] = None) -> AdapterResponse:
        """Faz commit das mudanças.
        
        Args:
            message: Mensagem do commit (opcional)
        """
        if message:
            return await self.send_message(f"/commit {message}")
        return await self.send_message("/commit")
    
    async def undo(self) -> AdapterResponse:
        """Desfaz última mudança."""
        return await self.send_message("/undo")
    
    async def reset(self) -> AdapterResponse:
        """Reseta para último commit."""
        return await self.send_message("/reset")
    
    def _extract_file_changes(self, output: str) -> list[str]:
        """Extrai arquivos modificados do output do Aider."""
        files = []
        
        # Padrões do Aider
        patterns = [
            r'(?:Edited|Created|Deleted)\s+["\']?(\S+)["\']?',
            r'(?:editou|criou|deletou)\s+["\']?(\S+)["\']?',
            r'◀\s+(\S+\.(?:py|rs|js|ts|go|java|cpp|c|md|json|yaml|toml))',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, output, re.IGNORECASE)
            for match in matches:
                file_path = match.group(1)
                if file_path not in files:
                    files.append(file_path)
        
        return files
    
    def _extract_commits(self, output: str) -> list[str]:
        """Extrai hashes de commits."""
        commits = []
        pattern = r'(?:commit|committed)\s+([a-f0-9]{7,40})'
        for match in re.finditer(pattern, output, re.IGNORECASE):
            commits.append(match.group(1))
        return commits
    
    def get_repo_map(self) -> AdapterResponse:
        """Obtém mapa do repositório.
        
        Executa aider --show-repo-map para ver o contexto.
        """
        return self.execute_command(
            "aider",
            ["--show-repo-map"],
            cwd=self.project_dir
        )
    
    def get_config(self) -> dict[str, Any]:
        """Retorna configuração atual."""
        return {
            "name": self.name,
            "version": self.get_version(),
            "model": self.model,
            "editor_model": self.editor_model,
            "auto_commit": self.auto_commit,
            "test_cmd": self.test_cmd,
            "lint_cmd": self.lint_cmd,
            "project_dir": self.project_dir,
            "is_git_repo": self.is_git_repo,
            "available": self.is_available(),
        }
