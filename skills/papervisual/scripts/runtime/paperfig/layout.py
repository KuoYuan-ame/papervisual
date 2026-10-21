"""Deterministic archetype layouts for small scientific framework diagrams."""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any

from .recommend import _hub_id, recommend

MARGIN = 90
BOTTOM_MARGIN = 70
NODE_W = 190
NODE_H = 108


def _ordered(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(nodes, key=lambda n: (n.get("order", 1e9), n["id"]))


def _layered(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, int]:
    ids = [n["id"] for n in nodes]
    outgoing: dict[str, list[str]] = defaultdict(list)
    indegree = {node_id: 0 for node_id in ids}
    for edge in edges:
        if edge["relation"] == "feedback":
            continue
        outgoing[edge["from"]].append(edge["to"])
        indegree[edge["to"]] += 1
    queue = deque(node_id for node_id in ids if indegree[node_id] == 0)
    level = {node_id: 0 for node_id in queue}
    while queue:
        source = queue.popleft()
        for target in outgoing[source]:
            level[target] = max(level.get(target, 0), level[source] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    # Cycles that are not feedback-marked are kept visible in a final layer.
    max_level = max(level.values(), default=0)
    for node_id in ids:
        level.setdefault(node_id, max_level + 1)
    return level


def _text_units(text: str) -> float:
    return sum(1.0 if ord(char) > 0x2E80 else (0.3 if char.isspace() else 0.56) for char in text)


def _wrap(text: str, max_units: float) -> list[str]:
    lines: list[str] = []
    current = ""
    for token in text.split():
        # Split long unspaced strings (including CJK text) at character boundaries.
        pieces: list[str] = []
        piece = ""
        for char in token:
            if piece and _text_units(piece + char) > max_units:
                pieces.append(piece)
                piece = char
            else:
                piece += char
        if piece:
            pieces.append(piece)
        for word in pieces or [token]:
            candidate = f"{current} {word}".strip()
            if current and _text_units(candidate) > max_units:
                lines.append(current)
                current = word
            else:
                current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def header_top(brief: dict[str, Any], width: int) -> float:
    """Reserve enough graph space below the wrapped, editable header text."""
    title_lines = _wrap(brief["title"], (width - 100) / 13.2)
    claim_lines = _wrap(brief["claim"], (width - 100) / 7.4)
    title_start = 42
    claim_start = title_start + len(title_lines) * 24 + 2
    return max(MARGIN, claim_start + len(claim_lines) * 16 + 16)


def layout(brief: dict[str, Any]) -> tuple[str, dict[str, dict[str, float]]]:
    nodes = brief["nodes"]
    edges = brief["edges"]
    width = brief.get("width", 1200)
    height = brief.get("height", 600)
    archetype = brief.get("archetype", "auto")
    if archetype == "auto":
        archetype, _ = recommend(brief)
    positions: dict[str, dict[str, float]] = {}
    inner_w = width - 2 * MARGIN
    top_margin = header_top(brief, width)
    inner_h = height - top_margin - BOTTOM_MARGIN
    center_y = top_margin + inner_h / 2

    if archetype in {"pipeline", "timeline"}:
        ordered = _ordered(nodes)
        columns = min(5, len(ordered), max(1, int((inner_w + 16) / (NODE_W + 16))))
        rows = math.ceil(len(ordered) / columns)
        for index, node in enumerate(ordered):
            col, row = index % columns, index // columns
            x = MARGIN + (inner_w - NODE_W) * col / max(1, columns - 1)
            y = top_margin + (inner_h - NODE_H) / 2 if rows == 1 else top_margin + (inner_h - NODE_H) * row / (rows - 1)
            positions[node["id"]] = {"x": x, "y": y, "w": NODE_W, "h": NODE_H}
    elif archetype == "compare":
        left = [n for n in _ordered(nodes) if n.get("group", "baseline").lower() in {"baseline", "control", "existing", "problem"}]
        right = [n for n in _ordered(nodes) if n not in left]
        if not left or not right:
            ordered = _ordered(nodes)
            split = max(1, len(ordered) // 2)
            left, right = ordered[:split], ordered[split:]
        for col, group in enumerate((left, right)):
            x = MARGIN + (inner_w - NODE_W) * col
            for row, node in enumerate(group):
                y = top_margin + (inner_h - NODE_H) * row / max(1, len(group) - 1)
                positions[node["id"]] = {"x": x, "y": y, "w": NODE_W, "h": NODE_H}
    elif archetype == "hub_spoke":
        core_id = _hub_id(brief)
        core = next((n for n in nodes if n["id"] == core_id), nodes[0])
        positions[core["id"]] = {"x": width / 2 - NODE_W / 2, "y": center_y - NODE_H / 2, "w": NODE_W, "h": NODE_H}
        others = [n for n in _ordered(nodes) if n["id"] != core["id"]]
        rx, ry = inner_w * 0.40, min(inner_h * 0.39, max(0, (inner_h - NODE_H) / 2))
        for i, node in enumerate(others):
            angle = -math.pi / 2 + 2 * math.pi * i / max(1, len(others))
            positions[node["id"]] = {"x": width / 2 + rx * math.cos(angle) - NODE_W / 2,
                                     "y": center_y + ry * math.sin(angle) - NODE_H / 2,
                                     "w": NODE_W, "h": NODE_H}
    elif archetype == "loop":
        ordered = _ordered(nodes)
        rx, ry = inner_w * 0.36, min(inner_h * 0.35, max(0, (inner_h - NODE_H) / 2))
        for i, node in enumerate(ordered):
            angle = -math.pi / 2 + 2 * math.pi * i / len(ordered)
            positions[node["id"]] = {"x": width / 2 + rx * math.cos(angle) - NODE_W / 2,
                                     "y": center_y + ry * math.sin(angle) - NODE_H / 2,
                                     "w": NODE_W, "h": NODE_H}
    else:  # mechanism: topological layers, columns within each layer
        levels = _layered(nodes, edges)
        buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
        by_id = {n["id"]: n for n in nodes}
        for node_id, level in levels.items():
            buckets[level].append(by_id[node_id])
        max_level = max(buckets)
        for level, bucket in buckets.items():
            bucket = _ordered(bucket)
            y = top_margin + (inner_h - NODE_H) * level / max(1, max_level)
            for col, node in enumerate(bucket):
                x = width / 2 - NODE_W / 2 if len(bucket) == 1 else MARGIN + (inner_w - NODE_W) * col / (len(bucket) - 1)
                positions[node["id"]] = {"x": x, "y": y, "w": NODE_W, "h": NODE_H}
    return archetype, positions
