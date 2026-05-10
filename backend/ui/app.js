const API = "/admin";

async function api(url, opts = {}) {
  const key = localStorage.getItem("api_key");
  if (key) {
    opts.headers = { ...opts.headers, "Authorization": "Bearer " + key };
  }
  const r = await fetch(API + url, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

const PROVIDERS = {
  alibaba: { name: "Alibaba Cloud (DashScope)", base: "https://dashscope.aliyuncs.com" },
  zhipu: { name: "Zhipu AI (GLM)", base: "https://open.bigmodel.cn/api/paas/v4" },
  openai: { name: "OpenAI", base: "https://api.openai.com/v1" },
};

async function load() {
  const data = await api("/providers");
  const g = document.getElementById("providers");
  g.innerHTML = Object.entries(PROVIDERS).map(([k, v]) => {
    const c = data[k] || {};
    const hasKey = c.api_key && c.api_key.length > 3;
    const m = c.enabled_models || {};
    return renderCard(k, v, hasKey, m);
  }).join("");
}

function renderCard(ptype, info, hasKey, models) {
  return `<div class="card">
    <h3>${info.name} <span class="badge${hasKey ? "" : " off"}">${hasKey ? "Configured" : "Not set"}</span></h3>
    <label>API Key</label>
    <input id="key-${ptype}" type="password" placeholder="sk-...">
    <button onclick="saveKey('${ptype}')">Save & Test</button>
    <span class="status" id="status-${ptype}"></span>
    <label>Embedding Model</label>
    <input id="emb-${ptype}" placeholder="text-embedding-v3" value="${models.embedding || ''}">
    <label>Rerank Model</label>
    <input id="rerank-${ptype}" placeholder="qwen3-rerank" value="${models.rerank || ''}">
    <button onclick="saveModels('${ptype}')">Save Models</button>
  </div>`;
}

async function saveKey(ptype) {
  const key = document.getElementById("key-" + ptype).value;
  const s = document.getElementById("status-" + ptype);
  try {
    await api("/providers/" + ptype, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: key }),
    });
    const valid = await api("/providers/" + ptype + "/validate");
    s.textContent = valid.valid ? "Valid API key" : "Invalid key";
    s.className = "status " + (valid.valid ? "ok" : "err");
    load();
  } catch (e) {
    s.textContent = "Error: " + e.message;
    s.className = "status err";
  }
}

async function saveModels(ptype) {
  const emb = document.getElementById("emb-" + ptype).value;
  const rerank = document.getElementById("rerank-" + ptype).value;
  const models = {};
  if (emb) models.embedding = emb;
  if (rerank) models.rerank = rerank;
  await api("/providers/" + ptype, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled_models: models }),
  });
  load();
}

async function loadEnv() {
  try {
    const e = await api("/environment");
    document.getElementById("env-info").textContent = JSON.stringify(e, null, 2);
  } catch (err) {
    document.getElementById("env-info").textContent = "Unavailable: " + err.message;
  }
}

load();
loadEnv();
loadRecommendations();
loadSettings();


async function loadSettings() {
  try {
    const s = await api("/settings");
    const el = document.getElementById("bm25-status");
    if (el) {
      const avail = s.bm25_available ? "Detected" : "Not available on this system";
      const mode = s.bm25_enabled === "1" ? "Forced ON" : s.bm25_enabled === "0" ? "Forced OFF" : "Auto (" + avail + ")";
      el.textContent = mode;
      el.className = "status " + (s.bm25_available || s.bm25_enabled === "1" ? "ok" : "err");
    }
  } catch(e) {}
}

async function toggleBM25() {
  try {
    const s = await api("/settings");
    const next = s.bm25_enabled === "1" ? "0" : "1";
    await api("/settings", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({bm25_enabled: next}),
    });
    loadSettings();
  } catch(e) {}
}


async function loadRecommendations() {
  try {
    const data = await api("/recommendations");
    let html = "";
    for (const r of data.recommendations || []) {
      html += '<div style="margin:8px 0;padding:8px;background:#0d1117;border-radius:6px">';
      html += '<strong>' + r.type.toUpperCase() + '</strong>: ' + r.model;
      html += '<br><span style="font-size:11px;color:#8b949e">' + r.reason + ' (' + r.size + ')</span>';
      html += '<br><code style="font-size:11px">' + r.install + '</code>';
      html += '</div>';
    }
    document.getElementById("recs").innerHTML = html;
  } catch(e) {
    document.getElementById("recs").textContent = "Unavailable";
  }
}
