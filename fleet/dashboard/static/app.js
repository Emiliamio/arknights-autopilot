/**
 * ASTA - PRTS Tactical Command Dashboard Client Logic
 * Real-time SSE Telemetry, 2.5D Isometric Canvas, Scatter Plot, and Overrides
 * Author: Emiliamio <mio2110767128@163.com>
 */

let sseSource = null;
let currentTelemetry = null;
let animFrameId = null;

// Map Dimensions for 1-7 (11 cols x 6 rows)
const GRID_COLS = 11;
const GRID_ROWS = 6;

// High-ground tiles for 1-7
const HIGH_GROUND_TILES = new Set([
  "3,1", "3,2", "3,3",
  "4,1", "4,2", "4,3",
  "6,2", "6,3",
  "7,2", "7,3"
]);

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
  console.log("[ASTA] Initializing PRTS Command Dashboard...");
  initSSE();
  initCanvasAnimation();
  fetchAccounts();
  fetchFleet();
  fetchMissions();
  fetchStagesCatalog().then(() => {
    renderCategoryOptions();
    searchCloudPlans();
  });
});

// 1. SSE Real-time Event Pipeline
function initSSE() {
  const connStatus = document.getElementById("connStatus");
  const indicator = connStatus.querySelector(".status-indicator");
  const text = connStatus.querySelector(".status-text");

  try {
    sseSource = new EventSource("/api/stream");

    sseSource.addEventListener("telemetry", (e) => {
      try {
        const data = JSON.parse(e.data);
        currentTelemetry = data;
        updateHUD(data);
      } catch (err) {
        console.error("[ASTA] Failed to parse telemetry event:", err);
      }
    });

    sseSource.onopen = () => {
      indicator.className = "status-indicator online";
      text.textContent = "SSE LINK ACTIVE";
    };

    sseSource.onerror = () => {
      indicator.className = "status-indicator offline";
      text.textContent = "LINK RETRYING...";
      // Fallback to manual polling if SSE breaks
      setTimeout(fetchTelemetryFallback, 2000);
    };
  } catch (e) {
    console.warn("[ASTA] EventSource error, falling back to polling:", e);
    setInterval(fetchTelemetryFallback, 1000);
    setInterval(fetchFleet, 3000);
  }
}

async function fetchTelemetryFallback() {
  try {
    const res = await fetch("/api/telemetry");
    if (res.ok) {
      const data = await res.json();
      currentTelemetry = data;
      updateHUD(data);
    }
  } catch (e) {
    console.error("[ASTA] Fallback polling failed:", e);
  }
}

// 2. Fetch Commercial Fleet & Accounts
async function fetchAccounts() {
  try {
    const res = await fetch("/api/accounts");
    if (res.ok) {
      const data = await res.json();
      renderAccounts(data.accounts || []);
      const tag = document.getElementById("accountCountTag");
      if (tag) tag.textContent = `${data.total || 0} ENROLLED`;
    }
  } catch (e) {
    console.error("[ASTA] Failed to fetch accounts:", e);
  }
}

async function fetchFleet() {
  try {
    const res = await fetch("/api/fleet");
    if (res.ok) {
      const data = await res.json();
      renderMuMuList(data);
    }
  } catch (e) {
    console.error("[ASTA] Failed to fetch fleet:", e);
  }
}

// 3. Render Fleet UI Elements
function renderAccounts(accounts) {
  const list = document.getElementById("accountsList");
  if (!list) return;

  const modalSelect = document.getElementById("modalAccSelect");
  const squadSelect = document.getElementById("squadAccSelect");
  const cloudSelect = document.getElementById("cloudAccSelect");
  if (accounts.length > 0) {
    const opts = accounts.map(acc => `<option value="${acc.account_id}">${acc.account_id} (${acc.client_name || 'Client'})</option>`).join("");
    if (modalSelect) modalSelect.innerHTML = opts;
    if (squadSelect) squadSelect.innerHTML = opts;
    if (cloudSelect) cloudSelect.innerHTML = opts;
  }

  list.innerHTML = accounts.map(acc => {
    const isSvip = acc.service_tier === "SVIP";
    const tierClass = isSvip ? "tier-svip" : "tier-monthly";
    const isBili = (acc.platform || '').toUpperCase() === 'BILIBILI';
    const platformTag = isBili ? '<span class="platform-bili">B服</span>' : '<span class="platform-official">官服</span>';
    const sanity = acc.daily_sanity_consumed || 0;
    const maxSanity = 240;
    const sanityPct = Math.min(100, Math.round((sanity / maxSanity) * 100));

    return `
      <div class="account-card">
        <div class="acc-header">
          <div style="display: flex; gap: 6px; align-items: center;">
            <span class="acc-id">${acc.account_id}</span>
            ${platformTag}
            <span class="${tierClass}">${acc.service_tier}</span>
          </div>
          ${acc.account_id !== 'EMILIAMIO_MAIN' ? `<button class="btn-tiny btn-delete" title="注销客户档案" onclick="deleteAccount('${acc.account_id}')">✕</button>` : '<small style="color: #00e676; font-size: 9px;">MASTER</small>'}
        </div>
        <div class="acc-body">
          <div>Client: <strong>${acc.client_name || 'Standard Client'}</strong></div>
          <div>Binding: <span style="color: #ffd600;">VM [${acc.assigned_instance ?? 0}]</span> | Status: <span style="color: #00e5ff;">${acc.current_status}</span></div>
          <div>Farmed Sanity: ${sanity} / ${maxSanity}</div>
          <div class="sanity-bar-wrap">
            <div class="sanity-bar-fill" style="width: ${sanityPct}%;"></div>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function renderMuMuList(data) {
  const list = document.getElementById("mumuList");
  if (!list) return;

  const slots = (data && data.slots) ? data.slots : [];
  if (slots.length === 0) {
    list.innerHTML = `<span class="mumu-tag">VM [0]: 127.0.0.1:16384 ● READY</span>`;
    return;
  }

  list.innerHTML = slots.map(slot => {
    const isRunning = slot.status === "RUNNING";
    const statusBadge = isRunning
      ? '<span class="step-badge badge-current" style="animation: pulse 1s infinite;">● RUNNING</span>'
      : '<span class="step-badge badge-pending">IDLE</span>';
    const activeInfo = slot.current_account
      ? `<span style="color: #00e5ff;">Acc: <strong>${slot.current_account}</strong> ➔ ${slot.current_mission_type || ''}</span>`
      : `<span style="color: #484f58;">Slot Idle (空闲待命)</span>`;

    return `
      <div class="mumu-vm-card ${isRunning ? 'vm-running' : ''}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <strong style="color: #fff; font-size: 12px;">VM [${slot.instance_index}]: ${slot.name}</strong>
          ${statusBadge}
        </div>
        <div style="color: #8b949e; font-size: 10px; margin-top: 4px;">
          Port: <strong style="color: #ffd600;">${slot.port}</strong> · 15FPS / 550MB
        </div>
        <div style="font-size: 10px; margin-top: 3px;">
          ${activeInfo}
        </div>
      </div>
    `;
  }).join("");
}

// 4. Update HUD Telemetry
function updateHUD(data) {
  if (!data) return;

  const tel = data.telemetry || {};
  const stage = data.stage || {};

  // Mission
  const stageTitleEl = document.getElementById("stageTitle");
  if (stageTitleEl && stage.title) {
    stageTitleEl.textContent = `${stage.id} ${stage.title}`;
  }

  // DP
  if (tel.dp !== undefined) {
    const dpEl = document.getElementById("dpVal");
    if (dpEl) dpEl.textContent = tel.dp;
    const dpFill = document.getElementById("dpFill");
    if (dpFill) {
      const pct = Math.min(100, Math.round((tel.dp / (tel.max_dp || 99)) * 100));
      dpFill.style.width = `${pct}%`;
    }
  }

  // Kills
  if (tel.kill_count) {
    const cur = tel.kill_count[0] || 0;
    const tot = tel.kill_count[1] || 28;
    const curEl = document.getElementById("killCurrent");
    if (curEl) curEl.textContent = cur;
    const totEl = document.getElementById("killTotal");
    if (totEl) totEl.textContent = tot;
    const killFill = document.getElementById("killFill");
    if (killFill) {
      const killPct = Math.min(100, Math.round((cur / tot) * 100));
      killFill.style.width = `${killPct}%`;
    }
  }

  // States
  if (tel.battle_state) {
    const bs = document.getElementById("battleState");
    if (bs) bs.textContent = tel.battle_state;
  }
  if (tel.speed_2x !== undefined) {
    const sp = document.getElementById("speed2x");
    if (sp) sp.textContent = `2X SPEED: ${tel.speed_2x ? 'ON' : 'OFF'}`;
  }

  // Threat Banner
  const banner = document.getElementById("threatBanner");
  const threatText = document.getElementById("threatText");
  const threatDesc = document.getElementById("threatDesc");
  if (banner && threatText && threatDesc) {
    if (tel.threat_level === "PANIC_LEAK") {
      banner.className = "threat-banner panic";
      threatText.textContent = "PANIC_LEAK (0.37ms PREEMPT)";
      threatDesc.textContent = "探测到敌军逼近蓝门 (<=2格)！应急截停守护进程已抢占触控 I/O！";
    } else {
      banner.className = "threat-banner safe";
      threatText.textContent = "SAFE";
      threatDesc.textContent = "战场防线稳固，未探测到突破蓝门临界威胁";
    }
  }

  // Deployed Operators
  renderDeployedOps(data.operators || []);

  // Copilot Steps
  renderCopilot(data.copilot || {});

  // Anti-Cheat Stats
  if (data.anti_cheat) {
    document.getElementById("bezierMs").textContent = `${data.anti_cheat.bezier_motion_ms || 338} ms (Humanized)`;
    document.getElementById("adbLatency").textContent = `${data.anti_cheat.adb_latency_ms || 170} ms`;
    renderScatterPlot(data.anti_cheat.touch_scatter || []);
  }

  // Terminal Logs
  renderLogs(data.logs || []);
}

function renderDeployedOps(ops) {
  const container = document.getElementById("operatorsList");
  if (!container) return;

  container.innerHTML = ops.map(op => `
    <div class="op-card">
      <div class="op-info">
        <span class="op-name">${op.name}</span>
        <span class="op-role">${op.role}</span>
        <span style="color: #8b949e;">Tile: (${op.tile[0]}, ${op.tile[1]}) ➔ ${op.orientation}</span>
      </div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <span class="op-hp">HP: ${op.hp_percent}%</span>
        ${op.sp_ready ? '<span class="op-sp-ready">⚡ SP READY</span>' : '<span style="color: #484f58;">SP CHARGING</span>'}
      </div>
    </div>
  `).join("");
}

function renderCopilot(copilot) {
  const container = document.getElementById("timelineSteps");
  const planName = document.getElementById("copilotPlanName");
  if (planName && copilot.name) planName.textContent = copilot.name;

  if (container && copilot.steps) {
    container.innerHTML = copilot.steps.map(step => {
      let rowClass = "step-row";
      let badgeClass = "badge-pending";
      if (step.status === "CURRENT") {
        rowClass += " current";
        badgeClass = "badge-current";
      } else if (step.status === "DEPLOYED") {
        rowClass += " deployed";
        badgeClass = "badge-deployed";
      }

      return `
        <div class="${rowClass}">
          <span>#${step.step} <strong>${step.name}</strong> [${step.action}] ➔ (${step.tile[0]}, ${step.tile[1]})</span>
          <span class="step-badge ${badgeClass}">${step.status} (DP: ${step.cost})</span>
        </div>
      `;
    }).join("");
  }

  const emContainer = document.getElementById("emergencyCards");
  if (emContainer && copilot.emergency_reserves) {
    emContainer.innerHTML = copilot.emergency_reserves.map(em => `
      <div class="em-card ${em.ready ? 'ready' : 'cooldown'}">
        <div style="display: flex; justify-content: space-between;">
          <strong>${em.name}</strong>
          <span class="em-status">${em.ready ? 'READY' : `${em.cooldown_sec}s`}</span>
        </div>
        <div style="color: #8b949e; font-size: 10px;">${em.role} · Cost: ${em.cost}</div>
      </div>
    `).join("");
  }
}

function renderLogs(logs) {
  const box = document.getElementById("terminalLog");
  if (!box) return;

  const atBottom = box.scrollHeight - box.scrollTop <= box.clientHeight + 20;

  box.innerHTML = logs.map(l => `
    <div class="log-entry">
      <span class="log-time">[${l.time}]</span>
      <span class="log-level-${l.level}">[${l.level}]</span>
      <span class="log-msg">${l.msg}</span>
    </div>
  `).join("");

  if (atBottom) {
    box.scrollTop = box.scrollHeight;
  }
}

// 5. Canvas 2.5D Isometric Battlefield Visualizer
function initCanvasAnimation() {
  const canvas = document.getElementById("battlefieldCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let particleOffset = 0;

  function renderLoop() {
    particleOffset = (particleOffset + 0.5) % 30;
    drawBattlefield(ctx, canvas.width, canvas.height, particleOffset);
    animFrameId = requestAnimationFrame(renderLoop);
  }

  renderLoop();
}

function drawBattlefield(ctx, w, h, particleOffset) {
  ctx.clearRect(0, 0, w, h);

  // Background Grid Matrix
  ctx.fillStyle = "#05080c";
  ctx.fillRect(0, 0, w, h);

  // Isometric Projection Parameters
  const originX = w * 0.5;
  const originY = h * 0.18;
  const tileW = 54;
  const tileH = 28;

  function toIso(col, row, z = 0) {
    const x = originX + (col - row) * (tileW * 0.5);
    const y = originY + (col + row) * (tileH * 0.5) - z;
    return { x, y };
  }

  // Draw Tiles
  for (let r = 0; r < GRID_ROWS; r++) {
    for (let c = 0; c < GRID_COLS; c++) {
      const key = `${c},${r}`;
      const isHigh = HIGH_GROUND_TILES.has(key);
      const isGoal = (c === 9 && r === 4);
      const isSpawn = (c === 1 && (r === 4 || r === 2));
      const isChoke = (c === 3 && r === 4);

      const z = isHigh ? 16 : 0;
      const p0 = toIso(c, r, z);
      const p1 = toIso(c + 1, r, z);
      const p2 = toIso(c + 1, r + 1, z);
      const p3 = toIso(c, r + 1, z);

      ctx.beginPath();
      ctx.moveTo(p0.x, p0.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.lineTo(p3.x, p3.y);
      ctx.closePath();

      // Styling based on tile role
      if (isGoal) {
        ctx.fillStyle = "rgba(41, 121, 255, 0.4)";
        ctx.strokeStyle = "#2979ff";
        ctx.lineWidth = 2;
      } else if (isSpawn) {
        ctx.fillStyle = "rgba(255, 23, 68, 0.4)";
        ctx.strokeStyle = "#ff1744";
        ctx.lineWidth = 2;
      } else if (isChoke) {
        ctx.fillStyle = "rgba(255, 214, 0, 0.35)";
        ctx.strokeStyle = "#ffd600";
        ctx.lineWidth = 2;
      } else if (isHigh) {
        ctx.fillStyle = "rgba(0, 229, 255, 0.15)";
        ctx.strokeStyle = "rgba(0, 229, 255, 0.4)";
        ctx.lineWidth = 1;
      } else {
        ctx.fillStyle = "rgba(255, 255, 255, 0.03)";
        ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
        ctx.lineWidth = 1;
      }

      ctx.fill();
      ctx.stroke();

      // High ground side extrusion for 2.5D depth
      if (isHigh) {
        const p2_base = toIso(c + 1, r + 1, 0);
        const p3_base = toIso(c, r + 1, 0);
        ctx.beginPath();
        ctx.moveTo(p3.x, p3.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.lineTo(p2_base.x, p2_base.y);
        ctx.lineTo(p3_base.x, p3_base.y);
        ctx.closePath();
        ctx.fillStyle = "rgba(0, 229, 255, 0.08)";
        ctx.fill();
      }
    }
  }

  // Draw A* DAG Network Flow Stream from (1, 4) to (9, 4)
  const path = [
    [1, 4], [2, 4], [3, 4], [4, 4], [5, 4], [6, 4], [7, 4], [8, 4], [9, 4]
  ];

  ctx.beginPath();
  ctx.setLineDash([8, 6]);
  ctx.lineDashOffset = -particleOffset;
  ctx.strokeStyle = "rgba(0, 229, 255, 0.8)";
  ctx.lineWidth = 3;

  for (let i = 0; i < path.length; i++) {
    const center = toIso(path[i][0] + 0.5, path[i][1] + 0.5, 0);
    if (i === 0) ctx.moveTo(center.x, center.y);
    else ctx.lineTo(center.x, center.y);
  }
  ctx.stroke();
  ctx.setLineDash([]); // Reset line dash

  // Draw Deployed Operators on Grid
  if (currentTelemetry && currentTelemetry.operators) {
    currentTelemetry.operators.forEach(op => {
      const isHigh = HIGH_GROUND_TILES.has(`${op.tile[0]},${op.tile[1]}`);
      const z = isHigh ? 16 : 0;
      const pt = toIso(op.tile[0] + 0.5, op.tile[1] + 0.5, z);

      // Operator Avatar Base
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 9, 0, Math.PI * 2);
      ctx.fillStyle = "#00e676";
      ctx.shadowColor = "#00e676";
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Operator Label
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 10px monospace";
      ctx.textAlign = "center";
      ctx.fillText(op.name, pt.x, pt.y - 12);
    });
  }

  // Draw Threat Blob if in PANIC mode
  if (currentTelemetry && currentTelemetry.telemetry && currentTelemetry.telemetry.threat_level === "PANIC_LEAK") {
    const enemyPt = toIso(4.2, 4.5, 0);
    ctx.beginPath();
    ctx.arc(enemyPt.x, enemyPt.y, 14, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(255, 23, 68, 0.6)";
    ctx.shadowColor = "#ff1744";
    ctx.shadowBlur = 15;
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.fillStyle = "#ff1744";
    ctx.font = "bold 11px monospace";
    ctx.fillText("LEAK TARGET", enemyPt.x, enemyPt.y - 16);
  }
}

// 6. 2D Gaussian Touch Scatter Canvas
function renderScatterPlot(points) {
  const canvas = document.getElementById("scatterCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  const cx = w * 0.5;
  const cy = h * 0.5;
  const scale = 8.0; // 8px limit maps to ~64px radius

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#05080c";
  ctx.fillRect(0, 0, w, h);

  // Draw 8px Boundary Circle
  ctx.beginPath();
  ctx.arc(cx, cy, 8.0 * scale, 0, Math.PI * 2);
  ctx.strokeStyle = "rgba(0, 229, 255, 0.4)";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  ctx.stroke();
  ctx.setLineDash([]);

  // Draw Crosshairs
  ctx.beginPath();
  ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
  ctx.moveTo(cx, 0); ctx.lineTo(cx, h);
  ctx.moveTo(0, cy); ctx.lineTo(w, cy);
  ctx.stroke();

  // Draw Touch Jitter Points
  points.forEach(pt => {
    const px = cx + pt[0] * scale;
    const py = cy + pt[1] * scale;

    ctx.beginPath();
    ctx.arc(px, py, 3, 0, Math.PI * 2);
    ctx.fillStyle = "#00e5ff";
    ctx.shadowColor = "#00e5ff";
    ctx.shadowBlur = 6;
    ctx.fill();
    ctx.shadowBlur = 0;
  });
}

// 7. Tactical Overrides Command Dispatch
async function sendOverride(action) {
  console.log(`[ASTA] Dispatching Tactical Override: ${action}`);
  try {
    const res = await fetch("/api/override", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action })
    });
    if (res.ok) {
      const data = await res.json();
      console.log("[ASTA] Override confirmed:", data);
      fetchTelemetryFallback(); // Instant refresh
    }
  } catch (e) {
    console.error("[ASTA] Override request failed:", e);
  }
}

// 8. Mission Orchestration Functions
async function fetchMissions() {
  try {
    const res = await fetch("/api/missions");
    if (res.ok) {
      const data = await res.json();
      renderMissions(data.missions || []);
    }
  } catch (e) {
    console.error("[ASTA] Failed to fetch missions:", e);
  }
}

function renderMissions(missions) {
  const list = document.getElementById("missionList");
  if (!list) return;

  if (missions.length === 0) {
    list.innerHTML = `<div style="color: #484f58; font-size: 11px; padding: 6px;">暂无排班工单，点击上方 [+ 布置战术任务] 建立新任务。</div>`;
    return;
  }

  list.innerHTML = missions.map(m => {
    let badgeClass = "badge-pending";
    if (m.status === "RUNNING") badgeClass = "badge-current";
    else if (m.status === "COMPLETED") badgeClass = "badge-deployed";
    else if (m.status === "FAILED") badgeClass = "badge-pending";

    let targetDesc = "";
    if (m.mission_type === "CAMPAIGN_CLEAR") {
      targetDesc = `第 ${m.target_chapter ?? 0} 章`;
    } else if (m.mission_type === "COPILOT_CLEAR") {
      targetDesc = `云端作业 [${m.target_stage}]`;
    } else if (m.mission_type === "SANITY_FARM") {
      targetDesc = `关卡 [${m.target_stage}]`;
    }

    let actionsHtml = "";
    if (m.status === "QUEUED") {
      actionsHtml = `
        <span class="step-badge badge-pending">QUEUED</span>
        <button class="btn-tiny btn-run-single" title="立即执行此任务" onclick="runSingleMission('${m.mission_id}')">▶ 执行</button>
        <button class="btn-tiny btn-delete" title="删除此工单" onclick="deleteMission('${m.mission_id}')">✕ 删除</button>
      `;
    } else if (m.status === "RUNNING") {
      actionsHtml = `
        <span class="step-badge badge-current" style="animation: pulse 1s infinite;">● 正在执行</span>
        <button class="btn-tiny btn-delete" title="立即截停此任务" onclick="triggerEmergencyStop()">🛑 停止</button>
      `;
    } else {
      actionsHtml = `
        <span class="step-badge ${badgeClass}">${m.status}</span>
        <button class="btn-tiny btn-delete" title="清理记录" onclick="deleteMission('${m.mission_id}')">✕</button>
      `;
    }

    return `
      <div class="mission-row">
        <div class="mission-left">
          <strong style="color: #00e5ff;">${m.account_id}</strong>
          <span>➔ [${m.mission_type}]</span>
          <span style="color: #ffd600;">${targetDesc}</span>
          <small style="color: #484f58;">${m.mission_id.slice(-8)}</small>
        </div>
        <div class="mission-actions">
          ${actionsHtml}
        </div>
      </div>
    `;
  }).join("");
}

async function runSingleMission(mission_id) {
  console.log(`[ASTA] Running single mission: ${mission_id}`);
  try {
    const res = await fetch("/api/missions/run_single", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mission_id })
    });
    if (res.ok) {
      fetchMissions();
      fetchTelemetryFallback();
    }
  } catch (e) {
    console.error("[ASTA] Run single mission failed:", e);
  }
}

async function deleteMission(mission_id) {
  console.log(`[ASTA] Deleting mission: ${mission_id}`);
  try {
    const res = await fetch("/api/missions/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mission_id })
    });
    if (res.ok) {
      fetchMissions();
      fetchTelemetryFallback();
    }
  } catch (e) {
    console.error("[ASTA] Delete mission failed:", e);
  }
}

async function clearMissions(status) {
  
  console.log(`[ASTA] Clearing missions: ${status}`);
  try {
    const res = await fetch("/api/missions/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status })
    });
    if (res.ok) {
      fetchMissions();
      fetchTelemetryFallback();
    }
  } catch (e) {
    console.error("[ASTA] Clear missions failed:", e);
  }
}

async function triggerRunMissions() {
  console.log("[ASTA] Triggering run queued missions...");
  try {
    const res = await fetch("/api/missions/run", { method: "POST" });
    if (res.ok) {
      fetchMissions();
      fetchTelemetryFallback();
    }
  } catch (e) {
    console.error("[ASTA] Run missions request failed:", e);
  }
}

function openMissionModal() {
  const modal = document.getElementById("missionModal");
  if (modal) modal.style.display = "flex";
}

function closeMissionModal() {
  const modal = document.getElementById("missionModal");
  if (modal) modal.style.display = "none";
}

function toggleMissionTypeFields() {
  const type = document.getElementById("modalTypeSelect").value;
  const chField = document.getElementById("chapterField");
  const stField = document.getElementById("stageField");
  const themeField = document.getElementById("themeField");

  if (type === "CAMPAIGN_CLEAR") {
    chField.style.display = "flex";
    stField.style.display = "none";
    if (themeField) themeField.style.display = "none";
  } else if (type === "COPILOT_CLEAR") {
    chField.style.display = "none";
    stField.style.display = "flex";
    if (themeField) themeField.style.display = "none";
  } else if (type === "ROGUELIKE") {
    chField.style.display = "none";
    stField.style.display = "none";
    if (themeField) themeField.style.display = "flex";
  } else if (type === "SANITY_FARM") {
    chField.style.display = "none";
    stField.style.display = "flex";
    if (themeField) themeField.style.display = "none";
  } else {
    chField.style.display = "none";
    stField.style.display = "none";
    if (themeField) themeField.style.display = "none";
  }
}

async function submitMission() {
  const account_id = document.getElementById("modalAccSelect").value;
  const mission_type = document.getElementById("modalTypeSelect").value;
  const target_chapter = parseInt(document.getElementById("modalChapterSelect").value, 10);
  const target_stage = document.getElementById("modalStageInput").value.trim();

  const theme = document.getElementById("modalThemeSelect") ? document.getElementById("modalThemeSelect").value : "IS4";
  const payload = {
    account_id,
    mission_type,
    target_chapter: mission_type === "CAMPAIGN_CLEAR" ? target_chapter : null,
    target_stage: (mission_type === "SANITY_FARM" || mission_type === "COPILOT_CLEAR") ? target_stage : null,
    params: { auto_skip_story: true, theme, stage: target_stage }
  };

  try {
    const res = await fetch("/api/missions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      closeMissionModal();
      fetchMissions();
      fetchTelemetryFallback();
    }
  } catch (e) {
    console.error("[ASTA] Failed to submit mission:", e);
  }
}

async function triggerEmergencyStop() {
  console.warn("[ASTA] EMERGENCY STOP ACTIVATED IMMEDIATELY BY COMMANDER!");
  try {
    const res = await fetch("/api/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "EMERGENCY_STOP" })
    });
    if (res.ok) {
      const data = await res.json();
      console.log("[ASTA] Stop acknowledged successfully:", data);
      fetchMissions();
      fetchTelemetryFallback();
    }
  } catch (e) {
    console.error("[ASTA] Emergency stop request failed:", e);
  }
}

// 9. Customer Account Management Functions
function openAccountModal() {
  const modal = document.getElementById("accountModal");
  if (modal) modal.style.display = "flex";
}

function closeAccountModal() {
  const modal = document.getElementById("accountModal");
  if (modal) modal.style.display = "none";
}

async function submitNewAccount() {
  const account_id = document.getElementById("modalNewAccId").value.trim();
  const client_name = document.getElementById("modalNewClientName").value.trim();
  const platform = document.getElementById("modalNewPlatform").value;
  const service_tier = document.getElementById("modalNewTier").value;
  const login_account = document.getElementById("modalNewLoginAcc").value.trim();
  const login_password = document.getElementById("modalNewLoginPwd").value.trim();
  const assigned_instance = parseInt(document.getElementById("modalNewVm").value, 10);

  if (!account_id || !client_name) {
    alert("请至少输入账户 ID 与客户备注！");
    return;
  }

  const payload = {
    account_id,
    client_name,
    platform,
    service_tier,
    login_account,
    login_password,
    assigned_instance
  };

  try {
    const res = await fetch("/api/accounts/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      closeAccountModal();
      fetchAccounts();
      fetchTelemetryFallback();
    }
  } catch (e) {
    console.error("[ASTA] Create account failed:", e);
  }
}

async function deleteAccount(account_id) {
  
  try {
    const res = await fetch("/api/accounts/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ account_id })
    });
    if (res.ok) {
      fetchAccounts();
      fetchTelemetryFallback();
    }
  } catch (e) {
    console.error("[ASTA] Delete account failed:", e);
  }
}

// 10. Squad Synthesis Functions
function openSquadModal() {
  const modal = document.getElementById("squadModal");
  if (modal) modal.style.display = "flex";
}

function closeSquadModal() {
  const modal = document.getElementById("squadModal");
  if (modal) modal.style.display = "none";
}

async function triggerSquadSynthesis() {
  const account_id = document.getElementById("squadAccSelect").value;
  const stage_id = document.getElementById("squadStageInput").value.trim() || "1-7";
  console.log(`[ASTA] Synthesizing squad for ${account_id} on ${stage_id}...`);

  try {
    const res = await fetch("/api/squad/synthesize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ account_id, stage_id })
    });
    if (res.ok) {
      const data = await res.json();
      renderSquadResults(data);
      fetchTelemetryFallback();
    }
  } catch (e) {
    console.error("[ASTA] Squad synthesis failed:", e);
  }
}

function renderSquadResults(data) {
  const summary = document.getElementById("squadSummaryText");
  const grid = document.getElementById("squadSlotsGrid");
  if (!grid) return;

  if (summary && data.summary) {
    summary.style.display = "block";
    summary.textContent = `[+] 战术策略: ${data.summary}`;
  }

  const squad = data.squad || [];
  grid.innerHTML = squad.map(op => `
    <div class="account-card" style="padding: 8px; font-size: 11px;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="color: #8b949e;">#${op.slot}</span>
        <strong style="color: #fff;">${op.name}</strong>
        <span style="color: #ffd600;">★${op.rarity}</span>
      </div>
      <div style="display: flex; justify-content: space-between; margin-top: 4px; color: #8b949e; font-size: 10px;">
        <span class="tag-cyan" style="font-size: 9px; padding: 1px 4px;">${op.class}</span>
        <span>Cost: ${op.cost}</span>
        <span style="color: #00e676;">Score: ${op.score}</span>
      </div>
    </div>
  `).join("");
}

// 11. Cloud Copilot Hub (Episodes 00-17 / Events / Resources & Online Plans)
let stagesCatalog = null;
let currentCloudPlans = [];

async function fetchStagesCatalog() {
  try {
    const res = await fetch("/api/stages/catalog");
    if (res.ok) {
      stagesCatalog = await res.json();
      console.log("[ASTA] Stages catalog loaded:", stagesCatalog);
    }
  } catch (e) {
    console.error("[ASTA] Failed to fetch stages catalog:", e);
  }
}

function openCloudCopilotModal() {
  console.log("[ASTA] openCloudCopilotModal triggered - focusing stage selector");
  const panel = document.querySelector(".panel-stage-selector");
  if (panel) {
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  const input = document.getElementById("customStageInput");
  if (input) {
    input.focus();
    input.select();
  }
  if (!stagesCatalog) {
    fetchStagesCatalog().then(() => {
      renderCategoryOptions();
    });
  }
}

function closeCloudCopilotModal() {
  // Modal is now integrated directly into Panel 1 & 2
  const modal = document.getElementById("cloudCopilotModal");
  if (modal) modal.style.display = "none";
}

function quickSelectStage(stage) {
  const input = document.getElementById("customStageInput");
  if (input) input.value = stage;
  const badge = document.getElementById("selectedStageBadge");
  if (badge) badge.textContent = `TARGET: ${stage}`;
  searchCloudPlans();
}

function renderCategoryOptions() {
  if (!stagesCatalog) return;
  onCategoryChanged();
}

function onCategoryChanged() {
  if (!stagesCatalog) return;
  const cat = document.getElementById("stageCategorySelect").value;
  const chSelect = document.getElementById("chapterSelect");
  const label = document.getElementById("chapterSelectLabel");
  if (!chSelect) return;

  if (cat === "main") {
    label.textContent = "所属主线章节 (EPISODE 00-17):";
    const chs = stagesCatalog.main_theme || [];
    chSelect.innerHTML = chs.map(c => `<option value="${c.chapter}">${c.title} (${c.stages_count}关 · Boss: ${c.boss})</option>`).join("");
  } else if (cat === "events") {
    label.textContent = "所属 SideStory / 故事集活动:";
    const evs = stagesCatalog.events || [];
    chSelect.innerHTML = evs.map((e, idx) => `<option value="EVENT_${idx}">${e.name} [${e.code}] (${e.stages.length}关)</option>`).join("");
  } else if (cat === "resources") {
    label.textContent = "所属物资 / 芯片 / 剿灭类别:";
    const resList = stagesCatalog.resources || [];
    chSelect.innerHTML = resList.map((r, idx) => `<option value="RES_${idx}">${r.category} (${r.stages.length}关)</option>`).join("");
  }
  onChapterChanged();
}

function onChapterChanged() {
  if (!stagesCatalog) return;
  const cat = document.getElementById("stageCategorySelect").value;
  const chVal = document.getElementById("chapterSelect").value;
  const stSelect = document.getElementById("stageSelect");
  if (!stSelect) return;

  let stages = [];
  if (cat === "main") {
    const chNum = parseInt(chVal, 10);
    const item = (stagesCatalog.main_theme || []).find(c => c.chapter === chNum);
    stages = item ? item.stages : [];
  } else if (cat === "events") {
    const idx = parseInt(chVal.replace("EVENT_", ""), 10);
    const item = (stagesCatalog.events || [])[idx];
    stages = item ? item.stages : [];
  } else if (cat === "resources") {
    const idx = parseInt(chVal.replace("RES_", ""), 10);
    const item = (stagesCatalog.resources || [])[idx];
    stages = item ? item.stages : [];
  }

  if (stages && stages.length > 0) {
    stSelect.innerHTML = stages.map(s => `<option value="${s}">${s}</option>`).join("");
    onStageSelectChanged();
  } else {
    stSelect.innerHTML = `<option value="1-7">1-7</option>`;
  }
}

function onStageSelectChanged() {
  const st = document.getElementById("stageSelect").value;
  const input = document.getElementById("customStageInput");
  if (input && st) {
    input.value = st;
  }
}

async function searchCloudPlans() {
  const stage = (document.getElementById("customStageInput").value || "1-7").trim().toUpperCase();
  const statusEl = document.getElementById("cloudSearchStatus");
  const listEl = document.getElementById("cloudPlansList");

  if (statusEl) {
    statusEl.innerHTML = `📡 正在联网查询 PRTS / MAA 作业库关卡 <strong>[${stage}]</strong> 的云端高赞作业...`;
  }
  if (listEl) {
    listEl.innerHTML = `<div class="cloud-empty-state"><span class="pulse-dot" style="display:inline-block; margin-right:6px;"></span> 正在解析云端战术作业矩阵...</div>`;
  }

  try {
    const res = await fetch(`/api/copilot/cloud/search?stage=${encodeURIComponent(stage)}&page=1&limit=10`);
    if (res.ok) {
      const data = await res.json();
      currentCloudPlans = data.plans || [];
      renderCloudPlans(data, stage);
    } else {
      if (statusEl) statusEl.textContent = `❌ 查询失败: HTTP ${res.status}`;
    }
  } catch (e) {
    console.error("[ASTA] Failed to search cloud plans:", e);
    if (statusEl) statusEl.textContent = `❌ 联网查询异常: ${e.message}`;
  }
}

function renderCloudPlans(data, stage) {
  const statusEl = document.getElementById("cloudSearchStatus");
  const listEl = document.getElementById("cloudPlansList");
  if (!listEl) return;

  const plans = data.plans || [];
  const plansBadge = document.getElementById("plansCountBadge");
  if (plansBadge) {
    plansBadge.textContent = `${plans.length} PLANS`;
  }
  const stageBadge = document.getElementById("selectedStageBadge");
  if (stageBadge) {
    stageBadge.textContent = `TARGET: ${stage}`;
  }

  if (statusEl) {
    statusEl.innerHTML = `✅ 成功检索到 <strong>${data.total || plans.length}</strong> 套关于关卡 <strong>[${stage}]</strong> 的战术作业 (耗时: ${data.source || 'PRTS Cloud'})`;
  }

  if (plans.length === 0) {
    listEl.innerHTML = `
      <div class="cloud-empty-state">
        <div>未发现专门针对 [${stage}] 的第三方高赞作业。</div>
        <div style="margin-top: 6px; color: #ffd600;">您可以直接点击【🚀 一键优选开打】，系统将自构基线通用战术方案执行通关！</div>
      </div>
    `;
    return;
  }

  listEl.innerHTML = plans.map(p => {
    const ops = (p.operators || []).slice(0, 8);
    const opsPills = ops.map(op => `<span class="cloud-op-pill">${op}</span>`).join("");
    const planIdStr = p.id ? String(p.id) : "";
    const likesStr = p.likes != null ? p.likes : 0;
    const viewsStr = p.views != null ? p.views : 0;

    return `
      <div class="cloud-plan-card">
        <div class="cloud-plan-header">
          <div class="cloud-plan-title">${p.title || 'MAA 智能通关作业'}</div>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-skill" style="padding: 3px 10px; font-size: 11px;" onclick="dispatchSpecificCloudPlan('${planIdStr}', '${stage}')">▶ 选用并执行</button>
          </div>
        </div>
        <div class="cloud-plan-meta">
          <span class="badge-author">👤 ${p.author || 'MAA社区干员'}</span>
          <span class="badge-likes">👍 ${likesStr} 赞</span>
          <span class="badge-views">👁️ ${viewsStr} 浏览</span>
          <span style="color: #484f58;">ID: ${planIdStr.slice(-8)}</span>
        </div>
        ${p.description ? `<div class="cloud-plan-desc">${p.description}</div>` : ''}
        ${opsPills ? `<div class="cloud-plan-operators">${opsPills}</div>` : ''}
      </div>
    `;
  }).join("");
}

async function dispatchSpecificCloudPlan(planId, stage) {
  const account_id = document.getElementById("cloudAccSelect").value;
  console.log(`[ASTA] Dispatching specific plan ${planId} for ${stage} on ${account_id}...`);
  try {
    const res = await fetch("/api/copilot/auto_dispatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id,
        stage_name: stage,
        plan_id: planId
      })
    });
    if (res.ok) {
      const data = await res.json();
      closeCloudCopilotModal();
      fetchMissions();
      fetchTelemetryFallback();
      alert(`🚀 [云端作业下发成功]\n已将作业绑定至工单 [${data.mission_id}] 并即刻启动！\n可在大屏面板 04 观测战术推演。`);
    } else {
      alert("❌ 下发失败，请查看控制台日志。");
    }
  } catch (e) {
    console.error("[ASTA] Failed to dispatch specific plan:", e);
    alert(`❌ 请求异常: ${e.message}`);
  }
}

async function autoDispatchBestPlan() {
  const account_id = document.getElementById("cloudAccSelect").value;
  const stage = (document.getElementById("customStageInput").value || "1-7").trim().toUpperCase();
  console.log(`[ASTA] Auto resolving best plan for ${stage} on ${account_id}...`);

  try {
    const res = await fetch("/api/copilot/auto_dispatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id,
        stage_name: stage
      })
    });
    if (res.ok) {
      const data = await res.json();
      closeCloudCopilotModal();
      fetchMissions();
      fetchTelemetryFallback();
      alert(`🚀 [智能优选通关已启动]\n关卡: [${stage}]\n匹配作业: ${data.plan_title}\n工单编号: ${data.mission_id}\n任务已派发至执行机队！`);
    } else {
      alert("❌ 智能优选下发失败，请查看服务控制台。");
    }
  } catch (e) {
    console.error("[ASTA] Auto dispatch best plan error:", e);
    alert(`❌ 请求异常: ${e.message}`);
  }
}

// Explicit global window bindings for inline HTML onclick handlers
window.openCloudCopilotModal = openCloudCopilotModal;
window.closeCloudCopilotModal = closeCloudCopilotModal;
window.quickSelectStage = quickSelectStage;
window.onCategoryChanged = onCategoryChanged;
window.onChapterChanged = onChapterChanged;
window.onStageSelectChanged = onStageSelectChanged;
window.searchCloudPlans = searchCloudPlans;
window.autoDispatchBestPlan = autoDispatchBestPlan;
window.dispatchSpecificCloudPlan = dispatchSpecificCloudPlan;


