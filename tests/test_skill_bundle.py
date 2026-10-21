"""The published skill must work outside the repository without installation."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/papervisual"


class PortableSkillTests(unittest.TestCase):
    def run_self_check(self, destination, output, *args):
        return subprocess.run(
            [sys.executable, "-I", "-S", "-X", "utf8",
             str(destination / "scripts/self_check.py"), "--output-dir", str(output), *args],
            cwd=output.parent, capture_output=True, text=True, encoding="utf-8")

    def copy_skill(self, temp):
        destination = Path(temp) / "copied-skill"
        shutil.copytree(SKILL, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        return destination

    def test_self_check_without_cairo_runs_four_steps_and_never_certifies_visuals(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = self.copy_skill(temp)
            output = Path(temp) / "check"
            result = self.run_self_check(destination, output)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads((output / "self-check.json").read_text(encoding="utf-8"))
            self.assertEqual(report["automated_status"], "passed")
            self.assertFalse(report["dependencies"]["raster"]["available"])
            self.assertEqual(report["exports"], {"svg": "passed", "png": "skipped", "pdf": "skipped"})
            self.assertEqual(report["visual_qa"]["status"], "not_completed")
            self.assertEqual([step["name"] for step in report["steps"]],
                             ["doctor", "suggest", "validate", "render", "qa", "repeat_render"])
            for name in ("manifest_before", "manifest_after"):
                self.assertEqual(report[name]["status"], "passed")
            self.assertTrue(report["repeat_svg"]["identical"])
            self.assertEqual(report["repeat_svg"]["sha256"],
                             hashlib.sha256((output / "figure.svg").read_bytes()).hexdigest())
            first_report = (output / "self-check.json").read_bytes()
            repeated = self.run_self_check(destination, output)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual((output / "self-check.json").read_bytes(), first_report)

    def test_required_raster_cannot_succeed_when_dependency_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = self.copy_skill(temp)
            output = Path(temp) / "check"
            result = self.run_self_check(destination, output, "--require-raster")
            self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
            report = json.loads((output / "self-check.json").read_text(encoding="utf-8"))
            self.assertEqual(report["automated_status"], "failed")
            self.assertEqual(report["visual_qa"]["status"], "not_completed")
            self.assertTrue(report["errors"])
            self.assertTrue(report["repeat_svg"]["identical"])

    def test_tampered_bundle_stops_before_executing_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = self.copy_skill(temp)
            (destination / "scripts/runtime/paperfig/cli.py").write_text(
                "raise RuntimeError('This code must not execute.')\n", encoding="utf-8")
            output = Path(temp) / "check"
            result = self.run_self_check(destination, output)
            self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
            report = json.loads((output / "self-check.json").read_text(encoding="utf-8"))
            self.assertEqual(report["manifest_before"]["status"], "failed")
            self.assertEqual(report["steps"], [])
            self.assertFalse((output / "figure.svg").exists())

    def test_invalid_brief_records_cli_failure_instead_of_automated_success(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = self.copy_skill(temp)
            brief = Path(temp) / "invalid.json"
            brief.write_text('{"nodes": []}', encoding="utf-8")
            output = Path(temp) / "check"
            result = self.run_self_check(destination, output, "--brief", str(brief))
            self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
            report = json.loads((output / "self-check.json").read_text(encoding="utf-8"))
            self.assertEqual(report["automated_status"], "failed")
            self.assertNotEqual(report["steps"][-1]["returncode"], 0)
            self.assertEqual(report["visual_qa"]["status"], "not_completed")

    def test_manifest_and_local_document_links(self):
        manifest = json.loads((SKILL / "bundle-manifest.json").read_text(encoding="utf-8"))
        for name, digest in manifest["files"].items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((SKILL / name).read_bytes()).hexdigest(), digest)
        for path in SKILL.rglob("*.md"):
            for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if "://" not in link and not link.startswith("#"):
                    target = (path.parent / link.split("#")[0]).resolve()
                    self.assertTrue(target.is_relative_to(SKILL.resolve()), str(target))
                    self.assertTrue(target.exists(), str(target))

    def test_reference_bbox_metadata_matches_rendered_geometry(self):
        """Avoid platform-dependent float repr in serialized SVG metadata."""
        root = ET.fromstring((SKILL / "assets/reference.svg").read_text(encoding="utf-8"))
        namespaced = "{http://www.w3.org/2000/svg}"
        label_groups = [item for item in root.iter()
                        if item.tag == namespaced + "g"
                        and item.get("id", "").startswith("edge-label-")]
        self.assertGreater(len(label_groups), 0)
        for item in label_groups:
            bbox = item.get("data-bbox")
            self.assertRegex(bbox, r"^-?\d+\.\d{2}(,-?\d+\.\d{2}){3}$")
            rect = item.find(namespaced + "rect")
            self.assertIsNotNone(rect)
            self.assertEqual([float(piece) for piece in bbox.split(",")],
                             [float(rect.get(key)) for key in ("x", "y", "width", "height")])

    def test_isolated_copy_renders_without_repository_imports(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "installed-skill"
            shutil.copytree(SKILL, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            wrapper = destination / "scripts/papervisual.py"
            brief = destination / "assets/reference.json"
            svg = Path(temp) / "figure.svg"
            prefix = [sys.executable, "-I", str(wrapper)]
            for args in (["validate", str(brief)], ["render", str(brief), "-o", str(svg)],
                         ["qa", str(brief), "--svg", str(svg)]):
                result = subprocess.run(prefix + args, cwd=temp, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(svg.read_text(encoding="utf-8"),
                             (destination / "assets/reference.svg").read_text(encoding="utf-8"))
            probe = ("import runpy, sys; runpy.run_path(sys.argv[1]); "
                     "import paperfig; print(paperfig.__file__)")
            result = subprocess.run([sys.executable, "-I", "-c", probe, str(wrapper)],
                                    cwd=temp, capture_output=True, text=True, check=True)
            # macOS may report /private/var/... while TemporaryDirectory uses /var/...;
            # Windows can also have equivalent, lexically different path spellings.
            loaded_module = Path(result.stdout.strip()).resolve()
            installed_root = destination.resolve()
            self.assertTrue(loaded_module.is_relative_to(installed_root),
                            f"Imported {loaded_module}, outside {installed_root}")
            # Earlier releases offered paperfig.py; preserve direct portable usage.
            alias_result = subprocess.run(
                [sys.executable, "-I", str(destination / "scripts/paperfig.py"),
                 "validate", str(brief)],
                cwd=temp, capture_output=True, text=True)
            self.assertEqual(alias_result.returncode, 0, alias_result.stderr + alias_result.stdout)


if __name__ == "__main__":
    unittest.main()
