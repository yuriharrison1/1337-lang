"""Aider Adapter — Integration with Aider (multi-LLM coding assistant).

Aider is a popular tool that lets you edit code in parallel with LLMs,
supporting multiple models (GPT-4, Claude, etc).
Documentation: https://aider.chat/
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
    """Adapter for Aider.

    Aider is unique because:
    - Supports multiple LLMs (OpenAI, Anthropic, OpenRouter, etc)
    - Edits files directly in the editor
    - Automatic git integration
    - Repository map for context
    - Automatic test support

    Features:
        - Chat with file context
        - Direct code editing
        - Automatic commits
        - Tests (pytest, etc)

    Example:
        >>> adapter = AiderAdapter(
        ...     project_dir="/path",
        ...     model="gpt-4o",
        ...     auto_commit=True
        ... )
        >>> resp = await adapter.send_message("Add email validation")

    Configuration:
        Requires OPENAI_API_KEY, ANTHROPIC_API_KEY, or another key
        depending on the chosen model.
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
        """Initializes the Aider adapter.

        Args:
            project_dir: Project directory (required)
            model: Main model
            editor_model: Model for edits (default=model)
            weak_model: Model for simple tasks
            auto_commit: Automatic commit after changes
            test_cmd: Command to run tests
            lint_cmd: Command for linting
        """
        super().__init__(project_dir=project_dir, **kwargs)
        self.model = model
        self.editor_model = editor_model or model
        self.weak_model = weak_model
        self.auto_commit = auto_commit
        self.test_cmd = test_cmd
        self.lint_cmd = lint_cmd

        if not self.project_dir:
            raise ValueError("Aider requires project_dir")

        self._check_project()

    def _check_project(self):
        """Checks whether the project directory is valid."""
        if not Path(self.project_dir).exists():
            raise ValueError(f"Project directory does not exist: {self.project_dir}")

        # Check whether it is a git repo (recommended)
        git_dir = Path(self.project_dir) / ".git"
        self.is_git_repo = git_dir.exists()

    def is_available(self) -> bool:
        """Checks whether 'aider' is installed."""
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
        """Builds the aider command with arguments."""
        cmd = ["aider"]

        # Models
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

        # Test/lint commands
        if self.test_cmd:
            cmd.extend(["--test-cmd", self.test_cmd])
        if self.lint_cmd:
            cmd.extend(["--lint-cmd", self.lint_cmd])

        # Message
        cmd.extend(["--message", message])

        # Files to edit
        if files:
            for f in files:
                cmd.append(f)

        # Read-only files (context)
        if read_only:
            for f in read_only:
                cmd.extend(["--read", f])

        # Context file
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
        """Sends a message to Aider.

        Args:
            message: Message text
            context: Context
            files: Files to edit
            read_only: Read-only files (context)

        Returns:
            AdapterResponse
        """
        if not self.is_available():
            raise ToolNotFoundError(
                "Aider not found. "
                "Install: pip install aider-chat"
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
                timeout=180.0  # Aider can take longer
            )

            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""

            success = proc.returncode == 0
            text = output if success else f"{output}\n{error}"

            # Extract modified files
            files_modified = self._extract_file_changes(text)

            # Detect commits
            commits = self._extract_commits(text)

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
                text="Timeout: Aider took longer than 180s",
                exit_code=-1
            )
        except Exception as e:
            return AdapterResponse(
                text=f"Error running Aider: {e}",
                exit_code=-1
            )

    async def add_files(self, files: list[str]) -> AdapterResponse:
        """Adds files to Aider's context.

        Args:
            files: List of file paths

        Returns:
            AdapterResponse
        """
        cmd = ["aider", "--add"] + files
        return await self.execute_command(cmd[0], cmd[1:], cwd=self.project_dir)

    async def drop_files(self, files: list[str]) -> AdapterResponse:
        """Removes files from Aider's context."""
        cmd = ["aider", "--drop"] + files
        return await self.execute_command(cmd[0], cmd[1:], cwd=self.project_dir)

    async def lint(self) -> AdapterResponse:
        """Runs linting on the modified files."""
        if not self.lint_cmd:
            return AdapterResponse(
                text="Lint not configured. Set lint_cmd."
            )
        return await self.send_message("/lint")

    async def test(self) -> AdapterResponse:
        """Runs tests."""
        if not self.test_cmd:
            return AdapterResponse(
                text="Tests not configured. Set test_cmd."
            )
        return await self.send_message("/test")

    async def commit(self, message: Optional[str] = None) -> AdapterResponse:
        """Commits the changes.

        Args:
            message: Commit message (optional)
        """
        if message:
            return await self.send_message(f"/commit {message}")
        return await self.send_message("/commit")

    async def undo(self) -> AdapterResponse:
        """Undoes the last change."""
        return await self.send_message("/undo")

    async def reset(self) -> AdapterResponse:
        """Resets to the last commit."""
        return await self.send_message("/reset")

    def _extract_file_changes(self, output: str) -> list[str]:
        """Extracts modified files from Aider's output."""
        files = []

        # Aider patterns
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
        """Extracts commit hashes."""
        commits = []
        pattern = r'(?:commit|committed)\s+([a-f0-9]{7,40})'
        for match in re.finditer(pattern, output, re.IGNORECASE):
            commits.append(match.group(1))
        return commits

    def get_repo_map(self) -> AdapterResponse:
        """Gets the repository map.

        Runs aider --show-repo-map to view the context.
        """
        return self.execute_command(
            "aider",
            ["--show-repo-map"],
            cwd=self.project_dir
        )

    def get_config(self) -> dict[str, Any]:
        """Returns the current configuration."""
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
