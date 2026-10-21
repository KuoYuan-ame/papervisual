"""Command-line interface for the offline PaperVisual."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .extract import draft_from_text
from .layout import layout
from .model import BriefError, load_brief
from .qa import audit
from .recommend import recommend
from .render import write_svg
from .physical import png_options
from .provenance import source_findings

STARTER = {
    "schema_version": "1.0",
    "language": "en",
    "title": "A reviewed research framework",
    "claim": "A concise statement of the central contribution.",
    "archetype": "auto",
    "width": 1200,
    "height": 600,
    "nodes": [
        {"id": "input", "label": "Input or context", "role": "input", "order": 1},
        {"id": "method", "label": "Core method", "role": "process", "order": 2},
        {"id": "result", "label": "Supported outcome", "role": "output", "order": 3}
    ],
    "edges": [
        {"from": "input", "to": "method", "relation": "sequence", "review_status": "needs_review"},
        {"from": "method", "to": "result", "relation": "sequence", "review_status": "needs_review"}
    ],
    "notes": ["Replace this starter with author-reviewed paper content."]
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="papervisual", description="Create editable scientific framework diagrams from a reviewed JSON brief.")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="write a starter brief")
    init.add_argument("path", nargs="?", default="figure-brief.json")
    suggest = sub.add_parser("suggest", help="recommend a layout and explain the choice")
    suggest.add_argument("brief")
    draft = sub.add_parser("draft", help="draft an English-first, review-required paper overview via an external model")
    draft.add_argument("text", help="UTF-8 text file sent to the configured endpoint")
    draft.add_argument("--output", default="figure-brief.draft.json")
    draft.add_argument("--model", required=True)
    draft.add_argument("--base-url", default="https://api.openai.com/v1")
    draft.add_argument("--language", choices=("en", "zh"), default="en", help="reader-facing figure language (default: en)")
    draft.add_argument("--style", choices=("reference", "default"), default="reference", help="figure visual style (default: reference)")
    draft.add_argument("--allow-external", action="store_true", help="confirm that the text may be sent to this endpoint")
    validate = sub.add_parser("validate", help="validate a brief")
    validate.add_argument("brief")
    render = sub.add_parser("render", help="render an editable SVG")
    render.add_argument("brief")
    render.add_argument("-o", "--output", default="figure.svg")
    render.add_argument("--png", help="also export a PNG (requires pip install papervisual[raster])")
    render.add_argument("--pdf", help="also export a PDF (requires pip install papervisual[raster])")
    batch = sub.add_parser("batch", help="render all JSON briefs in a directory and write QA reports")
    batch.add_argument("directory")
    batch.add_argument("-o", "--output-dir", default="figures")
    batch.add_argument("--png", action="store_true", help="also write 2x PNG files (requires the raster extra)")
    batch.add_argument("--pdf", action="store_true", help="also write PDF files (requires the raster extra)")
    qa = sub.add_parser("qa", help="run graph and approximate SVG checks")
    qa.add_argument("brief")
    qa.add_argument("--svg")
    qa.add_argument("--output", help="write the report as JSON")
    validate.add_argument("--release", action="store_true", help="reject missing claim/node/edge sources")
    qa.add_argument("--release", action="store_true", help="block missing sources and rendering findings")
    qa.add_argument("--require-confirmed", action="store_true", help="also require declared author confirmation")
    qa.add_argument("--rendered", action="store_true", help="measure glyphs and rendered text bounds (audit extra)")
    diagnose = sub.add_parser("doctor", help="diagnose PDF, fonts, math, Cairo and preview tools before rendering")
    diagnose.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            from .diagnostics import diagnose
            report = diagnose()
            text = json.dumps(report, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                Path(args.output).write_text(text + "\n", encoding="utf-8")
            print(text)
            return 0
        if args.command == "init":
            target = Path(args.path)
            if target.exists():
                raise BriefError(f"Refusing to overwrite existing file: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(STARTER, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote starter brief: {target}")
            return 0
        if args.command == "draft":
            if not args.allow_external:
                raise BriefError("Drafting sends text to an external model. Re-run with --allow-external only if sharing is permitted.")
            api_key = os.environ.get("PAPERFIG_API_KEY")
            if not api_key:
                raise BriefError("Set PAPERFIG_API_KEY for the configured endpoint.")
            try:
                text = Path(args.text).read_text(encoding="utf-8")
            except OSError as exc:
                raise BriefError(f"Could not read text input: {exc}") from exc
            if not text.strip():
                raise BriefError("Input text is empty.")
            brief = draft_from_text(text, api_key=api_key, model=args.model, base_url=args.base_url,
                                    language=args.language, style=args.style)
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote review-required draft: {target}")
            print("Review every claim and relationship before rendering or use.")
            return 0
        if args.command == "batch":
            source_dir = Path(args.directory)
            if not source_dir.is_dir():
                raise BriefError(f"Input directory does not exist: {source_dir}")
            paths = sorted(source_dir.glob("*.json"))
            if not paths:
                raise BriefError("No JSON briefs found in the input directory.")
            cairosvg = None
            if args.png or args.pdf:
                try:
                    import cairosvg as _cairosvg
                    cairosvg = _cairosvg
                except (ImportError, OSError) as exc:
                    raise BriefError("Batch PNG/PDF export requires the optional raster extra: pip install papervisual[raster].") from exc
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            results = []
            failed = False
            for path in paths:
                try:
                    brief = load_brief(path)
                    svg_path = write_svg(brief, output_dir / (path.stem + ".svg"))
                    outputs = {"input": path.name, "svg": svg_path.name}
                    if args.png:
                        png_path = output_dir / (path.stem + ".png")
                        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), **png_options(brief))
                        outputs["png"] = png_path.name
                    if args.pdf:
                        pdf_path = output_dir / (path.stem + ".pdf")
                        cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))
                        outputs["pdf"] = pdf_path.name
                    report = audit(brief, svg_path)
                    report_path = output_dir / (path.stem + ".qa.json")
                    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    results.append({**outputs, "errors": report["errors"], "warnings": report["warnings"]})
                    failed = failed or bool(report["errors"])
                except (BriefError, OSError) as exc:
                    failed = True
                    results.append({"input": path.name, "errors": [str(exc)], "warnings": []})
            summary = output_dir / "batch-summary.json"
            summary.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Processed {len(paths)} briefs; summary: {summary}")
            return 1 if failed else 0
        brief = load_brief(args.brief)
        if args.command == "suggest":
            choice, reasons = recommend(brief)
            override = brief.get("archetype", "auto")
            print(json.dumps({"recommended": choice, "configured": override, "reasons": reasons,
                              "next_step": "Review the recommendation and confirm or set archetype explicitly."}, indent=2))
            return 0
        if args.command == "validate":
            findings = source_findings(brief)
            if args.release and findings:
                raise BriefError("\n".join(findings))
            for warning in findings:
                print("Source warning: " + warning, file=sys.stderr)
            print(f"Valid brief: {len(brief['nodes'])} nodes, {len(brief['edges'])} edges.")
            return 0
        if args.command == "render":
            target = write_svg(brief, args.output)
            if args.png or args.pdf:
                try:
                    import cairosvg
                except (ImportError, OSError) as exc:
                    raise BriefError("PNG/PDF export requires the optional raster extra: pip install papervisual[raster].") from exc
                if args.png:
                    Path(args.png).parent.mkdir(parents=True, exist_ok=True)
                    cairosvg.svg2png(url=str(target), write_to=args.png, **png_options(brief))
                    print(f"Wrote PNG: {args.png}")
                if args.pdf:
                    Path(args.pdf).parent.mkdir(parents=True, exist_ok=True)
                    cairosvg.svg2pdf(url=str(target), write_to=args.pdf)
                    print(f"Wrote PDF: {args.pdf}")
            selected = brief['style'] if brief.get('style') in {'reference','theory'} else layout(brief)[0]
            print(f"Rendered {selected} diagram: {target}")
            return 0
        report = audit(brief, args.svg, release=args.release,
                       require_confirmed=args.require_confirmed, rendered=args.rendered)
        rendered = json.dumps(report, indent=2, ensure_ascii=False)
        if args.output:
            report_path = Path(args.output)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(rendered + "\n", encoding="utf-8")
            print(f"Wrote QA report: {args.output}")
        else:
            print(rendered)
        return 1 if report["errors"] else 0
    except BriefError as exc:
        print(f"Invalid brief:\n{exc}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as exc:
        print(f"File or encoding error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
