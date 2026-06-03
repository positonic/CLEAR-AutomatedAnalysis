# ADR 0001 — Country Situation Analysis is cached as per-location metadata

- Status: Accepted
- Date: 2026-06-03

## Context

The CLEAR ReliefWeb pipeline produces a per-country analytical product — the
**Situation Analysis** (key figures, sector severity, risks, displacement,
priority needs/interventions, information-coverage gaps, and the sources behind
them). The pipeline is LLM-heavy and slow, so the platform's `/analysis` page
cannot run it on demand; the output must be produced on a cadence and cached
behind clear-api for instant reads.

We needed a storage home for that cached product.

## Decision

Store the Situation Analysis as **one `locationMetadata` record** with
`type = "clear_situation_analysis"`, attached to the country's level-0
**Country** `locations` row.

- **Not the `crises` model.** `crises` is event-derived and many-per-country
  (it powers the Crises tab). The Situation Analysis is a single current
  analytical snapshot per country — a different thing. (Note: `crises` is the
  renamed former `Situation` model; the `"clear_situation_analysis"` type echoes
  the NRC term and is unrelated to it.)
- **Not object storage.** The bundle is ~100 KB of JSON read whole on every page
  load; a metadata row is one round-trip and versions atomically. (Source
  **PDFs** *are* in object storage, under `sources/{sha256}.pdf`.)
- **One bundled record, not many.** The pipeline regenerates all structures
  together and the page reads a country once, so a single record matches both
  patterns and supersedes atomically.

History/versioning is free from the existing valid-from/valid-to mechanism: each
run closes the prior current record and inserts a new one. A reserved
`summary: null` slot is filled later by AutoSitRep through the same upsert path.

## Consequences

- Reads use clear-api's existing per-location metadata query — no new read
  surface.
- The pipeline writes via a least-privilege `pipeline`-role API key
  (`ensureCountryLocation` + `upsertLocationMetadata`).
- **Hard to reverse once data is written under the type**, and surprising
  without this rationale — hence this ADR.
- **Known limitation:** an auto-created Country's geometry is a bounding box,
  not a true admin-0 boundary; adequate for now, refine when boundaries land.
