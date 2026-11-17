"""
Sandbox Execution Runner
Executes commands, tests, and file operations inside an isolated sandbox environment.
"""
import os
import sys
import subprocess
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Optional, AsyncIterator
from pydantic import BaseModel


class SandboxExecutionResult(BaseModel):
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False


class SandboxEnvironment:
    """
    Represents an isolated agent workspace sandbox.
    Supports asynchronous execution, output streaming, and timeout limits.
    """

    def __init__(self, sandbox_id: str, workspace_path: Path, timeout_seconds: int = 60):
        self.sandbox_id = sandbox_id
        self.workspace_path = Path(workspace_path).resolve()
        self.timeout_seconds = timeout_seconds
        self.workspace_path.mkdir(parents=True, exist_ok=True)

    def write_file(self, relative_path: str, content: str) -> None:
        """Writes content to a file inside the isolated sandbox."""
        target_path = (self.workspace_path / relative_path).resolve()
        # Security check: Prevent path traversal outside workspace
        if not str(target_path).startswith(str(self.workspace_path)):
            raise PermissionError(f"Path traversal security block: {relative_path}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

    def read_file(self, relative_path: str) -> str:
        """Reads content of a file inside the isolated sandbox."""
        target_path = (self.workspace_path / relative_path).resolve()
        if not str(target_path).startswith(str(self.workspace_path)):
            raise PermissionError(f"Path traversal security block: {relative_path}")
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        with open(target_path, "r", encoding="utf-8") as f:
            return f.read()

    def edit_file(self, relative_path: str, target: str, replacement: str) -> None:
        """Replaces exact target string with replacement inside a file."""
        content = self.read_file(relative_path)
        content_norm = content.replace("\r\n", "\n")
        target_norm = target.replace("\r\n", "\n")
        replacement_norm = replacement.replace("\r\n", "\n")
        if target_norm not in content_norm:
            raise ValueError(f"Target string not found in {relative_path}")
        new_content = content_norm.replace(target_norm, replacement_norm, 1)
        self.write_file(relative_path, new_content)

    async def execute_command(self, cmd: str) -> SandboxExecutionResult:
        """
        Executes a shell command inside the sandbox workspace asynchronously.
        """
        start_time = time.perf_counter()
        timed_out = False

        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.workspace_path)
        # Prevent interactive prompts
        env["DEBIAN_FRONTEND"] = "noninteractive"
        env["CI"] = "true"

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(self.workspace_path),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout_seconds
                )
                stdout = stdout_data.decode("utf-8", errors="replace")
                stderr = stderr_data.decode("utf-8", errors="replace")
                exit_code = process.returncode or 0
            except asyncio.TimeoutError:
                process.kill()
                stdout = ""
                stderr = f"Command timed out after {self.timeout_seconds} seconds."
                exit_code = 124
                timed_out = True

        except Exception as e:
            stdout = ""
            stderr = f"Sandbox execution failure: {str(e)}"
            exit_code = 1

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return SandboxExecutionResult(
            command=cmd,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=round(duration_ms, 2),
            timed_out=timed_out
        )

    async def execute_command_stream(self, cmd: str) -> AsyncIterator[str]:
        """Streams terminal output line-by-line for real-time control plane UI."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.workspace_path)
        env["PYTHONUNBUFFERED"] = "1"

        process = await asyncio.create_subprocess_shell(
            cmd,
            cwd=str(self.workspace_path),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env
        )

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace")

        await process.wait()
