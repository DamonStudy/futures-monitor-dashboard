#!/usr/bin/env python3
"""Parse broker PDF reports into markdown cache for playbook maintenance."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "期货研报" / "期货基本面"
DEFAULT_OUTPUT = ROOT / "data" / "research" / "parsed"
SUPPORTED_SUFFIXES = {".pdf", ".html", ".htm", ".docx", ".doc", ".txt", ".md"}


def parse_file(source: Path, output: Path) -> bool:
    output.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".md":
        output.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return True
    try:
        result = subprocess.run(
            ["xparse-cli", "parse", str(source)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("xparse-cli not found; install from xparse-parse skill docs.", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as exc:
        print(f"failed: {source.name}\n{exc.stderr}", file=sys.stderr)
        return False

    text = result.stdout or ""
    if not text.strip():
        print(f"empty output: {source.name}", file=sys.stderr)
        return False
    output.write_text(text, encoding="utf-8")
    return True


def collect_sources(source_dir: Path) -> list[Path]:
    files: list[Path] = []
    for suffix in SUPPORTED_SUFFIXES:
        files.extend(source_dir.glob(f"*{suffix}"))
        files.extend(source_dir.glob(f"*{suffix.upper()}"))
    return sorted({path.resolve() for path in files})


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse futures research files to markdown.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true", help="Re-parse even if markdown exists.")
    args = parser.parse_args()

    if not args.source.is_dir():
        print(f"source directory not found: {args.source}", file=sys.stderr)
        return 1

    sources = collect_sources(args.source)
    if not sources:
        print(f"no supported files in {args.source}")
        return 0

    ok = 0
    for source in sources:
        target = args.output / f"{source.stem}.md"
        if target.exists() and target.stat().st_size > 100 and not args.force:
            print(f"skip {source.name}")
            ok += 1
            continue
        print(f"parse {source.name} ...")
        if parse_file(source, target):
            ok += 1

    print(f"done: {ok}/{len(sources)}")
    return 0 if ok == len(sources) else 2


if __name__ == "__main__":
    raise SystemExit(main())
