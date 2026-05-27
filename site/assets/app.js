"use strict";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CORE_URL   = "graph-core.json";
const DETAIL_URL = "graph-detail.json";
const GRID_CAP = 200;

// Honour the user's reduced-motion preference: disables the force-graph
// animation + any decorative transitions when set.
const PREFERS_REDUCED_MOTION =
  window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// localStorage keys (persistence + onboarding flags)
const LS = {
  facets:    "wd.facets.v1",
  tab:       "wd.tab.v1",
  word:      "wd.word.v1",
  onboarded: "wd.onboarded.v1",
  theme:     "wd.theme",
};

function lsGet(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
function lsSet(key, val) { try { localStorage.setItem(key, val); } catch (e) {} }
function lsDel(key) { try { localStorage.removeItem(key); } catch (e) {} }

// Theme: light is the default. Persisted under "wd.theme"; the document's
// data-theme attribute drives the CSS palette. d3 charts read JS colour
// literals at render time, so a flip also swaps the JS palette and re-renders
// the active view (wireThemeToggle, below).
function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

// Categorical drift-type palette. LIGHT theme is the default; these literals
// mirror the LIGHT CSS vars in explore.css :root. The dark variants live under
// THEME_PALETTES.dark and are applied by applyThemePalette() on theme change so
// d3 charts (which read these JS literals at render time) stay in sync.
const DT_COLORS = {
  pejoration:      "#dc2626",
  amelioration:    "#15803d",
  broadening:      "#4338ca",
  narrowing:       "#7c3aed",
  metaphorization: "#b26a00",
  metonymization:  "#c2410c",
  reversal:        "#be185d",
  reappropriation: "#0f766e",
  unknown:         "#73788c",
};

const CONN_COLORS = {
  positive: "#15803d",
  neutral:  "#6b7280",
  negative: "#dc2626",
};

let TRIGGER_COLOR = "#b26a00";
let DRIFT_EDGE_COLOR = "#4338ca";
// BG_COLOR is the canvas behind every chart and the exported-PNG background, and
// it doubles as the separator stroke around beeswarm dots. On the light theme it
// is the white card colour; on dark it is the panel colour.
let BG_COLOR = "#ffffff";

// Cause lens: up to 5 trigger labels get distinct colours; gradual = faint.
// LIGHT defaults; swapped for dark by applyThemePalette().
let CAUSE_PALETTE = ["#b26a00", "#be185d", "#0369a1", "#0f766e", "#e11d48"];
let CAUSE_GRADUAL_COLOR = "#73788c";

// Chart-chrome tokens (axis lines/ticks, gridlines, axis + muted labels, gloss
// body text, graph node/arrow strokes, themed accent). LIGHT defaults; swapped
// for dark by applyThemePalette(). These mirror the --text*/--border/--accent
// CSS vars so d3 chrome stays legible on whichever canvas is active. Read at
// render time so a theme flip reflows correctly.
let ACCENT_COLOR = "#4338ca";  // themed brand accent (drift arrow blue/indigo)
let GLOSS_TEXT   = "#1b1b2a";  // chart body text (sense gloss); AA on canvas
let AXIS_TEXT    = "#5a5f72";  // axis tick + secondary label text
let FAINT_TEXT   = "#73788c";  // faintest chart labels / hints
let GRID_LINE    = "#e4dfd4";  // axis lines, ticks, gridlines
let NODE_STROKE  = "#8a8d9c";  // graph node + arrow stroke (mid-grey)

// Per-theme palette tables. applyThemePalette() mutates the live colour
// objects/scalars in place so existing references (WD.colors, dtColor, etc.)
// keep working without rebinding.
const THEME_PALETTES = {
  light: {
    DT: { pejoration:"#dc2626", amelioration:"#15803d", broadening:"#4338ca",
          narrowing:"#7c3aed", metaphorization:"#b26a00", metonymization:"#c2410c",
          reversal:"#be185d", reappropriation:"#0f766e", unknown:"#73788c" },
    CONN: { positive:"#15803d", neutral:"#6b7280", negative:"#dc2626" },
    TRIGGER: "#b26a00", DRIFT_EDGE: "#4338ca", BG: "#ffffff",
    CAUSE: ["#b26a00", "#be185d", "#0369a1", "#0f766e", "#e11d48"],
    CAUSE_GRADUAL: "#73788c",
    ACCENT: "#4338ca", GLOSS_TEXT: "#1b1b2a", AXIS_TEXT: "#5a5f72",
    FAINT_TEXT: "#73788c", GRID_LINE: "#e4dfd4", NODE_STROKE: "#8a8d9c",
  },
  dark: {
    DT: { pejoration:"#f05252", amelioration:"#2ecc7a", broadening:"#5b7cf8",
          narrowing:"#a78bfa", metaphorization:"#f5a623", metonymization:"#fb923c",
          reversal:"#e879f9", reappropriation:"#34d399", unknown:"#4e556d" },
    CONN: { positive:"#2ecc7a", neutral:"#8a94b0", negative:"#f05252" },
    TRIGGER: "#f5a623", DRIFT_EDGE: "#5b7cf8", BG: "#13141f",
    CAUSE: ["#f5a623", "#e879f9", "#38bdf8", "#34d399", "#fb7185"],
    CAUSE_GRADUAL: "#4e556d",
    ACCENT: "#5b7cf8", GLOSS_TEXT: "#dde1f0", AXIS_TEXT: "#8b93b4",
    FAINT_TEXT: "#4e556d", GRID_LINE: "#2e3245", NODE_STROKE: "#8a94b0",
  },
};

// Mutate the live colour state to match a theme ("light" | "dark").
function applyThemePalette(theme) {
  const p = THEME_PALETTES[theme] || THEME_PALETTES.light;
  Object.assign(DT_COLORS, p.DT);
  Object.assign(CONN_COLORS, p.CONN);
  TRIGGER_COLOR = p.TRIGGER;
  DRIFT_EDGE_COLOR = p.DRIFT_EDGE;
  BG_COLOR = p.BG;
  CAUSE_PALETTE = p.CAUSE.slice();
  CAUSE_GRADUAL_COLOR = p.CAUSE_GRADUAL;
  ACCENT_COLOR = p.ACCENT;
  GLOSS_TEXT = p.GLOSS_TEXT;
  AXIS_TEXT = p.AXIS_TEXT;
  FAINT_TEXT = p.FAINT_TEXT;
  GRID_LINE = p.GRID_LINE;
  NODE_STROKE = p.NODE_STROKE;
}

// Restore the persisted theme (default light) before anything renders, so the
// first paint already uses the correct CSS vars and JS palette.
(function initTheme() {
  const stored = lsGet(LS.theme);
  const theme = stored === "dark" ? "dark" : "light";
  if (theme === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
  applyThemePalette(theme);
})();

// Re-render whatever view is active so d3 charts pick up the new JS palette.
function rerenderActiveView() {
  const overviewActive = document.getElementById("panel-overview").classList.contains("active");
  const triggersActive = document.getElementById("panel-triggers").classList.contains("active");
  const detailActive   = document.getElementById("panel-detail").classList.contains("active");

  if (overviewActive && typeof renderOverviewTimeline === "function") renderOverviewTimeline();
  if (triggersActive && typeof renderTriggerTimeline === "function") {
    triggerTlRendered = false;
    renderTriggerTimeline();
  }
  if (detailActive && currentDetailWord && currentDetailWord.__detailMerged) {
    renderDetailDashboard(currentDetailWord);
    document.getElementById("detail-triggers").hidden = true;
    renderDetailTimeline(currentDetailWord);
    renderDetailGraph(currentDetailWord);
  }
  // Re-fire the active plugin view (network/map/trends/compare) so it rebuilds
  // its SVG with the live colours.
  const activePanel = document.querySelector(".exp-panel.active");
  if (activePanel) {
    const view = viewRegistry.get(activePanel.id.replace(/^panel-/, ""));
    if (view && view.activated && typeof view.onActivate === "function") {
      try { view.onActivate(activePanel); } catch (e) {}
    }
  }
}

// Flip between light and dark, persist, swap the JS palette, re-render.
function toggleTheme() {
  const next = currentTheme() === "dark" ? "light" : "dark";
  if (next === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
  lsSet(LS.theme, next);
  applyThemePalette(next);
  rerenderActiveView();
}

// Create + wire the header sun/moon toggle. The button label/icon is driven by
// CSS (.theme-toggle .icon-* under [data-theme]).
function wireThemeToggle() {
  const host = document.querySelector(".topbar-actions") || document.querySelector(".site-nav");
  if (!host || document.getElementById("wd-theme-toggle")) return;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.id = "wd-theme-toggle";
  btn.className = "theme-toggle";
  btn.setAttribute("aria-label", "Toggle light or dark theme");
  btn.title = "Toggle light / dark theme";
  btn.innerHTML = '<span class="icon-dark" aria-hidden="true">☾</span>' +
                  '<span class="icon-light" aria-hidden="true">☀</span>';
  btn.addEventListener("click", toggleTheme);
  host.appendChild(btn);
}
let CAUSE_COLOR_MAP = {};   // built once data loads: triggerLabel -> colour

function buildCauseColorMap(driftEventsFlat) {
  // Count how many events each trigger label covers, take top-5
  const freq = {};
  driftEventsFlat.forEach(e => {
    (e.causes || []).forEach(c => {
      if (c.triggerLabel) freq[c.triggerLabel] = (freq[c.triggerLabel] || 0) + 1;
    });
  });
  const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]);
  CAUSE_COLOR_MAP = {};
  sorted.forEach(([label], i) => {
    CAUSE_COLOR_MAP[label] = CAUSE_PALETTE[i] || CAUSE_PALETTE[CAUSE_PALETTE.length - 1];
  });
}

// Returns the colour for a dot in cause lens (uses top hypothesis if multiple)
function causeColor(eventNode) {
  const causes = eventNode.causes || [];
  if (causes.length === 0) return CAUSE_GRADUAL_COLOR;
  const top = causes[0]; // highest confidence (already sorted)
  return CAUSE_COLOR_MAP[top.triggerLabel] || CAUSE_PALETTE[CAUSE_PALETTE.length - 1];
}

function dtColor(typeStr) {
  if (!typeStr) return DT_COLORS.unknown;
  // Multi-type: use first
  const first = typeStr.split(",")[0].trim().toLowerCase();
  return DT_COLORS[first] || DT_COLORS.unknown;
}

function connColor(label) {
  if (!label) return CONN_COLORS.neutral;
  return CONN_COLORS[label.toLowerCase()] || CONN_COLORS.neutral;
}

function dtBg(typeStr) {
  const c = dtColor(typeStr);
  return c + "22";
}

// Lens state: "type" | "cause"
let currentLens = "type";
let showLinks = false;

// ---------------------------------------------------------------------------
// Tooltip
// ---------------------------------------------------------------------------

const expTooltip = document.getElementById("exp-tooltip");

function showTip(html, event) {
  expTooltip.innerHTML = html;
  expTooltip.style.display = "block";
  placeTip(event);
}

function hideTip() { expTooltip.style.display = "none"; }

function placeTip(event) {
  const pad = 14;
  let x = event.clientX + pad;
  let y = event.clientY + pad;
  const w = expTooltip.offsetWidth;
  const h = expTooltip.offsetHeight;
  if (x + w > window.innerWidth  - 8) x = event.clientX - w - pad;
  if (y + h > window.innerHeight - 8) y = event.clientY - h - pad;
  expTooltip.style.left = x + "px";
  expTooltip.style.top  = y + "px";
}

document.addEventListener("mousemove", (e) => {
  if (expTooltip.style.display !== "none") placeTip(e);
});

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// `graphData` holds graph-core (LIGHT words + shared aggregates). Heavy
// per-word detail (senses / driftEvents / frequencyObservations) lives in
// `detailData` and is merged onto a word object on demand via ensureDetail().
let graphData = null;
let detailData = null;          // wordId -> { senses, driftEvents, frequencyObservations, sources }
let detailPromise = null;       // single in-flight fetch of graph-detail.json
let flatByWord = new Map();     // "writtenForm|lang" -> [driftEventsFlat entries]

// Index driftEventsFlat by "word|lang" so card/filter code never scans the
// whole flat array per word.
function buildFlatIndex(flat) {
  flatByWord = new Map();
  (flat || []).forEach(e => {
    const key = e.word + "|" + e.lang;
    if (!flatByWord.has(key)) flatByWord.set(key, []);
    flatByWord.get(key).push(e);
  });
}

function flatFor(word) {
  return flatByWord.get(word.writtenForm + "|" + (word.language || "?")) || [];
}

// Fetch graph-detail.json exactly once; resolves to the wordId->detail map.
function loadDetail() {
  if (detailData) return Promise.resolve(detailData);
  if (detailPromise) return detailPromise;
  detailPromise = fetch(DETAIL_URL)
    .then(r => {
      if (!r.ok) throw new Error("Could not load " + DETAIL_URL + " (" + r.status + ")");
      return r.json();
    })
    .then(map => { detailData = map; return map; })
    .catch(err => {
      console.error(err);
      detailPromise = null;   // allow a later retry
      throw err;
    });
  return detailPromise;
}

// Merge heavy detail onto a LIGHT word object in place (idempotent), returning
// the same word. Safe to call once detailData is loaded.
function mergeDetail(word) {
  if (!word || word.__detailMerged) return word;
  const d = detailData && detailData[word.id];
  if (d) {
    word.senses = d.senses || [];
    word.driftEvents = d.driftEvents || [];
    word.frequencyObservations = d.frequencyObservations || [];
    if (d.sources && !word.sources) word.sources = d.sources;
    word.__detailMerged = true;
  }
  return word;
}

// Resolve a word's heavy detail, fetching graph-detail.json if needed.
// Returns a Promise<word> (word with senses/driftEvents/frequencyObservations).
function ensureDetail(word) {
  if (!word) return Promise.resolve(word);
  if (word.__detailMerged) return Promise.resolve(word);
  return loadDetail().then(() => mergeDetail(word));
}

const state = {
  search:     "",
  langs:      new Set(),
  types:      new Set(),
  connotations: new Set(),
  evidences:  new Set(),
  // Source and quality facets.
  // When non-empty = include only those matching.
  // Default: "detected" (Frequency) excluded; high+benchmark on.
  // We represent this as an EXCLUDE set: words whose SOLE quality is
  // in excludedQualities are hidden. Using explicit include sets instead:
  sources:    new Set(),   // empty = all sources allowed
  qualities:  new Set(),   // empty = all qualities allowed; populated with defaults on init
  hasTrigger: false,
  yearFrom:   null,
  yearTo:     null,
  // brush-driven year range (from overview timeline)
  brushYearFrom: null,
  brushYearTo:   null,
};

// Derived year range: brush overrides inputs when set
function effectiveYearFrom() { return state.brushYearFrom ?? state.yearFrom; }
function effectiveYearTo()   { return state.brushYearTo   ?? state.yearTo;   }

let currentDetailWord = null;

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------

// Tab buttons + panels are re-queried on demand because view modules register
// extra tabs (Compare/Network/Map/Trends) that exist in the DOM up front.
function allTabBtns() { return document.querySelectorAll(".exp-tab-btn"); }
function allPanels()  { return document.querySelectorAll(".exp-panel"); }

// Registry of plugin views: name -> { label, panelId, onActivate, activated }
const viewRegistry = new Map();

function switchTab(tab) {
  allTabBtns().forEach(b => {
    const isActive = b.dataset.tab === tab;
    b.classList.toggle("active", isActive);
    b.setAttribute("aria-selected", isActive ? "true" : "false");
  });
  allPanels().forEach(p => p.classList.remove("active"));
  const panel = document.getElementById("panel-" + tab);
  if (panel) {
    panel.classList.add("active");
    if (tab === "triggers") renderTriggerTimeline();
    // Registered plugin view: fire its onActivate the first time (and re-fire
    // on every activation so views can refresh to the current data/filters).
    const view = viewRegistry.get(tab);
    if (view && typeof view.onActivate === "function") {
      try { view.onActivate(panel); }
      catch (e) { console.error("view onActivate failed for " + tab, e); }
      view.activated = true;
    }
  }
  if (tab !== "detail") lsSet(LS.tab, tab);
}

// Delegated click handler so dynamically-added tab buttons work too.
document.querySelector(".exp-tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".exp-tab-btn");
  if (btn && btn.dataset.tab) switchTab(btn.dataset.tab);
});

// Back button
document.getElementById("detail-back-btn").addEventListener("click", () => {
  switchTab("overview");
});

// Detail sub-tabs
document.querySelectorAll(".detail-tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".detail-tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".detail-sub-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("detail-" + btn.dataset.dtab + "-panel").classList.add("active");
  });
});

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

showGridSkeleton();

fetch(CORE_URL)
  .then(r => {
    if (!r.ok) throw new Error("Could not load " + CORE_URL + " (" + r.status + ")");
    return r.json();
  })
  .then(data => {
    graphData = data;
    buildFlatIndex(data.driftEventsFlat || []);
    buildCauseColorMap(data.driftEventsFlat || []);
    initMetaBar(data.meta);
    initFacets(data.facets);
    buildDriftTypeLegend(data.facets.driftType);
    initLensControls();
    renderOverviewTimeline();
    window.WD.core = graphData;   // data now available to view modules
    restoreFacets();      // restore persisted facet state (before first grid render)
    // renderWordGrid called via applyFilters so quality default is applied
    applyFilters();
    initSearch();
    wireThemeToggle();
    maybeShowOnboarding();
    // Deep-link wins over persisted last-tab/word; else restore session.
    const hadDeepLink = applyDeepLink();
    if (!hadDeepLink) restoreSession();

    // Eagerly pull heavy detail once in the background, just after first paint,
    // so the first word-open is instant. A word opened before this lands shows
    // an inline loader (see openWordDetail).
    requestIdleOrTimeout(() => { loadDetail().catch(() => {}); }, 400);
  })
  .catch(err => {
    console.error(err);
    const grid = document.getElementById("word-grid");
    if (grid) grid.innerHTML =
      '<p class="empty-msg">Error loading data: ' + escHtml(err.message) + "</p>";
    const info = document.getElementById("grid-info");
    if (info) info.textContent = "";
  });

// Run a callback when the browser is idle, falling back to a timeout.
function requestIdleOrTimeout(fn, ms) {
  if (typeof window.requestIdleCallback === "function") {
    window.requestIdleCallback(fn, { timeout: ms + 1500 });
  } else {
    setTimeout(fn, ms);
  }
}

// Skeleton placeholder cards while graph-core.json is in flight.
function showGridSkeleton() {
  const grid = document.getElementById("word-grid");
  const info = document.getElementById("grid-info");
  if (info) info.innerHTML = '<span class="grid-loading"><span class="wd-spinner" aria-hidden="true"></span> Loading the knowledge graph&hellip;</span>';
  if (grid) {
    let html = "";
    for (let i = 0; i < 9; i++) html += '<div class="word-card skeleton-card" aria-hidden="true"></div>';
    grid.innerHTML = html;
  }
}

// ---------------------------------------------------------------------------
// Lens controls (Color by: Drift type | Cause)
// ---------------------------------------------------------------------------

function initLensControls() {
  const btnType  = document.getElementById("lens-type");
  const btnCause = document.getElementById("lens-cause");
  const linksChk = document.getElementById("show-links");

  btnType.addEventListener("click", () => {
    currentLens = "type";
    btnType.classList.add("active");
    btnCause.classList.remove("active");
    applyLens();
    updateLegendForLens();
  });

  btnCause.addEventListener("click", () => {
    currentLens = "cause";
    btnCause.classList.add("active");
    btnType.classList.remove("active");
    applyLens();
    updateLegendForLens();
  });

  linksChk.addEventListener("change", e => {
    showLinks = e.target.checked;
    applyLens();
  });
}

// Re-colour the dots + toggle connector lines without full re-render
function applyLens() {
  if (!overviewDotsSel) return;

  const fw = new Set(filteredWords().map(w => w.writtenForm + "|" + w.language));

  overviewDotsSel
    .attr("fill", n => currentLens === "cause" ? causeColor(n) : dtColor(n.type))
    .attr("stroke", n => {
      if (currentLens === "cause" && (n.causes || []).length > 0) return causeColor(n);
      return BG_COLOR;
    })
    .attr("stroke-width", n => (currentLens === "cause" && (n.causes || []).length > 0) ? 1.5 : 0.5)
    .attr("r", n => fw.has(n.word + "|" + n.lang) ? 5 : 4)
    .attr("opacity", n => {
      const active = fw.has(n.word + "|" + n.lang);
      if (!active) return 0.15;
      if (currentLens === "cause" && (n.causes || []).length === 0) return 0.45;
      return 0.85;
    });

  // Show/hide connector lines
  if (overviewConnectorsSel) {
    overviewConnectorsSel.attr("display", showLinks ? null : "none");
  }
}

function updateLegendForLens() {
  const legend = document.getElementById("dt-legend");
  const title  = document.getElementById("legend-title");
  if (!graphData) return;

  if (currentLens === "type") {
    title.textContent = "Drift type colours";
    buildDriftTypeLegend(graphData.facets.driftType);
  } else {
    title.textContent = "Cause colours";
    buildCauseLegend();
  }
}

// ---------------------------------------------------------------------------
// Meta bar
// ---------------------------------------------------------------------------

function initMetaBar(meta) {
  if (!meta) return;
  const chips = document.getElementById("meta-chips");
  const langStr = Object.entries(meta.byLanguage || {})
    .map(([l, n]) => n + " " + l.toUpperCase())
    .join(", ");
  chips.innerHTML = [
    '<span class="stat-chip"><strong>' + meta.words + '</strong> words</span>',
    '<span class="stat-chip"><strong>' + meta.driftEvents + '</strong> drift events</span>',
    '<span class="stat-chip"><strong>' + meta.triggers + '</strong> triggers</span>',
    langStr ? '<span class="stat-chip">' + langStr + '</span>' : "",
  ].join("");
}

// ---------------------------------------------------------------------------
// Facets
// ---------------------------------------------------------------------------

// Source-label -> CSS class slug
const SOURCE_SLUG = {
  "Curated":   "curated",
  "GfdS":      "gfds",
  "OWID":      "owid",
  "DWUG":      "dwug",
  "SemEval":   "semeval",
  "Frequency": "frequency",
};

// Quality -> CSS class
const QUALITY_CLASS = {
  "high":       "q-high",
  "benchmark":  "q-benchmark",
  "detected":   "q-detected",
};

function initFacets(facets) {
  const LANG_LABELS = { en: "English", de: "German" };

  buildChips("facet-lang", facets.language, l => LANG_LABELS[l] || l, "lang");
  buildChips("facet-type", facets.driftType, t => t, "type");
  buildChips("facet-connotation", facets.connotation, c => c, "connotation");
  buildChips("facet-evidence", facets.evidenceType, e => e, "evidence");
  buildChips("facet-source", facets.source || [], s => s, "source");
  buildChips("facet-quality", facets.quality || [], q => q, "quality");

  // Apply default: high + benchmark ON, detected OFF.
  // We activate quality chips for "high" and "benchmark" by default.
  const defaultOnQualities = (facets.quality || []).filter(q => q !== "detected");
  defaultOnQualities.forEach(q => {
    state.qualities.add(q);
    syncChip("facet-quality", q, true);
  });

  document.getElementById("facet-search").addEventListener("input", e => {
    state.search = e.target.value.trim().toLowerCase();
    applyFilters();
  });

  document.getElementById("year-from").addEventListener("change", e => {
    state.yearFrom = e.target.value ? parseInt(e.target.value) : null;
    applyFilters();
  });

  document.getElementById("year-to").addEventListener("change", e => {
    state.yearTo = e.target.value ? parseInt(e.target.value) : null;
    applyFilters();
  });

  document.getElementById("facet-has-trigger").addEventListener("change", e => {
    state.hasTrigger = e.target.checked;
    applyFilters();
  });

  document.getElementById("clear-all-btn").addEventListener("click", (e) => {
    e.stopPropagation();   // don't toggle the mobile drawer
    clearAllFilters();
  });

  // Mobile: the facet panel header toggles a collapsible drawer. On desktop
  // the body is always visible (CSS), so this toggle is a no-op there.
  const facetPanel = document.querySelector(".facet-panel");
  const facetHeader = document.querySelector(".facet-panel-header");
  if (facetHeader && facetPanel) {
    facetHeader.setAttribute("role", "button");
    facetHeader.setAttribute("tabindex", "0");
    facetHeader.setAttribute("aria-expanded", "false");
    const toggle = () => {
      const open = facetPanel.classList.toggle("facet-open");
      facetHeader.setAttribute("aria-expanded", open ? "true" : "false");
    };
    facetHeader.addEventListener("click", (e) => {
      if (e.target.closest(".facet-clear-btn")) return;
      toggle();
    });
    facetHeader.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
    });
  }
}

function buildChips(containerId, values, labelFn, facetKey) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = "";

  values.forEach(val => {
    const btn = document.createElement("button");
    btn.className = "facet-chip";
    btn.textContent = labelFn(val);
    btn.dataset.value = val;
    btn.setAttribute("aria-pressed", "false");

    // Drift-type chips get coloured left border
    if (facetKey === "type") {
      btn.style.borderLeftColor = dtColor(val);
      btn.style.borderLeftWidth = "3px";
    }

    // Source chips get source-slug class for badge matching
    if (facetKey === "source") {
      const slug = SOURCE_SLUG[val] || val.toLowerCase();
      btn.classList.add("src-" + slug);
      btn.style.borderLeftWidth = "3px";
    }

    // Quality chips get a tier indicator class
    if (facetKey === "quality") {
      const qc = QUALITY_CLASS[val] || "";
      if (qc) btn.classList.add(qc);
    }

    btn.addEventListener("click", () => {
      const stateKey = facetKey === "lang"        ? "langs"
                     : facetKey === "type"        ? "types"
                     : facetKey === "connotation" ? "connotations"
                     : facetKey === "source"      ? "sources"
                     : facetKey === "quality"     ? "qualities"
                     : "evidences";
      const set = state[stateKey];
      if (set.has(val)) {
        set.delete(val);
        btn.classList.remove("active");
        btn.setAttribute("aria-pressed", "false");
      } else {
        set.add(val);
        btn.classList.add("active");
        btn.setAttribute("aria-pressed", "true");
      }
      applyFilters();
    });
    container.appendChild(btn);
  });
}

function clearAllFilters() {
  state.search     = "";
  state.langs      = new Set();
  state.types      = new Set();
  state.connotations = new Set();
  state.evidences  = new Set();
  state.sources    = new Set();
  state.qualities  = new Set();
  state.hasTrigger = false;
  state.yearFrom   = null;
  state.yearTo     = null;
  state.brushYearFrom = null;
  state.brushYearTo   = null;

  document.getElementById("facet-search").value = "";
  document.getElementById("year-from").value = "";
  document.getElementById("year-to").value = "";
  document.getElementById("facet-has-trigger").checked = false;

  document.querySelectorAll(".facet-chip.active").forEach(c => {
    c.classList.remove("active");
    c.setAttribute("aria-pressed", "false");
  });

  // Restore default quality filters: high + benchmark ON, detected OFF
  if (graphData) {
    const defaultOnQualities = (graphData.facets.quality || []).filter(q => q !== "detected");
    defaultOnQualities.forEach(q => {
      state.qualities.add(q);
      syncChip("facet-quality", q, true);
    });
  }

  applyFilters();
}

// ---------------------------------------------------------------------------
// Filter logic
// ---------------------------------------------------------------------------

function filteredWords() {
  if (!graphData) return [];
  const yFrom = effectiveYearFrom();
  const yTo   = effectiveYearTo();

  // Filters run against LIGHT words plus the shared driftEventsFlat index.
  // No heavy per-word detail (senses/driftEvents) is required here, so the
  // grid + overview work from graph-core alone (first paint).
  return graphData.words.filter(w => {
    // text search
    if (state.search && !w.writtenForm.toLowerCase().includes(state.search)) return false;
    // language
    if (state.langs.size > 0 && !state.langs.has(w.language || "?")) return false;

    // source filter: word must have at least one matching source
    if (state.sources.size > 0) {
      const wordSources = w.sources || [w.source];
      const match = wordSources.some(s => state.sources.has(s));
      if (!match) return false;
    }

    // quality filter: word's quality must be in the allowed set
    if (state.qualities.size > 0 && !state.qualities.has(w.quality)) return false;

    // Flat drift-event records for this word (carry type/year/conn/causes).
    const flat = flatFor(w);

    // drift type: use the light driftTypeLabels (one per word, distinct).
    if (state.types.size > 0) {
      const labels = (w.driftTypeLabels || []).map(t => t.toLowerCase());
      const match = [...state.types].some(t =>
        labels.some(l => l.includes(t.toLowerCase())));
      if (!match) return false;
    }

    // connotation filter: from or to connotation (from driftEventsFlat).
    if (state.connotations.size > 0) {
      const allConns = new Set();
      flat.forEach(fe => {
        if (fe.fromConn) allConns.add(fe.fromConn.toLowerCase());
        if (fe.toConn)   allConns.add(fe.toConn.toLowerCase());
      });
      const match = [...state.connotations].some(c => allConns.has(c.toLowerCase()));
      if (!match) return false;
    }

    // evidence type filter: word must have at least one cause whose evidence
    // tiers include any of the selected evidence labels.
    if (state.evidences.size > 0) {
      const allEvidence = new Set(
        flat.flatMap(fe =>
          (fe.causes || []).flatMap(c => (c.evidence || []).map(ev => ev.toLowerCase()))
        )
      );
      const match = [...state.evidences].some(ev => allEvidence.has(ev.toLowerCase()));
      if (!match) return false;
    }

    // year filter: word overlaps the range. Prefer per-event years from the
    // flat index; fall back to the light yearStart/yearEnd span.
    if (yFrom !== null || yTo !== null) {
      const eventYears = flat.map(fe => fe.year).filter(y => y != null);
      if (eventYears.length) {
        const hasYear = eventYears.some(y => {
          if (yFrom !== null && y < yFrom) return false;
          if (yTo   !== null && y > yTo)   return false;
          return true;
        });
        if (!hasYear) return false;
      } else if (w.yearStart != null || w.yearEnd != null) {
        const lo = w.yearStart ?? w.yearEnd;
        const hi = w.yearEnd ?? w.yearStart;
        if (yTo   !== null && lo > yTo)   return false;
        if (yFrom !== null && hi < yFrom) return false;
      }
    }

    // has trigger (light field)
    if (state.hasTrigger && !w.hasTrigger) return false;

    return true;
  });
}

function applyFilters() {
  renderWordGrid();
  renderFeaturedRow();
  updateActiveFilterChips();
  // Highlight matching dots in the overview timeline
  highlightTimelineDots();
  // Keep connector visibility in sync with current showLinks state
  if (overviewConnectorsSel) {
    overviewConnectorsSel.attr("display", showLinks ? null : "none");
  }
  persistFacets();
}

// ---------------------------------------------------------------------------
// Persistence: facets, last tab, last word (localStorage)
// ---------------------------------------------------------------------------

function persistFacets() {
  const snap = {
    search:      state.search,
    langs:       [...state.langs],
    types:       [...state.types],
    connotations:[...state.connotations],
    evidences:   [...state.evidences],
    sources:     [...state.sources],
    qualities:   [...state.qualities],
    hasTrigger:  state.hasTrigger,
    yearFrom:    state.yearFrom,
    yearTo:      state.yearTo,
  };
  lsSet(LS.facets, JSON.stringify(snap));
}

function restoreFacets() {
  const raw = lsGet(LS.facets);
  if (!raw) return;
  let snap;
  try { snap = JSON.parse(raw); } catch (e) { return; }
  if (!snap || typeof snap !== "object") return;

  state.search      = snap.search || "";
  state.langs       = new Set(snap.langs || []);
  state.types       = new Set(snap.types || []);
  state.connotations= new Set(snap.connotations || []);
  state.evidences   = new Set(snap.evidences || []);
  state.sources     = new Set(snap.sources || []);
  state.qualities   = new Set(snap.qualities || []);
  state.hasTrigger  = !!snap.hasTrigger;
  state.yearFrom    = snap.yearFrom ?? null;
  state.yearTo      = snap.yearTo ?? null;

  // Reflect into the DOM controls.
  const searchEl = document.getElementById("facet-search");
  if (searchEl) searchEl.value = state.search;
  const yf = document.getElementById("year-from");
  const yt = document.getElementById("year-to");
  if (yf) yf.value = state.yearFrom != null ? state.yearFrom : "";
  if (yt) yt.value = state.yearTo != null ? state.yearTo : "";
  const ht = document.getElementById("facet-has-trigger");
  if (ht) ht.checked = state.hasTrigger;

  // Sync all chip facets. First clear every active chip, then re-activate.
  document.querySelectorAll(".facet-chip.active").forEach(c => {
    c.classList.remove("active");
    c.setAttribute("aria-pressed", "false");
  });
  const syncSet = (id, set) => set.forEach(v => syncChip(id, v, true));
  syncSet("facet-lang", state.langs);
  syncSet("facet-type", state.types);
  syncSet("facet-connotation", state.connotations);
  syncSet("facet-evidence", state.evidences);
  syncSet("facet-source", state.sources);
  syncSet("facet-quality", state.qualities);
}

// Restore the last tab + last opened word (deep-link takes precedence).
function restoreSession() {
  const lastWordId = lsGet(LS.word);
  const lastTab = lsGet(LS.tab);
  if (lastWordId) {
    const w = (graphData.words || []).find(x => x.id === lastWordId);
    if (w) { openWordDetail(w); return; }
  }
  if (lastTab && lastTab !== "detail" && document.getElementById("panel-" + lastTab)) {
    switchTab(lastTab);
  }
}

// ---------------------------------------------------------------------------
// Active filter chips bar
// ---------------------------------------------------------------------------

function updateActiveFilterChips() {
  const bar = document.getElementById("active-filters-bar");
  const chips = [];

  if (state.search) chips.push({ label: 'search: "' + state.search + '"', clear: () => { state.search = ""; document.getElementById("facet-search").value = ""; } });
  state.langs.forEach(l => chips.push({ label: "lang: " + l.toUpperCase(), clear: () => { state.langs.delete(l); syncChip("facet-lang", l, false); } }));
  state.types.forEach(t => chips.push({ label: "type: " + t, clear: () => { state.types.delete(t); syncChip("facet-type", t, false); } }));
  state.connotations.forEach(c => chips.push({ label: "conn: " + c, clear: () => { state.connotations.delete(c); syncChip("facet-connotation", c, false); } }));
  state.evidences.forEach(e => chips.push({ label: "evidence: " + e, clear: () => { state.evidences.delete(e); syncChip("facet-evidence", e, false); } }));
  state.sources.forEach(s => chips.push({ label: "source: " + s, clear: () => { state.sources.delete(s); syncChip("facet-source", s, false); } }));
  state.qualities.forEach(q => chips.push({ label: "quality: " + q, clear: () => { state.qualities.delete(q); syncChip("facet-quality", q, false); } }));
  if (state.hasTrigger) chips.push({ label: "has trigger", clear: () => { state.hasTrigger = false; document.getElementById("facet-has-trigger").checked = false; } });
  if (state.brushYearFrom !== null || state.brushYearTo !== null) {
    chips.push({ label: "years: " + (state.brushYearFrom ?? "?") + "-" + (state.brushYearTo ?? "?"), clear: () => { state.brushYearFrom = null; state.brushYearTo = null; clearBrushSelection(); } });
  }

  bar.innerHTML = chips.map((c, i) =>
    '<span class="active-filter-chip">' + escHtml(c.label) +
    '<button aria-label="Remove filter ' + escHtml(c.label) + '" data-idx="' + i + '">&times;</button></span>'
  ).join("");

  bar.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => {
      chips[parseInt(btn.dataset.idx)].clear();
      applyFilters();
    });
  });
}

function syncChip(containerId, value, active) {
  const c = document.querySelector(`#${containerId} .facet-chip[data-value="${CSS.escape(value)}"]`);
  if (c) {
    c.classList.toggle("active", active);
    c.setAttribute("aria-pressed", active ? "true" : "false");
  }
}

function clearBrushSelection() {
  // Clear brush visually -- we'll just re-render the timeline
  renderOverviewTimeline();
}

function escHtml(str) {
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

// ---------------------------------------------------------------------------
// Deep linking (?word=<writtenForm>[&lang=] | ?trigger=<id-or-label>)
// ---------------------------------------------------------------------------

// Reflect the currently open detail into the URL so links are shareable.
function updateUrlParam(kind, value, lang) {
  const params = new URLSearchParams();
  if (kind === "word") {
    params.set("word", value);
    if (lang) params.set("lang", lang);
  } else if (kind === "trigger") {
    params.set("trigger", value);
  }
  const qs = params.toString();
  history.replaceState(null, "", qs ? "?" + qs : location.pathname);
}

// On load, open a word or trigger detail from URL params. Robust: a param that
// matches nothing is silently ignored.
// Returns true if a deep-link param was honoured (overriding session restore).
function applyDeepLink() {
  if (!graphData) return false;
  const params = new URLSearchParams(location.search);

  // #triggers hash jumps straight to the Triggers tab.
  if (location.hash === "#triggers" && !params.get("word") && !params.get("trigger")) {
    switchTab("triggers");
    return true;
  }

  const triggerParam = params.get("trigger");
  if (triggerParam) {
    const triggers = graphData.triggers || [];
    const t = triggers.find(x => x.id === triggerParam)
           || triggers.find(x => x.id === "https://w3id.org/word-drift/resource/" + triggerParam)
           || triggers.find(x => (x.label || "").toLowerCase() === triggerParam.toLowerCase());
    if (t && showTriggerById(t.id)) return true;
  }

  const wordParam = params.get("word");
  if (wordParam) {
    const langParam = (params.get("lang") || "").toLowerCase();
    const matches = (graphData.words || []).filter(w => w.writtenForm === wordParam);
    const w = (langParam ? matches.find(m => (m.language || "").toLowerCase() === langParam) : null) || matches[0];
    if (w) { openWordDetail(w); return true; }
    // case-insensitive fallback
    const ci = (graphData.words || []).find(x => x.writtenForm.toLowerCase() === wordParam.toLowerCase());
    if (ci) { openWordDetail(ci); return true; }
  }
  return false;
}

// ---------------------------------------------------------------------------
// Drift type legend
// ---------------------------------------------------------------------------

function buildDriftTypeLegend(types) {
  const legend = document.getElementById("dt-legend");
  legend.innerHTML = types.map(t =>
    `<div class="legend-item">
       <div class="legend-swatch circle" style="background:${dtColor(t)};"></div>
       ${escHtml(t)}
     </div>`
  ).join("") +
  `<div class="legend-item">
     <div class="legend-swatch circle" style="background:${TRIGGER_COLOR};"></div>
     Trigger event
   </div>` +
  `<div class="legend-item">
     <svg width="14" height="14" style="flex-shrink:0"><circle cx="7" cy="7" r="5" fill="${TRIGGER_COLOR}" opacity="0.85"/><circle cx="7" cy="7" r="5" fill="none" stroke="${TRIGGER_COLOR}" stroke-width="2"/></svg>
     Has identified cause (ring)
   </div>` +
  `<div class="legend-item">
     <svg width="14" height="14" style="flex-shrink:0"><circle cx="7" cy="7" r="5" fill="none" stroke="${CAUSE_GRADUAL_COLOR}" stroke-width="1.5"/></svg>
     Gradual shift / no single cause
   </div>`;
}

function buildCauseLegend() {
  const legend = document.getElementById("dt-legend");
  // Build items from CAUSE_COLOR_MAP (top triggers) + gradual
  const items = Object.entries(CAUSE_COLOR_MAP).map(([label, color]) =>
    `<div class="legend-item">
       <div class="legend-swatch circle" style="background:${color};"></div>
       ${escHtml(label.length > 32 ? label.slice(0, 32) + "..." : label)}
     </div>`
  ).join("") +
  `<div class="legend-item">
     <div class="legend-swatch circle" style="background:${CAUSE_GRADUAL_COLOR};opacity:0.45;"></div>
     Gradual / no identified cause
   </div>` +
  `<div class="legend-item">
     <div class="legend-swatch" style="width:24px;height:2px;background:${TRIGGER_COLOR};opacity:0.5;border-radius:1px;margin-top:5px;"></div>
     Cause connector line
   </div>`;
  legend.innerHTML = items;
}

// ---------------------------------------------------------------------------
// OVERVIEW TIMELINE (stacked histogram + beeswarm)
// ---------------------------------------------------------------------------

let overviewTlSvg = null;
let overviewBrushG = null;
let overviewXScale = null;
let overviewDotsSel = null;
let overviewConnectorsSel = null;

function renderOverviewTimeline() {
  if (!graphData) return;
  const wrap = document.getElementById("overview-tl-wrap");
  wrap.innerHTML = "";

  const flat = graphData.driftEventsFlat || [];
  const byDecade = graphData.byDecadeType || [];
  const triggerImpact = graphData.triggerImpact || [];

  if (flat.length === 0 && byDecade.length === 0) {
    wrap.innerHTML = '<p class="empty-msg">No drift event data available.</p>';
    return;
  }

  const allYears = flat.map(e => e.year).filter(y => y != null);
  if (allYears.length === 0) {
    wrap.innerHTML = '<p class="empty-msg">No year data available.</p>';
    return;
  }

  // Include trigger years in the domain so markers are visible
  const trigYears = triggerImpact.map(t => t.year).filter(y => y != null);
  const allDomainYears = [...allYears, ...trigYears];

  const MIN_YEAR = Math.min(...allDomainYears) - 40;
  const MAX_YEAR = Math.max(...allDomainYears) + 60;

  const containerW = wrap.clientWidth || 900;
  const W = Math.max(containerW, 600);

  const MARGIN = { top: 12, right: 28, bottom: 52, left: 36 };
  const HIST_H = 60;
  const HIST_INNER_H = HIST_H - 12;
  const BRUSH_H = 24;
  const BEESWARM_H = 110;    // slightly taller to make room for rings
  const TRIGGER_STRIP_H = 28; // trigger markers between beeswarm and axis
  const SEPARATOR = 8;
  const TOTAL_H = MARGIN.top + HIST_H + SEPARATOR + BEESWARM_H + TRIGGER_STRIP_H + BRUSH_H + MARGIN.bottom;

  const xFull = d3.scaleLinear()
    .domain([MIN_YEAR, MAX_YEAR])
    .range([MARGIN.left, W - MARGIN.right]);

  // Build decade histogram data
  const allTypes = [...new Set(byDecade.map(d => d.type))];
  const decades  = [...new Set(byDecade.map(d => d.decade))].sort((a, b) => a - b);

  // Stack by decade
  const decadeMap = {};
  byDecade.forEach(d => {
    if (!decadeMap[d.decade]) decadeMap[d.decade] = {};
    decadeMap[d.decade][d.type] = (decadeMap[d.decade][d.type] || 0) + d.n;
  });

  const stackData = decades.map(dec => {
    const obj = { decade: dec };
    allTypes.forEach(t => { obj[t] = decadeMap[dec][t] || 0; });
    return obj;
  });

  const stackGen = d3.stack().keys(allTypes);
  const stacked = stackGen(stackData);

  const maxCount = d3.max(stacked, layer => d3.max(layer, d => d[1])) || 1;

  const yHist = d3.scaleLinear().domain([0, maxCount]).range([HIST_INNER_H, 0]);

  const decadeW = decades.length > 1
    ? Math.abs(xFull(decades[1]) - xFull(decades[0])) - 1
    : 20;

  const svg = d3.select(wrap).append("svg")
    .attr("viewBox", "0 0 " + W + " " + TOTAL_H)
    .attr("width", W).attr("height", TOTAL_H)
    .style("display", "block");

  overviewTlSvg = svg;
  svg.append("rect").attr("width", W).attr("height", TOTAL_H).attr("fill", BG_COLOR);

  // Zoomable layer: holds every year-positioned element (histogram, dots,
  // trigger strip, connectors, main axis). The brush mini-axis at the bottom
  // stays OUTSIDE this layer so it always shows the full domain.
  const clipId = "ov-clip";
  svg.append("clipPath").attr("id", clipId)
    .append("rect")
    .attr("x", MARGIN.left).attr("y", 0)
    .attr("width", Math.max(0, W - MARGIN.left - MARGIN.right) + 2)
    .attr("height", TOTAL_H);
  const zoomG = svg.append("g").attr("class", "ov-zoom-layer").attr("clip-path", "url(#" + clipId + ")");

  const histG = zoomG.append("g")
    .attr("transform", "translate(0," + MARGIN.top + ")");

  // Draw stacked bars
  stacked.forEach((layer, li) => {
    const typeName = allTypes[li];
    const color = dtColor(typeName);
    histG.selectAll(".hbar-" + li)
      .data(layer)
      .join("rect")
      .attr("class", "hbar-" + li)
      .attr("x", d => xFull(d.data.decade) - decadeW / 2)
      .attr("y", d => yHist(d[1]) + 2)
      .attr("width", decadeW)
      .attr("height", d => Math.max(0, yHist(d[0]) - yHist(d[1])))
      .attr("fill", color)
      .attr("opacity", 0.72);
  });

  // Hist y-axis ticks
  histG.selectAll(".hist-ytick").data(yHist.ticks(4)).join("text")
    .attr("class", "hist-ytick")
    .attr("x", MARGIN.left - 4)
    .attr("y", d => yHist(d) + 2)
    .attr("text-anchor", "end")
    .attr("fill", FAINT_TEXT).attr("font-size", 9).attr("font-family", "Inter,sans-serif")
    .text(d => d);

  // --- Beeswarm dots ---
  const beeY0 = MARGIN.top + HIST_H + SEPARATOR;

  // Beeswarm layout: jitter y to avoid overlap
  const beeRadius = 5;
  const beeNodes = flat
    .filter(e => e.year != null)
    .map(e => ({ ...e, beeX: xFull(e.year) }));

  // Simple column-based beeswarm: group by pixel column, stack vertically
  const cols = {};
  beeNodes.forEach(n => {
    const col = Math.round(n.beeX / (beeRadius * 2));
    if (!cols[col]) cols[col] = [];
    cols[col].push(n);
  });

  const midY = beeY0 + BEESWARM_H / 2;
  Object.values(cols).forEach(group => {
    group.forEach((n, i) => {
      const total = group.length;
      const offset = (i - (total - 1) / 2) * (beeRadius * 2 + 1);
      n.beeY = Math.max(beeY0 + beeRadius + 2, Math.min(beeY0 + BEESWARM_H - beeRadius - 2, midY + offset));
    });
  });

  // --- Trigger strip (below beeswarm, above axis) ---
  const trigStripY = beeY0 + BEESWARM_H;

  // Build a map: triggerLabel -> x position (use first hypothesis's year)
  // We use triggerImpact for the markers
  const maxWC = d3.max(triggerImpact, t => t.wordCount) || 1;
  const trigRScale = d3.scaleSqrt().domain([0, maxWC]).range([3, 8]);

  const trigG = zoomG.append("g");

  // Draw vertical tick lines at trigger positions
  const trigWithYear = triggerImpact.filter(t => t.year != null);
  trigWithYear.forEach(t => {
    const tx = xFull(t.year);
    // Subtle vertical line through beeswarm
    trigG.append("line")
      .attr("x1", tx).attr("x2", tx)
      .attr("y1", beeY0).attr("y2", trigStripY)
      .attr("stroke", CAUSE_COLOR_MAP[t.label] || TRIGGER_COLOR)
      .attr("stroke-width", 1)
      .attr("stroke-dasharray", "3 3")
      .attr("opacity", 0.22);

    // Diamond marker in strip
    const ds = trigRScale(t.wordCount) + 1;
    const cy = trigStripY + TRIGGER_STRIP_H / 2;
    trigG.append("polygon")
      .attr("points",
        tx + "," + (cy - ds) + " " +
        (tx + ds) + "," + cy + " " +
        tx + "," + (cy + ds) + " " +
        (tx - ds) + "," + cy)
      .attr("fill", CAUSE_COLOR_MAP[t.label] || TRIGGER_COLOR)
      .attr("opacity", 0.72)
      .attr("stroke", BG_COLOR)
      .attr("stroke-width", 0.5)
      .style("cursor", "pointer")
      .on("mouseenter", (event) => {
        showTip(
          "<strong>" + escHtml(t.label) + "</strong>" +
          "<p>" + escHtml(t.category || "trigger") + ", " + (t.year || "?") + "</p>" +
          (t.wordCount > 0
            ? '<p class="tt-sub">Reframed ' + t.wordCount + ' word' + (t.wordCount !== 1 ? "s" : "") + ": " + escHtml((t.words || []).slice(0, 6).join(", ")) + (t.words.length > 6 ? " ..." : "") + "</p>"
            : ""),
          event
        );
      })
      .on("mouseleave", hideTip);
  });

  // Build a lookup: triggerLabel -> x pixel (for connector lines)
  const trigXByLabel = {};
  trigWithYear.forEach(t => { trigXByLabel[t.label] = xFull(t.year); });

  // --- Connector lines (dots -> trigger markers) ---
  // Drawn in a separate group, hidden by default
  const connG = zoomG.append("g").attr("class", "cause-connectors");

  const connData = beeNodes.filter(n => (n.causes || []).length > 0).flatMap(n =>
    n.causes.filter(c => c.triggerLabel && trigXByLabel[c.triggerLabel] !== undefined).map(c => ({
      x1: n.beeX,
      y1: n.beeY,
      x2: trigXByLabel[c.triggerLabel],
      y2: trigStripY + TRIGGER_STRIP_H / 2,
      color: CAUSE_COLOR_MAP[c.triggerLabel] || TRIGGER_COLOR,
      confidence: c.confidence || 0.5,
    }))
  );

  const connLines = connG.selectAll("line").data(connData).join("line")
    .attr("x1", d => d.x1).attr("y1", d => d.y1)
    .attr("x2", d => d.x2).attr("y2", d => d.y2)
    .attr("stroke", d => d.color)
    .attr("stroke-width", 1)
    .attr("opacity", d => Math.max(0.1, d.confidence * 0.35))
    .attr("stroke-dasharray", "2 3")
    .attr("display", showLinks ? null : "none");

  overviewConnectorsSel = connLines;

  // --- Dot layer ---
  const dotG = zoomG.append("g").attr("class", "beeswarm-dots");

  // Outer rings for "has cause" dots (drawn first, behind fills)
  dotG.selectAll(".bee-ring")
    .data(beeNodes.filter(n => (n.causes || []).length > 0))
    .join("circle")
    .attr("class", "bee-ring")
    .attr("cx", n => n.beeX)
    .attr("cy", n => n.beeY)
    .attr("r", beeRadius + 2.5)
    .attr("fill", "none")
    .attr("stroke", n => causeColor(n))
    .attr("stroke-width", 1.5)
    .attr("opacity", 0.55)
    .style("pointer-events", "none");

  const dots = dotG.selectAll("circle:not(.bee-ring)")
    .data(beeNodes)
    .join("circle")
    .attr("cx", n => n.beeX)
    .attr("cy", n => n.beeY)
    .attr("r", beeRadius)
    .attr("fill", n => currentLens === "cause" ? causeColor(n) : dtColor(n.type))
    .attr("opacity", n => (n.causes || []).length > 0 ? 0.85 : 0.55)
    .attr("stroke", BG_COLOR).attr("stroke-width", 0.5)
    .style("cursor", "pointer")
    .on("mouseenter", (event, n) => {
      const fromTo = n.fromConn && n.toConn
        ? '<br><small>' + escHtml(n.fromConn) + ' &rarr; ' + escHtml(n.toConn) + '</small>'
        : "";
      let causeHtml = "";
      if ((n.causes || []).length > 0) {
        const top = n.causes[0];
        const evStr = (top.evidence || []).join(", ");
        const conf = top.confidence != null ? " (" + top.confidence.toFixed(1) + ")" : "";
        causeHtml =
          '<p class="tt-sub" style="color:' + (CAUSE_COLOR_MAP[top.triggerLabel] || TRIGGER_COLOR) + ';">' +
          "Cause: " + escHtml(top.triggerLabel || "?") + conf +
          (evStr ? "<br>" + escHtml(evStr) : "") +
          (n.causes.length > 1 ? " + " + (n.causes.length - 1) + " alt." : "") +
          "</p>";
      } else {
        causeHtml = '<p class="tt-sub">Gradual shift, no single cause</p>';
      }
      showTip(
        "<strong>" + escHtml(n.word) + " (" + n.lang + ")</strong>" +
        "<p>" + escHtml(n.type) + ", " + n.year + fromTo + "</p>" +
        causeHtml,
        event
      );
      d3.select(event.currentTarget).attr("r", beeRadius + 2).attr("opacity", 1);
      // Highlight connector lines for this dot on hover
      connG.selectAll("line")
        .attr("opacity", d => (d.x1 === n.beeX && d.y1 === n.beeY)
          ? Math.max(0.4, (d.confidence || 0.5) * 0.8)
          : (showLinks ? Math.max(0.1, (d.confidence || 0.5) * 0.35) : 0));
    })
    .on("mouseleave", (event, n) => {
      hideTip();
      d3.select(event.currentTarget).attr("r", beeRadius).attr("opacity", (n.causes || []).length > 0 ? 0.85 : 0.55);
      // Restore connector opacity
      connG.selectAll("line")
        .attr("opacity", d => showLinks ? Math.max(0.1, (d.confidence || 0.5) * 0.35) : 0);
    })
    .on("click", (event, n) => {
      const wordObj = graphData.words.find(w => w.writtenForm === n.word && w.language === n.lang);
      if (wordObj) openWordDetail(wordObj);
    });

  overviewDotsSel = dots;

  // X axis (below trigger strip). Lives OUTSIDE the zoom layer so its tick
  // labels are redrawn (not stretched) when the user zooms/pans.
  const axisY = trigStripY + TRIGGER_STRIP_H + 2;
  const axisSvg = svg.append("g")
    .attr("transform", "translate(0," + axisY + ")");

  const tickCount = Math.min(14, Math.max(5, Math.floor((MAX_YEAR - MIN_YEAR) / 100)));
  // Redraw the axis ticks for a given (possibly rescaled) x scale.
  function drawOverviewAxis(scale) {
    axisSvg.selectAll("*").remove();
    scale.ticks(tickCount).forEach(yr => {
      axisSvg.append("line")
        .attr("x1", scale(yr)).attr("x2", scale(yr))
        .attr("y1", 0).attr("y2", 5)
        .attr("stroke", GRID_LINE);
      axisSvg.append("text")
        .attr("x", scale(yr)).attr("y", 17)
        .attr("text-anchor", "middle")
        .attr("fill", AXIS_TEXT)
        .attr("font-size", 10).attr("font-family", "Inter,sans-serif")
        .text(yr);
    });
    axisSvg.append("line")
      .attr("x1", MARGIN.left).attr("x2", W - MARGIN.right)
      .attr("y1", 0).attr("y2", 0)
      .attr("stroke", GRID_LINE);
  }
  drawOverviewAxis(xFull);

  // --- Brush mini-axis ---
  const brushY = axisY + 22;
  overviewXScale = xFull;

  const brush = d3.brushX()
    .extent([[MARGIN.left, brushY], [W - MARGIN.right, brushY + BRUSH_H]])
    .on("end", (event) => {
      if (!event.selection) {
        state.brushYearFrom = null;
        state.brushYearTo   = null;
      } else {
        const [x0, x1] = event.selection;
        state.brushYearFrom = Math.round(xFull.invert(x0));
        state.brushYearTo   = Math.round(xFull.invert(x1));
      }
      applyFilters();
    });

  overviewBrushG = svg.append("g").attr("class", "overview-brush").call(brush);

  // Style the brush
  overviewBrushG.select(".selection")
    .attr("fill", "rgba(91,124,248,0.18)")
    .attr("stroke", ACCENT_COLOR).attr("stroke-width", 1);

  // Mini timeline under the brush area showing dense markers
  const miniDotG = svg.append("g");
  beeNodes.filter(n => n.year != null).forEach(n => {
    miniDotG.append("rect")
      .attr("x", xFull(n.year) - 0.5)
      .attr("y", brushY + 2)
      .attr("width", 1).attr("height", BRUSH_H - 4)
      .attr("fill", currentLens === "cause" ? causeColor(n) : dtColor(n.type))
      .attr("opacity", 0.35);
  });

  // Bring brush on top
  overviewBrushG.raise();

  // "Brush hint" label
  svg.append("text")
    .attr("x", W - MARGIN.right)
    .attr("y", brushY + BRUSH_H / 2 + 4)
    .attr("text-anchor", "end")
    .attr("fill", FAINT_TEXT).attr("font-size", 9).attr("font-family", "Inter,sans-serif")
    .text("scroll to zoom · drag bar to filter");

  // --- Zoom / pan (horizontal only), clamped to the data domain ----------
  // Pans + wheel-zooms the content layer; the axis is redrawn from a rescaled
  // x scale. The "Reset zoom" control returns to the full view. The brush is
  // independent (it filters by year), so we only translateExtent the x axis.
  const zoomW = W - MARGIN.left - MARGIN.right;
  const overviewZoom = d3.zoom()
    .scaleExtent([1, 24])
    .translateExtent([[MARGIN.left, 0], [W - MARGIN.right, TOTAL_H]])
    .extent([[MARGIN.left, 0], [W - MARGIN.right, TOTAL_H]])
    .filter(event => {
      // Allow wheel + drag-pan, but never hijack the brush region.
      if (event.type === "wheel") return true;
      const y = event.offsetY != null ? event.offsetY : 0;
      return y < brushY;   // pan only above the brush strip
    })
    .on("zoom", (event) => {
      const t = event.transform;
      // Horizontal-only transform on the content layer.
      zoomG.attr("transform", "translate(" + t.x + ",0) scale(" + t.k + ",1)");
      // Counter-scale stroke widths would be ideal, but dots are circles drawn
      // with cx/cy; horizontal scaling stretches them. To keep dots round we
      // instead redraw positions via a rescaled x. Cheap approach: rescale the
      // axis from the transform; dots stretch slightly which is acceptable at
      // these zoom levels and keeps interaction snappy.
      drawOverviewAxis(t.rescaleX(xFull));
      const resetBtn = document.getElementById("ov-zoom-reset");
      if (resetBtn) resetBtn.hidden = t.k === 1 && t.x === 0;
    });

  svg.call(overviewZoom).on("dblclick.zoom", null);

  // Reset-zoom control (HTML button overlaid on the timeline section).
  let resetBtn = document.getElementById("ov-zoom-reset");
  if (!resetBtn) {
    resetBtn = document.createElement("button");
    resetBtn.id = "ov-zoom-reset";
    resetBtn.className = "ov-zoom-reset";
    resetBtn.type = "button";
    resetBtn.textContent = "Reset zoom";
    wrap.appendChild(resetBtn);
  }
  resetBtn.hidden = true;
  resetBtn.onclick = () => {
    svg.transition().duration(PREFERS_REDUCED_MOTION ? 0 : 250)
      .call(overviewZoom.transform, d3.zoomIdentity);
  };
}

// Highlight matching dots on the overview timeline when filters change
function highlightTimelineDots() {
  if (!overviewDotsSel) return;
  const fw = new Set(filteredWords().map(w => w.writtenForm + "|" + w.language));

  overviewDotsSel
    .attr("fill", n => currentLens === "cause" ? causeColor(n) : dtColor(n.type))
    .attr("opacity", n => {
      const active = fw.has(n.word + "|" + n.lang);
      if (!active) return 0.15;
      if (currentLens === "cause" && (n.causes || []).length === 0) return 0.45;
      return 0.85;
    })
    .attr("r", n => fw.has(n.word + "|" + n.lang) ? 5 : 4);

  // Update ring opacity for cause lens
  if (overviewTlSvg) {
    overviewTlSvg.selectAll(".bee-ring")
      .attr("opacity", n => fw.has(n.word + "|" + n.lang) ? 0.55 : 0.1);
  }
}

// ---------------------------------------------------------------------------
// Word grid
// ---------------------------------------------------------------------------

function renderWordGrid() {
  if (!graphData) return;
  const grid = document.getElementById("word-grid");
  const info = document.getElementById("grid-info");

  const words = filteredWords();
  const total = words.length;
  const capped = words.slice(0, GRID_CAP);

  if (total === 0) {
    info.textContent = "No words match the current filters.";
    grid.innerHTML = "";
    return;
  }

  info.innerHTML = total > GRID_CAP
    ? "Showing <strong>" + GRID_CAP + "</strong> of <strong>" + total + "</strong> words."
    : "<strong>" + total + "</strong> word" + (total !== 1 ? "s" : "") + ".";

  const fragment = document.createDocumentFragment();
  capped.forEach(w => {
    const card = buildWordCard(w);
    fragment.appendChild(card);
  });

  grid.innerHTML = "";
  grid.appendChild(fragment);
}

function buildWordCard(word) {
  const el = document.createElement("div");
  el.className = "word-card";
  el.setAttribute("role", "listitem");
  el.setAttribute("tabindex", "0");
  el.setAttribute("aria-label", word.writtenForm + " (" + (word.language || "?") + ")");

  // Flat drift-event records for this word (from graph-core; no heavy detail).
  const flatEntries = flatFor(word);

  // Collect drift types for this word (light field, fall back to flat types).
  const types = (word.driftTypeLabels && word.driftTypeLabels.length)
    ? [...new Set(word.driftTypeLabels.flatMap(t => t.split(",").map(s => s.trim())))]
    : [...new Set(flatEntries.map(fe => fe.type).filter(Boolean))];

  // Collect distinct connotations from the flat from/to connotations.
  const connSet = new Set();
  flatEntries.forEach(fe => {
    if (fe.fromConn) connSet.add(fe.fromConn);
    if (fe.toConn)   connSet.add(fe.toConn);
  });
  const uniqConns = [...connSet];
  // Pick the strongest (highest-confidence) cause across all drift events
  let topCause = null;
  flatEntries.forEach(fe => {
    (fe.causes || []).forEach(c => {
      if (!topCause || (c.confidence || 0) > (topCause.confidence || 0)) {
        topCause = c;
      }
    });
  });

  // Build cause line HTML
  let causeLineHtml = "";
  if (topCause) {
    const causeColor = CAUSE_COLOR_MAP[topCause.triggerLabel] || TRIGGER_COLOR;
    const evLabel = (topCause.evidence || []).length > 0
      ? '<span class="cause-ev-chip">' + escHtml(topCause.evidence[0].replace(" (temporal coincidence)", "").replace("speculative ", "speculative")) + '</span>'
      : "";
    const confStr = topCause.confidence != null ? " (" + topCause.confidence.toFixed(1) + ")" : "";
    causeLineHtml =
      '<div class="word-card-cause has-cause" style="color:' + causeColor + ';">' +
        '<span class="cause-glyph">&#8627;</span>' +
        '<span class="cause-text">' +
          escHtml(topCause.triggerLabel || "?") + confStr + evLabel +
        '</span>' +
      '</div>';
  } else if (flatEntries.length > 0) {
    // Word has drift events but no identified cause
    causeLineHtml =
      '<div class="word-card-cause gradual">' +
        '<span class="cause-glyph">&#8767;</span>' +
        '<span class="cause-text">gradual shift, no single cause</span>' +
      '</div>';
  }

  // Build source badges
  const wordSources = word.sources || [word.source];
  const sourceBadgesHtml = wordSources.length
    ? '<div class="word-card-sources">' +
        wordSources.map(s => {
          const slug = SOURCE_SLUG[s] || s.toLowerCase();
          const qClass = word.quality === "detected" ? " quality-detected" : "";
          return '<span class="source-badge src-' + slug + qClass + '">' + escHtml(s) + '</span>';
        }).join("") +
      '</div>'
    : "";

  el.innerHTML =
    '<div class="word-card-top">' +
      '<span class="word-card-form">' + escHtml(word.writtenForm) + '</span>' +
      '<span class="word-card-lang">' + escHtml(word.language || "?") + '</span>' +
    '</div>' +
    sourceBadgesHtml +
    (types.length ? '<div class="word-card-type-chips">' +
      types.map(t =>
        '<span class="type-chip" style="background:' + dtColor(t) + '22;color:' + dtColor(t) + ';">' +
        escHtml(t) + '</span>'
      ).join("") +
    '</div>' : "") +
    (uniqConns.length ? '<div class="word-card-connotation">' +
      uniqConns.map(c =>
        '<span class="conn-dot" style="background:' + connColor(c) + ';"></span>'
      ).join("") +
      escHtml(uniqConns.join(" + ")) +
    '</div>' : "") +
    causeLineHtml;

  el.addEventListener("click", () => openWordDetail(word));
  el.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openWordDetail(word); } });
  return el;
}

// ---------------------------------------------------------------------------
// TRIGGERS PANEL
// ---------------------------------------------------------------------------

let triggerTlRendered = false;

function renderTriggerTimeline() {
  if (!graphData || triggerTlRendered) return;
  triggerTlRendered = true;

  const wrap = document.getElementById("trigger-tl-wrap");
  wrap.innerHTML = "";

  const impact = graphData.triggerImpact || [];
  const triggers = graphData.triggers || [];

  if (triggers.length === 0) {
    wrap.innerHTML = '<p class="empty-msg">No trigger data available.</p>';
    return;
  }

  const allYears = triggers.map(t => t.date).filter(y => y != null);
  if (allYears.length === 0) {
    wrap.innerHTML = '<p class="empty-msg">No trigger year data.</p>';
    return;
  }

  const MIN_YEAR = Math.min(...allYears) - 40;
  const MAX_YEAR = Math.max(...allYears) + 60;

  const containerW = wrap.clientWidth || 900;
  const W = Math.max(containerW, 600);
  const H = 220;
  const MARGIN = { top: 20, right: 30, bottom: 44, left: 24 };
  const INNER_H = H - MARGIN.top - MARGIN.bottom;

  const x = d3.scaleLinear().domain([MIN_YEAR, MAX_YEAR]).range([MARGIN.left, W - MARGIN.right]);

  // Build impact map: trigger_id -> wordCount
  const impactMap = {};
  impact.forEach(ti => { impactMap[ti.trigger] = ti; });

  const maxCount = d3.max(impact, ti => ti.wordCount) || 1;
  const rScale = d3.scaleSqrt().domain([0, maxCount]).range([6, 28]);

  const svg = d3.select(wrap).append("svg")
    .attr("viewBox", "0 0 " + W + " " + H)
    .attr("width", W).attr("height", H)
    .style("display", "block");

  svg.append("rect").attr("width", W).attr("height", H).attr("fill", BG_COLOR);

  const g = svg.append("g").attr("transform", "translate(0," + MARGIN.top + ")");

  // Center line
  const midY = INNER_H / 2;
  g.append("line")
    .attr("x1", MARGIN.left).attr("x2", W - MARGIN.right)
    .attr("y1", midY).attr("y2", midY)
    .attr("stroke", GRID_LINE);

  // Draw trigger circles
  const trigData = triggers.filter(t => t.date != null);
  const nodes = trigData.map(t => {
    const ti = impactMap[t.id] || {};
    const r = rScale(ti.wordCount || 0);
    return { ...t, r, wordCount: ti.wordCount || 0, words: ti.words || [] };
  });

  // Simple collision-avoid on Y by column
  const trigCols = {};
  nodes.forEach(n => {
    const col = Math.round(x(n.date) / (n.r * 2.5 + 2));
    if (!trigCols[col]) trigCols[col] = [];
    trigCols[col].push(n);
  });
  Object.values(trigCols).forEach(group => {
    group.forEach((n, i) => {
      const total = group.length;
      const offset = (i - (total - 1) / 2) * (n.r * 2 + 4);
      n.cy = Math.max(n.r + 2, Math.min(INNER_H - n.r - 2, midY + offset));
    });
  });

  // Category colour
  const catSet = [...new Set(nodes.map(n => n.category).filter(Boolean))];
  const catColor = d3.scaleOrdinal(d3.schemeTableau10).domain(catSet);

  g.selectAll(".trig-circle").data(nodes).join("circle")
    .attr("class", "trig-circle")
    .attr("cx", n => x(n.date))
    .attr("cy", n => n.cy)
    .attr("r", n => n.r)
    .attr("fill", n => catColor(n.category || "unknown"))
    .attr("opacity", 0.7)
    .attr("stroke", BG_COLOR).attr("stroke-width", 1)
    .style("cursor", "pointer")
    .on("mouseenter", (event, n) => {
      showTip(
        "<strong>" + escHtml(n.label) + "</strong>" +
        "<p>" + escHtml(n.category || "trigger") + ", " + (n.date || "?") + "</p>" +
        (n.wordCount > 0 ? '<p class="tt-sub">Reframed ' + n.wordCount + ' word' + (n.wordCount !== 1 ? "s" : "") + "</p>" : ""),
        event
      );
    })
    .on("mouseleave", () => hideTip())
    .on("click", (event, n) => {
      renderTriggerDetail(n, catColor);
    });

  // Labels for larger circles
  g.selectAll(".trig-label").data(nodes.filter(n => n.r >= 14)).join("text")
    .attr("class", "trig-label")
    .attr("x", n => x(n.date))
    .attr("y", n => n.cy - n.r - 4)
    .attr("text-anchor", "middle")
    .attr("fill", AXIS_TEXT)
    .attr("font-size", 9)
    .attr("font-family", "Inter,sans-serif")
    .text(n => n.label.length > 22 ? n.label.slice(0, 22) + "..." : n.label);

  // X axis
  const axisG = g.append("g").attr("transform", "translate(0," + (INNER_H + 4) + ")");
  axisG.append("line")
    .attr("x1", MARGIN.left).attr("x2", W - MARGIN.right)
    .attr("y1", 0).attr("y2", 0)
    .attr("stroke", GRID_LINE);
  const tickCnt = Math.min(12, Math.max(5, Math.floor((MAX_YEAR - MIN_YEAR) / 80)));
  x.ticks(tickCnt).forEach(yr => {
    axisG.append("line")
      .attr("x1", x(yr)).attr("x2", x(yr)).attr("y1", 0).attr("y2", 5)
      .attr("stroke", GRID_LINE);
    axisG.append("text")
      .attr("x", x(yr)).attr("y", 16).attr("text-anchor", "middle")
      .attr("fill", AXIS_TEXT).attr("font-size", 10).attr("font-family", "Inter,sans-serif")
      .text(yr);
  });
}

// Human-readable language label (shared with facet labels).
function langLabel(code) {
  const m = { en: "English", de: "German" };
  return m[code] || code || "?";
}

// Collect the per-word hypotheses this trigger supports, joining the trigger's
// reframed-word list against driftEventsFlat causes by triggerLabel + word.
// Returns one row per affected (word, lang) carrying drift type, confidence,
// evidence tiers and the resolved word object (for openWordDetail).
function hypothesesForTrigger(trigNode) {
  const rows = [];
  const seen = new Set();
  const wantWords = new Set(trigNode.words || []);
  (graphData.driftEventsFlat || []).forEach(fe => {
    if (!wantWords.has(fe.word)) return;
    (fe.causes || []).forEach(c => {
      if (c.triggerLabel !== trigNode.label) return;
      const key = fe.word + "|" + fe.lang;
      if (seen.has(key)) return;
      seen.add(key);
      const wordObj = (graphData.words || []).find(
        w => w.writtenForm === fe.word && (w.language || "?") === fe.lang
      ) || null;
      rows.push({
        word: fe.word,
        lang: fe.lang,
        driftType: fe.type || "drift",
        confidence: c.confidence != null ? c.confidence : null,
        evidence: c.evidence || [],
        wordObj,
      });
    });
  });
  rows.sort((a, b) => (b.confidence ?? -1) - (a.confidence ?? -1));
  return rows;
}

// Normalise wikidataSameAs (full URI or bare QID) to a wiki URL + QID, or null.
function wikidataLink(raw) {
  if (!raw) return null;
  const s = String(raw).trim();
  const m = s.match(/(Q\d+)\s*$/);
  if (!m) return null;
  const qid = m[1];
  return { qid, url: "https://www.wikidata.org/wiki/" + qid };
}

// --- Encyclopedia (Wikipedia via Wikidata) -------------------------------
// In-session cache by QID; persisted to localStorage for ~7 days. Never throws.
const WIKI_INFO_CACHE = new Map();
const WIKI_INFO_TTL_MS = 7 * 24 * 60 * 60 * 1000;

// Extract a bare "Qxxx" from a full entity URI, /wiki/ URL, or bare QID.
function wikiQid(raw) {
  if (!raw) return null;
  const m = String(raw).trim().match(/(Q\d+)/);
  return m ? m[1] : null;
}

// Scheme/host validation for external URLs returned by the Wikidata/Wikipedia
// APIs. The API responses are attacker-influenceable in principle, so any value
// inserted into the DOM as an href/src must be confirmed to be an https URL on
// the expected host before use. Escaping neutralises quote breakout but NOT a
// javascript:/data: scheme, so this is the real defence (F5).
function safeWikimediaThumb(u) {
  return (typeof u === "string" && /^https:\/\/[a-z0-9.-]*\.wikimedia\.org\//i.test(u)) ? u : null;
}
function safeWikipediaUrl(u) {
  return (typeof u === "string" && /^https:\/\/[a-z0-9.-]*\.wikipedia\.org\//i.test(u)) ? u : null;
}

// Resolve a Wikidata QID to a Wikipedia article summary. Returns a Promise of
// { title, extract, description, thumbnail, url, lang, wikidataUrl } or null.
// langPref is "de" or "en"; we prefer it, then English, German, then any.
function wikiInfo(qidRaw, langPref) {
  const qid = wikiQid(qidRaw);
  if (!qid) return Promise.resolve(null);
  const pref = langPref === "de" ? "de" : "en";
  const cacheKey = qid + "|" + pref;

  // 1. In-session cache.
  if (WIKI_INFO_CACHE.has(cacheKey)) {
    return Promise.resolve(WIKI_INFO_CACHE.get(cacheKey));
  }

  // 2. localStorage cache (fresh within TTL).
  const lsKey = "wd.wiki." + cacheKey;
  try {
    const raw = localStorage.getItem(lsKey);
    if (raw) {
      const rec = JSON.parse(raw);
      if (rec && typeof rec.ts === "number" && (Date.now() - rec.ts) < WIKI_INFO_TTL_MS) {
        WIKI_INFO_CACHE.set(cacheKey, rec.data);
        return Promise.resolve(rec.data);
      }
    }
  } catch (e) { /* corrupt / unavailable storage: ignore, refetch */ }

  const wikidataUrl = "https://www.wikidata.org/wiki/" + qid;

  // 3. Live fetch: Wikidata sitelinks -> Wikipedia REST summary.
  const entApi = "https://www.wikidata.org/w/api.php?action=wbgetentities&ids=" +
    encodeURIComponent(qid) + "&props=sitelinks%7Cdescriptions&format=json&origin=*";

  const result = fetch(entApi)
    .then(r => (r && r.ok ? r.json() : null))
    .then(j => {
      if (!j || !j.entities || !j.entities[qid]) return null;
      const ent = j.entities[qid];
      const sitelinks = ent.sitelinks || {};
      // Prefer langPref, then English, German, then any *wiki sitelink.
      const order = [];
      const seenLang = new Set();
      [pref, "en", "de"].forEach(l => {
        if (!seenLang.has(l)) { seenLang.add(l); order.push(l + "wiki"); }
      });
      let lang = null, title = null;
      for (const k of order) {
        if (sitelinks[k] && sitelinks[k].title) {
          lang = k.replace(/wiki$/, ""); title = sitelinks[k].title; break;
        }
      }
      if (!title) {
        const anyKey = Object.keys(sitelinks).find(
          k => /wiki$/.test(k) && !/wik(tionary|inews|iquote|isource|ibooks|iversity|ivoyage)$/.test(k) && sitelinks[k].title
        );
        if (anyKey) { lang = anyKey.replace(/wiki$/, ""); title = sitelinks[anyKey].title; }
      }
      if (!title || !lang) return null;
      const summaryUrl = "https://" + lang + ".wikipedia.org/api/rest_v1/page/summary/" +
        encodeURIComponent(title);
      return fetch(summaryUrl)
        .then(r => (r && r.ok ? r.json() : null))
        .then(s => {
          if (!s || !s.extract) return null;
          return {
            title: s.title || title,
            extract: s.extract,
            description: s.description || (ent.descriptions && ent.descriptions[lang] && ent.descriptions[lang].value) || null,
            thumbnail: (s.thumbnail && s.thumbnail.source) || null,
            url: (s.content_urls && s.content_urls.desktop && s.content_urls.desktop.page) ||
              ("https://" + lang + ".wikipedia.org/wiki/" + encodeURIComponent(title)),
            lang: s.lang || lang,
            wikidataUrl,
          };
        });
    })
    .then(data => {
      // Cache result (including null, to avoid retry storms within the session).
      WIKI_INFO_CACHE.set(cacheKey, data);
      if (data) {
        try { localStorage.setItem(lsKey, JSON.stringify({ ts: Date.now(), data })); }
        catch (e) { /* storage full / unavailable: still have in-session cache */ }
      }
      return data;
    })
    .catch(() => {
      // Network/offline/CORS/file:// failure: cache null for this session.
      WIKI_INFO_CACHE.set(cacheKey, null);
      return null;
    });

  return result;
}

function renderTriggerDetail(trigNode, catColor) {
  const panel = document.getElementById("trigger-detail");
  panel.classList.remove("empty");
  panel.classList.add("trigger-dashboard-host");
  panel.innerHTML = "";

  // Stamp the current trigger so async fills (e.g. the Wikipedia card) can
  // bail out if the user navigated to a different trigger meanwhile.
  panel.dataset.triggerId = trigNode.id || "";

  const box = document.createElement("div");
  box.className = "detail-dashboard";
  panel.appendChild(box);

  const rows = hypothesesForTrigger(trigNode);
  const langs = [...new Set(rows.map(r => r.lang))];

  // ---- 1. At-a-glance header card ---------------------------------------
  const header = document.createElement("div");
  header.className = "dash-card dash-header";

  const titleRow = document.createElement("div");
  titleRow.className = "dash-title-row dash-trigger-title-row";
  titleRow.innerHTML =
    '<span class="dash-word dash-trigger-word">' + escHtml(trigNode.label) + '</span>' +
    '<span class="dash-cat-chip">' + escHtml(trigNode.category || "trigger") + '</span>';
  header.appendChild(titleRow);

  // Date + Wikidata link
  const metaLine = document.createElement("div");
  metaLine.className = "dash-meta-line";
  let metaHtml =
    '<span class="dash-meta-key">Date</span>' +
    '<span class="dash-meta-val">' + escHtml(trigNode.date != null ? String(trigNode.date) : "?") + '</span>';
  const wd = wikidataLink(trigNode.wikidataSameAs);
  if (wd) {
    metaHtml +=
      '<a class="dash-wikidata-link" href="' + wd.url + '" target="_blank" rel="noopener noreferrer" ' +
      'title="' + escHtml(trigNode.label) + ' on Wikidata (' + wd.qid + ')">Wikidata ' +
      '<span aria-hidden="true">&#8599;</span></a>';
  }
  metaLine.innerHTML = metaHtml;
  header.appendChild(metaLine);

  // Impact line: "Reframed N words across M languages"
  const wordN = rows.length || trigNode.wordCount || 0;
  if (wordN > 0) {
    const langN = langs.length;
    const impact = document.createElement("div");
    impact.className = "dash-impact-line";
    impact.innerHTML =
      'Reframed <strong>' + wordN + '</strong> word' + (wordN === 1 ? '' : 's') +
      ' across <strong>' + langN + '</strong> language' + (langN === 1 ? '' : 's') +
      (langN ? ' <span class="dash-impact-langs">(' +
        langs.map(l => escHtml(langLabel(l))).join(", ") + ')</span>' : '');
    header.appendChild(impact);
  }

  box.appendChild(header);

  // ---- 2. Description card ----------------------------------------------
  if (trigNode.description) {
    const descCard = document.createElement("div");
    descCard.className = "dash-card dash-trigger-desc";
    descCard.innerHTML =
      '<div class="dash-card-title">Description</div>' +
      '<p class="dash-desc-text">' + escHtml(trigNode.description) + '</p>';
    box.appendChild(descCard);
  }

  // ---- 2b. About this event (live Wikipedia summary) --------------------
  renderTriggerWikiCard(box, trigNode, rows, langs);

  // ---- 3. Cross-lingual highlight (shared-trigger pair) -----------------
  const deWords = rows.filter(r => r.lang === "de").map(r => r.word);
  const enWords = rows.filter(r => r.lang === "en").map(r => r.word);
  if (deWords.length && enWords.length) {
    const xCard = document.createElement("div");
    xCard.className = "dash-card dash-trigger-xling";
    xCard.innerHTML =
      '<div class="dash-card-title">Cross-lingual</div>' +
      '<p class="dash-xling-text">This trigger reframed words in <strong>both</strong> languages: ' +
      '<span class="dash-xling-de">' + deWords.map(escHtml).join(", ") + '</span> ' +
      '<span class="dash-xling-and" aria-hidden="true">&amp;</span> ' +
      '<span class="dash-xling-en">' + enWords.map(escHtml).join(", ") + '</span>.</p>';
    box.appendChild(xCard);
  }

  // ---- 4. Affected-words cards ------------------------------------------
  const wordsCard = document.createElement("div");
  wordsCard.className = "dash-card dash-trigger-words";
  wordsCard.innerHTML = '<div class="dash-card-title">Affected words</div>';
  if (rows.length) {
    const grid = document.createElement("div");
    grid.className = "dash-affected-grid";
    rows.forEach(r => {
      const card = document.createElement("div");
      card.className = "dash-affected" + (r.wordObj ? "" : " is-unlinked");
      const conf = r.confidence;
      card.innerHTML =
        '<div class="dash-affected-head">' +
          '<span class="dash-affected-word">' + escHtml(r.word) + '</span>' +
          '<span class="dash-lang-badge">' + escHtml(r.lang) + '</span>' +
        '</div>' +
        '<span class="type-chip" style="background:' + dtColor(r.driftType) + '22;color:' + dtColor(r.driftType) + ';">' +
          escHtml(r.driftType) + '</span>' +
        (conf != null
          ? '<div class="dash-conf">' +
              '<span class="dash-conf-key">confidence</span>' +
              '<span class="dash-conf-track"><span class="dash-conf-fill" style="width:' + Math.round(conf * 100) + '%;"></span></span>' +
              '<span class="dash-conf-num">' + conf.toFixed(2) + '</span>' +
            '</div>'
          : '');
      if (r.wordObj) {
        makeActivatable(card, () => openWordDetail(r.wordObj));
        card.title = "Open word detail: " + r.word;
      }
      grid.appendChild(card);
    });
    wordsCard.appendChild(grid);
  } else {
    // Fall back to the raw word list when no rich join exists.
    const raw = trigNode.words || [];
    if (raw.length) {
      const list = document.createElement("div");
      list.className = "trigger-word-list";
      raw.forEach(form => {
        const pill = document.createElement("span");
        pill.className = "trigger-word-pill";
        pill.textContent = form;
        const wordObj = (graphData.words || []).find(w => w.writtenForm === form);
        if (wordObj) makeActivatable(pill, () => openWordDetail(wordObj));
        list.appendChild(pill);
      });
      wordsCard.appendChild(list);
    } else {
      const none = document.createElement("p");
      none.className = "dash-hyp-none";
      none.textContent = "No words directly linked in the current dataset.";
      wordsCard.appendChild(none);
    }
  }
  box.appendChild(wordsCard);

  // ---- 5. Evidence / confidence mini-summary ----------------------------
  const confs = rows.map(r => r.confidence).filter(c => c != null);
  const tierCounts = new Map();
  rows.forEach(r => {
    const rung = Math.max(-1, ...r.evidence.map(evidenceRung));
    if (rung >= 0) {
      const label = EVIDENCE_LADDER[rung].label;
      tierCounts.set(label, (tierCounts.get(label) || 0) + 1);
    }
  });
  if (confs.length || tierCounts.size) {
    const sumCard = document.createElement("div");
    sumCard.className = "dash-card dash-trigger-summary";
    sumCard.innerHTML = '<div class="dash-card-title">Evidence &amp; confidence</div>';

    if (confs.length) {
      const mean = confs.reduce((a, b) => a + b, 0) / confs.length;
      const lo = Math.min(...confs), hi = Math.max(...confs);
      const stat = document.createElement("div");
      stat.className = "dash-summary-stat";
      stat.innerHTML =
        '<span class="dash-meta-key">Confidence</span>' +
        '<span class="dash-meta-val">mean ' + mean.toFixed(2) +
        (confs.length > 1 ? ' (' + lo.toFixed(2) + '&ndash;' + hi.toFixed(2) + ')' : '') +
        '</span>';
      sumCard.appendChild(stat);
    }

    if (tierCounts.size) {
      const dist = document.createElement("div");
      dist.className = "dash-tier-dist";
      // Order by ladder strength (strongest first).
      const ordered = EVIDENCE_LADDER
        .map(r => r.label)
        .filter(l => tierCounts.has(l))
        .reverse();
      dist.innerHTML = ordered.map(label =>
        '<span class="dash-tier-pill">' + escHtml(label) +
        ' <span class="dash-tier-count">' + tierCounts.get(label) + '</span></span>'
      ).join("");
      sumCard.appendChild(dist);
    }
    box.appendChild(sumCard);
  }

  updateUrlParam("trigger", trigNode.id);
}

// Render the "About this event" card. Synchronous skeleton + async fill so the
// rest of the dashboard never blocks. Guards against navigation away.
function renderTriggerWikiCard(box, trigNode, rows, langs) {
  const wd = wikidataLink(trigNode.wikidataSameAs);

  const card = document.createElement("div");
  card.className = "dash-card dash-wiki";
  box.appendChild(card);

  // No linked encyclopedia entry: muted note, no network call.
  if (!wd) {
    card.innerHTML =
      '<div class="dash-card-title">About this event</div>' +
      '<p class="dash-wiki-empty">No linked encyclopedia entry for this trigger.</p>';
    return;
  }

  // Prefer German if any reframed word is German, else English.
  const langSet = new Set((langs && langs.length ? langs : (rows || []).map(r => r.lang)));
  const prefLang = langSet.has("de") ? "de" : "en";

  const loadingText = PREFERS_REDUCED_MOTION
    ? '<span class="dash-wiki-loadingtext">Loading...</span>'
    : '<span class="wd-spinner" aria-hidden="true"></span><span class="dash-wiki-loadingtext">Loading...</span>';
  card.innerHTML =
    '<div class="dash-card-title">About this event</div>' +
    '<div class="dash-wiki-loading" role="status">' + loadingText + '</div>';

  const triggerId = trigNode.id || "";

  wikiInfo(trigNode.wikidataSameAs, prefLang).then(info => {
    // Bail if the user navigated to a different trigger meanwhile.
    const panel = document.getElementById("trigger-detail");
    if (!panel || panel.dataset.triggerId !== triggerId) return;
    if (!card.isConnected) return;

    let html = '<div class="dash-card-title">About this event</div>';

    if (!info) {
      // Graceful fallback: Wikidata link only + muted note.
      html +=
        '<p class="dash-wiki-empty">No Wikipedia summary available (offline or no linked article).</p>' +
        '<div class="dash-wiki-footer">' +
          '<a class="dash-wikidata-link dash-wiki-link" href="' + wd.url + '" target="_blank" rel="noopener noreferrer">' +
            'View on Wikidata <span aria-hidden="true">&#8599;</span></a>' +
        '</div>';
      card.innerHTML = html;
      return;
    }

    // Thumbnail (small, right-floated) when present. Only insert it if it is an
    // https Wikimedia URL; otherwise omit the image (F5).
    const safeThumb = safeWikimediaThumb(info.thumbnail);
    if (safeThumb) {
      html +=
        '<img class="dash-wiki-thumb" src="' + escHtml(safeThumb) + '" ' +
        'alt="" loading="lazy" referrerpolicy="no-referrer">';
    }

    // Extract: keep it readable. Split on blank lines into up to 3 paragraphs.
    const paras = String(info.extract).split(/\n{2,}/).map(p => p.trim()).filter(Boolean).slice(0, 3);
    const body = paras.length ? paras : [String(info.extract)];
    html += body.map(p => '<p class="dash-wiki-extract">' + escHtml(p) + '</p>').join("");

    // Only render the "Read on Wikipedia" link if info.url is an https
    // Wikipedia URL; otherwise drop just that link (F5). The Wikidata link is
    // built internally from a validated QID, so it is always safe.
    const safeUrl = safeWikipediaUrl(info.url);
    html +=
      '<div class="dash-wiki-footer">' +
        (safeUrl
          ? '<a class="dash-wikidata-link dash-wiki-link" href="' + escHtml(safeUrl) + '" target="_blank" rel="noopener noreferrer">' +
              'Read on Wikipedia <span aria-hidden="true">&#8599;</span></a>'
          : '') +
        '<a class="dash-wikidata-link dash-wiki-link" href="' + wd.url + '" target="_blank" rel="noopener noreferrer">' +
          'View on Wikidata <span aria-hidden="true">&#8599;</span></a>' +
      '</div>' +
      '<p class="dash-wiki-attr">Summary from Wikipedia, CC BY-SA 4.0</p>';

    card.innerHTML = html;
  });
}

// Build a trigger "node" (the shape renderTriggerDetail expects), enriching the
// raw trigger record with the reframed word list + wordCount from triggerImpact.
function buildTriggerNode(trigger) {
  const impact = (graphData.triggerImpact || []).find(ti => ti.trigger === trigger.id) || {};
  return { ...trigger, wordCount: impact.wordCount || 0, words: impact.words || [] };
}

// Switch to the Triggers tab and show a trigger's detail by id.
function showTriggerById(triggerId) {
  const trigger = (graphData.triggers || []).find(t => t.id === triggerId);
  if (!trigger) return false;
  switchTab("triggers");
  renderTriggerDetail(buildTriggerNode(trigger), null);
  return true;
}

// ---------------------------------------------------------------------------
// WORD DETAIL (reuses original timeline + force graph logic)
// ---------------------------------------------------------------------------

function openWordDetail(word) {
  currentDetailWord = word;

  document.getElementById("detail-word-title").textContent = word.writtenForm;
  document.getElementById("detail-word-lang").textContent = "(" + (word.language || "?") + ")";

  // Update tab label
  const detailTabBtn = document.querySelector('[data-tab="detail"]');
  if (detailTabBtn) detailTabBtn.textContent = "Word Detail: " + word.writtenForm;

  switchTab("detail");
  updateUrlParam("word", word.writtenForm, word.language);
  lsSet(LS.word, word.id);

  if (word.__detailMerged) {
    renderWordDetailBody(word);
    return;
  }

  // Detail not loaded yet: show an inline loader, then render once it lands.
  showDetailLoader();
  const requestedId = word.id;
  ensureDetail(word)
    .then(() => {
      // Ignore stale resolutions if the user navigated to another word.
      if (currentDetailWord && currentDetailWord.id === requestedId) {
        renderWordDetailBody(word);
      }
    })
    .catch(err => {
      if (currentDetailWord && currentDetailWord.id === requestedId) {
        showDetailError(err);
      }
    });
}

// Render every sub-section of the word-detail view (detail must be merged).
function renderWordDetailBody(word) {
  hideDetailLoader();
  renderDetailDashboard(word);
  // The standalone proposed-trigger strip is superseded by the dashboard's
  // causal hypothesis cards (which carry the same clickable triggers). Keep
  // it hidden to avoid duplicate trigger pills.
  document.getElementById("detail-triggers").hidden = true;
  renderDetailTimeline(word);
  renderDetailGraph(word);
}

// Inline loader shown while heavy detail is fetched for an opened word.
function showDetailLoader() {
  const box = document.getElementById("detail-dashboard");
  box.hidden = false;
  box.innerHTML =
    '<div class="dash-card detail-loading-card">' +
      '<span class="wd-spinner" aria-hidden="true"></span>' +
      '<span>Loading word detail&hellip;</span>' +
    '</div>';
  document.getElementById("detail-tl-wrap").innerHTML =
    '<p class="empty-msg"><span class="wd-spinner" aria-hidden="true"></span> Loading timeline&hellip;</p>';
  document.getElementById("detail-graph-wrap").innerHTML =
    '<p class="empty-msg"><span class="wd-spinner" aria-hidden="true"></span> Loading force graph&hellip;</p>';
  document.getElementById("detail-triggers").hidden = true;
}

function hideDetailLoader() { /* replaced by real content in renderWordDetailBody */ }

function showDetailError(err) {
  const box = document.getElementById("detail-dashboard");
  box.hidden = false;
  box.innerHTML =
    '<div class="dash-card detail-loading-card">Could not load word detail: ' +
    escHtml(err && err.message ? err.message : String(err)) + '</div>';
}

// ---------------------------------------------------------------------------
// WORD DASHBOARD
// A consolidated, scannable single-word view rendered as a responsive grid of
// cards above the sense timeline + force graph. Sections:
//   1. At-a-glance header (drift types, connotation arc, year span, badges)
//   2. Causal hypothesis card(s) (trigger + evidence ladder + confidence)
//   3. Senses (gloss, connotation dot, firstAttested) in chronological order
//   4. Frequency sparkline (hidden if no observations)
//   5. Cross-lingual sibling (shared trigger id, other language)
//   6. Sources (distinct source labels for this word)
// ---------------------------------------------------------------------------

// Evidence ladder, weakest -> strongest. Matched loosely against the
// per-cause evidence strings in driftEventsFlat (which carry trailing
// qualifiers like "speculative (temporal coincidence)").
const EVIDENCE_LADDER = [
  { key: "speculative",  label: "Speculative" },
  { key: "frequency",    label: "FrequencyCorrelation" },
  { key: "change-signal",label: "ChangeSignalAlignment" },
  { key: "lexicographic",label: "LexicographicNote" },
  { key: "scholarly",    label: "ScholarlyAttestation" },
];

// Map a raw evidence string to a ladder rung index (0..4), or -1 if unknown.
function evidenceRung(raw) {
  if (!raw) return -1;
  const s = raw.toLowerCase();
  for (let i = 0; i < EVIDENCE_LADDER.length; i++) {
    if (s.indexOf(EVIDENCE_LADDER[i].key) !== -1) return i;
  }
  return -1;
}

// Find the flat drift events (rich causes: evidence + confidence) for a word.
function flatEventsForWord(word) {
  return (graphData.driftEventsFlat || []).filter(
    e => e.word === word.writtenForm && e.lang === (word.language || "?")
  );
}

// Resolve a trigger object by id from the graph.
function triggerById(id) {
  return (graphData.triggers || []).find(t => t.id === id) || null;
}

// Make a clickable element behave like the existing pill pattern.
function makeActivatable(el, onActivate) {
  el.setAttribute("role", "button");
  el.setAttribute("tabindex", "0");
  el.addEventListener("click", onActivate);
  el.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onActivate(); }
  });
}

function renderDetailDashboard(word) {
  const box = document.getElementById("detail-dashboard");
  box.innerHTML = "";
  box.hidden = false;

  const senses      = word.senses || [];
  const driftEvents = word.driftEvents || [];
  const flatEvents  = flatEventsForWord(word);

  // ---- 1. At-a-glance header card ---------------------------------------
  const header = document.createElement("div");
  header.className = "dash-card dash-header";

  // Title + language badge
  const titleRow = document.createElement("div");
  titleRow.className = "dash-title-row";
  titleRow.innerHTML =
    '<span class="dash-word">' + escHtml(word.writtenForm) + '</span>' +
    '<span class="dash-lang-badge">' + escHtml(word.language || "?") + '</span>';
  header.appendChild(titleRow);

  // Drift type chips
  const driftTypes = [...new Set(driftEvents.map(d => d.driftTypeLabel).filter(Boolean))];
  if (driftTypes.length) {
    const chips = document.createElement("div");
    chips.className = "dash-type-chips";
    chips.innerHTML = driftTypes.map(t =>
      '<span class="type-chip" style="background:' + dtColor(t) + '22;color:' + dtColor(t) + ';">' +
      escHtml(t) + '</span>'
    ).join("");
    header.appendChild(chips);
  }

  // Connotation arc: earliest sense colour -> latest sense colour.
  const sortedSenses = senses.slice().sort(
    (a, b) => (a.firstAttested ?? Infinity) - (b.firstAttested ?? Infinity)
  );
  if (sortedSenses.length) {
    const fromConn = sortedSenses[0].connotation;
    const toConn   = sortedSenses[sortedSenses.length - 1].connotation;
    const arc = document.createElement("div");
    arc.className = "dash-conn-arc";
    const fromTitle = "earliest sense: " + (fromConn || "unknown") + " connotation";
    const toTitle   = "latest sense: "   + (toConn   || "unknown") + " connotation";
    if (fromConn === toConn) {
      arc.innerHTML =
        '<span class="conn-dot" style="background:' + connColor(fromConn) + ';" title="' + escHtml(fromTitle) + '"></span>' +
        '<span class="dash-conn-label">' + escHtml(fromConn || "unknown") + ' (stable)</span>';
    } else {
      arc.innerHTML =
        '<span class="conn-dot" style="background:' + connColor(fromConn) + ';" title="' + escHtml(fromTitle) + '"></span>' +
        '<span class="dash-conn-from">' + escHtml(fromConn || "unknown") + '</span>' +
        '<span class="dash-conn-arrow" aria-hidden="true">&rarr;</span>' +
        '<span class="conn-dot" style="background:' + connColor(toConn) + ';" title="' + escHtml(toTitle) + '"></span>' +
        '<span class="dash-conn-to">' + escHtml(toConn || "unknown") + '</span>';
    }
    header.appendChild(arc);
  }

  // Year span: earliest firstAttested -> latest firstAttested.
  const attYears = senses.map(s => s.firstAttested).filter(y => y != null);
  if (attYears.length) {
    const minY = Math.min(...attYears), maxY = Math.max(...attYears);
    const span = document.createElement("div");
    span.className = "dash-meta-line";
    span.innerHTML =
      '<span class="dash-meta-key">Span</span>' +
      '<span class="dash-meta-val">' + minY + (maxY !== minY ? ' &ndash; ' + maxY : '') + '</span>';
    header.appendChild(span);
  }

  // Source + quality badges
  const wordSources = word.sources || (word.source ? [word.source] : []);
  const badges = document.createElement("div");
  badges.className = "dash-badges";
  badges.innerHTML =
    wordSources.map(s => {
      const slug = SOURCE_SLUG[s] || String(s).toLowerCase();
      const qClass = word.quality === "detected" ? " quality-detected" : "";
      return '<span class="source-badge src-' + slug + qClass + '">' + escHtml(s) + '</span>';
    }).join("") +
    (word.quality
      ? '<span class="dash-quality-badge q-' + escHtml(word.quality) + '">' + escHtml(word.quality) + '</span>'
      : "");
  header.appendChild(badges);

  box.appendChild(header);

  // ---- 2. Causal hypothesis card(s) -------------------------------------
  const causalCard = document.createElement("div");
  causalCard.className = "dash-card dash-causal";
  causalCard.innerHTML = '<div class="dash-card-title">Causal hypotheses</div>';

  driftEvents.forEach(de => {
    const ev = document.createElement("div");
    ev.className = "dash-hyp";

    // Event header: drift type + year(s)
    const yr = de.year != null
      ? (de.yearEnd != null && de.yearEnd !== de.year ? de.year + "–" + de.yearEnd : String(de.year))
      : "";
    const evHead = document.createElement("div");
    evHead.className = "dash-hyp-head";
    evHead.innerHTML =
      '<span class="type-chip" style="background:' + dtColor(de.driftTypeLabel) + '22;color:' + dtColor(de.driftTypeLabel) + ';">' +
        escHtml(de.driftTypeLabel || "drift") + '</span>' +
      (yr ? '<span class="dash-hyp-year">' + escHtml(yr) + '</span>' : '');
    ev.appendChild(evHead);

    const triggerIds = de.triggerIds || [];
    if (triggerIds.length === 0) {
      const none = document.createElement("p");
      none.className = "dash-hyp-none";
      none.textContent = "No proposed trigger for this drift event (gradual / unattributed shift).";
      ev.appendChild(none);
    } else {
      triggerIds.forEach(tid => {
        const trig = triggerById(tid);
        const label = trig ? trig.label : tid.split("/").pop();

        // Match the rich cause record (evidence + confidence) for this trigger.
        let cause = null;
        flatEvents.forEach(fe => {
          (fe.causes || []).forEach(c => {
            if (trig && c.triggerLabel === trig.label) cause = c;
          });
        });

        const hyp = document.createElement("div");
        hyp.className = "dash-hyp-trigger";

        // Clickable trigger pill -> existing showTriggerById
        const pill = document.createElement("span");
        pill.className = "trigger-word-pill";
        pill.textContent = label;
        if (trig) {
          pill.title = (trig.category || "trigger") + (trig.date != null ? " · " + trig.date : "");
          makeActivatable(pill, () => showTriggerById(trig.id));
        }
        hyp.appendChild(pill);

        // Evidence ladder
        const claimedRungs = new Set((cause && cause.evidence ? cause.evidence : []).map(evidenceRung).filter(i => i >= 0));
        const topRung = claimedRungs.size ? Math.max(...claimedRungs) : -1;
        const ladder = document.createElement("div");
        ladder.className = "dash-ladder";
        ladder.setAttribute("role", "list");
        ladder.setAttribute("aria-label", "evidence ladder, strongest claimed tier highlighted");
        EVIDENCE_LADDER.forEach((rung, i) => {
          const claimed = claimedRungs.has(i);
          const isTop = i === topRung;
          const seg = document.createElement("span");
          seg.className = "dash-ladder-rung" +
            (claimed ? " claimed" : "") + (isTop ? " top" : "");
          seg.setAttribute("role", "listitem");
          seg.textContent = rung.label;
          seg.title = rung.label + (claimed ? (isTop ? " (claimed tier)" : " (claimed)") : " (not claimed)");
          ladder.appendChild(seg);
          if (i < EVIDENCE_LADDER.length - 1) {
            const sep = document.createElement("span");
            sep.className = "dash-ladder-sep";
            sep.setAttribute("aria-hidden", "true");
            sep.textContent = "<";
            ladder.appendChild(sep);
          }
        });
        hyp.appendChild(ladder);
        if (topRung < 0) {
          const noEv = document.createElement("p");
          noEv.className = "dash-hyp-none";
          noEv.textContent = "No evidence tier recorded.";
          hyp.appendChild(noEv);
        }

        // Confidence bar + number
        const conf = cause && cause.confidence != null ? cause.confidence : null;
        if (conf != null) {
          const confRow = document.createElement("div");
          confRow.className = "dash-conf";
          confRow.innerHTML =
            '<span class="dash-conf-key">confidence</span>' +
            '<span class="dash-conf-track"><span class="dash-conf-fill" style="width:' + Math.round(conf * 100) + '%;"></span></span>' +
            '<span class="dash-conf-num">' + conf.toFixed(2) + '</span>';
          hyp.appendChild(confRow);
        }

        ev.appendChild(hyp);
      });
    }

    causalCard.appendChild(ev);
  });

  if (driftEvents.length === 0) {
    const none = document.createElement("p");
    none.className = "dash-hyp-none";
    none.textContent = "No drift events recorded for this word.";
    causalCard.appendChild(none);
  }
  box.appendChild(causalCard);

  // ---- 3. Senses card ---------------------------------------------------
  if (sortedSenses.length) {
    const sensesCard = document.createElement("div");
    sensesCard.className = "dash-card dash-senses";
    sensesCard.innerHTML = '<div class="dash-card-title">Senses</div>';
    sortedSenses.forEach(s => {
      const row = document.createElement("div");
      row.className = "dash-sense";
      const yr = s.firstAttested != null ? String(s.firstAttested) : "?";
      row.innerHTML =
        '<span class="conn-dot" style="background:' + connColor(s.connotation) + ';" title="' + escHtml(s.connotation || "unknown") + ' connotation"></span>' +
        '<span class="dash-sense-year">' + escHtml(yr) + '</span>' +
        '<span class="dash-sense-gloss">' + escHtml(s.glossEn || "(no gloss)") + '</span>';
      sensesCard.appendChild(row);
    });
    box.appendChild(sensesCard);
  }

  // ---- 4. Frequency sparkline card --------------------------------------
  const freq = (word.frequencyObservations || [])
    .filter(o => o.year != null && o.value != null)
    .sort((a, b) => a.year - b.year);
  if (freq.length >= 2) {
    const freqCard = document.createElement("div");
    freqCard.className = "dash-card dash-freq";
    freqCard.innerHTML = '<div class="dash-card-title">Frequency</div>';
    const sparkWrap = document.createElement("div");
    sparkWrap.className = "dash-spark-wrap";
    freqCard.appendChild(sparkWrap);
    // Range label
    const range = document.createElement("div");
    range.className = "dash-spark-range";
    range.innerHTML =
      '<span>' + freq[0].year + '</span>' +
      '<span>' + freq[freq.length - 1].year + '</span>';
    freqCard.appendChild(range);
    box.appendChild(freqCard);
    drawSparkline(sparkWrap, freq);
  }

  // ---- 5. Cross-lingual sibling card ------------------------------------
  // Use the EXPLICIT drift:crossLingualOf links only (exported as
  // word.crossLingualOf, a list of partner word ids). These are curated
  // translation equivalents (e.g. mouse <-> Maus). A shared trigger does NOT
  // create a sibling: doomscrolling and Querdenker both reframed under COVID-19
  // but are not equivalents, so neither shows the other here.
  const siblingIds = word.crossLingualOf || [];
  if (siblingIds.length) {
    const siblings = siblingIds
      .map(id => (graphData.words || []).find(w => w.id === id))
      .filter(Boolean);
    if (siblings.length) {
      const sibCard = document.createElement("div");
      sibCard.className = "dash-card dash-sibling";
      sibCard.innerHTML =
        '<div class="dash-card-title">Cross-lingual ' +
        (siblings.length > 1 ? 'siblings' : 'sibling') + '</div>';
      siblings.forEach(sibling => {
        const link = document.createElement("span");
        link.className = "trigger-word-pill dash-sibling-link";
        link.innerHTML =
          'Same concept in <strong>' + escHtml(sibling.language || "?") + '</strong>: ' +
          escHtml(sibling.writtenForm);
        makeActivatable(link, () => openWordDetail(sibling));
        sibCard.appendChild(link);
      });
      box.appendChild(sibCard);
    }
  }

  // ---- 6. Sources card --------------------------------------------------
  // Distinct source labels for this word, mapped to outbound dataset links
  // where one exists; otherwise rendered as a plain badge.
  const distinctSources = [...new Set(wordSources)];
  if (distinctSources.length) {
    const srcCard = document.createElement("div");
    srcCard.className = "dash-card dash-sources";
    srcCard.innerHTML = '<div class="dash-card-title">Sources</div>';
    const list = document.createElement("div");
    list.className = "dash-source-list";
    distinctSources.forEach(s => {
      const url = SOURCE_URL[s];
      const slug = SOURCE_SLUG[s] || String(s).toLowerCase();
      if (url) {
        const a = document.createElement("a");
        a.className = "source-badge src-" + slug;
        a.href = url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = s;
        list.appendChild(a);
      } else {
        const span = document.createElement("span");
        span.className = "source-badge src-" + slug;
        span.textContent = s;
        list.appendChild(span);
      }
    });
    srcCard.appendChild(list);
    box.appendChild(srcCard);
  }
}

// Outbound dataset links for known source labels (sources card).
const SOURCE_URL = {
  "GfdS":   "https://gfds.de/aktionen/wort-des-jahres/",
  "OWID":   "https://www.owid.de/",
  "DWUG":   "https://www.ims.uni-stuttgart.de/data/wugs",
  "SemEval":"https://competitions.codalab.org/competitions/20948",
};

// Tiny inline D3 sparkline of frequency observations.
function drawSparkline(wrap, freq) {
  const W = Math.max(wrap.clientWidth || 220, 160);
  const H = 44;
  const M = { top: 4, right: 4, bottom: 4, left: 4 };
  const x = d3.scaleLinear()
    .domain(d3.extent(freq, d => d.year))
    .range([M.left, W - M.right]);
  const y = d3.scaleLinear()
    .domain([0, d3.max(freq, d => d.value) || 1])
    .range([H - M.bottom, M.top]);

  const svg = d3.select(wrap).append("svg")
    .attr("viewBox", "0 0 " + W + " " + H)
    .attr("width", W).attr("height", H)
    .attr("class", "dash-spark");

  const line = d3.line()
    .x(d => x(d.year))
    .y(d => y(d.value))
    .curve(d3.curveMonotoneX);

  const area = d3.area()
    .x(d => x(d.year))
    .y0(H - M.bottom)
    .y1(d => y(d.value))
    .curve(d3.curveMonotoneX);

  svg.append("path").datum(freq)
    .attr("fill", "var(--accent)").attr("opacity", 0.14)
    .attr("d", area);
  svg.append("path").datum(freq)
    .attr("fill", "none").attr("stroke", "var(--accent)")
    .attr("stroke-width", 1.6).attr("d", line);

  // Endpoint marker
  const last = freq[freq.length - 1];
  svg.append("circle")
    .attr("cx", x(last.year)).attr("cy", y(last.value))
    .attr("r", 2.6).attr("fill", "var(--accent-hi)");
}

// Render clickable trigger pills in the word detail, linking back to the
// Triggers tab. The link is reified: each pill is a drift:CausalHypothesis
// proposedTrigger resolved from driftEvents[].triggerIds. No curated trigger,
// no section (avoid empty noise).
function renderDetailTriggers(word) {
  const box = document.getElementById("detail-triggers");
  box.innerHTML = "";

  const triggerIds = [...new Set((word.driftEvents || []).flatMap(d => d.triggerIds || []))];
  const triggers = (graphData.triggers || []).filter(t => triggerIds.includes(t.id));

  if (triggers.length === 0) {
    box.hidden = true;
    return;
  }
  box.hidden = false;

  const heading = document.createElement("div");
  heading.className = "detail-triggers-title";
  heading.textContent = triggers.length === 1 ? "Proposed trigger" : "Proposed triggers";
  box.appendChild(heading);

  const list = document.createElement("div");
  list.className = "trigger-word-list";
  triggers.forEach(t => {
    const pill = document.createElement("span");
    pill.className = "trigger-word-pill";
    pill.setAttribute("role", "button");
    pill.setAttribute("tabindex", "0");
    pill.textContent = t.label;
    pill.title = (t.category || "trigger") + (t.date != null ? " · " + t.date : "");
    pill.addEventListener("click", () => showTriggerById(t.id));
    pill.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); showTriggerById(t.id); } });
    list.appendChild(pill);
  });
  box.appendChild(list);
}

// ---------------------------------------------------------------------------
// Detail: Sense Timeline (ported from original explore.html)
// ---------------------------------------------------------------------------

function renderDetailTimeline(word) {
  const wrap = document.getElementById("detail-tl-wrap");
  wrap.innerHTML = "";

  const { senses, driftEvents, frequencyObservations } = word;

  if (!senses || senses.length === 0) {
    wrap.innerHTML = '<p class="empty-msg">No senses found for this word.</p>';
    return;
  }

  const triggerIds = new Set(driftEvents.flatMap(d => d.triggerIds || []));
  const triggers   = (graphData.triggers || []).filter(t => triggerIds.has(t.id));

  const allYears = [
    ...senses.map(s => s.firstAttested).filter(Boolean),
    ...driftEvents.map(d => d.year).filter(Boolean),
    ...triggers.map(t => t.date).filter(Boolean),
    ...frequencyObservations.map(o => o.year).filter(Boolean),
  ];

  if (allYears.length === 0) {
    wrap.innerHTML = '<p class="empty-msg">No year data available for this word.</p>';
    return;
  }

  const minYear = Math.min(...allYears) - 20;
  const maxYear = Math.max(...allYears) + 30;

  const W = Math.max(wrap.clientWidth || 860, 500);
  const MARGIN = { top: 30, right: 40, bottom: 50, left: 20 };
  const SENSE_H = 52;
  const SENSE_GAP = 16;
  const SPARKLINE_H = 48;
  const TRIGGER_ZONE_H = 48;

  const nSenses = senses.length;
  const hasSpark = frequencyObservations.length >= 2;
  const SENSES_H = nSenses * SENSE_H + (nSenses - 1) * SENSE_GAP;
  const INNER_H = SENSES_H + TRIGGER_ZONE_H + (hasSpark ? SPARKLINE_H + 16 : 0) + 20;
  const H = INNER_H + MARGIN.top + MARGIN.bottom;

  const x = d3.scaleLinear().domain([minYear, maxYear]).range([MARGIN.left, W - MARGIN.right]);

  const svg = d3.select(wrap).append("svg")
    .attr("viewBox", "0 0 " + W + " " + H)
    .attr("width", W).attr("height", H);

  const defs = svg.append("defs");
  defs.append("marker")
    .attr("id", "tl-arrow-det").attr("markerWidth", 8).attr("markerHeight", 6)
    .attr("refX", 8).attr("refY", 3).attr("orient", "auto")
    .append("polygon").attr("points", "0 0, 8 3, 0 6").attr("fill", DRIFT_EDGE_COLOR);

  svg.append("rect").attr("width", W).attr("height", H).attr("fill", BG_COLOR);

  const g = svg.append("g").attr("transform", "translate(0," + MARGIN.top + ")");

  // X axis
  const axisG = g.append("g")
    .attr("transform", "translate(0," + (SENSES_H + TRIGGER_ZONE_H + 10) + ")");
  axisG.append("line")
    .attr("x1", MARGIN.left).attr("x2", W - MARGIN.right)
    .attr("stroke", GRID_LINE).attr("stroke-width", 1);
  const tickCount = Math.min(12, Math.max(4, Math.floor((maxYear - minYear) / 30)));
  x.ticks(tickCount).forEach(yr => {
    axisG.append("line")
      .attr("x1", x(yr)).attr("x2", x(yr)).attr("y1", -4).attr("y2", 8).attr("stroke", GRID_LINE);
    axisG.append("text")
      .attr("x", x(yr)).attr("y", 22).attr("text-anchor", "middle")
      .attr("fill", AXIS_TEXT).attr("font-size", 11).attr("font-family", "Inter,sans-serif").text(yr);
  });

  // Sense y positions
  const senseY = {};
  senses.forEach((s, i) => { senseY[s.id] = i * (SENSE_H + SENSE_GAP) + SENSE_H / 2; });

  // Sense bands
  senses.forEach(s => {
    const cy = senseY[s.id];
    const y0 = cy - SENSE_H / 2;
    const color = connColor(s.connotation);
    const xStart = s.firstAttested ? x(s.firstAttested) : MARGIN.left + 2;
    const xEnd = W - MARGIN.right;
    const bandW = Math.max(xEnd - xStart, 2);

    g.append("rect").attr("x", xStart).attr("y", y0)
      .attr("width", bandW).attr("height", SENSE_H).attr("rx", 5).attr("ry", 5)
      .attr("fill", color).attr("opacity", 0.08);
    g.append("line").attr("x1", xStart).attr("x2", xStart)
      .attr("y1", y0 + 4).attr("y2", y0 + SENSE_H - 4)
      .attr("stroke", color).attr("stroke-width", 2.5).attr("stroke-linecap", "round");
    if (s.firstAttested) {
      g.append("text").attr("x", xStart + 6).attr("y", y0 + 13)
        .attr("fill", color).attr("font-size", 10).attr("font-family", "Inter,sans-serif")
        .attr("font-weight", "600").text(s.firstAttested);
    }
    const glossText = s.glossEn || "";
    const maxChars = Math.floor(bandW / 6.5) - 12;
    const gloss = glossText.length > maxChars ? glossText.slice(0, maxChars) + "..." : glossText;
    g.append("text").attr("x", xStart + 6).attr("y", cy + 5)
      .attr("fill", GLOSS_TEXT).attr("font-size", 11).attr("font-family", "Inter,sans-serif").text(gloss);
    if (s.connotation) {
      const tagX = W - MARGIN.right - 70;
      g.append("rect").attr("x", tagX).attr("y", cy - 9)
        .attr("width", 64).attr("height", 18).attr("rx", 4).attr("fill", color).attr("opacity", 0.18);
      g.append("text").attr("x", tagX + 32).attr("y", cy + 4)
        .attr("text-anchor", "middle").attr("fill", color)
        .attr("font-size", 10).attr("font-weight", "600").attr("font-family", "Inter,sans-serif").text(s.connotation);
    }
    g.append("rect").attr("x", xStart).attr("y", y0).attr("width", bandW).attr("height", SENSE_H)
      .attr("fill", "transparent").attr("cursor", "pointer")
      .on("mouseenter", (event) => {
        showTip(
          "<strong>" + escHtml(word.writtenForm) + " &ndash; sense</strong>" +
          "<p>" + escHtml(s.glossEn || "No gloss") + "</p>" +
          '<p class="tt-sub">Connotation: ' + (s.connotation || "?") + ' &bull; First attested: ' + (s.firstAttested || "?") + '</p>',
          event
        );
      })
      .on("mouseleave", hideTip);
  });

  // Drift arrows
  driftEvents.forEach(de => {
    const fromY = de.senseFromId ? senseY[de.senseFromId] : null;
    const toY   = de.senseToId   ? senseY[de.senseToId]   : null;
    if (fromY == null || toY == null || de.year == null) return;
    const ax = x(de.year);
    const yFrom = fromY + (fromY < toY ?  SENSE_H / 2 : -SENSE_H / 2);
    const yTo   = toY   + (toY < fromY ?  SENSE_H / 2 : -SENSE_H / 2);
    const mx = ax + 24;
    const my = (yFrom + yTo) / 2;
    g.append("path")
      .attr("d", "M " + ax + " " + yFrom + " Q " + mx + " " + my + " " + ax + " " + yTo)
      .attr("stroke", DRIFT_EDGE_COLOR).attr("stroke-width", 1.8).attr("fill", "none")
      .attr("marker-end", "url(#tl-arrow-det)")
      .attr("opacity", de.confidence != null ? Math.max(0.35, de.confidence) : 0.75);
    if (de.driftTypeLabel) {
      g.append("text").attr("x", mx + 4).attr("y", my)
        .attr("fill", DRIFT_EDGE_COLOR).attr("font-size", 9.5).attr("font-family", "Inter,sans-serif")
        .attr("dominant-baseline", "middle").text(de.driftTypeLabel);
    }
  });

  // Trigger markers
  const trigZoneY = SENSES_H + 4;
  const usedX = {};
  triggers.forEach(t => {
    if (!t.date) return;
    const tx = x(t.date);
    g.append("line").attr("x1", tx).attr("x2", tx).attr("y1", 0).attr("y2", SENSES_H)
      .attr("stroke", TRIGGER_COLOR).attr("stroke-width", 1).attr("stroke-dasharray", "3 3").attr("opacity", 0.4);
    const dy = trigZoneY + 14;
    const ds = 7;
    g.append("polygon")
      .attr("points", tx + "," + (dy - ds) + " " + (tx + ds) + "," + dy + " " + tx + "," + (dy + ds) + " " + (tx - ds) + "," + dy)
      .attr("fill", TRIGGER_COLOR).attr("opacity", 0.85).attr("cursor", "pointer")
      .on("mouseenter", (event) => {
        showTip(
          "<strong>" + escHtml(t.label) + "</strong>" +
          "<p>" + escHtml(t.category || "trigger") + "</p>" +
          '<p class="tt-sub">Date: ' + (t.date || "?") + "</p>",
          event
        );
      })
      .on("mouseleave", hideTip);
    const key = Math.round(tx / 20);
    let labelY = trigZoneY + 10;
    if (usedX[key]) labelY += 16;
    usedX[key] = true;
    const shortLabel = t.label.length > 26 ? t.label.slice(0, 26) + "..." : t.label;
    g.append("text").attr("x", tx + 9).attr("y", labelY)
      .attr("fill", TRIGGER_COLOR).attr("font-size", 9.5).attr("font-family", "Inter,sans-serif").text(shortLabel);
  });

  // Sparkline
  if (hasSpark) {
    const sparkY0 = SENSES_H + TRIGGER_ZONE_H + 18;
    const freqVals = frequencyObservations.map(o => o.value);
    const ySpark = d3.scaleLinear()
      .domain([Math.min(...freqVals), Math.max(...freqVals)])
      .range([sparkY0 + SPARKLINE_H, sparkY0]);
    const lineFn = d3.line().x(o => x(o.year)).y(o => ySpark(o.value)).curve(d3.curveMonotoneX);
    const areaFn = d3.area().x(o => x(o.year)).y0(sparkY0 + SPARKLINE_H).y1(o => ySpark(o.value)).curve(d3.curveMonotoneX);
    g.append("path").datum(frequencyObservations).attr("d", areaFn)
      .attr("fill", DRIFT_EDGE_COLOR).attr("opacity", 0.06);
    g.append("path").datum(frequencyObservations).attr("d", lineFn)
      .attr("fill", "none").attr("stroke", DRIFT_EDGE_COLOR).attr("stroke-width", 1.5).attr("opacity", 0.8);
    g.append("text").attr("x", MARGIN.left + 2).attr("y", sparkY0 - 4)
      .attr("fill", AXIS_TEXT).attr("font-size", 9.5).attr("font-family", "Inter,sans-serif")
      .text("relative frequency (corpus)");
    g.selectAll(".spark-dot").data(frequencyObservations).join("circle")
      .attr("cx", o => x(o.year)).attr("cy", o => ySpark(o.value))
      .attr("r", 3).attr("fill", DRIFT_EDGE_COLOR).attr("cursor", "pointer")
      .on("mouseenter", (event, o) => {
        showTip("<strong>Frequency: " + o.value + "</strong><p>Year: " + o.year + "</p>", event);
      })
      .on("mouseleave", hideTip);
  }
}

// ---------------------------------------------------------------------------
// Detail: Force graph (ported from original explore.html)
// ---------------------------------------------------------------------------

function renderDetailGraph(word) {
  const wrap = document.getElementById("detail-graph-wrap");
  wrap.innerHTML = "";

  const { senses, driftEvents } = word;
  if (!senses || senses.length === 0) {
    wrap.innerHTML = '<p class="empty-msg">No senses found for this word.</p>';
    return;
  }

  const triggerIds = new Set(driftEvents.flatMap(d => d.triggerIds || []));
  const triggers   = (graphData.triggers || []).filter(t => triggerIds.has(t.id));

  const nodes = [
    ...senses.map(s => ({
      id: s.id, type: "sense",
      label: word.writtenForm + (s.firstAttested ? " (" + s.firstAttested + ")" : ""),
      shortLabel: s.firstAttested ? String(s.firstAttested) : "?",
      gloss: s.glossEn, connotation: s.connotation, color: connColor(s.connotation),
    })),
    ...triggers.map(t => ({
      id: t.id, type: "trigger",
      label: t.label, shortLabel: t.date ? String(t.date) : "?",
      gloss: t.description, connotation: null, color: TRIGGER_COLOR,
      date: t.date, category: t.category,
    })),
  ];

  const links = [];
  driftEvents.forEach(de => {
    if (de.senseFromId && de.senseToId)
      links.push({ source: de.senseFromId, target: de.senseToId, type: "drift", label: de.driftTypeLabel || "", confidence: de.confidence });
  });
  driftEvents.forEach(de => {
    (de.triggerIds || []).forEach(tid => {
      const anchorId = de.senseToId || de.senseFromId;
      if (anchorId) links.push({ source: anchorId, target: tid, type: "trigger", label: "", confidence: de.confidence });
    });
  });

  const W = Math.max(wrap.clientWidth || 860, 500);
  const H = 480;

  const svg = d3.select(wrap).append("svg")
    .attr("viewBox", "0 0 " + W + " " + H).attr("width", W).attr("height", H);

  svg.append("rect").attr("width", W).attr("height", H).attr("fill", BG_COLOR);

  const defs = svg.append("defs");
  defs.append("marker").attr("id", "det-arrow-drift")
    .attr("markerWidth", 8).attr("markerHeight", 6).attr("refX", 20).attr("refY", 3).attr("orient", "auto")
    .append("polygon").attr("points", "0 0, 8 3, 0 6").attr("fill", NODE_STROKE);
  defs.append("marker").attr("id", "det-arrow-trigger")
    .attr("markerWidth", 8).attr("markerHeight", 6).attr("refX", 20).attr("refY", 3).attr("orient", "auto")
    .append("polygon").attr("points", "0 0, 8 3, 0 6").attr("fill", TRIGGER_COLOR);

  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id)
      .distance(d => d.type === "trigger" ? 180 : 150)
      .strength(d => d.type === "trigger" ? 0.25 : 0.6))
    .force("charge", d3.forceManyBody().strength(-400))
    .force("center", d3.forceCenter(W / 2, H / 2))
    .force("collision", d3.forceCollide(36))
    .alphaDecay(0.025);

  // Reduced motion: compute a static layout (no visible animation) by running
  // the simulation to convergence synchronously, then stopping it.
  if (PREFERS_REDUCED_MOTION) {
    sim.stop();
    for (let i = 0; i < 250; i++) sim.tick();
  }

  const gC = svg.append("g");
  svg.call(d3.zoom().scaleExtent([0.3, 4])
    .on("zoom", (event) => { gC.attr("transform", event.transform); }));

  const edgeG = gC.append("g");
  const edgePaths = edgeG.selectAll("path").data(links).join("path")
    .attr("stroke", d => d.type === "trigger" ? TRIGGER_COLOR : NODE_STROKE)
    .attr("stroke-width", d => d.type === "trigger" ? 1.2 : 1.8)
    .attr("stroke-dasharray", d => d.type === "trigger" ? "4 3" : "none")
    .attr("fill", "none")
    .attr("opacity", d => d.confidence != null ? Math.max(0.3, d.confidence * 0.9) : 0.6)
    .attr("marker-end", d => d.type === "trigger" ? "url(#det-arrow-trigger)" : "url(#det-arrow-drift)");

  const edgeLabels = edgeG.selectAll("text").data(links.filter(l => l.type === "drift" && l.label)).join("text")
    .attr("font-size", 10).attr("font-family", "Inter,sans-serif").attr("fill", AXIS_TEXT)
    .text(d => d.label);

  const nodeG = gC.append("g");
  const nodeElems = nodeG.selectAll("g").data(nodes).join("g")
    .call(d3.drag()
      .on("start", (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on("drag",  (event, d) => { d.fx = event.x; d.fy = event.y; })
      .on("end",   (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }))
    .on("mouseenter", (event, d) => {
      if (d.type === "sense") {
        showTip(
          "<strong>" + escHtml(word.writtenForm) + "</strong>" +
          "<p>" + escHtml(d.gloss || "No gloss") + "</p>" +
          '<p class="tt-sub">Connotation: ' + (d.connotation || "?") + ' &bull; First attested: ' + d.shortLabel + '</p>',
          event
        );
      } else {
        showTip(
          "<strong>" + escHtml(d.label) + "</strong>" +
          "<p>" + escHtml(d.gloss || "") + "</p>" +
          '<p class="tt-sub">' + escHtml(d.category || "trigger") + " &bull; Date: " + (d.date || "?") + '</p>',
          event
        );
      }
    })
    .on("mouseleave", hideTip);

  nodeElems.filter(d => d.type === "sense").append("circle")
    .attr("r", 22).attr("fill", d => d.color).attr("opacity", 0.18)
    .attr("stroke", d => d.color).attr("stroke-width", 2);

  const DSIZE = 20;
  nodeElems.filter(d => d.type === "trigger").append("polygon")
    .attr("points", "0," + (-DSIZE) + " " + DSIZE + ",0 0," + DSIZE + " " + (-DSIZE) + ",0")
    .attr("fill", d => d.color).attr("opacity", 0.18)
    .attr("stroke", d => d.color).attr("stroke-width", 2);

  nodeElems.append("text")
    .attr("text-anchor", "middle").attr("dominant-baseline", "middle")
    .attr("font-size", 10).attr("font-family", "Inter,sans-serif").attr("fill", GLOSS_TEXT)
    .text(d => d.shortLabel);

  nodeElems.filter(d => d.type === "sense").append("text")
    .attr("text-anchor", "middle").attr("y", 30).attr("font-size", 9)
    .attr("font-family", "Inter,sans-serif").attr("fill", AXIS_TEXT)
    .text(d => d.connotation ? d.connotation.slice(0, 3) : "?");

  nodeElems.filter(d => d.type === "trigger").append("text")
    .attr("text-anchor", "middle").attr("y", DSIZE + 14).attr("font-size", 9)
    .attr("font-family", "Inter,sans-serif").attr("fill", TRIGGER_COLOR)
    .text(d => { const s = d.label || ""; return s.length > 18 ? s.slice(0, 18) + "..." : s; });

  function renderTick() {
    edgePaths.attr("d", d => {
      const sx = d.source.x, sy = d.source.y, tx = d.target.x, ty = d.target.y;
      const dx = tx - sx, dy = ty - sy;
      const dr = Math.sqrt(dx * dx + dy * dy) * 1.4;
      return "M " + sx + " " + sy + " A " + dr + " " + dr + " 0 0 1 " + tx + " " + ty;
    });
    edgeLabels.attr("x", d => (d.source.x + d.target.x) / 2).attr("y", d => (d.source.y + d.target.y) / 2 - 6);
    nodeElems.attr("transform", d => "translate(" + d.x + "," + d.y + ")");
  }

  if (PREFERS_REDUCED_MOTION) {
    // Static: positions already settled; paint once, no ongoing animation.
    renderTick();
  } else {
    sim.on("tick", renderTick);
  }
}

// ---------------------------------------------------------------------------
// Featured row (vivid examples shown on the overview when no filter is active)
// ---------------------------------------------------------------------------

const FEATURED_FORMS = ["Querdenker", "funk", "slop", "Boykott", "gay", "Kaiser"];

// True when no facet filter is active (default quality-on does not count).
function noFilterActive() {
  if (state.search) return false;
  if (state.langs.size || state.types.size || state.connotations.size) return false;
  if (state.evidences.size || state.sources.size) return false;
  if (state.hasTrigger) return false;
  if (state.yearFrom != null || state.yearTo != null) return false;
  if (state.brushYearFrom != null || state.brushYearTo != null) return false;
  // qualities at the default (high+benchmark, no detected) is treated as "no filter"
  const def = (graphData.facets.quality || []).filter(q => q !== "detected").sort().join(",");
  const cur = [...state.qualities].sort().join(",");
  return cur === def || state.qualities.size === 0;
}

function renderFeaturedRow() {
  const row = document.getElementById("featured-row");
  const cards = document.getElementById("featured-cards");
  if (!row || !cards) return;
  if (!noFilterActive()) { row.hidden = true; return; }

  const picks = [];
  FEATURED_FORMS.forEach(form => {
    const w = (graphData.words || []).find(x => x.writtenForm === form);
    if (w) picks.push(w);
  });
  if (picks.length < 4) { row.hidden = true; return; }

  cards.innerHTML = "";
  picks.forEach(w => {
    const card = buildWordCard(w);
    card.classList.add("featured-card");
    cards.appendChild(card);
  });
  row.hidden = false;
}

// ---------------------------------------------------------------------------
// Random word
// ---------------------------------------------------------------------------

function openRandomWord() {
  const words = graphData && graphData.words ? graphData.words : [];
  if (!words.length) return;
  const w = words[Math.floor(Math.random() * words.length)];
  openWordDetail(w);
}

// ---------------------------------------------------------------------------
// Global search / command palette (fuzzy over words + triggers)
// ---------------------------------------------------------------------------

// Tiny subsequence fuzzy matcher: returns a score (higher = better) or -1.
// Rewards contiguous runs, an early first match, and an exact prefix.
function fuzzyScore(query, target) {
  const q = query.toLowerCase(), t = target.toLowerCase();
  if (!q) return 0;
  if (t === q) return 1000;
  if (t.startsWith(q)) return 800 - t.length;
  let ti = 0, qi = 0, score = 0, run = 0, firstIdx = -1;
  while (ti < t.length && qi < q.length) {
    if (t[ti] === q[qi]) {
      if (firstIdx < 0) firstIdx = ti;
      run += 1;
      score += 10 + run * 4;   // contiguous bonus
      qi += 1;
    } else {
      run = 0;
    }
    ti += 1;
  }
  if (qi < q.length) return -1;   // not all query chars matched
  score -= firstIdx;              // earlier match is better
  score -= (t.length - q.length) * 0.2;
  return score;
}

let searchIndex = [];   // [{type:'word'|'trigger', label, sub, ref}]
let searchActiveIdx = -1;
let searchResults = [];

function buildSearchIndex() {
  searchIndex = [];
  (graphData.words || []).forEach(w => {
    searchIndex.push({
      type: "word",
      label: w.writtenForm,
      sub: (w.language || "?").toUpperCase() + (w.driftTypeLabels && w.driftTypeLabels.length ? " · " + w.driftTypeLabels.join(", ") : ""),
      ref: w,
    });
  });
  (graphData.triggers || []).forEach(t => {
    searchIndex.push({
      type: "trigger",
      label: t.label,
      sub: "trigger" + (t.category ? " · " + t.category : "") + (t.date != null ? " · " + t.date : ""),
      ref: t,
    });
  });
}

function runSearch(query) {
  const q = query.trim();
  const box = document.getElementById("wd-search-results");
  const input = document.getElementById("wd-search");
  if (!q) {
    searchResults = [];
    box.hidden = true;
    input.setAttribute("aria-expanded", "false");
    return;
  }
  searchResults = searchIndex
    .map(item => ({ item, score: fuzzyScore(q, item.label) }))
    .filter(r => r.score > -1)
    .sort((a, b) => b.score - a.score)
    .slice(0, 10)
    .map(r => r.item);
  searchActiveIdx = searchResults.length ? 0 : -1;
  renderSearchResults();
}

function renderSearchResults() {
  const box = document.getElementById("wd-search-results");
  const input = document.getElementById("wd-search");
  if (!searchResults.length) {
    box.innerHTML = '<div class="wd-search-empty">No matches.</div>';
    box.hidden = false;
    input.setAttribute("aria-expanded", "true");
    return;
  }
  box.innerHTML = searchResults.map((item, i) =>
    '<div class="wd-search-item' + (i === searchActiveIdx ? " active" : "") + '" role="option"' +
    ' aria-selected="' + (i === searchActiveIdx ? "true" : "false") + '" data-idx="' + i + '">' +
      '<span class="wd-search-kind wd-search-kind-' + item.type + '">' + (item.type === "word" ? "WORD" : "TRIG") + '</span>' +
      '<span class="wd-search-label">' + escHtml(item.label) + '</span>' +
      '<span class="wd-search-sub">' + escHtml(item.sub) + '</span>' +
    '</div>'
  ).join("");
  box.hidden = false;
  input.setAttribute("aria-expanded", "true");
  box.querySelectorAll(".wd-search-item").forEach(el => {
    el.addEventListener("mousedown", (e) => {
      e.preventDefault();   // keep focus until we act
      selectSearchResult(parseInt(el.dataset.idx, 10));
    });
  });
}

function selectSearchResult(idx) {
  const item = searchResults[idx];
  if (!item) return;
  closeSearch();
  if (item.type === "word") openWordDetail(item.ref);
  else showTriggerById(item.ref.id);
}

function closeSearch() {
  const box = document.getElementById("wd-search-results");
  const input = document.getElementById("wd-search");
  box.hidden = true;
  input.setAttribute("aria-expanded", "false");
  searchResults = [];
  searchActiveIdx = -1;
}

function initSearch() {
  buildSearchIndex();
  const input = document.getElementById("wd-search");
  const box = document.getElementById("wd-search-results");
  if (!input) return;

  input.addEventListener("input", () => runSearch(input.value));
  input.addEventListener("focus", () => { if (input.value.trim()) runSearch(input.value); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); if (searchResults.length) { searchActiveIdx = (searchActiveIdx + 1) % searchResults.length; renderSearchResults(); } }
    else if (e.key === "ArrowUp") { e.preventDefault(); if (searchResults.length) { searchActiveIdx = (searchActiveIdx - 1 + searchResults.length) % searchResults.length; renderSearchResults(); } }
    else if (e.key === "Enter") { e.preventDefault(); if (searchActiveIdx >= 0) selectSearchResult(searchActiveIdx); }
    else if (e.key === "Escape") { input.value = ""; closeSearch(); input.blur(); }
  });
  input.addEventListener("blur", () => { setTimeout(closeSearch, 120); });

  // "/" focuses the search (unless already typing in a field).
  document.addEventListener("keydown", (e) => {
    if (e.key !== "/") return;
    const tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || e.target.isContentEditable) return;
    e.preventDefault();
    input.focus();
    input.select();
  });

  // Random word + help buttons.
  const randomBtn = document.getElementById("wd-random-btn");
  if (randomBtn) randomBtn.addEventListener("click", openRandomWord);
  const helpBtn = document.getElementById("wd-help-btn");
  if (helpBtn) helpBtn.addEventListener("click", () => showOnboarding(true));
}

// ---------------------------------------------------------------------------
// Onboarding overlay (one-time, localStorage flag; reopenable via ? button)
// ---------------------------------------------------------------------------

function maybeShowOnboarding() {
  if (lsGet(LS.onboarded) === "1") return;
  showOnboarding(false);
}

function showOnboarding(force) {
  const ov = document.getElementById("wd-onboard");
  if (!ov) return;
  ov.hidden = false;
  const close = () => {
    ov.hidden = true;
    lsSet(LS.onboarded, "1");
  };
  document.getElementById("wd-onboard-close").onclick = close;
  document.getElementById("wd-onboard-dismiss").onclick = close;
  ov.onclick = (e) => { if (e.target === ov) close(); };
  // Escape closes.
  const onKey = (e) => { if (e.key === "Escape") { close(); document.removeEventListener("keydown", onKey); } };
  document.addEventListener("keydown", onKey);
}

// ---------------------------------------------------------------------------
// window.WD plugin API
// Exposes a stable surface for parallel view modules. See assets/views/API.md.
// ---------------------------------------------------------------------------

function publishWD() {
  window.WD = {
    // --- data ---
    core: graphData,
    get words()           { return graphData ? graphData.words : []; },
    get triggers()        { return graphData ? graphData.triggers : []; },
    get driftEventsFlat() { return graphData ? graphData.driftEventsFlat : []; },
    get triggerImpact()   { return graphData ? graphData.triggerImpact : []; },
    get meta()            { return graphData ? graphData.meta : null; },
    get facets()          { return graphData ? graphData.facets : null; },
    get byDecadeType()    { return graphData ? graphData.byDecadeType : []; },

    // Lazy heavy detail: resolves to the word with senses/driftEvents/
    // frequencyObservations merged in. Accepts a wordId string or word object.
    getDetail(wordOrId) {
      const word = typeof wordOrId === "string"
        ? (graphData.words || []).find(w => w.id === wordOrId)
        : wordOrId;
      if (!word) return Promise.resolve(null);
      return ensureDetail(word);
    },

    // Look up helpers (synchronous, light data).
    wordById(id)     { return (graphData.words || []).find(w => w.id === id) || null; },
    triggerById(id)  { return triggerById(id); },
    flatForWord(w)   { return flatFor(w); },

    // --- navigation ---
    openWord(wordOrId) {
      const word = typeof wordOrId === "string"
        ? (graphData.words || []).find(w => w.id === wordOrId)
        : wordOrId;
      if (word) openWordDetail(word);
    },
    showTrigger(triggerId) { return showTriggerById(triggerId); },
    switchTab(name)        { switchTab(name); },

    // --- view registration ---
    // Register a tab-bound view. The matching tab button + #panelId must exist
    // (the four extra tabs are in the DOM up front). onActivate(panelEl) fires
    // when the tab becomes active. Returns true on success.
    registerView(name, def) {
      if (!name || !def || typeof def.onActivate !== "function") return false;
      viewRegistry.set(name, {
        label: def.label || name,
        panelId: def.panelId || ("panel-" + name),
        onActivate: def.onActivate,
        activated: false,
      });
      // Relabel the tab button if a label was provided.
      const btn = document.querySelector('.exp-tab-btn[data-tab="' + name + '"]');
      if (btn && def.label) btn.textContent = def.label;
      // If this tab is already active (e.g. restored), activate immediately.
      const panel = document.getElementById("panel-" + name);
      if (panel && panel.classList.contains("active")) {
        try { def.onActivate(panel); viewRegistry.get(name).activated = true; }
        catch (e) { console.error(e); }
      }
      return true;
    },

    // Toolbar hook stub for exporter.js and similar utility modules. Adds a
    // button to the top-bar actions; returns the created element (or null).
    registerToolbarButton(opts) {
      const host = document.querySelector(".topbar-actions");
      if (!host || !opts || typeof opts.onClick !== "function") return null;
      const b = document.createElement("button");
      b.type = "button";
      b.className = "wd-icon-btn";
      b.textContent = opts.label || "Action";
      if (opts.title) b.title = opts.title;
      b.addEventListener("click", opts.onClick);
      host.appendChild(b);
      return b;
    },

    // --- encyclopedia (Wikipedia via Wikidata) ---
    // Resolve a Wikidata QID (full URI, /wiki/Qxxx, or bare Qxxx) + langPref
    // ("de"|"en") to a Promise of { title, extract, description, thumbnail,
    // url, lang, wikidataUrl } or null. Cached in-session + localStorage (~7d).
    // Never throws.
    wikiInfo: wikiInfo,

    // --- shared helpers (so modules render consistently with the core) ---
    escHtml: escHtml,
    makeActivatable: makeActivatable,
    dtColor: dtColor,
    connColor: connColor,
    causeColor: causeColor,
    fmtYear: fmtYear,
    EVIDENCE_LADDER: EVIDENCE_LADDER,
    evidenceRung: evidenceRung,
    prefersReducedMotion: PREFERS_REDUCED_MOTION,
    colors: {
      // DT_COLORS / CONN_COLORS are mutated in place by applyThemePalette so the
      // same object reference always holds the live theme colours. The scalars
      // are exposed via getters so a theme flip is observed by view modules.
      DT_COLORS, CONN_COLORS,
      get TRIGGER_COLOR() { return TRIGGER_COLOR; },
      get DRIFT_EDGE_COLOR() { return DRIFT_EDGE_COLOR; },
      get BG_COLOR() { return BG_COLOR; },
      get CAUSE_PALETTE() { return CAUSE_PALETTE; },
      get CAUSE_COLOR_MAP() { return CAUSE_COLOR_MAP; },
      get ACCENT_COLOR() { return ACCENT_COLOR; },
      get GLOSS_TEXT() { return GLOSS_TEXT; },
      get AXIS_TEXT() { return AXIS_TEXT; },
      get FAINT_TEXT() { return FAINT_TEXT; },
      get GRID_LINE() { return GRID_LINE; },
      get NODE_STROKE() { return NODE_STROKE; },
    },
  };
}

// Format a year for display: negative years render as "350 BC".
function fmtYear(y) {
  if (y == null) return "?";
  return y < 0 ? Math.abs(y) + " BC" : String(y);
}

// ---------------------------------------------------------------------------
// Resize handler
// ---------------------------------------------------------------------------

let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    const overviewActive = document.getElementById("panel-overview").classList.contains("active");
    const triggersActive = document.getElementById("panel-triggers").classList.contains("active");
    const detailActive   = document.getElementById("panel-detail").classList.contains("active");

    if (overviewActive) renderOverviewTimeline();
    if (triggersActive) { triggerTlRendered = false; renderTriggerTimeline(); }
    if (detailActive && currentDetailWord && currentDetailWord.__detailMerged) {
      renderDetailDashboard(currentDetailWord);
      document.getElementById("detail-triggers").hidden = true;
      renderDetailTimeline(currentDetailWord);
      renderDetailGraph(currentDetailWord);
    }
    // Let active plugin views re-layout to the new width.
    const activePanel = document.querySelector(".exp-panel.active");
    if (activePanel) {
      const view = viewRegistry.get(activePanel.id.replace(/^panel-/, ""));
      if (view && view.activated && typeof view.onActivate === "function") {
        try { view.onActivate(activePanel); } catch (e) {}
      }
    }
  }, 280);
});

// Publish window.WD synchronously at the end of the inline script. This runs
// during HTML parse, BEFORE any `defer` view module executes, so modules can
// always call WD.registerView(...) regardless of when graph-core.json lands.
// Data getters read `graphData` lazily; the loader sets `WD.core` once ready.
publishWD();

