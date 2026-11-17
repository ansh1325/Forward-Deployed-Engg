"""
Telemetry & Prometheus Metrics Tracker for Sandbox & Agent Orchestration
"""
import time
from typing import Dict, Any


class HarnessTelemetry:
    """
    In-memory and Prometheus telemetry collector.
    Tracks concurrent workers, startup latency, and success rates.
    """

    def __init__(self):
        self.total_tasks_created = 0
        self.total_tasks_resolved = 0
        self.total_tasks_failed = 0
        self.active_agents_count = 0
        self.startup_times_ms: list[float] = []

    def record_agent_started(self):
        self.total_tasks_created += 1
        self.active_agents_count += 1

    def record_agent_finished(self, passed: bool):
        self.active_agents_count = max(0, self.active_agents_count - 1)
        if passed:
            self.total_tasks_resolved += 1
        else:
            self.total_tasks_failed += 1

    def record_startup_latency(self, latency_ms: float):
        self.startup_times_ms.append(latency_ms)
        if len(self.startup_times_ms) > 500:
            self.startup_times_ms = self.startup_times_ms[-500:]

    def get_summary(self) -> Dict[str, Any]:
        p99 = 0.0
        avg = 0.0
        if self.startup_times_ms:
            sorted_latencies = sorted(self.startup_times_ms)
            idx = min(int(len(sorted_latencies) * 0.99), len(sorted_latencies) - 1)
            p99 = sorted_latencies[idx]
            avg = sum(self.startup_times_ms) / len(self.startup_times_ms)

        total_finished = self.total_tasks_resolved + self.total_tasks_failed
        success_rate = (self.total_tasks_resolved / total_finished * 100.0) if total_finished > 0 else 100.0

        return {
            "active_agents": self.active_agents_count,
            "total_tasks": self.total_tasks_created,
            "resolved_tasks": self.total_tasks_resolved,
            "success_rate_percent": round(success_rate, 1),
            "p99_startup_ms": round(p99, 1),
            "avg_startup_ms": round(avg, 1)
        }


telemetry = HarnessTelemetry()
