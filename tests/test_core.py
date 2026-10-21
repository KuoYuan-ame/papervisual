import json
import math
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from paperfig.cli import STARTER, main
from paperfig.extract import draft_from_text
from paperfig.layout import layout
from paperfig.model import BriefError, validate_brief
from paperfig.qa import audit
from paperfig.recommend import recommend
from paperfig.render import render_svg


class CoreTests(unittest.TestCase):
    def test_reference_skip_edge_uses_gutter_instead_of_intervening_card(self):
        from paperfig.reference_style import reference_layout

        brief = json.loads((Path(__file__).parents[1] / "examples/reference.json")
                           .read_text(encoding="utf-8"))
        panel = brief["nodes"][0]["panel"]
        items = [node for node in brief["nodes"] if node["panel"] == panel]
        if len(items) < 3:
            extra = dict(items[-1], id="extra", order=2.5)
            brief["nodes"].append(extra)
        items = sorted([node for node in brief["nodes"] if node["panel"] == panel],
                       key=lambda node: node.get("order", 1e9))
        brief["edges"] = [{"from": items[0]["id"], "to": items[-1]["id"],
                           "relation": "hierarchy"}]
        boxes = reference_layout(brief)["positions"]
        root = ET.fromstring(render_svg(brief))
        edge = root.find(".//*[@id='edge-0']")
        coords = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", edge.attrib["d"])]
        self.assertEqual(len(coords), 8)
        self.assertLess(coords[2], boxes[items[1]["id"]]["x"])
        self.assertEqual(coords[2], coords[4])

    def test_examples_validate(self):
        root = Path(__file__).parents[1] / "examples"
        for path in root.glob("*.json"):
            with self.subTest(example=path.name):
                validate_brief(json.loads(path.read_text(encoding="utf-8")))

    def test_synthetic_recommendation_regressions(self):
        expected = {"pipeline": "pipeline", "compare": "compare", "hub-spoke": "hub_spoke",
                    "timeline": "timeline", "mechanism": "hub_spoke", "loop": "loop"}
        root = Path(__file__).parents[1] / "examples"
        for name, archetype in expected.items():
            with self.subTest(example=name):
                brief = json.loads((root / (name + ".json")).read_text(encoding="utf-8"))
                self.assertEqual(recommend(brief)[0], archetype)

    def test_all_archetypes_produce_in_bounds_nodes(self):
        root = Path(__file__).parents[1] / "examples"
        for path in root.glob("*.json"):
            brief = json.loads(path.read_text(encoding="utf-8"))
            report = audit(brief)
            self.assertEqual(report["errors"], [], path.name)
            self.assertEqual(len(brief["nodes"]), report["nodes"])

    def test_each_layout_archetype_places_nodes_inside_canvas(self):
        brief = json.loads(json.dumps(STARTER))
        brief["nodes"].append({"id": "extra", "label": "Additional evidence", "role": "evidence", "order": 4})
        brief["edges"].append({"from": "method", "to": "extra", "relation": "association"})
        for archetype in ("pipeline", "compare", "hub_spoke", "timeline", "mechanism", "loop"):
            with self.subTest(archetype=archetype):
                brief["archetype"] = archetype
                _, boxes = layout(brief)
                for box in boxes.values():
                    self.assertGreaterEqual(box["x"], 0)
                    self.assertGreaterEqual(box["y"], 0)
                    self.assertLessEqual(box["x"] + box["w"], brief["width"])
                    self.assertLessEqual(box["y"] + box["h"], brief["height"])

    def test_recommendation_is_explainable_and_override_is_separate(self):
        brief = dict(STARTER)
        choice, reasons = recommend(brief)
        self.assertEqual(choice, "pipeline")
        self.assertTrue(reasons)
        brief["archetype"] = "compare"
        self.assertEqual(brief["archetype"], "compare")

    def test_hub_recommendation_and_layout_use_the_same_center(self):
        brief = json.loads((Path(__file__).parents[1] / "examples" / "mechanism.json").read_text(encoding="utf-8"))
        recommended, _ = recommend(brief)
        self.assertEqual(recommended, "hub_spoke")
        brief["archetype"] = "hub_spoke"
        _, boxes = layout(brief)
        centers = {node_id: (box["x"] + box["w"] / 2, box["y"] + box["h"] / 2) for node_id, box in boxes.items()}
        self.assertEqual(centers["corrosion"], (600, sum(point[1] for point in centers.values()) / len(centers)))

    def test_invalid_edge_reference_fails(self):
        brief = json.loads(json.dumps(STARTER))
        brief["edges"][0]["to"] = "missing"
        with self.assertRaises(BriefError):
            validate_brief(brief)

    def test_self_edge_is_rejected(self):
        brief = json.loads(json.dumps(STARTER))
        brief["edges"][0]["to"] = brief["edges"][0]["from"]
        with self.assertRaises(BriefError):
            validate_brief(brief)

    def test_unhashable_enum_and_edge_values_produce_validation_errors(self):
        for field, value, section in (("role", [], "nodes"), ("review_status", {}, "nodes"),
                                      ("relation", [], "edges"), ("to", {}, "edges")):
            brief = json.loads(json.dumps(STARTER))
            brief[section][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(BriefError):
                validate_brief(brief)

    def test_non_finite_order_is_rejected(self):
        brief = json.loads(json.dumps(STARTER))
        brief["nodes"][0]["order"] = math.inf
        with self.assertRaises(BriefError):
            validate_brief(brief)

    def test_svg_has_editable_text_and_semantic_objects(self):
        svg = render_svg(STARTER)
        root = ET.fromstring(svg)
        ns = "{http://www.w3.org/2000/svg}"
        self.assertTrue(list(root.iter(ns + "text")))
        self.assertIsNotNone(root.find(".//*[@id='node-input']"))
        self.assertIsNotNone(root.find(".//*[@id='edges']"))

    def test_reference_style_renders_panels_and_a_wrapped_caption(self):
        brief = json.loads(json.dumps(STARTER))
        brief.update(style="reference", caption="A manuscript caption " * 30)
        for node, panel in zip(brief["nodes"], ("Background", "Method", "Results")):
            node["panel"] = panel
        root = ET.fromstring(render_svg(brief))
        ns = "{http://www.w3.org/2000/svg}"
        self.assertEqual(root.attrib["width"], "1400")
        self.assertEqual(len(root.findall(f".//{ns}rect[@fill='#315b9b']")), 3)
        self.assertGreater(len(root.findall(f".//{ns}rect[@stroke-dasharray]")), 2)
        caption = list(root.iter(ns + "text"))[-1]
        self.assertGreater(len(caption.findall(ns + "tspan")), 1)
        self.assertTrue(any(text.attrib.get("y") == "144.0" and "central contribution" in "".join(text.itertext())
                            for text in root.iter(ns + "text")))

    def test_reference_style_requires_panel_assignments(self):
        brief = json.loads(json.dumps(STARTER))
        brief["style"] = "reference"
        with self.assertRaises(BriefError):
            validate_brief(brief)

    def test_reference_style_customizes_or_hides_panel_descriptors_and_role_legend(self):
        brief = json.loads((Path(__file__).parents[1] / "examples" / "reference.json").read_text(encoding="utf-8"))
        panels = list(brief["panel_labels"])
        brief["panel_descriptors"] = {panels[0]: "Signal inputs", panels[1]: "", panels[2]: "", panels[3]: ""}
        brief["show_crossrefs"] = False
        for node in brief["nodes"]:
            node["role"] = "core"
        brief["legend_labels"] = {"blue": "Review-map modules"}
        root = ET.fromstring(render_svg(brief))
        rendered_text = " ".join("".join(element.itertext()) for element in root.iter("{http://www.w3.org/2000/svg}text"))
        self.assertIn("Signal inputs", rendered_text)
        self.assertIn("Review-map modules", rendered_text)
        self.assertNotIn("Source ingredients", rendered_text)
        self.assertNotIn("Incoming relationships", rendered_text)
        self.assertNotIn("See linked downstream panel", rendered_text)
        self.assertNotIn("Background / evidence", rendered_text)
        self.assertNotIn("Output / special case", rendered_text)
        self.assertEqual(rendered_text.count("Review-map modules"), 1)

    def test_reference_style_rejects_invalid_presentation_overrides(self):
        brief = json.loads((Path(__file__).parents[1] / "examples" / "reference.json").read_text(encoding="utf-8"))
        for field, value in (("panel_descriptors", {"inputs": 3}),
                             ("legend_labels", {"violet": "Unexpected role"}),
                             ("legend_labels", []), ("show_crossrefs", "false")):
            with self.subTest(field=field, value=value):
                candidate = json.loads(json.dumps(brief))
                candidate[field] = value
                with self.assertRaises(BriefError):
                    validate_brief(candidate)

    def test_long_reference_legend_wraps_inside_its_header_box(self):
        from paperfig.layout import _text_units

        brief = json.loads((Path(__file__).parents[1] / "examples/reference.json")
                           .read_text(encoding="utf-8"))
        brief["legend_labels"] = {"blue": "Construction and complementary evaluation"}
        root = ET.fromstring(render_svg(brief))
        legends = [element for element in root.iter("{http://www.w3.org/2000/svg}text")
                   if element.attrib.get("x") == "807.0"]
        self.assertTrue(legends)
        for element in legends:
            for span in element:
                self.assertLessEqual(_text_units(span.text or "")
                                     * float(element.attrib["font-size"]), 156)

    def test_reference_style_retains_undirected_relations_and_audits_its_own_geometry(self):
        brief = json.loads(json.dumps(STARTER))
        brief.update(style="reference", width=600, height=600)
        for node, panel in zip(brief["nodes"], ("Sources", "Method", "Results")):
            node["panel"] = panel
        brief["nodes"][1]["annotations"] = ["Source-backed condition"]
        brief["edges"][0].update(relation="association", source="Section 2", review_status="needs_review")
        root = ET.fromstring(render_svg(brief))
        edge = root.find(".//*[@id='edge-0']")
        self.assertNotIn("marker-end", edge.attrib)
        self.assertEqual(edge.attrib["data-source"], "Section 2")
        self.assertEqual(edge.attrib["data-review-status"], "needs_review")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "reference.svg"
            path.write_text(render_svg(brief), encoding="utf-8")
            report = audit(brief, path)
        self.assertEqual(report["archetype"], "reference")
        self.assertEqual(report["errors"], [])
        self.assertTrue(any("review" in warning for warning in report["warnings"]))

    def test_annotation_contract_rejects_nontext_and_excess_tags(self):
        for annotations in ([123], ["a", "b", "c"], "text", [""]):
            brief = json.loads(json.dumps(STARTER))
            brief["nodes"][0]["annotations"] = annotations
            with self.assertRaises(BriefError):
                validate_brief(brief)

    def test_arrows_stop_before_the_target_box_and_have_explicit_markers(self):
        brief = json.loads(json.dumps(STARTER))
        root = ET.fromstring(render_svg(brief))
        path = root.find(".//*[@id='edge-0']")
        self.assertIsNotNone(path)
        self.assertEqual(path.attrib["marker-end"], "url(#arrow-sequence)")
        coords = [float(number) for number in re.findall(r"-?\d+(?:\.\d+)?", path.attrib["d"])]
        _, boxes = layout(brief)
        source = boxes[brief["edges"][0]["from"]]
        target = boxes[brief["edges"][0]["to"]]
        self.assertGreater(coords[0], source["x"])
        self.assertLess(coords[2], target["x"])
        self.assertEqual(path.attrib["data-review-status"], "needs_review")

    def test_contrast_is_not_rendered_as_a_directed_claim(self):
        brief = json.loads(json.dumps(STARTER))
        brief["edges"][0]["relation"] = "contrast"
        root = ET.fromstring(render_svg(brief))
        path = root.find(".//*[@id='edge-0']")
        self.assertNotIn("marker-end", path.attrib)

    def test_proof_dependency_and_specialization_remain_distinct_directed_relations(self):
        for relation, dash in (("proof_dependency", "2 5"), ("specialization", "7 5")):
            brief = json.loads(json.dumps(STARTER))
            brief["edges"][0]["relation"] = relation
            root = ET.fromstring(render_svg(brief))
            path = root.find(".//*[@id='edge-0']")
            self.assertEqual(path.attrib["data-relation"], relation)
            self.assertEqual(path.attrib["stroke-dasharray"], dash)
            self.assertIn("marker-end", path.attrib)
        self.assertNotEqual(recommend({**STARTER, "edges": [dict(STARTER["edges"][0], relation="proof_dependency")]})[0], "pipeline")

    def test_long_header_is_wrapped_and_graph_is_below_it(self):
        brief = json.loads(json.dumps(STARTER))
        brief["title"] = "A substantially longer research framework title that needs two lines in a manuscript figure"
        brief["claim"] = "A " + "supported scientific claim " * 12
        root = ET.fromstring(render_svg(brief))
        ns = "{http://www.w3.org/2000/svg}"
        self.assertGreater(len(root.find(".//*[@id='header']").findall(ns + "text")), 2)
        _, boxes = layout(brief)
        self.assertGreaterEqual(min(box["y"] for box in boxes.values()), 130)

    def test_qa_surfaces_unreviewed_causality(self):
        brief = json.loads(json.dumps(STARTER))
        brief["edges"][0].update({"relation": "causal", "review_status": "needs_review"})
        report = audit(brief)
        self.assertTrue(any("causal" in warning.lower() for warning in report["warnings"]))

    def test_external_draft_requires_explicit_sharing_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            text = Path(temp) / "excerpt.txt"
            text.write_text("An unpublished excerpt", encoding="utf-8")
            result = main(["draft", str(text), "--model", "model-x"])
            self.assertEqual(result, 2)

    def test_external_extractor_forces_review_status(self):
        proposed = json.loads(json.dumps(STARTER))
        proposed["style"] = "reference"
        proposed["panel_labels"] = {"inputs": "Inputs", "results": "Results"}
        proposed["nodes"][0]["panel"] = "inputs"
        proposed["nodes"][1]["panel"] = "results"
        proposed["nodes"][2]["panel"] = "results"
        proposed["edges"][0]["review_status"] = "confirmed"
        response = {"choices": [{"message": {"content": json.dumps(proposed)}}]}
        for language in ("en", "zh"):
            with self.subTest(language=language):
                with patch("paperfig.extract.urllib.request.urlopen",
                           return_value=BytesIO(json.dumps(response).encode())) as endpoint:
                    draft = draft_from_text("Synthetic test", api_key="test", model="test-model",
                                            base_url="http://localhost:1234/v1", language=language)
                payload = json.loads(endpoint.call_args.args[0].data.decode("utf-8"))
                self.assertIn(f"requested figure language: {language}", payload["messages"][1]["content"].lower())
                self.assertIn("English for all reader-facing text", payload["messages"][0]["content"])
                self.assertEqual(draft["language"], language)
                self.assertEqual(draft["style"], "reference")
                self.assertEqual(draft["review_status"], "needs_review")
                self.assertTrue(all(node["review_status"] == "needs_review" for node in draft["nodes"]))
                self.assertTrue(all(edge["review_status"] == "needs_review" for edge in draft["edges"]))

    def test_default_style_prompt_keeps_evidence_contract_without_panel_requirements(self):
        response = {"choices": [{"message": {"content": json.dumps(STARTER)}}]}
        with patch("paperfig.extract.urllib.request.urlopen",
                   return_value=BytesIO(json.dumps(response).encode())) as endpoint:
            draft = draft_from_text("Synthetic source", api_key="test", model="test",
                                    base_url="http://localhost:1234/v1", style="default")
        prompt = json.loads(endpoint.call_args.args[0].data.decode("utf-8"))["messages"][0]["content"]
        self.assertEqual(draft["language"], "en")
        self.assertEqual(draft["style"], "default")
        self.assertIn('"style":"default"', prompt)
        self.assertIn("Do not add panel groups", prompt)
        for leftover in ('panel_labels', '"panel":', '2-4-panel', '2-4 panels', 'style=reference'):
            self.assertNotIn(leftover, prompt)
        for requirement in ("specific contribution", "source section/page/equation anchor",
                            "proof_dependency", "specialization", "scope boundary"):
            self.assertIn(requirement, prompt)

    def test_draft_rejects_unsupported_language_and_style_without_network(self):
        for field, value in (("language", "fr"), ("style", "bitmap")):
            with self.subTest(field=field), patch("paperfig.extract.urllib.request.urlopen") as endpoint:
                with self.assertRaises(BriefError):
                    draft_from_text("Synthetic", api_key="test", model="test",
                                    base_url="http://localhost:1234/v1", **{field: value})
                endpoint.assert_not_called()

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            brief = Path(temp) / "brief.json"
            svg = Path(temp) / "figure.svg"
            brief.write_text(json.dumps(STARTER), encoding="utf-8")
            self.assertEqual(main(["validate", str(brief)]), 0)
            self.assertEqual(main(["render", str(brief), "--output", str(svg)]), 0)
            self.assertTrue(svg.exists())
            self.assertEqual(main(["qa", str(brief), "--svg", str(svg)]), 0)

    def test_batch_continues_after_bad_input_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "inputs"
            output = Path(temp) / "output"
            directory.mkdir()
            (directory / "good.json").write_text(json.dumps(STARTER), encoding="utf-8")
            (directory / "bad.json").write_text('{"nodes": []}', encoding="utf-8")
            self.assertEqual(main(["batch", str(directory), "-o", str(output)]), 1)
            self.assertTrue((output / "good.svg").exists())
            self.assertTrue((output / "good.qa.json").exists())
            summary = json.loads((output / "batch-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(len(summary), 2)
            self.assertTrue(summary[0]["errors"])

    def test_batch_optional_exports_from_one_svg(self):
        try:
            import cairosvg  # noqa: F401
        except ImportError:
            self.skipTest("Optional CairoSVG Python package is not installed.")
        except OSError as exc:
            # Windows can have cairosvg installed without the native Cairo DLL.
            if "cairo" not in str(exc).lower():
                raise
            self.skipTest("Optional Cairo native library could not be loaded.")
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "inputs"
            output = Path(temp) / "output"
            directory.mkdir()
            (directory / "one.json").write_text(json.dumps(STARTER), encoding="utf-8")
            self.assertEqual(main(["batch", str(directory), "-o", str(output), "--png", "--pdf"]), 0)
            self.assertTrue((output / "one.png").exists())
            self.assertTrue((output / "one.pdf").exists())

    def test_model_malformed_nodes_are_rejected_without_typeerror(self):
        proposed = json.loads(json.dumps(STARTER))
        proposed["nodes"] = None
        response = {"choices": [{"message": {"content": json.dumps(proposed)}}]}
        with patch("paperfig.extract.urllib.request.urlopen", return_value=BytesIO(json.dumps(response).encode())):
            with self.assertRaises(BriefError):
                draft_from_text("Synthetic", api_key="test", model="test", base_url="http://localhost:1234/v1")


if __name__ == "__main__":
    unittest.main()
