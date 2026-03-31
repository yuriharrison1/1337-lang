"""Kimi Adapter — Integração com Kimi Code CLI (Moonshot AI).

Kimi é um modelo de linguagem da Moonshot AI popular na China,
com forte suporte a contexto longo (200K+ tokens).
Documentação: https://platform.moonshot.cn/
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from .base import AdapterContext, AdapterResponse, BaseIDEAdapter, MessageRole, ToolNotFoundError


class KimiAdapter(BaseIDEAdapter):
    """Adaptador para Kimi Code CLI.
    
    Kimi é conhecido por:
    - Contexto longo (até 2M tokens no Kimi K1.5)
    - Bom desempenho em código
    - Suporte multilíngue (chinês/inglês)
    
    Features:
        - Chat com contexto longo
        - Modo coding especializado
        - Suporte a arquivos
    
    Example:
        >>> adapter = KimiAdapter(project_dir="/path", api_key="sk-...")
        >>> resp = await adapter.send_message("Analise este projeto")
    
    Configuração:
        Requer MOONSHOT_API_KEY ou KIMI_API_KEY.
    """
    
    name = "kimi"
    version_command = ("kimi", "--version")
    
    MODELOS = ["kimi-k1", "kimi-k1.5", "kimi-moonshot-v1-128k", "kimi-moonshot-v1-32k"]
    
    def __init__(
        self,
        project_dir: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "kimi-k1.5",
        temperature: float = 0.7,
        timeout: int = 120,
        **kwargs
    ):
        """Inicializa adaptador Kimi.
        
        Args:
            project_dir: Diretório do projeto
            api_key: API key Moonshot
            model: Modelo Kimi
            temperature: Temperatura de sampling
            timeout: Timeout em segundos
        """
        super().__init__(project_dir=project_dir, **kwargs)
        self.api_key = api_key or os.environ.get("MOONSHOT_API_KEY") or os.environ.get("KIMI_API_KEY")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        
        self._check_project()
    
    def _check_project(self):
        """Verifica se o diretório do projeto é válido."""
        if self.project_dir and not Path(self.project_dir).exists():
            raise ValueError(f"Diretório do projeto não existe: {self.project_dir}")
    
    def is_available(self) -> bool:
        """Verifica se 'kimi' CLI está instalado."""
        try:
            result = subprocess.run(
                ["kimi", "--version"],
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
        """Constrói comando kimi com argumentos."""
        cmd = ["kimi"]
        
        # Modelo
        cmd.extend(["--model", self.model])
        
        # Temperatura
        cmd.extend(["--temperature", str(self.temperature)])
        
        # Arquivos de contexto
        if context and context.file_path:
            cmd.extend(["--file", context.file_path])
        
        if files:
            for f in files:
                cmd.extend(["--file", f])
        
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
        """Envia mensagem para Kimi.
        
        Args:
            message: Texto da mensagem
            context: Contexto
            files: Arquivos adicionais
            
        Returns:
            AdapterResponse
        """
        if not self.is_available():
            # Fallback para API direta se CLI não disponível
            return await self._send_via_api(message, context)
        
        cmd = self._build_command(message, context, files)
        
        env = os.environ.copy()
        if self.api_key:
            env["MOONSHOT_API_KEY"] = self.api_key
            env["KIMI_API_KEY"] = self.api_key
        
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
            
            files_modified = self._extract_file_changes(text)
            
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
                    "temperature": self.temperature,
                    "has_error": not success,
                }
            )
            
            self._add_to_history(response)
            return response
            
        except Exception as e:
            # Fallback para API
            return await self._send_via_api(message, context)
    
    async def _send_via_api(
        self,
        message: str,
        context: Optional[AdapterContext] = None
    ) -> AdapterResponse:
        """Fallback: envia via API HTTP direta.
        
        Usado quando CLI não está disponível.
        """
        if not self.api_key:
            return AdapterResponse(
                text="Kimi CLI não disponível e API key não configurada",
                exit_code=-1
            )
        
        import aiohttp
        
        url = "https://api.moonshot.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [{"role": "user", "content": message}]
        
        # Adiciona contexto de arquivo se houver
        if context and context.file_path:
            try:
                with open(context.file_path, 'r') as f:
                    content = f.read()
                messages.insert(0, {
                    "role": "system",
                    "content": f"Contexto do arquivo {context.file_path}:\n```\n{content[:8000]}\n```"
                })
            except Exception:
                pass
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        text = result['choices'][0]['message']['content']
                        
                        cogon = None
                        if self.auto_project:
                            cogon = await self.project_to_cogon(text)
                        
                        return AdapterResponse(
                            text=text,
                            cogon=cogon,
                            metadata={"via": "api", "model": self.model}
                        )
                    else:
                        error = await resp.text()
                        return AdapterResponse(
                            text=f"API Error: {resp.status} - {error}",
                            exit_code=-1
                        )
        except Exception as e:
            return AdapterResponse(
                text=f"Erro na API: {e}",
                exit_code=-1
            )
    
    async def stream_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream de resposta do Kimi."""
        # Kimi API suporta streaming
        if not self.is_available() and self.api_key:
            async for chunk in self._stream_via_api(message, context):
                yield chunk
        else:
            response = await self.send_message(message, context, **kwargs)
            for line in response.text.split('\n'):
                yield line + '\n'
                await __import__('asyncio').sleep(0.01)
    
    async def _stream_via_api(
        self,
        message: str,
        context: Optional[AdapterContext] = None
    ) -> AsyncIterator[str]:
        """Streaming via API."""
        import aiohttp
        
        url = "https://api.moonshot.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
            "temperature": self.temperature,
            "stream": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    async for line in resp.content:
                        line = line.decode().strip()
                        if line.startswith("data: "):
                            chunk = line[6:]
                            if chunk == "[DONE]":
                                break
                            try:
                                data = json.loads(chunk)
                                delta = data['choices'][0]['delta'].get('content', '')
                                if delta:
                                    yield delta
                            except (json.JSONDecodeError, KeyError):
                                pass
        except Exception as e:
            yield f"[Erro no stream: {e}]"
    
    def _extract_file_changes(self, output: str) -> list[str]:
        """Extrai arquivos modificados."""
        files = []
        patterns = [
            r'(?:修改|创建|删除|编辑)\s+["\']?(\S+)["\']?',
            r'(?:modified|created|deleted)\s+["\']?(\S+)["\']?',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, output, re.IGNORECASE)
            for match in matches:
                file_path = match.group(1)
                if file_path not in files:
                    files.append(file_path)
        
        return files
    
    async def analyze_project(self) -> AdapterResponse:
        """Análise abrangente do projeto."""
        return await self.send_message(
            "Analise a estrutura deste projeto. "
            "Identifique: padrões de código, dependências principais, "
            "possíveis problemas e oportunidades de melhoria."
        )
    
    async def generate_documentation(self, file_path: str) -> AdapterResponse:
        """Gera documentação para um arquivo."""
        context = AdapterContext(file_path=file_path)
        return await self.send_message(
            f"Gere documentação completa para {file_path}. "
            "Inclua: descrição, parâmetros, retornos, exemplos.",
            context=context
        )
    
    def get_config(self) -> dict[str, Any]:
        """Retorna configuração atual."""
        return {
            "name": self.name,
            "version": self.get_version(),
            "model": self.model,
            "temperature": self.temperature,
            "project_dir": self.project_dir,
            "available": self.is_available(),
            "api_configured": bool(self.api_key),
        }
