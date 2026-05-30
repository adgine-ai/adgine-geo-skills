#!/usr/bin/env python3
"""Export this skill directory as a portable zip package."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TOP_LEVEL_FILES = (
    "SKILL.md",
    "README.md",
    "requirements.txt",
    ".gitignore",
)

DEFAULT_SOURCE_DIRS = (
    "scripts",
    "tests",
)

EXCLUDED_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "htmlcov",
}

EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    ".coverage",
    "coverage.xml",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".zip",
    ".log",
}


@dataclass(frozen=True)
class PackageFile:
    source: Path
    archive_name: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_skill_name(root: Path) -> str:
    skill_md = root / "SKILL.md"
    if not skill_md.exists():
        return root.name
    text = skill_md.read_text(encoding="utf-8")
    match = re.search(r"^name:\s*([A-Za-z0-9_.-]+)\s*$", text, re.MULTILINE)
    return match.group(1) if match else root.name


def should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDED_DIR_NAMES for part in rel.parts[:-1]):
        return True
    if path.is_dir():
        return path.name in EXCLUDED_DIR_NAMES
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    return False


def collect_files(root: Path, *, include_tests: bool) -> list[Path]:
    files: list[Path] = []
    for file_name in DEFAULT_TOP_LEVEL_FILES:
        path = root / file_name
        if path.is_file() and not should_skip(path, root):
            files.append(path)

    source_dirs = list(DEFAULT_SOURCE_DIRS)
    if not include_tests:
        source_dirs.remove("tests")

    for dir_name in source_dirs:
        directory = root / dir_name
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file() and not should_skip(path, root):
                files.append(path)
    return sorted(dict.fromkeys(files), key=lambda item: item.relative_to(root).as_posix())


def build_package_files(root: Path, *, package_root: str, include_tests: bool) -> list[PackageFile]:
    package_files: list[PackageFile] = []
    for source in collect_files(root, include_tests=include_tests):
        rel = source.relative_to(root).as_posix()
        package_files.append(PackageFile(source=source, archive_name=f"{package_root}/{rel}"))
    return package_files


def resolve_output_path(root: Path, skill_name: str, output: str | None) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return (root / "dist" / f"{skill_name}-{timestamp}.zip").resolve()


def write_manifest(zip_handle: zipfile.ZipFile, *, package_root: str, skill_name: str, files: list[PackageFile]) -> None:
    manifest = {
        "name": skill_name,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file_count": len(files),
        "files": [item.archive_name for item in files],
    }
    zip_handle.writestr(
        f"{package_root}/PACKAGE_MANIFEST.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )


def write_zip(output_path: Path, files: list[PackageFile], *, package_root: str, skill_name: str, include_manifest: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zip_handle:
        for item in files:
            zip_handle.write(item.source, item.archive_name)
        if include_manifest:
            write_manifest(zip_handle, package_root=package_root, skill_name=skill_name, files=files)


def main(argv: list[str] | None = None) -> int:
    root = project_root()
    skill_name = read_skill_name(root)

    parser = argparse.ArgumentParser(description="Export the current GEO audit skill as a zip package.")
    parser.add_argument("--output", "-o", help="Output zip path. Defaults to dist/<skill-name>-<timestamp>.zip")
    parser.add_argument("--package-root", default=skill_name, help="Top-level directory name inside the zip")
    parser.add_argument("--no-tests", action="store_true", help="Exclude tests/ from the package")
    parser.add_argument("--no-manifest", action="store_true", help="Do not add PACKAGE_MANIFEST.json to the zip")
    parser.add_argument("--json", action="store_true", help="Print result metadata as JSON")
    args = parser.parse_args(argv)

    package_root = args.package_root.strip().strip("/")
    if not package_root or ".." in Path(package_root).parts:
        print("ERROR: --package-root must be a safe relative directory name", file=sys.stderr)
        return 2

    files = build_package_files(root, package_root=package_root, include_tests=not args.no_tests)
    if not files:
        print("ERROR: no files found to package", file=sys.stderr)
        return 3

    output_path = resolve_output_path(root, skill_name, args.output)
    write_zip(
        output_path,
        files,
        package_root=package_root,
        skill_name=skill_name,
        include_manifest=not args.no_manifest,
    )

    payload = {
        "output": str(output_path),
        "skill_name": skill_name,
        "package_root": package_root,
        "file_count": len(files) + (0 if args.no_manifest else 1),
        "size_bytes": output_path.stat().st_size,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Package written to {output_path}")
        print(f"Files: {payload['file_count']}, size: {payload['size_bytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
