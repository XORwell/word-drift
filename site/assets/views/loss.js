// WORD-DRIFT view module: Lexical loss
// The words we have "lost" because they became poisoned -- you can no longer
// use them neutrally -- set against the few that got reclaimed.
// Contract: see assets/views/API.md and ../../DATA-CONTRACT.md.
//
// Framing (honest, data-bound)
// ----------------------------
// Like colours fading to grey, words can drift to a negative connotation and
// lose their neutral or positive usability. We read this straight off the
// curated drift events:
//
//   POISONED  = toConn negative AND fromConn NOT negative
//               (a word that drifted into a negative connotation; the loss)
//   RECLAIMED = fromConn negative AND toConn NOT negative
//               (a word that got its colour back; the counterpoint)
//
// The colour-shift encoding is the heart of the view: every card paints the
// from-connotation dot and the to-connotation dot with WD.connColor and puts
// an arrow between them, so a poisoned word literally reads as colour draining
// toward the negative hue, and a reclaimed word reads as colour returning.
//
// This is the curated WORD-DRIFT corpus, not a measurement of the whole
// language. The counts below describe the curated set only.
(function () {
  "use strict";
  if (!window.WD || typeof window.WD.registerView !== "function") {
    console.warn("loss.js: window.WD not ready");
    return;
  }

  // Case-insensitive "negative" connotation test. null/undefined => not negative.
  function isNeg(conn) {
    return typeof conn === "string" && conn.trim().toLowerCase() === "negative";
  }

  // A "striking" rank for poisoned words: positive->negative is the sharpest
  // loss (you fall furthest), then neutral->negative, then anything else that
  // still qualifies. Lower number = more striking, sorted first.
  function poisonRank(e) {
    var f = (e.fromConn || "").trim().toLowerCase();
    if (f === "positive") return 0;
    if (f === "neutral") return 1;
    return 2;
  }
  // Mirror for reclaimed: negative->positive is the strongest reclamation.
  function reclaimRank(e) {
    var t = (e.toConn || "").trim().toLowerCase();
    if (t === "positive") return 0;
    if (t === "neutral") return 1;
    return 2;
  }

  function yearKey(e) {
    return e.year != null && isFinite(e.year) ? e.year : -Infinity;
  }

  WD.registerView("loss", {
    label: "Lexical loss",
    panelId: "panel-loss",
    onActivate: function (panelEl) {
      panelEl.innerHTML = "";

      var flat = WD.driftEventsFlat || [];

      // POISONED: drifted to negative, was not negative before (the loss).
      var poisoned = flat.filter(function (e) {
        return e && isNeg(e.toConn) && !isNeg(e.fromConn);
      });
      // RECLAIMED: was negative, no longer negative (the counterpoint).
      var reclaimed = flat.filter(function (e) {
        return e && isNeg(e.fromConn) && !isNeg(e.toConn);
      });

      // Sort poisoned most-striking-first: by valence drop, then by recency.
      poisoned.sort(function (a, b) {
        var r = poisonRank(a) - poisonRank(b);
        if (r !== 0) return r;
        return yearKey(b) - yearKey(a);
      });
      reclaimed.sort(function (a, b) {
        var r = reclaimRank(a) - reclaimRank(b);
        if (r !== 0) return r;
        return yearKey(b) - yearKey(a);
      });

      var nPoison = poisoned.length;
      var nReclaim = reclaimed.length;

      // ---- scaffold ----------------------------------------------------------
      var root = document.createElement("div");
      root.className = "wd-loss";

      if (!nPoison && !nReclaim) {
        root.innerHTML =
          '<p class="empty-msg">No connotation-shift events in the curated ' +
          "corpus yet, so there is nothing to read as lexical loss.</p>";
        panelEl.appendChild(root);
        return;
      }

      // 1) Honest intro -------------------------------------------------------
      var intro = document.createElement("div");
      intro.className = "wd-loss-intro";
      intro.innerHTML =
        '<h2 class="wd-loss-h">Lexical loss</h2>' +
        '<p class="wd-loss-lede">Like colours fading to grey, a word can drift ' +
        "to a negative connotation and lose its neutral use: once it is " +
        "poisoned you can no longer reach for it without dragging the new " +
        "meaning along, and with the word goes a slice of cognitive space. " +
        "In the curated WORD-DRIFT corpus <strong>" + WD.escHtml(String(nPoison)) +
        "</strong> word" + (nPoison === 1 ? "" : "s") + " drifted to a negative " +
        "connotation (lost neutral usability), versus <strong>" +
        WD.escHtml(String(nReclaim)) + "</strong> reclaimed. " +
        "These are counts within the curated set, not a claim about the whole " +
        "language.</p>";
      root.appendChild(intro);

      // 2) Headline asymmetry stat + colour-drain visual ----------------------
      var negCol = WD.connColor("negative");
      var posCol = WD.connColor("positive");
      var total = nPoison + nReclaim;
      var poisonPct = total > 0 ? (nPoison / total) * 100 : 0;
      var reclaimPct = total > 0 ? (nReclaim / total) * 100 : 0;
      var net = nPoison - nReclaim;

      var stat = document.createElement("div");
      stat.className = "wd-loss-stat";
      stat.innerHTML =
        '<div class="wd-loss-stat-nums">' +
          '<span class="wd-loss-stat-cell">' +
            '<span class="wd-loss-stat-n" style="color:' + negCol + '">' +
              WD.escHtml(String(nPoison)) + "</span>" +
            '<span class="wd-loss-stat-lbl">poisoned</span>' +
          "</span>" +
          '<span class="wd-loss-stat-vs">vs</span>' +
          '<span class="wd-loss-stat-cell">' +
            '<span class="wd-loss-stat-n" style="color:' + posCol + '">' +
              WD.escHtml(String(nReclaim)) + "</span>" +
            '<span class="wd-loss-stat-lbl">reclaimed</span>' +
          "</span>" +
          '<span class="wd-loss-stat-net">net colour loss <strong>' +
            (net >= 0 ? "+" : "") + WD.escHtml(String(net)) + "</strong></span>" +
        "</div>" +
        // a single bar: the negative share draining the positive one.
        '<div class="wd-loss-bar" role="img" aria-label="' +
          WD.escHtml(nPoison + " poisoned versus " + nReclaim + " reclaimed") + '">' +
          '<span class="wd-loss-bar-seg" style="width:' + poisonPct.toFixed(2) +
            '%;background:' + negCol + '"></span>' +
          '<span class="wd-loss-bar-seg" style="width:' + reclaimPct.toFixed(2) +
            '%;background:' + posCol + '"></span>' +
        "</div>" +
        '<p class="wd-loss-bar-cap">The bar is the corpus split: colour ' +
          "draining toward the negative hue is the loss, the sliver of " +
          "positive hue is what came back.</p>";
      root.appendChild(stat);

      // 3) Sections -----------------------------------------------------------
      root.appendChild(buildSection({
        kind: "poison",
        title: "Poisoned",
        sub: "Words that lost neutral or positive use and drifted negative.",
        events: poisoned,
        emptyMsg: "No poisoned words in the curated corpus.",
        primary: true,
      }));

      root.appendChild(buildSection({
        kind: "reclaim",
        title: "Reclaimed",
        sub: "The counterpoint: words that got their colour back.",
        events: reclaimed,
        emptyMsg: "No reclaimed words in the curated corpus.",
        primary: false,
      }));

      panelEl.appendChild(root);

      // --- section builder ---------------------------------------------------
      function buildSection(opts) {
        var sec = document.createElement("section");
        sec.className = "wd-loss-section" + (opts.primary ? " is-primary" : "");

        var hd = document.createElement("div");
        hd.className = "wd-loss-sec-head";
        hd.innerHTML =
          '<h3 class="wd-loss-sec-h">' + WD.escHtml(opts.title) +
            ' <span class="wd-loss-sec-count">' +
            WD.escHtml(String(opts.events.length)) + "</span></h3>" +
          '<p class="wd-loss-sec-sub">' + WD.escHtml(opts.sub) + "</p>";
        sec.appendChild(hd);

        if (!opts.events.length) {
          var em = document.createElement("p");
          em.className = "empty-msg";
          em.textContent = opts.emptyMsg;
          sec.appendChild(em);
          return sec;
        }

        var grid = document.createElement("div");
        grid.className = "wd-loss-grid";
        opts.events.forEach(function (e) {
          grid.appendChild(buildCard(e, opts.kind));
        });
        sec.appendChild(grid);
        return sec;
      }

      // --- card builder ------------------------------------------------------
      function buildCard(e, kind) {
        var card = document.createElement("div");
        card.className = "wd-loss-card wd-loss-card-" + kind;

        var word = e.word == null ? "" : String(e.word);
        var lang = e.lang ? String(e.lang) : "";
        var type = e.type ? String(e.type) : "";
        var fromCol = WD.connColor(e.fromConn);
        var toCol = WD.connColor(e.toConn);

        // Title row: clickable word + language badge.
        var titleRow = document.createElement("div");
        titleRow.className = "wd-loss-card-title";

        var wordEl = document.createElement("span");
        wordEl.className = "wd-loss-word";
        wordEl.textContent = word;
        wordEl.title = "Open " + word + " in the word detail";
        WD.makeActivatable(wordEl, function () {
          // Resolve the light word by written form so detail opens reliably.
          var lw = findLightWord(word, lang);
          WD.openWord(lw || word);
        });
        titleRow.appendChild(wordEl);

        if (lang) {
          var langEl = document.createElement("span");
          langEl.className = "wd-loss-lang";
          langEl.textContent = lang.toUpperCase();
          titleRow.appendChild(langEl);
        }
        card.appendChild(titleRow);

        // The colour shift: from-dot -> to-dot, the visual heart.
        var arc = document.createElement("div");
        arc.className = "wd-loss-arc";
        arc.innerHTML =
          '<span class="wd-loss-conn">' +
            '<span class="conn-dot" style="background:' + fromCol + '"></span>' +
            '<span class="wd-loss-conn-lbl">' +
              WD.escHtml(connLabel(e.fromConn)) + "</span>" +
          "</span>" +
          '<span class="wd-loss-arrow" aria-hidden="true">' +
            (kind === "reclaim" ? "&#8592;&#8594;" : "&#8594;") + "</span>" +
          '<span class="wd-loss-conn">' +
            '<span class="conn-dot" style="background:' + toCol + '"></span>' +
            '<span class="wd-loss-conn-lbl">' +
              WD.escHtml(connLabel(e.toConn)) + "</span>" +
          "</span>";
        arc.setAttribute(
          "aria-label",
          connLabel(e.fromConn) + " to " + connLabel(e.toConn) + " connotation"
        );
        card.appendChild(arc);

        // Meta: drift type + year.
        var meta = document.createElement("div");
        meta.className = "wd-loss-meta";
        if (type) {
          meta.innerHTML +=
            '<span class="wd-loss-type" style="border-color:' +
            colorMix(WD.dtColor(type)) + ';color:' + WD.dtColor(type) + '">' +
            WD.escHtml(type) + "</span>";
        }
        meta.innerHTML +=
          '<span class="wd-loss-year">' +
          WD.escHtml(WD.fmtYear(e.year != null ? e.year : null)) + "</span>";
        card.appendChild(meta);

        // Trigger: clickable when present.
        var cause = (e.causes && e.causes.length) ? e.causes[0] : null;
        if (e.hasTrigger && cause && cause.triggerLabel) {
          var trig = document.createElement("div");
          trig.className = "wd-loss-trigger";
          var tlabel = document.createElement("span");
          tlabel.className = "wd-loss-trigger-label";
          tlabel.textContent = cause.triggerLabel;
          // Try to resolve the trigger IRI by matching label, so showTrigger
          // can navigate; fall back to a plain (non-clickable) label.
          var triggerId = findTriggerId(cause.triggerLabel);
          if (triggerId) {
            tlabel.classList.add("is-link");
            tlabel.title = "Show this trigger";
            WD.makeActivatable(tlabel, function () {
              WD.showTrigger(triggerId);
            });
          }
          trig.innerHTML = '<span class="wd-loss-trigger-pre">trigger</span>';
          trig.appendChild(tlabel);
          card.appendChild(trig);
        } else {
          var noTrig = document.createElement("div");
          noTrig.className = "wd-loss-trigger wd-loss-trigger-none";
          noTrig.innerHTML =
            '<span class="wd-loss-trigger-pre">trigger</span>' +
            '<span class="wd-loss-trigger-label">none proposed</span>';
          card.appendChild(noTrig);
        }

        return card;
      }
    },
  });

  // Connotation label for display ("unknown" when null/blank).
  function connLabel(conn) {
    if (typeof conn !== "string" || !conn.trim()) return "unknown";
    return conn.trim();
  }

  // border colour from a hex drift-type colour at low opacity.
  function colorMix(hex) {
    return "color-mix(in srgb, " + hex + " 42%, transparent)";
  }

  // Resolve a light word by written form (and language when given) so openWord
  // gets an object key rather than a bare string when possible.
  function findLightWord(writtenForm, lang) {
    var words = WD.words || [];
    var byForm = null;
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (w.writtenForm !== writtenForm) continue;
      if (lang && w.language && w.language !== lang) {
        if (!byForm) byForm = w; // remember a form-only match as fallback
        continue;
      }
      return w;
    }
    return byForm;
  }

  // Resolve a trigger IRI by exact label match (triggers carry labels, the
  // flat events only carry the label string).
  function findTriggerId(label) {
    if (!label) return null;
    var trigs = WD.triggers || [];
    for (var i = 0; i < trigs.length; i++) {
      if (trigs[i].label === label) return trigs[i].id;
    }
    return null;
  }

  // ---- scoped styles (injected once) --------------------------------------
  if (!document.getElementById("wd-loss-style")) {
    var css = document.createElement("style");
    css.id = "wd-loss-style";
    css.textContent = [
      "#panel-loss { padding: 1.25rem 2rem 2rem; }",
      ".wd-loss { max-width: 1100px; }",
      ".wd-loss-intro { margin-bottom: 1.1rem; }",
      ".wd-loss-h { margin: 0 0 0.4rem; font-size: 1.35rem; color: var(--text); letter-spacing: -0.01em; }",
      ".wd-loss-lede { margin: 0; font-size: 0.9rem; line-height: 1.6; color: var(--text-sub); max-width: 72ch; }",
      ".wd-loss-lede strong { color: var(--text); }",
      // headline stat
      ".wd-loss-stat { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1rem 1.1rem; margin-bottom: 1.4rem; }",
      ".wd-loss-stat-nums { display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.5rem 1.1rem; }",
      ".wd-loss-stat-cell { display: inline-flex; align-items: baseline; gap: 0.4rem; }",
      ".wd-loss-stat-n { font-size: 2rem; font-weight: 800; line-height: 1; letter-spacing: -0.02em; }",
      ".wd-loss-stat-lbl { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-sub); }",
      ".wd-loss-stat-vs { font-size: 0.78rem; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.08em; }",
      ".wd-loss-stat-net { margin-left: auto; font-size: 0.78rem; color: var(--text-sub); }",
      ".wd-loss-stat-net strong { color: var(--text); font-size: 0.95rem; }",
      ".wd-loss-bar { display: flex; width: 100%; height: 14px; border-radius: 7px; overflow: hidden; margin: 0.85rem 0 0.5rem; background: var(--bg-card2); }",
      ".wd-loss-bar-seg { display: block; height: 100%; }",
      ".wd-loss-bar-cap { margin: 0; font-size: 0.72rem; line-height: 1.5; color: var(--text-faint); max-width: 70ch; }",
      // sections
      ".wd-loss-section { margin-bottom: 1.6rem; }",
      ".wd-loss-sec-head { border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; margin-bottom: 0.85rem; }",
      ".wd-loss-sec-h { margin: 0 0 0.15rem; font-size: 1.05rem; color: var(--text); }",
      ".wd-loss-section.is-primary .wd-loss-sec-h { font-size: 1.2rem; }",
      ".wd-loss-sec-count { font-size: 0.8rem; font-weight: 600; color: var(--text-faint); margin-left: 0.25rem; }",
      ".wd-loss-sec-sub { margin: 0; font-size: 0.78rem; color: var(--text-sub); }",
      // grid + cards
      ".wd-loss-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 0.7rem; }",
      ".wd-loss-section.is-primary .wd-loss-grid { grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }",
      ".wd-loss-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 0.7rem 0.8rem; display: flex; flex-direction: column; gap: 0.45rem; }",
      ".wd-loss-card-poison { border-left: 3px solid var(--dt-pejoration); }",
      ".wd-loss-card-reclaim { border-left: 3px solid var(--dt-amelioration); }",
      ".wd-loss-card-title { display: flex; align-items: baseline; gap: 0.45rem; }",
      ".wd-loss-word { font-size: 1.05rem; font-weight: 700; color: var(--text); cursor: pointer; }",
      ".wd-loss-word:hover { color: var(--accent-hi); text-decoration: underline; }",
      ".wd-loss-word:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }",
      ".wd-loss-lang { font-size: 0.6rem; font-weight: 700; letter-spacing: 0.07em; color: var(--accent-hi); border: 1px solid var(--border); border-radius: 3px; padding: 0.05rem 0.3rem; }",
      // the colour-shift arc
      ".wd-loss-arc { display: flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; color: var(--text-sub); }",
      ".wd-loss-conn { display: inline-flex; align-items: center; gap: 0.3rem; }",
      ".wd-loss-arc .conn-dot { width: 12px; height: 12px; box-shadow: 0 0 0 1px color-mix(in srgb, var(--text) 18%, transparent); }",
      ".wd-loss-conn-lbl { font-weight: 600; }",
      ".wd-loss-arrow { color: var(--text-faint); font-weight: 700; letter-spacing: -0.02em; }",
      // meta
      ".wd-loss-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 0.4rem; }",
      ".wd-loss-type { font-size: 0.66rem; font-weight: 700; letter-spacing: 0.03em; text-transform: lowercase; border: 1px solid var(--border); border-radius: 4px; padding: 0.08rem 0.4rem; }",
      ".wd-loss-year { font-size: 0.72rem; color: var(--text-faint); font-family: var(--font-mono); }",
      // trigger
      ".wd-loss-trigger { display: flex; align-items: baseline; gap: 0.4rem; font-size: 0.74rem; }",
      ".wd-loss-trigger-pre { font-size: 0.6rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-faint); flex-shrink: 0; }",
      ".wd-loss-trigger-label { color: var(--text-sub); line-height: 1.4; }",
      ".wd-loss-trigger-label.is-link { color: var(--gold, var(--accent-hi)); cursor: pointer; }",
      ".wd-loss-trigger-label.is-link:hover { text-decoration: underline; }",
      ".wd-loss-trigger-label.is-link:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }",
      ".wd-loss-trigger-none .wd-loss-trigger-label { color: var(--text-faint); font-style: italic; }",
      "@media (max-width: 640px) { #panel-loss { padding: 0.75rem 1rem 1.5rem; } }",
    ].join("\n");
    document.head.appendChild(css);
  }
})();
