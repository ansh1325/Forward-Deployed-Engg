import pytest
from pathlib import Path
from agent.analyzer import RepoAnalyzer

SAMPLE_REPO_DIR = Path(__file__).resolve().parent.parent / "benchmarks" / "sample_repo"


def test_repo_analyzer_parses_symbols():
    analyzer = RepoAnalyzer(SAMPLE_REPO_DIR)
    repo_map = analyzer.analyze_workspace("surcharge calculator")

    assert repo_map.total_files >= 2
    assert any("calculator.py" in path for path in repo_map.files)
    
    # Candidate ranking should place app/calculator.py in candidate files
    calc_path = [p for p in repo_map.top_candidate_files if "app/calculator.py" in p or p.endswith("calculator.py") and "test" not in p]
    assert len(calc_path) > 0

    calc_analysis = repo_map.files[calc_path[0]]
    func_names = [s.name for s in calc_analysis.symbols]
    assert "compute_dynamic_freight_surcharge" in func_names
    assert "calculate_temperature_decay" in func_names
