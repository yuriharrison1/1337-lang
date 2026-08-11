"""Codex Adapter — Integration with OpenAI Codex CLI.

Codex is OpenAI's coding tool based on GPT-4.
Documentation: https://github.com/openai/codex
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
    """Adapter for OpenAI Codex CLI.

    Codex is a coding agent that can:
    - Read and edit files
    - Execute terminal commands
    - Use tools (git, grep, etc)
    - Work in sandboxed mode

    Supported features:
        - Interactive chat
        - Approval mode (full, suggest, none)
        - Directory context
        - Command execution

    Example:
        >>> adapter = CodexAdapter(project_dir="/path/to/project")
        >>> if adapter.is_available():
        ...     resp = await adapter.send_message("Refactor this function")
        ...     print(resp.text)

    Configuration:
        Requires OPENAI_API_KEY in the environment.
    """

    name = "codex"
    version_command = ("codex", "--version")

    # Codex approval modes
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
        """Initializes the Codex adapter.

        Args:
            project_dir: Project directory
            api_key: OpenAI API key (optional, uses env)
            model: Model (gpt-4o, o3-mini, etc)
            approval_mode: full/suggest/none
            timeout: Timeout in seconds
        """
        super().__init__(project_dir=project_dir, **kwargs)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.approval_mode = approval_mode
        self.timeout = timeout

        if approval_mode not in self.APPROVAL_MODES:
            raise ValueError(f"approval_mode must be one of: {self.APPROVAL_MODES}")

        self._check_project()

    def _check_project(self):
        """Checks whether the project directory is valid."""
        if self.project_dir and not Path(self.project_dir).exists():
            raise ValueError(f"Project directory does not exist: {self.project_dir}")

    def is_available(self) -> bool:
        """Checks whether the 'codex' CLI is installed."""
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
        """Builds the codex command with arguments."""
        cmd = ["codex"]

        # Model
        cmd.extend(["--model", self.model])

        # Approval mode
        cmd.extend(["--approval-mode", self.approval_mode])

        # Quiet mode (less status output)
        cmd.append("--quiet")

        # Image (if any)
        if image_paths:
            for img in image_paths:
                cmd.extend(["--image", img])

        # Message
        cmd.append(message)

        return cmd

    async def send_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        image_paths: Optional[list[str]] = None,
        **kwargs
    ) -> AdapterResponse:
        """Sends a message to Codex.

        Args:
            message: Message text
            context: Context with file/selection
            image_paths: Image paths for analysis

        Returns:
            AdapterResponse

        Raises:
            ToolNotFoundError: If codex is not installed
        """
        if not self.is_available():
            raise ToolNotFoundError(
                "Codex not found. "
                "Install: https://github.com/openai/codex"
            )

        if not self.api_key:
            raise ToolNotFoundError(
                "OPENAI_API_KEY not configured"
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

            # Extract modified files
            files_modified = self._extract_file_changes(text)

            # Project into COGON
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
                text=f"Timeout: Codex took longer than {self.timeout}s",
                exit_code=-1,
                command_executed=" ".join(cmd)
            )
        except Exception as e:
            return AdapterResponse(
                text=f"Error running Codex: {e}",
                exit_code=-1,
                command_executed=" ".join(cmd)
            )

    async def stream_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Streams a response from Codex.

        Codex does not support native streaming in quiet mode.
        Simulates it line by line.
        """
        response = await self.send_message(message, context, **kwargs)

        for line in response.text.split('\n'):
            yield line + '\n'
            await __import__('asyncio').sleep(0.01)

    def _extract_file_changes(self, output: str) -> list[str]:
        """Extracts modified files from Codex output."""
        files = []

        # Common Codex patterns
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
        """Requests a review of the current changes.

        Returns:
            AdapterResponse with Codex's analysis
        """
        return await self.send_message(
            "Review the changes made and explain what was changed "
            "and why. List the modified files."
        )

    async def explain_file(self, file_path: str) -> AdapterResponse:
        """Requests an explanation of a specific file.

        Args:
            file_path: File path

        Returns:
            AdapterResponse with the explanation
        """
        context = AdapterContext(file_path=file_path)
        return await self.send_message(
            f"Explain the file {file_path} in detail. "
            "Include: purpose, structure, and important points.",
            context=context
        )

    async def suggest_tests(self, file_path: str) -> AdapterResponse:
        """Requests test suggestions for a file.

        Args:
            file_path: File path

        Returns:
            AdapterResponse with suggested tests
        """
        context = AdapterContext(file_path=file_path)
        return await self.send_message(
            f"Suggest unit tests for {file_path}. "
            "Include edge cases and necessary mocks.",
            context=context
        )

    def get_config(self) -> dict[str, Any]:
        """Returns the current configuration."""
        return {
            "name": self.name,
            "version": self.get_version(),
            "model": self.model,
            "approval_mode": self.approval_mode,
            "project_dir": self.project_dir,
            "available": self.is_available(),
        }
