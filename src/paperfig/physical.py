"""Physical SVG/PDF size and raster density use one export contract."""

import json
import xml.etree.ElementTree as ET


def finalize(svg, brief):
    if "width_mm" not in brief:
        return svg
    root = ET.fromstring(svg)
    _, _, w, h = map(float, root.get("viewBox").split())
    width = brief["width_mm"]
    # Do not reserialize: preserve SVG namespaces and editable text bytes.
    import re
    svg = re.sub(r'(<svg\b[^>]*\bwidth=")[^"]+', rf'\g<1>{width:g}mm', svg, count=1)
    svg = re.sub(r'(<svg\b[^>]*\bheight=")[^"]+', rf'\g<1>{width*h/w:g}mm', svg, count=1)
    metadata = json.dumps({k: brief[k] for k in ("width_mm", "dpi", "min_font_pt") if k in brief})
    return svg.replace('</svg>', f'<metadata id="export-contract">{metadata}</metadata></svg>')


def png_options(brief):
    if "width_mm" in brief:
        return {"output_width": round(brief["width_mm"] / 25.4 * brief.get("dpi", 300))}
    return {"scale": 2}
