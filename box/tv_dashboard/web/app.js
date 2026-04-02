const DESIGN_QUERY = new URLSearchParams(window.location.search);
const DESIGN_MODE = DESIGN_QUERY.get("design") !== "0" && Boolean(window.HOMEAIHUB_TV_DESIGN_MODE);
const DESIGN_DATA = window.HOMEAIHUB_TV_DESIGN_DATA || {};

const state = {
  notifications: [],
  mode: "dashboard",
  primaryView: "schedule",
  sideView: "reminders",
  designScene: DESIGN_QUERY.get("scene") || "morning",
  dismissedNotificationIds: new Set(),
  heroDrag: { active: false, offsetX: 0, offsetY: 0 },
  conversationDrag: { active: false, offsetX: 0, offsetY: 0 },
  latestTranscript: "",
  latestTranscriptFile: "",
  latestReply: "",
  liveTime: new Date(),
};

const PERSON_STYLE = {
  Dad: "blue",
  Mom: "pink",
  Alex: "orange",
  Emma: "green",
  Family: "green",
};

const DOCK_SCENES = {
  calendar: "morning",
  photos: "evening",
  reminders: "away",
  settings: "pairing",
};

function designScenes() {
  return DESIGN_DATA.scenes || {};
}

function activeSceneOrder() {
  return Array.isArray(DESIGN_DATA.rotation) && DESIGN_DATA.rotation.length
    ? DESIGN_DATA.rotation
    : Object.keys(designScenes());
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function avatarMarkup(name, color, avatarUrl = "") {
  const initial = escapeHtml((name || "?").slice(0, 1));
  const media = avatarUrl
    ? `<img class="avatar-image" src="${escapeHtml(avatarUrl)}" alt="" onerror="this.remove(); this.parentElement.classList.add('avatar-fallback'); this.parentElement.textContent='${initial}'" />`
    : initial;
  return `<div class="avatar-shell color-${escapeHtml(color || "green")}">
    <div class="avatar-ring">
      <div class="avatar-photo">${media}</div>
    </div>
  </div>`;
}

function scheduleRow(item) {
  return `<div class="schedule-item priority-${escapeHtml(item.priority || "normal")}">
    <div class="schedule-time">${escapeHtml(item.time || "--:--")}</div>
    ${avatarMarkup(item.person || "Family", item.color || PERSON_STYLE[item.person] || "green", item.avatar_url || "")}
    <div class="schedule-copy">
      <div class="schedule-person">${escapeHtml(item.person || "Family")}</div>
      <div class="schedule-title">${escapeHtml(item.title)}</div>
      <div class="schedule-subtitle">${escapeHtml(item.location || item.summary || "")}</div>
    </div>
    <div class="schedule-chip">
      <strong>${escapeHtml(item.time || "TBD")}</strong>
      <span>${escapeHtml(item.title || "")}</span>
    </div>
  </div>`;
}

function timelineCard(row) {
  const bars = (row.events || []).slice(0, 4).map((event) => `
    <div class="person-event color-${escapeHtml(event.color || "green")}">
      <span>${escapeHtml(event.time || "TBD")}</span>
      <strong>${escapeHtml(event.title)}</strong>
    </div>`).join("");
  return `
    <div class="person-card">
      <div class="person-head">
        ${avatarMarkup(row.person || "Family", row.color || PERSON_STYLE[row.person] || "green", row.avatar_url || "")}
        <div>
          <div class="schedule-person">${escapeHtml(row.person || "Family")}</div>
          <div class="schedule-subtitle">Weekly focus</div>
        </div>
      </div>
      <div class="person-events">${bars || '<div class="empty-state">No events</div>'}</div>
    </div>`;
}

function tile(item) {
  return `<div class="system-tile">
    <div class="tile-label">${escapeHtml(item.label)}</div>
    <div class="tile-value tone-${escapeHtml(item.tone || "green")}">${escapeHtml(item.value)}</div>
  </div>`;
}

function sideCard(item) {
  return `<div class="side-card priority-${escapeHtml(item.priority || "normal")}">
    <div class="side-card-top">
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.time || "TBD")}</span>
    </div>
    <div class="side-card-meta">${escapeHtml(item.person || "Family")}${item.location ? ` | ${escapeHtml(item.location)}` : ""}</div>
    <div class="side-card-copy">${escapeHtml(item.summary || item.message || "")}</div>
  </div>`;
}

function focusMarkup(focus = {}) {
  const nextUp = focus.next_up;
  return `
    <div class="focus-title">${escapeHtml(focus.title || "Household Focus")}</div>
    <div class="focus-summary">${escapeHtml(focus.summary || "Home is calm and ready")}</div>
    <div class="focus-stats">
      <div class="focus-pill">Confirmations ${escapeHtml(focus.pending_confirmations || 0)}</div>
      <div class="focus-pill">${nextUp ? `Next ${escapeHtml(nextUp.time || "TBD")} ${escapeHtml(nextUp.title || "")}` : "No urgent schedule"}</div>
    </div>`;
}

function weekdayColumns(scheduleItems) {
  const labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const buckets = labels.map((label) => ({ label, items: [] }));
  (scheduleItems || []).forEach((item, index) => {
    buckets[index % buckets.length].items.push(item);
  });
  return buckets;
}

function dateBoard(scheduleItems) {
  const columns = weekdayColumns(scheduleItems);
  return `<div class="date-board">
    ${columns.map((column, index) => {
      const items = column.items.slice(0, 2);
      const isToday = index === 3;
      return `<div class="date-column ${isToday ? "today-column" : ""}">
        <div class="date-column-head">${column.label}</div>
        <div class="date-column-body">
          ${items.length
            ? items.map((item) => `<div class="date-slot priority-${escapeHtml(item.priority || "normal")}"><strong>${escapeHtml(item.time || "OFF")}</strong><span>${escapeHtml(item.title || "")}</span></div>`).join("")
            : '<div class="date-slot off-slot"><strong>OFF</strong></div>'}
        </div>
      </div>`;
    }).join("")}
  </div>`;
}

function setPrimaryTab(view) {
  state.primaryView = view;
  document.getElementById("tabSchedule").classList.toggle("active", view === "schedule");
  document.getElementById("tabDate").classList.toggle("active", view === "date");
  document.getElementById("tabTimeline").classList.toggle("active", view === "timeline");
  document.getElementById("scheduleView").classList.toggle("hidden", view !== "schedule");
  document.getElementById("dateView").classList.toggle("hidden", view !== "date");
  document.getElementById("timelineView").classList.toggle("hidden", view !== "timeline");
}

function setSideTab(view) {
  state.sideView = view;
  document.getElementById("tabReminders").classList.toggle("active", view === "reminders");
  document.getElementById("tabInfo").classList.toggle("active", view === "info");
  document.getElementById("reminderView").classList.toggle("hidden", view !== "reminders");
  document.getElementById("infoView").classList.toggle("hidden", view !== "info");
}

function renderConversation(payload) {
  const heard = document.getElementById("conversationHeard");
  const reply = document.getElementById("conversationReply");
  const lastTranscript = payload.voice?.last_transcript || state.latestTranscript || payload.voice?.recent_sessions?.[0]?.transcript || "";
  const responseText = payload.voice?.last_reply || state.latestReply || payload.voice?.wake_ack_message || payload.footer?.voice_status || "Lumi replies will appear here.";
  heard.textContent = lastTranscript ? `You said: ${lastTranscript}` : "You said: waiting for voice input.";
  reply.textContent = state.latestTranscriptFile ? `Lumi: ${responseText}  |  ${state.latestTranscriptFile}` : `Lumi: ${responseText}`;
  applyConversationPosition();
}

function renderCommandMode(commandMode, payload) {
  const panel = document.getElementById("commandModePanel");
  const title = document.getElementById("commandModeTitle");
  const heard = document.getElementById("commandModeHeard");
  const reply = document.getElementById("commandModeReply");
  if (!commandMode) {
    panel.classList.add("hidden");
    return;
  }
  panel.classList.remove("hidden");
  title.textContent = commandMode.title || "Command mode";
  heard.textContent = commandMode.message || payload.voice?.last_transcript || "Waiting for a task to handle.";
  reply.textContent = commandMode.reply || payload.voice?.last_reply || "Tell me what to handle.";
}

function updateLiveClock() {
  const now = state.liveTime instanceof Date ? state.liveTime : new Date();
  const hours = now.getHours();
  const minutes = now.getMinutes();
  const month = now.toLocaleString("en-US", { month: "long" });
  const weekday = now.toLocaleString("en-US", { weekday: "long" });
  document.getElementById("clock").textContent = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
  document.querySelector(".ampm").textContent = hours >= 12 ? "PM" : "AM";
  if (state.mode === "dashboard") {
    document.getElementById("date").textContent = `${weekday}, ${month} ${now.getDate()}`;
  }
}

function renderWakeOverlay(overlay) {
  const panel = document.getElementById("wakeOverlay");
  if (!overlay) {
    panel.classList.add("hidden");
    panel.innerHTML = "";
    return;
  }
  panel.classList.remove("hidden");
  panel.innerHTML = `
    <span class="wake-kicker">Voice Wake</span>
    <span class="wake-copy">${escapeHtml(overlay.title || overlay.message || "Listening")}</span>
    <span class="wake-meta">${escapeHtml(overlay.time || "")}</span>`;
}

function renderHero(alert) {
  const hero = document.getElementById("heroAlert");
  if (!alert) {
    hero.classList.add("hidden");
    hero.innerHTML = "";
    return;
  }
  hero.classList.remove("hidden");
  hero.innerHTML = `
    <div class="hero-kicker">Priority Alert</div>
    <div class="hero-title-large">${escapeHtml(alert.title)}</div>
    <div class="hero-copy">${escapeHtml(alert.message)}</div>`;
  applyHeroPosition();
}

function updateDockBadge() {
  const badge = document.getElementById("dockNotificationCount");
  badge.textContent = String(state.notifications.length);
  badge.classList.toggle("hidden", state.notifications.length === 0);
}

function updateDockState() {
  document.querySelectorAll(".dock-item").forEach((button) => {
    const scene = DOCK_SCENES[button.dataset.dock];
    const active = DESIGN_MODE ? scene === state.designScene : button.dataset.dock === "calendar";
    button.classList.toggle("active", active);
  });
}

function notificationId(notification) {
  if (!notification) return "";
  return String(notification.id || `${notification.title || ""}:${notification.message || ""}`);
}

function shouldShowModal(notification) {
  if (!notification) return false;
  if (notification.modal === false) return false;
  if (notification.requires_confirmation || notification.requires_ack || notification.blocking) return true;
  const category = String(notification.kind || notification.category || "").toLowerCase();
  if (["emergency", "alert", "confirmation", "security", "visitor"].includes(category)) return true;
  const priority = String(notification.priority || "").toLowerCase();
  const combined = `${notification.title || ""} ${notification.message || ""}`.toLowerCase();
  const interruptKeywords = [
    "confirm",
    "confirmation",
    "urgent",
    "emergency",
    "alert",
    "doorbell",
    "visitor",
    "security",
    "紧急",
    "确认",
    "警报",
    "告警",
  ];
  return priority === "critical" || interruptKeywords.some((keyword) => combined.includes(keyword));
}

function currentModalNotification() {
  return (state.notifications || []).find((notification) => {
    const id = notificationId(notification);
    return !state.dismissedNotificationIds.has(id) && shouldShowModal(notification);
  }) || null;
}

function renderModal() {
  const modal = document.getElementById("modal");
  const notification = currentModalNotification();
  if (!notification) {
    modal.classList.add("hidden");
    return;
  }
  modal.classList.remove("hidden");
  document.getElementById("modalTitle").textContent = notification.title;
  document.getElementById("modalMessage").textContent = notification.message;
  document.getElementById("modalMeta").textContent = [notification.person, notification.location].filter(Boolean).join(" | ");
  document.getElementById("modalAck").onclick = async () => {
    state.dismissedNotificationIds.add(notificationId(notification));
    if (DESIGN_MODE) {
      renderModal();
      return;
    }
    await api("/api/box/notifications/ack", { method: "POST", body: JSON.stringify({ id: notification.id }) });
    await refresh();
  };
}

function renderPairing(payload) {
  state.mode = "pairing";
  document.getElementById("commandModePanel").classList.add("hidden");
  const pairing = payload.pairing;
  const onboarding = payload.onboarding || {};
  document.getElementById("clock").textContent = "10:15";
  document.querySelector(".ampm").textContent = "PAIR";
  document.getElementById("date").textContent = payload.device.device_name || "HomeAIHub Box";
  document.getElementById("sceneBadge").textContent = payload.scene_label || "Pairing";
  document.getElementById("sceneBadge").title = payload.scene_hint || "";
  document.getElementById("weather").textContent = "Setup";
  document.getElementById("tvStatus").textContent = "ONBOARDING";
  document.getElementById("status").textContent = "UNCLAIMED";
  document.getElementById("heroAlert").classList.remove("hidden");
  document.getElementById("heroAlert").innerHTML = `
    <div class="hero-kicker">Pair This Box</div>
    <div class="hero-title-large">${escapeHtml(onboarding.title || "HomeAIHub pairing ready")}</div>
    <div class="hero-copy">${escapeHtml(onboarding.subtitle || "Open the family app and scan the claim payload.")}</div>`;
  renderWakeOverlay(null);

  document.getElementById("scheduleView").innerHTML = `
    <div class="pairing-os-card pairing-main-card">
      <div class="pairing-main-copy">
        <div class="pairing-heading">HomeAIHub Pairing</div>
        <div class="pairing-token">${escapeHtml(pairing.claim_token)}</div>
        <div class="pairing-meta">Device ID ${escapeHtml(pairing.device_id)}</div>
        <div class="pairing-meta">Expires ${escapeHtml(pairing.claim_expires_at)}</div>
        <div class="pairing-meta">Claim URL ${escapeHtml(pairing.claim_url)}</div>
      </div>
      <div class="pairing-qr-card monospace-card"><pre>${escapeHtml(JSON.stringify(pairing.qr_payload, null, 2))}</pre></div>
    </div>`;

  document.getElementById("dateView").innerHTML = `
    <div class="pairing-os-card pairing-grid-card">
      ${(onboarding.steps || []).map((step, index) => `<div class="pairing-step-card"><span>${index + 1}</span><strong>${escapeHtml(step)}</strong></div>`).join("")}
    </div>`;

  document.getElementById("timelineView").innerHTML = `
    <div class="pairing-os-card pairing-grid-card">
      <div class="pairing-status-badge">Remote control locked until claim completes</div>
      <div class="pairing-status-copy">Local wake, local voice, and TV dashboard preview are still available before pairing.</div>
    </div>`;

  document.getElementById("focusCard").innerHTML = focusMarkup({
    title: "Onboarding Steps",
    summary: "Use your phone or tablet to bind this box once.",
    pending_confirmations: 0,
  });

  document.getElementById("reminderView").innerHTML = (onboarding.steps || []).map((step, index) => `
    <div class="side-card priority-normal">
      <div class="side-card-top"><strong>Step ${index + 1}</strong><span>Setup</span></div>
      <div class="side-card-copy">${escapeHtml(step)}</div>
    </div>`).join("") || '<div class="empty-state">Open the mobile app to continue</div>';

  document.getElementById("infoView").innerHTML = `
    <div class="side-card priority-low">
      <div class="side-card-top"><strong>Pairing Scope</strong><span>Gateway</span></div>
      <div class="side-card-copy">After claim, all remote photo, text, and voice data will route through the gateway into this home box.</div>
    </div>`;

  document.getElementById("systemStrip").innerHTML = [
    tile({ label: "Home Mode", value: "pairing", tone: "green" }),
    tile({ label: "Dashboard", value: "onboarding", tone: "blue" }),
    tile({ label: "Voice", value: "local only", tone: "orange" }),
    tile({ label: "Agent", value: "pairing-agent", tone: "pink" }),
  ].join("");

  document.getElementById("voiceStatus").textContent = "How can I assist you?";
  document.getElementById("footerUpdate").textContent = `Claim path: ${pairing.claim_url}`;
  document.getElementById("footerSummary").textContent = "Waiting for first family claim";
  renderConversation({
    voice: { last_transcript: "", wake_ack_message: "Pair this box to begin conversations." },
    footer: { voice_status: "Pair this box to begin conversations." },
  });
  state.notifications = [];
  updateDockBadge();
  updateDockState();
  setPrimaryTab("schedule");
  setSideTab("reminders");
  renderModal();
}

function renderDashboard(payload) {
  state.mode = "dashboard";
  state.liveTime = new Date();
  updateLiveClock();
  document.getElementById("sceneBadge").textContent = payload.scene_label || "Family Dashboard";
  document.getElementById("sceneBadge").title = payload.scene_hint || "";
  document.getElementById("weather").textContent = payload.header.weather;
  document.getElementById("tvStatus").textContent = `${payload.header.tv_power.toUpperCase()} / ${payload.header.tv_input}`;
  document.getElementById("status").textContent = payload.header.status;

  renderHero(payload.hero_alert);
  renderWakeOverlay(payload.wake_overlay);
  document.getElementById("scheduleView").innerHTML = (payload.today_schedule || []).slice(0, 4).map(scheduleRow).join("") || '<div class="empty-state">No schedule for today</div>';
  document.getElementById("dateView").innerHTML = dateBoard(payload.today_schedule || []);
  document.getElementById("timelineView").innerHTML = (payload.timeline || []).slice(0, 4).map(timelineCard).join("") || '<div class="empty-state">No family schedule yet</div>';
  document.getElementById("focusCard").innerHTML = focusMarkup(payload.focus || {});
  document.getElementById("reminderView").innerHTML = (payload.reminders || []).slice(0, 3).map(sideCard).join("") || '<div class="empty-state">No active reminders</div>';
  document.getElementById("infoView").innerHTML = (payload.infos || []).slice(0, 3).map(sideCard).join("") || '<div class="empty-state">No new updates</div>';
  document.getElementById("systemStrip").innerHTML = (payload.system_tiles || []).map(tile).join("");
  document.getElementById("voiceStatus").textContent = payload.footer.voice_status || "How can I assist you?";
  document.getElementById("footerUpdate").textContent = `Route ${payload.footer.last_route} | ${payload.footer.recent_update}`;
  document.getElementById("footerSummary").textContent = payload.footer.summary;
  renderConversation(payload);
  renderCommandMode(
    payload.command_mode || (payload.voice?.command_mode_active
      ? {
          title: "Command mode",
          message: payload.voice?.last_transcript || state.latestTranscript || "Waiting for a task to handle.",
          reply: payload.voice?.last_reply || state.latestReply || "Tell me what to handle.",
        }
      : null),
    payload,
  );

  state.notifications = payload.notifications || [];
  updateDockBadge();
  updateDockState();
  renderModal();
}

function applyHeroPosition() {
  const hero = document.getElementById("heroAlert");
  const savedLeft = window.localStorage.getItem("homeaihub.hero.left");
  const savedTop = window.localStorage.getItem("homeaihub.hero.top");
  if (savedLeft && savedTop) {
    hero.style.left = `${savedLeft}px`;
    hero.style.top = `${savedTop}px`;
    hero.style.right = "auto";
  } else {
    hero.style.left = "";
    hero.style.top = "";
    hero.style.right = "";
  }
}

function beginHeroDrag(event) {
  const hero = document.getElementById("heroAlert");
  if (hero.classList.contains("hidden")) return;
  const rect = hero.getBoundingClientRect();
  state.heroDrag.active = true;
  state.heroDrag.offsetX = event.clientX - rect.left;
  state.heroDrag.offsetY = event.clientY - rect.top;
  hero.classList.add("dragging");
}

function moveHeroDrag(event) {
  if (!state.heroDrag.active) return;
  const hero = document.getElementById("heroAlert");
  const nextLeft = Math.max(16, Math.min(window.innerWidth - hero.offsetWidth - 16, event.clientX - state.heroDrag.offsetX));
  const nextTop = Math.max(88, Math.min(window.innerHeight - hero.offsetHeight - 16, event.clientY - state.heroDrag.offsetY));
  hero.style.left = `${nextLeft}px`;
  hero.style.top = `${nextTop}px`;
  hero.style.right = "auto";
}

function endHeroDrag() {
  if (!state.heroDrag.active) return;
  const hero = document.getElementById("heroAlert");
  state.heroDrag.active = false;
  hero.classList.remove("dragging");
  const rect = hero.getBoundingClientRect();
  window.localStorage.setItem("homeaihub.hero.left", String(Math.round(rect.left)));
  window.localStorage.setItem("homeaihub.hero.top", String(Math.round(rect.top)));
}

function buildDesignPayload() {
  const scenes = designScenes();
  const payload = scenes[state.designScene] || scenes.morning || Object.values(scenes)[0];
  return structuredClone(payload || {});
}

function persistScene() {
  const url = new URL(window.location.href);
  url.searchParams.set("scene", state.designScene);
  if (DESIGN_QUERY.get("design") === "0") url.searchParams.set("design", "0");
  window.history.replaceState({}, "", url);
}

function applySceneDefaults() {
  if (state.designScene === "pairing") {
    state.primaryView = "schedule";
    state.sideView = "reminders";
    return;
  }
  if (state.designScene === "away") {
    state.primaryView = "date";
    state.sideView = "reminders";
    return;
  }
  if (state.designScene === "evening") {
    state.primaryView = "timeline";
    state.sideView = "info";
    return;
  }
  if (state.designScene === "emergency") {
    state.primaryView = "schedule";
    state.sideView = "reminders";
    return;
  }
  state.primaryView = "schedule";
  state.sideView = "reminders";
}

function setDesignScene(scene) {
  if (!DESIGN_MODE || !designScenes()[scene]) return;
  state.designScene = scene;
  applySceneDefaults();
  persistScene();
  setPrimaryTab(state.primaryView);
  setSideTab(state.sideView);
  refresh();
}

function cycleDesignScene(direction = 1) {
  const order = activeSceneOrder();
  if (!DESIGN_MODE || order.length < 2) return;
  const currentIndex = Math.max(order.indexOf(state.designScene), 0);
  const nextIndex = (currentIndex + direction + order.length) % order.length;
  setDesignScene(order[nextIndex]);
}

async function refresh() {
  const payload = DESIGN_MODE ? buildDesignPayload() : await api("/api/box/dashboard");
  if (!DESIGN_MODE) {
    try {
      const latest = await api("/api/box/voice/input/transcripts/latest");
      state.latestTranscript = latest.transcript || payload.voice?.last_transcript || state.latestTranscript;
      if (latest.transcript_file) {
        state.latestTranscriptFile = latest.transcript_file;
      }
    } catch {
      state.latestTranscript = payload.voice?.last_transcript || state.latestTranscript;
    }
    state.latestReply = payload.voice?.last_reply || payload.voice?.wake_ack_message || payload.footer?.voice_status || state.latestReply;
  }
  if (payload.mode === "pairing") {
    renderPairing(payload);
    return;
  }
  renderDashboard(payload);
}

function applyConversationPosition() {
  const panel = document.getElementById("conversationPanel");
  const savedLeft = window.localStorage.getItem("homeaihub.conversation.left");
  const savedTop = window.localStorage.getItem("homeaihub.conversation.top");
  if (savedLeft && savedTop) {
    panel.style.left = `${savedLeft}px`;
    panel.style.top = `${savedTop}px`;
    panel.style.right = "auto";
  } else {
    panel.style.left = "";
    panel.style.top = "";
    panel.style.right = "";
  }
}

function beginConversationDrag(event) {
  const panel = document.getElementById("conversationPanel");
  const rect = panel.getBoundingClientRect();
  state.conversationDrag.active = true;
  state.conversationDrag.offsetX = event.clientX - rect.left;
  state.conversationDrag.offsetY = event.clientY - rect.top;
  panel.classList.add("dragging");
}

function moveConversationDrag(event) {
  if (!state.conversationDrag.active) return;
  const panel = document.getElementById("conversationPanel");
  const nextLeft = Math.max(16, Math.min(window.innerWidth - panel.offsetWidth - 16, event.clientX - state.conversationDrag.offsetX));
  const nextTop = Math.max(88, Math.min(window.innerHeight - panel.offsetHeight - 16, event.clientY - state.conversationDrag.offsetY));
  panel.style.left = `${nextLeft}px`;
  panel.style.top = `${nextTop}px`;
  panel.style.right = "auto";
}

function endConversationDrag() {
  if (!state.conversationDrag.active) return;
  const panel = document.getElementById("conversationPanel");
  state.conversationDrag.active = false;
  panel.classList.remove("dragging");
  const rect = panel.getBoundingClientRect();
  window.localStorage.setItem("homeaihub.conversation.left", String(Math.round(rect.left)));
  window.localStorage.setItem("homeaihub.conversation.top", String(Math.round(rect.top)));
}

document.getElementById("tabSchedule").addEventListener("click", () => setPrimaryTab("schedule"));
document.getElementById("tabDate").addEventListener("click", () => setPrimaryTab("date"));
document.getElementById("tabTimeline").addEventListener("click", () => setPrimaryTab("timeline"));
document.getElementById("tabReminders").addEventListener("click", () => setSideTab("reminders"));
document.getElementById("tabInfo").addEventListener("click", () => setSideTab("info"));

document.querySelectorAll(".dock-item").forEach((button) => {
  button.addEventListener("click", () => {
    if (DESIGN_MODE) {
      const scene = DOCK_SCENES[button.dataset.dock];
      if (scene) setDesignScene(scene);
      return;
    }
    document.querySelectorAll(".dock-item").forEach((item) => item.classList.toggle("active", item === button));
  });
});

document.getElementById("heroAlert").addEventListener("pointerdown", beginHeroDrag);
document.getElementById("conversationPanel").addEventListener("pointerdown", beginConversationDrag);
document.addEventListener("pointermove", moveHeroDrag);
document.addEventListener("pointermove", moveConversationDrag);
document.addEventListener("pointerup", endHeroDrag);
document.addEventListener("pointerup", endConversationDrag);
document.addEventListener("pointercancel", endHeroDrag);
document.addEventListener("pointercancel", endConversationDrag);

document.addEventListener("keydown", (event) => {
  if (!DESIGN_MODE) return;
  if (event.key === "ArrowRight") cycleDesignScene(1);
  if (event.key === "ArrowLeft") cycleDesignScene(-1);
  if (event.key === "1") setDesignScene("morning");
  if (event.key === "2") setDesignScene("away");
  if (event.key === "3") setDesignScene("evening");
  if (event.key === "4") setDesignScene("emergency");
  if (event.key === "5") setDesignScene("pairing");
});

applySceneDefaults();
setPrimaryTab(state.primaryView);
setSideTab(state.sideView);
applyHeroPosition();
applyConversationPosition();
refresh();
setInterval(refresh, 1500);
setInterval(() => {
  state.liveTime = new Date();
  updateLiveClock();
}, 1000);
