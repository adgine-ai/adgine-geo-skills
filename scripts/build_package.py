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

EXCLUDE_DIRS = {".git", "dist", "__pycache__", ".github", ".idea", ".vscode", "ref"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDE_FILES = {".gitignore", "scripts/build_package.py" ,"VERSION"}


def build_archive(output_path: Path, root: Path) -> None:
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(root.rglob("*")):
            if not item.is_file():
                continue
            rel = item.relative_to(root)
            parts = rel.parts
            if any(p in EXCLUDE_DIRS for p in parts):
                continue
            if item.suffix in EXCLUDE_SUFFIXES:
                continue
            if str(rel) in EXCLUDE_FILES:
                continue
            if item.name == ".gitignore":
                continue
            zf.write(item, rel)


def main():
    parser = argparse.ArgumentParser(description="Build adgine-geo skills package")
    parser.add_argument("--output", default="dist", help="Output directory (default: dist/)")
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    version = (root / "VERSION").read_text().strip()
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    base = f"adgine-geo-v{version}"
    for ext in (".skill", ".zip"):
        out = output_dir / f"{base}{ext}"
        build_archive(out, root)
        size_kb = out.stat().st_size // 1024
        print(f"Built: {out}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
