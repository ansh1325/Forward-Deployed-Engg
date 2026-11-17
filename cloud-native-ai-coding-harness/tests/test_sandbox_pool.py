import pytest
import asyncio
import time
from pathlib import Path
from sandbox.manager import PrewarmedSandboxPool

SAMPLE_REPO_DIR = Path(__file__).resolve().parent.parent / "benchmarks" / "sample_repo"


@pytest.mark.asyncio
async def test_prewarmed_pool_startup_latency():
    pool = PrewarmedSandboxPool(warm_target=3, max_concurrent=10)
    await pool.start()

    try:
        assert pool.warm_pool.qsize() == 3

        start_time = time.perf_counter()
        sandbox = await pool.acquire_sandbox(
            repo_name="sample_repo",
            source_repo_path=SAMPLE_REPO_DIR
        )
        elapsed_seconds = time.perf_counter() - start_time

        # SLA Guarantee: Startup must be strictly under 5 seconds
        assert elapsed_seconds < 5.0, f"Startup took {elapsed_seconds}s which violates <5s SLA"
        assert sandbox.workspace_path.exists()
        assert (sandbox.workspace_path / "app" / "calculator.py").exists()

        # Clean release
        await pool.release_sandbox(sandbox)

    finally:
        await pool.stop()
