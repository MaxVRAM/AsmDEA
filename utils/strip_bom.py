#!/usr/bin/env python3
"""Strip UTF-8 BOMs from text files under the configured project root.

Standalone utility — runs independently of the main asmdea CLI. Loads the
target project path from ``.env`` (``ROOT_PATH``) and rewrites any matching
files that begin with the UTF-8 BOM (``ef bb bf``) so they conform to the
``charset = utf-8`` (BOM-less) convention.

Defaults to a dry-run so it can be inspected before writing. Pass ``--apply``
to actually rewrite files. ``FILTER_PATH`` from ``.env`` is honoured so the
same excluded subtrees (e.g. ``Library/PackageCache``, third-party folders)
are skipped.

Usage:
    python strip_bom.py                          # dry-run, .cs files
    python strip_bom.py --apply                  # rewrite .cs files
    python strip_bom.py --apply --ext .cs .json  # multiple extensions
    python strip_bom.py --path D:/Other/Project  # override ROOT_PATH
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from common import configure_console, get_console

BOM = b"\xef\xbb\xbf"
DEFAULT_EXTENSIONS = (".cs",)


def get_env_list(key: str) -> list[str]:
    """Parse a comma-separated env variable into a list of stripped strings."""
    value = os.environ.get(key, "")
    return [s.strip() for s in value.split(",") if s.strip()]


def is_excluded(path: Path, root: Path, filter_segments: list[str]) -> bool:
    """Return True if ``path`` falls under any excluded segment.

    Matches the semantics used by the rest of the project: a segment matches
    anywhere in the relative path (e.g. ``Library/PackageCache``,
    ``ThirdParty``).
    """
    if not filter_segments:
        return False
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    return any(seg and seg in rel for seg in filter_segments)


def file_starts_with_bom(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(3) == BOM
    except OSError:
        return False


def strip_bom(path: Path) -> bool:
    """Rewrite ``path`` without its leading BOM. Returns True on success."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return False
    if not data.startswith(BOM):
        return False
    try:
        with open(path, "wb") as f:
            f.write(data[len(BOM) :])
    except OSError:
        return False
    return True


def iter_target_files(
    root: Path,
    extensions: tuple[str, ...],
    filter_segments: list[str],
) -> list[Path]:
    """Walk ``root`` for files matching ``extensions``, skipping filtered subtrees."""
    matches: list[Path] = []
    ext_lower = tuple(e.lower() for e in extensions)
    for dirpath, dirnames, filenames in os.walk(root):
        dir_path = Path(dirpath)
        if is_excluded(dir_path, root, filter_segments):
            dirnames[:] = []
            continue
        for name in filenames:
            if not name.lower().endswith(ext_lower):
                continue
            full = dir_path / name
            if is_excluded(full, root, filter_segments):
                continue
            matches.append(full)
    return matches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="strip_bom",
        description="Strip UTF-8 BOMs from text files under the configured project root.",
    )
    parser.add_argument(
        "--path",
        "-p",
        type=Path,
        default=Path(os.environ.get("ROOT_PATH", ".")),
        help="Project root to scan (default: ROOT_PATH from .env)",
    )
    parser.add_argument(
        "--ext",
        "-e",
        nargs="+",
        default=list(DEFAULT_EXTENSIONS),
        metavar="EXT",
        help=f"File extensions to scan (default: {' '.join(DEFAULT_EXTENSIONS)})",
    )
    parser.add_argument(
        "--filter-path",
        nargs="*",
        default=get_env_list("FILTER_PATH"),
        metavar="SEG",
        help="Path segments to exclude (default: FILTER_PATH from .env)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Rewrite files (default: dry-run, report only)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable coloured output (plain text mode)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_console(plain=args.no_color)
    console = get_console()

    root: Path = args.path.resolve()
    if not root.exists() or not root.is_dir():
        console.print(f"[error]Project path does not exist or is not a directory:[/] [path]{root}[/]")
        return 2

    extensions = tuple(e if e.startswith(".") else f".{e}" for e in args.ext)
    mode = "APPLY" if args.apply else "DRY-RUN"

    console.print(f"[info]BOM strip {mode}[/] — scanning [path]{root}[/]")
    console.print(f"[muted]Extensions:[/] {', '.join(extensions)}")
    if args.filter_path:
        console.print(f"[muted]Excluding segments:[/] {', '.join(args.filter_path)}")

    candidates = iter_target_files(root, extensions, args.filter_path)
    bom_files = [p for p in candidates if file_starts_with_bom(p)]

    console.print(
        f"[muted]Scanned:[/] [count]{len(candidates)}[/] files  "
        f"[muted]With BOM:[/] [count]{len(bom_files)}[/]"
    )

    if not bom_files:
        console.print("[success]No BOM-prefixed files found.[/]")
        return 0

    rewritten = 0
    failed: list[Path] = []
    for path in bom_files:
        rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        if args.apply:
            if strip_bom(path):
                rewritten += 1
                console.print(f"  [success]stripped[/] [path]{rel}[/]")
            else:
                failed.append(path)
                console.print(f"  [error]failed[/]   [path]{rel}[/]")
        else:
            console.print(f"  [warning]would strip[/] [path]{rel}[/]")

    if args.apply:
        console.print(
            f"[success]Done.[/] Rewrote [count]{rewritten}[/] of [count]{len(bom_files)}[/] files."
        )
        if failed:
            console.print(f"[error]{len(failed)} files could not be rewritten.[/]")
            return 1
        return 0
    else:
        console.print(
            f"[info]Dry-run complete.[/] Re-run with [command]--apply[/] to rewrite "
            f"[count]{len(bom_files)}[/] files."
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
