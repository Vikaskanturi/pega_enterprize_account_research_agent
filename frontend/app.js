/* =====================================================================
   PEGA RESEARCH AGENT — Frontend Application
   Connects to FastAPI via WebSocket for real-time step streaming.
   ===================================================================== */

// ── Constants ───────────────────────────────────────────────────────────

const WS_URL = `ws://${location.host}/ws/research`;
const API_BASE = `${location.protocol}//${location.host}`;

const STEP_NAMES = {
  1: "Input & Classification",
  2: "Revenue Classification",
  3: "Basic Firmographics",
  4: "Corporate Structure",
  5: "GCC Check (India)",
  6: "LinkedIn Discovery",
  7: "Employee Count",
  8: "Engineering / IT / QA",
  9: "Pega Usage Verification",
  10: "Competing Platforms",
  11: "Service Company Check",
  12: "Final Categorization",
  13: "Research Notes",
};

const STEP_ICONS = {
  1: "🔍", 2: "💰", 3: "🏢", 4: "🌐", 5: "🇮🇳",
  6: "💼", 7: "👥", 8: "⚙️", 9: "🔵", 10: "🏷",
  11: "🤝", 12: "📊", 13: "📝",
};

const MODEL_ICONS = {
  "Google": "🔮",
  "OpenAI": "🟢",
  "Anthropic": "🟣",
  "Groq": "⚡",
  "HuggingFace": "🤗",
  "Ollama": "🦙",
};

// ── State ────────────────────────────────────────────────────────────────

let selectedModel = "gemini-2.5-flash";
let currentWs = null;
let currentJobId = null;
let currentState = null;
let jobs = [];
let isResearching = false;
let researchStartTime = null;
let stepStates = {}; // stepNum → 'pending'|'active'|'done'|'error'

// ── Init ─────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  await loadModels();
  renderStepCards();
  setupEnterKey();
  loadJobHistory();
  checkHealth();          // ← validate API keys on startup
});

function setupEnterKey() {
  document.getElementById("company-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") startResearch();
  });
}

// ── Health / System Status ────────────────────────────────────────────────

const SERVICE_LABELS = {
  gemini:    { icon: "🔮", name: "Gemini (Google)",   note: "Primary LLM — required" },
  openai:    { icon: "🟢", name: "OpenAI (GPT-4o)",   note: "Optional LLM" },
  anthropic: { icon: "🟣", name: "Anthropic (Claude)", note: "Optional LLM" },
  groq:      { icon: "⚡", name: "Groq",              note: "Optional LLM" },
  huggingface:{ icon: "🤗", name: "Hugging Face",     note: "Optional LLM" },
  serpapi:   { icon: "🔍", name: "SerpAPI",            note: "Web search — required" },
  browser:   { icon: "🌐", name: "Playwright Browser", note: "Used for LinkedIn scraping" },
};

async function checkHealth() {
  const list = document.getElementById("health-list");
  if (!list) return;
  list.innerHTML = '<div class="health-checking">Checking services…</div>';
  const btn = document.getElementById("refresh-health-btn");
  if (btn) btn.style.opacity = "0.4";

  try {
    const res = await fetch(`${API_BASE}/api/health`);
    const data = await res.json();
    renderHealth(data.services, data.status);
  } catch (e) {
    list.innerHTML = '<div class="health-checking" style="color:#EF4444">Could not reach server</div>';
  } finally {
    if (btn) btn.style.opacity = "1";
  }
}

function renderHealth(services, overallStatus) {
  const list = document.getElementById("health-list");
  list.innerHTML = "";

  const order = ["gemini", "serpapi", "browser", "openai", "anthropic", "groq", "huggingface"];
  let allOk = 0, total = order.length;

  for (const svcKey of order) {
    const svc = services[svcKey] || { ok: false, reason: "Not checked" };
    const meta = SERVICE_LABELS[svcKey] || { icon: "❓", name: svcKey, note: "" };
    if (svc.ok) allOk++;

    const item = document.createElement("div");
    item.className = `health-item ${svc.ok ? "health-ok" : "health-fail"}`;
    item.title = svc.reason || "";
    item.innerHTML = `
      <span class="health-icon">${meta.icon}</span>
      <div class="health-info">
        <div class="health-name">${meta.name}</div>
        <div class="health-reason">${svc.ok ? "✓ " + (svc.reason || "OK") : "✗ " + (svc.reason || "Not available")}</div>
      </div>
      <div class="health-dot ${svc.ok ? "dot-green" : "dot-red"}"></div>
    `;
    list.appendChild(item);
  }

  // Summary line
  const summary = document.createElement("div");
  summary.className = "health-summary";
  summary.textContent = overallStatus === "ready"
    ? `✅ System ready — ${allOk}/${total} services active`
    : `⚠️ Degraded — ${allOk}/${total} services active`;
  summary.style.color = overallStatus === "ready" ? "#10B981" : "#F59E0B";
  list.appendChild(summary);

  // Update topbar status dot
  const dot = document.getElementById("status-dot");
  if (dot) {
    dot.style.background = overallStatus === "ready" ? "var(--accent-green)" : "#F59E0B";
    dot.title = overallStatus === "ready" ? "All systems ready" : "Some services unavailable";
  }
}

// ── Model Loading ─────────────────────────────────────────────────────────

async function loadModels() {
  try {
    const res = await fetch(`${API_BASE}/api/models`);
    const data = await res.json();
    renderModelGrid(data.models);
  } catch (e) {
    renderModelGrid(defaultModels());
  }
}

function defaultModels() {
  return [
    { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", provider: "Google", speed: "Fast", cost: "Free" },
    { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI", speed: "Medium", cost: "Medium" },
    { id: "claude-sonnet", name: "Claude Sonnet", provider: "Anthropic", speed: "Medium", cost: "Medium" },
    { id: "groq-llama3", name: "Groq Llama 3", provider: "Groq", speed: "Super Fast", cost: "Low" },
    { id: "groq-qwen", name: "Groq Qwen 32B", provider: "Groq", speed: "Super Fast", cost: "Low" },
    { id: "hf-meta-llama3", name: "HF Llama 3", provider: "HuggingFace", speed: "Medium", cost: "Low" },
    { id: "llama3", name: "Llama 3 (Local)", provider: "Ollama", speed: "Slow", cost: "Free" },
  ];
}

function renderModelGrid(models) {
  const grid = document.getElementById("model-grid");
  if (!grid) return;
  grid.innerHTML = "";
  for (const m of models) {
    const badge = m.cost === "Free" ? "free" : m.speed === "Fast" ? "fast" : "pro";
    const badgeLabel = m.cost === "Free" ? "Free" : m.speed;
    const btn = document.createElement("button");
    btn.className = `model-btn ${m.id === selectedModel ? "active" : ""}`;
    btn.id = `model-btn-${m.id}`;
    btn.onclick = () => selectModel(m.id, m.name);
    btn.innerHTML = `
      <div class="model-icon">${MODEL_ICONS[m.provider] || "🤖"}</div>
      <div class="model-info">
        <div class="model-name">${m.name}</div>
        <div class="model-meta">${m.provider}</div>
      </div>
      <div class="model-badge badge-${badge}">${badgeLabel}</div>
    `;
    grid.appendChild(btn);
  }
}

function selectModel(modelId, modelName) {
  selectedModel = modelId;
  document.querySelectorAll(".model-btn").forEach(b => b.classList.remove("active"));
  const btn = document.getElementById(`model-btn-${modelId}`);
  if (btn) btn.classList.add("active");
  document.getElementById("active-model-label").textContent = modelName;
  showToast(`Model: ${modelName}`, "info");
  document.getElementById("custom-model-id").value = "";
}

function clearModelSelection() {
  selectedModel = null;
  document.querySelectorAll(".model-btn").forEach(b => b.classList.remove("active"));
  document.getElementById("active-model-label").textContent = "Custom Model";
}

// ── Step Cards ────────────────────────────────────────────────────────────

function renderStepCards() {
  const grid = document.getElementById("steps-grid");
  grid.innerHTML = "";
  for (let i = 1; i <= 13; i++) {
    stepStates[i] = "pending";
    const card = document.createElement("div");
    card.className = "step-card";
    card.id = `step-card-${i}`;
    card.innerHTML = `
      <div class="step-number" id="step-num-${i}">${STEP_ICONS[i]}</div>
      <div class="step-content">
        <div class="step-title">Step ${i}: ${STEP_NAMES[i]}</div>
        <div class="step-log" id="step-log-${i}">Waiting...</div>
      </div>
    `;
    grid.appendChild(card);
  }
}

function updateStepCard(step, status, message = "") {
  const card = document.getElementById(`step-card-${step}`);
  const numEl = document.getElementById(`step-num-${step}`);
  const logEl = document.getElementById(`step-log-${step}`);
  if (!card) return;

  card.className = `step-card ${status}`;
  if (status === "done") numEl.textContent = "✓";
  else if (status === "error") numEl.textContent = "✗";
  else if (status === "active") numEl.textContent = STEP_ICONS[step];
  else numEl.textContent = STEP_ICONS[step];

  if (message) logEl.textContent = message;
}

// ── Research Entry Point ──────────────────────────────────────────────────

async function startResearch() {
  const company = document.getElementById("company-input").value.trim();
  if (!company) {
    showToast("Please enter a company name", "error");
    return;
  }
  if (isResearching) {
    showToast("Research already in progress", "info");
    return;
  }

  let modelToUse = selectedModel;
  const customProv = document.getElementById("custom-provider").value;
  let customModel = "";
  if (customProv === "lmstudio" && document.getElementById("lmstudio-dropdown") && document.getElementById("lmstudio-dropdown").style.display !== "none") {
      customModel = document.getElementById("lmstudio-dropdown").value.trim();
  } else {
      customModel = document.getElementById("custom-model-id").value.trim();
  }
  
  if (customModel) {
    modelToUse = `${customProv}:${customModel}`;
  }

  if (!modelToUse) {
    showToast("Please select or enter a custom model", "error");
    return;
  }

  isResearching = true;
  researchStartTime = Date.now();
  currentState = null;
  stepStates = {};

  // UI: switch to progress tab
  switchTab("progress");
  document.getElementById("welcome-state").style.display = "none";
  const activeRes = document.getElementById("active-research");
  activeRes.style.display = "flex";

  // Set company header
  const initials = company.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
  document.getElementById("company-avatar").textContent = initials;
  document.getElementById("company-name-display").textContent = company;
  document.getElementById("company-meta").textContent = "Connecting to research pipeline...";
  document.getElementById("company-etype").textContent = "";

  // Reset steps
  renderStepCards();
  setProgress(0, "Initializing...");

  // Start/Stop buttons
  document.getElementById("start-btn").style.display = "none";
  document.getElementById("stop-btn").style.display = "block";

  // Download + Export buttons reset
  document.getElementById("download-btn").style.display = "none";
  const exportBtn = document.getElementById("export-btn");
  if (exportBtn) {
    exportBtn.disabled = true;
    exportBtn.style.opacity = "0.45";
    exportBtn.style.cursor = "not-allowed";
  }
  const saveLocalBtn = document.getElementById("save-local-btn");
  if (saveLocalBtn) {
    saveLocalBtn.disabled = true;
    saveLocalBtn.style.opacity = "0.45";
    saveLocalBtn.style.cursor = "not-allowed";
  }

  addLog("info", 0, `Starting research for: ${company} [model: ${modelToUse}]`);

  // Connect WebSocket
  openWebSocket(company, modelToUse);
}

function stopResearch() {
  if (currentWs && currentWs.readyState === WebSocket.OPEN) {
    currentWs.send(JSON.stringify({ action: "stop" }));
    showToast("Stopping research...", "info");
    document.getElementById("stop-btn").innerText = "Stopping...";
    document.getElementById("stop-btn").disabled = true;
  }
}

function openWebSocket(company, model) {
  if (currentWs) {
    currentWs.close();
    currentWs = null;
  }

  const ws = new WebSocket(WS_URL);
  currentWs = ws;

  ws.onopen = () => {
    ws.send(JSON.stringify({ company_name: company, llm_model: model }));
    addLog("success", 0, "WebSocket connected.");
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleEvent(data);
    } catch (e) {
      console.error("WS parse error:", e);
    }
  };

  ws.onerror = (e) => {
    addLog("error", 0, "WebSocket error — check that the server is running.");
    showToast("Connection error — is the server running?", "error");
    finishResearch();
  };

  ws.onclose = () => {
    addLog("info", 0, "WebSocket closed.");
  };
}

function handleEvent(event) {
  const { type, step, step_name, message, state, error, job_id, output_path } = event;

  switch (type) {
    case "start":
      document.getElementById("company-meta").textContent = "Pipeline started...";
      addLog("info", 0, `Pipeline started for: ${state?.company_name}`);
      break;

    case "step_start":
      updateStepCard(step, "active", "Running...");
      setProgress((step - 1) / 13 * 100, `Step ${step}: ${step_name}`);
      addLog("info", step, `Starting: ${step_name}`);
      document.getElementById("company-meta").textContent = `Step ${step}/13 — ${step_name}`;
      break;

    case "step_done":
      updateStepCard(step, "done", message || "Complete");
      setProgress(step / 13 * 100, `Step ${step}: ${step_name} — Done`);
      addLog("success", step, `Done: ${step_name}`);

      // Update results preview from state
      if (state) {
        currentState = state;
        updateResultsPreview(state);
      }
      break;

    case "step_error":
      updateStepCard(step, "error", error || "Error");
      addLog("error", step, `Error in step ${step}: ${error}`);
      break;

    case "stopped_early":
      addLog("info", step, "Company is a Pega Partner — research halted.");
      showToast("⚠️ Company is a Pega Partner — research stopped.", "info");
      document.getElementById("company-meta").textContent = "Pega Partner — not researched further.";
      break;

    case "excel_ready":
      currentJobId = job_id || "latest";
      // Don't show download yet — wait for full 'complete' event
      addLog("success", 13, `Excel ready (partial): ${output_path}`);
      break;

    case "job_id":
      currentJobId = event.job_id;
      break;

    case "complete":
      addLog("success", 13, "Research complete!");
      showToast(`✅ Research complete for ${currentState?.company_name || "company"}`, "success");
      if (currentState) {
        updateResultsPreview(currentState);
        addJobToHistory(currentState);
      }
      setProgress(100, "Research Complete ✅");
      document.getElementById("company-meta").textContent = "Research complete — all 33 columns populated.";
      // Only show download button now that research is fully done
      const dlBtn = document.getElementById("download-btn");
      dlBtn.style.display = "flex";
      dlBtn.disabled = false;
      dlBtn.title = "Download the completed research as an Excel file";
      finishResearch();
      switchTab("results");
      break;

    case "fatal_error":
      addLog("error", 0, `Fatal error: ${message}`);
      showToast(`Fatal error: ${message}`, "error");
      finishResearch();
      break;

    default:
      if (message) addLog("info", step || 0, message);
  }
}

function finishResearch() {
  isResearching = false;
  const btn = document.getElementById("start-btn");
  btn.disabled = false;
  document.getElementById("start-btn-text").textContent = "🚀 Start Research";
  document.getElementById("status-dot").style.background = "var(--accent-green)";
  document.getElementById("stop-btn").style.display = "none";
  document.getElementById("start-btn").style.display = "block";
  if (currentWs) currentWs.close();
}

// ── Progress Bar ─────────────────────────────────────────────────────────

function setProgress(pct, label) {
  document.getElementById("progress-bar").style.width = `${Math.min(pct, 100)}%`;
  document.getElementById("progress-pct").textContent = `${Math.round(pct)}%`;
  document.getElementById("progress-label-text").textContent = label;
}

// ── Results Rendering ─────────────────────────────────────────────────────

function updateResultsPreview(state) {
  // Enable the export button whenever data is loaded
  const exportBtn = document.getElementById("export-btn");
  if (exportBtn) {
    exportBtn.disabled = false;
    exportBtn.style.opacity = "1";
    exportBtn.style.cursor = "pointer";
  }
  const saveLocalBtn = document.getElementById("save-local-btn");
  if (saveLocalBtn) {
    saveLocalBtn.disabled = false;
    saveLocalBtn.style.opacity = "1";
    saveLocalBtn.style.cursor = "pointer";
  }

  const cols = state.columns || {};
  const etype = cols["Enterprise Type"] || "";
  const etypeClass = etype.replace(".", "-").toLowerCase();

  // Update header E-type
  const etypeEl = document.getElementById("company-etype");
  etypeEl.textContent = etype || "";
  etypeEl.className = `company-etype etype-${etypeClass || "none"}`;

  const area = document.getElementById("results-area");
  area.innerHTML = "";

  const grid = document.createElement("div");
  grid.className = "results-cards";

  // Card 1: Identity
  grid.appendChild(makeCard("🏢 Company Identity", [
    { label: "Company", value: cols["Company Name"] },
    { label: "Parent Company", value: cols["Parent Company"] },
    { label: "India Subsidiary", value: cols["India Subsidiary"] },
    { label: "Industry", value: cols["Industry"] },
    { label: "Headquarters", value: cols["Headquarters Location"] },
    { label: "Annual Revenue", value: cols["Annual Revenue (USD)"], highlight: true },
  ]));

  // Card 2: Pega Status
  const pegaVal = cols["Pega Usage Confirmed"] || "";
  const pegaClass = pegaVal === "Yes" ? "pega-yes" : pegaVal === "No" ? "pega-no" : "pega-unsure";
  grid.appendChild(makeCard("🔵 Pega Intelligence", [
    { label: "Customer / Partner", value: cols["Pega Customer / Partner"], highlight: true },
    { label: "Pega Usage", value: pegaVal, cls: pegaClass },
    { label: "Evidence", value: cols["Pega Evidence"] },
  ]));

  // Card 3: Revenue
  grid.appendChild(makeCard("💰 Revenue Profile", [
    { label: "Primary Revenue", value: cols["Primary Revenue Source"] },
    { label: "Classification", value: cols["Software or Non-Software"], highlight: true },
  ]));

  // Card 4: GCC
  grid.appendChild(makeCard("🇮🇳 India GCC Presence", [
    { label: "GCC in India", value: cols["GCCs in India"] },
    { label: "Number of GCCs", value: cols["Number of GCCs"] },
    { label: "GCC Locations", value: cols["GCC Locations"] },
    { label: "Main GCC", value: cols["Main GCC in India"] },
  ]));

  // Card 5: Headcount (custom layout)
  const hcCard = document.createElement("div");
  hcCard.className = "result-card";
  hcCard.innerHTML = `
    <div class="result-card-title">👥 Headcount</div>
    <div class="hc-grid">
      <div class="hc-item">
        <div class="hc-label">Total (Global)</div>
        <div class="hc-value">${cols["Total Employee Count (Org-wide)"] || "—"}</div>
      </div>
      <div class="hc-item">
        <div class="hc-label">Total (India)</div>
        <div class="hc-value">${cols["Employee Count (India)"] || "—"}</div>
      </div>
      <div class="hc-item">
        <div class="hc-label">Engineering (Global)</div>
        <div class="hc-value">${cols["Engineering Count (Org-wide)"] || "—"}</div>
        <div class="hc-sub">${cols["Engineering % of Total Headcount"] || ""} of total</div>
      </div>
      <div class="hc-item">
        <div class="hc-label">Engineering (India)</div>
        <div class="hc-value">${cols["Engineering Count (India)"] || "—"}</div>
      </div>
      <div class="hc-item">
        <div class="hc-label">IT (Global)</div>
        <div class="hc-value">${cols["IT Count (Org-wide)"] || "—"}</div>
      </div>
      <div class="hc-item">
        <div class="hc-label">QA/SDET (Global)</div>
        <div class="hc-value">${cols["SDET & QA Count (Org-wide)"] || "—"}</div>
      </div>
    </div>
  `;
  grid.appendChild(hcCard);

  // Card 6: Outsourcing
  grid.appendChild(makeCard("🤝 Development Model", [
    { label: "Dev Model", value: cols["Software Development Model"], highlight: true },
    { label: "Service Companies", value: cols["Service Companies Identified"] },
    { label: "Hiring for Tech Roles", value: cols["Hiring for Tech Roles"] },
    { label: "Roles Hiring For", value: cols["Tech Roles Being Hired For"] },
  ]));

  // Card 7: Platforms
  grid.appendChild(makeCard("🏷 Competing Platforms", [
    { label: "Other Platforms", value: cols["Other Enterprise Platforms"] },
  ]));

  // Card 8: Enterprise Type (large)
  const etypeCard = document.createElement("div");
  etypeCard.className = "result-card";
  etypeCard.style.background = getEtypeCardBg(etype);
  etypeCard.innerHTML = `
    <div class="result-card-title">📊 Enterprise Classification</div>
    <div style="display:flex;align-items:center;gap:16px">
      <div style="font-size:48px;font-weight:900;color:${getEtypeColor(etype)}">${etype || "—"}</div>
      <div style="flex:1">
        <div style="font-size:14px;font-weight:700;margin-bottom:4px">${getEtypeLabel(etype)}</div>
        <div style="font-size:12px;color:var(--text-secondary)">${getEtypeDesc(etype)}</div>
      </div>
    </div>
    <div style="font-size:11px;color:var(--text-muted);margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">
      ${cols["Research Notes / Comments"] || "No additional notes."}
    </div>
  `;
  grid.appendChild(etypeCard);

  area.appendChild(grid);
}

function makeCard(title, fields) {
  const card = document.createElement("div");
  card.className = "result-card";
  card.innerHTML = `<div class="result-card-title">${title}</div>`;
  for (const f of fields) {
    const val = f.value || "";
    const isNA = !val || val === "N/A" || val === "Unknown";
    const cls = f.cls || (f.highlight && !isNA ? "highlight" : isNA ? "na" : "");
    card.innerHTML += `
      <div class="result-field">
        <div class="result-label">${f.label}</div>
        <div class="result-value ${cls}">${val || "—"}</div>
      </div>
    `;
  }
  return card;
}

function getEtypeColor(etype) {
  return { E1: "#EF4444", "E1.1": "#F59E0B", E2: "#3B82F6", E3: "#10B981" }[etype] || "#94A3B8";
}

function getEtypeCardBg(etype) {
  const colors = { E1: "rgba(239,68,68,0.06)", "E1.1": "rgba(245,158,11,0.06)", E2: "rgba(59,130,246,0.06)", E3: "rgba(16,185,129,0.06)" };
  return colors[etype] ? `var(--bg-card); background: ${colors[etype]}` : "";
}

function getEtypeLabel(etype) {
  return {
    E1: "Fully Outsourced",
    "E1.1": "Transitioning In-House",
    E2: "Non-Software Enterprise",
    E3: "Software-First Enterprise",
  }[etype] || "Classification Pending";
}

function getEtypeDesc(etype) {
  return {
    E1: "Development fully outsourced to service companies. Minimal internal engineering.",
    "E1.1": "Currently outsourced but actively building an internal engineering team.",
    E2: "Core business is non-software (e.g. insurance, banking). Tech is a support function.",
    E3: "Software is the primary business. Strong build-over-buy culture.",
  }[etype] || "Enterprise type not yet determined.";
}

// ── Log Stream ────────────────────────────────────────────────────────────

function addLog(level, step, message) {
  const stream = document.getElementById("log-stream");
  const elapsed = researchStartTime ? `${((Date.now() - researchStartTime) / 1000).toFixed(1)}s` : "00:00";
  const stepLabel = step > 0 ? `[S${step}]` : "[SYS]";
  const line = document.createElement("div");
  line.className = `log-line log-${level}`;
  line.innerHTML = `
    <span class="log-time">${elapsed}</span>
    <span class="log-step">${stepLabel}</span>
    <span>${escapeHtml(message)}</span>
  `;
  stream.appendChild(line);
  stream.scrollTop = stream.scrollHeight;
}

function clearLogs() {
  document.getElementById("log-stream").innerHTML =
    '<div class="log-line log-info"><span class="log-time">0.0s</span><span>[SYS]</span><span>Log cleared.</span></div>';
}

function escapeHtml(str) {
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// ── Job History ───────────────────────────────────────────────────────────

function addJobToHistory(state) {
  jobs.unshift(state);
  if (jobs.length > 20) jobs.pop();
  renderJobList();
  localStorage.setItem("pega_jobs", JSON.stringify(jobs.slice(0, 10)));
}

function loadJobHistory() {
  try {
    const saved = JSON.parse(localStorage.getItem("pega_jobs") || "[]");
    jobs = saved;
    renderJobList();
  } catch(e) {}
}

function renderJobList() {
  const list = document.getElementById("job-list");
  if (!jobs.length) {
    list.innerHTML = `<div class="empty-state" style="padding:20px 0"><div class="empty-icon">📂</div><div>No research yet</div></div>`;
    return;
  }
  list.innerHTML = "";
  for (const j of jobs) {
    const etype = j.columns?.["Enterprise Type"] || "";
    const etypeClass = etype.replace(".", "-").toLowerCase();
    const item = document.createElement("div");
    item.className = "job-item";
    item.onclick = () => { currentState = j; updateResultsPreview(j); switchTab("results"); };
    item.innerHTML = `
      <div class="job-etype etype-${etypeClass || "none"}">${etype || "?"}</div>
      <div class="job-name">${j.company_name}</div>
      <div class="job-status">${j.completed ? "Done" : "Partial"}</div>
    `;
    list.appendChild(item);
  }
}

// ── Tab Switching ─────────────────────────────────────────────────────────

function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  document.getElementById(`tab-${tab}`).classList.add("active");
  document.getElementById(`panel-${tab}`).classList.add("active");
}

// ── Excel Download ────────────────────────────────────────────────────────

async function downloadExcel() {
  const btn = document.getElementById("download-btn");
  const originalText = btn.innerHTML;

  // Show loading state
  btn.innerHTML = "⏳ Downloading...";
  btn.disabled = true;

  try {
    const encodedId = encodeURIComponent(currentJobId || "latest");
    const url = `${API_BASE}/api/research/${encodedId}/download/pega_research_results.xlsx?t=${Date.now()}`;

    console.log("Downloading from:", url);

    const response = await fetch(url);

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Server returned ${response.status}: ${errText}`);
    }

    // Convert response to a Blob so we fully own the filename
    const blob = await response.blob();

    // Build a safe filename from the company name (or fallback)
    const company = (currentState?.company_name || "pega_research")
      .replace(/[^a-z0-9_\-]/gi, "_")
      .toLowerCase();
    const filename = `pega_research_${company}.xlsx`;

    // Create a temporary object URL and trigger the download
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();

    // Clean up
    setTimeout(() => {
      URL.revokeObjectURL(objectUrl);
      document.body.removeChild(link);
    }, 300);

    showToast(`📥 Downloading ${filename}`, "success");
  } catch (err) {
    console.error("Download failed:", err);
    showToast(`Download failed: ${err.message}`, "error");
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

// ── Excel Export (generate from current state) ───────────────────────────

async function exportToExcel() {
  if (!currentState) {
    showToast("No research data to export yet.", "error");
    return;
  }

  const btn = document.getElementById("export-btn");
  const originalText = btn.innerHTML;
  btn.innerHTML = "⏳ Generating...";
  btn.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/api/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: currentState.company_name || "research",
        columns: currentState.columns || {},
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Server error ${response.status}`);
    }

    const blob = await response.blob();
    const company = (currentState.company_name || "research")
      .replace(/[^a-z0-9_\-]/gi, "_")
      .toLowerCase();
    const filename = `pega_research_${company}.xlsx`;

    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    setTimeout(() => { URL.revokeObjectURL(objectUrl); document.body.removeChild(link); }, 300);

    showToast(`📊 Exported: ${filename}`, "success");
  } catch (err) {
    console.error("Export failed:", err);
    showToast(`Export failed: ${err.message}`, "error");
  } finally {
    btn.innerHTML = originalText;
    // Re-enable only if we still have data
    if (currentState) {
      btn.disabled = false;
      btn.style.opacity = "1";
      btn.style.cursor = "pointer";
      
      const saveLocalBtn = document.getElementById("save-local-btn");
      if (saveLocalBtn) {
        saveLocalBtn.disabled = false;
        saveLocalBtn.style.opacity = "1";
        saveLocalBtn.style.cursor = "pointer";
      }
    }
  }
}

// ── Save Locally (Append to Master Excel file) ───────────────────────────

async function saveLocally() {
  if (!currentState) {
    showToast("No research data to save yet.", "error");
    return;
  }

  const btn = document.getElementById("save-local-btn");
  const originalText = btn.innerHTML;
  btn.innerHTML = "⏳ Saving...";
  btn.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/api/save_local`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        columns: currentState.columns || {},
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Server error ${response.status}`);
    }

    const data = await response.json();
    showToast(data.message, "success");
  } catch (err) {
    console.error("Save failed:", err);
    showToast(`Save failed: ${err.message}`, "error");
  } finally {
    btn.innerHTML = originalText;
    if (currentState) {
      btn.disabled = false;
      btn.style.opacity = "1";
      btn.style.cursor = "pointer";
    }
  }
}

// ── Toasts ────────────────────────────────────────────────────────────────

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4100);
}

// ── Settings Modal ────────────────────────────────────────────────────────
async function openSettingsModal() {
  const modal = document.getElementById("settings-modal");
  
  // Fetch current keys
  try {
    const res = await fetch(`${API_BASE}/api/settings`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById("key-gemini").value = data.gemini || "";
      document.getElementById("key-groq").value = data.groq || "";
      document.getElementById("key-hf").value = data.huggingface || "";
      document.getElementById("key-openai").value = data.openai || "";
      document.getElementById("key-anthropic").value = data.anthropic || "";
      document.getElementById("key-serpapi").value = data.serpapi || "";
      document.getElementById("key-tavily").value = data.tavily || "";
    }
  } catch (e) {
    console.error("Could not fetch settings", e);
  }
  
  modal.showModal();
}

function closeSettingsModal() {
  document.getElementById("settings-modal").close();
}

async function saveSettings() {
  const payload = {
    gemini: document.getElementById("key-gemini").value,
    groq: document.getElementById("key-groq").value,
    huggingface: document.getElementById("key-hf").value,
    openai: document.getElementById("key-openai").value,
    anthropic: document.getElementById("key-anthropic").value,
    serpapi: document.getElementById("key-serpapi").value,
    tavily: document.getElementById("key-tavily").value,
  };
  
  try {
    const res = await fetch(`${API_BASE}/api/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    
    if (res.ok) {
      showToast("API Keys saved successfully!", "success");
      closeSettingsModal();
      checkHealth(); // Re-check the health to update dots
    } else {
      showToast("Failed to save API keys", "error");
    }
  } catch (e) {
    showToast("Network error saving keys", "error");
  }
}

// ── Dynamic Custom Model Selection ───────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const providerSelect = document.getElementById("custom-provider");
  if (!providerSelect) return;
  
  providerSelect.addEventListener("change", async (e) => {
    const container = document.getElementById("custom-model-id").parentElement;
    clearModelSelection();
    
    if (e.target.value === "lmstudio") {
      let dropdown = document.getElementById("lmstudio-dropdown");
      if (!dropdown) {
        dropdown = document.createElement("select");
        dropdown.id = "lmstudio-dropdown";
        dropdown.className = "input-field";
        dropdown.style.flex = "1";
        dropdown.style.padding = "6px";
        dropdown.style.fontSize = "12px";
        dropdown.style.height = "32px";
        container.insertBefore(dropdown, document.getElementById("custom-model-id"));
      }
      
      document.getElementById("custom-model-id").style.display = "none";
      dropdown.style.display = "block";
      dropdown.innerHTML = `<option value="">Loading models...</option>`;
      
      let loadBtn = document.getElementById("lmstudio-load-btn");
      if (!loadBtn) {
        loadBtn = document.createElement("button");
        loadBtn.id = "lmstudio-load-btn";
        loadBtn.textContent = "Load RAM";
        loadBtn.className = "start-btn";
        loadBtn.style.padding = "6px 12px";
        loadBtn.style.fontSize = "11px";
        loadBtn.style.cursor = "pointer";
        loadBtn.style.background = "#3b82f6";
        loadBtn.onclick = async () => {
          const mod = dropdown.value;
          if(!mod) return;
          loadBtn.textContent = "Loading...";
          try {
            await fetch("/api/lmstudio/load", {
              method: "POST", headers:{"Content-Type":"application/json"},
              body: JSON.stringify({model: mod})
            });
            showToast("Model loaded into RAM", "success");
          } catch(err) { showToast("Load failed", "error"); }
          loadBtn.textContent = "Load RAM";
        };
        container.appendChild(loadBtn);
      }
      loadBtn.style.display = "block";
      
      try {
        const res = await fetch("/api/lmstudio/models");
        const data = await res.json();
        
        let modelList = [];
        if (data && data.data) modelList = data.data; // OpenAI format
        else if (data && data.models) modelList = data.models; // LM Studio API format
        
        if (modelList && modelList.length > 0) {
          dropdown.innerHTML = modelList.map(m => {
            const val = m.id || m.key;
            const name = m.display_name || m.id || m.key;
            return `<option value="${val}">${name}</option>`;
          }).join("");
        } else {
          dropdown.innerHTML = `<option value="">No models found</option>`;
        }
      } catch(err) {
        dropdown.innerHTML = `<option value="">Error connecting LM Studio</option>`;
      }
    } else {
      document.getElementById("custom-model-id").style.display = "block";
      const dropdown = document.getElementById("lmstudio-dropdown");
      if (dropdown) dropdown.style.display = "none";
      const loadBtn = document.getElementById("lmstudio-load-btn");
      if (loadBtn) loadBtn.style.display = "none";
    }
  });
});
