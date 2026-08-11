"""Claude Code Adapter — Integration with Anthropic's CLI.

Claude Code is Anthropic's official tool for coding with Claude.
Documentation: https://docs.anthropic.com/claude/docs/claude-code
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
    """Adapter for Claude Code (Anthropic's CLI).

    Claude Code enables interacting with Claude directly from the terminal,
    with access to the filesystem, git, and command execution.

    Supported features:
        - Interactive chat via CLI
        - Non-interactive mode (--output)
        - Automatic file context
        - Git integration
        - Sandboxed command execution

    Example:
        >>> adapter = ClaudeCodeAdapter(project_dir="/path/to/project")
        >>> if adapter.is_available():
        ...     resp = await adapter.send_message("Explain this code")
        ...     print(resp.text)

    Configuration:
        The CLI uses the ANTHROPIC_API_KEY variable or looks in ~/.anthropic/.
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
        """Initializes the Claude Code adapter.

        Args:
            project_dir: Project directory (required)
            api_key: Anthropic API key (optional, uses env)
            model: Claude model to use
            auto_accept: If True, automatically accepts suggestions
            verbose: Verbose mode for debugging
        """
        super().__init__(project_dir=project_dir, **kwargs)
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.auto_accept = auto_accept
        self.verbose = verbose

        # Check whether a project is configured
        self._check_project()

    def _check_project(self):
        """Checks whether the project directory is valid."""
        if self.project_dir and not Path(self.project_dir).exists():
            raise ValueError(f"Project directory does not exist: {self.project_dir}")

    def is_available(self) -> bool:
        """Checks whether the 'claude' CLI is installed.

        Returns:
            True if the claude command is on the PATH
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
        """Builds the claude command with arguments.

        Args:
            message: Message for Claude
            context: Optional context
            files: Specific files to include

        Returns:
            List of arguments for subprocess
        """
        cmd = ["claude"]

        # Non-interactive mode (captures output)
        cmd.append("--output")

        # Model
        cmd.extend(["--model", self.model])

        # Project directory
        if self.project_dir:
            cmd.extend(["--cwd", self.project_dir])

        # Context files
        if context and context.file_path:
            cmd.extend(["--file", context.file_path])

        if files:
            for f in files:
                cmd.extend(["--file", f])

        # Auto-accept (dangerous, use with caution)
        if self.auto_accept:
            cmd.append("--yes")

        # Message
        cmd.append(message)

        return cmd

    async def send_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        files: Optional[list[str]] = None,
        **kwargs
    ) -> AdapterResponse:
        """Sends a message to Claude Code.

        Args:
            message: Message text
            context: Context with file/selection
            files: Additional files for context

        Returns:
            AdapterResponse with text and metadata

        Raises:
            ToolNotFoundError: If claude is not installed
        """
        if not self.is_available():
            raise ToolNotFoundError(
                "Claude Code not found. "
                "Install: https://docs.anthropic.com/claude/docs/claude-code"
            )

        cmd = self._build_command(message, context, files)

        # Execute command
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

            # Claude Code returns 0 even with warnings
            success = proc.returncode == 0
            text = output if success else f"{output}\n{error}"

            # Extract modified files from the output
            files_modified = self._extract_file_changes(text)

            # Project response into a COGON if auto_project is enabled
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
                text="Timeout: Claude Code took longer than 120s",
                exit_code=-1,
                command_executed=" ".join(cmd)
            )
        except Exception as e:
            return AdapterResponse(
                text=f"Error running Claude Code: {e}",
                exit_code=-1,
                command_executed=" ".join(cmd)
            )

    async def stream_message(
        self,
        message: str,
        context: Optional[AdapterContext] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Streams a response from Claude Code.

        NOTE: Claude Code does not support native streaming in --output mode.
        This implementation simulates streaming line by line.

        Yields:
            Lines of the output
        """
        response = await self.send_message(message, context, **kwargs)

        # Simulate streaming line by line
        for line in response.text.split('\n'):
            yield line + '\n'
            await __import__('asyncio').sleep(0.01)  # Simulate delay

    def _extract_file_changes(self, output: str) -> list[str]:
        """Extracts the list of modified files from the output.

        Claude Code indicates changes with patterns such as:
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
        """Shows a diff of changes proposed by Claude.

        Args:
            target: Diff target (HEAD, staged, etc)

        Returns:
            AdapterResponse with the diff
        """
        return await self.execute_command(
            "git",
            ["diff", target],
            cwd=self.project_dir
        )

    async def accept_changes(self) -> AdapterResponse:
        """Accepts proposed changes (when auto_accept=False).

        Returns:
            AdapterResponse with the result
        """
        # Claude Code has no explicit "accept" command
        # Changes are already applied automatically
        return AdapterResponse(
            text="Changes already applied. Use git to manage them."
        )

    async def reject_changes(self) -> AdapterResponse:
        """Rejects proposed changes.

        Returns:
            AdapterResponse with the git checkout result
        """
        return await self.execute_command(
            "git",
            ["checkout", "--", "."],
            cwd=self.project_dir
        )

    def get_config(self) -> dict[str, Any]:
        """Returns the adapter's current configuration."""
        return {
            "name": self.name,
            "version": self.get_version(),
            "model": self.model,
            "project_dir": self.project_dir,
            "auto_accept": self.auto_accept,
            "available": self.is_available(),
        }
