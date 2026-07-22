#!/usr/bin/env python3
"""Local Markdown link integrity checker for the Printer Protocol Orchard.

Scans every `*.md` file in the repository, extracts inline Markdown links of the
form `[text](target)`, and verifies that each *local* target resolves to a file
that exists on disk. This catches renamed/moved papers, schemas, and fixtures
before they ship as dead cross-references.

Scope
-----
  * Local link integrity ONLY — the network is never contacted.
  * Targets that are skipped (treated as always-valid):
      - `http:` / `https:` URLs
      - `mailto:` links
      - pure in-page anchors (`#section`)
  * For a local target, any `#fragment` is stripped, the path is resolved relative
    to the containing file, and the result must exist. Missing targets print
    `BROKEN <file>: <target>`.

Pure standard library, Python 3.9+. No third-party imports.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIR_NAMES = {".git", "node_modules"}

# Inline Markdown link: [text](target). The target stops at the first
# whitespace (which would begin an optional "title") or the closing paren.
LINK_RE = re.compile(r"\[[^\]]*\]\(\s*(?P<target>[^)\s]+)")


def _is_skipped_dir(name: str) -> bool:
    return name in SKIP_DIR_NAMES or name.endswith(".egg-info")


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def iter_markdown_files() -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if not _is_skipped_dir(d)]
        for name in filenames:
            if name.lower().endswith(".md"):
                yield Path(dirpath) / name


def _is_external_or_anchor(target: str) -> bool:
    lowered = target.lower()
    if lowered.startswith(("http:", "https:", "mailto:")):
        return True
    if target.startswith("#"):
        return True
    return False


def resolve_target(md_file: Path, target: str) -> Path:
    """Resolve a local link target (fragment stripped) relative to its file."""
    # Strip any #fragment, then URL-decode (e.g. %20 -> space).
    path_part = target.split("#", 1)[0]
    path_part = unquote(path_part)
    if path_part.startswith("/"):
        # Root-relative to the repo.
        return (REPO_ROOT / path_part.lstrip("/")).resolve()
    return (md_file.parent / path_part).resolve()


def check_file(md_file: Path) -> List[str]:
    """Return a list of broken target strings for one Markdown file."""
    broken: List[str] = []
    try:
        text = md_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return broken

    for match in LINK_RE.finditer(text):
        target = match.group("target")
        if _is_external_or_anchor(target):
            continue
        # An empty path part (link is only a fragment after decode) is fine.
        if not target.split("#", 1)[0]:
            continue
        resolved = resolve_target(md_file, target)
        if not resolved.exists():
            broken.append(target)

    return broken


def main(argv: Optional[List[str]] = None) -> int:
    total_links_files = 0
    broken_count = 0

    for md_file in iter_markdown_files():
        total_links_files += 1
        for target in check_file(md_file):
            broken_count += 1
            print(f"BROKEN {_rel(md_file)}: {target}")

    if broken_count:
        print(
            f"\nlink check: {broken_count} broken local link(s) across "
            f"{total_links_files} markdown file(s) — FAILED"
        )
        return 1

    print(f"link check: OK ({total_links_files} markdown files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
