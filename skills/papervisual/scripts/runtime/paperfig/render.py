"""Editable SVG renderer using only Python's standard library."""

from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Any

from .provenance import source_text, status

from .layout import _wrap, layout

COLORS = {
    "input": ("#e8f1f8", "#376a8e"),
    "process": ("#edf1f7", "#315b9b"),
    "evidence": ("#e9f2df", "#558d3b"),
    "output": ("#fff0df", "#d56b00"),
    "caveat": ("#fde9e9", "#bd2330"),
    "core": ("#e6edf8", "#244b80"),
    "context": ("#f1f1f1", "#777777"),
}
RELATION_STYLES = {
    "sequence": ("#444444", "solid"),
    "data": ("#315b9b", "solid"),
    "causal": ("#bd2330", "solid"),
    "feedback": ("#558d3b", "dashed"),
    "contrast": ("#d56b00", "dashed"),
    "association": ("#707070", "dotted"),
    "hierarchy": ("#315b9b", "solid"),
    "proof_dependency": ("#315b9b", "dotted"),
    "specialization": ("#d56b00", "dashed"),
}
DIRECTED_RELATIONS = {"sequence", "data", "causal", "feedback", "hierarchy",
                      "proof_dependency", "specialization"}


def render_svg(brief: dict[str, Any]) -> str:
    from .physical import finalize
    return finalize(_render_svg(brief), brief)


def _render_svg(brief: dict[str, Any]) -> str:
    if brief.get("style") == "theory":
        from .theory_style import render_theory_svg
        return render_theory_svg(brief)
    if brief.get("style", "default") == "reference":
        from .reference_style import render_reference_svg

        return render_reference_svg(brief)
    archetype, positions = layout(brief)
    width, height = brief.get("width", 1200), brief.get("height", 600)
    title_lines = _wrap(brief["title"], (width - 100) / 13.2)
    claim_lines = _wrap(brief["claim"], (width - 100) / 7.4)
    title_start = 42
    claim_start = title_start + len(title_lines) * 24 + 2
    relations = {edge["relation"] for edge in brief["edges"] if edge["relation"] in DIRECTED_RELATIONS}
    markers = "".join(
        f'<marker id="arrow-{relation}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{RELATION_STYLES[relation][0]}"/></marker>'
        for relation in sorted(relations)
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(brief["title"])}</title>',
        f'<desc id="desc">{html.escape(brief["claim"])}</desc>',
        f'<defs>{markers}</defs>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<g id="header" font-family="Arial, Helvetica, sans-serif">',
        *[f'<text x="{width/2:g}" y="{title_start+i*24}" text-anchor="middle" font-size="22" font-weight="700" fill="#26384d">{html.escape(line)}</text>' for i, line in enumerate(title_lines)],
        *[f'<text x="{width/2:g}" y="{claim_start+i*16}" text-anchor="middle" font-size="13" fill="#59636e">{html.escape(line)}</text>' for i, line in enumerate(claim_lines)],
        '</g>',
        f'<g id="archetype" data-archetype="{archetype}"/>',
        '<g id="edges" fill="none" stroke-linecap="round" stroke-linejoin="round">',
    ]
    for index, edge in enumerate(brief["edges"]):
        a, b = positions[edge["from"]], positions[edge["to"]]
        x1, y1 = a["x"] + a["w"] / 2, a["y"] + a["h"] / 2
        x2, y2 = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        dx, dy = x2 - x1, y2 - y1
        # Intersect the center-to-center ray with each rectangle. The arrow tip
        # ends at the target boundary, so it remains visible above the node fill.
        scale = 1.0 / max(abs(dx) / (a["w"] / 2), abs(dy) / (a["h"] / 2), 1e-6)
        sx, sy = x1 + dx * scale, y1 + dy * scale
        scale = 1.0 / max(abs(dx) / (b["w"] / 2), abs(dy) / (b["h"] / 2), 1e-6)
        ray_length = math.hypot(dx, dy)
        arrow_clearance = 9 / ray_length if ray_length > 1e-6 and edge["relation"] in DIRECTED_RELATIONS else 0
        ex, ey = x2 - dx * (scale + arrow_clearance), y2 - dy * (scale + arrow_clearance)
        color, style = RELATION_STYLES[edge["relation"]]
        dash = ' stroke-dasharray="7 5"' if style == "dashed" else (' stroke-dasharray="2 5"' if style == "dotted" else "")
        marker = f' marker-end="url(#arrow-{edge["relation"]})"' if edge["relation"] in DIRECTED_RELATIONS else ""
        review = status(edge)
        opacity = "0.72" if review == "needs_review" else "1"
        source = html.escape(source_text(edge.get("source", "")), quote=True)
        parts.append(f'<path id="edge-{index}" data-from="{edge["from"]}" data-to="{edge["to"]}" data-relation="{edge["relation"]}" data-review-status="{review}" data-source="{source}" d="M {sx:.1f} {sy:.1f} L {ex:.1f} {ey:.1f}" stroke="{color}" stroke-width="2" opacity="{opacity}"{dash}{marker}/>')
        label = edge.get("label", "")
        if label:
            parts.append(f'<text x="{(sx+ex)/2:.1f}" y="{(sy+ey)/2-5:.1f}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="11" fill="{color}">{html.escape(label)}</text>')
    parts.append("</g>")
    parts.append('<g id="nodes" font-family="Arial, Helvetica, sans-serif">')
    for node in brief["nodes"]:
        box = positions[node["id"]]
        fill, stroke = COLORS[node["role"]]
        x, y, w, h = box["x"], box["y"], box["w"], box["h"]
        review = status(node)
        opacity = "0.78" if review == "needs_review" else "1"
        parts.append(f'<g id="node-{node["id"]}" data-role="{node["role"]}" data-review-status="{review}" data-source="{html.escape(source_text(node.get("source", "")), quote=True)}" opacity="{opacity}">')
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        label_lines = _wrap(node["label"], (w - 14) / 15)
        detail_lines = _wrap(node.get("detail", ""), (w - 14) / 11) if node.get("detail") else []
        total = len(label_lines) + len(detail_lines)
        start_y = y + h / 2 - (total - 1) * 9
        for i, line in enumerate(label_lines):
            parts.append(f'<text x="{x+w/2:.1f}" y="{start_y+i*19:.1f}" text-anchor="middle" font-size="15" font-weight="700" fill="#26384d">{html.escape(line)}</text>')
        detail_start = start_y + len(label_lines) * 19
        for i, line in enumerate(detail_lines):
            parts.append(f'<text x="{x+w/2:.1f}" y="{detail_start+i*15:.1f}" text-anchor="middle" font-size="11" fill="#626d78">{html.escape(line)}</text>')
        if node.get("source"):
            parts.append(f'<title>{html.escape("Source: " + source_text(node["source"]))}</title>')
        parts.append("</g>")
    parts.append("</g>")
    parts.append('<g id="relation-legend" font-family="Arial, Helvetica, sans-serif" font-size="10" fill="#59636e">')
    for index, relation in enumerate(sorted({edge["relation"] for edge in brief["edges"]})):
        x = 50 + (index % 4) * ((width - 100) / 4)
        y = height - 48 + (index // 4) * 16
        color, style = RELATION_STYLES[relation]
        dash = ' stroke-dasharray="7 5"' if style == "dashed" else (' stroke-dasharray="2 5"' if style == "dotted" else "")
        marker = f' marker-end="url(#arrow-{relation})"' if relation in DIRECTED_RELATIONS else ""
        parts.append(f'<path d="M {x:.1f} {y-3:.1f} h 24" stroke="{color}" stroke-width="1.5"{dash}{marker}/><text x="{x+34:.1f}" y="{y:.1f}">{relation}</text>')
    parts.append("</g>")
    if status(brief) == "needs_review" or any(status(item) == "needs_review" for item in brief["nodes"] + brief["edges"]):
        parts.append(f'<text id="review-notice" x="{width/2:g}" y="{height-10}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="10" fill="#9c3540">DRAFT: contains claims or relationships requiring author review</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def write_svg(brief: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_svg(brief), encoding="utf-8")
    return target
