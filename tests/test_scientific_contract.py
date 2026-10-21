"""Scientific release gates must fail for stripped evidence and unreadable output."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from paperfig.cli import main
from paperfig.model import BriefError, validate_brief
from paperfig.qa import audit
from paperfig.render import render_svg, write_svg


ROOT = Path(__file__).parents[1]


def reference():
    return json.loads((ROOT/'examples/reference.json').read_text(encoding='utf-8'))


class ScientificContractTests(unittest.TestCase):
    def test_malformed_physical_settings_are_rejected_before_render(self):
        for field,value in [('width_mm',None),('dpi',float('nan')),('min_font_pt',True),('style',[])]:
            brief=reference();brief[field]=value
            with self.subTest(field=field),self.assertRaises(BriefError):
                validate_brief(brief)
    def test_stripping_sources_and_statuses_cannot_pass_silently(self):
        brief = reference()
        brief.pop('claim_source')
        for item in [brief,*brief['nodes'],*brief['edges']]:
            item.pop('review_status',None)
            item.pop('source',None)
        validate_brief(brief)
        report = audit(brief)
        self.assertEqual(len(report['checks']['sources']['missing']),1+len(brief['nodes'])+len(brief['edges']))
        self.assertEqual(len(report['checks']['author_confirmation']['pending']),1+len(brief['nodes'])+len(brief['edges']))
        self.assertTrue(report['warnings'])
        self.assertTrue(audit(brief,release=True)['errors'])
        self.assertIn('review-notice',render_svg(brief))

    def test_sources_do_not_confirm_science_and_status_does_not_supply_sources(self):
        brief = reference()
        for item in [brief,*brief['nodes'],*brief['edges']]:
            item.pop('review_status',None)
        report=audit(brief,release=True)
        self.assertEqual(report['errors'],[])
        self.assertEqual(report['checks']['sources']['status'],'present_not_verified')
        self.assertTrue(audit(brief,release=True,require_confirmed=True)['errors'])
        for item in [brief,*brief['nodes'],*brief['edges']]:
            item['review_status']='confirmed'
            item.pop('source',None)
        brief.pop('claim_source')
        self.assertTrue(audit(brief,release=True)['errors'])

    def test_structured_sources_preserve_theorem_and_equation(self):
        brief=reference()
        brief['nodes'][0]['source']={'pages':'3','theorem':'1.2','equation':'1.5',
                                    'explanation':'Supports this bound.'}
        validate_brief(brief)
        self.assertIn('1.5',render_svg(brief))
        self.assertEqual(audit(brief)['checks']['sources']['missing'],[])
        brief['claim_source']={'explanation':'No actual locator'}
        with self.assertRaises(BriefError):
            validate_brief(brief)

    def test_release_cli_blocks_missing_claim_source(self):
        brief=reference()
        brief.pop('claim_source')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'brief.json'
            path.write_text(json.dumps(brief),encoding='utf-8')
            self.assertEqual(main(['validate',str(path),'--release']),2)
            self.assertEqual(main(['qa',str(path),'--release']),1)

    def test_annotations_cannot_hide_edge_labels(self):
        brief=reference()
        brief['edges'][0]['label']='Set k = j and r = 1'
        svg=render_svg(brief)
        self.assertIn('id="edge-label-0"',svg)
        self.assertIn('Set k = j and r = 1',svg)

    def test_physical_size_flags_too_small_text_and_exports_real_dpi(self):
        brief=reference()
        brief.update(width_mm=180,min_font_pt=8,dpi=300)
        with tempfile.TemporaryDirectory() as temp:
            svg=write_svg(brief,Path(temp)/'figure.svg')
            self.assertIn('width="180mm"',svg.read_text())
            report=audit(brief,svg,release=True)
            self.assertTrue(any('below' in error for error in report['errors']))
            try:
                import cairosvg
                from PIL import Image
            except ImportError:
                self.skipTest("Optional raster dependencies are not installed.")
            except OSError as exc:
                # An installed CairoSVG may still lack the native Cairo DLL.
                if "cairo" not in str(exc).lower():
                    raise
                self.skipTest("Optional Cairo native library could not be loaded.")
            target=Path(temp)/'figure.png'
            from paperfig.physical import png_options
            cairosvg.svg2png(url=str(svg),write_to=str(target),**png_options(brief))
            with Image.open(target) as image:
                self.assertEqual(image.width,round(180/25.4*300))

    def test_missing_measurement_dependency_is_not_completed(self):
        brief=reference()
        with tempfile.TemporaryDirectory() as temp:
            svg=write_svg(brief,Path(temp)/'figure.svg')
            with patch.dict('sys.modules',{'fontTools.ttLib':None}):
                report=audit(brief,svg,rendered=True,release=True)
            self.assertEqual(report['checks']['rendering']['status'],'not_completed')
            self.assertTrue(report['errors'])

    def test_detects_edges_crossing_other_cards_and_labels_over_nodes(self):
        brief=reference()
        with tempfile.TemporaryDirectory() as temp:
            svg=write_svg(brief,Path(temp)/'figure.svg')
            from paperfig.reference_style import reference_layout
            box=reference_layout(brief)['positions']['context']
            extra=(f'<path id="edge-bad" data-from="screen" data-to="estimate" '
                   f'd="M {box["x"]-10} {box["y"]+20} L {box["x"]+box["w"]+10} {box["y"]+20}"/>'
                   f'<g id="edge-label-bad" data-bbox="{box["x"]},{box["y"]},40,20"/>')
            svg.write_text(svg.read_text().replace('</svg>',extra+'</svg>'))
            report=audit(brief,svg)
            findings=report['checks']['rendering']['findings']
            self.assertTrue(any('crosses node' in item for item in findings))
            self.assertTrue(any('overlaps node' in item for item in findings))

    def test_rendered_checks_require_an_artifact(self):
        self.assertTrue(audit(reference(),rendered=True,release=True)['errors'])

    def test_measured_audit_detects_missing_glyph_and_real_text_collision(self):
        try:
            import cairosvg, pymupdf, fontTools, matplotlib  # noqa: F401
        except (ImportError, OSError):
            self.skipTest('Optional audit extra is not installed.')
        brief=reference()
        with tempfile.TemporaryDirectory() as temp:
            svg=write_svg(brief,Path(temp)/'figure.svg')
            extra=('<text x="20" y="160" font-size="16" font-family="Arial">SAME</text>'
                   '<text x="20" y="160" font-size="16" font-family="Arial">SAME</text>'
                   '<text x="90" y="160" font-size="16" font-family="Arial">&#x10FFFF;</text>')
            svg.write_text(svg.read_text().replace('</svg>',extra+'</svg>'))
            findings=audit(brief,svg,rendered=True,release=True)['errors']
            self.assertTrue(any('Missing font glyph' in f for f in findings))
            self.assertTrue(any('Measured text collision' in f for f in findings))


class MathContractTests(unittest.TestCase):
    def setUp(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest('Optional math extra is not installed.')

    def test_fraction_scripts_source_retained_and_repeat_deterministic(self):
        from paperfig.mathsvg import formula_svg
        source=r'\frac{Q_i^j(K)^{-1/(ij)}}{Q_i^j(L)}'
        first,_,height=formula_svg(source,0,0,size=16,max_width=600,key='main')
        second,_,_=formula_svg(source,0,0,size=16,max_width=600,key='main')
        self.assertEqual(first,second)
        self.assertIn('data-formula-source',first)
        self.assertIn(source,first)
        self.assertIn('<path',first)
        self.assertGreater(height,16)
        with self.assertRaises(BriefError):
            formula_svg(source,0,0,size=16,max_width=10,key='main')

    def test_theory_cycles_and_silently_omitted_formulas_rejected(self):
        brief=reference()
        brief['nodes'][0]['formula']='x_i^p'
        with self.assertRaises(BriefError):
            validate_brief(brief)
        brief.update(style='theory')
        brief['nodes'][0]['emphasis']='main'
        brief['edges'] += [dict(brief['edges'][0],**{'from':'estimate','to':'observations'})]
        validate_brief(brief)
        with self.assertRaises(BriefError):
            render_svg(brief)

    def test_unsupported_math_syntax_fails_instead_of_plain_string_fallback(self):
        from paperfig.mathsvg import formula_svg
        with self.assertRaises(BriefError):
            formula_svg(r'\notacommand{x}',0,0,size=14,max_width=500,key='test')

    def test_independent_tools_align_with_the_result_they_support(self):
        from paperfig.theory_style import theory_layout
        brief=json.loads((ROOT/'examples/theory/brief.json').read_text())
        brief['nodes'].append(dict(brief['nodes'][0],id='tool',label='Independent tool'))
        brief['edges'].append(dict(brief['edges'][0],**{'from':'tool','to':'case'}))
        levels=theory_layout(brief)['levels']
        self.assertEqual(levels['tool'],levels['case']-1)
        self.assertGreater(levels['tool'],levels['setup'])


if __name__=='__main__':
    unittest.main()
