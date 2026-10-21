"""A compact, panelized scientific-diagram theme inspired by the supplied sample.

The theme deliberately uses original vector primitives rather than copying any
source artwork. It is a visual treatment: the paper brief still owns the
labels, provenance, and relationships.
"""

from __future__ import annotations

import html

from typing import Any

from .provenance import source_text, status

from .layout import _text_units, _wrap
from .edge_labels import label_svg, path_points


BLUE = "#315b9b"
BLUE_DARK = "#243b63"
BLUE_PALE = "#eef1f7"
GREEN = "#4c8a37"
GREEN_PALE = "#edf5e8"
ORANGE = "#ef7100"
ORANGE_PALE = "#fff0db"
RED = "#c80013"
RED_PALE = "#ffe0e0"
GRAY = "#777777"
GRAY_DARK = "#5e5e5e"
GRAY_LINE = "#b2b2b2"
GRAY_PALE = "#f5f5f5"
WHITE = "#ffffff"

ROLE_STYLE = {
    "input": (BLUE_PALE, BLUE),
    "process": (BLUE_PALE, BLUE),
    "evidence": (GREEN_PALE, GREEN),
    "output": (ORANGE_PALE, ORANGE),
    "caveat": (RED_PALE, RED),
    "core": (BLUE_PALE, BLUE),
    "context": ("#eeeeee", GRAY),
}


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _font(brief: dict[str, Any]) -> str:
    text = " ".join([brief.get("title", ""), brief.get("claim", "")])
    if any(ord(char) > 127 for char in text):
        return "Microsoft YaHei, Arial, sans-serif"
    return "Arial, Helvetica, sans-serif"


def _svg_text(x: float, y: float, text: str, *, size: float = 16, fill: str = BLUE_DARK,
              weight: str = "400", anchor: str = "start", family: str = "Arial, sans-serif",
              italic: bool = False, extra: str = "") -> str:
    style = " font-style=\"italic\"" if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{family}" '
            f'font-size="{size:.1f}" font-weight="{weight}" fill="{fill}"{style}{extra}>'
            f'{_esc(text)}</text>')


def _multiline(x: float, y: float, lines: list[str], *, size: float, fill: str,
               weight: str = "400", anchor: str = "start", family: str = "Arial, sans-serif",
               line_height: float | None = None) -> str:
    if not lines:
        return ""
    step = line_height or size * 1.25
    spans = "".join(
        f'<tspan x="{x:.1f}" dy="{0 if i == 0 else step:.1f}">{_esc(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{family}" '
            f'font-size="{size:.1f}" font-weight="{weight}" fill="{fill}">{spans}</text>')


def _rect(x: float, y: float, w: float, h: float, *, fill: str = "none", stroke: str = "none",
          width: float = 1, radius: float = 0, dash: str = "", opacity: float | None = None) -> str:
    attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'width="{w:.1f}"', f'height="{h:.1f}"',
             f'fill="{fill}"', f'stroke="{stroke}"', f'stroke-width="{width:.1f}"']
    if radius:
        attrs.append(f'rx="{radius:.1f}"')
    if dash:
        attrs.append(f'stroke-dasharray="{dash}"')
    if opacity is not None:
        attrs.append(f'opacity="{opacity:.2f}"')
    return "<rect " + " ".join(attrs) + "/>"


def _line(x1: float, y1: float, x2: float, y2: float, *, stroke: str = BLUE_DARK,
          width: float = 1.5, dash: str = "", marker: str = "") -> str:
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    extra += f' marker-end="url(#{marker})"' if marker else ""
    return (f'<path d="M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}" fill="none" '
            f'stroke="{stroke}" stroke-width="{width:.1f}" stroke-linecap="round"{extra}/>')


def _poly(points: list[tuple[float, float]], *, fill: str, stroke: str = "none", width: float = 1) -> str:
    point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polygon points="{point_text}" fill="{fill}" stroke="{stroke}" stroke-width="{width:.1f}"/>'


def _label_backed_text(x: float, y: float, label: str, *, color: str, family: str,
                       size: float = 14, anchor: str = "middle") -> str:
    estimate = max(26.0, _text_units(label) * size + 14)
    left = x - estimate / 2 if anchor == "middle" else x
    return (_rect(left, y - size - 5, estimate, size + 11, fill=GRAY_PALE, stroke="none", radius=3)
            + _svg_text(x, y, label, size=size, fill=color, anchor=anchor, family=family))


def _icon_database(x: float, y: float, scale: float = 1.0, color: str = BLUE) -> str:
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.3f})">'
            f'<path d="M 0 0 C 0 -7 34 -7 34 0 L 34 31 C 34 38 0 38 0 31 Z" fill="#8fc4ee" stroke="{color}" stroke-width="2"/>'
            f'<ellipse cx="17" cy="0" rx="17" ry="7" fill="#7eb5e3" stroke="{color}" stroke-width="2"/>'
            f'<path d="M 0 15 C 0 22 34 22 34 15 M 0 30 C 0 37 34 37 34 30" fill="none" stroke="{color}" stroke-width="1.6"/>'
            "</g>")


def _icon_document(x: float, y: float, scale: float = 1.0, color: str = GREEN) -> str:
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.3f})">'
            f'<path d="M 2 1 H 21 L 30 10 V 39 H 2 Z" fill="#ffffff" stroke="{color}" stroke-width="2"/>'
            f'<path d="M 21 1 V 10 H 30" fill="#e9edf2" stroke="{color}" stroke-width="2"/>'
            f'<path d="M 8 17 H 24 M 8 23 H 24 M 8 29 H 21" stroke="{color}" stroke-width="2"/>'
            "</g>")


def _icon_magnifier(x: float, y: float, scale: float = 1.0, color: str = BLUE) -> str:
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.3f})">'
            f'<circle cx="15" cy="15" r="12" fill="#d7ecff" stroke="{color}" stroke-width="2"/>'
            '<path d="M 24 24 L 37 37" stroke="#7f4b2c" stroke-width="5" stroke-linecap="round"/>'
            '<circle cx="15" cy="15" r="8" fill="#f3fbff" opacity=".8"/>'
            "</g>")


def _icon_network(x: float, y: float, scale: float = 1.0, color: str = BLUE_DARK) -> str:
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.3f})">'
            '<path d="M 7 28 L 20 9 L 37 25 L 7 28 M 20 9 L 37 25" fill="none" stroke="#777" stroke-width="2"/>'
            f'<circle cx="7" cy="28" r="5" fill="#abd7a0" stroke="{color}" stroke-width="2"/>'
            f'<circle cx="20" cy="9" r="5" fill="#f2d77f" stroke="{color}" stroke-width="2"/>'
            f'<circle cx="37" cy="25" r="5" fill="#f1a4a4" stroke="{color}" stroke-width="2"/>'
            "</g>")


def _icon_shield(x: float, y: float, scale: float = 1.0, color: str = BLUE) -> str:
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.3f})">'
            f'<path d="M 20 2 L 37 8 V 21 C 37 32 28 39 20 43 C 12 39 3 32 3 21 V 8 Z" fill="#eaf3ff" stroke="{color}" stroke-width="2"/>'
            f'<path d="M 11 21 L 17 27 L 29 14" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
            "</g>")


def _icon_gavel(x: float, y: float, scale: float = 1.0, color: str = "#75432b") -> str:
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.3f}) rotate(12 20 20)">'
            f'<rect x="16" y="12" width="9" height="31" rx="2" fill="{color}"/>'
            f'<rect x="2" y="5" width="36" height="11" rx="2" fill="{color}" stroke="#4a2b1f" stroke-width="2"/>'
            '<path d="M 6 45 H 39" stroke="#777" stroke-width="4"/>'
            "</g>")


def _icon_plus(x: float, y: float, scale: float = 1.0, color: str = BLUE) -> str:
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.3f})">'
            f'<circle cx="20" cy="20" r="16" fill="#ffffff" stroke="{color}" stroke-width="2"/>'
            f'<path d="M 20 10 V 30 M 10 20 H 30" stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
            "</g>")


def _icon_warning(x: float, y: float, scale: float = 1.0, color: str = RED) -> str:
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({scale:.3f})">'
            f'<path d="M 20 2 L 39 38 H 1 Z" fill="#ffbbbb" stroke="{color}" stroke-width="2"/>'
            f'<path d="M 20 12 V 25 M 20 31 V 32" stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
            "</g>")


def _icon_for(node: dict[str, Any], x: float, y: float, scale: float = 1.0) -> str:
    # Semantic roles, not IDs from a particular paper, choose the icon.
    role = node.get("role", "context")
    icon = {"input": _icon_database, "evidence": _icon_document,
            "process": _icon_magnifier, "core": _icon_shield,
            "output": _icon_document, "caveat": _icon_warning,
            "context": _icon_network}[role]
    color = ROLE_STYLE[role][1]
    return icon(x, y, scale, color)


def _fit(text: str, width: float, size: float, max_lines: int = 2) -> tuple[list[str], float]:
    """Wrap without discarding text; enlarge the canvas for pathological briefs."""
    lines = _wrap(text, width / size)
    while (len(lines) > max_lines or any(_text_units(word) * size > width
                                        for word in text.split())) and size > 8:
        size -= .5
        lines = _wrap(text, width / size)
    return lines, size


def reference_layout(brief: dict[str, Any]) -> dict[str, Any]:
    """Shared geometry, in SVG viewBox units, for rendering and structural QA."""
    nodes = sorted(brief["nodes"], key=lambda node: node.get("order", 1e9))
    groups: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        groups.setdefault(node["panel"], []).append(node)
    output_width = max(1400, brief.get("width", 1800))
    output_height = max(870, brief.get("height", 1100))
    width = 1007.0
    height = max(625.0, output_height * width / output_width)
    # More nodes get more vertical room instead of microscopic cards.
    card_gap = 36 if any(e.get('label') for e in brief['edges']) else 20
    height = max(height, 296 + max(len(items) for items in groups.values()) * (86+card_gap))
    caption = brief.get("caption") or brief["title"] + ". " + brief["claim"]
    caption_lines, caption_size = _fit(caption, width - 20, 15, 4)
    footer_h = max(88, 30 + len(caption_lines) * caption_size * 1.22)
    gap, margin, body_y = 7.0, 16.0, 168.0
    panel_w = (width - 2 * margin - gap * (len(groups) - 1)) / len(groups)
    height += footer_h - 88
    body_h = height - body_y - footer_h
    positions = {}
    panels = {}
    for index, (name, items) in enumerate(groups.items()):
        x = margin + index * (panel_w + gap)
        panels[name] = (x, body_y, panel_w, body_h)
        if len(items) == 1:
            ys, card_h = [body_y + 179], 94.0
        else:
            card_h = min(86.0, (body_h - 94 - card_gap * (len(items) - 1)) / len(items))
            ys = [body_y + 70 + i * (card_h + card_gap) for i in range(len(items))]
        for node, y in zip(items, ys):
            positions[node["id"]] = dict(x=x + 12, y=y, w=panel_w - 24, h=card_h)
    return dict(width=width, height=height, output_width=output_width,
                output_height=round(height * output_width / width), groups=groups,
                panels=panels, positions=positions, footer_h=footer_h)


def _card(parts: list[str], node: dict[str, Any], box: dict[str, float], family: str,
          *, relation: str = "") -> None:
    x, y, w, h = (box[key] for key in ("x", "y", "w", "h"))
    fill, stroke = ROLE_STYLE[node["role"]]
    parts.append(f'<g id="node-{_esc(node["id"])}" data-role="{node["role"]}" '
                 f'data-review-status="{status(node)}" '
                 f'data-source="{_esc(source_text(node.get("source", "")))}">')
    parts.append(_rect(x, y, w, h, fill=fill, stroke=stroke, width=1.5, radius=9, dash="5 3"))
    parts.append(_icon_for(node, x + 10, y + 13, .65))
    title, size = _fit(node["label"], w - 55, 13.5)
    detail, dsize = _fit(node.get("detail", ""), w - 55, 11, 2)
    parts.append(_multiline(x + 45, y + 23, title, size=size, fill=stroke,
                            family=family, weight="700", line_height=size * 1.18))
    detail_y = y + 27 + len(title) * size * 1.18
    parts.append(_multiline(x + 45, detail_y, detail, size=dsize, fill=GRAY_DARK,
                            family=family, line_height=dsize * 1.17))
    if relation:
        lines, rsize = _fit(relation, w - 24, 10.5, 1)
        parts.append(_multiline(x + w / 2, y + h - 10, lines, size=rsize,
                                fill=GRAY_DARK, anchor="middle", family=family))
    annotations = node.get("annotations", [])
    if annotations:
        tag_w = (w - 18 - 5 * (len(annotations) - 1)) / len(annotations)
        for i, text in enumerate(annotations):
            xx = x + 9 + i * (tag_w + 5)
            parts.append(_rect(xx, y + h - 25, tag_w, 18, fill=WHITE,
                               stroke=stroke, width=.7, radius=2))
            lines, asize = _fit(text, tag_w - 8, 10, 1)
            parts.append(_multiline(xx + tag_w / 2, y + h - 12, lines,
                                    size=asize, fill=stroke, anchor="middle", family=family))
    parts.append(f'<title>{_esc(source_text(node.get("source", "")))}</title></g>')


def _chip(parts: list[str], node: dict[str, Any], x: float, y: float, w: float,
          family: str, label: str = "") -> None:
    parts.append(_rect(x, y, w, 73, fill="none", stroke=BLUE_DARK,
                       width=1.2, radius=7, dash="4 3"))
    parts.append(_icon_for(node, x + w / 2 - 10, y + 6, .48))
    lines, size = _fit(node["label"], w - 10, 10.8)
    parts.append(_multiline(x + w / 2, y + 39, lines, size=size, fill=BLUE,
                            weight="700", anchor="middle", family=family, line_height=12))
    if label:
        lines, size = _fit(label, w - 10, 9, 1)
        parts.append(_multiline(x + w / 2, y + 66, lines, size=size, fill=GRAY_DARK,
                                anchor="middle", family=family, line_height=10))


def render_reference_svg(brief: dict[str, Any]) -> str:
    """Render a dense overview, panel flow, small icons and manuscript caption."""
    geom = reference_layout(brief)
    width, height = geom["width"], geom["height"]
    groups, panels, positions = geom["groups"], geom["panels"], geom["positions"]
    nodes = {node["id"]: node for node in brief["nodes"]}
    edges = brief["edges"]
    zh = any(ord(char) > 0x2E80 for char in brief["title"])
    family = _font(brief)
    serif = "Microsoft YaHei" if zh else "Times New Roman"
    review = any(status(item) == "needs_review" for item in [brief, *nodes.values(), *edges])
    labels = brief.get("panel_labels", {})
    display = {name: labels.get(name, name.split("|", 1)[-1].strip()) for name in groups}
    show_crossrefs = brief.get("show_crossrefs", True)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{geom["output_width"]}" height="{geom["output_height"]}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{_esc(brief["title"])}</title>',
        f'<desc id="desc">{_esc(brief["claim"])}</desc>', '<defs>',
    ]
    for name, color in (("arrow-ref", GRAY_DARK), ("arrow-blue", BLUE), ("arrow-red", RED)):
        parts.append(f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 Z" fill="{color}"/></marker>')
    parts.extend(['</defs>', _rect(0, 0, width, height, fill=WHITE)])

    # Match the reference's 18% overview / 65% panel area / caption hierarchy.
    lx, lw, cx, cw, rx, rw = 18., 219., 247., 496., 753., 219.
    for x, w in ((lx, lw), (rx, rw)):
        parts.append(_rect(x, 10, w, 110, stroke=BLUE, width=1.5, dash="8 5"))
    overview = list(groups.values())[0][:3]
    for i, node in enumerate(overview):
        yy = 26 + i * 34
        parts.append(_icon_for(node, lx + 15, yy - 5, .58))
        lines, size = _fit(node["label"], lw - 69, 14, 1)
        parts.append(_multiline(lx + 65, yy + 14, lines, size=size, fill=BLUE,
                                family=family, weight="700", line_height=15))
    parts.append(_rect(cx, 10, cw, 35, stroke=BLUE, width=1.5, dash="8 5"))
    title, size = _fit(brief["title"], cw - 24, 18, 1)
    title_y = 29 if len(title) > 1 else 34
    parts.append(_multiline(cx + cw / 2, title_y, title, size=size, fill=BLUE,
                            weight="700", anchor="middle", family=family, line_height=size + 1))
    mini_w = (cw - (len(groups) - 1) * 7) / len(groups)
    for i, (name, items) in enumerate(groups.items()):
        xx = cx + i * (mini_w + 7)
        parts.append(_rect(xx, 58, mini_w, 62, stroke=BLUE, width=1.5, dash="7 4"))
        parts.append(_icon_for(items[0], xx + 10, 77, .60))
        lines, size = _fit(display[name], mini_w - 46, 13)
        parts.append(_multiline(xx + 40, 82, lines, size=size, fill=BLUE,
                                family=family, weight="700", line_height=16))
        parts.append(_line(cx + cw / 2, 45, xx + mini_w / 2, 56,
                           stroke=BLUE, width=1.2, marker="arrow-blue"))
    legend_labels = brief.get("legend_labels", {})
    default_legend = {
        "blue": (BLUE, "方法 / 主要结果" if zh else "Method / main result"),
        "green": (GREEN, "背景 / 依据" if zh else "Background / evidence"),
        "orange": (ORANGE, "输出 / 特殊情形" if zh else "Output / special case"),
        "red": (RED, "草稿 · 待作者核对" if zh else "Draft / author review"),
    }
    used_colors = {ROLE_STYLE[node["role"]][1] for node in nodes.values()}
    if review:
        used_colors.add(RED)
    legend = []
    for color_name in ("blue", "green", "orange", "red"):
        color, default_label = default_legend[color_name]
        if color in used_colors:
            legend.append((color, legend_labels.get(color_name, default_label)))
    for i, (color, text) in enumerate(legend):
        yy = 18 + i * 26
        parts.append(_icon_document(rx + 14, yy - 2, .51, color))
        lines, size = _fit(text, rw - 64, 13.2, 2)
        parts.append(_multiline(rx + 54, yy + 13, lines, size=size, fill=color,
                                weight="700", family=family, line_height=11))

    summary, summary_size = _fit(brief["claim"], width - 40, 12, 2)
    parts.append(_multiline(width / 2, 144, summary, size=summary_size, fill=BLUE_DARK,
                            weight="700", anchor="middle", family=family, line_height=14))

    for index, (name, (x, y, w, h)) in enumerate(panels.items()):
        parts.append(_rect(x, y, w, h, fill=GRAY_PALE, stroke="#dddddd"))
        parts.append(_rect(x, y, w, 33, fill=BLUE))
        lines, size = _fit(display[name], w - 40, 14, 1)
        parts.append(_multiline(x + w / 2, y + 22, lines, size=size, fill=WHITE,
                                weight="700", anchor="middle", family=family, line_height=15))
        if index:
            parts.append(_poly([(x - 23, y + 2), (x - 4, y + 2), (x + 13, y + 16.5),
                                (x - 4, y + 31), (x - 23, y + 31), (x - 6, y + 16.5)],
                               fill="#cecece", stroke=WHITE, width=1.4))
        items = groups[name]
        descriptors = brief.get("panel_descriptors", {})
        default_heading = ""
        if show_crossrefs:
            if index == 0:
                default_heading = "来源与定义" if zh else "Source ingredients"
            elif len(items) == 1:
                default_heading = "输入关系" if zh else "Incoming relationships"
            else:
                default_heading = "分组模块与关系" if zh else "Grouped modules and links"
        heading = descriptors.get(name, default_heading)
        if heading:
            parts.append(_svg_text(x + w / 2, y + 55, heading, size=13, fill=GRAY,
                                   family=serif, anchor="middle"))

    edge_labels = []
    used_label_boxes = []
    # Draw true graph edges under the cards; preserve direction and provenance.
    parts.append('<g id="edges" fill="none" stroke-linecap="round" stroke-linejoin="round">')
    for i, edge in enumerate(edges):
        a, b = positions[edge["from"]], positions[edge["to"]]
        same = nodes[edge["from"]]["panel"] == nodes[edge["to"]]["panel"]
        if same:
            x1 = x2 = a["x"] + a["w"] / 2
            if b["y"] >= a["y"]:
                y1, y2 = a["y"] + a["h"], b["y"] - 3
            else:
                y1, y2 = a["y"], b["y"] + b["h"] + 3
        else:
            forward = a["x"] < b["x"]
            x1 = a["x"] + (a["w"] if forward else 0)
            x2 = b["x"] + (0 if forward else b["w"])
            y1, y2 = a["y"] + a["h"] / 2, b["y"] + b["h"] / 2
        relation = edge["relation"]
        color, edge_style = {
            "causal": (RED, "solid"), "specialization": (ORANGE, "5 3"),
            "proof_dependency": (BLUE, "2 3"), "hierarchy": (BLUE, "5 3"),
            "association": (GRAY_DARK, "2 3"), "contrast": (ORANGE, "5 3"),
        }.get(relation, (GRAY_DARK, "solid"))
        dash = "" if edge_style == "solid" else edge_style
        marker = "" if relation in {"contrast", "association"} else (
            "arrow-red" if relation == "causal" else "arrow-blue" if relation == "proof_dependency"
            else "arrow-ref")
        path = _line(x1, y1, x2, y2, stroke=color, width=1.25, dash=dash, marker=marker)
        attrs = (f' id="edge-{i}" data-from="{edge["from"]}" data-to="{edge["to"]}" '
                 f'data-relation="{relation}" data-review-status="{status(edge)}" '
                 f'data-source="{_esc(source_text(edge.get("source", "")))}"')
        # Skip an intervening card along the panel gutter, so containment
        # edges cannot look like an invented sequential chain.
        if same and abs(a["y"] - b["y"]) > a["h"] + 25:
            x1, x2 = a["x"], b["x"]
            y1, y2 = a["y"] + a["h"] / 2, b["y"] + b["h"] / 2
            lane = min(x1, x2) - 7
            path = (f'<path d="M {x1:.1f} {y1:.1f} L {lane:.1f} {y1:.1f} '
                    f'L {lane:.1f} {y2:.1f} L {x2:.1f} {y2:.1f}" fill="none" '
                    f'stroke="{color}" stroke-width="1.25"'
                    + (f' stroke-dasharray="{dash}"' if dash else "")
                    + (f' marker-end="url(#{marker})"' if marker else "") + '/>')
        # A long jump goes below intervening cards instead of disappearing
        # under their fills. Adjacent panels retain the reference's short links.
        if not same and abs(a["x"] - b["x"]) > a["w"] * 1.5:
            lane = panels[nodes[edge["from"]]["panel"]][1] + panels[nodes[edge["from"]]["panel"]][3] - 11
            path = path.replace(f'M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}',
                                f'M {x1:.1f} {y1:.1f} L {x1 + 9:.1f} {y1:.1f} '
                                f'L {x1 + 9:.1f} {lane:.1f} L {x2 - 8:.1f} {lane:.1f} '
                                f'L {x2 - 8:.1f} {y2:.1f} L {x2:.1f} {y2:.1f}')
        parts.append(path.replace('<path ', '<path' + attrs + ' ', 1))
        if edge.get('label'):
            edge_labels.append((edge['label'], i, path_points(path)))
    parts.append('</g>')

    # A sparse panel gets a miniature view of its *actual* incoming edges.
    # Repeated source glyphs are cross-references, never invented modules.
    for name, items in groups.items():
        x, y, w, h = panels[name]
        if len(items) != 1:
            for node in items:
                _card(parts, node, positions[node["id"]], family,
                      relation="")
            continue
        node = items[0]
        if not show_crossrefs:
            _card(parts, node, positions[node["id"]], family)
            continue
        incoming = [e for e in edges if e["to"] == node["id"]]
        outgoing = [e for e in edges if e["from"] == node["id"]]
        target = positions[node["id"]]
        if incoming:
            chip_w = (w - 32 - 9 * (len(incoming) - 1)) / len(incoming)
            for i, edge in enumerate(incoming):
                xx = x + 16 + i * (chip_w + 9)
                _chip(parts, nodes[edge["from"]], xx, y + 68, chip_w, family, edge.get("label", ""))
                parts.append(_line(xx + chip_w / 2, y + 141, target["x"] + target["w"] / 2,
                                   target["y"] - 4, stroke=GRAY_DARK, width=1.2, dash="4 3",
                                   marker="" if edge["relation"] in {"association", "contrast"} else "arrow-ref"))
        _card(parts, node, target, family)
        if outgoing:
            lines = _wrap(" · ".join(e.get("label", "") or nodes[e["to"]]["label"] for e in outgoing), (w - 38) / 11)
            yy = target["y"] + target["h"] + 32
            parts.append(_line(x + w / 2, target["y"] + target["h"] + 3,
                               x + w / 2, yy - 11, stroke=GRAY_DARK, width=1.2, dash="4 3"))
            parts.append(_rect(x + 17, yy - 7, w - 34, 21 + len(lines) * 13,
                               stroke=BLUE_DARK, width=1.2, radius=8, dash="5 3"))
            parts.append(_multiline(x + w / 2, yy + 9, lines, size=11, fill=BLUE,
                                    anchor="middle", family=family, line_height=14))
            parts.append(_svg_text(x + w / 2, yy + 32 + len(lines) * 12,
                                   "下游关系见相邻栏" if zh else "See linked downstream panel",
                                   size=10.5, fill=GRAY, anchor="middle", family=serif))
    # Decorative cross-reference cards also reserve space for edge labels.
    import xml.etree.ElementTree as ET
    obstacles = []
    for fragment in parts:
        if not fragment.startswith('<rect '):
            continue
        rect = ET.fromstring(fragment)
        coords = tuple(float(rect.get(k)) for k in ('x','y','width','height'))
        if 190 < coords[1] and coords[2] < 250 and coords[3] < 120:
            obstacles.append(coords)
    for label, i, points in edge_labels:
        parts.append(label_svg(label, i, points, positions, used_label_boxes,
                               canvas_width=width, y_range=(232, height-geom['footer_h']-22),
                               obstacles=obstacles))
    if review:
        parts.append(_svg_text(width - 23, height - geom["footer_h"] - 7,
                               "结构草稿 · 科学内容待作者核对" if zh else "DRAFT · scientific interpretation requires author review",
                               size=10, fill=RED, anchor="end", family=family,
                               extra=' id="review-notice"'))
    # Caption stays editable; never truncate to an arbitrary line count.
    caption = brief.get("caption") or brief["title"] + ". " + brief["claim"]
    lines, size = _fit(caption, width - 20, 15, 4)
    parts.append(_multiline(8, height - geom["footer_h"] + 23, lines, size=size, fill="#111111",
                            family=serif, line_height=size * 1.22))
    parts.append('</svg>')
    return "\n".join(parts)
