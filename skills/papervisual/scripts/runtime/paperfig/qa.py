"""Structural, provenance, and approximate SVG geometry checks."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .layout import _text_units, header_top, layout
from .model import validate_brief
from .provenance import source_findings, status

SVG_NS = "{http://www.w3.org/2000/svg}"


def audit(brief: dict[str, Any], svg_path: str | Path | None = None, *, release: bool = False,
          require_confirmed: bool = False, rendered: bool = False) -> dict[str, Any]:
    validate_brief(brief)
    reference = brief.get("style") == "reference"
    if brief.get("style") == "theory":
        from .theory_style import theory_layout
        geometry = theory_layout(brief)
        archetype, boxes = "theory", geometry["positions"]
    elif reference:
        from .reference_style import reference_layout

        geometry = reference_layout(brief)
        archetype, boxes = "reference", geometry["positions"]
    else:
        archetype, boxes = layout(brief)
    warnings: list[str] = []
    errors: list[str] = []
    if rendered and not svg_path:
        errors.append('Rendered audit requires --svg; rendering checks were not completed.')
    width, height = ((geometry["width"], geometry["height"]) if (reference or brief.get("style") == "theory")
                     else (brief.get("width", 1200), brief.get("height", 600)))
    if brief.get("style", "default") == "default" and header_top(brief, width) + 108 > height - 70:
        warnings.append("Title and claim leave too little space for the graph; shorten them or enlarge the canvas.")
    if status(brief) == "needs_review":
        warnings.append("Central claim is a draft and needs author review.")
    for node in brief["nodes"]:
        box = boxes[node["id"]]
        if box["x"] < 0 or box["y"] < 0 or box["x"] + box["w"] > width or box["y"] + box["h"] > height:
            errors.append(f"Node '{node['id']}' falls outside the canvas.")
        if not any(edge["from"] == node["id"] or edge["to"] == node["id"] for edge in brief["edges"]):
            warnings.append(f"Node '{node['id']}' is isolated from all relationships.")
        if len(node["label"]) > 44:
            warnings.append(f"Node '{node['id']}' has a long label; inspect wrapping at final size.")
        if status(node) == "needs_review":
            warnings.append(f"Node '{node['id']}' needs author review.")
        if node.get("role") == "caveat" and not node.get("source"):
            warnings.append(f"Caveat node '{node['id']}' has no source anchor.")
    node_ids = list(boxes)
    for index, node_id in enumerate(node_ids):
        a = boxes[node_id]
        for other_id in node_ids[index + 1:]:
            b = boxes[other_id]
            overlap_x = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            overlap_y = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
            if overlap_x > 0 and overlap_y > 0:
                errors.append(f"Nodes '{node_id}' and '{other_id}' overlap; revise the layout or inspect manually.")
    for i, edge in enumerate(brief["edges"]):
        if status(edge) == "needs_review":
            warnings.append(f"Edge {i} ({edge['from']} -> {edge['to']}) still needs scientific review.")
        if edge["relation"] == "causal" and status(edge) != "confirmed":
            warnings.append(f"Causal edge {i} is not confirmed; verify that the source supports causality.")
        if edge["relation"] == "causal" and not edge.get("source"):
            warnings.append(f"Causal edge {i} has no source anchor.")

    if svg_path:
        try:
            root = ET.parse(svg_path).getroot()
        except (OSError, ET.ParseError) as exc:
            errors.append(f"SVG could not be parsed: {exc}")
        else:
            if root.tag != SVG_NS + "svg":
                errors.append("Output root is not an SVG element.")
            texts = list(root.iter(SVG_NS + "text"))
            if not texts:
                errors.append("SVG contains no editable text elements.")
            svg_ids = {element.attrib.get("id") for element in root.iter()}
            for node in brief["nodes"]:
                if f"node-{node['id']}" not in svg_ids:
                    errors.append(f"SVG is missing rendered node '{node['id']}'.")
            if "edges" not in svg_ids:
                errors.append("SVG is missing its edge group.")
            if not root.attrib.get("viewBox"):
                errors.append("SVG has no viewBox; responsive scaling may fail.")
            for group in root.iter(SVG_NS + "g"):
                if not group.attrib.get("id", "").startswith("node-"):
                    continue
                rect = group.find(SVG_NS + "rect")
                if rect is None:
                    continue
                box_width = float(rect.attrib["width"])
                box_top = float(rect.attrib["y"])
                box_bottom = box_top + float(rect.attrib["height"])
                for element in group.findall(SVG_NS + "text"):
                    spans = element.findall(SVG_NS + "tspan")
                    text = max((span.text or "" for span in spans), key=_text_units, default="") if spans else "".join(element.itertext())
                    size = float(element.attrib.get("font-size", "14"))
                    estimate = sum(1.0 if ord(char) > 0x2E80 else (0.3 if char.isspace() else 0.56) for char in text) * size
                    if estimate > box_width - 14:
                        warnings.append(f"Text may exceed its node box: {text[:40]!r}.")
                    baseline = float(element.attrib.get("y", "0"))
                    if baseline - size < box_top + 4 or baseline + size * 0.25 > box_bottom - 4:
                        warnings.append(f"Text may exceed node height: {text[:40]!r}.")
            # Approximate glyph widths and vertical bounds; the final render still needs visual review.
            for element in texts:
                spans = element.findall(SVG_NS + "tspan")
                text = max((span.text or "" for span in spans), key=_text_units, default="") if spans else "".join(element.itertext())
                size = float(element.attrib.get("font-size", "14"))
                x = float(element.attrib.get("x", "0"))
                y = float(element.attrib.get("y", "0"))
                anchor = element.attrib.get("text-anchor", "start")
                estimated = _text_units(text) * size
                left = x - estimated / 2 if anchor == "middle" else (x - estimated if anchor == "end" else x)
                if left < 0 or left + estimated > width:
                    warnings.append(f"Text may exceed canvas width: {text[:40]!r}.")
                if y < 0 or y > height:
                    warnings.append(f"Text baseline may exceed canvas height: {text[:40]!r}.")
    structure_errors = list(errors)
    missing_sources = source_findings(brief)
    warnings.extend(missing_sources)
    if release:
        errors.extend(missing_sources)
    pending = ["claim"] if status(brief) != "confirmed" else []
    pending += [n["id"] for n in brief["nodes"] if status(n) != "confirmed"]
    pending += [f"edge-{i}" for i, e in enumerate(brief["edges"]) if status(e) != "confirmed"]
    if require_confirmed and pending:
        errors.append("Author scientific confirmation is pending: " + ", ".join(pending))
    checks = {
        "structure": {"status": "failed" if structure_errors else "passed"},
        "sources": {"status": "failed" if missing_sources else "present_not_verified",
                    "missing": missing_sources},
        "author_confirmation": {"status": "pending" if pending else "declared_confirmed",
                                "pending": pending, "independently_verified": False},
        "rendering": {"status": "not_completed"},
        "visual_qa": {"status": "not_completed"},
    }
    if svg_path:
        from .render_audit import inspect_render
        checks["rendering"] = inspect_render(brief, svg_path, boxes, advanced=rendered)
        warnings.extend(checks["rendering"]["findings"])
        if release:
            errors.extend(checks["rendering"]["findings"])
            if checks["rendering"]["status"] == "not_completed":
                errors.append("Requested rendered checks could not complete.")
    return {"checks": checks, "release_mode": release, "archetype": archetype, "nodes": len(brief["nodes"]), "edges": len(brief["edges"]),
            "editable_text": True, "errors": errors, "warnings": warnings,
            "author_checklist": [
                "Confirm every node is supported by the paper.",
            "Check that the figure states the paper's specific contribution, not only its topic.",
            "Check that decisive evidence, assumptions, and scope boundaries are represented.",
            "Confirm arrows distinguish proof dependency, specialization, sequence, data flow, association, and causation.",
                "Check terminology, abbreviations, chronology, and limitations.",
            "Check that reader-facing text uses the requested figure language (English by default).",
                "Inspect SVG at final print size for overlap and legibility.",
            ]}
