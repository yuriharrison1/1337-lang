"""Base classes for IDE adapters.

Defines the common interface that all adapters must implement.
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
    """Role of a message in the conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class AdapterContext:
    """Context for an interaction with the adapter.

    Attributes:
        file_path: Current file being edited
        project_dir: Project root directory
        selection: Text selected in the editor
        line_number: Current cursor line
        column: Current cursor column
        language: Detected programming language
        git_branch: Current git branch
        git_commit: Current commit hash
        env_vars: Relevant environment variables
        metadata: Additional metadata
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
        """Creates a context from VS Code data."""
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
        """Creates a context from Neovim data."""
        return cls(
            file_path=data.get('file'),
            selection=data.get('selection'),
            line_number=data.get('line'),
            column=data.get('col'),
        )

    def to_cogon_projection(self) -> tuple[list[float], list[float]]:
        """Converts the context into a semantic projection (sem, unc).

        Returns values based on the context type:
        - Code → high A9_PROCESSO, C9_NATUREZA verb
        - File → high A8_ESTADO
        - Git → B2_TEMPORALIDADE, B7_ORIGEM
        """
        sem = [0.5] * 32
        unc = [0.3] * 32

        # A8_ESTADO — configurational
        if self.file_path:
            sem[8] = 0.8  # A8_ESTADO
            unc[8] = 0.1

        # A9_PROCESSO — transformation
        if self.selection:
            sem[9] = 0.7  # A9_PROCESSO
            sem[30] = 0.6  # C9_NATUREZA (verb)
            unc[9] = 0.15

        # B2_TEMPORALIDADE — temporal anchor
        if self.git_branch or self.git_commit:
            sem[15] = 0.75  # B2_TEMPORALIDADE
            unc[15] = 0.1

        return sem, unc


@dataclass
class AdapterResponse:
    """Response from an IDE adapter.

    Attributes:
        text: Response text
        cogon: Semantic representation of the response
        role: Message role
        files_modified: Files modified by the action
        exit_code: Exit code (0 = success)
        command_executed: Command that was executed
        metadata: Additional metadata
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
        """Returns True if the operation succeeded."""
        return self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        """Serializes to a dictionary."""
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
    """Base class for all IDE adapters.

    All adapters must implement:
    - send_message: Send a message and receive a response
    - is_available: Check whether the tool is installed
    - get_version: Get the tool's version

    Optionally, they may override:
    - stream_message: Response streaming
    - execute_command: Execution of specific commands
    - project_to_cogon: Custom semantic projection
    """

    # Adapter name (should be overridden)
    name: str = "base"

    # Command used to check installation
    version_command: tuple[str, ...] = ()

    def __init__(
        self,
        projector: Optional[SemanticProjector] = None,
        project_dir: Optional[str] = None,
        auto_project: bool = True,
    ):
        """Initializes the adapter.

        Args:
            projector: Semantic projector (None = MockProjector)
            project_dir: Project root directory
            auto_project: If True, projects every message into COGONs
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
        """Sends a message to the IDE tool.

        Args:
            message: Message text
            context: Optional context (file, selection, etc)
            **kwargs: Additional adapter-specific arguments

        Returns:
            AdapterResponse with the result
        """
        pass

    async def stream_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Streams a response from the IDE tool.

        Yields:
            Text chunks of the response

        Default: accumulates everything and yields once.
        Adapters should override this for true streaming.
        """
        response = await self.send_message(message, context, **kwargs)
        yield response.text

    @abstractmethod
    def is_available(self) -> bool:
        """Checks whether the IDE tool is installed and accessible.

        Returns:
            True if available, False otherwise
        """
        pass

    def get_version(self) -> Optional[str]:
        """Gets the IDE tool's version.

        Returns:
            Version string or None if unavailable
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
        """Executes a command directly on the tool.

        Args:
            command: Main command
            args: Command arguments
            cwd: Working directory

        Returns:
            AdapterResponse with the command's output
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
                text="Timeout executing command",
                exit_code=-1,
                command_executed=" ".join(full_cmd)
            )
        except Exception as e:
            return AdapterResponse(
                text=f"Error: {e}",
                exit_code=-1,
                command_executed=" ".join(full_cmd)
            )

    async def project_to_cogon(self, text: str) -> Cogon:
        """Projects text into a COGON.

        Args:
            text: Text to project

        Returns:
            COGON with sem[32] and unc[32]
        """
        sem, unc = await self.projector.project(text)
        return Cogon.new(sem=sem, unc=unc)

    def compute_delta(self, prev: Cogon, curr: Cogon) -> list[float]:
        """Computes the delta between two COGONs.

        Args:
            prev: Previous COGON
            curr: Current COGON

        Returns:
            Difference vector (32 dimensions)
        """
        from leet import delta
        return delta(prev, curr)

    def get_convergence_score(self) -> float:
        """Computes the session's convergence score.

        Returns the average distance between consecutive COGONs.
        Low value = conversation converged.
        """
        if len(self._session_cogons) < 2:
            return 1.0

        distances = []
        for i in range(1, len(self._session_cogons)):
            d = dist(self._session_cogons[i-1], self._session_cogons[i])
            distances.append(d)

        return sum(distances) / len(distances)

    def clear_history(self):
        """Clears the message history."""
        self._history.clear()
        self._session_cogons.clear()

    def _add_to_history(self, response: AdapterResponse):
        """Adds a response to the history."""
        self._history.append(response)
        if response.cogon:
            self._session_cogons.append(response.cogon)


class ToolNotFoundError(Exception):
    """Exception raised when the IDE tool is not installed."""
    pass


class AdapterError(Exception):
    """Generic adapter exception."""
    pass
