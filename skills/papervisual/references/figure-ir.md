# Figure IR

The JSON IR is the stable interface between content extraction, layout, rendering, and review. See `figure-ir.schema.json` for the machine-readable shape.

## Main fields

- `title` and `claim` define what the reader sees first.
- `language` records the intended reader-facing text language (`en` by default, or `zh`). It does not translate manually authored content; the external draft command uses English by default.
- `review_status` records whether the central claim is author-confirmed or a draft.
- `archetype` is `auto` or one of the six deterministic layouts.
- `style` is `default`, `reference` or `theory`. The latter renders a compact overview and 2–4 panels instead of the archetype layout. Every node must have a nonempty `panel`; `panel_labels` maps panel IDs to visible titles. Optional `panel_descriptors` maps panel IDs to short, paper-specific subheadings; an empty string hides that subheading. Panel order follows the first occurrence in nodes sorted by `order`.
- `caption` supplies an editable manuscript caption for the reference theme. An omitted caption falls back to the title and claim.
- For the reference theme, `show_crossrefs` controls miniature source cards and downstream-link placeholders in sparse panels; it defaults to `true` to preserve the sample treatment and can be set to `false` for a cleaner taxonomy overview.
- `nodes` contain visible entities. `role` chooses a semantic color token; `source` stores a short traceability anchor; `review_status` separates drafts from confirmed content. The reference theme derives its role-color legend from colors used by the nodes; optional `legend_labels` replaces the default names for `blue`, `green`, `orange`, and `red`.
- Nodes may contain `annotations`: up to two nonempty short strings, rendered as condition tags by the reference theme. These are content, so they require the same source support and review as the node. Default layouts currently ignore these optional tags.
- `edges` connect node IDs and name the relationship. `source` stores a supporting quote/section anchor, and `review_status` records author review.
- `notes` hold user-authored cautions and do not appear on the canvas. A relationship legend is derived from the edge types and drawn automatically.

## Relationship semantics

`sequence` means ordered steps; `data` means information transfer; `causal` makes a causal claim; `feedback` means a return/update path; `contrast` marks a comparison; `association` marks a non-causal relationship; `hierarchy` means containment or level; `proof_dependency` means one result is used to prove another; `specialization` means a general result yields a restricted case by fixing its inputs or parameters. The last two are directed and distinct from one another. `contrast` and `association` use unheaded lines. The renderer varies line color, dash pattern and arrowheads; check the legend and do not rely on color alone.

## Layout recommendation

For `style: "reference"`, `suggest` still recommends an underlying graph archetype, but the reference renderer uses the declared panel groups. Sparse panels repeat their actual incoming sources as small cross-references; they do not add graph nodes or infer new edges. Icons depend on semantic roles, not paper-specific IDs. See the [style and adaptation guide](reference-style.zh-CN.md) and `../assets/reference.json`.

`papervisual suggest` considers explicit relations, groups, degree, and temporal language. Proof-dependency or specialization graphs favor a layered mechanism layout. This small heuristic is intended to produce a reviewable starting point. It does not parse the prose claim and can recommend a poor layout; users can override `archetype` in the JSON.

## Evidence, theory and physical contracts

`claim_source` anchors the central claim. Node/edge `source` accepts a nonempty locator string or an object with `pages`, `section`, `theorem`, `equation`, and `explanation`; an explanation alone is insufficient. All missing `review_status` values default to `needs_review`. Sources and author declarations are independent. `validate --release` and `qa --release` reject missing sources.

`style: "theory"` requires exactly one node with `emphasis: "main"`; other nodes use `normal` or omit it. Optional node `formula` is TeX in the Mathtext subset, rendered as paths with its source retained. It is rejected in non-theory styles. `assumptions` and `equality` are separate text fields in theory cards. Proof graphs are layered and must be acyclic apart from separately classified feedback. Formula editing means changing TeX and rerendering.

`width_mm` sets final physical width (40–1000 mm); `min_font_pt` sets the minimum requested point size (4–40 pt; default 8); `dpi` sets PNG pixel density (72–1200; default 300). Legacy `width`/`height` remain supported when no physical width is supplied. Physical sizes require checking at the declared final width. See [scientific QA](scientific-qa.md) for actual guarantees and limitations.
