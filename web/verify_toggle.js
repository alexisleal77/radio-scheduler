// Functional check for web/app.js's PT/EN toggle, run against the REAL
// app.js source (not a reimplementation) inside a minimal simulated DOM,
// using the actual committed evidence JSON files. No browser required.
//
// This does not replace an actual visual check in a browser — it proves
// the toggle logic itself is correct (including the specific bug this
// caught: a dynamic <code id="..."> element getting wiped whenever a
// data-i18n ancestor's innerHTML was replaced on language switch).
//
// Run: node web/verify_toggle.js

const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const REPO_ROOT = path.join(__dirname, "..");
const appJs = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");

function makeEl(id, dataI18n) {
  return {
    id,
    _attrs: {},
    innerHTML: "",
    textContent: "",
    getAttribute(name) {
      if (name === "data-i18n") return dataI18n || null;
      return this._attrs[name] ?? null;
    },
    setAttribute(name, value) {
      this._attrs[name] = String(value);
    },
    addEventListener() {},
    classList: {
      _set: new Set(),
      add(c) { this._set.add(c); },
      contains(c) { return this._set.has(c); },
    },
  };
}

// Mirrors the ids/data-i18n attributes actually present in index.html.
const elements = {
  "html-root": makeEl("html-root"),
  "lang-pt": makeEl("lang-pt"),
  "lang-en": makeEl("lang-en"),
  "load-status": makeEl("load-status"),
  "demo-content": makeEl("demo-content"),
  "harness-content": makeEl("harness-content"),
  "baseline-content": makeEl("baseline-content"),
  "harness-source-path": makeEl("harness-source-path"),
  "baseline-source-path": makeEl("baseline-source-path"),
};

const i18nKeys = [
  "h1", "subtitle", "loading", "demo-title", "demo-intro",
  "harness-title", "harness-intro", "baseline-title", "baseline-intro",
  "awaiting", "awaiting", "awaiting", "footer",
];
const i18nEls = i18nKeys.map((key) => makeEl(null, key));

const localStorageStub = (() => {
  const store = {};
  return {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
  };
})();

const fixtures = {
  demo: JSON.parse(fs.readFileSync(path.join(REPO_ROOT, "evidence/demo/results.json"), "utf8")),
  harness: JSON.parse(fs.readFileSync(path.join(REPO_ROOT, "evidence/harness6g/demo-20260929T230957Z/evidence.json"), "utf8")),
  baseline: JSON.parse(fs.readFileSync(path.join(REPO_ROOT, "evidence/baseline/baseline-claude-code-native-4b22db6bc358/record.json"), "utf8")),
};

function fetchStub(url) {
  let data;
  if (url.includes("demo/results.json")) data = fixtures.demo;
  else if (url.includes("harness6g")) data = fixtures.harness;
  else if (url.includes("baseline")) data = fixtures.baseline;
  else return Promise.reject(new Error("unexpected fetch: " + url));
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(data) });
}

const documentStub = {
  getElementById: (id) => {
    if (!elements[id]) throw new Error("getElementById: unknown id " + id);
    return elements[id];
  },
  querySelectorAll: (sel) => {
    if (sel === "[data-i18n]") return i18nEls;
    throw new Error("unexpected selector " + sel);
  },
};

const sandbox = { console, fetch: fetchStub, localStorage: localStorageStub, document: documentStub, Promise, setTimeout };
vm.createContext(sandbox);
vm.runInContext(appJs, sandbox, { filename: "app.js" });

function h1El() {
  return i18nEls.find((e) => e.getAttribute("data-i18n") === "h1");
}

function badgeLabel(container) {
  return elements[container].innerHTML.match(/badge (?:pass|fail)">([A-Z]+)</)?.[1];
}

setTimeout(() => {
  let failures = 0;
  function check(label, fn) {
    try {
      fn();
      console.log(`ok - ${label}`);
    } catch (err) {
      failures += 1;
      console.log(`FAIL - ${label}: ${err.message}`);
    }
  }

  check("initial language is PT", () => {
    assert.strictEqual(elements["lang-pt"]._attrs["aria-pressed"], "true");
    assert.strictEqual(h1El().innerHTML, "Radio Scheduler — Visualizador de Evidências");
  });

  check("real evidence rendered (table + badges present)", () => {
    assert.ok(elements["demo-content"].innerHTML.includes("<table>"));
    assert.ok(elements["harness-content"].innerHTML.includes("badge"));
    assert.ok(elements["baseline-content"].innerHTML.includes("badge"));
  });

  const harnessPathBefore = elements["harness-source-path"].textContent;
  const baselinePathBefore = elements["baseline-source-path"].textContent;

  sandbox.switchLanguage("en");

  check("switching to EN updates static text and button state", () => {
    assert.strictEqual(elements["lang-en"]._attrs["aria-pressed"], "true");
    assert.strictEqual(elements["lang-pt"]._attrs["aria-pressed"], "false");
    assert.strictEqual(h1El().innerHTML, "Radio Scheduler — Evidence Viewer");
  });

  check("switching to EN does not wipe the dynamic source-path elements (regression check)", () => {
    assert.strictEqual(elements["harness-source-path"].textContent, harnessPathBefore);
    assert.strictEqual(elements["baseline-source-path"].textContent, baselinePathBefore);
  });

  check("switching to EN re-renders check badges in English", () => {
    assert.strictEqual(badgeLabel("harness-content"), "PASSED");
  });

  sandbox.switchLanguage("pt");

  check("switching back to PT restores Portuguese text and badges", () => {
    assert.strictEqual(h1El().innerHTML, "Radio Scheduler — Visualizador de Evidências");
    assert.strictEqual(badgeLabel("harness-content"), "PASSOU");
    assert.strictEqual(elements["harness-source-path"].textContent, harnessPathBefore);
  });

  console.log(failures === 0 ? "\nAll checks passed." : `\n${failures} check(s) FAILED.`);
  process.exit(failures === 0 ? 0 : 1);
}, 50);
