# ADR 0005 — One Oxigraph store, no federated SPARQL yet

**Status:** Accepted

## Context

`00-vision.md` borrows the language of "federated meaning systems" as a *modelling* metaphor: many platforms, many groups, many registers, no single owner of meaning. A reasonable misreading of that metaphor is "therefore, deploy one KG per platform and join them by federated SPARQL". That is a deployment topology, not the modelling claim. They can come apart.

The 2.x deployment is a single Oxigraph store fronted by FastAPI, with SHACL validation in the ETL path and Trails capabilities served on top. It handles the current data volume comfortably, runs on a small VPS, and lets every query be planned in one engine with full statistics.

Federation buys distribution, autonomy of per-platform stores, and the ability to serve different licences from different endpoints. It costs operational complexity (N endpoints, N TLS surfaces, N upgrade cycles), cross-endpoint trust questions (who signs what; how do we revoke a misbehaving source), and query-planning complications that get worse as joins span endpoints. At the data volumes we have through M8 (tens of millions of triples, single-digit number of source classes), federation pays back exactly nothing.

## Decision

Ship one Oxigraph store for word-drift 3.0 through at least M8. All sources land in the same store, partitioned by named graph where useful for licensing or rollback, never by separate endpoint. The "platform" axis in the data model (ADR-0003) is a modelling concept, not a deployment topology; `drift:Platform` instances live in the same store as every other class.

Defer federated SPARQL as a deployment choice to a post-M8 ADR, to be opened only if at least one of the following holds: a source class arrives whose licence forbids co-location; the store exceeds a size we cannot comfortably back up; an external partner needs to host their own endpoint and have it joined live.

## Consequences

- Operations stay simple: one process, one backup, one SHACL gate.
- Cross-platform queries (the actual research workload) run in one engine with full statistics — exactly the queries federation would slow down.
- We retain the option to add federation later without re-modelling: ADR-0003's classes (`Platform`, `CorpusContext`, `Register`) are deployment-agnostic.
- The PROV-CRED line and any external collaborators that want to consume the KG do so via the single endpoint, with the same auth surface.
- We carry the risk that, if federation ever becomes necessary, we pay the migration cost in one large step rather than absorbing it incrementally. That risk is acceptable for the current and forecast scale.

## Alternatives considered

- **Per-platform KGs joined by federated SPARQL from day one.** Rejected for M0–M8: it adds operational complexity and query-planning complications that pay back only at a scale we do not have.
- **One store, one named graph per platform.** Compatible with this decision and likely how we will partition Reddit-derived data from Wikipedia-derived data once both land. Not the same as federation; it stays in one engine.
- **Two stores (public vs. staging).** Already the operational reality (the private staging store for raw Reddit cells per `04-data-sources.md §3.4`). That is a privacy boundary, not federation, and is out of scope for this ADR.
