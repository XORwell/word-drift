// WORD-DRIFT view module: Map
// Where meaning-changing trigger events are located on Earth.
//
// Data: site/trigger-coords.json — 93 of 170 Wikidata-linked triggers carry
//       {triggerId,label,qid,lat,lon,eventDate,category,coordSource}.
// Projection: d3.geoNaturalEarth1 (from the global d3 v7 bundle, which ships
//       d3-geo). Land context: a vendored, dependency-free coarse coastline
//       (assets/vendor/world-110m.json, a plain GeoJSON FeatureCollection so no
//       topojson-client is needed). If that file is missing we gracefully fall
//       back to graticule + sphere outline only.
// Points: coloured by category (d3.schemeTableau10, matching the Triggers-tab
//       dashboard map), sized by the trigger's wordCount (WD.triggerImpact),
//       click -> WD.showTrigger. coordSource is shown honestly so fallback
//       (birthplace/HQ) points are not over-read as event locations.
//
// Contract: see assets/views/API.md.
(function () {
  "use strict";
  if (!window.WD || typeof window.WD.registerView !== "function") {
    console.warn("map.js: window.WD not ready");
    return;
  }

  var COORDS_URL = "trigger-coords.json";
  var LAND_URL = "assets/vendor/world-110m.json";

  // Module-level caches (fetch once, reuse across re-activations / resizes).
  var coordsPromise = null; // Promise<{data, error}>
  var landPromise = null;   // Promise<GeoJSON|null>

  // coordSource -> human-readable provenance note. P625 is the event's own
  // coordinate location; the others are place fallbacks attached to a person or
  // organisation linked to the event, so the dot is only an approximation.
  var SOURCE_NOTE = {
    P625: { exact: true, text: "exact event location (P625)" },
    P19: { exact: false, text: "approx: birthplace of namesake (P19)" },
    P159: { exact: false, text: "approx: organisation headquarters (P159)" },
    P740: { exact: false, text: "approx: location of formation (P740)" },
  };

  function sourceNote(src) {
    return SOURCE_NOTE[src] || { exact: false, text: "approximate location (" + (src || "?") + ")" };
  }

  function loadCoords() {
    if (!coordsPromise) {
      coordsPromise = fetch(COORDS_URL, { cache: "no-cache" })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(function (doc) {
          var list = Array.isArray(doc) ? doc : (doc && doc.triggers) || [];
          var rows = list.filter(function (t) {
            return t && isFinite(t.lat) && isFinite(t.lon);
          });
          return { data: doc, rows: rows, error: null };
        })
        .catch(function (err) {
          return { data: null, rows: [], error: err };
        });
    }
    return coordsPromise;
  }

  function loadLand() {
    if (!landPromise) {
      landPromise = fetch(LAND_URL, { cache: "force-cache" })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(function (geo) {
          // Accept either a FeatureCollection or a bare geometry/feature.
          if (geo && (geo.type === "FeatureCollection" || geo.type === "Feature" ||
            geo.type === "MultiPolygon" || geo.type === "Polygon")) {
            return geo;
          }
          return null;
        })
        .catch(function () {
          return null; // graceful: no land, graticule-only
        });
    }
    return landPromise;
  }

  // wordCount lookup keyed by trigger IRI, from WD.triggerImpact.
  function buildWordCountIndex() {
    var idx = Object.create(null);
    (WD.triggerImpact || []).forEach(function (t) {
      if (t && t.trigger != null) idx[t.trigger] = t.wordCount || 0;
    });
    return idx;
  }

  // Parse an eventDate ("0387", "1899", "-44", numbers) to a display year.
  function fmtEventYear(raw) {
    if (raw == null || raw === "") return "?";
    var n = parseInt(String(raw).replace(/^(-?)0+(\d)/, "$1$2"), 10);
    if (isNaN(n)) return WD.escHtml(String(raw));
    if (typeof WD.fmtYear === "function") return WD.fmtYear(n);
    return String(n);
  }

  function emptyState(panelEl, msg) {
    panelEl.innerHTML = '<p class="empty-msg">' + WD.escHtml(msg) + "</p>";
  }

  WD.registerView("map", {
    label: "Map",
    panelId: "panel-map",
    onActivate: function (panelEl) {
      var d3 = window.d3;
      if (!d3 || typeof d3.geoNaturalEarth1 !== "function") {
        emptyState(panelEl, "Map view needs d3-geo, which is not available in this build.");
        return;
      }

      panelEl.innerHTML = '<p class="empty-msg">Map view loading…</p>';

      Promise.all([loadCoords(), loadLand()]).then(function (res) {
        var coords = res[0];
        var land = res[1];

        if (coords.error) {
          emptyState(panelEl, "Trigger coordinates are unavailable (" +
            (coords.error.message || "load failed") + "). The map cannot be drawn.");
          return;
        }
        if (!coords.rows.length) {
          emptyState(panelEl, "No located triggers found in trigger-coords.json.");
          return;
        }

        render(panelEl, d3, coords, land);
      });
    },
  });

  function render(panelEl, d3, coords, land) {
    var rows = coords.rows;
    var meta = coords.data || {};
    var totalLinked = meta.qidLinkedTriggers || 170;
    var located = meta.withCoordinates || rows.length;

    var wc = buildWordCountIndex();

    // Categories: match the dashboard map on the Triggers tab, which uses
    // d3.scaleOrdinal(d3.schemeTableau10) keyed by the category string.
    var catSet = [];
    rows.forEach(function (r) {
      var c = r.category || "Other";
      if (catSet.indexOf(c) === -1) catSet.push(c);
    });
    catSet.sort();
    // Curated, theme-aware categorical palette (read fresh per render so the map
    // re-themes on a light/dark toggle). Falls back to Tableau10 if vars missing.
    function cssVar(name, fallback) {
      try {
        var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return v || fallback;
      } catch (e) { return fallback; }
    }
    var MAP_PALETTE = [
      cssVar("--dt-broadening", "#4338ca"),
      cssVar("--dt-metaphorization", "#b26a00"),
      cssVar("--dt-amelioration", "#15803d"),
      cssVar("--dt-reversal", "#be185d"),
      cssVar("--cause-t2", "#0369a1"),
      cssVar("--cause-t4", "#e11d48"),
      cssVar("--dt-narrowing", "#7c3aed"),
      cssVar("--dt-metonymization", "#c2410c"),
      cssVar("--dt-reappropriation", "#0f766e"),
      cssVar("--dt-pejoration", "#dc2626"),
    ];
    var catColor = d3.scaleOrdinal(MAP_PALETTE).domain(catSet);

    // ---- Layout -----------------------------------------------------------
    panelEl.innerHTML = "";

    var wrap = document.createElement("div");
    wrap.className = "wd-map-wrap";
    wrap.style.display = "flex";
    wrap.style.flexDirection = "column";
    wrap.style.gap = "0.6rem";
    wrap.style.padding = "0.4rem 0 0";
    panelEl.appendChild(wrap);

    // Header: count + caption about provenance.
    var header = document.createElement("div");
    header.className = "wd-map-header";
    header.style.display = "flex";
    header.style.flexWrap = "wrap";
    header.style.alignItems = "baseline";
    header.style.justifyContent = "space-between";
    header.style.gap = "0.5rem";
    header.innerHTML =
      '<div style="font-size:0.82rem;color:var(--text-sub);">' +
        "<strong style=\"color:var(--text);\">" + located + " of " + totalLinked +
        " linked triggers located</strong>" +
      "</div>" +
      '<div style="font-size:0.72rem;color:var(--text-faint);max-width:46ch;text-align:right;">' +
        "Hollow rings mark approximate points (birthplace / HQ fallbacks), not the event’s own coordinates." +
      "</div>";
    wrap.appendChild(header);

    // Map + legend row.
    var body = document.createElement("div");
    body.style.display = "flex";
    body.style.flexWrap = "wrap";
    body.style.gap = "0.8rem";
    body.style.alignItems = "flex-start";
    wrap.appendChild(body);

    var mapBox = document.createElement("div");
    mapBox.style.flex = "1 1 520px";
    mapBox.style.minWidth = "0";
    mapBox.style.position = "relative";
    mapBox.style.background = "var(--bg-card)";
    mapBox.style.border = "1px solid var(--border)";
    mapBox.style.borderRadius = "var(--radius)";
    mapBox.style.overflow = "hidden";
    body.appendChild(mapBox);

    var legendBox = document.createElement("div");
    legendBox.style.flex = "0 0 auto";
    legendBox.style.minWidth = "150px";
    body.appendChild(legendBox);

    // Tooltip (own element; WD does not expose showTip/hideTip). Mirrors the
    // #exp-tooltip styling so it reads consistently with the rest of the app.
    var tip = document.createElement("div");
    tip.setAttribute("role", "tooltip");
    tip.style.position = "fixed";
    tip.style.pointerEvents = "none";
    tip.style.background = "var(--bg-card2)";
    tip.style.border = "1px solid var(--border)";
    tip.style.borderRadius = "var(--radius)";
    tip.style.padding = "0.55rem 0.8rem";
    tip.style.fontSize = "0.8rem";
    tip.style.maxWidth = "280px";
    tip.style.lineHeight = "1.5";
    tip.style.boxShadow = "0 4px 20px rgba(0,0,0,0.4)";
    tip.style.zIndex = "9999";
    tip.style.display = "none";
    document.body.appendChild(tip);

    function showTip(html, ev) {
      tip.innerHTML = html;
      tip.style.display = "block";
      placeTip(ev);
    }
    function hideTip() { tip.style.display = "none"; }
    function placeTip(ev) {
      var pad = 14;
      var x = ev.clientX + pad, y = ev.clientY + pad;
      var w = tip.offsetWidth, h = tip.offsetHeight;
      if (x + w > window.innerWidth - 8) x = ev.clientX - w - pad;
      if (y + h > window.innerHeight - 8) y = ev.clientY - h - pad;
      tip.style.left = x + "px";
      tip.style.top = y + "px";
    }

    // ---- Dimensions -------------------------------------------------------
    var width = Math.max(320, mapBox.clientWidth || panelEl.clientWidth || 640);
    // Natural Earth has a ~1.97:1 aspect ratio; clamp height so it fits nicely.
    var height = Math.max(260, Math.min(620, Math.round(width / 1.95)));

    var svg = d3.select(mapBox).append("svg")
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", "0 0 " + width + " " + height)
      .attr("role", "img")
      .attr("aria-label", "World map of " + located + " trigger event locations")
      .style("display", "block")
      .style("background", "var(--bg-card)")
      .style("cursor", "grab");

    // ---- Projection -------------------------------------------------------
    var projection = d3.geoNaturalEarth1();
    var path = d3.geoPath(projection);
    projection.fitExtent([[6, 6], [width - 6, height - 6]], { type: "Sphere" });

    var defs = svg.append("defs");
    // soft drop for points
    var gRoot = svg.append("g"); // everything zoomable lives here

    // Sphere outline + ocean fill.
    gRoot.append("path")
      .datum({ type: "Sphere" })
      .attr("d", path)
      .attr("fill", "var(--bg-card2)")
      .attr("stroke", "var(--border)")
      .attr("stroke-width", 1);

    // Graticule.
    var graticule = d3.geoGraticule10();
    gRoot.append("path")
      .datum(graticule)
      .attr("d", path)
      .attr("fill", "none")
      .attr("stroke", "var(--border-soft, var(--border))")
      .attr("stroke-width", 0.5)
      .attr("stroke-opacity", 0.7)
      .attr("pointer-events", "none");

    // Land (if vendored geometry was available).
    var landNote = "graticule + sphere only (no land geometry available offline)";
    if (land) {
      var landFeatures =
        land.type === "FeatureCollection" ? land
          : land.type === "Feature" ? { type: "FeatureCollection", features: [land] }
            : { type: "FeatureCollection", features: [{ type: "Feature", geometry: land, properties: {} }] };
      gRoot.append("path")
        .datum(landFeatures)
        .attr("d", path)
        .attr("fill", "var(--bg-panel)")
        .attr("fill-opacity", 0.85)
        .attr("stroke", "var(--text-faint)")
        .attr("stroke-width", 0.5)
        .attr("stroke-opacity", 0.6)
        .attr("pointer-events", "none");
      landNote = "vendored world-110m coastline (GeoJSON)";
    }

    // ---- Points -----------------------------------------------------------
    // Size by wordCount: gentle sqrt scale so a 12-word trigger does not dwarf
    // the map. Radii in projected (pre-zoom) pixels; counter-scaled on zoom.
    var maxWc = d3.max(rows, function (r) { return wc[r.triggerId] || 1; }) || 1;
    var rScale = d3.scaleSqrt().domain([0, maxWc]).range([2.5, 11]);

    // Project once; keep rows whose coordinate lands on the map.
    var pts = [];
    rows.forEach(function (r) {
      var xy = projection([+r.lon, +r.lat]);
      if (!xy || !isFinite(xy[0]) || !isFinite(xy[1])) return;
      var note = sourceNote(r.coordSource);
      pts.push({
        row: r,
        x: xy[0],
        y: xy[1],
        r: rScale(wc[r.triggerId] || 0),
        color: catColor(r.category || "Other"),
        exact: note.exact,
        noteText: note.text,
        words: wc[r.triggerId] || 0,
      });
    });

    var pointsG = gRoot.append("g").attr("class", "wd-map-points");

    var marks = pointsG.selectAll("circle").data(pts).join("circle")
      .attr("cx", function (d) { return d.x; })
      .attr("cy", function (d) { return d.y; })
      .attr("r", function (d) { return d.r; })
      // Filled = exact (P625); hollow ring = approximate fallback.
      .attr("fill", function (d) { return d.exact ? d.color : "none"; })
      .attr("fill-opacity", function (d) { return d.exact ? 0.78 : 1; })
      .attr("stroke", function (d) { return d.color; })
      .attr("stroke-width", function (d) { return d.exact ? 1 : 1.6; })
      .attr("stroke-dasharray", function (d) { return d.exact ? null : "2.5 1.8"; })
      .style("cursor", "pointer")
      .attr("tabindex", 0)
      .attr("role", "button")
      .attr("aria-label", function (d) {
        return d.row.label + ", " + fmtEventYear(d.row.eventDate);
      });

    function tipHtml(d) {
      var r = d.row;
      return "<strong>" + WD.escHtml(r.label) + "</strong>" +
        '<p>' + WD.escHtml(r.category || "trigger") + " &bull; " + fmtEventYear(r.eventDate) + "</p>" +
        (d.words > 0
          ? '<p class="tt-sub" style="color:var(--text-sub);">Reframed ' + d.words +
            " word" + (d.words !== 1 ? "s" : "") + "</p>"
          : "") +
        '<p class="tt-sub" style="color:' + (d.exact ? "var(--text-faint)" : "var(--accent-hi)") + ';">' +
          WD.escHtml(d.noteText) + "</p>";
    }

    function activate(d) {
      if (d.row && d.row.triggerId && typeof WD.showTrigger === "function") {
        WD.showTrigger(d.row.triggerId);
      }
    }

    marks
      .on("mouseenter", function (event, d) { showTip(tipHtml(d), event); })
      .on("mousemove", function (event) { placeTip(event); })
      .on("mouseleave", function () { hideTip(); })
      .on("focus", function (event, d) {
        var b = this.getBoundingClientRect();
        showTip(tipHtml(d), { clientX: b.left + b.width / 2, clientY: b.top });
      })
      .on("blur", function () { hideTip(); })
      .on("click", function (event, d) { activate(d); })
      .on("keydown", function (event, d) {
        if (event.key === "Enter" || event.key === " " || event.key === "Spacebar") {
          event.preventDefault();
          activate(d);
        }
      });

    // ---- Zoom / pan (clamped) --------------------------------------------
    var zoom = d3.zoom()
      .scaleExtent([1, 8])
      .translateExtent([[0, 0], [width, height]])
      .on("zoom", function (event) {
        var k = event.transform.k;
        gRoot.attr("transform", event.transform.toString());
        // Counter-scale strokes/points so they stay legible when zoomed in.
        gRoot.selectAll("path").attr("vector-effect", "non-scaling-stroke");
        marks
          .attr("r", function (d) { return d.r / k; })
          .attr("stroke-width", function (d) { return (d.exact ? 1 : 1.6) / k; })
          .attr("stroke-dasharray", function (d) { return d.exact ? null : (2.5 / k) + " " + (1.8 / k); });
      });

    svg.call(zoom);
    svg.on("dblclick.zoom", null); // avoid surprise zoom jumps on double-click
    svg.on("mousedown.cursor", function () { svg.style("cursor", "grabbing"); });
    svg.on("mouseup.cursor", function () { svg.style("cursor", "grab"); });

    // Reset-view control.
    var resetBtn = document.createElement("button");
    resetBtn.type = "button";
    resetBtn.textContent = "Reset view";
    resetBtn.className = "facet-clear-btn";
    resetBtn.style.position = "absolute";
    resetBtn.style.top = "8px";
    resetBtn.style.right = "8px";
    resetBtn.style.background = "var(--bg-card2)";
    resetBtn.style.border = "1px solid var(--border)";
    resetBtn.style.borderRadius = "var(--radius)";
    resetBtn.style.padding = "0.25rem 0.55rem";
    resetBtn.style.fontSize = "0.72rem";
    resetBtn.style.cursor = "pointer";
    resetBtn.addEventListener("click", function () {
      var t = svg.transition();
      if (WD.prefersReducedMotion) {
        svg.call(zoom.transform, d3.zoomIdentity);
      } else {
        svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity);
      }
      void t;
    });
    mapBox.appendChild(resetBtn);

    // ---- Legend -----------------------------------------------------------
    var legendTitle = document.createElement("div");
    legendTitle.className = "legend-title";
    legendTitle.textContent = "Trigger category";
    legendTitle.style.fontSize = "0.7rem";
    legendTitle.style.textTransform = "uppercase";
    legendTitle.style.letterSpacing = "0.04em";
    legendTitle.style.color = "var(--text-faint)";
    legendTitle.style.marginBottom = "0.5rem";
    legendBox.appendChild(legendTitle);

    // Count rows per category for the legend.
    var catCounts = Object.create(null);
    rows.forEach(function (r) {
      var c = r.category || "Other";
      catCounts[c] = (catCounts[c] || 0) + 1;
    });

    var legendRows = document.createElement("div");
    legendRows.style.display = "flex";
    legendRows.style.flexDirection = "column";
    legendRows.style.gap = "0.35rem";
    catSet.forEach(function (c) {
      var item = document.createElement("div");
      item.className = "legend-item";
      item.innerHTML =
        '<span class="legend-swatch circle" style="background:' + catColor(c) + ';"></span>' +
        WD.escHtml(c) +
        ' <span style="color:var(--text-faint);">(' + catCounts[c] + ")</span>";
      legendRows.appendChild(item);
    });
    legendBox.appendChild(legendRows);

    // Provenance + size encoding key.
    var key = document.createElement("div");
    key.style.marginTop = "0.9rem";
    key.style.paddingTop = "0.7rem";
    key.style.borderTop = "1px solid var(--border)";
    key.style.display = "flex";
    key.style.flexDirection = "column";
    key.style.gap = "0.35rem";
    key.innerHTML =
      '<div class="legend-item">' +
        '<span class="legend-swatch circle" style="background:var(--text-sub);"></span>' +
        "exact location (P625)</div>" +
      '<div class="legend-item">' +
        '<span class="legend-swatch circle" style="background:transparent;border:1.5px dashed var(--text-sub);"></span>' +
        "approx (P19 / P159 / P740)</div>" +
      '<div class="legend-item" style="color:var(--text-faint);font-size:0.72rem;margin-top:0.2rem;">' +
        "Dot size = words reframed by the trigger.</div>";
    legendBox.appendChild(key);

    // Footnote about the base map approach (honest about offline fallback).
    var foot = document.createElement("div");
    foot.style.fontSize = "0.68rem";
    foot.style.color = "var(--text-faint)";
    foot.style.marginTop = "0.5rem";
    foot.textContent = "Base map: " + landNote + ", Natural Earth projection.";
    legendBox.appendChild(foot);

    // Clean up the floating tooltip if the panel is torn down / re-rendered.
    // onActivate clears panelEl.innerHTML on the next build, but the tip lives
    // on document.body, so remove it when the panel is emptied.
    var observer = new MutationObserver(function () {
      if (!document.body.contains(panelEl) || panelEl.firstChild !== wrap) {
        hideTip();
        if (tip.parentNode) tip.parentNode.removeChild(tip);
        observer.disconnect();
      }
    });
    try {
      observer.observe(panelEl, { childList: true });
    } catch (e) { /* MutationObserver unavailable: tip simply persists hidden */ }
  }
})();
