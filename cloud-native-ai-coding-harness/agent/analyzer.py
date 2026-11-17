"""
Repository AST Analyzer & Context Gathering Engine
Parses repository symbols, dependencies, and file structures to identify root cause locations.
"""
import ast
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class SymbolDefinition(BaseModel):
    name: str
    symbol_type: str  # 'function', 'class', 'method'
    line_number: int
    docstring: Optional[str] = None
    args: List[str] = []


class FileAnalysis(BaseModel):
    file_path: str
    symbols: List[SymbolDefinition] = []
    imports: List[str] = []
    line_count: int


class RepoMap(BaseModel):
    total_files: int
    files: Dict[str, FileAnalysis] = {}
    top_candidate_files: List[str] = []


class RepoAnalyzer:
    """
    Parses workspace files, extracts Abstract Syntax Trees (ASTs),
    and scores files for relevance against a task description.
    """

    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)

    def analyze_workspace(self, task_query: str = "") -> RepoMap:
        repo_map = RepoMap(total_files=0)
        query_tokens = set(task_query.lower().replace("_", " ").split())

        for root, _, files in os.walk(self.workspace_path):
            for file in files:
                if not file.endswith(".py"):
                    continue
                if any(ignored in root for ignored in [".git", "__pycache__", ".venv", "venv"]):
                    continue

                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(self.workspace_path)).replace("\\", "/")

                file_info = self._analyze_python_file(full_path, rel_path)
                repo_map.files[rel_path] = file_info
                repo_map.total_files += 1

        # Score candidate files based on keyword overlap in symbols and docstrings
        scored_files = []
        for path, finfo in repo_map.files.items():
            score = 0
            # Test files get lower direct priority for edits unless task is test-specific
            if "test" in path.lower():
                score -= 2

            for sym in finfo.symbols:
                sym_tokens = set(sym.name.lower().replace("_", " ").split())
                if sym_tokens & query_tokens:
                    score += 5
                if sym.docstring:
                    doc_tokens = set(sym.docstring.lower().split())
                    score += len(doc_tokens & query_tokens) * 2

            scored_files.append((score, path))

        scored_files.sort(key=lambda x: x[0], reverse=True)
        repo_map.top_candidate_files = [path for _, path in scored_files[:5]]

        return repo_map

    def _analyze_python_file(self, file_path: Path, rel_path: str) -> FileAnalysis:
        symbols: List[SymbolDefinition] = []
        imports: List[str] = []
        line_count = 0

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                code = f.read()
            line_count = len(code.splitlines())

            tree = ast.parse(code, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    args = [arg.arg for arg in node.args.args]
                    symbols.append(SymbolDefinition(
                        name=node.name,
                        symbol_type="function",
                        line_number=node.lineno,
                        docstring=ast.get_docstring(node),
                        args=args
                    ))
                elif isinstance(node, ast.ClassDef):
                    symbols.append(SymbolDefinition(
                        name=node.name,
                        symbol_type="class",
                        line_number=node.lineno,
                        docstring=ast.get_docstring(node),
                        args=[]
                    ))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for alias in node.names:
                        imports.append(f"{mod}.{alias.name}")

        except Exception:
            pass

        return FileAnalysis(
            file_path=rel_path,
            symbols=symbols,
            imports=imports,
            line_count=line_count
        )
