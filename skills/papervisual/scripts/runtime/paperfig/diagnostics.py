"""Read-only diagnostics run before optional exports or math parsing."""

import importlib
import shutil
import sys


def diagnose():
    modules = {}
    for name in ('cairosvg', 'matplotlib', 'fontTools', 'PIL', 'pymupdf', 'pypdf'):
        try:
            module = importlib.import_module(name)
            modules[name] = {'available': True, 'version': getattr(module, '__version__', 'unknown')}
        except Exception as exc:
            modules[name] = {'available': False, 'reason': f'{type(exc).__name__}: {exc}'}
    fonts = []
    if modules['matplotlib']['available']:
        from matplotlib.font_manager import findfont, FontProperties
        for family in ('Arial', 'Times New Roman', 'STIXGeneral', 'Microsoft YaHei'):
            try:
                path = findfont(FontProperties(family=[family]), fallback_to_default=False)
                fonts.append({'family': family, 'path': path, 'available': True})
            except ValueError:
                fonts.append({'family': family, 'available': False})
    tools = {name: shutil.which(name) for name in ('pdftotext', 'pdftoppm', 'inkscape', 'chrome', 'msedge')}
    return {'python': sys.version.split()[0], 'modules': modules, 'fonts': fonts,
            'tools': tools, 'preview_status': 'not_inspected',
            'notes': ['A discovered viewer or PDF reader is not proof of visual inspection or PDF parsing success.',
                      'Core SVG needs only Python; math needs matplotlib; measured text/glyph QA needs the audit extra.']}
