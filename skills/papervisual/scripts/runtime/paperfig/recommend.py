"""Explainable layout recommendation based on declared graph relationships."""

from __future__ import annotations

from collections import Counter
from typing import Any


def _hub_id(brief: dict[str, Any]) -> str | None:
    """Return a deterministic, explicitly-core-or-highest-degree center."""
    nodes = brief.get("nodes", [])
    core = next((node["id"] for node in nodes if node.get("role") == "core"), None)
    if core is not None:
        return core
    degrees = Counter()
    for edge in brief.get("edges", []):
        degrees[edge["from"]] += 1
        degrees[edge["to"]] += 1
    return min(degrees, key=lambda node_id: (-degrees[node_id], node_id)) if degrees else None


def recommend(brief: dict[str, Any]) -> tuple[str, list[str]]:
    edges = brief.get("edges", [])
    nodes = brief.get("nodes", [])
    rel = Counter(edge["relation"] for edge in edges)
    degrees = Counter()
    for edge in edges:
        degrees[edge["from"]] += 1
        degrees[edge["to"]] += 1
    if rel["feedback"] >= 1:
        return "loop", ["The brief declares at least one feedback relationship."]
    if rel["contrast"] >= 1 or len({node.get("group") for node in nodes if node.get("group")}) >= 2:
        return "compare", ["The brief contains explicit contrast or grouped alternatives."]
    if rel["causal"] >= 2 or rel["hierarchy"] >= 2:
        return "mechanism", ["The brief emphasizes causal or hierarchical relationships."]
    time_words = ("time", "month", "day", "week", "season", "baseline", "follow-up", "before", "after")
    if sum(any(word in node.get("label", "").lower() for word in time_words) for node in nodes) >= 2:
        return "timeline", ["Multiple nodes are explicitly time-oriented."]
    hub = _hub_id(brief)
    if hub:
        if degrees[hub] >= max(3, len(nodes) - 2):
            return "hub_spoke", [f"Node '{hub}' acts as a shared center under the declared relationships."]
    sequential = sum(edge["relation"] in {"sequence", "data"} for edge in edges)
    if sequential >= max(1, len(edges) // 2):
        return "pipeline", ["Most declared relationships describe ordered steps or data flow."]
    return "mechanism", ["The graph is not a clear pipeline, contrast, loop, or hub; a neutral relation map is recommended."]
