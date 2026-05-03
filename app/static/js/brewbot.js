/* Brewbot — WebSocket live readings + UI helpers */

// ── Live device readings via WebSocket ────────────────────────────────────────

(function () {
  const WS_URL = `ws://${location.host}/api/ws/readings`;
  let ws, retryDelay = 2000;

  function connect() {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      retryDelay = 2000;
      // Send a ping every 30s to keep the connection alive
      ws._ping = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send("ping"), 30000);
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === "reading")          updateDeviceTile(msg.device_key, msg.value, msg.unit);
        else if (msg.type === "state")       updateDeviceStatus(msg.device_key, msg.online);
        else if (msg.type === "device_registered") location.reload(); // new device — refresh
      } catch (_) {}
    };

    ws.onclose = () => {
      clearInterval(ws._ping);
      setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 1.5, 30000);
    };
  }

  // Only connect on pages that have device tiles
  if (document.querySelector("[data-device-key]")) connect();
})();

function updateDeviceTile(deviceKey, value, unit) {
  const tile = document.querySelector(`[data-device-key="${deviceKey}"]`);
  if (!tile) return;
  const el = tile.querySelector(".device-value");
  if (el) el.textContent = typeof value === "number" ? value.toFixed(1) : value;
  const unitEl = tile.querySelector(".device-unit");
  if (unitEl && unit) unitEl.textContent = "°" + unit;
  updateDeviceStatus(deviceKey, true);
}

function updateDeviceStatus(deviceKey, online) {
  const tile = document.querySelector(`[data-device-key="${deviceKey}"]`);
  if (!tile) return;
  const dot = tile.querySelector(".status-dot");
  if (dot) { dot.classList.toggle("online", online); dot.classList.toggle("offline", !online); }
}

// ── Ingredient row management ─────────────────────────────────────────────────

const _rowCounters = {};

function addIngredientRow(type) {
  if (_rowCounters[type] === undefined) {
    // Count existing rows to set starting index
    _rowCounters[type] = document.querySelectorAll(`[data-row-type="${type}"]`).length;
  }
  const idx = _rowCounters[type]++;
  htmx.ajax("GET", `/htmx/row/${type}?index=${idx}`, {
    target: `#${type}s-tbody`,
    swap: "beforeend",
  });
}

function removeRow(btn) {
  btn.closest("tr").remove();
}

// ── Relay command ─────────────────────────────────────────────────────────────

async function sendCommand(deviceId, action) {
  const btn = event.currentTarget;
  btn.disabled = true;
  try {
    const res = await fetch(`/api/devices/${deviceId}/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    if (!res.ok) throw new Error(await res.text());
  } catch (e) {
    alert("Command failed: " + e.message);
  } finally {
    btn.disabled = false;
  }
}

// ── SRM → hex colour ──────────────────────────────────────────────────────────

const SRM_COLORS = [
  "#FFE699","#FFD878","#FFCA5A","#FFBF42","#FBB123","#F8A600",
  "#F39C00","#EA8F00","#E58500","#DE7C00","#D77200","#CF6900",
  "#CB6200","#C35900","#BB5100","#B54C00","#B04500","#A63E00",
  "#A13700","#9B3200","#952D00","#8E2900","#882300","#821E00",
  "#7B1A00","#771800","#701400","#6A1100","#660D00","#5E0B00",
  "#59080B","#520907","#4A0505","#420606","#3A0404","#370003",
  "#2E0003","#29000B","#240009","#1F0007",
];

function srmColor(srm) {
  if (!srm) return "#ccc";
  const idx = Math.max(0, Math.min(Math.round(srm) - 1, SRM_COLORS.length - 1));
  return SRM_COLORS[idx];
}

document.querySelectorAll(".srm-chip[data-srm]").forEach(el => {
  el.style.backgroundColor = srmColor(parseFloat(el.dataset.srm));
});
