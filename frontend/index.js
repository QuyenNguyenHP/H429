(function () {
  const config = window.APP_CONFIG || {};
  const paths = config.paths || {};
  const API_BASE = config.apiBaseUrl || window.API_BASE_URL || "http://localhost:8000";
  const API_PATH = paths.analog || "/api/live/analog_lable_value";
  const POLL_MS = Number(config.refreshMs) > 0 ? Number(config.refreshMs) : 5000;

  const grid = document.getElementById("grid");
  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  const lastUpdated = document.getElementById("lastUpdated");
  const errorText = document.getElementById("errorText");
  const sourceText = document.getElementById("sourceText");
  const dgSelector = document.getElementById("dgSelector");

  sourceText.textContent = `Source: ${API_BASE}${API_PATH}`;

  function formatNumber(value) {
    const n = Number(value);
    if (Number.isNaN(n)) return "--";
    if (Math.abs(n) >= 100) return n.toFixed(1);
    if (Math.abs(n) >= 10) return n.toFixed(2);
    return n.toFixed(3);
  }

  function render(rows) {
    grid.innerHTML = "";
    const orderedRows = rows.slice();

    orderedRows.forEach((item) => {
        const card = document.createElement("article");
        card.className = "card";

        const h3 = document.createElement("h3");
        h3.textContent = item.label || "Unknown label";

        const val = document.createElement("div");
        val.className = "value";
        val.textContent = formatNumber(item.value);

        card.appendChild(h3);
        card.appendChild(val);
        grid.appendChild(card);
      });
  }

  function bindDGSelector() {
    if (!dgSelector) return;
    dgSelector.addEventListener("click", (ev) => {
      const btn = ev.target.closest(".dg-btn");
      if (!btn) return;
      const dg = String(btn.getAttribute("data-dg") || "").trim();
      if (!["1", "2", "3", "4"].includes(dg)) return;
      window.location.href = `./DGs_dashboard.html?dg=${dg}`;
    });
  }

  function setConnected(ok) {
    statusDot.className = ok ? "dot good" : "dot bad";
    statusText.textContent = ok ? "Connected" : "Disconnected";
  }

  async function load() {
    try {
      const res = await fetch(`${API_BASE}${API_PATH}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      const rows = Array.isArray(data) ? data : [];
      render(rows);
      errorText.textContent = "";
      setConnected(true);
      lastUpdated.textContent = `Updated ${new Date().toLocaleTimeString()}`;
    } catch (err) {
      setConnected(false);
      errorText.textContent = err.message || "Failed to load data";
    }
  }

  load();
  bindDGSelector();
  setInterval(load, POLL_MS);
})();

