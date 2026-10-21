"""CI check: schema parity, fresh SVG fixtures, QA and optional export smoke tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import cairosvg
import jsonschema

from paperfig.model import load_brief
from paperfig.qa import audit
from paperfig.render import render_svg


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas" / "figure-ir.schema.json").read_text(encoding="utf-8"))
    examples = sorted((root / "examples").glob("*.json"))
    examples.append(root / 'examples/theory/brief.json')
    assert len(examples) >= 6
    with tempfile.TemporaryDirectory() as temp:
        for path in examples:
            brief = load_brief(path)
            jsonschema.validate(brief, schema)
            svg = render_svg(brief)
            name = 'theory' if brief.get('style') == 'theory' else path.stem
            fixture = root / "examples" / "rendered" / (name + ".svg")
            if brief.get('style') != 'theory':
                assert svg == fixture.read_text(encoding="utf-8"), f"Stale SVG fixture: {fixture.name}"
            else:
                # Matplotlib versions can change path serialization across systems.
                assert svg == render_svg(brief), 'Non-deterministic math paths'
            actual = Path(temp) / (name+'.svg')
            actual.write_text(svg,encoding='utf-8')
            assert not audit(brief, actual, release=True)["errors"], path.name
            png = Path(temp) / (path.stem + ".png")
            pdf = Path(temp) / (path.stem + ".pdf")
            cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(png))
            cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=str(pdf))
            assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), png.name
            assert pdf.read_bytes().startswith(b"%PDF-"), pdf.name
    print(f"Verified schema, deterministic SVG, QA and PNG/PDF export for {len(examples)} examples.")


if __name__ == "__main__":
    main()
