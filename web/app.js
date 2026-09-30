// Radio Scheduler — evidence viewer (read-only, no build step, no framework).
//
// Fetches the JSON files already written by scripts/demo.py,
// scripts/harness6g_demo.py, and scripts/baseline_run.py under evidence/,
// and renders them. It never executes anything and never writes anything.
//
// LIMITATION (documented, not hidden): the harness6g and baseline paths
// below name the one run directory each currently produces. Re-running
// scripts/harness6g_demo.py or scripts/baseline_run.py creates a NEW
// timestamped/hashed directory under evidence/, so these two paths need
// updating by hand to point at the new run. This is intentional v0.1
// simplicity, not an oversight — see web/README.md for how to update it.
const CONFIG = {
  demoPath: "../evidence/demo/results.json",
  harnessPath: "../evidence/harness6g/demo-20260929T230957Z/evidence.json",
  baselinePath: "../evidence/baseline/baseline-claude-code-native-4b22db6bc358/record.json",
};

const STRINGS = {
  pt: {
    "html-lang": "pt-BR",
    h1: "Radio Scheduler — Visualizador de Evidências",
    subtitle:
      'Página estática, somente leitura — lê os arquivos já gerados em <code>evidence/</code> ' +
      "pelos scripts existentes. Não executa nada, não modifica nada. Ver " +
      '<a href="../docs/demo.md">docs/demo.md</a> para os comandos que produzem essas evidências.',
    loading: "Carregando evidências…",
    loaded: "Evidências carregadas.",
    "load-error":
      "Falha ao carregar evidências — se você abriu este arquivo diretamente (file://), " +
      "rode um servidor local (veja web/README.md) e recarregue. Detalhe: ",
    awaiting: "Aguardando dados…",
    "demo-title": "Entrega A — Demonstração dos escalonadores",
    "demo-intro":
      "Round Robin, Proportional Fair e MaxCQI executados sobre os mesmos cenários exógenos, " +
      "com estado inicial independente por algoritmo. Fonte: <code>evidence/demo/results.json</code>.",
    "harness-title": "Entrega B — HARNESS6G (modo replay)",
    "harness-intro":
      "Fluxo materializar → verificar → congelar, replay de candidatos fixos " +
      "(nenhum modelo especializado envolvido). Fonte:",
    "baseline-title": "Entrega C — Baseline (invocação real)",
    "baseline-intro":
      "Configuração <code>claude-code-native</code>, invocação real e não-interativa em worktree " +
      "isolado, candidato avaliado pelo mesmo avaliador do HARNESS6G. Fonte:",
    footer:
      'Gerado a partir de <code>evidence/</code> — ver <a href="../docs/CHECKPOINT.md">docs/CHECKPOINT.md</a> ' +
      "para o estado completo da entrega e " +
      '<a href="../docs/proposal-traceability.md">docs/proposal-traceability.md</a> para o que está ' +
      "implementado vs. em aberto.",
    commit: "Commit",
    "generated-at": "Gerado em",
    scenario: "Cenário",
    "no-decisions": "Nenhuma decisão de alocação em nenhuma TTI.",
    "computational-cost": (reps, wall, cpu, mem) =>
      `Custo computacional (mediana de ${reps} repetições): ${wall} tempo de relógio, ${cpu} CPU, ${mem} pico de memória.`,
    "no-results": "Sem resultados.",
    task: "Tarefa",
    mode: "Modo",
    "termination-reason": "Motivo de término",
    revision: "Revisão",
    "frozen-candidate": "Candidato terminal congelado",
    path: "Caminho",
    "hash-sha256": "Hash sha256",
    interface: "Interface",
    "no-frozen-candidate": "Nenhum candidato foi congelado nesta execução.",
    "model-identity": "model_identity",
    "terminal-hash": "Hash do candidato terminal",
    "public-evaluation": "Avaliação pública/demo",
    "public-evaluation-note": "Não é aceitação protegida final — ver docs/proposal-traceability.md.",
    pass: "PASSOU",
    fail: "FALHOU",
    "load-failed": (path, message) => `Não foi possível carregar ${path}: ${message}`,
  },
  en: {
    "html-lang": "en",
    h1: "Radio Scheduler — Evidence Viewer",
    subtitle:
      'Static, read-only page — reads the files already produced in <code>evidence/</code> ' +
      "by the existing scripts. It runs nothing and modifies nothing. See " +
      '<a href="../docs/demo.md">docs/demo.md</a> for the commands that produce this evidence.',
    loading: "Loading evidence…",
    loaded: "Evidence loaded.",
    "load-error":
      "Failed to load evidence — if you opened this file directly (file://), " +
      "run a local server (see web/README.md) and reload. Detail: ",
    awaiting: "Awaiting data…",
    "demo-title": "Delivery A — Scheduler demonstration",
    "demo-intro":
      "Round Robin, Proportional Fair, and MaxCQI run over the same exogenous scenarios, " +
      "with independent initial state per algorithm. Source: <code>evidence/demo/results.json</code>.",
    "harness-title": "Delivery B — HARNESS6G (replay mode)",
    "harness-intro":
      "Materialize → check → freeze flow, replaying fixed candidates " +
      "(no specialized model involved). Source:",
    "baseline-title": "Delivery C — Baseline (real invocation)",
    "baseline-intro":
      "The <code>claude-code-native</code> configuration, a real non-interactive invocation in an " +
      "isolated worktree, its candidate evaluated by the same evaluator HARNESS6G uses. Source:",
    footer:
      'Generated from <code>evidence/</code> — see <a href="../docs/CHECKPOINT.md">docs/CHECKPOINT.md</a> ' +
      "for the full delivery state and " +
      '<a href="../docs/proposal-traceability.md">docs/proposal-traceability.md</a> for what is ' +
      "implemented vs. still open.",
    commit: "Commit",
    "generated-at": "Generated at",
    scenario: "Scenario",
    "no-decisions": "No allocation decision in any TTI.",
    "computational-cost": (reps, wall, cpu, mem) =>
      `Computational cost (median of ${reps} repetitions): ${wall} wall-clock time, ${cpu} CPU, ${mem} peak memory.`,
    "no-results": "No results.",
    task: "Task",
    mode: "Mode",
    "termination-reason": "Termination reason",
    revision: "Revision",
    "frozen-candidate": "Frozen terminal candidate",
    path: "Path",
    "hash-sha256": "sha256 hash",
    interface: "Interface",
    "no-frozen-candidate": "No candidate was frozen in this run.",
    "model-identity": "model_identity",
    "terminal-hash": "Terminal candidate hash",
    "public-evaluation": "Public/demo evaluation",
    "public-evaluation-note": "Not final protected acceptance — see docs/proposal-traceability.md.",
    pass: "PASSED",
    fail: "FAILED",
    "load-failed": (path, message) => `Could not load ${path}: ${message}`,
  },
};

let currentLang = localStorage.getItem("radio-scheduler-lang") || "pt";
const rawData = { demo: null, harness: null, baseline: null };

function t(key) {
  return STRINGS[currentLang][key];
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function badge(passed) {
  const cls = passed ? "pass" : "fail";
  const label = passed ? t("pass") : t("fail");
  return `<span class="badge ${cls}">${label}</span>`;
}

function formatMs(ns) {
  return (ns / 1e6).toFixed(3) + " ms";
}

function formatKiB(bytes) {
  return (bytes / 1024).toFixed(1) + " KiB";
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function applyStaticStrings() {
  document.getElementById("html-root").lang = t("html-lang");
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const value = t(key);
    if (value !== undefined) {
      el.innerHTML = value;
    }
  });
  document.getElementById("lang-pt").setAttribute("aria-pressed", String(currentLang === "pt"));
  document.getElementById("lang-en").setAttribute("aria-pressed", String(currentLang === "en"));
}

function renderDemo(payload) {
  const container = document.getElementById("demo-content");
  if (!payload) return;
  const results = payload.results || [];
  const byScenario = new Map();
  for (const result of results) {
    if (!byScenario.has(result.scenario_id)) {
      byScenario.set(result.scenario_id, []);
    }
    byScenario.get(result.scenario_id).push(result);
  }

  let html = "";
  html += `<p class="meta-line">${t("commit")}: <code>${escapeHtml(payload.metadata?.commit ?? "?")}</code> · ${t("generated-at")}: ${escapeHtml(payload.metadata?.generated_at ?? "?")}</p>`;

  for (const [scenarioId, scenarioResults] of byScenario) {
    html += `<div class="card">`;
    html += `<h3>${t("scenario")}: <code>${escapeHtml(scenarioId)}</code></h3>`;
    html += `<p class="description">${escapeHtml(scenarioResults[0].scenario_description ?? "")}</p>`;

    for (const result of scenarioResults) {
      html += `<h4>${escapeHtml(result.scheduler_name)} v${escapeHtml(result.scheduler_version)}</h4>`;

      const ttiIndices = Object.keys(result.decisions_by_tti || {}).sort((a, b) => Number(a) - Number(b));
      if (ttiIndices.length === 0) {
        html += `<p class="check-detail">${t("no-decisions")}</p>`;
      } else {
        html += `<div class="table-wrap"><table><thead><tr><th>TTI</th><th>UE</th><th>Resource Blocks</th></tr></thead><tbody>`;
        for (const tti of ttiIndices) {
          for (const entry of result.decisions_by_tti[tti]) {
            const rbs = (entry.resource_block_ids || []).join(", ") || "—";
            html += `<tr><td>${escapeHtml(tti)}</td><td>${escapeHtml(entry.ue_id)}</td><td>${escapeHtml(rbs)}</td></tr>`;
          }
        }
        html += `</tbody></table></div>`;
      }

      const b = result.benchmark;
      if (b) {
        html += `<p class="meta-line">${t("computational-cost")(
          b.repetitions,
          formatMs(b.median_wall_time_ns),
          formatMs(b.median_cpu_time_ns),
          formatKiB(b.median_peak_traced_memory_bytes)
        )}</p>`;
      }
    }
    html += `</div>`;
  }

  container.innerHTML = html || `<p class="placeholder">${t("no-results")}</p>`;
}

function renderHarness(data) {
  document.getElementById("harness-source-path").textContent = CONFIG.harnessPath;
  const container = document.getElementById("harness-content");
  if (!data) return;

  let html = "";
  html += `<p class="meta-line">${t("task")}: <code>${escapeHtml(data.task_id)}</code> v${escapeHtml(data.task_version)} · ${t("mode")}: <code>${escapeHtml(data.mode)}</code> · ${t("termination-reason")}: <strong>${escapeHtml(data.termination_reason)}</strong></p>`;

  for (const observation of data.observations || []) {
    html += `<div class="card">`;
    html += `<h3>${t("revision")} ${observation.revision_index} <span class="check-detail">(hash ${escapeHtml((observation.candidate_hash || "").slice(0, 12) || "—")})</span></h3>`;
    html += `<ul class="check-list">`;
    for (const check of observation.check_results || []) {
      html += `<li>${badge(check.passed)} <strong>${escapeHtml(check.check_id)}</strong> <span class="check-detail">(${escapeHtml(check.category)}) — ${escapeHtml(check.detail)}</span></li>`;
    }
    html += `</ul></div>`;
  }

  if (data.frozen_manifest) {
    html += `<div class="card"><h3>${t("frozen-candidate")}</h3>` +
      `<p class="meta-line">${t("path")}: <code>${escapeHtml(data.frozen_candidate_path)}</code></p>` +
      `<p class="meta-line">${t("hash-sha256")}: <code>${escapeHtml(data.frozen_manifest.content_sha256)}</code></p>` +
      `<p class="meta-line">${t("interface")}: <code>${escapeHtml(data.frozen_manifest.interface_version)}</code></p></div>`;
  } else {
    html += `<p class="placeholder">${t("no-frozen-candidate")}</p>`;
  }

  container.innerHTML = html;
}

function renderBaseline(data) {
  document.getElementById("baseline-source-path").textContent = CONFIG.baselinePath;
  const container = document.getElementById("baseline-content");
  if (!data) return;

  let html = "";
  html += `<div class="card">`;
  html += `<h3>${escapeHtml(data.configuration_id)}</h3>`;
  html += `<p class="meta-line">agent_version: <code>${escapeHtml(data.agent_version)}</code></p>`;
  html += `<p class="meta-line">${t("model-identity")}: ${escapeHtml(data.model_identity)}</p>`;
  html += `<p class="meta-line">base_commit: <code>${escapeHtml(data.base_commit)}</code></p>`;
  html += `<p class="meta-line">invocation_mode: <code>${escapeHtml(data.invocation_mode)}</code></p>`;
  html += `<p class="meta-line">${t("termination-reason")}: <strong>${escapeHtml(data.termination_reason)}</strong></p>`;
  if (data.terminal_hash) {
    html += `<p class="meta-line">${t("terminal-hash")}: <code>${escapeHtml(data.terminal_hash)}</code></p>`;
  }
  html += `</div>`;

  if (data.public_evaluation) {
    html += `<div class="card"><h3>${t("public-evaluation")}</h3>`;
    html += `<p class="check-detail">${t("public-evaluation-note")}</p>`;
    html += `<ul class="check-list">`;
    for (const [category, passed] of Object.entries(data.public_evaluation.categories || {})) {
      html += `<li>${badge(passed)} ${escapeHtml(category)}</li>`;
    }
    html += `</ul></div>`;
  }

  container.innerHTML = html;
}

function renderAll() {
  applyStaticStrings();

  if (rawData.demo) {
    renderDemo(rawData.demo);
  }
  if (rawData.harness) {
    renderHarness(rawData.harness);
  }
  if (rawData.baseline) {
    renderBaseline(rawData.baseline);
  }
}

function showLoadError(sectionId, path, message) {
  document.getElementById(sectionId).innerHTML =
    `<p class="placeholder">${escapeHtml(t("load-failed")(path, message))}</p>`;
}

async function loadAll() {
  const statusEl = document.getElementById("load-status");

  const [demoResult, harnessResult, baselineResult] = await Promise.allSettled([
    fetchJson(CONFIG.demoPath),
    fetchJson(CONFIG.harnessPath),
    fetchJson(CONFIG.baselinePath),
  ]);

  if (demoResult.status === "fulfilled") {
    rawData.demo = demoResult.value;
  } else {
    showLoadError("demo-content", CONFIG.demoPath, demoResult.reason.message);
  }

  if (harnessResult.status === "fulfilled") {
    rawData.harness = harnessResult.value;
  } else {
    showLoadError("harness-content", CONFIG.harnessPath, harnessResult.reason.message);
  }

  if (baselineResult.status === "fulfilled") {
    rawData.baseline = baselineResult.value;
  } else {
    showLoadError("baseline-content", CONFIG.baselinePath, baselineResult.reason.message);
  }

  renderAll();
  statusEl.textContent = t("loaded");
  statusEl.classList.add("ok");
}

function switchLanguage(lang) {
  if (lang === currentLang) return;
  currentLang = lang;
  localStorage.setItem("radio-scheduler-lang", lang);
  renderAll();
}

document.getElementById("lang-pt").addEventListener("click", () => switchLanguage("pt"));
document.getElementById("lang-en").addEventListener("click", () => switchLanguage("en"));

applyStaticStrings();
loadAll().catch((err) => {
  const statusEl = document.getElementById("load-status");
  statusEl.textContent = t("load-error") + err.message;
  statusEl.classList.add("error");
});
