"""
Sandboxed Agent Tools Interface
Provides tools for file inspection, surgical edits, and test command execution.
"""
from typing import Dict, Any, Optional
from sandbox.container_runner import SandboxEnvironment, SandboxExecutionResult


class AgentToolbox:
    """
    Wraps sandbox capabilities into safe, structured agent tools.
    """

    def __init__(self, sandbox: SandboxEnvironment):
        self.sandbox = sandbox

    def read_file(self, relative_path: str) -> str:
        """Reads the full content of a file within the sandbox."""
        return self.sandbox.read_file(relative_path)

    def write_file(self, relative_path: str, content: str) -> None:
        """Writes content to a file inside the sandbox."""
        self.sandbox.write_file(relative_path, content)

    def edit_file(self, relative_path: str, target: str, replacement: str) -> str:
        """Replaces exact target string with replacement inside a file."""
        self.sandbox.edit_file(relative_path, target, replacement)
        return f"Successfully updated {relative_path}"

    async def run_bash(self, command: str) -> SandboxExecutionResult:
        """Runs a bash command inside the sandbox."""
        return await self.sandbox.execute_command(command)

    async def run_pytest(self, test_path: str = "tests") -> SandboxExecutionResult:
        """Runs pytest on the test path."""
        cmd = f"python -m pytest {test_path} -v --tb=short"
        return await self.sandbox.execute_command(cmd)
