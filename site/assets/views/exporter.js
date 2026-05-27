// WORD-DRIFT utility module: Exporter + sharing utilities.
// Unlike the tab views, the exporter owns no panel. It registers a few toolbar
// buttons that act on whatever view is currently visible.
//
// Capabilities:
//   1. Chart export: serialise the active panel's primary <svg> to a standalone
//      SVG download, or rasterise it to a PNG download.
//   2. CSV export: dump all LIGHT words (WD.words) with an honest header row.
//   3. Permalink / Cite: copy the current deep-link URL, or a CC-BY citation
//      string built from WD.meta + the repo URL.
//   4. Run the query: open the competency-question SPARQL for the active view
//      in the repo (it opens the file; it does not execute SPARQL here).
//
// Contract: see assets/views/API.md. D3 v7 is global; no extra libraries.
(function () {
  "use strict";
  if (!window.WD || typeof window.WD.registerToolbarButton !== "function") {
    console.warn("exporter.js: window.WD not ready");
    return;
  }

  var REPO_URL = "https://github.com/XORwell/word-drift";
  var QUERY_DIR_URL =
    "https://github.com/XORwell/word-drift/tree/main/queries/competency";
  var QUERY_BASE_URL =
    "https://github.com/XORwell/word-drift/tree/main/queries";
  var reduced = !!WD.prefersReducedMotion;

  // -------------------------------------------------------------------------
  // Active-view detection
  // -------------------------------------------------------------------------

  // The visible panel carries class "active"; its id is "panel-<tab>".
  function activeTab() {
    var panel = document.querySelector(".exp-panel.active");
    if (!panel || !panel.id) return "overview";
    return panel.id.replace(/^panel-/, "");
  }

  function activePanel() {
    return document.querySelector(".exp-panel.active");
  }

  // The primary <svg> of the active panel. The detail tab has two stacked
  // sub-panels (sense timeline / force graph); only one is visible at a time,
  // so prefer the SVG inside the active sub-panel there.
  function activeSvg() {
    var panel = activePanel();
    if (!panel) return null;
    var sub = panel.querySelector(".detail-sub-panel.active");
    var scope = sub || panel;
    // Pick the first reasonably sized svg (skip tiny icon svgs in headers).
    var svgs = scope.querySelectorAll("svg");
    var best = null;
    for (var i = 0; i < svgs.length; i++) {
      var s = svgs[i];
      var r = s.getBoundingClientRect();
      if (r.width >= 80 && r.height >= 60) { best = s; break; }
      if (!best) best = s;
    }
    return best;
  }

  // A short, view-specific label for the active sub-chart (for filenames).
  function activeChartName() {
    var tab = activeTab();
    if (tab === "detail") {
      var sub = document.querySelector("#panel-detail .detail-sub-panel.active");
      if (sub && sub.id === "detail-graph-panel") return "detail-force-graph";
      return "detail-timeline";
    }
    return tab;
  }

  // -------------------------------------------------------------------------
  // Clipboard with graceful fallback (file:// has no navigator.clipboard).
  // -------------------------------------------------------------------------
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(
        function () { return true; },
        function () { return legacyCopy(text); }
      );
    }
    return Promise.resolve(legacyCopy(text));
  }

  function legacyCopy(text) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.top = "-1000px";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      ta.setSelectionRange(0, text.length);
      var ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (e) {
      return false;
    }
  }

  // -------------------------------------------------------------------------
  // Download helper
  // -------------------------------------------------------------------------
  function triggerDownload(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Revoke after a tick so the download has time to start.
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
  }

  // -------------------------------------------------------------------------
  // Transient confirmation toast (no animation when reduced motion is set).
  // -------------------------------------------------------------------------
  var toastEl = null;
  var toastTimer = null;
  function toast(msg) {
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.setAttribute("role", "status");
      toastEl.setAttribute("aria-live", "polite");
      toastEl.style.position = "fixed";
      toastEl.style.zIndex = "9999";
      toastEl.style.right = "16px";
      toastEl.style.bottom = "16px";
      toastEl.style.maxWidth = "min(420px, 80vw)";
      toastEl.style.padding = "10px 14px";
      toastEl.style.borderRadius = "8px";
      toastEl.style.background = "var(--bg-card2)";
      toastEl.style.color = "var(--text)";
      toastEl.style.border = "1px solid var(--border)";
      toastEl.style.font = "13px/1.4 system-ui, sans-serif";
      toastEl.style.boxShadow = "var(--shadow-pop, 0 4px 18px rgba(0,0,0,0.35))";
      toastEl.style.pointerEvents = "none";
      if (!reduced) toastEl.style.transition = "opacity .18s ease";
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.style.opacity = "1";
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      if (reduced) { toastEl.style.opacity = "0"; }
      else { toastEl.style.opacity = "0"; }
    }, reduced ? 2600 : 2200);
  }

  // -------------------------------------------------------------------------
  // 1. Chart export (SVG + PNG)
  // -------------------------------------------------------------------------

  // Inline enough computed style onto a cloned svg subtree that it renders
  // standalone (CSS rules in the page stylesheet would not travel with it).
  var STYLE_PROPS = [
    "fill", "fill-opacity", "stroke", "stroke-width", "stroke-opacity",
    "stroke-dasharray", "stroke-linecap", "stroke-linejoin", "opacity",
    "font-family", "font-size", "font-weight", "font-style", "text-anchor",
    "dominant-baseline", "alignment-baseline", "color", "letter-spacing",
    "visibility", "display", "shape-rendering", "paint-order"
  ];

  function inlineStyles(source, target) {
    var cs = window.getComputedStyle(source);
    var decl = "";
    for (var i = 0; i < STYLE_PROPS.length; i++) {
      var p = STYLE_PROPS[i];
      var v = cs.getPropertyValue(p);
      if (!v) continue;
      // Skip plain "none" except for fill/stroke, where "none" is meaningful
      // for shapes (e.g. an unfilled stroked path).
      if (v === "none" && p !== "fill" && p !== "stroke") continue;
      decl += p + ":" + v + ";";
    }
    target.setAttribute("style", decl);
    var sc = source.children, tc = target.children;
    for (var j = 0; j < sc.length; j++) {
      if (tc[j]) inlineStyles(sc[j], tc[j]);
    }
  }

  // Returns { string, width, height } for the serialised standalone SVG.
  function serialiseSvg(svg) {
    var rect = svg.getBoundingClientRect();
    var width = Math.max(1, Math.round(rect.width || svg.clientWidth || 800));
    var height = Math.max(1, Math.round(rect.height || svg.clientHeight || 500));

    var clone = svg.cloneNode(true);
    inlineStyles(svg, clone);

    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clone.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
    clone.setAttribute("width", width);
    clone.setAttribute("height", height);
    if (!clone.getAttribute("viewBox")) {
      clone.setAttribute("viewBox", "0 0 " + width + " " + height);
    }

    // Opaque background so PNGs are not transparent black.
    var bg = (WD.colors && WD.colors.BG_COLOR) || "#ffffff";
    var bgRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bgRect.setAttribute("x", "0");
    bgRect.setAttribute("y", "0");
    bgRect.setAttribute("width", String(width));
    bgRect.setAttribute("height", String(height));
    bgRect.setAttribute("fill", bg);
    clone.insertBefore(bgRect, clone.firstChild);

    var xml = new XMLSerializer().serializeToString(clone);
    if (!/^<\?xml/.test(xml)) {
      xml = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + xml;
    }
    return { string: xml, width: width, height: height };
  }

  function exportSvg() {
    var svg = activeSvg();
    if (!svg) { toast("No chart on this view to export."); return; }
    var s = serialiseSvg(svg);
    var blob = new Blob([s.string], { type: "image/svg+xml;charset=utf-8" });
    triggerDownload(blob, "word-drift-" + activeChartName() + ".svg");
    toast("Downloaded " + activeChartName() + ".svg");
  }

  function exportPng() {
    var svg = activeSvg();
    if (!svg) { toast("No chart on this view to export."); return; }
    var s = serialiseSvg(svg);
    var scale = Math.min(2, (window.devicePixelRatio || 1));
    if (scale < 1) scale = 1;

    var svgBlob = new Blob([s.string], { type: "image/svg+xml;charset=utf-8" });
    var url = URL.createObjectURL(svgBlob);
    var img = new Image();
    img.onload = function () {
      try {
        var canvas = document.createElement("canvas");
        canvas.width = Math.round(s.width * scale);
        canvas.height = Math.round(s.height * scale);
        var ctx = canvas.getContext("2d");
        ctx.setTransform(scale, 0, 0, scale, 0, 0);
        var bg = (WD.colors && WD.colors.BG_COLOR) || "#ffffff";
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, s.width, s.height);
        ctx.drawImage(img, 0, 0, s.width, s.height);
        URL.revokeObjectURL(url);
        canvas.toBlob(function (blob) {
          if (!blob) { toast("PNG export failed (canvas)."); return; }
          triggerDownload(blob, "word-drift-" + activeChartName() + ".png");
          toast("Downloaded " + activeChartName() + ".png");
        }, "image/png");
      } catch (e) {
        URL.revokeObjectURL(url);
        toast("PNG export failed: " + (e && e.message ? e.message : "error"));
      }
    };
    img.onerror = function () {
      URL.revokeObjectURL(url);
      toast("PNG export failed (could not rasterise SVG).");
    };
    img.src = url;
  }

  // -------------------------------------------------------------------------
  // 2. CSV export of the current word set (all LIGHT words)
  // -------------------------------------------------------------------------
  function csvCell(v) {
    if (v == null) return "";
    var s = String(v);
    if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  function exportCsv() {
    var words = (WD.words || []).slice();
    if (!words.length) { toast("No words loaded yet."); return; }
    var header = [
      "writtenForm", "language", "source", "quality",
      "driftTypeLabels", "yearStart", "yearEnd", "hasTrigger"
    ];
    var lines = [header.join(",")];
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      var dtl = (w.driftTypeLabels || []).join("; ");
      lines.push([
        csvCell(w.writtenForm),
        csvCell(w.language),
        csvCell(w.source),
        csvCell(w.quality),
        csvCell(dtl),
        csvCell(w.yearStart),
        csvCell(w.yearEnd),
        csvCell(w.hasTrigger ? "true" : "false")
      ].join(","));
    }
    // BOM so Excel reads UTF-8 (umlauts in writtenForm) correctly.
    var blob = new Blob(["﻿" + lines.join("\r\n") + "\r\n"],
      { type: "text/csv;charset=utf-8" });
    triggerDownload(blob, "word-drift-words.csv");
    toast("Downloaded word-drift-words.csv (" + words.length + " words).");
  }

  // -------------------------------------------------------------------------
  // 2b. Context export: the currently open WORD or TRIGGER as RDF / JSON
  // -------------------------------------------------------------------------
  // Honesty note: graph.json (the in-memory model) does NOT carry the per-claim
  // source URLs or the reified CausalHypothesis IRIs. Those live only in the
  // downloadable dataset (word-drift.ttl) and in claims-ledger.csv. So for the
  // open context we offer two honest exports:
  //   - "this word/trigger as JSON": the full in-memory record, lossless for
  //     what the page actually holds.
  //   - "this word/trigger as Turtle": a faithful snippet of the triples we CAN
  //     reconstruct (word, senses, drift events, their triggers, and a
  //     CausalHypothesis stub linking drift to trigger). A header comment points
  //     reviewers at the full dataset + ledger for source-level provenance.
  // Everything is built from WD.words / WD.triggers / WD.flatForWord; no fetch.

  var DRIFT_NS = "https://w3id.org/word-drift/ontology#";
  var RES_NS = "https://w3id.org/word-drift/resource/";

  // Read the currently open word IRI from the URL (?word=) -> light/heavy word.
  function openWord() {
    var params = new URLSearchParams(location.search);
    var name = params.get("word");
    if (!name) return null;
    var lang = params.get("lang");
    var words = WD.words || [];
    // Prefer an exact writtenForm (+ language) match; fall back to id match.
    var hit = null;
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (w.writtenForm === name && (!lang || w.language === lang)) { hit = w; break; }
    }
    if (!hit) {
      for (var j = 0; j < words.length; j++) {
        if (words[j].writtenForm === name) { hit = words[j]; break; }
      }
    }
    if (!hit && WD.wordById) hit = WD.wordById(name);
    return hit;
  }

  // Read the currently open trigger from the Triggers view.
  function openTrigger() {
    var params = new URLSearchParams(location.search);
    var id = params.get("trigger");
    if (!id) return null;
    if (WD.triggerById) {
      var t = WD.triggerById(id);
      if (t) return t;
      // The URL param may be a short id without the resource namespace.
      t = WD.triggerById(RES_NS + id);
      if (t) return t;
    }
    var trs = WD.triggers || [];
    for (var i = 0; i < trs.length; i++) {
      if (trs[i].id === id || trs[i].id.split("/").pop() === id) return trs[i];
    }
    return null;
  }

  // Slugify a string for a filename.
  function slug(s) {
    return String(s || "export").toLowerCase()
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "export";
  }

  // Turtle helpers -----------------------------------------------------------
  function ttlEscape(s) {
    return String(s).replace(/\\/g, "\\\\").replace(/"/g, '\\"')
      .replace(/\n/g, "\\n").replace(/\r/g, "\\r").replace(/\t/g, "\\t");
  }
  function ttlStr(s, lang) {
    var out = '"' + ttlEscape(s) + '"';
    return lang ? out + "@" + lang : out;
  }
  // Render a year (may be negative for BC) as an xsd:gYear literal.
  function ttlGYear(y) {
    if (y == null || y === "") return null;
    var n = parseInt(y, 10);
    if (isNaN(n)) return null;
    var neg = n < 0;
    var pad = String(Math.abs(n));
    while (pad.length < 4) pad = "0" + pad;
    return '"' + (neg ? "-" : "") + pad + '"^^xsd:gYear';
  }
  function iri(id) { return "<" + id + ">"; }

  var TTL_PREFIXES = [
    "@prefix drift: <" + DRIFT_NS + "> .",
    "@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
    "@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .",
    "@prefix owl:   <http://www.w3.org/2002/07/owl#> .",
    "@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .",
    "@prefix prov:  <http://www.w3.org/ns/prov#> .",
    "@prefix skos:  <http://www.w3.org/2004/02/skos/core#> ."
  ].join("\n");

  var TTL_PROVENANCE_NOTE =
    "# WORD-DRIFT context export (reconstructed from the in-memory graph).\n" +
    "# This snippet is FAITHFUL but PARTIAL: per-claim source URLs and the full\n" +
    "# reified CausalHypothesis records are NOT in the page model. For complete,\n" +
    "# citable provenance use the full dataset and the claims ledger:\n" +
    "#   " + REPO_URL + " (downloads/word-drift.ttl, downloads/claims-ledger.csv)\n";

  // Emit Turtle for a trigger node (and its hypothesis stubs are emitted by the
  // caller). Returns an array of lines.
  function triggerTtl(tr) {
    var lines = [];
    lines.push(iri(tr.id) + " a drift:TriggerEvent ;");
    var body = [];
    if (tr.label != null) body.push("    rdfs:label " + ttlStr(tr.label));
    if (tr.category != null) body.push("    drift:triggerCategory " + ttlStr(tr.category));
    var gy = ttlGYear(tr.date);
    if (gy) body.push("    drift:eventDate " + gy);
    if (tr.wikidataSameAs) body.push("    owl:sameAs " + iri(tr.wikidataSameAs));
    if (tr.description != null) body.push("    drift:description " + ttlStr(tr.description));
    lines.push(body.join(" ;\n") + " .");
    return lines;
  }

  // Build a Turtle snippet for one (heavy) word: its senses, drift events, and
  // for each drift event with a trigger, a CausalHypothesis stub + the trigger.
  function wordToTtl(w) {
    var blocks = [];
    var seenTriggers = {};

    // Word
    var wb = [iri(w.id) + " a drift:Word ;"];
    var wbody = [];
    if (w.writtenForm != null) wbody.push("    drift:writtenForm " + ttlStr(w.writtenForm, w.language || null));
    if (w.language != null) wbody.push("    drift:language " + ttlStr(w.language));
    (w.senses || []).forEach(function (s) { wbody.push("    drift:hasSense " + iri(s.id)); });
    wb.push(wbody.join(" ;\n") + " .");
    blocks.push(wb.join("\n"));

    // Senses
    (w.senses || []).forEach(function (s) {
      var sb = [iri(s.id) + " a drift:Sense ;"];
      var sbody = [];
      if (s.glossEn != null) sbody.push("    drift:gloss " + ttlStr(s.glossEn, "en"));
      if (s.connotationId) sbody.push("    drift:connotation " + iri(s.connotationId));
      else if (s.connotation) sbody.push("    drift:connotationLabel " + ttlStr(s.connotation));
      var sgy = ttlGYear(s.firstAttested);
      if (sgy) sbody.push("    drift:firstAttested " + sgy);
      if (!sbody.length) sbody.push("    rdfs:label " + ttlStr(s.id.split("/").pop()));
      sb.push(sbody.join(" ;\n") + " .");
      blocks.push(sb.join("\n"));
    });

    // Drift events (+ causal hypothesis stubs + triggers)
    var flat = (WD.flatForWord ? WD.flatForWord(w) : []) || [];
    (w.driftEvents || []).forEach(function (e, idx) {
      var eb = [iri(e.id) + " a drift:DriftEvent ;"];
      var ebody = ["    drift:affectsWord " + iri(w.id)];
      if (e.senseFromId) ebody.push("    drift:senseFrom " + iri(e.senseFromId));
      if (e.senseToId) ebody.push("    drift:senseTo " + iri(e.senseToId));
      (e.driftTypeIds || []).forEach(function (t) { ebody.push("    drift:driftType " + iri(t)); });
      if (!(e.driftTypeIds || []).length && e.driftTypeLabel) {
        ebody.push("    drift:driftTypeLabel " + ttlStr(e.driftTypeLabel));
      }
      var egy = ttlGYear(e.year);
      if (egy) ebody.push("    drift:year " + egy);
      if (e.confidence != null) ebody.push("    drift:confidence " + Number(e.confidence));
      eb.push(ebody.join(" ;\n") + " .");
      blocks.push(eb.join("\n"));

      // For each linked trigger, emit a CausalHypothesis stub.
      var causes = flat[idx] && flat[idx].causes ? flat[idx].causes : [];
      (e.triggerIds || []).forEach(function (trId, ti) {
        var hypId = RES_NS + "hyp-" + slug(w.writtenForm) + "-" + (idx + 1) + (ti ? "-" + (ti + 1) : "");
        var hb = [iri(hypId) + " a drift:CausalHypothesis ;"];
        var hbody = [
          "    drift:aboutDrift " + iri(e.id),
          "    drift:proposedTrigger " + iri(trId)
        ];
        var c = causes[ti] || causes[0];
        if (c && c.confidence != null) hbody.push("    drift:confidence " + Number(c.confidence));
        if (c && (c.evidence || []).length) {
          c.evidence.forEach(function (ev) { hbody.push("    drift:evidenceType " + ttlStr(ev)); });
        }
        hbody.push("    prov:wasInfluencedBy " + iri(trId));
        hb.push(hbody.join(" ;\n") + " .");
        blocks.push(hb.join("\n"));

        var tr = WD.triggerById ? WD.triggerById(trId) : null;
        if (tr && !seenTriggers[tr.id]) {
          seenTriggers[tr.id] = true;
          blocks.push(triggerTtl(tr).join("\n"));
        }
      });
    });

    return TTL_PROVENANCE_NOTE + "\n" + TTL_PREFIXES + "\n\n" + blocks.join("\n\n") + "\n";
  }

  // Build a Turtle snippet for one trigger: the trigger node, plus for each
  // affected word a CausalHypothesis stub linking that word's drift to it.
  function triggerToTtl(tr) {
    var blocks = [triggerTtl(tr).join("\n")];
    var impact = (WD.triggerImpact || []).filter(function (ti) {
      return ti.trigger === tr.id;
    })[0];
    var affected = impact ? (impact.words || []) : [];
    var seenWords = {};
    affected.forEach(function (form) {
      var words = (WD.words || []).filter(function (w) { return w.writtenForm === form; });
      words.forEach(function (w) {
        if (seenWords[w.id]) return;
        seenWords[w.id] = true;
        blocks.push(iri(w.id) + " a drift:Word ;\n    drift:writtenForm " +
          ttlStr(w.writtenForm, w.language || null) + " .");
        // Hypothesis stubs for this word's drift events that point at this trigger.
        (w.driftEvents || []).forEach(function (e, idx) {
          if ((e.triggerIds || []).indexOf(tr.id) === -1) return;
          var hypId = RES_NS + "hyp-" + slug(w.writtenForm) + "-to-" + slug(tr.id.split("/").pop());
          blocks.push(iri(hypId) + " a drift:CausalHypothesis ;\n" +
            "    drift:aboutDrift " + iri(e.id) + " ;\n" +
            "    drift:proposedTrigger " + iri(tr.id) + " ;\n" +
            "    prov:wasInfluencedBy " + iri(tr.id) + " .");
        });
      });
    });
    return TTL_PROVENANCE_NOTE + "\n" + TTL_PREFIXES + "\n\n" + blocks.join("\n\n") + "\n";
  }

  // Trigger downloads for the open context. These are no-ops with a toast if
  // nothing is open, but the menu only offers them when context exists.
  function exportOpenWordTtl() {
    var w = openWord();
    if (!w) { toast("Open a word first (Word Detail view)."); return; }
    var finish = function (full) {
      var blob = new Blob([wordToTtl(full)], { type: "text/turtle;charset=utf-8" });
      triggerDownload(blob, "word-drift-" + slug(full.writtenForm) + ".ttl");
      toast("Downloaded " + slug(full.writtenForm) + ".ttl");
    };
    if (w.__detailMerged || (w.senses && w.driftEvents)) { finish(w); }
    else if (WD.getDetail) { WD.getDetail(w).then(function (full) { finish(full || w); }); }
    else { finish(w); }
  }

  function exportOpenWordJson() {
    var w = openWord();
    if (!w) { toast("Open a word first (Word Detail view)."); return; }
    var finish = function (full) {
      var rec = {
        word: full,
        flatEvents: WD.flatForWord ? WD.flatForWord(full) : [],
        note: "In-memory record. Per-claim source URLs and full provenance live " +
          "in the downloadable dataset (downloads/word-drift.ttl) and the claims " +
          "ledger (downloads/claims-ledger.csv) at " + REPO_URL + ".",
        datasetEntry: full.id,
        source: location.href
      };
      var blob = new Blob([JSON.stringify(rec, null, 2)], { type: "application/json;charset=utf-8" });
      triggerDownload(blob, "word-drift-" + slug(full.writtenForm) + ".json");
      toast("Downloaded " + slug(full.writtenForm) + ".json");
    };
    if (w.__detailMerged || (w.senses && w.driftEvents)) { finish(w); }
    else if (WD.getDetail) { WD.getDetail(w).then(function (full) { finish(full || w); }); }
    else { finish(w); }
  }

  function exportOpenTriggerTtl() {
    var tr = openTrigger();
    if (!tr) { toast("Open a trigger first (Triggers view)."); return; }
    var blob = new Blob([triggerToTtl(tr)], { type: "text/turtle;charset=utf-8" });
    triggerDownload(blob, "word-drift-trigger-" + slug(tr.id.split("/").pop()) + ".ttl");
    toast("Downloaded trigger " + slug(tr.id.split("/").pop()) + ".ttl");
  }

  function exportOpenTriggerJson() {
    var tr = openTrigger();
    if (!tr) { toast("Open a trigger first (Triggers view)."); return; }
    var impact = (WD.triggerImpact || []).filter(function (ti) { return ti.trigger === tr.id; })[0];
    var rec = {
      trigger: tr,
      affectedWords: impact ? (impact.words || []) : [],
      note: "In-memory record. Per-claim source URLs and full provenance live in " +
        "the downloadable dataset and the claims ledger at " + REPO_URL + ".",
      datasetEntry: tr.id,
      source: location.href
    };
    var blob = new Blob([JSON.stringify(rec, null, 2)], { type: "application/json;charset=utf-8" });
    triggerDownload(blob, "word-drift-trigger-" + slug(tr.id.split("/").pop()) + ".json");
    toast("Downloaded trigger " + slug(tr.id.split("/").pop()) + ".json");
  }

  // -------------------------------------------------------------------------
  // 3. Permalink / Cite
  // -------------------------------------------------------------------------
  function copyLink() {
    var href = location.href;
    copyText(href).then(function (ok) {
      toast(ok ? "Link copied to clipboard." : "Could not copy. URL: " + href);
    });
  }

  // Build a citation string from the current deep-link + WD.meta. CC-BY.
  function buildCitation() {
    var params = new URLSearchParams(location.search);
    var word = params.get("word");
    var trigger = params.get("trigger");
    var year = new Date().getFullYear();
    var accessed = new Date().toISOString().slice(0, 10);
    var meta = WD.meta || {};

    var subject;
    if (word) {
      subject = 'entry "' + word + '"';
    } else if (trigger) {
      subject = 'trigger "' + trigger + '"';
    } else {
      var counts = [];
      if (meta.words != null) counts.push(meta.words + " words");
      if (meta.driftEvents != null) counts.push(meta.driftEvents + " drift events");
      if (meta.triggers != null) counts.push(meta.triggers + " triggers");
      subject = "dataset" + (counts.length ? " (" + counts.join(", ") + ")" : "");
    }

    return "WORD-DRIFT: a knowledge graph of lexical semantic change, " +
      subject + ". " + year + ". CC-BY. " + REPO_URL +
      " (accessed " + accessed + "; " + location.href + ").";
  }

  function copyCitation() {
    var cite = buildCitation();
    copyText(cite).then(function (ok) {
      toast(ok ? "Citation copied to clipboard." : "Could not copy citation.");
    });
  }

  // -------------------------------------------------------------------------
  // 4. Run the query (link to the repo's competency SPARQL for this view)
  // -------------------------------------------------------------------------
  // Map each tab to the most relevant query file. These open the .rq in the
  // repo; the static page cannot execute SPARQL.
  var QUERY_FOR_TAB = {
    overview: {
      file: "competency/cq03-drifttype-by-trigger-category.rq",
      desc: "Which drift types follow which trigger categories?"
    },
    triggers: {
      file: "competency/cq01-event-reframed-most-words.rq",
      desc: "Which event reframed the most words?"
    },
    detail: {
      file: "competency/cq02-hypotheses-for-word.rq",
      desc: "Causal hypotheses for a single word."
    },
    compare: {
      file: "competency/cq04-cross-lingual-same-direction.rq",
      desc: "Cross-lingual words drifting in the same direction."
    },
    network: {
      file: "competency/cq09-competing-hypotheses.rq",
      desc: "Drift events with competing hypotheses."
    },
    map: {
      file: "competency/cq06-triggers-in-date-range.rq",
      desc: "Triggers within a date range."
    },
    trends: {
      file: "competency/cq10-sense-timeline-with-source.rq",
      desc: "Sense timeline with source provenance."
    }
  };

  var queryPopover = null;
  function closePopover() {
    if (queryPopover && queryPopover.parentNode) {
      queryPopover.parentNode.removeChild(queryPopover);
    }
    queryPopover = null;
    document.removeEventListener("keydown", onPopoverKey, true);
    document.removeEventListener("click", onDocClick, true);
  }
  function onPopoverKey(e) { if (e.key === "Escape") closePopover(); }
  function onDocClick(e) {
    if (queryPopover && !queryPopover.contains(e.target)) closePopover();
  }

  function showQueryPopover(anchorBtn) {
    closePopover();
    var tab = activeTab();
    var q = QUERY_FOR_TAB[tab] || QUERY_FOR_TAB.overview;
    var fileUrl = QUERY_BASE_URL + "/" + q.file;
    var fileName = q.file.split("/").pop();

    var pop = document.createElement("div");
    pop.setAttribute("role", "dialog");
    pop.setAttribute("aria-label", "SPARQL query for this view");
    pop.style.position = "fixed";
    pop.style.zIndex = "10000";
    pop.style.maxWidth = "min(360px, 90vw)";
    pop.style.padding = "12px 14px";
    pop.style.borderRadius = "10px";
    pop.style.background = "var(--bg-card)";
    pop.style.color = "var(--text)";
    pop.style.border = "1px solid var(--border)";
    pop.style.boxShadow = "var(--shadow-pop, 0 6px 24px rgba(0,0,0,0.4))";
    pop.style.font = "13px/1.45 system-ui, sans-serif";

    var esc = WD.escHtml || function (s) { return String(s); };
    pop.innerHTML =
      '<div style="font-weight:600;margin-bottom:6px;">Competency question</div>' +
      '<div style="margin-bottom:8px;color:var(--text-sub);">' + esc(q.desc) + '</div>' +
      '<div style="margin-bottom:10px;">Behind the ' + esc(tab) +
        ' view: <code style="background:var(--bg-card2);padding:1px 5px;border-radius:4px;">' +
        esc(fileName) + '</code></div>' +
      '<div style="font-size:11px;color:var(--text-faint);margin-bottom:10px;">' +
        'Opens the query file in the repository. The static page does not ' +
        'execute SPARQL.</div>';

    var actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "8px";
    actions.style.flexWrap = "wrap";

    var openBtn = document.createElement("a");
    openBtn.href = fileUrl;
    openBtn.target = "_blank";
    openBtn.rel = "noopener noreferrer";
    openBtn.textContent = "Open " + fileName;
    styleLink(openBtn);
    openBtn.addEventListener("click", function () { closePopover(); });

    var allBtn = document.createElement("a");
    allBtn.href = QUERY_DIR_URL;
    allBtn.target = "_blank";
    allBtn.rel = "noopener noreferrer";
    allBtn.textContent = "All queries";
    styleLink(allBtn, true);
    allBtn.addEventListener("click", function () { closePopover(); });

    actions.appendChild(openBtn);
    actions.appendChild(allBtn);
    pop.appendChild(actions);
    document.body.appendChild(pop);

    // Position under the anchor button.
    var r = anchorBtn.getBoundingClientRect();
    var pr = pop.getBoundingClientRect();
    var left = Math.max(8, Math.min(r.left, window.innerWidth - pr.width - 8));
    var top = r.bottom + 8;
    if (top + pr.height > window.innerHeight - 8) {
      top = Math.max(8, r.top - pr.height - 8);
    }
    pop.style.left = left + "px";
    pop.style.top = top + "px";

    queryPopover = pop;
    // Defer listener attachment so the opening click does not close it.
    setTimeout(function () {
      document.addEventListener("keydown", onPopoverKey, true);
      document.addEventListener("click", onDocClick, true);
    }, 0);
  }

  function styleLink(a, secondary) {
    a.style.display = "inline-block";
    a.style.padding = "6px 12px";
    a.style.borderRadius = "6px";
    a.style.textDecoration = "none";
    a.style.font = "600 12px/1 system-ui, sans-serif";
    a.style.cursor = "pointer";
    if (secondary) {
      a.style.background = "transparent";
      a.style.color = "var(--text-sub)";
      a.style.border = "1px solid var(--border)";
    } else {
      a.style.background = "var(--accent)";
      a.style.color = "#fff";
      a.style.border = "1px solid var(--accent)";
    }
  }

  // -------------------------------------------------------------------------
  // Export menu (groups the chart/data actions under one toolbar button)
  // -------------------------------------------------------------------------
  var exportMenu = null;
  function closeMenu() {
    if (exportMenu && exportMenu.parentNode) {
      exportMenu.parentNode.removeChild(exportMenu);
    }
    exportMenu = null;
    document.removeEventListener("keydown", onMenuKey, true);
    document.removeEventListener("click", onMenuDocClick, true);
  }
  function onMenuKey(e) { if (e.key === "Escape") closeMenu(); }
  function onMenuDocClick(e) {
    if (exportMenu && !exportMenu.contains(e.target)) closeMenu();
  }

  function separator() {
    var sep = document.createElement("div");
    sep.style.height = "1px";
    sep.style.background = "var(--border)";
    sep.style.margin = "6px 4px";
    return sep;
  }

  function menuItem(label, sub, fn) {
    var it = document.createElement("button");
    it.type = "button";
    it.style.display = "block";
    it.style.width = "100%";
    it.style.textAlign = "left";
    it.style.padding = "8px 12px";
    it.style.background = "transparent";
    it.style.border = "0";
    it.style.color = "var(--text)";
    it.style.cursor = "pointer";
    it.style.font = "13px/1.3 system-ui, sans-serif";
    it.style.borderRadius = "6px";
    var esc = WD.escHtml || function (s) { return String(s); };
    it.innerHTML = '<span style="display:block;">' + esc(label) + '</span>' +
      (sub ? '<span style="display:block;font-size:11px;color:var(--text-faint);">' +
        esc(sub) + '</span>' : "");
    if (!reduced) {
      it.addEventListener("mouseenter", function () { it.style.background = "var(--bg-card2)"; });
      it.addEventListener("mouseleave", function () { it.style.background = "transparent"; });
    }
    it.addEventListener("click", function () { closeMenu(); fn(); });
    return it;
  }

  function showExportMenu(anchorBtn) {
    if (exportMenu) { closeMenu(); return; }
    var m = document.createElement("div");
    m.setAttribute("role", "menu");
    m.style.position = "fixed";
    m.style.zIndex = "10000";
    m.style.minWidth = "230px";
    m.style.padding = "6px";
    m.style.borderRadius = "10px";
    m.style.background = "var(--bg-card)";
    m.style.border = "1px solid var(--border)";
    m.style.boxShadow = "var(--shadow-pop, 0 6px 24px rgba(0,0,0,0.4))";

    var name = activeChartName();
    m.appendChild(menuItem("Chart as SVG", "word-drift-" + name + ".svg", exportSvg));
    m.appendChild(menuItem("Chart as PNG", "word-drift-" + name + ".png", exportPng));
    m.appendChild(separator());
    m.appendChild(menuItem("Words as CSV", "all words, light fields", exportCsv));

    // Context-aware exports for the open word or trigger. Source URLs are not
    // in the page model, so these are faithful-but-partial snippets; the JSON
    // option is lossless for what the page holds. Both link back to the dataset.
    var w = openWord();
    var tr = openTrigger();
    if (w) {
      m.appendChild(separator());
      m.appendChild(menuItem("This word as Turtle",
        slug(w.writtenForm) + ".ttl (partial: no source URLs)", exportOpenWordTtl));
      m.appendChild(menuItem("This word as JSON",
        slug(w.writtenForm) + ".json (full in-memory record)", exportOpenWordJson));
    } else if (tr) {
      m.appendChild(separator());
      var tn = slug(tr.id.split("/").pop());
      m.appendChild(menuItem("This trigger as Turtle",
        "trigger-" + tn + ".ttl (trigger + affected words)", exportOpenTriggerTtl));
      m.appendChild(menuItem("This trigger as JSON",
        "trigger-" + tn + ".json (full in-memory record)", exportOpenTriggerJson));
    }

    document.body.appendChild(m);
    var r = anchorBtn.getBoundingClientRect();
    var mr = m.getBoundingClientRect();
    var left = Math.max(8, Math.min(r.left, window.innerWidth - mr.width - 8));
    m.style.left = left + "px";
    m.style.top = (r.bottom + 8) + "px";

    exportMenu = m;
    setTimeout(function () {
      document.addEventListener("keydown", onMenuKey, true);
      document.addEventListener("click", onMenuDocClick, true);
    }, 0);
  }

  // -------------------------------------------------------------------------
  // Register toolbar buttons
  // -------------------------------------------------------------------------
  WD.registerToolbarButton({
    label: "Export",
    title: "Export the current chart (SVG/PNG) or the word list (CSV)",
    onClick: function (e) {
      showExportMenu(e.currentTarget || e.target);
    }
  });

  WD.registerToolbarButton({
    label: "Copy link",
    title: "Copy a permalink to the current view (deep-links the open word/trigger)",
    onClick: copyLink
  });

  WD.registerToolbarButton({
    label: "Cite",
    title: "Copy a CC-BY citation for the current word, trigger, or dataset",
    onClick: copyCitation
  });

  WD.registerToolbarButton({
    label: "Query",
    title: "Show the SPARQL competency question behind this view (opens the repo)",
    onClick: function (e) {
      showQueryPopover(e.currentTarget || e.target);
    }
  });
})();
