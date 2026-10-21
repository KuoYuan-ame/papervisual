# Changelog

## Unreleased

- Rendered glyph coverage audit now discloses fallback font resolution when the requested platform font is unavailable; manual cross-platform visual checks remain necessary.

- Enforced source locators for the claim, every node and edge in release mode; absent review status defaults to needs_review and author declaration remains a separate gate.
- Added Mathtext/STIX formula paths with preserved TeX source, script-size checks, and a layered theory style with a dominant theorem and adjacent conditions.
- Added final-width millimeters, point-size minimum and PNG DPI contracts; independent edge labels reserve space even with node annotations.
- Added early doctor diagnostics and optional rendered glyph/text measurement, card/label/formula collisions and edge-through-card checks. Reports separate source, structure, author, rendering and manual visual states.
- Portable self-check supports release, rendered and author-confirmation flags and retains blocked QA findings; includes an original synthetic theory example.

- Added explicit PNG/PDF → SVG-viewer → uncompleted-visual-QA fallback instructions; automated success is never reported as full visual acceptance.
- Added a portable `scripts/self_check.py` release command for dependency and manifest checks, the four CLI steps, repeated SVG hashes and JSON reporting; `--require-raster` enforces PNG/PDF dependencies.

- Made the Skill folder standalone: bundled renderer, schema, original visual anchors and workflow references, deterministic ZIP with file hashes, isolated execution tests and CI drift checks.
- Added release-test provenance rules distinguishing an existing-brief replay from fresh paper analysis; routed same-panel skip edges around intervening cards.
- Wrapped long reference legend labels and moved long-jump edge lanes clear of downstream hints after portable-paper tests.

- Added a reusable repository Skill with paper-type-specific synthesis, the reference visual contract, default-English output, source anchoring, review gates and a render/visual-inspection workflow.
- The reference theme can use paper-specific panel descriptors and semantic legend labels; generic role legend entries are omitted when unused.
- The reusable workflow now warns that a survey taxonomy or article outline must not be misread as a causal research pipeline.
- Added a compact `reference` SVG theme with 2–4 panels, role-based original vector icons, localized labels, captions and optional source-backed condition tags.
- Reference QA uses the renderer's actual geometry. Association and comparison edges keep their undirected meaning; scientific review and provenance metadata remain visible or embedded.
- PNG exports use the actual SVG dimensions, including a theme-expanded canvas. Added a synthetic reference example and a reusable style/adaptation guide.
- Reworked opt-in paper extraction around paper type, specific contribution, evidence coverage and scope. English and the `reference` theme are the draft defaults; Chinese is an explicit `--language zh` choice.
- Added separate directed `proof_dependency` and `specialization` relationships for theory-paper argument maps, plus author-review checks for contribution, evidence and scope.

## 0.1.0 — 2026-10-19

### Branding and compatibility

- Public brand, GitHub repository, Skill ID and distribution name standardized to `PaperVisual` / `papervisual`.
- Added `papervisual` CLI and standalone launcher; retained `paperfig` Python module and command for compatibility.
- Refreshed ZIP generation, Skill documentation and GitHub release steps.


- First public MVP: editable SVG framework diagrams, six deterministic layouts, relationship-based suggestions, structural and approximate geometry QA, and optional opt-in model-assisted drafts.
- Includes six synthetic examples, batch rendering with per-file QA, source metadata, relation legends, and visible review notices. No manuscript parser or independent scientific verification.

