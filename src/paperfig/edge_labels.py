"""Independent edge labels with deterministic placement around node boxes."""

import html
import math
import re

from .layout import _text_units, _wrap


def intersects(a, b, pad=2):
    return (min(a[0]+a[2], b[0]+b[2]) - max(a[0], b[0]) > -pad
            and min(a[1]+a[3], b[1]+b[3]) - max(a[1], b[1]) > -pad)


def path_points(path):
    data = re.search(r'\bd="([^"]+)"', path)
    if not data or re.search(r'[ACHQSTVZachqstvz]', data[1]):
        return []
    values = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', data[1])]
    return list(zip(values[::2], values[1::2]))


def label_svg(label, index, points, boxes, used, *, size=11, canvas_width=1007,
              y_range=None, obstacles=()):
    lines = _wrap(label, 145/size)
    width = min(canvas_width-12, max(_text_units(t)*size for t in lines)+12)
    height = len(lines)*size*1.2+8
    segments = sorted(zip(points, points[1:]), key=lambda ab: math.dist(*ab), reverse=True)
    candidates = []
    blocked = [tuple(v[k] for k in ('x','y','w','h')) for v in boxes.values()] + list(obstacles)
    def candidate(rect, anchor):
        if y_range and (rect[1] < y_range[0] or rect[1]+rect[3] > y_range[1]):
            return
        collisions = sum(intersects(rect, other) for other in blocked)
        collisions += sum(intersects(rect, other) for other in used)
        distance = math.dist((rect[0]+width/2, rect[1]+height/2), anchor)
        candidates.append((collisions*100000 + distance, rect, anchor))
    for a, b in segments:
        for fraction in (.5, .3, .7):
            x, y = a[0]+(b[0]-a[0])*fraction, a[1]+(b[1]-a[1])*fraction
            for ox, oy in ((0, 0), (0, -height/2-4), (width/2+6, 0), (-width/2-6, 0)):
                rect = (max(4, min(canvas_width-width-4, x-width/2+ox)), y-height/2+oy, width, height)
                candidate(rect, (x,y))
    # A short link can have no space for a label. Search nearby clear space
    # and keep an explicit leader to the actual link instead of hiding text.
    if y_range and segments:
        for x in range(8, int(canvas_width-width-8), 18):
            for y in range(int(y_range[0]), int(y_range[1]-height), 12):
                center = (x+width/2, y+height/2)
                anchors = []
                for a,b in segments:
                    dx,dy = b[0]-a[0], b[1]-a[1]
                    t = max(0,min(1,((center[0]-a[0])*dx+(center[1]-a[1])*dy)/(dx*dx+dy*dy or 1)))
                    anchors.append((a[0]+t*dx,a[1]+t*dy))
                candidate((x,y,width,height), min(anchors,key=lambda p: math.dist(center,p)))
    if not candidates:
        return ''
    _, rect, anchor = min(candidates, key=lambda item: item[0])
    used.append(rect)
    x, y, w, h = rect
    spans = ''.join(f'<tspan x="{x+w/2:.2f}" dy="{0 if i==0 else size*1.2:.2f}">{html.escape(t)}</tspan>'
                    for i, t in enumerate(lines))
    target = (max(x,min(x+w,anchor[0])),max(y,min(y+h,anchor[1])))
    leader = ''
    if math.dist(anchor,target)>8:
        leader = (f'<path d="M {anchor[0]:.2f} {anchor[1]:.2f} L {target[0]:.2f} {target[1]:.2f}" '
                  'stroke="#777777" stroke-width="0.8" stroke-dasharray="2 2" fill="none"/>')
    return (f'<g id="edge-label-{index}" data-bbox="{x:.2f},{y:.2f},{w:.2f},{h:.2f}">{leader}'
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="3" fill="#ffffff"/>'
            f'<text x="{x+w/2:.2f}" y="{y+size+3:.2f}" text-anchor="middle" '
            f'font-family="Arial, sans-serif" font-size="{size}" fill="#243b63">{spans}</text></g>')
