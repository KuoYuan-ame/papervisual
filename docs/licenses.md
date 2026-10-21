# Code, examples and optional dependencies

Project source code, schemas, documentation, synthetic briefs and original SVG shapes are released under the root MIT License. The synthetic examples are software demonstrations, not data from real studies. No reference screenshot, copied paper figure, manuscript, logo, external icon, or font file is bundled.

SVG declares common system font families and uses fonts installed on the rendering system. Font availability can change wrapping and glyph appearance; inspect the output on the target platform.

Core runtime code uses only Python's standard library. The optional raster extra installs CairoSVG, which brings its own dependencies and license terms; these are separate upstream packages, not relicensed by this repository. Build and CI tools (setuptools, build, jsonschema, ruff) are development dependencies. Check each installed distribution's metadata for the version and applicable upstream license.
