"""Mathtext typesetting with preserved TeX source and accessible description.

Rendered formulas are vector paths, not directly editable text. Edit the
formula field and rerender; ordinary figure text remains editable SVG text.
"""

import hashlib
import html
from io import StringIO
import re
import xml.etree.ElementTree as ET

from .model import BriefError


def formula_svg(source, x, y, *, size, max_width, key):
    try:
        from matplotlib import rc_context
        from matplotlib.font_manager import FontProperties
        from matplotlib.mathtext import MathTextParser, math_to_image
    except ImportError as exc:
        raise BriefError("Formula typesetting requires the math extra (matplotlib).") from exc
    expression = source if source.startswith("$") and source.endswith("$") else "$" + source + "$"
    try:
        with rc_context({"mathtext.fontset": "stix", "svg.fonttype": "path",
                         "svg.hashsalt": "paperfig", "font.family": "STIXGeneral"}):
            parsed = MathTextParser("path").parse(expression, dpi=72, prop=FontProperties(size=size))
            # Refuse unsupported glyphs rather than emitting silent .notdef boxes.
            if any(not glyph[0].get_char_index(glyph[2]) for glyph in parsed.glyphs):
                raise BriefError(f"Formula contains an unsupported math glyph: {source}")
            output = StringIO()
            math_to_image(expression, output, prop=FontProperties(size=size), dpi=72, format="svg")
    except (ValueError, RuntimeError) as exc:
        raise BriefError(f"Invalid mathtext formula {source!r}: {exc}") from exc
    root = ET.fromstring(output.getvalue())
    width, height = map(float, (root.get("width").removesuffix("pt"), root.get("height").removesuffix("pt")))
    if width > max_width:
        raise BriefError(f"Formula in {key} needs {width:.1f} units but has {max_width:.1f}; "
                         "rearrange the figure or author a shorter equivalent formula; no automatic shrinking.")
    # Keep namespace declarations, remove nondeterministic RDF dates/background.
    body = output.getvalue()[output.getvalue().index('<svg'):]
    body = re.sub(r'<metadata>.*?</metadata>', '', body, flags=re.S)
    body = re.sub(r'<g id="patch_1">.*?</g>', '', body, flags=re.S)
    prefix = "math-" + hashlib.sha256(key.encode()).hexdigest()[:10] + "-"
    for match in re.findall(r'\bid="([^"]+)"', body):
        body = body.replace(f'id="{match}"', f'id="{prefix}{match}"')
        body = body.replace(f'#{match}"', f'#{prefix}{match}"')
    body = re.sub(r'width="[^"]+"', f'width="{width}"', body, count=1)
    body = re.sub(r'height="[^"]+"', f'height="{height}"', body, count=1)
    body = body.replace('<svg ', f'<svg x="{x:.2f}" y="{y:.2f}" ', 1)
    group = (f'<g id="formula-{html.escape(key)}" data-formula-source="{html.escape(source, quote=True)}" '
             f'data-math-font-size="{size}" data-math-min-font-size="{min((g[1] for g in parsed.glyphs), default=size)}" '
             f'data-bbox="{x},{y},{width},{height}" '
             'data-edit-mode="edit-TeX-in-brief-and-rerender">'
             f'<title>{html.escape(source)}</title>{body}</g>')
    return group, width, height
