const state = { sessionId: "" };

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function requireSession() {
  if (!state.sessionId) throw new Error("Open a session first");
}

function listItem(title, text) {
  return `<div class="list-item"><strong>${title}</strong><span>${text}</span></div>`;
}

function render(status, overview, pairing) {
  const device = status.device.device;
  document.getElementById("deviceCard").innerHTML = [
    listItem("Device", `${device.device_name} (${device.device_id})`),
    listItem("Pairing state", device.status),
    listItem("Owner", device.owner_name || "Unclaimed"),
    listItem("Family", device.family_id || "None"),
  ].join("");

  document.getElementById("pairingCard").innerHTML = [
    listItem("Claim token", pairing.claim_token),
    listItem("Expires at", pairing.claim_expires_at),
    listItem("Claim URL", pairing.claim_url),
    listItem("Pairing ready", pairing.paired ? "No" : "Yes"),
  ].join("");

  if (!document.getElementById("claimToken").value) {
    document.getElementById("claimToken").value = pairing.claim_token;
  }

  document.getElementById("nodeList").innerHTML = overview.nodes
    .map((node) => listItem(node.node_name, `${node.node_role} / ${node.status}`))
    .join("");

  document.getElementById("commandList").innerHTML =
    overview.recent_commands
      .map((command) => listItem(`${command.agent_name} -> ${command.action_name}`, `${command.status} / ${command.target_node}`))
      .join("") || listItem("Commands", "No commands yet");
}

async function refresh() {
  const [status, overview, pairing] = await Promise.all([
    api("/api/gateway/family/status"),
    api("/api/gateway/control-plane/overview"),
    api("/api/gateway/device/pairing"),
  ]);
  render(status, overview, pairing);
}

async function openSession() {
  const actorName = document.getElementById("actorName").value.trim() || "Owner";
  const actorRole = document.getElementById("actorRole").value;
  const session = await api("/api/gateway/control-plane/sessions/open", {
    method: "POST",
    body: JSON.stringify({ actor_name: actorName, actor_role: actorRole }),
  });
  state.sessionId = session.session_id;
  document.getElementById("sessionMeta").textContent = `Session ${session.session_id} (${actorRole})`;
  await refresh();
}

async function claimBox() {
  const result = await api("/api/gateway/device/claim", {
    method: "POST",
    body: JSON.stringify({
      actor_user_id: document.getElementById("ownerId").value.trim(),
      actor_name: document.getElementById("ownerName").value.trim(),
      family_name: document.getElementById("familyName").value.trim(),
      claim_token: document.getElementById("claimToken").value.trim(),
    }),
  });
  document.getElementById("claimResult").textContent = result.ok ? `Claimed by ${result.owner_name}` : result.error;
  await refresh();
}

async function unbindBox() {
  const result = await api("/api/gateway/device/unbind", {
    method: "POST",
    body: JSON.stringify({
      actor_user_id: document.getElementById("ownerId").value.trim() || "user-demo",
      actor_name: document.getElementById("ownerName").value.trim() || "Owner",
    }),
  });
  document.getElementById("claimResult").textContent = result.ok ? "Device unbound" : result.error;
  await refresh();
}

async function resetBox() {
  await api("/api/gateway/device/reset", { method: "POST", body: "{}" });
  document.getElementById("claimResult").textContent = "Pairing token reset";
  await refresh();
}

async function dispatch(agentName, actionName, payload) {
  requireSession();
  const result = await api("/api/gateway/control-plane/dispatch", {
    method: "POST",
    body: JSON.stringify({
      session_id: state.sessionId,
      agent_name: agentName,
      action_name: actionName,
      payload,
    }),
  });
  await refresh();
  return result;
}

document.getElementById("openSession").onclick = () => openSession();
document.getElementById("claimBox").onclick = () => claimBox();
document.getElementById("unbindBox").onclick = () => unbindBox();
document.getElementById("resetBox").onclick = () => resetBox();
document.getElementById("manualSubmit").onclick = async () => {
  const text = document.getElementById("manualInput").value.trim();
  if (!text) return;
  await dispatch("family-assistant", "intake.manual", { text });
  document.getElementById("manualInput").value = "";
};
document.getElementById("screenshotSubmit").onclick = async () => {
  const text = document.getElementById("screenshotInput").value.trim();
  if (!text) return;
  await dispatch("family-assistant", "intake.screenshot", { text });
  document.getElementById("screenshotInput").value = "";
};
document.getElementById("refreshDashboard").onclick = () => dispatch("home-automation-assistant", "dashboard.refresh", {});
document.getElementById("wakeTv").onclick = () => dispatch("home-automation-assistant", "tv.wake", {});
document.getElementById("playTts").onclick = () => dispatch("home-automation-assistant", "tts.play", { message: "Time to leave in 15 minutes" });

refresh();
