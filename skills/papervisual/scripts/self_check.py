"""Offline release checks for a portable skill; never certify visual QA."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


SKILL = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest() -> dict:
    """Check completeness and hashes before executing bundled code."""
    errors = []
    try:
        manifest_path = SKILL / "bundle-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = manifest["files"]
        if manifest.get("format") != 1 or not isinstance(files, dict) or not files:
            raise ValueError("Unsupported or empty manifest.")
        for name, digest in files.items():
            target = (SKILL / name).resolve()
            if not target.is_relative_to(SKILL.resolve()) or not target.is_file():
                errors.append(f"Missing or invalid manifest path: {name}")
            elif sha256(target) != digest:
                errors.append(f"Hash mismatch: {name}")
        actual = {p.relative_to(SKILL).as_posix() for p in SKILL.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
        for name in sorted(actual - files.keys() - {"bundle-manifest.json"}):
            errors.append(f"Unlisted skill file: {name}")
        return {"status": "failed" if errors else "passed", "errors": errors,
                "files": len(files), "manifest_sha256": sha256(manifest_path)}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"status": "failed", "errors": [str(exc)]}


def python_command() -> list[str]:
    # Preserve a caller's dependency-free (-S) run in child processes.
    return [sys.executable, "-I", "-X", "utf8"] + (["-S"] if sys.flags.no_site else [])


def raster_dependencies() -> dict:
    probe = (
        "import json\n"
        "try:\n"
        " import cairosvg\n"
        " from cairocffi import cairo_version_string\n"
        " print(json.dumps({'available': True, 'cairosvg': cairosvg.__version__, "
        "'cairo': cairo_version_string()}))\n"
        "except Exception as exc:\n"
        " print(json.dumps({'available': False, 'reason': type(exc).__name__ + ': ' + str(exc)}))\n"
    )
    result = subprocess.run(python_command() + ["-c", probe], capture_output=True,
                            text=True, encoding="utf-8")
    if result.returncode:
        return {"available": False, "reason": result.stderr.strip() or "Dependency probe failed."}
    try:
        return json.loads(result.stdout)
    except ValueError:
        return {"available": False, "reason": "Dependency probe returned invalid JSON."}


def run_checks(brief: Path, output: Path, require_raster: bool, release=False, require_confirmed=False, rendered=False) -> int:
    report = {
        "automated_status": "failed",
        "visual_qa": {
            "status": "not_completed",
            "reason": "This command does not inspect images or certify a viewer session.",
            "next_step": "Inspect PNG/PDF if exported, otherwise SVG in an available viewer, "
                         "at final dimensions. If no viewer is available, report visual QA incomplete.",
        },
        "dependencies": {"python": sys.version.split()[0], "python_supported": sys.version_info >= (3, 10)},
        "brief": str(brief), "steps": [], "errors": [],
    }
    report["manifest_before"] = verify_manifest()
    if report["manifest_before"]["status"] != "passed":
        report["errors"].append("Manifest validation failed; bundled CLI was not executed.")
    elif not report["dependencies"]["python_supported"]:
        report["errors"].append("Python 3.10+ is required.")
    else:
        raster = raster_dependencies()
        report["dependencies"]["raster"] = raster
        report["exports"] = {"svg": "pending", "png": "pending" if raster["available"] else "skipped",
                             "pdf": "pending" if raster["available"] else "skipped"}
        if require_raster and not raster["available"]:
            report["errors"].append("PNG/PDF dependencies are required but unavailable.")
        prefix = python_command() + [str(SKILL / "scripts/papervisual.py")]
        render = ["render", str(brief), "-o", str(output / "figure.svg")]
        if raster["available"]:
            render += ["--png", str(output / "figure.png"), "--pdf", str(output / "figure.pdf")]
        qa_flags = (["--release"] if release else []) + (["--require-confirmed"] if require_confirmed else []) + (["--rendered"] if rendered else [])
        commands = [
            ("doctor", ["doctor", "--output", str(output / "doctor.json")]),
            ("suggest", ["suggest", str(brief)]),
            ("validate", ["validate", str(brief)] + (["--release"] if release else [])),
            ("render", render),
            ("qa", ["qa", str(brief), "--svg", str(output / "figure.svg"),
                    "--output", str(output / "figure.qa.json")] + qa_flags),
            ("repeat_render", ["render", str(brief), "-o", str(output / "figure.repeat.svg")]),
        ]
        for name, args in commands:
            result = subprocess.run(prefix + args, cwd=output, capture_output=True,
                                    text=True, encoding="utf-8")
            report["steps"].append({"name": name, "returncode": result.returncode,
                                    "stdout": result.stdout, "stderr": result.stderr})
            if result.returncode:
                report["errors"].append(f"CLI step failed: {name}")
                break
        if len(report["steps"]) == 6 and not report["steps"][-1]["returncode"]:
            first = sha256(output / "figure.svg")
            second = sha256(output / "figure.repeat.svg")
            report["repeat_svg"] = {"sha256": first, "repeat_sha256": second,
                                    "identical": first == second}
            if first != second:
                report["errors"].append("Repeated SVG hashes differ.")
        if (output / 'figure.qa.json').is_file():
            qa = json.loads((output / "figure.qa.json").read_text(encoding="utf-8"))
            report["qa"] = {"errors": qa["errors"], "warnings": qa["warnings"], "checks": qa["checks"]}
            report["errors"].extend(qa["errors"])
        for extension in ("svg", "png", "pdf"):
            path = output / f"figure.{extension}"
            if path.is_file():
                data = path.read_bytes()
                valid = ((extension == "svg" and b"<svg" in data)
                         or (extension == "png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
                         or (extension == "pdf" and data.startswith(b"%PDF-")))
                report["exports"][extension] = "passed" if valid else "failed"
                if not valid:
                    report["errors"].append(f"Invalid {extension.upper()} file signature.")
            elif report["exports"][extension] != "skipped":
                report["exports"][extension] = "failed"
                report["errors"].append(f"Missing {extension.upper()} export.")
        report["manifest_after"] = verify_manifest()
        if (report["manifest_after"]["status"] != "passed"
                or report["manifest_after"].get("manifest_sha256")
                != report["manifest_before"].get("manifest_sha256")):
            report["errors"].append("Bundle changed during the check.")
    if not report["errors"]:
        report["automated_status"] = "passed"
    target = output / "self-check.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Automated checks: {report['automated_status']}. Visual QA: NOT COMPLETED.")
    print(f"Report: {target}")
    return 0 if report["automated_status"] == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief", type=Path, default=SKILL / "assets/reference.json")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="new or empty output folder outside the skill")
    parser.add_argument("--require-raster", action="store_true",
                        help="fail automated checks if PNG/PDF dependencies are unavailable")
    parser.add_argument("--release", action="store_true", help="block missing sources and rendering findings")
    parser.add_argument("--require-confirmed", action="store_true", help="require declared author confirmation separately")
    parser.add_argument("--rendered", action="store_true", help="require measured glyph/text checks (audit extra)")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.is_relative_to(SKILL.resolve()):
        parser.error("Output must be outside the frozen skill folder.")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error("Output folder must be new or empty to avoid mixing runs.")
    output.mkdir(parents=True, exist_ok=True)
    return run_checks(args.brief.resolve(), output, args.require_raster,
                      args.release, args.require_confirmed, args.rendered)


if __name__ == "__main__":
    raise SystemExit(main())
