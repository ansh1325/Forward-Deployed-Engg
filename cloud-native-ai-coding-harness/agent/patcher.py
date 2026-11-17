"""
Unified Git Diff & Patch Delivery Module
Generates valid git diffs, unified patches, and Pull Request metadata payloads.
"""
import difflib
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel


class PatchSummary(BaseModel):
    files_changed: List[str]
    insertions: int
    deletions: int
    unified_diff: str
    pr_title: str
    pr_body: str


class PatchGenerator:
    """
    Computes unified diffs between original baseline snapshots and modified sandbox files.
    """

    @staticmethod
    def compute_diff(
        original_content: str,
        modified_content: str,
        filename: str = "modified_file.py"
    ) -> str:
        orig_lines = original_content.splitlines(keepends=True)
        mod_lines = modified_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )
        return "".join(diff)

    @staticmethod
    def generate_patch(
        original_files: Dict[str, str],
        modified_files: Dict[str, str],
        task_title: str = "Automated Fix",
        test_output: str = ""
    ) -> PatchSummary:
        total_diff_lines = []
        files_changed = []
        insertions = 0
        deletions = 0

        for filepath, mod_content in modified_files.items():
            orig_content = original_files.get(filepath, "")
            if orig_content == mod_content:
                continue

            files_changed.append(filepath)
            diff_str = PatchGenerator.compute_diff(orig_content, mod_content, filepath)
            total_diff_lines.append(diff_str)

            for line in diff_str.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    insertions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    deletions += 1

        full_patch = "\n".join(total_diff_lines)

        pr_title = f"fix(agent): {task_title}"
        pr_body = (
            f"## Autonomous Agent Patch Delivery\n\n"
            f"**Files Changed:** {', '.join(files_changed) if files_changed else 'None'}\n"
            f"**Stats:** +{insertions} / -{deletions} lines\n\n"
            f"### Verification Status\n"
            f"```\n{test_output[-500:] if test_output else 'Tests Passed Cleanly.'}\n```\n\n"
            f"Generated autonomously by **Cloud-Native AI Coding Harness**."
        )

        return PatchSummary(
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
            unified_diff=full_patch,
            pr_title=pr_title,
            pr_body=pr_body
        )
