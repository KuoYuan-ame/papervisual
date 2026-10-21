# Scientific figure contracts and release checks

Read this when producing a theory figure, specifying print dimensions, or preparing a release. The CLI renders a curated brief; an analyst must still read the manuscript and confirm the evidence.

## Evidence and review

Supply `claim_source` on the brief and `source` on every node and edge. A source can be a nonempty locator string or an object with `pages`, `section`, `theorem`, `equation`, and `explanation` (at least one actual locator is required). Use PDF page numbers explicitly when journal pagination differs. Annotations, conditions and formulas inherit their node's source; include all necessary anchors there.

`review_status` defaults to `needs_review` on the claim, nodes and edges. A source does not confirm a scientific interpretation. Never mark content `confirmed` merely to silence a warning; it records an actual author declaration, which the program cannot authenticate.

Ordinary `validate`/`qa` report missing sources; `validate --release` and `qa --release` reject them. `qa --require-confirmed` separately rejects pending author declarations. The source check establishes that locators are present, not that the quoted paper supports the claim. Invented or irrelevant locators still require human detection.

## Theory figures and formulas

Use `style: "theory"` for a layered proof graph, with exactly one node having `emphasis: "main"`. Keep proof dependencies and parameter/function specializations distinct. This layout uses the same deep blue, pale gray, dashed cards and orange specializations as the reference theme, but omits its repeated overview and panel headings. It sizes card heights from content. Cycles must be resolved or represented as explanatory notes rather than false proof dependencies.

Node fields:

```json
{
  "id": "main", "label": "Main bound", "role": "core",
  "emphasis": "main",
  "formula": "\\frac{x}{y}+\\frac{y}{x}\\geq2",
  "assumptions": "Positive real numbers x and y.",
  "equality": "Exactly when x = y.",
  "source": {"section": "Original synthetic algebra example"},
  "review_status": "needs_review"
}
```

The `formula` field accepts the Matplotlib Mathtext subset of TeX, including subscripts, superscripts, fractions and STIX mathematical fonts. It requires Matplotlib (`math` extra). Unsupported syntax fails; there is no plain-string fallback. Formulas are single mathematical expressions: the renderer does not break a formula arbitrarily or shrink it to fit a card. For an oversized formula, revise the composition or author a scientifically equivalent shorter expression. Formula fields in other styles are rejected to prevent silently omitted equations.

Ordinary labels and conditions remain editable SVG text. **Typeset equations are vector paths**, with TeX retained in `data-formula-source`, an SVG title, and the JSON brief. Edit the TeX field and rerender to change a formula; these paths are not native editable equation text. STIX fonts are supplied by Matplotlib, not copied into the Skill. The script inspects parsed glyph sizes, including nested scripts. Arrow labels remain independent editable text, even when nodes have annotations; keep them concise. This is not a general TeX engine or arbitrary graph routing solver.

## Physical output

Set `width_mm`, `min_font_pt` and `dpi` in the brief before rendering (for example 180, 8 and 300). SVG and PDF have the declared physical width; PNG width is rounded from `width_mm / 25.4 * dpi`. Without these fields legacy pixel dimensions remain supported, but final print-size acceptance is unresolved.

The theory layout rewraps text and increases mathematical font size to preserve the requested minimum. It may become taller or reject an expression that cannot fit. Reference/default layouts retain their established appearance; QA flags too-small type instead of silently claiming compliance. Change the content or layout when flagged. Resizing a completed figure afterward invalidates the font-size check. Pixel count alone does not establish readability.

## Dependency diagnosis and QA

Run `papervisual doctor --output doctor.json` before extracting the paper or rendering. It reports Python, PDF libraries/tools, fonts, Mathtext, Cairo and preview tools. Tool discovery is not proof that a PDF can be read or a viewer has been inspected. Test the actual PDF, not just the executable's existence.

From a source checkout, install optional measurement support with `python -m pip install ".[audit]"`. For a copied Skill, use an existing environment with CairoSVG/native Cairo, Matplotlib, fonttools and PyMuPDF 1.x, or install those packages if appropriate. Core non-math SVG still needs only Python. Missing dependencies must be reported, never represented as completed checks.

```sh
papervisual validate brief.json --release
papervisual render brief.json -o figure.svg --png figure.png --pdf figure.pdf
papervisual qa brief.json --svg figure.svg --release --rendered --output figure.qa.json
```

Add `--require-confirmed` only when author declarations are required. `--rendered` requires an SVG and the optional audit dependencies; in release mode uncompleted requested measurements block success.

The report separates structure, source locator presence, author declaration, rendering and visual inspection. Geometry detects labels over cards/other labels and straight/polyline edges through unrelated cards. Rendered measurement uses Cairo PDF output and PyMuPDF word boxes to detect overflow, real text collisions and text intersecting equation bounds. Formula bounds and the minimum parsed script size are checked. Fonttools checks coverage of resolved installed font candidates; the actual Cairo fallback selection can differ. SVG effects, rotations, arbitrary curves and external fonts are not comprehensively audited. A lack of findings is not a proof of perfect typography.

For a frozen portable bundle:

```sh
python /path/to/scripts/self_check.py --brief /path/to/brief.json --output-dir /path/to/new-folder --release --rendered --require-raster
```

This runs diagnostics, suggest, validate, render, qa and repeat-render, checks the manifest before/after, and compares SVG hashes. A blocked QA step still saves its findings. The self-check always records human visual QA as `not_completed`. Inspect the actual PNG and a rasterized PDF at the declared dimensions, or follow the SVG-viewer fallback in the portable-test guide. Record visual inspection separately, including formats, dimensions, viewer and findings. Do not rewrite the automatic report to imply a viewer inspection occurred.

The original synthetic theory example demonstrates the fields; it is not a substitute for extracting the new paper. Rendering an existing brief tests replay, not manuscript understanding. Cross-system fonts and different Mathtext versions may change path serialization; repeat hashes are a within-environment guarantee.
