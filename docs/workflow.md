# Paper-to-figure workflow

## Local, author-authored brief

1. Identify the paper type, central question, and specific contribution. Separate new results from background and cited prior work.
2. Trace the shortest supported argument from problem/setup through decisive method, lemma, experiment or comparison to primary result, consequence, and scope boundary.
3. Select 5–8 nonredundant nodes with distinct roles in that argument. Retain enough evidence anchors, assumptions, parameters, comparisons, and limitations to interpret the main result. Do not turn the section list into a graph.
4. Record source anchors for important nodes and edges. Distinguish `proof_dependency` from `specialization` in theory papers, and distinguish association from causation in empirical work.
5. Use English for reader-facing figure text by default; change the language only when the user requests it. Source anchors may retain their original wording for traceability.
6. For the compact reference theme, group the argument into 2–4 panels using `style: "reference"`, `panel`, and `panel_labels`. Set `panel_descriptors` and `legend_labels` when generic theme text does not match the paper.
7. Run `papervisual suggest`, validate, render, and run `papervisual qa`. Compare the figure with the abstract, main results and discussion at final size.

## Model-assisted text draft

The `draft` command sends a selected UTF-8 text file to an OpenAI-compatible chat completion endpoint. It is an explicit network operation and requires `--allow-external`, a user-provided `PAPERFIG_API_KEY`, and a model name. Use a provider endpoint only when you are allowed to share the text with it.

The default command uses `--language en --style reference`; use `--language zh` only for a Chinese figure requested by the user. The draft is not a source of truth. The adapter forces the central claim, every node, and every edge to `needs_review`, validates the returned structure, and writes a JSON file. The author must check the contribution, evidence coverage, scope, labels, source anchors, ordering and arrow semantics. The software has no paper parser and does not independently check whether source anchors support the proposed interpretation.

For review articles, summarize taxonomies and the authors' synthesis rather than presenting section order as a method pipeline. `suggest` is a graph heuristic; inspect its recommendation and set `archetype` explicitly when it confuses taxonomy, article structure, and a research process. The reference theme uses explicit panel groups regardless of `archetype`.

## Interpreting QA

Errors block a structurally invalid brief or unreadable SVG. Warnings identify items for review, such as unreviewed edges, unsupported causal links, isolated nodes, overlapping boxes, long labels, or approximate text bounds. A clean report is not a scientific correctness certificate. The author checklist is always part of the report.
