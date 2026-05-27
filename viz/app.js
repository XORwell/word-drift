/**
 * app.js — WORD-DRIFT visualization
 * Fetches viz/data/graph.json and renders:
 *   1. A horizontal sense timeline with drift arrows and trigger markers
 *   2. A D3 force-directed graph of senses and trigger events
 */

"use strict";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DATA_URL = "data/graph.json";

const CONNOTATION_COLOR = {
  positive: "#34c97e",
  neutral:  "#8a94b0",
  negative: "#f05252",
};

const TRIGGER_COLOR = "#f5a623";
const DRIFT_EDGE_COLOR = "#5b7cf8";
const BG_COLOR = "#1a1d27";

// Prefer a known connotation label; fall back gracefully
function connColor(label) {
  if (!label) return CONNOTATION_COLOR.neutral;
  return CONNOTATION_COLOR[label.toLowerCase()] || CONNOTATION_COLOR.neutral;
}

// ---------------------------------------------------------------------------
// Tooltip
// ---------------------------------------------------------------------------

const tooltip = document.getElementById("tooltip");

function showTooltip(html, event) {
  tooltip.innerHTML = html;
  tooltip.style.display = "block";
  positionTooltip(event);
}

function hideTooltip() {
  tooltip.style.display = "none";
}

function positionTooltip(event) {
  const pad = 14;
  let x = event.clientX + pad;
  let y = event.clientY + pad;
  const w = tooltip.offsetWidth;
  const h = tooltip.offsetHeight;
  if (x + w > window.innerWidth - 10) x = event.clientX - w - pad;
  if (y + h > window.innerHeight - 10) y = event.clientY - h - pad;
  tooltip.style.left = x + "px";
  tooltip.style.top  = y + "px";
}

document.addEventListener("mousemove", (e) => {
  if (tooltip.style.display !== "none") positionTooltip(e);
});

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------

const tabBtns  = document.querySelectorAll(".tab-btn");
const panels   = document.querySelectorAll(".panel");

tabBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    tabBtns.forEach(b => b.classList.remove("active"));
    panels.forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("panel-" + btn.dataset.tab).classList.add("active");
  });
});

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

let graphData = null;
let currentWord = null;

fetch(DATA_URL)
  .then(r => {
    if (!r.ok) throw new Error("Could not load " + DATA_URL + " (" + r.status + ")");
    return r.json();
  })
  .then(data => {
    graphData = data;
    buildWordSelector(data.words);
    if (data.words.length > 0) {
      const defaultWord = data.words.find(w => w.writtenForm === "Querdenker") || data.words[0];
      document.getElementById("word-select").value = defaultWord.id;
      selectWord(defaultWord.id);
    }
  })
  .catch(err => {
    console.error(err);
    document.getElementById("timeline-empty").textContent =
      "Error loading data: " + err.message;
    document.getElementById("graph-empty").textContent =
      "Error loading data: " + err.message;
  });

// ---------------------------------------------------------------------------
// Word selector
// ---------------------------------------------------------------------------

function buildWordSelector(words) {
  const sel = document.getElementById("word-select");
  sel.innerHTML = "";

  // Group by language
  const langs = [...new Set(words.map(w => w.language || "?"))].sort(l => l === "en" ? -1 : 1);

  langs.forEach(lang => {
    const group = document.createElement("optgroup");
    group.label = lang === "en" ? "English" : lang === "de" ? "German" : lang;
    words
      .filter(w => (w.language || "?") === lang)
      .forEach(w => {
        const opt = document.createElement("option");
        opt.value = w.id;
        opt.textContent = w.writtenForm + " (" + lang + ")";
        group.appendChild(opt);
      });
    sel.appendChild(group);
  });

  sel.addEventListener("change", () => selectWord(sel.value));
}

function selectWord(id) {
  currentWord = graphData.words.find(w => w.id === id);
  if (!currentWord) return;
  renderTimeline(currentWord);
  renderGraph(currentWord);
}

// ---------------------------------------------------------------------------
// Timeline
// ---------------------------------------------------------------------------

function renderTimeline(word) {
  const wrap = document.getElementById("timeline-svg-wrap");
  const emptyMsg = document.getElementById("timeline-empty");

  // Remove previous SVG
  wrap.querySelectorAll("svg").forEach(el => el.remove());
  emptyMsg.style.display = "none";

  document.getElementById("timeline-heading").textContent =
    "Sense timeline — " + word.writtenForm + " (" + (word.language || "?") + ")";

  const { senses, driftEvents, frequencyObservations } = word;

  if (!senses || senses.length === 0) {
    emptyMsg.textContent = "No senses found for this word.";
    emptyMsg.style.display = "block";
    return;
  }

  // Collect all trigger events referenced by this word's drift events
  const triggerIds = new Set(driftEvents.flatMap(d => d.triggerIds || []));
  const triggers = graphData.triggers.filter(t => triggerIds.has(t.id));

  // Gather all years for the x-axis extent
  const allYears = [
    ...senses.map(s => s.firstAttested).filter(Boolean),
    ...driftEvents.map(d => d.year).filter(Boolean),
    ...triggers.map(t => t.date).filter(Boolean),
    ...frequencyObservations.map(o => o.year).filter(Boolean),
  ];

  if (allYears.length === 0) {
    emptyMsg.textContent = "No year data available for this word.";
    emptyMsg.style.display = "block";
    return;
  }

  const minYear = Math.min(...allYears) - 20;
  const maxYear = Math.max(...allYears) + 30;

  // Layout constants
  const W = Math.max(wrap.clientWidth || 900, 600);
  const MARGIN = { top: 30, right: 40, bottom: 50, left: 20 };
  const SENSE_HEIGHT = 52;
  const SENSE_GAP = 16;
  const SPARKLINE_H = 48;
  const TRIGGER_ZONE_H = 48;

  const nSenses = senses.length;
  const hasSpark = frequencyObservations.length >= 2;
  const SENSES_H = nSenses * SENSE_HEIGHT + (nSenses - 1) * SENSE_GAP;
  const INNER_H = SENSES_H + TRIGGER_ZONE_H + (hasSpark ? SPARKLINE_H + 16 : 0) + 20;
  const H = INNER_H + MARGIN.top + MARGIN.bottom;

  const x = d3.scaleLinear()
    .domain([minYear, maxYear])
    .range([MARGIN.left, W - MARGIN.right]);

  const svg = d3.select(wrap).append("svg")
    .attr("viewBox", `0 0 ${W} ${H}`)
    .attr("width", W)
    .attr("height", H);

  // Defs
  const defs = svg.append("defs");
  defs.append("marker")
    .attr("id", "tl-arrowhead")
    .attr("markerWidth", 8).attr("markerHeight", 6)
    .attr("refX", 8).attr("refY", 3)
    .attr("orient", "auto")
    .append("polygon")
      .attr("points", "0 0, 8 3, 0 6")
      .attr("fill", DRIFT_EDGE_COLOR);

  // Background
  svg.append("rect")
    .attr("width", W).attr("height", H)
    .attr("fill", BG_COLOR);

  const g = svg.append("g")
    .attr("transform", `translate(0,${MARGIN.top})`);

  // X axis
  const axisG = g.append("g")
    .attr("class", "tl-axis")
    .attr("transform", `translate(0,${SENSES_H + TRIGGER_ZONE_H + 10})`);

  axisG.append("line")
    .attr("x1", MARGIN.left).attr("x2", W - MARGIN.right)
    .attr("y1", 0).attr("y2", 0)
    .attr("stroke", "#2e3245").attr("stroke-width", 1);

  const tickCount = Math.min(12, Math.max(4, Math.floor((maxYear - minYear) / 30)));
  const ticks = x.ticks(tickCount);

  ticks.forEach(yr => {
    axisG.append("line")
      .attr("x1", x(yr)).attr("x2", x(yr))
      .attr("y1", -4).attr("y2", 8)
      .attr("stroke", "#2e3245");
    axisG.append("text")
      .attr("x", x(yr)).attr("y", 22)
      .attr("text-anchor", "middle")
      .attr("fill", "#7b82a0")
      .attr("font-size", 11)
      .attr("font-family", "var(--font)")
      .text(yr);
  });

  // Sense y-positions (centre of band)
  const senseY = {};
  senses.forEach((s, i) => {
    senseY[s.id] = i * (SENSE_HEIGHT + SENSE_GAP) + SENSE_HEIGHT / 2;
  });

  // Sense bands
  senses.forEach((s, i) => {
    const cy = senseY[s.id];
    const bandH = SENSE_HEIGHT;
    const y0 = cy - bandH / 2;
    const color = connColor(s.connotation);
    const xStart = s.firstAttested ? x(s.firstAttested) : MARGIN.left + 2;
    const xEnd = W - MARGIN.right;
    const bandW = Math.max(xEnd - xStart, 2);

    // Background band
    g.append("rect")
      .attr("x", xStart)
      .attr("y", y0)
      .attr("width", bandW)
      .attr("height", bandH)
      .attr("rx", 5).attr("ry", 5)
      .attr("fill", color)
      .attr("opacity", 0.08);

    // Left edge line
    g.append("line")
      .attr("x1", xStart).attr("x2", xStart)
      .attr("y1", y0 + 4).attr("y2", y0 + bandH - 4)
      .attr("stroke", color).attr("stroke-width", 2.5)
      .attr("stroke-linecap", "round");

    // Year label
    if (s.firstAttested) {
      g.append("text")
        .attr("x", xStart + 6).attr("y", y0 + 13)
        .attr("fill", color)
        .attr("font-size", 10)
        .attr("font-family", "var(--font)")
        .attr("font-weight", "600")
        .text(s.firstAttested);
    }

    // Gloss (truncated)
    const glossText = s.glossEn || "";
    const maxChars = Math.floor(bandW / 6.5) - 12;
    const gloss = glossText.length > maxChars
      ? glossText.slice(0, maxChars) + "..."
      : glossText;

    g.append("text")
      .attr("x", xStart + 6).attr("y", cy + 5)
      .attr("fill", "#e2e6f3")
      .attr("font-size", 11)
      .attr("font-family", "var(--font)")
      .text(gloss);

    // Connotation tag
    if (s.connotation) {
      const tagX = W - MARGIN.right - 70;
      g.append("rect")
        .attr("x", tagX).attr("y", cy - 9)
        .attr("width", 64).attr("height", 18)
        .attr("rx", 4).attr("fill", color).attr("opacity", 0.18);
      g.append("text")
        .attr("x", tagX + 32).attr("y", cy + 4)
        .attr("text-anchor", "middle")
        .attr("fill", color)
        .attr("font-size", 10)
        .attr("font-weight", "600")
        .attr("font-family", "var(--font)")
        .text(s.connotation);
    }

    // Hover area
    g.append("rect")
      .attr("x", xStart).attr("y", y0)
      .attr("width", bandW).attr("height", bandH)
      .attr("fill", "transparent")
      .attr("cursor", "pointer")
      .on("mouseenter", (event) => {
        const confText = "";
        showTooltip(
          `<strong>${word.writtenForm} &mdash; sense</strong>
           <span class="tt-tag ${(s.connotation || "").toLowerCase()}">${s.connotation || "?"}</span>
           <p>${s.glossEn || "No gloss"}</p>
           <div class="tt-meta">First attested: ${s.firstAttested || "?"}</div>`,
          event
        );
      })
      .on("mouseleave", hideTooltip);
  });

  // Drift event arrows (between senses on the same horizontal plane, drawn as diagonal arcs)
  driftEvents.forEach(de => {
    const fromY = de.senseFromId != null ? senseY[de.senseFromId] : null;
    const toY   = de.senseToId   != null ? senseY[de.senseToId]   : null;
    if (fromY == null || toY == null || de.year == null) return;

    const ax = x(de.year);
    // Arrow from bottom of fromSense to top of toSense (or vice versa)
    const yFrom = fromY + (fromY < toY ? SENSE_HEIGHT / 2 : -SENSE_HEIGHT / 2);
    const yTo   = toY   + (toY < fromY ? SENSE_HEIGHT / 2 : -SENSE_HEIGHT / 2);

    // Curved path
    const mx = ax + 24;
    const my = (yFrom + yTo) / 2;
    const path = `M ${ax} ${yFrom} Q ${mx} ${my} ${ax} ${yTo}`;

    g.append("path")
      .attr("d", path)
      .attr("class", "tl-drift-arrow")
      .attr("stroke", DRIFT_EDGE_COLOR)
      .attr("stroke-width", 1.8)
      .attr("fill", "none")
      .attr("marker-end", "url(#tl-arrowhead)")
      .attr("opacity", de.confidence != null ? Math.max(0.35, de.confidence) : 0.75);

    // Type label
    if (de.driftTypeLabel) {
      g.append("text")
        .attr("x", mx + 4).attr("y", my)
        .attr("fill", DRIFT_EDGE_COLOR)
        .attr("font-size", 9.5)
        .attr("font-family", "var(--font)")
        .attr("dominant-baseline", "middle")
        .text(de.driftTypeLabel);
    }
  });

  // Trigger event markers on timeline (in trigger zone below senses)
  const triggerZoneY = SENSES_H + 4;
  const usedTriggerX = {};  // avoid label overlap

  triggers.forEach(t => {
    if (!t.date) return;
    const tx = x(t.date);

    // Dashed vertical line into sense zone
    g.append("line")
      .attr("x1", tx).attr("x2", tx)
      .attr("y1", 0).attr("y2", SENSES_H)
      .attr("stroke", TRIGGER_COLOR)
      .attr("stroke-width", 1)
      .attr("stroke-dasharray", "3 3")
      .attr("opacity", 0.4);

    // Diamond in trigger zone
    const dy = triggerZoneY + 14;
    const ds = 7;
    g.append("polygon")
      .attr("points", `${tx},${dy - ds} ${tx + ds},${dy} ${tx},${dy + ds} ${tx - ds},${dy}`)
      .attr("fill", TRIGGER_COLOR)
      .attr("opacity", 0.85)
      .attr("cursor", "pointer")
      .on("mouseenter", (event) => {
        showTooltip(
          `<strong>${t.label}</strong>
           <span class="tt-tag trigger">${t.category || "trigger"}</span>
           <p>${t.description || ""}</p>
           <div class="tt-meta">Date: ${t.date || "?"}${t.wikidataSameAs ? " &bull; " + t.wikidataSameAs : ""}</div>`,
          event
        );
      })
      .on("mouseleave", hideTooltip);

    // Label (avoid overlap by offsetting repeated x values)
    let labelX = tx + 9;
    let labelY = triggerZoneY + 10;
    const key = Math.round(tx / 20);
    if (usedTriggerX[key]) {
      labelY += 16;
    }
    usedTriggerX[key] = true;

    const maxLabelChars = 26;
    const shortLabel = t.label.length > maxLabelChars
      ? t.label.slice(0, maxLabelChars) + "..."
      : t.label;

    g.append("text")
      .attr("x", labelX).attr("y", labelY)
      .attr("fill", TRIGGER_COLOR)
      .attr("font-size", 9.5)
      .attr("font-family", "var(--font)")
      .text(shortLabel);
  });

  // Frequency sparkline
  if (hasSpark) {
    const sparkY0 = SENSES_H + TRIGGER_ZONE_H + 18;
    const sparkH  = SPARKLINE_H;

    const freqVals = frequencyObservations.map(o => o.value);
    const minF = Math.min(...freqVals);
    const maxF = Math.max(...freqVals);
    const yScaleSpark = d3.scaleLinear()
      .domain([minF, maxF])
      .range([sparkY0 + sparkH, sparkY0]);

    const line = d3.line()
      .x(o => x(o.year))
      .y(o => yScaleSpark(o.value))
      .curve(d3.curveMonotoneX);

    // Shaded area
    const area = d3.area()
      .x(o => x(o.year))
      .y0(sparkY0 + sparkH)
      .y1(o => yScaleSpark(o.value))
      .curve(d3.curveMonotoneX);

    g.append("path")
      .datum(frequencyObservations)
      .attr("d", area)
      .attr("fill", DRIFT_EDGE_COLOR)
      .attr("opacity", 0.06);

    g.append("path")
      .datum(frequencyObservations)
      .attr("d", line)
      .attr("class", "tl-spark-line");

    g.append("text")
      .attr("x", MARGIN.left + 2).attr("y", sparkY0 - 4)
      .attr("fill", "#7b82a0")
      .attr("font-size", 9.5)
      .attr("font-family", "var(--font)")
      .text("relative frequency (corpus)");

    // Dots
    g.selectAll(".spark-dot")
      .data(frequencyObservations)
      .join("circle")
        .attr("class", "spark-dot")
        .attr("cx", o => x(o.year))
        .attr("cy", o => yScaleSpark(o.value))
        .attr("r", 3)
        .attr("fill", DRIFT_EDGE_COLOR)
        .attr("cursor", "pointer")
        .on("mouseenter", (event, o) => {
          showTooltip(
            `<strong>Frequency: ${o.value}</strong><div class="tt-meta">Year: ${o.year}</div>`,
            event
          );
        })
        .on("mouseleave", hideTooltip);
  }
}

// ---------------------------------------------------------------------------
// Force graph
// ---------------------------------------------------------------------------

function renderGraph(word) {
  const wrap = document.getElementById("graph-svg-wrap");
  const emptyMsg = document.getElementById("graph-empty");

  wrap.querySelectorAll("svg").forEach(el => el.remove());
  emptyMsg.style.display = "none";

  document.getElementById("graph-heading").textContent =
    "Sense / trigger force graph — " + word.writtenForm + " (" + (word.language || "?") + ")";

  const { senses, driftEvents } = word;

  if (!senses || senses.length === 0) {
    emptyMsg.textContent = "No senses found for this word.";
    emptyMsg.style.display = "block";
    return;
  }

  // Collect relevant trigger event ids
  const triggerIds = new Set(driftEvents.flatMap(d => d.triggerIds || []));
  const triggers = graphData.triggers.filter(t => triggerIds.has(t.id));

  // Build nodes
  const nodes = [
    ...senses.map(s => ({
      id: s.id,
      type: "sense",
      label: word.writtenForm + (s.firstAttested ? " (" + s.firstAttested + ")" : ""),
      shortLabel: s.firstAttested ? String(s.firstAttested) : "?",
      gloss: s.glossEn,
      connotation: s.connotation,
      color: connColor(s.connotation),
    })),
    ...triggers.map(t => ({
      id: t.id,
      type: "trigger",
      label: t.label,
      shortLabel: t.date ? String(t.date) : "?",
      gloss: t.description,
      connotation: null,
      color: TRIGGER_COLOR,
      date: t.date,
      category: t.category,
    })),
  ];

  // Build links
  const links = [];

  // Drift event edges (sense-to-sense)
  driftEvents.forEach(de => {
    if (de.senseFromId && de.senseToId) {
      links.push({
        source: de.senseFromId,
        target: de.senseToId,
        type: "drift",
        label: de.driftTypeLabel || "",
        confidence: de.confidence,
      });
    }
  });

  // TriggeredBy edges (drift event -> trigger), represented as sense -> trigger
  driftEvents.forEach(de => {
    (de.triggerIds || []).forEach(tid => {
      // Link from the "to" sense to the trigger for visual clarity
      const anchorId = de.senseToId || de.senseFromId;
      if (anchorId) {
        links.push({
          source: anchorId,
          target: tid,
          type: "trigger",
          label: "",
          confidence: de.confidence,
        });
      }
    });
  });

  const W = Math.max(wrap.clientWidth || 900, 600);
  const H = 520;

  const svg = d3.select(wrap).append("svg")
    .attr("viewBox", `0 0 ${W} ${H}`)
    .attr("width", W)
    .attr("height", H);

  // Background
  svg.append("rect")
    .attr("width", W).attr("height", H)
    .attr("fill", BG_COLOR);

  // Defs: arrowheads
  const defs = svg.append("defs");

  defs.append("marker")
    .attr("id", "g-arrowhead-drift")
    .attr("markerWidth", 8).attr("markerHeight", 6)
    .attr("refX", 20).attr("refY", 3)
    .attr("orient", "auto")
    .append("polygon")
      .attr("points", "0 0, 8 3, 0 6")
      .attr("fill", "#8a94b0");

  defs.append("marker")
    .attr("id", "g-arrowhead-trigger")
    .attr("markerWidth", 8).attr("markerHeight", 6)
    .attr("refX", 20).attr("refY", 3)
    .attr("orient", "auto")
    .append("polygon")
      .attr("points", "0 0, 8 3, 0 6")
      .attr("fill", TRIGGER_COLOR);

  // Build a lookup map for nodes
  const nodeById = {};
  nodes.forEach(n => { nodeById[n.id] = n; });

  // Force simulation
  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links)
      .id(d => d.id)
      .distance(d => d.type === "trigger" ? 180 : 150)
      .strength(d => d.type === "trigger" ? 0.25 : 0.6)
    )
    .force("charge", d3.forceManyBody().strength(-400))
    .force("center", d3.forceCenter(W / 2, H / 2))
    .force("collision", d3.forceCollide(36))
    .alphaDecay(0.025);

  const gContainer = svg.append("g");

  // Zoom/pan
  svg.call(
    d3.zoom()
      .scaleExtent([0.3, 4])
      .on("zoom", (event) => {
        gContainer.attr("transform", event.transform);
      })
  );

  // Edges
  const edgeG = gContainer.append("g").attr("class", "edges");

  const edgePaths = edgeG.selectAll("path")
    .data(links)
    .join("path")
    .attr("class", d => d.type === "trigger" ? "g-trigger-edge" : "g-drift-edge")
    .attr("stroke", d => d.type === "trigger" ? TRIGGER_COLOR : "#8a94b0")
    .attr("stroke-width", d => d.type === "trigger" ? 1.2 : 1.8)
    .attr("stroke-dasharray", d => d.type === "trigger" ? "4 3" : "none")
    .attr("fill", "none")
    .attr("opacity", d => d.confidence != null ? Math.max(0.3, d.confidence * 0.9) : 0.6)
    .attr("marker-end", d => d.type === "trigger" ? "url(#g-arrowhead-trigger)" : "url(#g-arrowhead-drift)");

  // Edge labels
  const edgeLabels = edgeG.selectAll("text")
    .data(links.filter(l => l.type === "drift" && l.label))
    .join("text")
    .attr("class", "g-drift-label")
    .text(d => d.label);

  // Nodes
  const nodeG = gContainer.append("g").attr("class", "nodes");

  const nodeElems = nodeG.selectAll("g")
    .data(nodes)
    .join("g")
    .attr("class", d => "g-" + d.type + "-node")
    .call(
      d3.drag()
        .on("start", (event, d) => {
          if (!event.active) sim.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x; d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) sim.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
    )
    .on("mouseenter", (event, d) => {
      let html;
      if (d.type === "sense") {
        const tagClass = (d.connotation || "").toLowerCase();
        html = `<strong>${word.writtenForm}</strong>
          <span class="tt-tag ${tagClass}">${d.connotation || "?"}</span>
          <p>${d.gloss || "No gloss"}</p>
          <div class="tt-meta">First attested: ${d.shortLabel}</div>`;
      } else {
        html = `<strong>${d.label}</strong>
          <span class="tt-tag trigger">${d.category || "trigger"}</span>
          <p>${d.gloss || ""}</p>
          <div class="tt-meta">Date: ${d.date || "?"}</div>`;
      }
      showTooltip(html, event);
    })
    .on("mouseleave", hideTooltip);

  // Sense nodes: circles
  nodeElems.filter(d => d.type === "sense")
    .append("circle")
    .attr("r", 22)
    .attr("fill", d => d.color)
    .attr("opacity", 0.18)
    .attr("stroke", d => d.color)
    .attr("stroke-width", 2);

  // Trigger nodes: diamonds
  const DSIZE = 20;
  nodeElems.filter(d => d.type === "trigger")
    .append("polygon")
    .attr("points", `0,${-DSIZE} ${DSIZE},0 0,${DSIZE} ${-DSIZE},0`)
    .attr("fill", d => d.color)
    .attr("opacity", 0.18)
    .attr("stroke", d => d.color)
    .attr("stroke-width", 2);

  // Node labels
  nodeElems.append("text")
    .attr("class", "g-node-label")
    .attr("text-anchor", "middle")
    .attr("dominant-baseline", "middle")
    .attr("font-size", 10)
    .attr("font-family", "var(--font)")
    .text(d => d.shortLabel);

  // Word label under each sense node
  nodeElems.filter(d => d.type === "sense")
    .append("text")
    .attr("text-anchor", "middle")
    .attr("y", 30)
    .attr("font-size", 9)
    .attr("font-family", "var(--font)")
    .attr("fill", "#7b82a0")
    .text(d => {
      const conn = d.connotation ? d.connotation.slice(0, 3) : "?";
      return conn;
    });

  // Trigger label below diamond
  nodeElems.filter(d => d.type === "trigger")
    .append("text")
    .attr("text-anchor", "middle")
    .attr("y", DSIZE + 14)
    .attr("font-size", 9)
    .attr("font-family", "var(--font)")
    .attr("fill", TRIGGER_COLOR)
    .text(d => {
      const s = d.label || "";
      return s.length > 18 ? s.slice(0, 18) + "..." : s;
    });

  // Simulation tick
  sim.on("tick", () => {
    edgePaths.attr("d", d => {
      const sx = d.source.x;
      const sy = d.source.y;
      const tx = d.target.x;
      const ty = d.target.y;
      // Slightly curved arc
      const dx = tx - sx;
      const dy = ty - sy;
      const dr = Math.sqrt(dx * dx + dy * dy) * 1.4;
      return `M ${sx} ${sy} A ${dr} ${dr} 0 0 1 ${tx} ${ty}`;
    });

    edgeLabels
      .attr("x", d => (d.source.x + d.target.x) / 2)
      .attr("y", d => (d.source.y + d.target.y) / 2 - 6);

    nodeElems.attr("transform", d => `translate(${d.x},${d.y})`);
  });
}

// ---------------------------------------------------------------------------
// Resize: re-render on significant window resize
// ---------------------------------------------------------------------------

let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (currentWord) {
      renderTimeline(currentWord);
      renderGraph(currentWord);
    }
  }, 250);
});
