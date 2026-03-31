"""Base classes for IDE adapters.

Define a interface comum que todos os adaptadores devem implementar.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional, Protocol

from leet import Cogon, blend, dist
from leet.bridge import MockProjector, SemanticProjector


class MessageRole(Enum):
    """Papel de uma mensagem na conversação."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class AdapterContext:
    """Contexto para uma interação com o adaptador.
    
    Attributes:
        file_path: Arquivo atual sendo editado
        project_dir: Diretório raiz do projeto
        selection: Texto selecionado no editor
        line_number: Linha atual do cursor
        column: Coluna atual do cursor
        language: Linguagem de programação detectada
        git_branch: Branch git atual
        git_commit: Commit hash atual
        env_vars: Variáveis de ambiente relevantes
        metadata: Metadados adicionais
    """
    file_path: Optional[str] = None
    project_dir: Optional[str] = None
    selection: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    language: Optional[str] = None
    git_branch: Optional[str] = None
    git_commit: Optional[str] = None
    env_vars: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_vscode(cls, data: dict) -> AdapterContext:
        """Cria contexto a partir de dados do VS Code."""
        return cls(
            file_path=data.get('fileName'),
            project_dir=data.get('workspaceFolder'),
            selection=data.get('selectedText'),
            line_number=data.get('lineNumber'),
            column=data.get('column'),
            language=data.get('languageId'),
        )
    
    @classmethod
    def from_neovim(cls, data: dict) -> AdapterContext:
        """Cria contexto a partir de dados do Neovim."""
        return cls(
            file_path=data.get('file'),
            selection=data.get('selection'),
            line_number=data.get('line'),
            column=data.get('col'),
        )
    
    def to_cogon_projection(self) -> tuple[list[float], list[float]]:
        """Converte o contexto em projeção semântica (sem, unc).
        
        Retorna valores baseados no tipo de contexto:
        - Código → A9_PROCESSO alto, C9_NATUREZA verbo
        - Arquivo → A8_ESTADO alto
        - Git → B2_TEMPORALIDADE, B7_ORIGEM
        """
        sem = [0.5] * 32
        unc = [0.3] * 32
        
        # A8_ESTADO — configuracional
        if self.file_path:
            sem[8] = 0.8  # A8_ESTADO
            unc[8] = 0.1
        
        # A9_PROCESSO — transformação
        if self.selection:
            sem[9] = 0.7  # A9_PROCESSO
            sem[30] = 0.6  # C9_NATUREZA (verbo)
            unc[9] = 0.15
        
        # B2_TEMPORALIDADE — âncora temporal
        if self.git_branch or self.git_commit:
            sem[15] = 0.75  # B2_TEMPORALIDADE
            unc[15] = 0.1
        
        return sem, unc


@dataclass
class AdapterResponse:
    """Resposta de um adaptador IDE.
    
    Attributes:
        text: Texto da resposta
        cogon: Representação semântica da resposta
        role: Papel da mensagem
        files_modified: Arquivos modificados pela ação
        exit_code: Código de saída (0 = sucesso)
        command_executed: Comando que foi executado
        metadata: Metadados adicionais
    """
    text: str
    cogon: Optional[Cogon] = None
    role: MessageRole = MessageRole.ASSISTANT
    files_modified: list[str] = field(default_factory=list)
    exit_code: int = 0
    command_executed: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def success(self) -> bool:
        """Retorna True se a operação foi bem-sucedida."""
        return self.exit_code == 0
    
    def to_dict(self) -> dict[str, Any]:
        """Serializa para dicionário."""
        return {
            'text': self.text,
            'role': self.role.value,
            'exit_code': self.exit_code,
            'command_executed': self.command_executed,
            'files_modified': self.files_modified,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
        }


class BaseIDEAdapter(ABC):
    """Classe base para todos os adaptadores IDE.
    
    Todos os adaptadores devem implementar:
    - send_message: Enviar mensagem e receber resposta
    - is_available: Verificar se a ferramenta está instalada
    - get_version: Obter versão da ferramenta
    
    Opcionalmente podem sobrescrever:
    - stream_message: Streaming de resposta
    - execute_command: Execução de comandos específicos
    - project_to_cogon: Projeção semântica customizada
    """
    
    # Nome do adaptador (deve ser sobrescrito)
    name: str = "base"
    
    # Comando para verificar instalação
    version_command: tuple[str, ...] = ()
    
    def __init__(
        self,
        projector: Optional[SemanticProjector] = None,
        project_dir: Optional[str] = None,
        auto_project: bool = True,
    ):
        """Inicializa o adaptador.
        
        Args:
            projector: Projetor semântico (None = MockProjector)
            project_dir: Diretório raiz do projeto
            auto_project: Se True, projeta todas as mensagens em COGONs
        """
        self.projector = projector or MockProjector()
        self.project_dir = project_dir
        self.auto_project = auto_project
        self._history: list[AdapterResponse] = []
        self._session_cogons: list[Cogon] = []
    
    @abstractmethod
    async def send_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        **kwargs
    ) -> AdapterResponse:
        """Envia uma mensagem para a ferramenta IDE.
        
        Args:
            message: Texto da mensagem
            context: Contexto opcional (arquivo, seleção, etc)
            **kwargs: Argumentos adicionais específicos do adaptador
            
        Returns:
            AdapterResponse com o resultado
        """
        pass
    
    async def stream_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream de resposta da ferramenta IDE.
        
        Yields:
            Chunks de texto da resposta
            
        Padrão: acumula tudo e yield uma vez.
        Adaptadores devem sobrescrever para verdadeiro streaming.
        """
        response = await self.send_message(message, context, **kwargs)
        yield response.text
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se a ferramenta IDE está instalada e acessível.
        
        Returns:
            True se disponível, False caso contrário
        """
        pass
    
    def get_version(self) -> Optional[str]:
        """Obtém a versão da ferramenta IDE.
        
        Returns:
            String da versão ou None se não disponível
        """
        if not self.version_command:
            return None
        
        try:
            result = subprocess.run(
                self.version_command,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None
    
    async def execute_command(
        self,
        command: str,
        args: list[str],
        cwd: Optional[str] = None
    ) -> AdapterResponse:
        """Executa um comando diretamente na ferramenta.
        
        Args:
            command: Comando principal
            args: Argumentos do comando
            cwd: Diretório de trabalho
            
        Returns:
            AdapterResponse com saída do comando
        """
        full_cmd = [command] + args
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd or self.project_dir
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=60.0
            )
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            text = output if proc.returncode == 0 else f"{output}\n{error}"
            
            return AdapterResponse(
                text=text.strip(),
                exit_code=proc.returncode,
                command_executed=" ".join(full_cmd)
            )
            
        except asyncio.TimeoutError:
            return AdapterResponse(
                text="Timeout executando comando",
                exit_code=-1,
                command_executed=" ".join(full_cmd)
            )
        except Exception as e:
            return AdapterResponse(
                text=f"Erro: {e}",
                exit_code=-1,
                command_executed=" ".join(full_cmd)
            )
    
    async def project_to_cogon(self, text: str) -> Cogon:
        """Projeta texto em COGON.
        
        Args:
            text: Texto a projetar
            
        Returns:
            COGON com sem[32] e unc[32]
        """
        sem, unc = await self.projector.project(text)
        return Cogon.new(sem=sem, unc=unc)
    
    def compute_delta(self, prev: Cogon, curr: Cogon) -> list[float]:
        """Computa delta entre dois COGONs.
        
        Args:
            prev: COGON anterior
            curr: COGON atual
            
        Returns:
            Vetor de diferença (32 dimensões)
        """
        from leet import delta
        return delta(prev, curr)
    
    def get_convergence_score(self) -> float:
        """Computa score de convergência da sessão.
        
        Retorna média das distâncias entre COGONs consecutivos.
        Valor baixo = conversação convergiu.
        """
        if len(self._session_cogons) < 2:
            return 1.0
        
        distances = []
        for i in range(1, len(self._session_cogons)):
            d = dist(self._session_cogons[i-1], self._session_cogons[i])
            distances.append(d)
        
        return sum(distances) / len(distances)
    
    def clear_history(self):
        """Limpa histórico de mensagens."""
        self._history.clear()
        self._session_cogons.clear()
    
    def _add_to_history(self, response: AdapterResponse):
        """Adiciona resposta ao histórico."""
        self._history.append(response)
        if response.cogon:
            self._session_cogons.append(response.cogon)


class ToolNotFoundError(Exception):
    """Exceção quando a ferramenta IDE não está instalada."""
    pass


class AdapterError(Exception):
    """Exceção genérica de adaptador."""
    pass
