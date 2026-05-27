// WORD-DRIFT view module: Trends
// Drift-type composition over time + connotation-share trend.
// Contract: see assets/views/API.md and ../../DATA-CONTRACT.md.
//
// Design notes
// ------------
// The corpus spans ~350 BC to 2024 but is heavily back-loaded: only a handful
// of drift events predate 1800. A linear time axis would crush the antiquity
// points into invisible slivers, so we bucket *piecewise* and lay buckets out
// on an ordinal BAND scale (every bucket gets equal width). This keeps the
// ancient events visible while preserving decade-level detail for the modern
// corpus.
//
//   - year  < 1800 : bucket by century (e.g. "350 BC", "13th c.", "17th c.")
//   - year >= 1800 : bucket by decade  (e.g. "1900s", "1990s")
//
// Two stacked-bar charts:
//   (1) drift-type composition per bucket, with an Absolute <-> 100% toggle.
//       The normalised view is where the pejoration/amelioration balance over
//       time becomes legible.
//   (2) a slim connotation-share strip (negative / neutral / positive of the
//       *resulting* sense per event), always 100%-normalised.
//
// Source: WD.driftEventsFlat (year + type + toConn for every event, no detail
// fetch needed). WD.byDecadeType is an alternative but only carries decade
// buckets and no connotation, so the flat array is the honest primary source.
(function () {
  "use strict";
  if (!window.WD || typeof window.WD.registerView !== "function") {
    console.warn("trends.js: window.WD not ready");
    return;
  }

  var d3 = window.d3;

  // ---- bucketing -----------------------------------------------------------
  // A bucket has: key (sort order), label (display), and a midpoint year used
  // only for ordering. Returns null for events without a usable year.
  function bucketFor(year) {
    if (year == null || !isFinite(year)) return null;
    if (year < 1800) {
      // century bucket. For year y, the century start is floor.
      // BC handled by sign; "350 BC" etc.
      var cStart;
      var label;
      if (year < 0) {
        // BC century: -350 -> century starting at -399..-300, label "4th c. BC"
        cStart = Math.floor(year / 100) * 100; // e.g. -400
        var bcOrdinal = Math.abs(cStart) / 100; // 4 -> "4th c. BC"
        label = ordinal(bcOrdinal) + " c. BC";
      } else if (year < 100) {
        cStart = 0;
        label = "1st c.";
      } else {
        cStart = Math.floor(year / 100) * 100; // 1750 -> 1700
        label = ordinal(cStart / 100 + 1) + " c.";
      }
      return { key: cStart, label: label, mid: cStart + 50 };
    }
    // decade bucket
    var dStart = Math.floor(year / 10) * 10;
    return { key: dStart, label: dStart + "s", mid: dStart + 5 };
  }

  function ordinal(n) {
    var s = ["th", "st", "nd", "rd"];
    var v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  }

  // Drift types, in a stable stacking order. Discover from data, then keep a
  // deterministic order so colours/legend are consistent across renders.
  function orderedTypes(events) {
    var seen = {};
    events.forEach(function (e) { if (e.type) seen[e.type] = true; });
    return Object.keys(seen).sort(function (a, b) {
      return a.toLowerCase().localeCompare(b.toLowerCase());
    });
  }

  var CONN_ORDER = ["negative", "neutral", "positive"];

  // Build per-bucket aggregates from the flat events.
  function aggregate(events) {
    var byKey = new Map(); // key -> { key, label, mid, types:{type:n}, conns:{c:n}, total }
    events.forEach(function (e) {
      var b = bucketFor(e.year);
      if (!b) return;
      var rec = byKey.get(b.key);
      if (!rec) {
        rec = { key: b.key, label: b.label, mid: b.mid, types: {}, conns: {}, total: 0 };
        byKey.set(b.key, rec);
      }
      var t = e.type || "(unknown)";
      rec.types[t] = (rec.types[t] || 0) + 1;
      var c = e.toConn || "neutral";
      rec.conns[c] = (rec.conns[c] || 0) + 1;
      rec.total += 1;
    });
    return Array.from(byKey.values()).sort(function (a, b) { return a.mid - b.mid; });
  }

  // --------------------------------------------------------------------------
  WD.registerView("trends", {
    label: "Trends",
    panelId: "panel-trends",
    onActivate: function (panelEl) {
      panelEl.innerHTML = "";

      var events = (WD.driftEventsFlat || []).filter(function (e) {
        return e && e.year != null && isFinite(e.year);
      });

      if (!events.length) {
        panelEl.innerHTML = '<p class="empty-msg">No dated drift events to chart.</p>';
        return;
      }

      var buckets = aggregate(events);
      if (!buckets.length) {
        panelEl.innerHTML = '<p class="empty-msg">No drift events fall into a time bucket.</p>';
        return;
      }

      var types = orderedTypes(events);

      // ---- scaffold ----------------------------------------------------------
      var root = document.createElement("div");
      root.className = "wd-trends";

      var head = document.createElement("div");
      head.className = "wd-trends-head";
      head.innerHTML =
        '<div class="wd-trends-titles">' +
        '<h3 class="wd-trends-h">Drift-type composition over time</h3>' +
        '<p class="wd-trends-sub">' +
        WD.escHtml(String(events.length)) + " dated drift events, " +
        "bucketed by century before 1800 and by decade from 1800 on." +
        "</p>" +
        "</div>";

      // mode toggle
      var toggle = document.createElement("div");
      toggle.className = "wd-trends-toggle";
      toggle.setAttribute("role", "group");
      toggle.setAttribute("aria-label", "Chart mode");
      var btnAbs = mkToggleBtn("Absolute", true);
      var btnNorm = mkToggleBtn("100% share", false);
      toggle.appendChild(btnAbs);
      toggle.appendChild(btnNorm);
      head.appendChild(toggle);
      root.appendChild(head);

      // legend (drift types)
      var legend = document.createElement("div");
      legend.className = "wd-trends-legend";
      legend.innerHTML = types.map(function (t) {
        return '<span class="wd-trends-leg-item">' +
          '<span class="wd-trends-sw" style="background:' + WD.dtColor(t) + '"></span>' +
          WD.escHtml(t) + "</span>";
      }).join("");
      root.appendChild(legend);

      // main chart holder
      var chartWrap = document.createElement("div");
      chartWrap.className = "wd-trends-chart";
      root.appendChild(chartWrap);

      // connotation strip
      var connHead = document.createElement("h3");
      connHead.className = "wd-trends-h wd-trends-h2";
      connHead.textContent = "Connotation of the resulting sense (share per period)";
      root.appendChild(connHead);

      var connLegend = document.createElement("div");
      connLegend.className = "wd-trends-legend";
      connLegend.innerHTML = CONN_ORDER.map(function (c) {
        return '<span class="wd-trends-leg-item">' +
          '<span class="wd-trends-sw" style="background:' + WD.connColor(c) + '"></span>' +
          WD.escHtml(c) + "</span>";
      }).join("");
      root.appendChild(connLegend);

      var connWrap = document.createElement("div");
      connWrap.className = "wd-trends-chart wd-trends-chart-conn";
      root.appendChild(connWrap);

      // honesty caption
      var cap = document.createElement("p");
      cap.className = "wd-trends-caption";
      cap.textContent =
        "These proportions reflect the curated WORD-DRIFT corpus, not " +
        "language-wide word frequency. A rising share of a drift type means " +
        "more curated examples in that period, not that the language as a " +
        "whole shifted that way.";
      root.appendChild(cap);

      // own tooltip (the core's #exp-tooltip is not exposed via WD)
      var tip = document.createElement("div");
      tip.className = "wd-trends-tip";
      tip.style.display = "none";
      root.appendChild(tip);

      panelEl.appendChild(root);

      // ---- render -----------------------------------------------------------
      var mode = "absolute"; // | "normalised"
      var animate = !WD.prefersReducedMotion;

      function setMode(m) {
        mode = m;
        btnAbs.setAttribute("aria-pressed", String(m === "absolute"));
        btnNorm.setAttribute("aria-pressed", String(m === "normalised"));
        btnAbs.classList.toggle("is-on", m === "absolute");
        btnNorm.classList.toggle("is-on", m === "normalised");
        drawMain();
      }
      btnAbs.addEventListener("click", function () { setMode("absolute"); });
      btnNorm.addEventListener("click", function () { setMode("normalised"); });

      function tipShow(html, ev) {
        tip.innerHTML = html;
        tip.style.display = "block";
        tipMove(ev);
      }
      function tipHide() { tip.style.display = "none"; }
      function tipMove(ev) {
        var pr = root.getBoundingClientRect();
        var pad = 14;
        var x = ev.clientX - pr.left + pad;
        var y = ev.clientY - pr.top + pad;
        var w = tip.offsetWidth, h = tip.offsetHeight;
        if (x + w > pr.width - 8) x = ev.clientX - pr.left - w - pad;
        if (y + h > pr.height - 8) y = ev.clientY - pr.top - h - pad;
        tip.style.left = x + "px";
        tip.style.top = y + "px";
      }

      function drawMain() {
        drawStacked({
          host: chartWrap,
          buckets: buckets,
          keys: types,
          colorFor: WD.dtColor,
          valueFor: function (rec, k) { return rec.types[k] || 0; },
          normalised: mode === "normalised",
          height: 360,
          yLabel: mode === "normalised" ? "share of drift events" : "drift events",
          tipKind: "type",
        });
      }

      function drawConn() {
        drawStacked({
          host: connWrap,
          buckets: buckets,
          keys: CONN_ORDER,
          colorFor: WD.connColor,
          valueFor: function (rec, k) { return rec.conns[k] || 0; },
          normalised: true,
          height: 130,
          yLabel: "",
          tipKind: "conn",
        });
      }

      function drawStacked(opts) {
        var host = opts.host;
        host.innerHTML = "";
        var W = Math.max(360, host.clientWidth || panelEl.clientWidth || 720);
        var H = opts.height;
        var m = { top: 12, right: 12, bottom: 56, left: 48 };
        var iw = W - m.left - m.right;
        var ih = H - m.top - m.bottom;

        var svg = d3.select(host).append("svg")
          .attr("width", W).attr("height", H)
          .attr("viewBox", "0 0 " + W + " " + H)
          .attr("role", "img")
          .attr("aria-label", opts.tipKind === "conn"
            ? "Stacked connotation share over time"
            : "Stacked drift-type composition over time");

        var g = svg.append("g")
          .attr("transform", "translate(" + m.left + "," + m.top + ")");

        var x = d3.scaleBand()
          .domain(opts.buckets.map(function (b) { return b.label; }))
          .range([0, iw]).paddingInner(0.18).paddingOuter(0.08);

        // y-max
        var yMax = opts.normalised
          ? 1
          : d3.max(opts.buckets, function (b) {
              return opts.keys.reduce(function (s, k) { return s + opts.valueFor(b, k); }, 0);
            }) || 1;
        var y = d3.scaleLinear().domain([0, yMax]).nice(opts.normalised ? false : true).range([ih, 0]);

        // gridlines
        var yTicks = opts.normalised ? [0, 0.25, 0.5, 0.75, 1] : y.ticks(5);
        g.append("g").attr("class", "wd-trends-grid")
          .selectAll("line").data(yTicks).enter().append("line")
          .attr("x1", 0).attr("x2", iw)
          .attr("y1", function (d) { return y(d); })
          .attr("y2", function (d) { return y(d); })
          .attr("stroke", "var(--border-soft)").attr("stroke-width", 1);

        // bars: per bucket, stack the keys
        var bucketsG = g.selectAll(".wd-bucket").data(opts.buckets).enter().append("g")
          .attr("class", "wd-bucket")
          .attr("transform", function (b) { return "translate(" + x(b.label) + ",0)"; });

        var bw = x.bandwidth();
        bucketsG.each(function (b) {
          var sel = d3.select(this);
          var total = opts.keys.reduce(function (s, k) { return s + opts.valueFor(b, k); }, 0);
          var acc = 0;
          opts.keys.forEach(function (k) {
            var v = opts.valueFor(b, k);
            if (v <= 0) return;
            var frac = total > 0 ? v / total : 0;
            var val = opts.normalised ? frac : v;
            var y0 = acc;
            var y1 = acc + val;
            acc = y1;
            var rectY = y(y1);
            var rectH = Math.max(0, y(y0) - y(y1));
            var rect = sel.append("rect")
              .attr("x", 0).attr("width", bw)
              .attr("fill", opts.colorFor(k))
              .attr("y", animate ? ih : rectY)
              .attr("height", animate ? 0 : rectH)
              .style("cursor", "default");
            var label = b.label;
            var pct = total > 0 ? Math.round((v / total) * 100) : 0;
            rect.on("mousemove", function (ev) {
              rect.attr("opacity", 0.82);
              var html = '<strong>' + WD.escHtml(label) + "</strong><br>" +
                '<span class="wd-trends-tip-sw" style="background:' + opts.colorFor(k) + '"></span>' +
                WD.escHtml(k) + ": <strong>" + v + "</strong> " +
                (v === 1 ? "event" : "events") +
                " (" + pct + "% of " + total + ")";
              tipShow(html, ev);
            }).on("mouseleave", function () {
              rect.attr("opacity", 1);
              tipHide();
            });
            if (animate) {
              rect.transition().duration(450).delay(opts.buckets.indexOf(b) * 6)
                .attr("y", rectY).attr("height", rectH);
            }
          });
        });

        // x axis: thin out labels if crowded
        var everyN = Math.ceil(opts.buckets.length / Math.max(6, Math.floor(iw / 64)));
        var xAxis = g.append("g").attr("class", "wd-trends-axis")
          .attr("transform", "translate(0," + ih + ")");
        xAxis.append("line").attr("x1", 0).attr("x2", iw).attr("stroke", "var(--border)");
        opts.buckets.forEach(function (b, i) {
          if (i % everyN !== 0 && i !== opts.buckets.length - 1) return;
          var cx = x(b.label) + bw / 2;
          xAxis.append("text")
            .attr("x", cx).attr("y", 16)
            .attr("text-anchor", "end")
            .attr("transform", "rotate(-40," + cx + ",16)")
            .attr("fill", "var(--text-sub)").attr("font-size", 10)
            .text(b.label);
        });

        // y axis
        var yAxis = g.append("g").attr("class", "wd-trends-axis");
        yTicks.forEach(function (t) {
          yAxis.append("text")
            .attr("x", -8).attr("y", y(t) + 3)
            .attr("text-anchor", "end")
            .attr("fill", "var(--text-sub)").attr("font-size", 10)
            .text(opts.normalised ? Math.round(t * 100) + "%" : t);
        });
        if (opts.yLabel) {
          yAxis.append("text")
            .attr("transform", "rotate(-90)")
            .attr("x", -ih / 2).attr("y", -38)
            .attr("text-anchor", "middle")
            .attr("fill", "var(--text-faint)").attr("font-size", 10)
            .text(opts.yLabel);
        }
      }

      setMode("absolute");
      drawConn();
    },
  });

  function mkToggleBtn(label, on) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "wd-trends-tbtn" + (on ? " is-on" : "");
    b.textContent = label;
    b.setAttribute("aria-pressed", String(!!on));
    return b;
  }

  // ---- scoped styles (injected once) --------------------------------------
  if (!document.getElementById("wd-trends-style")) {
    var css = document.createElement("style");
    css.id = "wd-trends-style";
    css.textContent = [
      ".wd-trends{position:relative;padding:4px 2px 8px;}",
      ".wd-trends-head{display:flex;flex-wrap:wrap;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:8px;}",
      ".wd-trends-h{margin:0 0 2px;font-size:15px;color:var(--text);}",
      ".wd-trends-h2{margin-top:18px;}",
      ".wd-trends-sub{margin:0;font-size:12px;color:var(--text-sub);}",
      ".wd-trends-toggle{display:inline-flex;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;}",
      ".wd-trends-tbtn{appearance:none;background:transparent;color:var(--text-sub);border:0;padding:6px 12px;font-size:12px;font-family:inherit;cursor:pointer;}",
      ".wd-trends-tbtn+.wd-trends-tbtn{border-left:1px solid var(--border);}",
      ".wd-trends-tbtn:hover{color:var(--accent-hi);}",
      ".wd-trends-tbtn.is-on{background:var(--accent);color:#fff;}",
      ".wd-trends-legend{display:flex;flex-wrap:wrap;gap:8px 14px;margin:6px 0 8px;font-size:11px;color:var(--text-sub);}",
      ".wd-trends-leg-item{display:inline-flex;align-items:center;gap:5px;}",
      ".wd-trends-sw{display:inline-block;width:11px;height:11px;border-radius:2px;}",
      ".wd-trends-chart{width:100%;min-height:120px;}",
      ".wd-trends-chart-conn{min-height:60px;}",
      ".wd-trends-caption{margin:12px 0 0;font-size:11px;line-height:1.5;color:var(--text-faint);max-width:70ch;}",
      ".wd-trends-tip{position:absolute;z-index:50;pointer-events:none;background:var(--bg-card2);border:1px solid var(--border);border-radius:6px;padding:7px 9px;font-size:12px;color:var(--text);box-shadow:0 4px 16px rgba(0,0,0,.4);max-width:260px;}",
      ".wd-trends-tip-sw{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;vertical-align:baseline;}",
    ].join("\n");
    document.head.appendChild(css);
  }
})();
