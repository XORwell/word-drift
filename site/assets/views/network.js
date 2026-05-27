// WORD-DRIFT view module: Network
// Force-directed graph revealing structure across the trigger/word corpus.
// Two modes:
//   "trigger-words"  bipartite graph: trigger nodes (sized by wordCount, coloured
//                    by category) linked to the words they reframed.
//   "co-occurrence"  trigger-trigger graph: two triggers are linked when they
//                    share a category AND sit in the same era (decade bucket).
// Contract: see assets/views/API.md.
(function () {
  "use strict";
  if (!window.WD || typeof window.WD.registerView !== "function") {
    console.warn("network.js: window.WD not ready");
    return;
  }

  var d3 = window.d3;

  // --- theme-aware colour helpers -------------------------------------------
  // Colours are read fresh per render so the network re-themes when the user
  // flips light/dark (the host re-fires onActivate on toggle). The categorical
  // palette is built from the drift-type CSS vars (theme-tuned, AA-legible).
  function cssVar(name, fallback) {
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return v || fallback;
    } catch (e) { return fallback; }
  }

  // Categories are free strings on triggers ("political", "technological",
  // "cultural / artistic", ...). Normalise case/whitespace, map to a palette.
  function catPalette() {
    return [
      cssVar("--dt-broadening", "#4338ca"),     // indigo
      cssVar("--dt-metaphorization", "#b26a00"), // gold
      cssVar("--dt-amelioration", "#15803d"),    // green
      cssVar("--dt-reversal", "#be185d"),        // magenta
      cssVar("--cause-t2", "#0369a1"),           // sky
      cssVar("--cause-t4", "#e11d48"),           // rose
      cssVar("--dt-narrowing", "#7c3aed"),       // violet
      cssVar("--dt-metonymization", "#c2410c"),  // orange
      cssVar("--dt-reappropriation", "#0f766e"), // teal
      cssVar("--dt-pejoration", "#dc2626"),      // red
    ];
  }
  function catUnknown() { return cssVar("--text-faint", "#73788c"); }

  function normCat(c) {
    if (!c) return "uncategorised";
    return String(c).trim().toLowerCase();
  }

  // Build a deterministic category -> colour map from the live trigger list,
  // ordered by frequency so the biggest categories get the most distinct hues.
  function buildCatColors(triggers) {
    var palette = catPalette();
    var unknown = catUnknown();
    var freq = {};
    triggers.forEach(function (t) {
      var k = normCat(t.category);
      freq[k] = (freq[k] || 0) + 1;
    });
    var sorted = Object.keys(freq).sort(function (a, b) { return freq[b] - freq[a]; });
    var map = {};
    sorted.forEach(function (k, i) {
      map[k] = (k === "uncategorised") ? unknown : (palette[i] || unknown);
    });
    return map;
  }

  // Pretty label for a normalised category key.
  function prettyCat(k) {
    if (!k || k === "uncategorised") return "Uncategorised";
    return k.replace(/\b\w/g, function (m) { return m.toUpperCase(); });
  }

  // --- shared tooltip (reuse the core's #exp-tooltip element) ---------------
  function tipEl() { return document.getElementById("exp-tooltip"); }
  function showTip(html, event) {
    var el = tipEl();
    if (!el) return;
    el.innerHTML = html;
    el.style.display = "block";
    placeTip(event);
  }
  function placeTip(event) {
    var el = tipEl();
    if (!el) return;
    var pad = 14;
    var x = event.clientX + pad;
    var y = event.clientY + pad;
    var w = el.offsetWidth;
    var h = el.offsetHeight;
    if (x + w > window.innerWidth - 8) x = event.clientX - w - pad;
    if (y + h > window.innerHeight - 8) y = event.clientY - h - pad;
    el.style.left = x + "px";
    el.style.top = y + "px";
  }
  function hideTip() {
    var el = tipEl();
    if (el) el.style.display = "none";
  }

  var esc = WD.escHtml;

  // --- view state (persists between activations) ----------------------------
  var state = {
    mode: "trigger-words", // or "co-occurrence"
    topN: 40,              // how many triggers to show, by impact
  };

  // --- data builders --------------------------------------------------------

  // Rank triggers by impact (wordCount desc, then year). triggerImpact entries
  // carry {trigger, label, year, category, wordCount, words}.
  function rankedImpact() {
    return (WD.triggerImpact || [])
      .slice()
      .sort(function (a, b) {
        if (b.wordCount !== a.wordCount) return b.wordCount - a.wordCount;
        return (a.year == null ? 1e9 : a.year) - (b.year == null ? 1e9 : b.year);
      });
  }

  // Index light words by writtenForm for navigation (first match wins).
  var _wordByForm = null;
  function wordByForm(form) {
    if (!_wordByForm) {
      _wordByForm = {};
      (WD.words || []).forEach(function (w) {
        if (w.writtenForm && !(w.writtenForm in _wordByForm)) _wordByForm[w.writtenForm] = w;
      });
    }
    return _wordByForm[form] || null;
  }

  // Build trigger -> words bipartite graph from the top-N impact triggers.
  function buildBipartite(catColors) {
    var imp = rankedImpact().filter(function (t) { return t.wordCount > 0; });
    var chosen = imp.slice(0, state.topN);

    var nodes = [];
    var links = [];
    var wordNodes = {}; // writtenForm -> node

    chosen.forEach(function (t) {
      var ck = normCat(t.category);
      nodes.push({
        id: "T:" + t.trigger,
        kind: "trigger",
        triggerId: t.trigger,
        label: t.label,
        year: t.year,
        catKey: ck,
        wordCount: t.wordCount,
        color: catColors[ck] || CAT_UNKNOWN,
        r: 7 + Math.sqrt(t.wordCount) * 6,
      });
      (t.words || []).forEach(function (form) {
        var wid = "W:" + form;
        if (!wordNodes[form]) {
          var w = wordByForm(form);
          var wn = {
            id: wid,
            kind: "word",
            form: form,
            wordRef: w,        // light word or null
            color: cssVar("--neutral", "#6b7280"),
            r: 5,
            deg: 0,
          };
          wordNodes[form] = wn;
          nodes.push(wn);
        }
        wordNodes[form].deg += 1;
        links.push({ source: "T:" + t.trigger, target: wid });
      });
    });

    // Slightly grow words shared by multiple triggers (real cross-links).
    Object.keys(wordNodes).forEach(function (f) {
      var n = wordNodes[f];
      if (n.deg > 1) n.r = 5 + (n.deg - 1) * 2.5;
    });

    return { nodes: nodes, links: links, triggerCount: chosen.length, wordCount: Object.keys(wordNodes).length };
  }

  // Build trigger -> trigger co-occurrence graph: link two triggers if they
  // share a category AND fall in the same decade. To stay legible we restrict
  // to the top-N impact triggers as well.
  function buildCoOccurrence(catColors) {
    var imp = rankedImpact().slice(0, state.topN);
    var nodes = imp.map(function (t) {
      var ck = normCat(t.category);
      return {
        id: "T:" + t.trigger,
        kind: "trigger",
        triggerId: t.trigger,
        label: t.label,
        year: t.year,
        catKey: ck,
        wordCount: t.wordCount,
        color: catColors[ck] || CAT_UNKNOWN,
        r: 7 + Math.sqrt(Math.max(1, t.wordCount)) * 5,
      };
    });

    function decade(y) { return (y == null) ? null : Math.floor(y / 10) * 10; }

    var links = [];
    for (var i = 0; i < nodes.length; i++) {
      for (var j = i + 1; j < nodes.length; j++) {
        var a = nodes[i], b = nodes[j];
        if (a.catKey === b.catKey && a.catKey !== "uncategorised") {
          var da = decade(a.year), db = decade(b.year);
          if (da != null && da === db) {
            links.push({ source: a.id, target: b.id, cat: a.catKey });
          }
        }
      }
    }
    return { nodes: nodes, links: links, triggerCount: nodes.length, wordCount: 0 };
  }

  // --- rendering ------------------------------------------------------------

  function render(panelEl) {
    panelEl.innerHTML = "";
    hideTip();

    var triggers = WD.triggers || [];
    if (!triggers.length || !(WD.triggerImpact || []).length) {
      var empty = document.createElement("p");
      empty.className = "empty-msg";
      empty.textContent = "No trigger data available to draw a network.";
      panelEl.appendChild(empty);
      return;
    }

    var catColors = buildCatColors(triggers);
    // Theme-aware colours, read fresh each render (re-fires on theme toggle).
    var CAT_UNKNOWN = catUnknown();
    var WORD_NODE_COLOR = cssVar("--neutral", "#6b7280");
    var WORD_LABEL_COLOR = cssVar("--text-sub", "#5a5f72");
    var EDGE_COLOR = (WD.colors && WD.colors.DRIFT_EDGE_COLOR) || cssVar("--accent", "#4338ca");

    // ---- controls -----------------------------------------------------------
    var controls = document.createElement("div");
    controls.style.cssText = "display:flex;flex-wrap:wrap;gap:1rem;align-items:center;margin-bottom:0.75rem;";

    // mode toggle
    var modeWrap = document.createElement("div");
    modeWrap.style.cssText = "display:flex;align-items:center;gap:0.4rem;font-size:0.8rem;color:var(--text-sub);";
    var modeLabel = document.createElement("span");
    modeLabel.textContent = "Graph:";
    var modeSel = document.createElement("select");
    modeSel.className = "wd-icon-btn";
    modeSel.style.cssText = "padding:0.3rem 0.5rem;";
    [["trigger-words", "Triggers → words"], ["co-occurrence", "Trigger co-occurrence"]].forEach(function (opt) {
      var o = document.createElement("option");
      o.value = opt[0];
      o.textContent = opt[1];
      if (opt[0] === state.mode) o.selected = true;
      modeSel.appendChild(o);
    });
    modeSel.addEventListener("change", function () {
      state.mode = modeSel.value;
      render(panelEl);
    });
    modeWrap.appendChild(modeLabel);
    modeWrap.appendChild(modeSel);

    // top-N control
    var nWrap = document.createElement("div");
    nWrap.style.cssText = "display:flex;align-items:center;gap:0.4rem;font-size:0.8rem;color:var(--text-sub);";
    var nLabel = document.createElement("span");
    nLabel.textContent = "Top triggers by impact:";
    var nSel = document.createElement("select");
    nSel.className = "wd-icon-btn";
    nSel.style.cssText = "padding:0.3rem 0.5rem;";
    [20, 40, 80, 150, 302].forEach(function (n) {
      var o = document.createElement("option");
      o.value = String(n);
      o.textContent = (n >= 302) ? "All (302)" : String(n);
      if (n === state.topN) o.selected = true;
      nSel.appendChild(o);
    });
    nSel.addEventListener("change", function () {
      state.topN = parseInt(nSel.value, 10) || 40;
      render(panelEl);
    });
    nWrap.appendChild(nLabel);
    nWrap.appendChild(nSel);

    controls.appendChild(modeWrap);
    controls.appendChild(nWrap);
    panelEl.appendChild(controls);

    // ---- build graph data ---------------------------------------------------
    var g = (state.mode === "co-occurrence")
      ? buildCoOccurrence(catColors)
      : buildBipartite(catColors);

    // ---- caption / counts ---------------------------------------------------
    var caption = document.createElement("p");
    caption.style.cssText = "font-size:0.78rem;color:var(--text-faint);margin:0 0 0.6rem;";
    if (state.mode === "co-occurrence") {
      caption.textContent = g.triggerCount + " triggers, " + g.links.length +
        " co-occurrence links (shared category + same decade).";
    } else {
      caption.textContent = g.triggerCount + " triggers, " + g.wordCount + " words, " +
        g.links.length + " reframing links.";
    }
    panelEl.appendChild(caption);

    if (!g.nodes.length) {
      var e2 = document.createElement("p");
      e2.className = "empty-msg";
      e2.textContent = "No nodes match the current filter. Try increasing the trigger count.";
      panelEl.appendChild(e2);
      return;
    }

    // ---- legend -------------------------------------------------------------
    var legend = document.createElement("div");
    legend.className = "legend-row";
    legend.style.cssText = "margin-bottom:0.6rem;";
    // categories present in this graph
    var present = {};
    g.nodes.forEach(function (n) { if (n.kind === "trigger") present[n.catKey] = true; });
    Object.keys(present).sort().forEach(function (ck) {
      var item = document.createElement("div");
      item.className = "legend-item";
      var sw = document.createElement("div");
      sw.className = "legend-swatch circle";
      sw.style.background = catColors[ck] || CAT_UNKNOWN;
      item.appendChild(sw);
      item.appendChild(document.createTextNode(prettyCat(ck)));
      legend.appendChild(item);
    });
    if (state.mode === "trigger-words") {
      var witem = document.createElement("div");
      witem.className = "legend-item";
      var wsw = document.createElement("div");
      wsw.className = "legend-swatch circle";
      wsw.style.background = WORD_NODE_COLOR;
      witem.appendChild(wsw);
      witem.appendChild(document.createTextNode("Word (reframed)"));
      legend.appendChild(witem);
    }
    var hint = document.createElement("div");
    hint.className = "legend-item";
    hint.style.color = "var(--text-faint)";
    hint.textContent = (state.mode === "trigger-words")
      ? "Trigger size = words reframed. Click to open."
      : "Trigger size = impact. Click to open.";
    legend.appendChild(hint);
    panelEl.appendChild(legend);

    // ---- svg ----------------------------------------------------------------
    var W = Math.max(panelEl.clientWidth || 860, 480);
    var H = 540;
    var BG = (WD.colors && WD.colors.BG_COLOR) || cssVar("--bg-card", "#ffffff");

    var svg = d3.select(panelEl).append("svg")
      .attr("viewBox", "0 0 " + W + " " + H)
      .attr("width", W).attr("height", H)
      .attr("role", "img")
      .attr("aria-label", "Trigger network force-directed graph")
      .style("max-width", "100%")
      .style("border", "1px solid var(--border)")
      .style("border-radius", "8px")
      .style("background", BG);

    svg.append("rect").attr("width", W).attr("height", H).attr("fill", BG);

    var gZoom = svg.append("g");
    svg.call(d3.zoom().scaleExtent([0.3, 5]).on("zoom", function (event) {
      gZoom.attr("transform", event.transform);
    }));

    var edgeG = gZoom.append("g");
    var nodeG = gZoom.append("g");

    // ---- simulation ---------------------------------------------------------
    var linkDist = (state.mode === "co-occurrence") ? 70 : 60;
    var sim = d3.forceSimulation(g.nodes)
      .force("link", d3.forceLink(g.links).id(function (d) { return d.id; })
        .distance(linkDist).strength(state.mode === "co-occurrence" ? 0.15 : 0.4))
      .force("charge", d3.forceManyBody().strength(state.mode === "co-occurrence" ? -120 : -160))
      .force("center", d3.forceCenter(W / 2, H / 2))
      .force("collision", d3.forceCollide(function (d) { return d.r + 4; }))
      .alphaDecay(0.028);

    var reduced = !!WD.prefersReducedMotion;
    if (reduced) {
      sim.stop();
      var ticks = Math.ceil(Math.log(sim.alphaMin()) / Math.log(1 - sim.alphaDecay()));
      for (var i = 0; i < ticks; i++) sim.tick();
    }

    // ---- edges --------------------------------------------------------------
    var edges = edgeG.selectAll("line").data(g.links).join("line")
      .attr("stroke", function (d) {
        return (state.mode === "co-occurrence" && d.cat)
          ? (catColors[d.cat] || CAT_UNKNOWN)
          : EDGE_COLOR;
      })
      .attr("stroke-width", state.mode === "co-occurrence" ? 1 : 1.4)
      .attr("stroke-opacity", state.mode === "co-occurrence" ? 0.28 : 0.45);

    // ---- nodes --------------------------------------------------------------
    var nodeSel = nodeG.selectAll("g").data(g.nodes).join("g")
      .attr("cursor", "pointer")
      .call(d3.drag()
        .on("start", function (event, d) {
          if (!reduced && !event.active) sim.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on("drag", function (event, d) { d.fx = event.x; d.fy = event.y; })
        .on("end", function (event, d) {
          if (!reduced && !event.active) sim.alphaTarget(0);
          d.fx = null; d.fy = null;
        }));

    nodeSel.append("circle")
      .attr("r", function (d) { return d.r; })
      .attr("fill", function (d) { return d.color; })
      .attr("fill-opacity", function (d) { return d.kind === "trigger" ? 0.85 : 0.55; })
      .attr("stroke", function (d) { return d.color; })
      .attr("stroke-width", function (d) { return d.kind === "trigger" ? 1.5 : 1; })
      .attr("stroke-opacity", 0.9);

    // word labels (small, only for words in bipartite mode so the canvas stays readable)
    nodeSel.filter(function (d) { return d.kind === "word"; }).append("text")
      .attr("text-anchor", "middle")
      .attr("dy", function (d) { return d.r + 10; })
      .attr("font-size", 9)
      .attr("font-family", "Inter, sans-serif")
      .attr("fill", WORD_LABEL_COLOR)
      .attr("pointer-events", "none")
      .text(function (d) { return d.form.length > 16 ? d.form.slice(0, 16) + "…" : d.form; });

    // trigger labels (only when few enough to be legible)
    if (g.triggerCount <= 50) {
      nodeSel.filter(function (d) { return d.kind === "trigger"; }).append("text")
        .attr("text-anchor", "middle")
        .attr("dy", function (d) { return d.r + 11; })
        .attr("font-size", 9)
        .attr("font-family", "Inter, sans-serif")
        .attr("fill", function (d) { return d.color; })
        .attr("pointer-events", "none")
        .text(function (d) {
          var s = d.label || "";
          return s.length > 22 ? s.slice(0, 22) + "…" : s;
        });
    }

    // ---- interactions: tooltip, click, keyboard -----------------------------
    nodeSel
      .on("mouseenter", function (event, d) {
        var html;
        if (d.kind === "trigger") {
          html = "<strong>" + esc(d.label) + "</strong>" +
            '<p class="tt-sub">' + esc(prettyCat(d.catKey)) +
            " &bull; " + esc(WD.fmtYear(d.year)) +
            " &bull; " + d.wordCount + (d.wordCount === 1 ? " word" : " words") + "</p>";
        } else {
          var deg = d.deg || 1;
          html = "<strong>" + esc(d.form) + "</strong>" +
            '<p class="tt-sub">Reframed by ' + deg + (deg === 1 ? " trigger" : " triggers") +
            (d.wordRef ? " &bull; click to open" : "") + "</p>";
        }
        showTip(html, event);
      })
      .on("mousemove", function (event) { placeTip(event); })
      .on("mouseleave", hideTip);

    nodeSel.each(function (d) {
      var self = this;
      var act = function () {
        hideTip();
        if (d.kind === "trigger") {
          WD.showTrigger(d.triggerId);
        } else if (d.wordRef) {
          WD.openWord(d.wordRef);
        }
      };
      // makeActivatable adds role=button, tabindex, click + Enter/Space.
      // For words with no resolvable light word, still make triggers/words
      // focusable but only wire activation when it does something.
      if (d.kind === "trigger" || d.wordRef) {
        WD.makeActivatable(self, act);
      }
      // accessible label
      if (d.kind === "trigger") {
        self.setAttribute("aria-label", "Trigger: " + (d.label || "") + ", " + d.wordCount + " words");
      } else {
        self.setAttribute("aria-label", "Word: " + d.form);
      }
    });

    // ---- tick ---------------------------------------------------------------
    function ticked() {
      edges
        .attr("x1", function (d) { return d.source.x; })
        .attr("y1", function (d) { return d.source.y; })
        .attr("x2", function (d) { return d.target.x; })
        .attr("y2", function (d) { return d.target.y; });
      nodeSel.attr("transform", function (d) { return "translate(" + d.x + "," + d.y + ")"; });
    }

    if (reduced) {
      ticked(); // paint the converged layout once, no animation
    } else {
      sim.on("tick", ticked);
    }

    // clean up the simulation if the panel gets torn down / re-rendered
    panelEl._wdNetworkStop = function () { sim.stop(); };
  }

  WD.registerView("network", {
    label: "Network",
    panelId: "panel-network",
    onActivate: function (panelEl) {
      if (panelEl._wdNetworkStop) {
        try { panelEl._wdNetworkStop(); } catch (e) { /* ignore */ }
      }
      render(panelEl);
    },
  });
})();
