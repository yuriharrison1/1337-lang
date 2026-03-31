"""Codex Adapter — Integração com OpenAI Codex CLI.

Codex é a ferramenta de coding da OpenAI baseada em GPT-4.
Documentação: https://github.com/openai/codex
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from .base import AdapterContext, AdapterResponse, BaseIDEAdapter, MessageRole, ToolNotFoundError


class CodexAdapter(BaseIDEAdapter):
    """Adaptador para OpenAI Codex CLI.
    
    Codex é um agente de coding que pode:
    - Ler e editar arquivos
    - Executar comandos no terminal
    - Usar ferramentas (git, grep, etc)
    - Trabalhar em modo sandboxed
    
    Features suportadas:
        - Chat interativo
        - Modo aprovação (full, suggest, none)
        - Contexto de diretório
        - Execução de comandos
    
    Example:
        >>> adapter = CodexAdapter(project_dir="/path/to/project")
        >>> if adapter.is_available():
        ...     resp = await adapter.send_message("Refatore esta função")
        ...     print(resp.text)
    
    Configuração:
        Requer OPENAI_API_KEY no ambiente.
    """
    
    name = "codex"
    version_command = ("codex", "--version")
    
    # Modos de aprovação do Codex
    APPROVAL_MODES = ["full", "suggest", "none"]
    
    def __init__(
        self,
        project_dir: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        approval_mode: str = "suggest",
        timeout: int = 120,
        **kwargs
    ):
        """Inicializa adaptador Codex.
        
        Args:
            project_dir: Diretório do projeto
            api_key: API key OpenAI (opcional, usa env)
            model: Modelo (gpt-4o, o3-mini, etc)
            approval_mode: full/suggest/none
            timeout: Timeout em segundos
        """
        super().__init__(project_dir=project_dir, **kwargs)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.approval_mode = approval_mode
        self.timeout = timeout
        
        if approval_mode not in self.APPROVAL_MODES:
            raise ValueError(f"approval_mode deve ser um de: {self.APPROVAL_MODES}")
        
        self._check_project()
    
    def _check_project(self):
        """Verifica se o diretório do projeto é válido."""
        if self.project_dir and not Path(self.project_dir).exists():
            raise ValueError(f"Diretório do projeto não existe: {self.project_dir}")
    
    def is_available(self) -> bool:
        """Verifica se 'codex' CLI está instalado."""
        try:
            result = subprocess.run(
                ["codex", "--version"],
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
        image_paths: Optional[list[str]] = None
    ) -> list[str]:
        """Constrói comando codex com argumentos."""
        cmd = ["codex"]
        
        # Modelo
        cmd.extend(["--model", self.model])
        
        # Modo de aprovação
        cmd.extend(["--approval-mode", self.approval_mode])
        
        # Quiet mode (menos output de status)
        cmd.append("--quiet")
        
        # Imagem (se houver)
        if image_paths:
            for img in image_paths:
                cmd.extend(["--image", img])
        
        # Mensagem
        cmd.append(message)
        
        return cmd
    
    async def send_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        image_paths: Optional[list[str]] = None,
        **kwargs
    ) -> AdapterResponse:
        """Envia mensagem para Codex.
        
        Args:
            message: Texto da mensagem
            context: Contexto com arquivo/seleção
            image_paths: Caminhos de imagens para análise
            
        Returns:
            AdapterResponse
            
        Raises:
            ToolNotFoundError: Se codex não estiver instalado
        """
        if not self.is_available():
            raise ToolNotFoundError(
                "Codex não encontrado. "
                "Instale: https://github.com/openai/codex"
            )
        
        if not self.api_key:
            raise ToolNotFoundError(
                "OPENAI_API_KEY não configurada"
            )
        
        cmd = self._build_command(message, context, image_paths)
        
        env = os.environ.copy()
        if self.api_key:
            env["OPENAI_API_KEY"] = self.api_key
        
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
                timeout=self.timeout
            )
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            success = proc.returncode == 0
            text = output if success else f"{output}\n{error}"
            
            # Extrai arquivos modificados
            files_modified = self._extract_file_changes(text)
            
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
                command_executed=" ".join(cmd),
                metadata={
                    "model": self.model,
                    "approval_mode": self.approval_mode,
                    "has_error": not success,
                }
            )
            
            self._add_to_history(response)
            return response
            
        except __import__('asyncio').TimeoutError:
            return AdapterResponse(
                text=f"Timeout: Codex demorou mais de {self.timeout}s",
                exit_code=-1,
                command_executed=" ".join(cmd)
            )
        except Exception as e:
            return AdapterResponse(
                text=f"Erro executando Codex: {e}",
                exit_code=-1,
                command_executed=" ".join(cmd)
            )
    
    async def stream_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream de resposta do Codex.
        
        Codex não suporta streaming nativo em modo quiet.
        Simula por linhas.
        """
        response = await self.send_message(message, context, **kwargs)
        
        for line in response.text.split('\n'):
            yield line + '\n'
            await __import__('asyncio').sleep(0.01)
    
    def _extract_file_changes(self, output: str) -> list[str]:
        """Extrai arquivos modificados do output do Codex."""
        files = []
        
        # Padrões comuns do Codex
        patterns = [
            r'(?:modified|created|deleted)\s+["\']?(\S+)["\']?',
            r'(?:arquivo|file)\s+["\']?(\S+)["\']?\s+(?:modificado|criado|excluído)',
            r'✓\s+(\S+\.(?:py|rs|js|ts|go|java|cpp|c|md|json|yaml|toml))',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, output, re.IGNORECASE)
            for match in matches:
                file_path = match.group(1)
                if file_path not in files:
                    files.append(file_path)
        
        return files
    
    async def review_changes(self) -> AdapterResponse:
        """Solicita revisão das mudanças atuais.
        
        Returns:
            AdapterResponse com análise do Codex
        """
        return await self.send_message(
            "Revise as mudanças feitas e explique o que foi alterado "
            "e por quê. Liste os arquivos modificados."
        )
    
    async def explain_file(self, file_path: str) -> AdapterResponse:
        """Solicita explicação de um arquivo específico.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            AdapterResponse com explicação
        """
        context = AdapterContext(file_path=file_path)
        return await self.send_message(
            f"Explique o arquivo {file_path} em detalhes. "
            "Inclua: propósito, estrutura, e pontos importantes.",
            context=context
        )
    
    async def suggest_tests(self, file_path: str) -> AdapterResponse:
        """Solicita sugestão de testes para um arquivo.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            AdapterResponse com testes sugeridos
        """
        context = AdapterContext(file_path=file_path)
        return await self.send_message(
            f"Sugira testes unitários para {file_path}. "
            "Inclua casos edge e mocks necessários.",
            context=context
        )
    
    def get_config(self) -> dict[str, Any]:
        """Retorna configuração atual."""
        return {
            "name": self.name,
            "version": self.get_version(),
            "model": self.model,
            "approval_mode": self.approval_mode,
            "project_dir": self.project_dir,
            "available": self.is_available(),
        }
