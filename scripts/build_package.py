#!/usr/bin/env python3
"""
Build adgine-geo-skills suite package (.skill file) for platform distribution.

Usage:
    python3 scripts/build_package.py [--output dist/]

Output:
    dist/adgine-geo-v{VERSION}.skill  (zip archive with .skill extension)
"""

import argparse
import zipfile
from pathlib import Path

EXCLUDE_DIRS = {".git", "dist", "__pycache__", ".github", ".idea", ".vscode"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def build(output_dir: Path, root: Path, version: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_path = output_dir / f"adgine-geo-v{version}.skill"

    with zipfile.ZipFile(skill_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(root.rglob("*")):
            if not item.is_file():
                continue
            rel = item.relative_to(root)
            parts = rel.parts
            if any(p in EXCLUDE_DIRS for p in parts):
                continue
            if item.suffix in EXCLUDE_SUFFIXES:
                continue
            zf.write(item, rel)

    return skill_path


def main():
    parser = argparse.ArgumentParser(description="Build adgine-geo skills package")
    parser.add_argument("--output", default="dist", help="Output directory (default: dist/)")
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    version = (root / "VERSION").read_text().strip()
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = root / output_dir

    skill_path = build(output_dir, root, version)
    size_kb = skill_path.stat().st_size // 1024
    print(f"Built: {skill_path}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
