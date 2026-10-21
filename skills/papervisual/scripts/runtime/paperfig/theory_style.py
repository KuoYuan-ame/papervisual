"""Layered proof map with a dominant theorem and adjacent conditions."""

import html
import re

from .edge_labels import label_svg
from .layout import _layered, _wrap
from .mathsvg import formula_svg
from .model import BriefError
from .provenance import source_text, status
from .reference_style import BLUE, BLUE_DARK, GRAY_PALE, ROLE_STYLE, _rect, _multiline


def theory_layout(brief):
    nodes = brief['nodes']
    levels = _layered(nodes, brief['edges'])
    # _layered's fallback is for general graphs; a proof map must be acyclic.
    for edge in brief['edges']:
        if edge['relation'] != 'feedback' and levels[edge['from']] >= levels[edge['to']]:
            raise BriefError('Theory proof map contains a cycle; remove/reclassify unsupported dependencies.')
    # Independent tools belong immediately before the result they support.
    # Keep terminal corollaries in their original layer to preserve full-width math.
    dependencies = [e for e in brief['edges'] if e['relation'] != 'feedback']
    for node in nodes:
        outgoing = [e for e in dependencies if e['from'] == node['id']]
        incoming = [e for e in dependencies if e['to'] == node['id']]
        if outgoing and not incoming:
            levels[node['id']] = min(levels[e['to']] for e in outgoing)-1
    width = 1000.
    size = max(11.5, brief.get('min_font_pt', 8) * width * 25.4 / (brief.get('width_mm', 297)*72))
    positions, content = {}, {}
    header = 34 + len(_wrap(brief['title'], 920/(size*1.4)))*size*1.8
    header += len(_wrap(brief['claim'], 920/size))*size*1.4 + 20
    y = header
    for level in sorted(set(levels.values())):
        row = sorted([n for n in nodes if levels[n['id']] == level], key=lambda n: n.get('order', 0))
        card_w = (width-80-(len(row)-1)*26)/len(row)
        for i, node in enumerate(row):
            main = node.get('emphasis') == 'main'
            font = size*1.18 if main else size
            available = card_w-28
            label = _wrap(node['label'], available/(font*1.12))
            detail = _wrap(node.get('detail', ''), available/font) if node.get('detail') else []
            conditions = []
            for field, title in (('assumptions', 'Assumptions'), ('equality', 'Equality')):
                if node.get(field):
                    conditions += _wrap(title+': '+node[field], available/font)
            conditions += [line for annotation in node.get('annotations', []) for line in _wrap(annotation, available/font)]
            top = y+15
            formula = None
            formula_h = 0
            formula_size = font*1.25
            if node.get('formula'):
                formula, _, formula_h = formula_svg(node['formula'], 0, 0, size=formula_size,
                                                     max_width=available, key=node['id'])
                smallest = float(re.search(r'data-math-min-font-size="([^"]+)"', formula)[1])
                target = brief.get('min_font_pt',8)*width*25.4/(brief.get('width_mm',297)*72)
                if smallest < target:
                    formula_size *= target/smallest
                    formula, _, formula_h = formula_svg(node['formula'],0,0,size=formula_size,
                                                         max_width=available,key=node['id'])
            h = (30 + len(label)*font*1.35 + len(detail)*font*1.3
                 + (formula_h+16 if formula else 0) + len(conditions)*font*1.3 + (12 if conditions else 0))
            positions[node['id']] = dict(x=40+i*(card_w+26), y=y, w=card_w, h=h)
            content[node['id']] = dict(size=font, label=label, detail=detail, conditions=conditions,
                                       formula_h=formula_h, formula_size=formula_size, top=top)
        y += max(positions[n['id']]['h'] for n in row)
        if level < max(levels.values()):
            y += max(82, 22*len([e for e in brief['edges'] if levels[e['to']] == level+1]))
    caption = _wrap(brief.get('caption', brief['claim']), 920/size)
    height = y+45+len(caption)*size*1.35+30
    return dict(width=width, height=height, positions=positions, content=content, size=size,
                header=header, caption=caption, footer_y=y+32, levels=levels)


def render_theory_svg(brief):
    geom = theory_layout(brief)
    w, h, boxes, size = geom['width'], geom['height'], geom['positions'], geom['size']
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
             f'<title>{html.escape(brief["title"])}</title>',
             '<defs><marker id="proof-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 Z" fill="#315b9b"/></marker></defs>',
             '<defs><marker id="special-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 Z" fill="#ef7100"/></marker></defs>',
             _rect(0, 0, w, h, fill='#ffffff')]
    title = _wrap(brief['title'], 920/(size*1.4))
    parts.append(_multiline(40, 32, title, size=size*1.4, fill=BLUE, weight='700', line_height=size*1.8))
    parts.append(_multiline(40, 38+len(title)*size*1.8, _wrap(brief['claim'], 920/size),
                            size=size, fill=BLUE_DARK, line_height=size*1.4))
    parts.append('<g id="edges">')
    paths = []
    for i, edge in enumerate(brief['edges']):
        a, b = boxes[edge['from']], boxes[edge['to']]
        x1, y1, x2, y2 = a['x']+a['w']/2, a['y']+a['h'], b['x']+b['w']/2, b['y']-4
        mid = (y1+y2)/2
        points = [(x1,y1),(x1,mid),(x2,mid),(x2,y2)]
        if geom['levels'][edge['to']] - geom['levels'][edge['from']] > 1:
            lane = 15 + (i%3)*6
            row_bottom = max(boxes[k]['y']+boxes[k]['h'] for k in boxes
                             if geom['levels'][k] == geom['levels'][edge['from']])
            points = [(x1,y1), (x1,row_bottom+18), (lane,row_bottom+18),
                      (lane,y2-20), (x2,y2-20), (x2,y2)]
        paths.append(points)
        color = '#ef7100' if edge['relation'] == 'specialization' else BLUE
        marker = 'special-arrow' if edge['relation'] == 'specialization' else 'proof-arrow'
        marker_attr = '' if edge['relation'] in {'association','contrast'} else f' marker-end="url(#{marker})"'
        d = 'M '+' L '.join(f'{x:.2f} {y:.2f}' for x,y in points)
        parts.append(f'<path id="edge-{i}" data-from="{edge["from"]}" data-to="{edge["to"]}" '
                     f'data-relation="{edge["relation"]}" data-source="{html.escape(source_text(edge.get("source")), quote=True)}" '
                     f'data-review-status="{status(edge)}" d="{d}" fill="none" stroke="{color}" '
                     f'stroke-width="1.5" stroke-dasharray="5 3"{marker_attr}/>')
    parts.append('</g>')
    for node in brief['nodes']:
        box, content = boxes[node['id']], geom['content'][node['id']]
        x,y,cw,ch = (box[k] for k in ('x','y','w','h'))
        font = content['size']
        main = node.get('emphasis') == 'main'
        fill, stroke = ROLE_STYLE[node['role']]
        parts.append(f'<g id="node-{node["id"]}" data-review-status="{status(node)}" '
                     f'data-source="{html.escape(source_text(node.get("source")), quote=True)}">')
        parts.append(_rect(x,y,cw,ch,fill=fill if main else GRAY_PALE,stroke=stroke,
                           width=2.8 if main else 1.5,radius=8,dash='' if main else '5 3'))
        yy = y+font+12
        parts.append(_multiline(x+14,yy,content['label'],size=font*1.12,fill=stroke,weight='700',line_height=font*1.35))
        yy += len(content['label'])*font*1.35+4
        if content['detail']:
            parts.append(_multiline(x+14,yy,content['detail'],size=font,fill=BLUE_DARK,line_height=font*1.3))
            yy += len(content['detail'])*font*1.3
        if node.get('formula'):
            formula, _, fh = formula_svg(node['formula'], x+14, yy+3, size=content['formula_size'],
                                          max_width=cw-28,key=node['id'])
            parts.append(formula)
            yy += fh+font+12
        if content['conditions']:
            parts.append(_multiline(x+14,yy,content['conditions'],size=font,fill=BLUE_DARK,line_height=font*1.3))
        parts.append('</g>')
    used = []
    for i,(edge,points) in enumerate(zip(brief['edges'],paths)):
        if edge.get('label'):
            parts.append(label_svg(edge['label'],i,points,boxes,used,size=size,canvas_width=w))
    parts.append(_multiline(40,geom['footer_y'],geom['caption'],size=size,fill=BLUE_DARK,line_height=size*1.35))
    if any(status(item) != 'confirmed' for item in [brief,*brief['nodes'],*brief['edges']]):
        parts.append(_multiline(40,h-12,['DRAFT - scientific interpretation requires author review'],size=size,fill='#c80013'))
    parts.append('</svg>')
    return '\n'.join(parts)
