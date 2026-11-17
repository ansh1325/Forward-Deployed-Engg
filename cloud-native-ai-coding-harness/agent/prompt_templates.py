"""
Prompt Templates & Reasoning Directives for Coding Agent
"""

SYSTEM_PROMPT = """You are an Autonomous Cloud-Native SWE Agent.
Your objective is to inspect a repository, diagnose bug reports, apply surgical file edits, and ensure all test suites pass.

OPERATIONAL PRINCIPLES:
1. Always analyze repository AST and relevant files first.
2. Formulate a precise hypothesis before making edits.
3. Make minimal, surgical edits. Do not refactor unrelated code.
4. Execute test suites to verify that your changes fix the bug without introducing regressions.
5. If tests fail, read the traceback carefully, deduce the flaw, and iterate until green.
"""

ANALYSIS_PROMPT_TEMPLATE = """Task Description:
{task_description}

Top Candidate Files Identified by AST Analyzer:
{candidate_files_summary}

Please provide your step-by-step diagnostic plan:
1. Root cause hypothesis
2. Specific files to read/edit
3. Verification command to run
"""

REPAIR_ITERATION_PROMPT = """Previous test run FAILED with the following output:
```
{test_output}
```

Current file contents for {file_path}:
```python
{file_content}
```

Please identify why the test failed and specify the exact edit replacement needed to pass the tests.
"""
