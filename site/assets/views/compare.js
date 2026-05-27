// WORD-DRIFT view module: Compare
// Cross-lingual comparison view: pairs of Words that are the SAME concept across
// German and English, taken from the EXPLICIT drift:crossLingualOf links in the
// data (exported as word.crossLingualOf). Pairs are NOT inferred from a shared
// trigger: COVID-19 independently reframed "Querdenker" (de) and "doomscrolling"
// (en), but those are not translation equivalents and must never be paired. When
// both partners of a genuine pair happen to share a trigger, that trigger is
// shown as CONTEXT only; it never creates the pairing.
// Contract: see assets/views/API.md.
(function () {
  "use strict";
  if (!window.WD || typeof window.WD.registerView !== "function") {
    console.warn("compare.js: window.WD not ready");
    return;
  }

  // --- helpers ---------------------------------------------------------------

  // Index light words by IRI id (crossLingualOf carries word ids).
  function buildWordById() {
    var byId = Object.create(null);
    var words = WD.words || [];
    for (var i = 0; i < words.length; i++) byId[words[i].id] = words[i];
    return byId;
  }

  // For a given written form + trigger label, find the flat event whose top
  // cause names that trigger, returning { type, confidence } for that link.
  // Falls back to the word's first flat event if no labelled cause matches.
  function linkForWord(writtenForm, triggerLabel) {
    var flat = WD.driftEventsFlat || [];
    var fallback = null;
    for (var i = 0; i < flat.length; i++) {
      var f = flat[i];
      if (f.word !== writtenForm) continue;
      if (!fallback) fallback = f;
      var causes = f.causes || [];
      for (var j = 0; j < causes.length; j++) {
        if (triggerLabel && causes[j].triggerLabel === triggerLabel) {
          return {
            type: f.type || null,
            confidence: typeof causes[j].confidence === "number" ? causes[j].confidence : null,
            flat: f,
          };
        }
      }
    }
    if (fallback) {
      var c0 = (fallback.causes || [])[0];
      return {
        type: fallback.type || null,
        confidence: c0 && typeof c0.confidence === "number" ? c0.confidence : null,
        flat: fallback,
      };
    }
    return { type: null, confidence: null, flat: null };
  }

  // Distinct trigger labels naming a cause for this written form (via flat).
  function triggerLabelsForWord(writtenForm) {
    var flat = WD.driftEventsFlat || [];
    var set = Object.create(null);
    for (var i = 0; i < flat.length; i++) {
      var f = flat[i];
      if (f.word !== writtenForm) continue;
      var causes = f.causes || [];
      for (var j = 0; j < causes.length; j++) {
        if (causes[j].triggerLabel) set[causes[j].triggerLabel] = true;
      }
    }
    return set;
  }

  // For a de/en pair, find a trigger LABEL that both partners share (context
  // only). Returns the label or null. The pairing itself never depends on this.
  function sharedTriggerLabel(deWord, enWord) {
    var deLabels = triggerLabelsForWord(deWord.writtenForm);
    var enLabels = triggerLabelsForWord(enWord.writtenForm);
    var shared = null;
    for (var lbl in enLabels) {
      if (deLabels[lbl]) { shared = lbl; break; }
    }
    return shared;
  }

  // Resolve a trigger LABEL to its impact record (id + year + category) so the
  // context node can deep-link to the trigger detail.
  function triggerByLabel(label) {
    if (!label) return null;
    var impact = WD.triggerImpact || [];
    for (var i = 0; i < impact.length; i++) {
      if (impact[i].label === label) return impact[i];
    }
    return null;
  }

  // Build cross-lingual pairs from EXPLICIT crossLingualOf links only.
  // Each pair is de <-> en; deduped by (deId|enId). A shared trigger, if any,
  // is attached as context.
  function findCrossLingual() {
    var byId = buildWordById();
    var words = WD.words || [];
    var seen = Object.create(null);
    var rows = [];

    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      var links = w.crossLingualOf || [];
      for (var k = 0; k < links.length; k++) {
        var partner = byId[links[k]];
        if (!partner) continue;
        // Orient as de <-> en. Skip same-language links (data is en<->de only,
        // but stay defensive) and anything we can't orient.
        var deW = null, enW = null;
        if (w.language === "de" && partner.language === "en") { deW = w; enW = partner; }
        else if (w.language === "en" && partner.language === "de") { deW = partner; enW = w; }
        else { continue; }

        var key = deW.id + "|" + enW.id;
        if (seen[key]) continue;
        seen[key] = true;

        var label = sharedTriggerLabel(deW, enW);
        var trig = triggerByLabel(label);

        rows.push({
          de: makeEntry(deW, label),
          en: makeEntry(enW, label),
          sharedTriggerLabel: label,
          triggerId: trig ? trig.trigger : null,
          triggerYear: trig ? trig.year : null,
          triggerCategory: trig ? trig.category : null,
        });
      }
    }

    // Sort: pairs WITH a shared trigger first (by year desc), then the rest
    // alphabetically by the English form.
    rows.sort(function (a, b) {
      var aHas = a.sharedTriggerLabel ? 1 : 0;
      var bHas = b.sharedTriggerLabel ? 1 : 0;
      if (aHas !== bHas) return bHas - aHas;
      if (aHas) {
        var ay = a.triggerYear == null ? -1e9 : a.triggerYear;
        var by = b.triggerYear == null ? -1e9 : b.triggerYear;
        if (ay !== by) return by - ay;
      }
      return a.en.writtenForm.localeCompare(b.en.writtenForm);
    });

    return { rows: rows, pairCount: rows.length };
  }

  function makeEntry(lightWord, triggerLabel) {
    var link = linkForWord(lightWord.writtenForm, triggerLabel);
    return {
      writtenForm: lightWord.writtenForm,
      lang: lightWord.language,
      word: lightWord, // light word (for openWord)
      type: link.type,
      confidence: link.confidence,
      flat: link.flat,
    };
  }

  function pct(c) {
    return c == null ? "n/a" : Math.round(c * 100) + "%";
  }

  // --- rendering -------------------------------------------------------------

  function onActivate(panelEl) {
    panelEl.innerHTML = "";

    var result = findCrossLingual();
    var rows = result.rows;

    if (!rows.length) {
      var empty = document.createElement("p");
      empty.className = "empty-msg";
      empty.textContent =
        "No cross-lingual pairs found: no Word is linked to a same-concept Word " +
        "in the other language (drift:crossLingualOf).";
      panelEl.appendChild(empty);
      return;
    }

    var reduce = !!WD.prefersReducedMotion;

    var root = document.createElement("div");
    root.style.padding = "1rem 1.25rem 2rem";
    root.style.maxWidth = "1100px";
    root.style.margin = "0 auto";

    // Intro + summary.
    var head = document.createElement("div");
    head.style.marginBottom = "1.1rem";

    var title = document.createElement("h2");
    title.textContent = "Cross-lingual pairs";
    title.style.cssText = "font-size:1.05rem;font-weight:700;margin:0 0 0.35rem;color:var(--text);";
    head.appendChild(title);

    var lede = document.createElement("p");
    lede.style.cssText = "font-size:0.85rem;color:var(--text-sub);margin:0 0 0.7rem;line-height:1.5;";
    lede.textContent =
      "Words that are the same concept across German and English, linked explicitly " +
      "(drift:crossLingualOf). Each row pairs the German side (left) with its English " +
      "equivalent (right). Where both adopted their new sense under the same real-world " +
      "trigger, that trigger is shown in the middle as context.";
    head.appendChild(lede);

    var withTrigger = 0;
    for (var t = 0; t < rows.length; t++) if (rows[t].sharedTriggerLabel) withTrigger++;

    var chips = document.createElement("div");
    chips.style.cssText = "display:flex;gap:0.5rem;flex-wrap:wrap;";
    chips.appendChild(statChip(rows.length + " DE-EN pairs"));
    chips.appendChild(statChip(withTrigger + " share a trigger"));
    head.appendChild(chips);

    root.appendChild(head);

    // Cards.
    var list = document.createElement("div");
    list.style.cssText = "display:flex;flex-direction:column;gap:0.9rem;";
    for (var i = 0; i < rows.length; i++) {
      list.appendChild(renderCard(rows[i], panelEl, reduce));
    }
    root.appendChild(list);

    panelEl.appendChild(root);
  }

  function statChip(text) {
    var el = document.createElement("span");
    el.className = "stat-chip";
    el.textContent = text;
    return el;
  }

  // One pair card: DE word | center (shared trigger context or plain link) | EN word.
  function renderCard(row, panelEl, reduce) {
    var card = document.createElement("div");
    card.style.cssText =
      "background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-lg);" +
      "padding:0.9rem 1rem 1rem;";

    // Header row: language labels.
    var header = document.createElement("div");
    header.style.cssText =
      "display:grid;grid-template-columns:1fr auto 1fr;align-items:center;" +
      "gap:0.5rem;margin-bottom:0.5rem;";
    header.appendChild(langTag("Deutsch", "left"));
    var spacer = document.createElement("span");
    spacer.textContent = row.triggerYear != null ? WD.fmtYear(row.triggerYear) : "";
    spacer.style.cssText =
      "font-family:var(--font-mono);font-size:0.72rem;color:var(--text-faint);text-align:center;";
    header.appendChild(spacer);
    header.appendChild(langTag("English", "right"));
    card.appendChild(header);

    // Body: bipartite layout with a center node.
    var rowH = 58;
    var bodyH = rowH;

    var body = document.createElement("div");
    body.style.cssText =
      "display:grid;grid-template-columns:1fr 150px 1fr;align-items:stretch;gap:0;";

    body.appendChild(wordColumn([row.de], "left", panelEl, reduce, rowH));
    body.appendChild(centerColumn(row, bodyH, reduce, panelEl));
    body.appendChild(wordColumn([row.en], "right", panelEl, reduce, rowH));

    card.appendChild(body);
    return card;
  }

  function langTag(label, side) {
    var el = document.createElement("span");
    el.textContent = label;
    el.style.cssText =
      "font-size:0.72rem;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;" +
      "color:var(--text-sub);" +
      (side === "left" ? "text-align:left;" : "text-align:right;");
    return el;
  }

  function wordColumn(entries, side, panelEl, reduce, rowH) {
    var col = document.createElement("div");
    col.style.cssText =
      "display:flex;flex-direction:column;justify-content:center;gap:0.45rem;" +
      (side === "left" ? "align-items:flex-end;" : "align-items:flex-start;");
    for (var i = 0; i < entries.length; i++) {
      col.appendChild(wordCard(entries[i], side, panelEl, reduce));
    }
    return col;
  }

  function wordCard(entry, side, panelEl, reduce) {
    var color = entry.flat ? WD.causeColor(entry.flat) : WD.dtColor(entry.type);
    var el = document.createElement("div");
    el.style.cssText =
      "display:inline-flex;flex-direction:column;gap:0.15rem;min-width:0;max-width:100%;" +
      "background:var(--bg-card2);border:1px solid var(--border);border-left:3px solid " +
      color + ";border-radius:8px;padding:0.4rem 0.6rem;cursor:pointer;" +
      (side === "left" ? "text-align:right;" : "text-align:left;") +
      (reduce ? "" : "transition:border-color 0.12s,background 0.12s;");

    var wf = document.createElement("span");
    wf.textContent = entry.writtenForm;
    wf.style.cssText = "font-weight:600;font-size:0.95rem;color:var(--text);";
    el.appendChild(wf);

    var meta = document.createElement("span");
    meta.style.cssText = "font-size:0.72rem;color:var(--text-sub);";
    var typeTxt = entry.type ? entry.type : "drift";
    meta.innerHTML =
      "<span style=\"color:" + color + ";font-weight:600;\">" + WD.escHtml(typeTxt) + "</span>" +
      " · conf " + WD.escHtml(pct(entry.confidence));
    el.appendChild(meta);

    var target = entry.word || entry.writtenForm;
    el.title = "Open " + entry.writtenForm + " (" + (entry.lang || "?") + ")";
    if (!reduce) {
      el.addEventListener("mouseenter", function () {
        el.style.borderColor = color;
        el.style.background = "var(--bg-card)";
      });
      el.addEventListener("mouseleave", function () {
        el.style.borderColor = "var(--border)";
        el.style.borderLeftColor = color;
        el.style.background = "var(--bg-card2)";
      });
    }
    WD.makeActivatable(el, function () {
      WD.openWord(target);
    });
    return el;
  }

  // Center column: a node linking the pair. If the pair shares a trigger, the
  // node is the (clickable) trigger as CONTEXT; otherwise a neutral link glyph.
  function centerColumn(row, bodyH, reduce, panelEl) {
    var W = 150;
    var hasTrigger = !!row.sharedTriggerLabel;
    var center = document.createElement("div");
    center.style.cssText =
      "position:relative;display:flex;align-items:center;justify-content:center;min-height:" +
      bodyH + "px;";

    var svg = d3
      .create("svg")
      .attr("width", W)
      .attr("height", bodyH)
      .attr("viewBox", "0 0 " + W + " " + bodyH)
      .style("position", "absolute")
      .style("inset", "0")
      .style("overflow", "visible");

    var cx = W / 2;
    var cy = bodyH / 2;
    var deColor = row.de.flat ? WD.causeColor(row.de.flat) : WD.dtColor(row.de.type);
    var enColor = row.en.flat ? WD.causeColor(row.en.flat) : WD.dtColor(row.en.type);
    var linkColor = "var(--border)";

    function draw(x, color) {
      var mx = (x + cx) / 2;
      svg
        .append("path")
        .attr("d", "M" + x + "," + cy + "C" + mx + "," + cy + " " + mx + "," + cy + " " + cx + "," + cy)
        .attr("fill", "none")
        .attr("stroke", hasTrigger ? color : linkColor)
        .attr("stroke-width", 1.8)
        .attr("stroke-opacity", hasTrigger ? 0.7 : 0.6)
        .attr("stroke-dasharray", hasTrigger ? null : "3,3");
    }
    draw(4, deColor);
    draw(W - 4, enColor);

    center.appendChild(svg.node());

    var wrap = document.createElement("div");
    wrap.style.cssText =
      "position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;gap:0.35rem;";

    if (hasTrigger) {
      // Clickable trigger node (CONTEXT only).
      var node = document.createElement("button");
      node.type = "button";
      node.title = "Shared trigger (context): " + row.sharedTriggerLabel;
      node.style.cssText =
        "width:54px;height:54px;border-radius:50%;" +
        "background:var(--bg-panel);border:2px solid var(--gold);color:var(--gold);" +
        "display:flex;align-items:center;justify-content:center;cursor:pointer;font-family:var(--font);" +
        "box-shadow:0 0 0 4px var(--bg-card);" +
        (reduce ? "" : "transition:transform 0.12s,box-shadow 0.12s;");
      node.setAttribute("aria-label", "Open shared trigger (context): " + row.sharedTriggerLabel);

      var glyph = document.createElement("span");
      glyph.textContent = "⚡"; // lightning: a shared trigger (context)
      glyph.style.cssText = "font-size:1.1rem;line-height:1;pointer-events:none;";
      node.appendChild(glyph);

      if (!reduce) {
        node.addEventListener("mouseenter", function () { node.style.transform = "scale(1.08)"; });
        node.addEventListener("mouseleave", function () { node.style.transform = "scale(1)"; });
      }
      if (row.triggerId) {
        node.addEventListener("click", function () { WD.showTrigger(row.triggerId); });
      } else {
        node.disabled = true;
        node.style.cursor = "default";
      }
      wrap.appendChild(node);

      var lbl = document.createElement("span");
      lbl.textContent = row.sharedTriggerLabel;
      lbl.style.cssText =
        "max-width:140px;font-size:0.68rem;line-height:1.25;text-align:center;color:var(--text-sub);" +
        "display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;";
      wrap.appendChild(lbl);
    } else {
      // Neutral cross-lingual link node (no shared trigger).
      var linkNode = document.createElement("span");
      linkNode.title = "Cross-lingual equivalent";
      linkNode.style.cssText =
        "width:40px;height:40px;border-radius:50%;background:var(--bg-panel);" +
        "border:1.5px dashed var(--border);color:var(--text-sub);" +
        "display:flex;align-items:center;justify-content:center;font-size:1rem;" +
        "box-shadow:0 0 0 4px var(--bg-card);";
      linkNode.textContent = "⇄"; // left-right arrow: translation equivalents
      linkNode.setAttribute("aria-label", "Cross-lingual equivalent");
      wrap.appendChild(linkNode);

      var lbl2 = document.createElement("span");
      lbl2.textContent = "same concept";
      lbl2.style.cssText =
        "max-width:140px;font-size:0.68rem;line-height:1.25;text-align:center;color:var(--text-faint);";
      wrap.appendChild(lbl2);
    }

    center.appendChild(wrap);
    return center;
  }

  WD.registerView("compare", {
    label: "Compare",
    panelId: "panel-compare",
    onActivate: onActivate,
  });
})();
