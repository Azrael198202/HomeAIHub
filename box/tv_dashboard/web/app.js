const state = { notifications: [] };

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function eventRow(item) {
  return `<div class="schedule-item">
    <div class="time-tag">${item.time || "--:--"}</div>
    <div class="event-main">
      <div class="event-person color-${item.color}">${item.person}</div>
      <div class="event-title">${item.title}</div>
    </div>
    <div class="event-location">${item.location || ""}</div>
  </div>`;
}

function card(item) {
  return `<div class="info-card priority-${item.priority}">
    <div class="info-head">${item.time || "TBD"} ${item.person}</div>
    <div class="info-title">${item.title}</div>
    <div class="info-meta">${item.location || item.summary}</div>
  </div>`;
}

function tile(item) {
  return `<div class="system-tile">
    <div class="tile-label">${item.label}</div>
    <div class="tile-value tone-${item.tone || "green"}">${item.value}</div>
  </div>`;
}

function timelineRow(row) {
  const bars = row.events
    .map((event) => `<div class="timeline-bar color-${event.color}"><span>${event.time || "TBD"}</span><strong>${event.title}</strong></div>`)
    .join("");
  return `<div class="timeline-row"><div class="timeline-person color-${row.color}">${row.person}</div><div class="timeline-track">${bars || '<div class="empty">No schedule yet</div>'}</div></div>`;
}

function renderPairing(payload) {
  const pairing = payload.pairing;
  document.getElementById("clock").textContent = "PAIR";
  document.getElementById("date").textContent = payload.device.device_name;
  document.getElementById("weather").textContent = "Setup";
  document.getElementById("status").textContent = "UNCLAIMED";
  document.getElementById("tvStatus").textContent = "ONBOARDING";
  document.getElementById("systemStrip").innerHTML = [
    tile({ label: "Home Mode", value: "pairing", tone: "green" }),
    tile({ label: "Dashboard", value: "onboarding", tone: "blue" }),
    tile({ label: "Voice", value: "idle", tone: "orange" }),
    tile({ label: "Agent", value: "pairing-agent", tone: "pink" }),
  ].join("");
  document.getElementById("heroAlert").classList.add("hidden");

  document.getElementById("scheduleList").innerHTML = `
    <div class="info-card priority-normal">
      <div class="info-title">Scan This Box</div>
      <div class="info-meta">Device ID: ${pairing.device_id}</div>
      <div class="info-meta">Claim token: ${pairing.claim_token}</div>
      <div class="info-meta">Expires: ${pairing.claim_expires_at}</div>
    </div>
  `;
  document.getElementById("timeline").innerHTML = `
    <div class="info-card priority-low">
      <div class="info-title">QR Payload</div>
      <div class="info-meta">${JSON.stringify(pairing.qr_payload)}</div>
    </div>
  `;
  document.getElementById("reminderList").innerHTML = `
    <div class="info-card priority-high">
      <div class="info-title">Open Mobile App</div>
      <div class="info-meta">Claim URL: ${pairing.claim_url}</div>
    </div>
  `;
  document.getElementById("infoList").innerHTML = `
    <div class="info-card priority-low">
      <div class="info-title">Waiting For Claim</div>
      <div class="info-meta">Use the mobile mock to claim this device.</div>
    </div>
  `;
  document.getElementById("voiceStatus").textContent = "Onboarding mode";
  document.getElementById("footerSummary").textContent = "Waiting for first family claim";
  document.getElementById("footerUpdate").textContent = `Claim URL: ${pairing.claim_url}`;
  state.notifications = [];
  renderModal();
}

function renderDashboard(payload) {
  document.getElementById("clock").textContent = payload.header.time;
  document.getElementById("date").textContent = `${payload.header.weekday} ${payload.header.date}`;
  document.getElementById("weather").textContent = payload.header.weather;
  document.getElementById("status").textContent = payload.header.status;
  document.getElementById("tvStatus").textContent = `${payload.header.tv_power.toUpperCase()} / ${payload.header.tv_input}`;
  document.getElementById("systemStrip").innerHTML = (payload.system_tiles || []).map(tile).join("");
  document.getElementById("scheduleList").innerHTML = payload.today_schedule.map(eventRow).join("") || '<div class="empty">No schedule</div>';
  document.getElementById("timeline").innerHTML = payload.timeline.map(timelineRow).join("") || '<div class="empty">No timeline</div>';
  document.getElementById("reminderList").innerHTML = payload.reminders.map(card).join("") || '<div class="empty">No reminders</div>';
  document.getElementById("infoList").innerHTML = payload.infos.map(card).join("") || '<div class="empty">No info</div>';
  document.getElementById("voiceStatus").textContent = payload.footer.voice_status;
  document.getElementById("footerSummary").textContent = `${payload.footer.summary} | ${payload.footer.active_agent}`;
  document.getElementById("footerUpdate").textContent = `Recent update: ${payload.footer.recent_update} | Route: ${payload.footer.last_route}`;
  renderHero(payload.hero_alert);
  state.notifications = payload.notifications || [];
  renderModal();
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
    <div class="hero-title">Priority Alert</div>
    <div class="hero-message">${alert.title}</div>
    <div class="hero-meta">${alert.message}</div>
  `;
}

function renderModal() {
  const modal = document.getElementById("modal");
  const notification = state.notifications[0];
  if (!notification) {
    modal.classList.add("hidden");
    return;
  }
  modal.classList.remove("hidden");
  document.getElementById("modalTitle").textContent = notification.title;
  document.getElementById("modalMessage").textContent = notification.message;
  document.getElementById("modalMeta").textContent = [notification.person, notification.location].filter(Boolean).join(" | ");
  document.getElementById("modalAck").onclick = async () => {
    await api("/api/box/notifications/ack", { method: "POST", body: JSON.stringify({ id: notification.id }) });
    await refresh();
  };
}

async function refresh() {
  const payload = await api("/api/box/dashboard");
  if (payload.mode === "pairing") {
    renderPairing(payload);
    return;
  }
  renderDashboard(payload);
}

refresh();
setInterval(refresh, 30000);
