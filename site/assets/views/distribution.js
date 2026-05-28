// WORD-DRIFT 3.0 — Distribution view (M4)
//
// Multi-group meaning distribution for one word over time.
//
// Design language (binding): linguistic atlases, scientific observatories,
// archival editorial graphics. No SaaS-dashboard aesthetic, no animated
// gradients, no diverging cool/warm for value judgements. Sense identity
// gets one stable hue across all sub-views; group identity is encoded by
// stroke + column position, not by colour, so the same sense reads the same
// way regardless of which group is foregrounded.
//
// Renders three coordinated panels:
//   1. Metric strip — Entropy, Fragmentation, Max group divergence over time
//      (sparklines with stable y-axis bands).
//   2. Stacked sense proportions per group (small multiples: one column per
//      group, one row per year, area encoding weight share).
//   3. A glanceable summary card: current word, n_groups, n_senses,
//      most-recent fragmentation value with a one-line interpretation.
//
// Data source: GET /graph-distribution.json (a 3.0 endpoint, served alongside
// the 2.x /graph-core.json). Falls back to a "no multi-group data" message
// for words without MeaningAttribution records.
//
// Contract: site/assets/views/API.md.

(function () {
  "use strict";
  if (!window.WD || typeof window.WD.registerView !== "function") {
    console.warn("distribution.js: window.WD not ready");
    return;
  }

  // ---- One-shot fetch of the distribution document --------------------------
  // Cached on first request; the doc is small (one record per attested word).

  var _docPromise = null;
  function loadDoc() {
    if (_docPromise) return _docPromise;
    _docPromise = fetch("graph-distribution.json", { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .catch(function (e) {
        _docPromise = null;
        console.error("distribution: fetch failed", e);
        return null;
      });
    return _docPromise;
  }

  // ---- Current word: prefer URL param, then localStorage, then first word --

  function currentWordIri(doc) {
    var qs = new URLSearchParams(window.location.search);
    var fromUrl = qs.get("word");
    if (fromUrl) {
      // Treat ?word=Querdenker or ?word=https://w3id.org/word-drift/... both.
      for (var iri in doc.words) {
        if (iri === fromUrl || doc.words[iri].writtenForm === fromUrl) {
          return iri;
        }
      }
    }
    // Try localStorage (same key the main app uses).
    try {
      var ls = window.localStorage.getItem("wd:explore:word");
      if (ls && doc.words[ls]) return ls;
    } catch (_) { /* ignore */ }
    // Fall back to the first word with any attribution (typically Querdenker).
    var keys = Object.keys(doc.words);
    return keys.length ? keys[0] : null;
  }

  // ---- Visual palette: archival, calm ---------------------------------------
  // Sense hues drawn from a slightly desaturated curated palette inspired by
  // 19th-century atlas plates. Stable across the view; assigned by insertion
  // order so the same sense IRI always reads as the same hue.

  var SENSE_PALETTE = [
    "#7b8a5e", // moss
    "#a86c4d", // burnt sienna
    "#5b6c87", // slate blue
    "#b9985a", // ochre
    "#6f5b8c", // muted plum
    "#88787b", // taupe
  ];

  function senseColors(senses) {
    var out = {};
    senses.forEach(function (s, i) { out[s.id] = SENSE_PALETTE[i % SENSE_PALETTE.length]; });
    return out;
  }

  // ---- Layout primitives ----------------------------------------------------

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "style" && typeof attrs[k] === "object") {
        Object.assign(n.style, attrs[k]);
      } else if (k === "html") {
        n.innerHTML = attrs[k];
      } else if (k === "text") {
        n.textContent = attrs[k];
      } else {
        n.setAttribute(k, attrs[k]);
      }
    });
    (children || []).forEach(function (c) {
      if (c == null) return;
      if (typeof c === "string") n.appendChild(document.createTextNode(c));
      else n.appendChild(c);
    });
    return n;
  }

  // Word picker — a tiny dropdown of all attested words. Updates the URL
  // without reloading so the back button stays useful.
  function buildWordPicker(doc, currentIri, onChange) {
    var sel = el("select", { class: "wd-dist-word-picker", "aria-label": "Word" });
    var iris = Object.keys(doc.words).sort(function (a, b) {
      return doc.words[a].writtenForm.localeCompare(doc.words[b].writtenForm);
    });
    iris.forEach(function (iri) {
      var w = doc.words[iri];
      var opt = el("option", { value: iri, text: w.writtenForm });
      if (iri === currentIri) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", function () { onChange(sel.value); });
    return sel;
  }

  // ---- Summary card ---------------------------------------------------------

  function renderSummary(word) {
    var metrics = word.metrics || [];
    var latest = metrics.length ? metrics[metrics.length - 1] : null;
    var nGroups = (word.groups || []).length;
    var nSenses = (word.senses || []).length;
    var lines = [];
    lines.push(
      el("div", { class: "wd-dist-card-title" }, [
        "Distribution snapshot: ",
        el("strong", { text: word.writtenForm }),
      ])
    );
    if (latest) {
      var frag = latest.fragmentation == null ? "—" : latest.fragmentation.toFixed(3);
      var ent = latest.entropy == null ? "—" : latest.entropy.toFixed(3);
      var div = latest.divergence_max == null ? "—" : latest.divergence_max.toFixed(3);
      lines.push(el("dl", { class: "wd-dist-card-dl" }, [
        el("dt", { text: "Year" }), el("dd", { text: String(latest.year) }),
        el("dt", { text: "Groups attested" }), el("dd", { text: String(nGroups) }),
        el("dt", { text: "Senses attested" }), el("dd", { text: String(nSenses) }),
        el("dt", { text: "Entropy (bits)" }), el("dd", { text: ent }),
        el("dt", { text: "Fragmentation" }), el("dd", { text: frag }),
        el("dt", { text: "Max group divergence" }), el("dd", { text: div }),
      ]));
      // Interpretation line (no melodrama; one descriptive sentence).
      var interp = "";
      if (latest.divergence_max != null && latest.divergence_max > 0.8) {
        interp = "Groups attest near-disjoint readings; the lexical form is shared, the meaning is not.";
      } else if (latest.divergence_max != null && latest.divergence_max > 0.3) {
        interp = "Groups overlap on some senses but a substantive split is present.";
      } else if (latest.entropy != null && latest.entropy < 0.1) {
        interp = "Distribution is concentrated on one sense across groups.";
      } else {
        interp = "Distribution is mixed; no single group disagreement dominates.";
      }
      lines.push(el("p", { class: "wd-dist-card-interp", text: interp }));
    } else {
      lines.push(el("p", { class: "wd-dist-card-interp", text: "No multi-group data for this word yet." }));
    }
    return el("div", { class: "wd-dist-card" }, lines);
  }

  // ---- Metric sparklines (Entropy / Fragmentation / Max divergence) --------

  function sparkline(metrics, accessor, ylabel, ymax) {
    var w = 360, h = 80, m = { t: 14, r: 8, b: 22, l: 36 };
    var iw = w - m.l - m.r, ih = h - m.t - m.b;
    var svgNS = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    svg.setAttribute("class", "wd-dist-spark");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", ylabel + " over time");

    var pts = metrics
      .map(function (r) { return { x: r.year, y: accessor(r) }; })
      .filter(function (p) { return p.y != null; });

    if (pts.length === 0) {
      var txt = document.createElementNS(svgNS, "text");
      txt.setAttribute("x", w / 2);
      txt.setAttribute("y", h / 2 + 4);
      txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("class", "wd-dist-spark-empty");
      txt.textContent = "no data";
      svg.appendChild(txt);
      return svg;
    }

    var xs = pts.map(function (p) { return p.x; });
    var xMin = Math.min.apply(null, xs), xMax = Math.max.apply(null, xs);
    if (xMin === xMax) { xMin -= 1; xMax += 1; }
    var yMax = ymax != null ? ymax : Math.max(1, Math.max.apply(null, pts.map(function (p) { return p.y; })));

    function px(x) { return m.l + ((x - xMin) / (xMax - xMin)) * iw; }
    function py(y) { return m.t + ih - (y / yMax) * ih; }

    // Axis lines: bottom + 0 baseline
    var axisColor = "#7d7568";
    var axis = document.createElementNS(svgNS, "line");
    axis.setAttribute("x1", m.l); axis.setAttribute("x2", m.l + iw);
    axis.setAttribute("y1", m.t + ih); axis.setAttribute("y2", m.t + ih);
    axis.setAttribute("stroke", axisColor); axis.setAttribute("stroke-width", "1");
    svg.appendChild(axis);

    // y label
    var ylab = document.createElementNS(svgNS, "text");
    ylab.setAttribute("x", 4); ylab.setAttribute("y", m.t + 6);
    ylab.setAttribute("class", "wd-dist-spark-label");
    ylab.textContent = ylabel;
    svg.appendChild(ylab);

    var yMaxLabel = document.createElementNS(svgNS, "text");
    yMaxLabel.setAttribute("x", 4); yMaxLabel.setAttribute("y", m.t + 6 + 14);
    yMaxLabel.setAttribute("class", "wd-dist-spark-axis");
    yMaxLabel.textContent = "max " + yMax.toFixed(2);
    svg.appendChild(yMaxLabel);

    // Year ticks: first + last
    [xMin, xMax].forEach(function (x) {
      var t = document.createElementNS(svgNS, "text");
      t.setAttribute("x", px(x)); t.setAttribute("y", h - 6);
      t.setAttribute("class", "wd-dist-spark-axis");
      t.setAttribute("text-anchor", "middle");
      t.textContent = String(x);
      svg.appendChild(t);
    });

    // Path
    var d = pts
      .sort(function (a, b) { return a.x - b.x; })
      .map(function (p, i) { return (i === 0 ? "M" : "L") + px(p.x).toFixed(1) + " " + py(p.y).toFixed(1); })
      .join(" ");
    var path = document.createElementNS(svgNS, "path");
    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "#5b6c87");
    path.setAttribute("stroke-width", "1.6");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    svg.appendChild(path);

    // Dots
    pts.forEach(function (p) {
      var c = document.createElementNS(svgNS, "circle");
      c.setAttribute("cx", px(p.x).toFixed(1));
      c.setAttribute("cy", py(p.y).toFixed(1));
      c.setAttribute("r", "2.4");
      c.setAttribute("fill", "#3a3530");
      svg.appendChild(c);
    });

    return svg;
  }

  // ---- Stacked sense proportions per group (small multiples) ---------------
  // Each group gets its own narrow column; each year is a horizontal row.
  // Within a (group, year) cell, sense weights are stacked horizontally.
  // The same sense always has the same hue. Groups with no data at a year
  // show a hatched empty cell so absence reads differently from "zero".

  function renderSmallMultiples(word) {
    var senses = word.senses || [];
    var groups = word.groups || [];
    var attrs = word.attributions || [];
    if (!senses.length || !groups.length) {
      return el("p", { class: "empty-msg", text: "No multi-group data for this word." });
    }

    var colorBySense = senseColors(senses);
    var glossById = {};
    senses.forEach(function (s) { glossById[s.id] = s.gloss || "(no gloss)"; });
    var labelByGroup = {};
    var kindByGroup = {};
    groups.forEach(function (g) {
      labelByGroup[g.id] = g.label || g.id;
      kindByGroup[g.id] = g.kind || "";
    });

    // Index attributions by (year, group) -> [{sense, weight}]
    var years = Array.from(new Set(attrs.map(function (a) { return a.year; }).filter(function (y) { return y != null; }))).sort(function (a, b) { return a - b; });
    var byCell = {};
    attrs.forEach(function (a) {
      if (a.year == null) return;
      var key = a.year + "|" + a.group;
      (byCell[key] = byCell[key] || []).push(a);
    });

    // Container: header row + one row per year. Tell the grid how many
    // group columns to expect so the small-multiples align.
    var container = el("div", { class: "wd-dist-sm" });
    container.style.setProperty("--n-groups", String(groups.length));

    // Header: group labels
    var header = el("div", { class: "wd-dist-sm-row wd-dist-sm-head" });
    header.appendChild(el("div", { class: "wd-dist-sm-yearcol", text: "" }));
    groups.forEach(function (g) {
      var kind = kindByGroup[g.id];
      header.appendChild(el("div", { class: "wd-dist-sm-cell wd-dist-sm-grouphead" }, [
        el("div", { class: "wd-dist-sm-grouplabel", text: labelByGroup[g.id] }),
        kind ? el("div", { class: "wd-dist-sm-groupkind", text: kind }) : null,
      ]));
    });
    container.appendChild(header);

    // One row per year
    years.forEach(function (year) {
      var row = el("div", { class: "wd-dist-sm-row" });
      row.appendChild(el("div", { class: "wd-dist-sm-yearcol", text: String(year) }));
      groups.forEach(function (g) {
        var cell = el("div", { class: "wd-dist-sm-cell" });
        var entries = byCell[year + "|" + g.id] || [];
        if (!entries.length) {
          cell.classList.add("wd-dist-sm-absent");
          cell.title = labelByGroup[g.id] + " — no attribution at " + year;
          row.appendChild(cell);
          return;
        }
        var total = entries.reduce(function (acc, e) { return acc + (e.weight || 0); }, 0);
        if (total <= 0) total = 1;
        // Stacked horizontal bar
        var bar = el("div", { class: "wd-dist-sm-bar" });
        entries.forEach(function (e) {
          var pct = (e.weight || 0) / total;
          var seg = el("span", {
            class: "wd-dist-sm-seg",
            title: glossById[e.sense] + " — " + (pct * 100).toFixed(0) + "%",
            style: {
              backgroundColor: colorBySense[e.sense] || "#888",
              width: (pct * 100).toFixed(2) + "%",
            },
          });
          bar.appendChild(seg);
        });
        cell.appendChild(bar);
        row.appendChild(cell);
      });
      container.appendChild(row);
    });

    // Sense legend
    var legend = el("div", { class: "wd-dist-sm-legend" });
    senses.forEach(function (s) {
      legend.appendChild(el("span", { class: "wd-dist-sm-legend-item" }, [
        el("span", {
          class: "wd-dist-sm-legend-swatch",
          style: { backgroundColor: colorBySense[s.id] },
        }),
        el("span", { text: glossById[s.id] }),
      ]));
    });

    return el("div", {}, [container, legend]);
  }

  // ---- Main render ----------------------------------------------------------

  function render(panelEl, doc, currentIri) {
    panelEl.innerHTML = "";
    if (!doc || !doc.words || !Object.keys(doc.words).length) {
      panelEl.appendChild(el("p", {
        class: "empty-msg",
        text: "No multi-group attribution data. Once Word Drift 3.0 ingests "
             + "MeaningAttribution records for a word, it will appear here.",
      }));
      return;
    }

    var word = doc.words[currentIri];
    if (!word) {
      // Fallback to first available
      currentIri = Object.keys(doc.words)[0];
      word = doc.words[currentIri];
    }

    // Header strip: picker + small intro line
    var head = el("div", { class: "wd-dist-head" });
    head.appendChild(el("div", { class: "wd-dist-head-title" }, [
      el("strong", { text: "Meaning distribution" }),
      el("span", {
        class: "wd-dist-head-sub",
        text: " — how this word is read across groups, year by year (Word Drift 3.0).",
      }),
    ]));
    var picker = buildWordPicker(doc, currentIri, function (iri) {
      var qs = new URLSearchParams(window.location.search);
      qs.set("word", word ? doc.words[iri].writtenForm : iri);
      var newUrl = window.location.pathname + "?" + qs.toString();
      window.history.replaceState({}, "", newUrl);
      render(panelEl, doc, iri);
    });
    head.appendChild(picker);
    panelEl.appendChild(head);

    // Layout: two-column. Left = summary + sparklines. Right = small multiples.
    var grid = el("div", { class: "wd-dist-grid" });

    var left = el("div", { class: "wd-dist-left" });
    left.appendChild(renderSummary(word));

    var sparkBox = el("div", { class: "wd-dist-sparks" });
    var sparkTitle = el("div", { class: "wd-dist-sparks-title", text: "Metrics over time" });
    sparkBox.appendChild(sparkTitle);
    sparkBox.appendChild(sparkline(
      word.metrics || [], function (r) { return r.entropy; }, "Entropy (bits)", null
    ));
    sparkBox.appendChild(sparkline(
      word.metrics || [], function (r) { return r.fragmentation; }, "Fragmentation", 1.0
    ));
    sparkBox.appendChild(sparkline(
      word.metrics || [], function (r) { return r.divergence_max; }, "Max group divergence (bits)", 1.0
    ));
    left.appendChild(sparkBox);

    var right = el("div", { class: "wd-dist-right" });
    right.appendChild(el("div", { class: "wd-dist-right-title", text: "Per-group sense distribution" }));
    right.appendChild(renderSmallMultiples(word));

    grid.appendChild(left);
    grid.appendChild(right);
    panelEl.appendChild(grid);

    // M5: regional sub-panel. Renders only if the word has region records.
    if ((word.regions || []).length > 0) {
      panelEl.appendChild(renderRegionalPanel(word));
    }

    // M6: platform sub-panel. Renders only if the word has platform records.
    if ((word.platforms || []).length > 0) {
      panelEl.appendChild(renderPlatformPanel(word));
    }
  }

  // ---- Platform sub-panel (M6) ---------------------------------------------
  // A latest-year stacked bar per platform plus the cross-platform JSD
  // sparkline from word.metrics.platform_divergence_max.

  function renderPlatformPanel(word) {
    var container = el("div", { class: "wd-dist-platform-panel" });
    container.appendChild(el("div", {
      class: "wd-dist-right-title",
      text: "Platform-conditioned distribution (M6)",
    }));

    var platforms = word.platforms || [];
    var senses = word.senses || [];
    if (!platforms.length || !senses.length) return container;

    var colorBySense = senseColors(senses);
    var glossById = {};
    senses.forEach(function (s) { glossById[s.id] = s.gloss || "(no gloss)"; });

    // For each platform, take the latest year with any attribution and
    // build a normalised sense stack.
    var attrs = (word.attributions || []).filter(function (a) { return a.platform; });
    var byPlatformYear = {};
    attrs.forEach(function (a) {
      if (a.year == null) return;
      var k = a.platform + "|" + a.year;
      (byPlatformYear[k] = byPlatformYear[k] || []).push(a);
    });
    var latestYear = {};
    Object.keys(byPlatformYear).forEach(function (k) {
      var p = k.indexOf("|");
      var pid = k.slice(0, p);
      var y = parseInt(k.slice(p + 1), 10);
      if (!(pid in latestYear) || y > latestYear[pid]) latestYear[pid] = y;
    });

    var rows = el("div", { class: "wd-dist-platform-rows" });
    platforms.forEach(function (p) {
      var year = latestYear[p.id];
      if (year == null) return;
      var entries = byPlatformYear[p.id + "|" + year] || [];
      var total = entries.reduce(function (acc, e) { return acc + (e.weight || 0); }, 0);
      if (total <= 0) return;
      var row = el("div", { class: "wd-dist-platform-row" });
      row.appendChild(el("div", { class: "wd-dist-platform-meta" }, [
        el("div", { class: "wd-dist-platform-label", text: p.label || p.id }),
        p.kind ? el("div", { class: "wd-dist-platform-kind", text: p.kind + " — " + year }) : null,
      ]));
      var bar = el("div", { class: "wd-dist-platform-bar" });
      // Aggregate by sense (within the latest year, same platform).
      var stack = {};
      entries.forEach(function (e) { stack[e.sense] = (stack[e.sense] || 0) + (e.weight || 0); });
      Object.keys(stack).forEach(function (sId) {
        var pct = stack[sId] / total;
        bar.appendChild(el("span", {
          class: "wd-dist-platform-seg",
          title: glossById[sId] + " — " + (pct * 100).toFixed(0) + "%",
          style: {
            backgroundColor: colorBySense[sId] || "#888",
            width: (pct * 100).toFixed(2) + "%",
          },
        }));
      });
      row.appendChild(bar);
      rows.appendChild(row);
    });
    container.appendChild(rows);

    // Cross-platform divergence note
    var metrics = word.metrics || [];
    var latest = metrics.length ? metrics[metrics.length - 1] : null;
    if (latest && latest.platform_divergence_max != null) {
      container.appendChild(el("p", {
        class: "wd-dist-region-caption",
        text: "Max cross-platform JSD at " + latest.year + ": "
              + latest.platform_divergence_max.toFixed(3) + " bits "
              + "across " + (latest.n_platforms || 0) + " platforms. "
              + "Higher values indicate platform-native readings of the same word.",
      }));
    }
    return container;
  }

  // ---- Regional sub-panel (M5) ---------------------------------------------
  // A proportional-symbol map using d3.geoNaturalEarth1 (already loaded for
  // the Map tab). One circle per region, sized by total attribution weight
  // at the latest available year, segmented into senses by colour. No
  // animation. Falls back to a circle list if d3 or world data is missing.

  function renderRegionalPanel(word) {
    var container = el("div", { class: "wd-dist-region-panel" });
    container.appendChild(el("div", {
      class: "wd-dist-right-title",
      text: "Regional distribution (M5)",
    }));

    var regions = word.regions || [];
    var senses = word.senses || [];
    if (!regions.length || !senses.length) return container;

    var colorBySense = senseColors(senses);
    var glossById = {};
    senses.forEach(function (s) { glossById[s.id] = s.gloss || "(no gloss)"; });
    var regionMeta = {};
    regions.forEach(function (r) { regionMeta[r.id] = r; });

    // Latest year per region with at least one attribution.
    var byRegionYear = {};
    (word.attributions || []).forEach(function (a) {
      if (!a.region || a.year == null) return;
      var key = a.region + "|" + a.year;
      (byRegionYear[key] = byRegionYear[key] || []).push(a);
    });
    var latestYearByRegion = {};
    Object.keys(byRegionYear).forEach(function (k) {
      var p = k.indexOf("|");
      var rid = k.slice(0, p);
      var y = parseInt(k.slice(p + 1), 10);
      if (!(rid in latestYearByRegion) || y > latestYearByRegion[rid]) {
        latestYearByRegion[rid] = y;
      }
    });

    // Total per region (for sizing) and per-sense weights (for stacks).
    var regionTotal = {};
    var regionStack = {};
    regions.forEach(function (r) {
      var y = latestYearByRegion[r.id];
      if (y == null) return;
      var entries = byRegionYear[r.id + "|" + y] || [];
      var total = entries.reduce(function (acc, e) { return acc + (e.weight || 0); }, 0);
      regionTotal[r.id] = total;
      var stack = {};
      entries.forEach(function (e) { stack[e.sense] = (stack[e.sense] || 0) + (e.weight || 0); });
      regionStack[r.id] = stack;
    });

    // SVG map
    var svgNS = "http://www.w3.org/2000/svg";
    var w = 720, h = 360;
    var svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    svg.setAttribute("class", "wd-dist-region-map");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Regional sense distribution for " + word.writtenForm);

    var hasD3 = typeof window.d3 !== "undefined" && typeof d3.geoNaturalEarth1 === "function";
    var projection = null, pathGen = null;
    if (hasD3) {
      projection = d3.geoNaturalEarth1().fitSize([w, h], { type: "Sphere" });
      pathGen = d3.geoPath(projection);
      // Coastline outline (vendored world-110m as a FeatureCollection)
      fetch("assets/vendor/world-110m.json", { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (world) {
          if (!world) return;
          var feats = (world.features || []);
          var g = document.createElementNS(svgNS, "g");
          g.setAttribute("class", "wd-dist-region-land");
          feats.forEach(function (f) {
            var d = pathGen(f);
            if (!d) return;
            var p = document.createElementNS(svgNS, "path");
            p.setAttribute("d", d);
            g.appendChild(p);
          });
          svg.insertBefore(g, svg.firstChild);
        })
        .catch(function () { /* offline / vendor missing: skip land */ });
    }

    // Render one stacked circle per region.
    var rMax = 36;
    var maxTotal = Math.max.apply(null,
      Object.values(regionTotal).concat([0.0001])
    );

    regions.forEach(function (r) {
      var total = regionTotal[r.id] || 0;
      if (total <= 0 || r.lat == null || r.lon == null) return;
      var pt = projection ? projection([r.lon, r.lat]) : pseudoProject(r.lon, r.lat, w, h);
      if (!pt) return;
      var radius = rMax * Math.sqrt(total / maxTotal);
      var year = latestYearByRegion[r.id];
      // Build stacked arcs by sense
      var stack = regionStack[r.id] || {};
      var senseIds = Object.keys(stack);
      // Sort by gloss so colour reads stably across regions.
      senseIds.sort(function (a, b) { return (glossById[a] || "").localeCompare(glossById[b] || ""); });

      var g = document.createElementNS(svgNS, "g");
      g.setAttribute("transform", "translate(" + pt[0].toFixed(1) + " " + pt[1].toFixed(1) + ")");

      var cumStart = -Math.PI / 2;
      var totalForArc = total;
      senseIds.forEach(function (sId) {
        var v = stack[sId];
        if (v <= 0) return;
        var slice = (v / totalForArc) * Math.PI * 2;
        var pathd = arcPath(0, 0, radius, cumStart, cumStart + slice);
        var p = document.createElementNS(svgNS, "path");
        p.setAttribute("d", pathd);
        p.setAttribute("fill", colorBySense[sId] || "#888");
        p.setAttribute("stroke", "#3a3530");
        p.setAttribute("stroke-width", "0.5");
        p.setAttribute("opacity", "0.85");
        var title = document.createElementNS(svgNS, "title");
        title.textContent = (regionMeta[r.id].label || r.id)
          + " @ " + year + " — " + glossById[sId]
          + " (" + (v / totalForArc * 100).toFixed(0) + "%)";
        p.appendChild(title);
        g.appendChild(p);
        cumStart += slice;
      });

      // Region label
      var lbl = document.createElementNS(svgNS, "text");
      lbl.setAttribute("x", "0");
      lbl.setAttribute("y", (radius + 12).toFixed(1));
      lbl.setAttribute("text-anchor", "middle");
      lbl.setAttribute("class", "wd-dist-region-label");
      lbl.textContent = regionMeta[r.id].label || r.id;
      g.appendChild(lbl);

      svg.appendChild(g);
    });

    container.appendChild(svg);

    var caption = el("p", {
      class: "wd-dist-region-caption",
      text: "Circle area is proportional to the most-recent total attribution weight for "
            + word.writtenForm + " in that region. Slices show the sense breakdown at that year. "
            + "Hover a slice for the percentage. Coordinates are presentation centroids only; "
            + "do not treat them as gazetteer geometry.",
    });
    container.appendChild(caption);
    return container;
  }

  // Fallback projection if d3 isn't ready: equirectangular, no land.
  function pseudoProject(lon, lat, w, h) {
    var x = ((lon + 180) / 360) * w;
    var y = ((90 - lat) / 180) * h;
    return [x, y];
  }

  // SVG arc path from (x,y), radius r, start angle a0 to end angle a1.
  function arcPath(cx, cy, r, a0, a1) {
    var x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0);
    var x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
    var large = (a1 - a0) > Math.PI ? 1 : 0;
    if (Math.abs(a1 - a0) >= Math.PI * 2 - 1e-6) {
      // Full circle
      return "M " + (cx - r) + " " + cy + " a " + r + " " + r + " 0 1 0 " + (2 * r) + " 0 a " + r + " " + r + " 0 1 0 " + (-2 * r) + " 0 Z";
    }
    return "M " + cx + " " + cy + " L " + x0.toFixed(2) + " " + y0.toFixed(2)
         + " A " + r + " " + r + " 0 " + large + " 1 " + x1.toFixed(2) + " " + y1.toFixed(2) + " Z";
  }

  // ---- View registration ----------------------------------------------------

  WD.registerView("distribution", {
    label: "Distribution",
    panelId: "panel-distribution",
    onActivate: function (panelEl) {
      panelEl.innerHTML = '<p class="empty-msg">Loading meaning distribution&hellip;</p>';
      loadDoc().then(function (doc) {
        if (!doc) {
          panelEl.innerHTML = '<p class="empty-msg">Could not load /graph-distribution.json. '
            + 'This endpoint is served only by the live Trails app, not the static fallback.</p>';
          return;
        }
        render(panelEl, doc, currentWordIri(doc));
      });
    },
  });
})();
