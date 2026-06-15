const POLL_INTERVAL = 3000;
const container = document.getElementById("apps-container");
let openLogs = new Set();
let activeLogTab = {};
let expandedApps = new Set();
let draggedId = null;
let justDragged = false;

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

async function fetchApps() {
  const res = await fetch("/api/apps");
  if (!res.ok) throw new Error("Failed to fetch apps");
  return res.json();
}

async function appAction(appId, action, btn) {
  btn.disabled = true;
  try {
    const res = await fetch(`/api/apps/${appId}/${action}`, { method: "POST" });
    if (!res.ok) {
      const data = await res.json();
      alert(data.detail || "Action failed");
    }
  } catch (e) {
    alert("Request failed: " + e.message);
  }
  setTimeout(refreshApps, 500);
}

async function toggleAutostart(appId) {
  try {
    const res = await fetch(`/api/apps/${appId}/autostart`, { method: "PUT" });
    if (!res.ok) return;
    const data = await res.json();
    const card = document.getElementById(`card-${appId}`);
    if (!card) return;

    const btn = card.querySelector("[data-autostart]");
    btn.textContent = data.autostart ? "Disable Auto-start" : "Enable Auto-start";
    btn.classList.toggle("active", data.autostart);

    const header = card.querySelector(".app-header");
    const badge = header.querySelector(".autostart-badge");
    if (data.autostart && !badge) {
      const arrow = header.querySelector(".expand-arrow");
      arrow.insertAdjacentHTML(
        "beforebegin",
        '<span class="autostart-badge">auto-start</span>'
      );
    } else if (!data.autostart && badge) {
      badge.remove();
    }
  } catch (e) {
    alert("Failed to toggle auto-start");
  }
}

async function fetchServiceLog(appId, serviceName) {
  const res = await fetch(`/api/apps/${appId}/logs?service=${serviceName}`);
  if (!res.ok) return {};
  return res.json();
}

function toggleExpand(appId) {
  const details = document.querySelector(`#card-${appId} .app-details`);
  if (!details) return;

  if (expandedApps.has(appId)) {
    expandedApps.delete(appId);
    details.classList.remove("expanded");
  } else {
    expandedApps.add(appId);
    details.classList.add("expanded");
  }
}

function toggleLog(appId) {
  const slot = document.getElementById(`log-${appId}`);
  if (!slot) return;

  if (openLogs.has(appId)) {
    openLogs.delete(appId);
    delete activeLogTab[appId];
    slot.innerHTML = "";
  } else {
    openLogs.add(appId);
    const services = JSON.parse(slot.dataset.services);
    activeLogTab[appId] = services[0];
    renderLogPanel(appId, services);
    refreshLog(appId, activeLogTab[appId]);
  }
}

function renderLogPanel(appId, services) {
  const slot = document.getElementById(`log-${appId}`);
  const multiService = services.length > 1;

  const tabsHtml = multiService
    ? `<div class="logs-tabs">${services
        .map(
          (s) =>
            `<button class="logs-tab ${
              s === activeLogTab[appId] ? "active" : ""
            }" data-tab-service="${s}">${s}</button>`
        )
        .join("")}</div>`
    : "";

  slot.innerHTML = `<div class="logs-panel">${tabsHtml}<div class="log-service-label">${activeLogTab[appId]}</div><pre>Loading...</pre></div>`;

  if (multiService) {
    slot.querySelectorAll(".logs-tab").forEach((tab) => {
      tab.addEventListener("click", (e) => {
        e.stopPropagation();
        activeLogTab[appId] = tab.dataset.tabService;
        slot
          .querySelectorAll(".logs-tab")
          .forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        slot.querySelector(".log-service-label").textContent = tab.dataset.tabService;
        slot.querySelector("pre").textContent = "Loading...";
        refreshLog(appId, tab.dataset.tabService);
      });
    });
  }
}

async function refreshLog(appId, serviceName) {
  const slot = document.getElementById(`log-${appId}`);
  if (!slot || !openLogs.has(appId)) return;

  const logs = await fetchServiceLog(appId, serviceName);
  const text = logs[serviceName] || "(no output)";

  if (activeLogTab[appId] !== serviceName) return;

  const panel = slot.querySelector(".logs-panel");
  if (!panel) return;

  const wasAtBottom =
    panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 10;
  panel.querySelector("pre").textContent = text;

  if (wasAtBottom) {
    panel.scrollTop = panel.scrollHeight;
  }
}

async function saveOrder() {
  const ids = [...container.querySelectorAll(".app-card")].map(
    (c) => c.dataset.appId
  );
  await fetch("/api/apps/order", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ids),
  });
}

function buildCard(app) {
  const card = document.createElement("div");
  card.className = `app-card status-${app.status}`;
  card.id = `card-${app.id}`;
  card.dataset.appId = app.id;
  card.draggable = true;

  const multiService = app.services.length > 1;

  const servicesHtml = app.services
    .map(
      (s) => `
    <div class="service-row" data-service="${escapeHtml(s.name)}">
      <span class="service-dot ${s.running ? "running" : "stopped"}"></span>
      <span class="service-name">${escapeHtml(s.name)}</span>
      <span class="service-port">:${parseInt(s.port, 10) || 0}</span>
    </div>`
    )
    .join("");

  const logButtonHtml = `<button class="btn btn-logs" data-log-toggle="${app.id}">Logs</button>`;
  const serviceNames = JSON.stringify(app.services.map((s) => s.name));
  const logSlotHtml = `<div class="log-slot" id="log-${app.id}" data-services='${serviceNames}'></div>`;

  const isRunning = app.status === "running";
  const isStopped = app.status === "stopped";
  const isExpanded = expandedApps.has(app.id);

  card.innerHTML = `
    <div class="app-header" data-expand="${app.id}">
      <span class="drag-handle">&#x2630;</span>
      <span class="status-dot ${app.status}"></span>
      <span class="app-name">${escapeHtml(app.name)}</span>
      ${(app.tags || []).map((t) => `<span class="tag-badge">${escapeHtml(t)}</span>`).join("")}
      ${app.autostart ? '<span class="autostart-badge">auto-start</span>' : ""}
      <span class="expand-arrow">${isExpanded ? "&#9650;" : "&#9660;"}</span>
    </div>
    <div class="app-details ${isExpanded ? "expanded" : ""}">
      <p class="app-desc">${escapeHtml(app.description)}</p>
      <div class="services">${servicesHtml}</div>
      <div class="actions">
        <button class="btn btn-start" ${isRunning ? "disabled" : ""} data-action="start">Start</button>
        <button class="btn btn-stop" ${isStopped ? "disabled" : ""} data-action="stop">Stop</button>
        <button class="btn btn-restart" ${isStopped ? "disabled" : ""} data-action="restart">Restart</button>
        <a class="btn btn-open" href="${escapeHtml(app.url)}" target="_blank" ${!isRunning ? 'style="pointer-events:none;opacity:0.4" tabindex="-1" aria-disabled="true"' : ""}>Open</a>
        ${logButtonHtml}
        <button class="btn btn-autostart ${app.autostart ? "active" : ""}" data-autostart="${app.id}">${app.autostart ? "Disable Auto-start" : "Enable Auto-start"}</button>
      </div>
      ${logSlotHtml}
    </div>
  `;

  card.querySelector("[data-expand]").addEventListener("click", (e) => {
    if (e.target.closest(".drag-handle")) return;
    if (justDragged && Date.now() - justDragged < 200) { justDragged = false; return; }
    justDragged = false;
    toggleExpand(app.id);
    const arrow = card.querySelector(".expand-arrow");
    arrow.innerHTML = expandedApps.has(app.id) ? "&#9650;" : "&#9660;";
  });

  card.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      appAction(app.id, btn.dataset.action, btn);
    });
  });

  card.querySelector("[data-autostart]").addEventListener("click", (e) => {
    e.stopPropagation();
    toggleAutostart(app.id);
  });

  card.querySelector("[data-log-toggle]").addEventListener("click", (e) => {
    e.stopPropagation();
    toggleLog(e.currentTarget.dataset.logToggle);
  });

  card.addEventListener("dragstart", (e) => {
    draggedId = app.id;
    card.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
  });

  card.addEventListener("dragend", () => {
    card.classList.remove("dragging");
    draggedId = null;
    justDragged = Date.now();
    container
      .querySelectorAll(".drag-over")
      .forEach((el) => el.classList.remove("drag-over"));
  });

  let dragOverCount = 0;

  card.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  });

  card.addEventListener("dragenter", (e) => {
    e.preventDefault();
    dragOverCount++;
    if (draggedId && draggedId !== app.id) {
      card.classList.add("drag-over");
    }
  });

  card.addEventListener("dragleave", () => {
    dragOverCount--;
    if (dragOverCount <= 0) {
      dragOverCount = 0;
      card.classList.remove("drag-over");
    }
  });

  card.addEventListener("drop", (e) => {
    e.preventDefault();
    card.classList.remove("drag-over");
    if (!draggedId || draggedId === app.id) return;

    const dragged = document.getElementById(`card-${draggedId}`);
    if (!dragged) return;

    const cards = [...container.querySelectorAll(".app-card")];
    const fromIdx = cards.indexOf(dragged);
    const toIdx = cards.indexOf(card);

    if (fromIdx < toIdx) {
      container.insertBefore(dragged, card.nextSibling);
    } else {
      container.insertBefore(dragged, card);
    }

    saveOrder();
  });

  return card;
}

function updateCard(card, app) {
  const wasDragging = card.classList.contains("dragging");
  card.className = `app-card status-${app.status}`;
  if (wasDragging) card.classList.add("dragging");

  const statusDot = card.querySelector(".app-header .status-dot");
  statusDot.className = `status-dot ${app.status}`;

  app.services.forEach((s) => {
    const row = card.querySelector(`.service-row[data-service="${s.name}"]`);
    if (row) {
      row.querySelector(".service-dot").className = `service-dot ${
        s.running ? "running" : "stopped"
      }`;
    }
  });

  const isRunning = app.status === "running";
  const isStopped = app.status === "stopped";

  const startBtn = card.querySelector(".btn-start");
  const stopBtn = card.querySelector(".btn-stop");
  const restartBtn = card.querySelector(".btn-restart");
  const openLink = card.querySelector(".btn-open");

  if (startBtn) startBtn.disabled = isRunning;
  if (stopBtn) stopBtn.disabled = isStopped;
  if (restartBtn) restartBtn.disabled = isStopped;
  if (openLink) {
    openLink.style.pointerEvents = isRunning ? "" : "none";
    openLink.style.opacity = isRunning ? "" : "0.4";
    openLink.tabIndex = isRunning ? 0 : -1;
    openLink.setAttribute("aria-disabled", !isRunning);
  }
}

async function refreshApps() {
  try {
    const apps = await fetchApps();
    const activeIds = new Set(apps.map((a) => a.id));

    apps.forEach((app) => {
      const card = document.getElementById(`card-${app.id}`);
      if (card) {
        updateCard(card, app);
      } else {
        container.appendChild(buildCard(app));
      }
    });

    [...container.querySelectorAll(".app-card")].forEach((card) => {
      if (!activeIds.has(card.dataset.appId)) {
        const removedId = card.dataset.appId;
        card.remove();
        expandedApps.delete(removedId);
        openLogs.delete(removedId);
        delete activeLogTab[removedId];
      }
    });

    for (const appId of openLogs) {
      if (!expandedApps.has(appId)) continue;
      if (activeLogTab[appId]) {
        await refreshLog(appId, activeLogTab[appId]);
      }
    }
  } catch (e) {
    if (!container.children.length) {
      container.innerHTML = '<p class="loading">Failed to load apps</p>';
    }
  }
}

const backupContainer = document.getElementById("backup-container");
let backupExpanded = true;
let backupLogOpen = false;

async function fetchBackupStatus() {
  const res = await fetch("/api/backup/status");
  if (!res.ok) throw new Error("Failed to fetch backup status");
  return res.json();
}

function timeAgo(dateStr) {
  if (!dateStr) return "never";
  const date = new Date(dateStr.replace(" ", "T"));
  if (isNaN(date.getTime())) {
    const parts = dateStr.match(/(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})/);
    if (parts) {
      const d = new Date(parts[1] + "T" + parts[2]);
      if (!isNaN(d.getTime())) return timeAgoFromDate(d);
    }
    return dateStr;
  }
  return timeAgoFromDate(date);
}

function timeAgoFromDate(date) {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatNextRun(raw) {
  if (!raw) return "";
  try {
    const cleaned = raw.replace(/^[A-Za-z]{3}\s+/, "").replace(/\s+[A-Z]{2,5}$/, "").replace(" ", "T");
    const d = new Date(cleaned);
    if (isNaN(d.getTime())) return raw;
    const now = new Date();
    const diffMs = d.getTime() - now.getTime();
    if (diffMs < 0) return "overdue";
    const diffH = Math.floor(diffMs / 3600000);
    const diffM = Math.floor((diffMs % 3600000) / 60000);
    if (diffH > 0) return `in ${diffH}h ${diffM}m`;
    return `in ${diffM}m`;
  } catch {
    return raw;
  }
}

function repoDotClass(result) {
  if (result === "pushed" || result === "pushed to remote") return "pushed";
  if (result === "push failed" || result === "skipped") return "failed";
  if (result === "no changes" || result === "committed") return "no-changes";
  return "unknown";
}

function repoStatusText(repo) {
  const result = repo.last_push_result;
  if (result === "pushed" || result === "pushed to remote") {
    return `pushed ${timeAgo(repo.pushed_time)}`;
  }
  if (result === "push failed") return "push failed";
  if (result === "skipped") return "skipped (VPN unavailable)";
  if (result === "no changes") return "no changes";
  if (result === "committed") return "committed (not pushed)";
  return "unknown";
}

function buildBackupCard(data) {
  const card = document.createElement("div");
  card.className = `backup-card status-${data.status}`;
  card.id = "backup-card";

  const nextRunText = formatNextRun(data.next_run);

  const reposHtml = data.repos
    .filter((r) => r.last_push_result !== "no changes" || r.ahead > 0)
    .map((r) => {
      const dotClass = repoDotClass(r.last_push_result);
      const statusText = repoStatusText(r);
      const linkHtml = r.commit_url
        ? `<a class="repo-link" href="${escapeHtml(r.commit_url)}" target="_blank">Remote &#x2197;</a>`
        : "";
      const aheadHtml =
        r.ahead > 0 ? `<span class="repo-ahead">${parseInt(r.ahead, 10)} ahead</span>` : "";
      return `<div class="repo-row">
        <span class="repo-dot ${dotClass}"></span>
        <span class="repo-name">${escapeHtml(r.name)}</span>
        <span class="repo-status">${escapeHtml(statusText)}</span>
        ${aheadHtml}
        ${linkHtml}
      </div>`;
    })
    .join("");

  const issuesHtml =
    data.issues.length > 0
      ? `<div class="issue-banner warning">${parseInt(data.issues.length, 10)} repo${data.issues.length > 1 ? "s" : ""} failed to push on last run</div>`
      : "";

  card.innerHTML = `
    <div class="backup-header" id="backup-header">
      <span class="status-dot ${data.status === "ok" ? "running" : data.status === "warning" ? "partial" : "stopped"}"></span>
      <span class="app-name">Backup</span>
      ${data.running ? '<span class="tag-badge">running</span>' : ""}
      ${data.last_run ? `<span class="tag-badge" style="background:rgba(148,163,184,0.15);color:var(--text-muted)">${timeAgo(data.last_run)}</span>` : ""}
      <span class="next-run">${nextRunText ? "Next: " + nextRunText : ""}</span>
      <span class="expand-arrow">${backupExpanded ? "&#9650;" : "&#9660;"}</span>
    </div>
    <div class="backup-details ${backupExpanded ? "expanded" : ""}">
      <div class="repos-list">${reposHtml}</div>
      ${issuesHtml}
      <div class="backup-actions">
        <button class="btn btn-run" id="btn-backup-run" ${data.running ? "disabled" : ""}>${data.running ? "Running..." : "Run Now"}</button>
        <button class="btn btn-stop" id="btn-backup-stop" ${!data.running ? "disabled" : ""}>Stop</button>
        <button class="btn btn-logs" id="btn-backup-logs">Logs</button>
      </div>
      <div id="backup-log-slot"></div>
    </div>
  `;

  card.querySelector("#backup-header").addEventListener("click", () => {
    backupExpanded = !backupExpanded;
    const details = card.querySelector(".backup-details");
    const arrow = card.querySelector(".expand-arrow");
    details.classList.toggle("expanded", backupExpanded);
    arrow.innerHTML = backupExpanded ? "&#9650;" : "&#9660;";
  });

  card.querySelector("#btn-backup-run").addEventListener("click", async (e) => {
    e.stopPropagation();
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.textContent = "Running...";
    try {
      const res = await fetch("/api/backup/run", { method: "POST" });
      if (!res.ok) {
        const d = await res.json();
        alert(d.detail || "Failed to start backup");
      }
    } catch (err) {
      alert("Request failed: " + err.message);
    }
    setTimeout(refreshBackup, 1000);
  });

  card.querySelector("#btn-backup-stop").addEventListener("click", async (e) => {
    e.stopPropagation();
    const btn = e.currentTarget;
    btn.disabled = true;
    try {
      const res = await fetch("/api/backup/stop", { method: "POST" });
      if (!res.ok) {
        const d = await res.json();
        alert(d.detail || "Failed to stop backup");
      }
    } catch (err) {
      alert("Request failed: " + err.message);
    }
    setTimeout(refreshBackup, 500);
  });

  card.querySelector("#btn-backup-logs").addEventListener("click", async (e) => {
    e.stopPropagation();
    const slot = document.getElementById("backup-log-slot");
    if (backupLogOpen) {
      backupLogOpen = false;
      slot.innerHTML = "";
      return;
    }
    backupLogOpen = true;
    slot.innerHTML =
      '<div class="backup-log-panel"><pre>Loading...</pre></div>';
    try {
      const res = await fetch("/api/backup/logs");
      const data = await res.json();
      const panel = slot.querySelector(".backup-log-panel");
      if (panel) {
        panel.querySelector("pre").textContent = data.logs || "(empty)";
        panel.scrollTop = panel.scrollHeight;
      }
    } catch {
      const pre = slot.querySelector("pre");
      if (pre) pre.textContent = "(failed to load logs)";
    }
  });

  return card;
}

function updateBackupCard(card, data) {
  card.className = `backup-card status-${data.status}`;

  const dot = card.querySelector(".backup-header .status-dot");
  dot.className = `status-dot ${data.status === "ok" ? "running" : data.status === "warning" ? "partial" : "stopped"}`;

  const nextRun = card.querySelector(".next-run");
  const nextRunText = formatNextRun(data.next_run);
  nextRun.textContent = nextRunText ? "Next: " + nextRunText : "";

  const reposList = card.querySelector(".repos-list");
  if (reposList) {
    reposList.innerHTML = data.repos
      .filter((r) => r.last_push_result !== "no changes" || r.ahead > 0)
      .map((r) => {
        const dotClass = repoDotClass(r.last_push_result);
        const statusText = repoStatusText(r);
        const linkHtml = r.commit_url
          ? `<a class="repo-link" href="${escapeHtml(r.commit_url)}" target="_blank">Remote &#x2197;</a>`
          : "";
        const aheadHtml =
          r.ahead > 0 ? `<span class="repo-ahead">${parseInt(r.ahead, 10)} ahead</span>` : "";
        return `<div class="repo-row">
          <span class="repo-dot ${dotClass}"></span>
          <span class="repo-name">${escapeHtml(r.name)}</span>
          <span class="repo-status">${escapeHtml(statusText)}</span>
          ${aheadHtml}
          ${linkHtml}
        </div>`;
      })
      .join("");
  }

  const oldBanner = card.querySelector(".issue-banner");
  if (data.issues.length > 0) {
    const bannerHtml = `<div class="issue-banner warning">${data.issues.length} repo${data.issues.length > 1 ? "s" : ""} failed to push on last run</div>`;
    if (oldBanner) {
      oldBanner.outerHTML = bannerHtml;
    } else {
      reposList.insertAdjacentHTML("afterend", bannerHtml);
    }
  } else if (oldBanner) {
    oldBanner.remove();
  }

  const runBtn = card.querySelector("#btn-backup-run");
  if (runBtn) {
    runBtn.disabled = data.running;
    runBtn.textContent = data.running ? "Running..." : "Run Now";
  }

  const stopBtn = card.querySelector("#btn-backup-stop");
  if (stopBtn) {
    stopBtn.disabled = !data.running;
  }

  const tags = card.querySelectorAll(".backup-header .tag-badge");
  tags.forEach((t) => t.remove());
  const appName = card.querySelector(".backup-header .app-name");
  if (data.running) {
    appName.insertAdjacentHTML("afterend", '<span class="tag-badge">running</span>');
  }
  if (data.last_run) {
    const style = 'style="background:rgba(148,163,184,0.15);color:var(--text-muted)"';
    const runningBadge = card.querySelector(".backup-header .tag-badge");
    const insertAfter = runningBadge || appName;
    insertAfter.insertAdjacentHTML(
      "afterend",
      `<span class="tag-badge" ${style}>${timeAgo(data.last_run)}</span>`
    );
  }

  if (backupLogOpen) {
    fetch("/api/backup/logs")
      .then((r) => r.json())
      .then((d) => {
        const pre = card.querySelector(".backup-log-panel pre");
        if (pre) pre.textContent = d.logs || "(empty)";
      })
      .catch(() => {});
  }
}

async function refreshBackup() {
  try {
    const data = await fetchBackupStatus();
    const card = document.getElementById("backup-card");
    if (card) {
      updateBackupCard(card, data);
    } else {
      backupContainer.appendChild(buildBackupCard(data));
    }
  } catch {
    if (!document.getElementById("backup-card")) {
      backupContainer.innerHTML =
        '<p class="loading" style="padding:1rem">Backup status unavailable</p>';
    }
  }
}

refreshApps();
refreshBackup();
setInterval(refreshApps, POLL_INTERVAL);
setInterval(refreshBackup, POLL_INTERVAL);
