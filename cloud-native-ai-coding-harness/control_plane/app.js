// Control Plane Real-Time Frontend Driver
let currentTaskId = null;
let activeEventSource = null;

// DOM Elements
const taskListContainer = document.getElementById("taskListContainer");
const traceContainer = document.getElementById("traceContainer");
const terminalOutput = document.getElementById("terminalOutput");
const diffOutput = document.getElementById("diffOutput");
const prTitle = document.getElementById("prTitle");
const prBody = document.getElementById("prBody");
const activeTaskIdDisplay = document.getElementById("activeTaskIdDisplay");
const btnBenchmark = document.getElementById("btnBenchmark");
const btnNewTask = document.getElementById("btnNewTask");

// Tabs
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    tab.classList.add("active");
    const target = document.getElementById(tab.dataset.tab);
    if (target) target.classList.add("active");
  });
});

// Fetch telemetry and pool status every 2 seconds
async function refreshMetrics() {
  try {
    const res = await fetch("/api/pool/metrics");
    if (!res.ok) return;
    const data = await res.json();

    if (data.telemetry) {
      document.getElementById("metricActiveAgents").innerText = data.telemetry.active_agents || 0;
      document.getElementById("metricSuccessRate").innerText = (data.telemetry.success_rate_percent || 100) + "%";
    }
    if (data.pool) {
      document.getElementById("metricWarmPool").innerText = data.pool.warm_pool_size || 0;
      const p99Ms = data.pool.p99_startup_latency_ms || 1500;
      document.getElementById("metricP99Latency").innerText = (p99Ms / 1000).toFixed(1) + "s";
    }
  } catch (e) {
    // console.error("Telemetry fetch error:", e);
  }
}

// Fetch all tasks
async function loadTasks() {
  try {
    const res = await fetch("/api/tasks");
    if (!res.ok) return;
    const tasks = await res.json();
    document.getElementById("taskCount").innerText = `${tasks.length} Tasks`;

    taskListContainer.innerHTML = "";
    tasks.forEach(task => {
      const el = document.createElement("div");
      el.className = `task-item ${task.task_id === currentTaskId ? "active" : ""}`;
      el.innerHTML = `
        <div class="task-meta">
          <span style="font-family: monospace; color: var(--accent);">${task.task_id}</span>
          <span class="status-tag status-${task.status}">${task.status}</span>
        </div>
        <div style="font-size: 12px; font-weight: 600; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          ${task.task_description}
        </div>
        <div style="font-size: 11px; color: var(--text-muted); display: flex; justify-content: space-between;">
          <span>Repo: ${task.repo_name}</span>
          <span>${task.duration_seconds > 0 ? task.duration_seconds + "s" : ""}</span>
        </div>
      `;
      el.addEventListener("click", () => selectTask(task.task_id));
      taskListContainer.appendChild(el);
    });

    if (!currentTaskId && tasks.length > 0) {
      selectTask(tasks[0].task_id);
    }
  } catch (e) {
    console.error("Task list error:", e);
  }
}

// Select and stream a specific task
function selectTask(taskId) {
  if (currentTaskId === taskId && activeEventSource) return;
  currentTaskId = taskId;
  activeTaskIdDisplay.innerText = taskId;

  // Highlight active task in sidebar
  document.querySelectorAll(".task-item").forEach(item => {
    item.classList.toggle("active", item.innerHTML.includes(taskId));
  });

  // Reset containers
  traceContainer.innerHTML = "";
  terminalOutput.innerText = `[STREAM CONNECTED: ${taskId}]\n`;
  diffOutput.innerHTML = "Awaiting diff updates...";
  prTitle.innerText = "PR Not Ready";
  prBody.innerText = "Pending task verification...";

  if (activeEventSource) {
    activeEventSource.close();
  }

  // Connect SSE Stream
  activeEventSource = new EventSource(`/api/tasks/${taskId}/events`);

  activeEventSource.onmessage = (e) => {
    const evt = JSON.parse(e.data);
    handleStreamEvent(evt);
  };

  activeEventSource.onerror = () => {
    // Stream closed or completed
    activeEventSource.close();
  };
}

function handleStreamEvent(evt) {
  const timeStr = new Date((evt.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString();

  // 1. Thought / Tool Trace
  if (evt.event_type === "thought" || evt.event_type === "tool_call" || evt.event_type === "status") {
    const card = document.createElement("div");
    card.className = `trace-card ${evt.event_type}-trace`;
    card.innerHTML = `
      <div class="trace-time">${timeStr} • [${evt.event_type.toUpperCase()}]</div>
      <div>${evt.message}</div>
    `;
    traceContainer.appendChild(card);
    traceContainer.scrollTop = traceContainer.scrollHeight;
  }

  // 2. Terminal stdout/stderr
  if (evt.event_type === "terminal") {
    terminalOutput.innerText += `\n[${timeStr}] === Sandbox Terminal Output ===\n${evt.message}\n`;
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
  }

  // 3. Diff Window
  if (evt.event_type === "diff" && evt.message) {
    renderDiff(evt.message);
  }

  // 4. Patch / PR
  if (evt.event_type === "patch" && evt.data) {
    prTitle.innerText = evt.data.pr_title || "Autonomous Fix PR";
    prBody.innerText = evt.data.pr_body || "";
    if (evt.data.unified_diff) {
      renderDiff(evt.data.unified_diff);
    }
  }

  // Refresh tasks on completion
  if (evt.event_type === "status" && ["RESOLVED", "FAILED"].includes(evt.message)) {
    loadTasks();
  }
}

function renderDiff(rawDiff) {
  diffOutput.innerHTML = "";
  if (!rawDiff.trim()) {
    diffOutput.innerHTML = "No changes generated.";
    return;
  }

  const lines = rawDiff.split("\n");
  lines.forEach(line => {
    const span = document.createElement("span");
    if (line.startsWith("+") && !line.startsWith("+++")) {
      span.className = "diff-line-add";
    } else if (line.startsWith("-") && !line.startsWith("---")) {
      span.className = "diff-line-del";
    } else if (line.startsWith("@@") || line.startsWith("diff")) {
      span.className = "diff-line-info";
    }
    span.innerText = line + "\n";
    diffOutput.appendChild(span);
  });
}

// 1-Click Benchmark Action
btnBenchmark.addEventListener("click", async () => {
  btnBenchmark.disabled = true;
  btnBenchmark.innerText = "⏳ Dispatching Agent...";
  try {
    const res = await fetch("/api/benchmark/run-sample", { method: "POST" });
    const data = await res.json();
    await loadTasks();
    selectTask(data.task_id);
  } catch (e) {
    alert("Failed to start benchmark: " + e.message);
  } finally {
    btnBenchmark.disabled = false;
    btnBenchmark.innerText = "▶ Run Benchmark Fix";
  }
});

// Custom Task Action
btnNewTask.addEventListener("click", async () => {
  const desc = prompt("Enter bug description / coding task for SWE agent:", "Fix latitude validation boundary in data_pipeline.py");
  if (!desc) return;

  try {
    const res = await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_description: desc, repo_name: "sample_repo" })
    });
    const data = await res.json();
    await loadTasks();
    selectTask(data.task_id);
  } catch (e) {
    alert("Failed to dispatch task: " + e.message);
  }
});

// Initial boot
loadTasks();
refreshMetrics();
setInterval(refreshMetrics, 2000);
setInterval(loadTasks, 5000);
