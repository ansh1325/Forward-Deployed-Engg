import pytest
import asyncio
from pathlib import Path
from sandbox.manager import PrewarmedSandboxPool
from agent.loop import AutonomousExecutionLoop, AgentLoopResult

SAMPLE_REPO_DIR = Path(__file__).resolve().parent.parent / "benchmarks" / "sample_repo"


@pytest.mark.asyncio
async def test_autonomous_execution_loop_solves_benchmark():
    pool = PrewarmedSandboxPool(warm_target=2, max_concurrent=5)
    await pool.start()

    try:
        sandbox = await pool.acquire_sandbox(
            repo_name="sample_repo",
            source_repo_path=SAMPLE_REPO_DIR
        )

        events_received = []

        async def capture_event(evt):
            events_received.append(evt)

        loop = AutonomousExecutionLoop(
            sandbox=sandbox,
            task_id="test-task-1",
            task_description="Fix freight surcharge weight threshold in calculator.py and temperature decay validation",
            max_iterations=3,
            event_callback=capture_event
        )

        res: AgentLoopResult = await loop.run()

        # The loop must pass tests and produce valid patch
        assert res.tests_passed is True
        assert res.status == "RESOLVED"
        assert res.patch_summary is not None
        assert len(res.patch_summary.files_changed) > 0
        assert len(events_received) > 0

        # Verify event stream types
        event_types = {e.event_type for e in events_received}
        assert "thought" in event_types
        assert "terminal" in event_types
        assert "diff" in event_types

        await pool.release_sandbox(sandbox)

    finally:
        await pool.stop()
