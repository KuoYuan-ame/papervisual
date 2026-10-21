"""Synchronize a portable skill from maintained sources and optionally zip it.

Only an explicit set of public resources is copied. User manuscripts, work
directories, caches and conversation images are never packaging inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "papervisual"


def expected_files() -> dict[str, bytes]:
    files = {}
    for name in ("reference-style.zh-CN.md", "agent-workflow.zh-CN.md", "figure-ir.md", "scientific-qa.md"):
        data = (ROOT / "docs" / name).read_text(encoding="utf-8")
        data = data.replace("examples/reference.json", "../assets/reference.json")
        data = data.replace("schemas/figure-ir.schema.json", "figure-ir.schema.json")
        files[f"references/{name}"] = data.encode("utf-8")
    files["references/figure-ir.schema.json"] = (ROOT / "schemas/figure-ir.schema.json").read_bytes()
    for path in sorted((ROOT / "src/paperfig").glob("*.py")):
        files[f"scripts/runtime/paperfig/{path.name}"] = path.read_bytes()
    for src, dest in (
        ("examples/reference.json", "assets/reference.json"),
        ("examples/rendered/reference.svg", "assets/reference.svg"),
        ("examples/rendered/reference.png", "assets/reference.png"),
        ("examples/theory/brief.json", "assets/theory.json"),
        ("examples/rendered/theory.svg", "assets/theory.svg"),
        ("examples/rendered/theory.png", "assets/theory.png"),
        ("LICENSE", "LICENSE"),
    ):
        files[dest] = (ROOT / src).read_bytes()
    return files


def bundle(check: bool, archive: Path | None) -> None:
    files = expected_files()
    # Entrypoint and wrapper are maintained directly, not generated copies.
    for name in ("SKILL.md", "scripts/papervisual.py", "scripts/paperfig.py", "scripts/self_check.py",
                 "references/portable-test.zh-CN.md"):
        files[name] = (SKILL / name).read_bytes()
    manifest = {
        "format": 1,
        "renderer_version": "0.1.0",
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    files["bundle-manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    actual = {p.relative_to(SKILL).as_posix() for p in SKILL.rglob("*")
              if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    unexpected = actual - files.keys()
    if unexpected:
        raise SystemExit(f"Unexpected skill files; review before packaging: {sorted(unexpected)}")
    if check:
        stale = [name for name, data in files.items()
                 if not (SKILL / name).is_file() or (SKILL / name).read_bytes() != data]
        if stale:
            raise SystemExit(f"Stale skill resources; run tools/bundle_skill.py: {stale}")
    else:
        for name, data in files.items():
            path = SKILL / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if archive:
        archive.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as output:
            for name, data in sorted(files.items()):
                info = ZipInfo("papervisual/" + name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                output.writestr(info, data)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix(archive.suffix + ".sha256").write_text(
            f"{digest}  {archive.name}\n", encoding="utf-8")
        print(f"Archive: {archive.name}; SHA256: {digest}")
    print(f"{'Verified' if check else 'Bundled'} {len(files)} portable skill files.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on unsynchronized resources")
    parser.add_argument("--zip", type=Path, dest="archive", help="also build a deterministic ZIP")
    args = parser.parse_args()
    bundle(args.check, args.archive)


if __name__ == "__main__":
    main()
