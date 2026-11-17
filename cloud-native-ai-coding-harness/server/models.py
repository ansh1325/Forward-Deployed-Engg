"""
Pydantic Schemas & DTOs for Control Plane API
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import time


class CreateTaskRequest(BaseModel):
    task_description: str = Field(..., description="Issue description or bug report to fix")
    repo_name: str = Field(default="sample_repo", description="Target repository identifier")
    max_iterations: int = Field(default=5, ge=1, le=10)


class AgentTaskResponse(BaseModel):
    task_id: str
    repo_name: str
    task_description: str
    status: str
    sandbox_id: Optional[str] = None
    created_at: float
    duration_seconds: float = 0.0
    iterations_used: int = 0
    tests_passed: bool = False
    unified_diff: Optional[str] = None
    pr_title: Optional[str] = None
    pr_body: Optional[str] = None


class EventMessage(BaseModel):
    task_id: str
    event_type: str  # 'thought', 'tool_call', 'terminal', 'diff', 'status', 'patch'
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=time.time)
