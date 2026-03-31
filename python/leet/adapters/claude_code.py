"""Claude Code Adapter — Integração com a CLI da Anthropic.

Claude Code é a ferramenta oficial da Anthropic para coding com Claude.
Documentação: https://docs.anthropic.com/claude/docs/claude-code
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from .base import AdapterContext, AdapterResponse, BaseIDEAdapter, MessageRole, ToolNotFoundError


class ClaudeCodeAdapter(BaseIDEAdapter):
    """Adaptador para Claude Code (CLI da Anthropic).
    
    Claude Code permite interação com Claude diretamente do terminal,
    com acesso ao filesystem, git, e execução de comandos.
    
    Features suportadas:
        - Chat interativo via CLI
        - Modo não-interativo (--output)
        - Contexto de arquivos automático
        - Integração git
        - Execução de comandos sandboxed
    
    Example:
        >>> adapter = ClaudeCodeAdapter(project_dir="/path/to/project")
        >>> if adapter.is_available():
        ...     resp = await adapter.send_message("Explique este código")
        ...     print(resp.text)
    
    Configuração:
        A CLI usa a variável ANTHROPIC_API_KEY ou busca em ~/.anthropic/.
    """
    
    name = "claude-code"
    version_command = ("claude", "--version")
    
    def __init__(
        self,
        project_dir: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        auto_accept: bool = False,
        verbose: bool = False,
        **kwargs
    ):
        """Inicializa adaptador Claude Code.
        
        Args:
            project_dir: Diretório do projeto (obrigatório)
            api_key: API key Anthropic (opcional, usa env)
            model: Modelo Claude a usar
            auto_accept: Se True, aceita automaticamente sugestões
            verbose: Modo verboso para debug
        """
        super().__init__(project_dir=project_dir, **kwargs)
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.auto_accept = auto_accept
        self.verbose = verbose
        
        # Verifica se tem projeto configurado
        self._check_project()
    
    def _check_project(self):
        """Verifica se o diretório do projeto é válido."""
        if self.project_dir and not Path(self.project_dir).exists():
            raise ValueError(f"Diretório do projeto não existe: {self.project_dir}")
    
    def is_available(self) -> bool:
        """Verifica se 'claude' CLI está instalado.
        
        Returns:
            True se claude command está no PATH
        """
        try:
            result = subprocess.run(
                ["claude", "--version"],
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
        files: Optional[list[str]] = None
    ) -> list[str]:
        """Constrói comando claude com argumentos.
        
        Args:
            message: Mensagem para Claude
            context: Contexto opcional
            files: Arquivos específicos para incluir
            
        Returns:
            Lista de argumentos para subprocess
        """
        cmd = ["claude"]
        
        # Modo não-interativo (captura output)
        cmd.append("--output")
        
        # Modelo
        cmd.extend(["--model", self.model])
        
        # Diretório do projeto
        if self.project_dir:
            cmd.extend(["--cwd", self.project_dir])
        
        # Arquivos de contexto
        if context and context.file_path:
            cmd.extend(["--file", context.file_path])
        
        if files:
            for f in files:
                cmd.extend(["--file", f])
        
        # Auto-accept (perigoso, use com cautela)
        if self.auto_accept:
            cmd.append("--yes")
        
        # Mensagem
        cmd.append(message)
        
        return cmd
    
    async def send_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        files: Optional[list[str]] = None,
        **kwargs
    ) -> AdapterResponse:
        """Envia mensagem para Claude Code.
        
        Args:
            message: Texto da mensagem
            context: Contexto com arquivo/seleção
            files: Arquivos adicionais para contexto
            
        Returns:
            AdapterResponse com texto e metadados
            
        Raises:
            ToolNotFoundError: Se claude não estiver instalado
        """
        if not self.is_available():
            raise ToolNotFoundError(
                "Claude Code não encontrado. "
                "Instale: https://docs.anthropic.com/claude/docs/claude-code"
            )
        
        cmd = self._build_command(message, context, files)
        
        # Executa comando
        env = os.environ.copy()
        if self.api_key:
            env["ANTHROPIC_API_KEY"] = self.api_key
        
        try:
            proc = await __import__('asyncio').create_subprocess_exec(
                *cmd,
                stdout=__import__('asyncio').subprocess.PIPE,
                stderr=__import__('asyncio').subprocess.PIPE,
                env=env,
                cwd=self.project_dir
            )
            
            stdout, stderr = await __import__('asyncio').wait_for(
                proc.communicate(),
                timeout=120.0
            )
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            # Claude Code retorna 0 mesmo com warnings
            success = proc.returncode == 0
            text = output if success else f"{output}\n{error}"
            
            # Extrai arquivos modificados do output
            files_modified = self._extract_file_changes(text)
            
            # Projeta resposta em COGON se auto_project ativado
            cogon = None
            if self.auto_project:
                cogon = await self.project_to_cogon(text)
            
            response = AdapterResponse(
                text=text.strip(),
                cogon=cogon,
                role=MessageRole.ASSISTANT,
                files_modified=files_modified,
                exit_code=proc.returncode,
                command_executed=" ".join(cmd),
                metadata={
                    "model": self.model,
                    "auto_accept": self.auto_accept,
                    "has_error": not success,
                }
            )
            
            self._add_to_history(response)
            return response
            
        except __import__('asyncio').TimeoutError:
            return AdapterResponse(
                text="Timeout: Claude Code demorou mais de 120s",
                exit_code=-1,
                command_executed=" ".join(cmd)
            )
        except Exception as e:
            return AdapterResponse(
                text=f"Erro executando Claude Code: {e}",
                exit_code=-1,
                command_executed=" ".join(cmd)
            )
    
    async def stream_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream de resposta do Claude Code.
        
        NOTA: Claude Code não suporta streaming nativo no modo --output.
        Esta implementação simula streaming por linhas.
        
        Yields:
            Linhas do output
        """
        response = await self.send_message(message, context, **kwargs)
        
        # Simula streaming por linhas
        for line in response.text.split('\n'):
            yield line + '\n'
            await __import__('asyncio').sleep(0.01)  # Simula delay
    
    def _extract_file_changes(self, output: str) -> list[str]:
        """Extrai lista de arquivos modificados do output.
        
        Claude Code indica mudanças com padrões como:
        - "I will edit X"
        - "Edited X"
        - "Created X"
        """
        files = []
        
        patterns = [
            r'(?:edited|created|modified|deleted)\s+["\']?(\S+\.(?:py|rs|js|ts|jsx|tsx|go|java|cpp|c|h|hpp|md|txt|json|yaml|yml|toml))["\']?',
            r'(?:file|arquivo)\s+["\']?(\S+)["\']?',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, output, re.IGNORECASE)
            for match in matches:
                file_path = match.group(1)
                if file_path not in files:
                    files.append(file_path)
        
        return files
    
    async def diff(self, target: str = "HEAD") -> AdapterResponse:
        """Mostra diff de mudanças propostas por Claude.
        
        Args:
            target: Alvo do diff (HEAD, staged, etc)
            
        Returns:
            AdapterResponse com diff
        """
        return await self.execute_command(
            "git",
            ["diff", target],
            cwd=self.project_dir
        )
    
    async def accept_changes(self) -> AdapterResponse:
        """Aceita mudanças propostas (quando auto_accept=False).
        
        Returns:
            AdapterResponse com resultado
        """
        # Claude Code não tem comando explícito de "accept"
        # Mudanças já são aplicadas automaticamente
        return AdapterResponse(
            text="Mudanças já aplicadas. Use git para gerenciar."
        )
    
    async def reject_changes(self) -> AdapterResponse:
        """Rejeita mudanças propostas.
        
        Returns:
            AdapterResponse com resultado do git checkout
        """
        return await self.execute_command(
            "git",
            ["checkout", "--", "."],
            cwd=self.project_dir
        )
    
    def get_config(self) -> dict[str, Any]:
        """Retorna configuração atual do adaptador."""
        return {
            "name": self.name,
            "version": self.get_version(),
            "model": self.model,
            "project_dir": self.project_dir,
            "auto_accept": self.auto_accept,
            "available": self.is_available(),
        }
