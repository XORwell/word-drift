"use strict";
// Shared theme bootstrap for the static pages (index, about). Loaded in <head>
// without defer so the pre-paint step runs before the body renders (no flash).
//
// 1. Pre-paint: apply the persisted theme (default light) immediately.
// 2. After the DOM is ready: wire the #wd-theme-toggle button (present on the
//    static pages). The explorer (explore.html) wires its own toggle in app.js,
//    so this no-ops there when the button is absent.
//
// NOTE: explore.html also loads this file purely for the pre-paint step; its
// toggle button id is the same, but app.js attaches its own click handler with
// full palette re-render, so we must not double-bind. We therefore only wire a
// toggle here if one does not already carry app.js's handler. app.js creates
// the button dynamically AFTER data load, so at DOMContentLoaded on explore.html
// the button does not yet exist and this wiring no-ops.

// 1. Pre-paint theme application.
try {
  if (localStorage.getItem("wd.theme") === "dark") {
    document.documentElement.dataset.theme = "dark";
  }
} catch (e) {}

// 2. Toggle wiring for the static pages.
(function () {
  function wireToggle() {
    var btn = document.getElementById("wd-theme-toggle");
    if (!btn || btn.dataset.wdThemeBound === "1") return;
    btn.dataset.wdThemeBound = "1";
    btn.addEventListener("click", function () {
      var dark = document.documentElement.dataset.theme === "dark";
      if (dark) { delete document.documentElement.dataset.theme; }
      else { document.documentElement.dataset.theme = "dark"; }
      try { localStorage.setItem("wd.theme", dark ? "light" : "dark"); } catch (e) {}
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireToggle);
  } else {
    wireToggle();
  }
})();
