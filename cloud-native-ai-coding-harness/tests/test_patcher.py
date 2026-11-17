import pytest
from agent.patcher import PatchGenerator


def test_patch_generator_unified_diff():
    original = "def add(a, b):\n    return a - b\n"
    modified = "def add(a, b):\n    return a + b\n"

    diff = PatchGenerator.compute_diff(original, modified, "math_utils.py")
    assert "-    return a - b" in diff
    assert "+    return a + b" in diff

    patch = PatchGenerator.generate_patch(
        original_files={"math_utils.py": original},
        modified_files={"math_utils.py": modified},
        task_title="Fix subtraction in add"
    )

    assert patch.files_changed == ["math_utils.py"]
    assert patch.insertions == 1
    assert patch.deletions == 1
    assert "fix(agent): Fix subtraction in add" in patch.pr_title
