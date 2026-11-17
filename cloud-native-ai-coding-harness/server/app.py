"""
FastAPI Server & Real-time Event Streaming Engine
Supports 100+ concurrent agents and streams SSE execution traces, terminal stdout, and diffs.
"""
import os
import uuid
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from sandbox.manager import PrewarmedSandboxPool
from agent.loop import AutonomousExecutionLoop, LoopEvent, AgentLoopResult
from .models import CreateTaskRequest, AgentTaskResponse, EventMessage
from .telemetry import telemetry

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_SAMPLE_DIR = PROJECT_ROOT / "benchmarks" / "sample_repo"

# In-memory storage for active tasks and their live event queues
sandbox_pool: Optional[PrewarmedSandboxPool] = None
task_store: Dict[str, Dict[str, Any]] = {}
event_queues: Dict[str, List[asyncio.Queue]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sandbox_pool
    sandbox_pool = PrewarmedSandboxPool(warm_target=5, max_concurrent=120)
    await sandbox_pool.start()
    yield
    await sandbox_pool.stop()


app = FastAPI(
    title="Cloud-Native AI Coding Harness",
    description="High-concurrency cloud coding-agent harness with pre-warmed sandboxes and streaming control plane",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def broadcast_event(task_id: str, event: LoopEvent):
    """Stores event in task history and fans out to all active SSE subscribers."""
    if task_id in task_store:
        task_store[task_id]["events"].append(event.model_dump())

    queues = event_queues.get(task_id, [])
    for q in queues:
        await q.put(event)


async def run_agent_task_worker(task_id: str, req: CreateTaskRequest):
    """Background worker executing the autonomous SWE cycle inside an isolated sandbox."""
    global sandbox_pool
    telemetry.record_agent_started()
    task_data = task_store[task_id]

    try:
        # Acquire warm sandbox (<5s startup SLA)
        acquire_start = time.perf_counter()
        sandbox = await sandbox_pool.acquire_sandbox(
            repo_name=req.repo_name,
            source_repo_path=BENCHMARK_SAMPLE_DIR
        )
        startup_ms = (time.perf_counter() - acquire_start) * 1000.0
        telemetry.record_startup_latency(startup_ms)

        task_data["sandbox_id"] = sandbox.sandbox_id
        task_data["status"] = "RUNNING"

        # Emit warm sandbox acquired event
        await broadcast_event(task_id, LoopEvent(
            task_id=task_id,
            event_type="status",
            message=f"Acquired warm sandbox [{sandbox.sandbox_id}] in {round(startup_ms, 1)}ms",
            data={"sandbox_id": sandbox.sandbox_id, "startup_latency_ms": startup_ms}
        ))

        # Launch Autonomous SWE Loop
        loop = AutonomousExecutionLoop(
            sandbox=sandbox,
            task_id=task_id,
            task_description=req.task_description,
            max_iterations=req.max_iterations,
            event_callback=lambda evt: broadcast_event(task_id, evt)
        )

        res: AgentLoopResult = await loop.run()

        # Update task status
        task_data["status"] = res.status
        task_data["duration_seconds"] = res.duration_seconds
        task_data["iterations_used"] = res.iterations_used
        task_data["tests_passed"] = res.tests_passed
        if res.patch_summary:
            task_data["unified_diff"] = res.patch_summary.unified_diff
            task_data["pr_title"] = res.patch_summary.pr_title
            task_data["pr_body"] = res.patch_summary.pr_body

        telemetry.record_agent_finished(res.tests_passed)

        # Release and recycle sandbox
        await sandbox_pool.release_sandbox(sandbox)

    except Exception as e:
        task_data["status"] = "ERROR"
        telemetry.record_agent_finished(False)
        await broadcast_event(task_id, LoopEvent(
            task_id=task_id,
            event_type="status",
            message=f"Critical Task Error: {str(e)}",
            data={"error": str(e)}
        ))


@app.post("/api/tasks", response_model=AgentTaskResponse)
async def create_task(req: CreateTaskRequest, background_tasks: BackgroundTasks):
    """Submits a new coding task to the harness."""
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    created_at = time.time()

    task_record = {
        "task_id": task_id,
        "repo_name": req.repo_name,
        "task_description": req.task_description,
        "status": "QUEUED",
        "sandbox_id": None,
        "created_at": created_at,
        "duration_seconds": 0.0,
        "iterations_used": 0,
        "tests_passed": False,
        "unified_diff": None,
        "pr_title": None,
        "pr_body": None,
        "events": []
    }
    task_store[task_id] = task_record
    event_queues[task_id] = []

    background_tasks.add_task(run_agent_task_worker, task_id, req)
    return AgentTaskResponse(**task_record)


@app.get("/api/tasks", response_model=List[AgentTaskResponse])
async def list_tasks():
    """Returns all active and completed tasks."""
    return [
        AgentTaskResponse(**{k: v for k, v in t.items() if k != "events"})
        for t in reversed(list(task_store.values()))
    ]


@app.get("/api/tasks/{task_id}", response_model=AgentTaskResponse)
async def get_task(task_id: str):
    """Returns details and patch for a single task."""
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    t = task_store[task_id]
    return AgentTaskResponse(**{k: v for k, v in t.items() if k != "events"})


@app.get("/api/tasks/{task_id}/events")
async def stream_task_events(task_id: str):
    """
    Server-Sent Events (SSE) streaming endpoint.
    Streams thoughts, terminal output, diff updates, and status transitions live.
    """
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    queue = asyncio.Queue()
    event_queues.setdefault(task_id, []).append(queue)

    async def event_generator():
        # 1. Send past history first
        for past_evt in task_store[task_id]["events"]:
            yield f"data: {json.dumps(past_evt)}\n\n"

        # 2. Stream live events as they occur
        try:
            while True:
                evt = await queue.get()
                yield f"data: {json.dumps(evt.model_dump())}\n\n"
                if evt.event_type == "status" and evt.message in ["RESOLVED", "FAILED", "ERROR"]:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if task_id in event_queues and queue in event_queues[task_id]:
                event_queues[task_id].remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@app.get("/api/pool/metrics")
async def get_pool_metrics():
    """Returns real-time telemetry: warm sandboxes, P99 startup latency, active workers."""
    global sandbox_pool
    pool_metrics = sandbox_pool.get_metrics() if sandbox_pool else {}
    telemetry_data = telemetry.get_summary()
    return {
        "pool": pool_metrics.model_dump() if hasattr(pool_metrics, "model_dump") else pool_metrics,
        "telemetry": telemetry_data
    }


@app.post("/api/benchmark/run-sample")
async def trigger_sample_benchmark(background_tasks: BackgroundTasks):
    """1-Click launch of the Freight Surcharge & Temperature Decay repair benchmark."""
    req = CreateTaskRequest(
        task_description="Fix freight surcharge weight threshold in calculator.py and add insulation_r_value validation for temperature decay",
        repo_name="sample_repo",
        max_iterations=3
    )
    return await create_task(req, background_tasks)


# Mount static frontend
control_plane_dir = PROJECT_ROOT / "control_plane"
if control_plane_dir.exists():
    app.mount("/", StaticFiles(directory=str(control_plane_dir), html=True), name="control_plane")
