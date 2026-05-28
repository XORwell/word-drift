// WORD-DRIFT — version stamping.
//
// Replaces hard-coded version strings in the static site footers and citation
// blocks with values served by GET /api/version (which reads owl:versionInfo
// from the live ontology + the git tag).
//
// Usage in HTML:
//
//   <span data-wd-version="schema">Schema</span>
//   <span data-wd-version="release">unreleased</span>
//   <span data-wd-version="commit"></span>
//   <span data-wd-version="citation">untagged</span>
//
// The text content before the script runs is kept as a graceful fallback for
// browsers that can't reach the API (e.g. the static GitHub Pages mirror).

(function () {
  "use strict";

  function apply(meta) {
    var nodes = document.querySelectorAll("[data-wd-version]");
    nodes.forEach(function (n) {
      var key = n.getAttribute("data-wd-version");
      if (!key) return;
      var val = "";
      if (key === "schema")        val = meta.schemaLabel || "";
      else if (key === "release")  val = meta.releaseLabel || "";
      else if (key === "commit")   val = meta.commit ? "(" + meta.commit + ")" : "";
      else if (key === "citation") val = meta.citationVersion || "";
      else if (key === "ontology") val = meta.ontology || "";
      if (val) n.textContent = val;
    });
  }

  fetch("api/version", { credentials: "same-origin" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (meta) { if (meta) apply(meta); })
    .catch(function () { /* leave the static fallback text in place */ });
})();
