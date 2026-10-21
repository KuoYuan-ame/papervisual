"""Input loading and dependency-free structural validation for figure briefs."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .provenance import source_present

ARCHETYPES = {"pipeline", "compare", "hub_spoke", "timeline", "mechanism", "loop"}
ROLES = {"input", "process", "evidence", "output", "caveat", "core", "context"}
RELATIONS = {"sequence", "data", "causal", "feedback", "contrast", "association", "hierarchy",
             "proof_dependency", "specialization"}
ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class BriefError(ValueError):
    """Raised when a brief is malformed or graph references are invalid."""


def load_brief(path: str | Path) -> dict[str, Any]:
    try:
        brief = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BriefError(str(exc)) from exc
    validate_brief(brief)
    return brief


def validate_brief(brief: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(brief, dict):
        raise BriefError("Brief root must be a JSON object.")
    root_fields = {"schema_version", "language", "title", "claim", "caption", "claim_source", "width_mm", "min_font_pt", "dpi", "style", "panel_labels", "panel_descriptors", "legend_labels", "show_crossrefs", "review_status", "archetype", "width", "height", "nodes", "edges", "notes"}
    for key in brief.keys() - root_fields:
        errors.append(f"Unknown top-level field: {key}.")
    for field in ("title", "claim"):
        if not isinstance(brief.get(field), str) or not brief[field].strip():
            errors.append(f"{field} must be a non-empty string.")
    if "caption" in brief and (not isinstance(brief["caption"], str) or not brief["caption"].strip()):
        errors.append("caption must be a non-empty string when provided.")
    if "style" in brief and (not isinstance(brief['style'],str) or brief["style"] not in {"default", "reference", "theory"}):
        errors.append("style must be 'default', 'reference', or 'theory'.")
    if "language" in brief and (not isinstance(brief["language"], str)
                                 or brief["language"] not in {"en", "zh"}):
        errors.append("language must be 'en' or 'zh'.")
    if "panel_labels" in brief and (
        not isinstance(brief["panel_labels"], dict)
        or any(not isinstance(key, str) or not isinstance(value, str) or not value.strip()
               for key, value in brief["panel_labels"].items())
    ):
        errors.append("panel_labels must map strings to non-empty strings.")
    for field in ("panel_descriptors", "legend_labels"):
        values = brief.get(field, {})
        if (not isinstance(values, dict)
                or any(not isinstance(key, str) or not isinstance(value, str)
                       for key, value in values.items())):
            errors.append(f"{field} must map strings to strings.")
    if (isinstance(brief.get("legend_labels"), dict)
            and not set(brief["legend_labels"]).issubset({"blue", "green", "orange", "red"})):
        errors.append("legend_labels keys must be blue, green, orange, or red.")
    if "show_crossrefs" in brief and not isinstance(brief["show_crossrefs"], bool):
        errors.append("show_crossrefs must be a boolean.")
    if not isinstance(brief.get("review_status", "needs_review"), str) or brief.get("review_status", "needs_review") not in {"confirmed", "needs_review"}:
        errors.append("review_status must be 'confirmed' or 'needs_review'.")
    if "schema_version" in brief and not isinstance(brief["schema_version"], str):
        errors.append("schema_version must be a string.")
    nodes = brief.get("nodes")
    edges = brief.get("edges")
    if not isinstance(nodes, list) or len(nodes) < 2:
        errors.append("nodes must be an array with at least two items.")
        nodes = []
    if not isinstance(edges, list):
        errors.append("edges must be an array.")
        edges = []

    ids: list[str] = []
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{i}] must be an object.")
            continue
        for key in node.keys() - {"id", "label", "detail", "annotations", "role", "group", "panel", "order", "source", "review_status", "formula", "emphasis", "assumptions", "equality"}:
            errors.append(f"nodes[{i}] has unknown field {key!r}.")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not ID_RE.fullmatch(node_id):
            errors.append(f"nodes[{i}].id must use letters, digits, '_' or '-'.")
        else:
            ids.append(node_id)
        if not isinstance(node.get("label"), str) or not node["label"].strip():
            errors.append(f"nodes[{i}].label must be a non-empty string.")
        if not isinstance(node.get("role"), str) or node.get("role") not in ROLES:
            errors.append(f"nodes[{i}].role must be one of: {', '.join(sorted(ROLES))}.")
        status = node.get("review_status", "needs_review")
        if not isinstance(status, str) or status not in {"confirmed", "needs_review"}:
            errors.append(f"nodes[{i}].review_status must be 'confirmed' or 'needs_review'.")
        if not isinstance(node.get("detail", ""), str):
            errors.append(f"nodes[{i}].detail must be a string.")
        annotations = node.get("annotations", [])
        if (not isinstance(annotations, list) or len(annotations) > 2
                or any(not isinstance(text, str) or not text.strip() for text in annotations)):
            errors.append(f"nodes[{i}].annotations must contain at most two non-empty strings.")
        for field in ("group", "panel"):
            if field in node and not isinstance(node[field], str):
                errors.append(f"nodes[{i}].{field} must be a string.")
        if "order" in node and (isinstance(node["order"], bool) or not isinstance(node["order"], (int, float))):
            errors.append(f"nodes[{i}].order must be a number.")
        elif "order" in node and not math.isfinite(node["order"]):
            errors.append(f"nodes[{i}].order must be finite.")
    if len(ids) != len(set(ids)):
        errors.append("node ids must be unique.")

    known = set(ids)
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edges[{i}] must be an object.")
            continue
        for key in edge.keys() - {"from", "to", "relation", "label", "review_status", "source"}:
            errors.append(f"edges[{i}] has unknown field {key!r}.")
        for endpoint in ("from", "to"):
            value = edge.get(endpoint)
            if not isinstance(value, str) or value not in known:
                errors.append(f"edges[{i}].{endpoint} references unknown node {edge.get(endpoint)!r}.")
        if not isinstance(edge.get("relation"), str) or edge.get("relation") not in RELATIONS:
            errors.append(f"edges[{i}].relation must be one of: {', '.join(sorted(RELATIONS))}.")
        if edge.get("from") == edge.get("to"):
            errors.append(f"edges[{i}] cannot connect a node to itself.")
        status = edge.get("review_status", "needs_review")
        if not isinstance(status, str) or status not in {"confirmed", "needs_review"}:
            errors.append(f"edges[{i}].review_status must be 'confirmed' or 'needs_review'.")
        for field in ("label",):
            if field in edge and not isinstance(edge[field], str):
                errors.append(f"edges[{i}].{field} must be a string.")
    for label, value in [("claim_source", brief.get("claim_source"))] + [
        (f"node {n.get('id')}.source", n.get("source")) for n in nodes if isinstance(n, dict)
    ] + [(f"edge {i}.source", e.get("source")) for i, e in enumerate(edges) if isinstance(e, dict)]:
        if value is not None and not source_present(value):
            errors.append(f"{label} must be nonempty text or a structured source locator.")
    for field, low, high in (("width_mm", 40, 1000), ("min_font_pt", 4, 40), ("dpi", 72, 1200)):
        value = brief.get(field)
        if field in brief and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not math.isfinite(value) or not low <= value <= high):
            errors.append(f"{field} must be a finite number from {low} to {high}.")
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        for field in ("formula", "assumptions", "equality"):
            if field in node and (not isinstance(node[field], str) or not node[field].strip()):
                errors.append(f"nodes[{i}].{field} must be nonempty text.")
        if "emphasis" in node and node["emphasis"] not in ("normal", "main"):
            errors.append(f"nodes[{i}].emphasis must be normal or main.")
        if node.get("formula") and brief.get("style") != "theory":
            errors.append("Formula fields currently require style=theory; never silently omit math.")
    if brief.get("style") == "theory" and sum(n.get("emphasis") == "main" for n in nodes
                                               if isinstance(n, dict)) != 1:
        errors.append("Theory style needs exactly one main theorem node (emphasis=main).")
    archetype = brief.get("archetype", "auto")
    if not isinstance(archetype, str) or archetype not in ARCHETYPES | {"auto"}:
        errors.append(f"archetype must be 'auto' or one of: {', '.join(sorted(ARCHETYPES))}.")
    for dim in ("width", "height"):
        if dim in brief and (type(brief[dim]) is not int or not 600 <= brief[dim] <= 4000):
            errors.append(f"{dim} must be an integer from 600 to 4000.")
    if "notes" in brief and (not isinstance(brief["notes"], list) or any(not isinstance(note, str) for note in brief["notes"])):
        errors.append("notes must be an array of strings.")
    if brief.get("style") == "reference":
        panel_labels = [node.get("panel") for node in nodes if isinstance(node, dict)]
        if any(not isinstance(label, str) or not label.strip() for label in panel_labels):
            errors.append("Every node needs a non-empty panel label when style is 'reference'.")
        elif not 2 <= len(set(panel_labels)) <= 4:
            errors.append("Reference style requires two to four distinct panel labels.")
    if errors:
        raise BriefError("\n".join(errors))
    return []
