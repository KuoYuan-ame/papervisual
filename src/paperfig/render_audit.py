"""SVG geometry and optional font-metric checks; findings never certify visuals."""

from io import BytesIO
import xml.etree.ElementTree as ET

from .edge_labels import intersects, path_points

NS = '{http://www.w3.org/2000/svg}'


def segment_hits(a, b, box):
    # Liang-Barsky against a slightly inset rectangle, allowing border endpoints.
    left, top, width, height = box
    low, high = 0., 1.
    dx, dy = b[0]-a[0], b[1]-a[1]
    for p,q in ((-dx,a[0]-left),(dx,left+width-a[0]),(-dy,a[1]-top),(dy,top+height-a[1])):
        if abs(p) < 1e-9:
            if q < 0:
                return False
        elif p < 0:
            low = max(low,q/p)
        else:
            high = min(high,q/p)
    return low < high


def inspect_render(brief, svg_path, boxes, *, advanced=False):
    report = {'status': 'partial', 'findings': [], 'font_coverage': 'not_completed',
              'text_bounds': 'not_completed', 'line_geometry': 'completed',
              'limitations': ['Manual visual QA remains required; SVG effects, rotations and external fonts are not fully audited.']}
    findings = report['findings']
    try:
        root = ET.parse(svg_path).getroot()
    except (OSError, ET.ParseError) as exc:
        report.update(status='not_completed', findings=[f'Cannot inspect SVG: {exc}'])
        return report
    width = float(root.get('viewBox').split()[2])
    report['physical_size'] = {'status': 'not_specified'}
    if 'width_mm' in brief:
        factor = brief['width_mm']/width*72/25.4
        sizes = [float(e.get('font-size')) for e in root.iter() if e.get('font-size')]
        sizes += [float(e.get('data-math-min-font-size')) for e in root.iter() if e.get('data-math-min-font-size')]
        if sizes:
            report['physical_size'] = {'status': 'measured', 'width_mm': brief['width_mm'], 'min_font_pt': min(sizes)*factor,
                                       'required_pt': brief.get('min_font_pt', 8)}
            if min(sizes)*factor < brief.get('min_font_pt', 8)-.05:
                findings.append(f"Minimum text/script size {min(sizes)*factor:.2f} pt is below {brief.get('min_font_pt',8):g} pt.")
    labels = []
    formulas = []
    for element in root.iter(NS+'g'):
        if element.get('id','').startswith('formula-'):
            rect = tuple(map(float,element.get('data-bbox').split(',')))
            formulas.append((element.get('id'),rect))
            node_id = element.get('id').removeprefix('formula-')
            if node_id in boxes:
                box = boxes[node_id]
                if (rect[0]<box['x']+2 or rect[1]<box['y']+2 or rect[0]+rect[2]>box['x']+box['w']-2
                        or rect[1]+rect[3]>box['y']+box['h']-2):
                    findings.append(f"Formula crosses node '{node_id}' border.")
        if element.get('id','').startswith('edge-label-'):
            rect = tuple(map(float,element.get('data-bbox').split(',')))
            labels.append((element.get('id'),rect))
            for node_id, box in boxes.items():
                if intersects(rect,tuple(box[k] for k in ('x','y','w','h')),pad=0):
                    findings.append(f"Edge label {element.get('id')} overlaps node '{node_id}'.")
    for i,(name,rect) in enumerate(labels):
        for other,other_rect in labels[i+1:]:
            if intersects(rect,other_rect,pad=0):
                findings.append(f'Edge labels {name} and {other} collide.')
        for other,other_rect in formulas:
            if intersects(rect,other_rect,pad=0):
                findings.append(f'Edge label {name} collides with {other}.')
    for edge in root.iter(NS+'path'):
        if not edge.get('id','').startswith('edge-'):
            continue
        points = path_points(ET.tostring(edge,encoding='unicode'))
        if not points:
            report['line_geometry']='partial'
        for node_id,box in boxes.items():
            if node_id in (edge.get('data-from'),edge.get('data-to')):
                continue
            inset = (box['x']+1,box['y']+1,box['w']-2,box['h']-2)
            if any(segment_hits(a,b,inset) for a,b in zip(points,points[1:])):
                findings.append(f"Edge {edge.get('id')} crosses node '{node_id}'.")
    if not advanced:
        report['limitations'].append('Run qa --rendered with the audit extra for measured glyph/text checks.')
        return report
    try:
        import cairosvg
        import pymupdf
        from fontTools.ttLib import TTFont
        from matplotlib.font_manager import FontProperties, findfont
    except (ImportError,OSError) as exc:
        report.update(status='not_completed')
        report['limitations'].append(f'Measured audit dependencies unavailable: {exc}')
        return report
    parents = {child:parent for parent in root.iter() for child in parent}
    font_maps = {}
    for text in root.iter(NS+'text'):
        family = text.get('font-family')
        parent = text
        while not family and parent in parents:
            parent = parents[parent]
            family = parent.get('font-family')
        # These renderers supply one family list per text group. Generic CSS fallback is not assumed verified.
        families = [v.strip() for v in (family or 'Arial').split(',')]
        codepoints = {ord(c) for c in ''.join(text.itertext()) if not c.isspace()}
        supported = set()
        for family in families:
            try:
                path = findfont(FontProperties(family=[family]),fallback_to_default=False)
            except ValueError:
                continue
            if path not in font_maps:
                with TTFont(path) as font:
                    font_maps[path] = set(font.getBestCmap() or {})
            supported.update(font_maps[path])
        if not supported and codepoints:
            # A generic browser/Cairo fallback may render these characters even if
            # Matplotlib cannot resolve any explicitly declared SVG font family.
            # Check an actual available fallback, but disclose the uncertainty.
            try:
                fallback = findfont(FontProperties(family=families), fallback_to_default=True)
            except ValueError:
                fallback = None
            if fallback:
                if fallback not in font_maps:
                    with TTFont(fallback) as font:
                        font_maps[fallback] = set(font.getBestCmap() or {})
                supported.update(font_maps[fallback])
                report.setdefault('font_fallbacks', []).append({'requested': family or 'Arial', 'resolved': fallback})
        missing = codepoints-supported
        if missing:
            findings.append('Missing font glyph coverage: '+', '.join(f'U+{c:04X}' for c in sorted(missing)))
    if report.get('font_fallbacks'):
        report['limitations'].append('Unresolvable SVG font families were checked against an available fallback. Exact browser/print font matching requires manual inspection.')
    report['font_coverage']='completed'
    report['resolved_fonts']=list(font_maps)
    try:
        pdf = cairosvg.svg2pdf(bytestring=ET.tostring(root))
        with pymupdf.open(stream=BytesIO(pdf),filetype='pdf') as document:
            page = document[0]
            scale = width/page.rect.width
            words = [(word[:4],word[4]) for word in page.get_text('words')]
            measured=[]
            for rect,word in words:
                r = (rect[0]*scale,rect[1]*scale,(rect[2]-rect[0])*scale,(rect[3]-rect[1])*scale)
                measured.append((r,word))
                if r[0]<-.5 or r[1]<-.5 or r[0]+r[2]>width+.5 or r[1]+r[3]>float(root.get('viewBox').split()[3])+.5:
                    findings.append(f'Rendered text exceeds canvas: {word!r}.')
                for name,formula in formulas:
                    if intersects(r,formula,pad=-1):
                        findings.append(f'Measured text collides with {name}: {word!r}.')
                # Text crossing a card edge is a measured overflow.
                for node_id,box in boxes.items():
                    cx,cy=r[0]+r[2]/2,r[1]+r[3]/2
                    if box['x']<cx<box['x']+box['w'] and box['y']<cy<box['y']+box['h']:
                        if (r[0]<box['x']+2 or r[0]+r[2]>box['x']+box['w']-2
                                or r[1]<box['y']+2 or r[1]+r[3]>box['y']+box['h']-2):
                            findings.append(f"Measured text crosses node '{node_id}' border: {word!r}.")
            for i,(a,word) in enumerate(measured):
                for b,other in measured[i+1:]:
                    # Positive overlap beyond font bearings; spaces are separate words.
                    ix=min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])
                    iy=min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1])
                    if ix>1.5 and iy>min(a[3],b[3])*.35:
                        findings.append(f'Measured text collision: {word!r} / {other!r}.')
        report['text_bounds']='completed'
        report['status']='failed' if findings else 'passed'
    except Exception as exc:
        report['status']='not_completed'
        report['limitations'].append(f'Rendered text measurement failed: {exc}')
    report['findings']=list(dict.fromkeys(findings))
    return report
