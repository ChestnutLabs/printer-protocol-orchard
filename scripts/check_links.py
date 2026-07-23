#!/usr/bin/env python3
"""Local Markdown link integrity checker for the Printer Protocol Orchard.

Scans every `*.md` file in the repository, extracts inline Markdown links of the
form `[text](target)`, and verifies two things for each *local* target:

  1. The file it points to exists on disk.
  2. If the link carries a `#fragment`, a matching heading anchor exists in the
     target file (or, for a pure `#anchor`, in the same file).

This catches renamed/moved papers and — new — dead in-page anchors, which would
otherwise render as silent no-op links on the site and on GitHub.

Scope
-----
  * Local link integrity ONLY — the network is never contacted.
  * Targets that are skipped (treated as always-valid):
      - `http:` / `https:` URLs
      - `mailto:` links
  * File check: any `#fragment` is stripped, the path is resolved relative to the
    containing file, and the result must exist. Missing targets print
    `BROKEN <file>: <target>`.
  * Anchor check: applied only when the (resolved) target is a Markdown file. The
    fragment is compared against the file's heading slugs, computed with a
    GitHub-compatible algorithm kept in sync with the `toc.slugify` setting in
    mkdocs.yml (so an anchor resolves identically in raw Markdown on GitHub and on
    the rendered site). Explicit `{#id}` (attr_list) and HTML `id=`/`name=` anchors
    are also honoured. A missing anchor prints
    `BROKEN <file>: <target>  (no anchor '#<frag>' in <target-file>)`.

Pure standard library, Python 3.9+. No third-party imports.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIR_NAMES = {".git", "node_modules"}

# Inline Markdown link: [text](target). The target stops at the first
# whitespace (which would begin an optional "title") or the closing paren.
LINK_RE = re.compile(r"\[[^\]]*\]\(\s*(?P<target>[^)\s]+)")

# ATX heading: 1-6 leading '#', text, optional trailing '#'s.
ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(?P<text>.*?)\s*#*\s*$")
# Fenced code block delimiter (``` or ~~~), so headings inside code are ignored.
FENCE_RE = re.compile(r"^\s*(?P<fence>```+|~~~+)")
# Explicit attr_list id on a heading: {#custom-id} (also tolerates {: ... #id ... }).
EXPLICIT_ID_RE = re.compile(r"\{:?[^}]*#([-\w]+)[^}]*\}")
# Inline HTML anchor: <a id="x"> / <span name="y"> etc.
HTML_ID_RE = re.compile(r"""<[^>]*\b(?:id|name)\s*=\s*["']([-\w]+)["']""")

# Cache of resolved-md-file -> anchor set, so a file is slugified at most once.
_ANCHOR_CACHE: Dict[Path, Set[str]] = {}


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


def slugify_github(text: str) -> str:
    """Heading -> anchor slug, GitHub-compatible (matches pymdownx.slugs.slugify
    case='lower' used by mkdocs.yml). Keeps letters/digits/underscore/hyphen and
    turns each remaining whitespace char into a hyphen WITHOUT collapsing runs, so
    `Faults & HMS` -> `faults--hms` (the `&` drops out, leaving two spaces)."""
    text = re.sub(r"`+", "", text)                       # drop inline-code ticks
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [t](u)/![alt](u) -> text
    text = re.sub(r"[*_]{1,3}", "", text)                # drop emphasis markers
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)                 # keep word chars, ws, hyphen
    text = re.sub(r"\s", "-", text)                      # ws -> hyphen (no collapse)
    return text


def _anchor_set(text: str) -> Set[str]:
    """All valid anchor ids in a Markdown document: heading slugs (de-duplicated
    GitHub-style with -1/-2 suffixes) plus explicit {#id} and HTML id/name anchors.
    Headings inside fenced code blocks are ignored."""
    anchors: Set[str] = set()
    base_counts: Dict[str, int] = {}
    in_fence = False
    fence_char = ""

    for line in text.splitlines():
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group("fence")[0]
            if not in_fence:
                in_fence, fence_char = True, marker
            elif line.strip()[:1] == fence_char:
                in_fence = False
            continue
        if in_fence:
            continue

        for hid in HTML_ID_RE.findall(line):
            anchors.add(hid.lower())

        m = ATX_HEADING_RE.match(line)
        if not m:
            continue
        htext = m.group("text")
        explicit = EXPLICIT_ID_RE.search(htext)
        if explicit:
            anchors.add(explicit.group(1).lower())
            htext = EXPLICIT_ID_RE.sub("", htext)
        slug = slugify_github(htext)
        if not slug:
            continue
        n = base_counts.get(slug, 0)
        anchors.add(slug if n == 0 else f"{slug}-{n}")
        base_counts[slug] = n + 1

    return anchors


def get_anchors(md_file: Path) -> Set[str]:
    cached = _ANCHOR_CACHE.get(md_file)
    if cached is None:
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        cached = _anchor_set(text)
        _ANCHOR_CACHE[md_file] = cached
    return cached


def _anchor_ok(frag: str, anchors: Set[str]) -> bool:
    frag = unquote(frag).lower()
    if frag in anchors:
        return True
    # Tolerate a de-dup suffix style we didn't generate (e.g. python-markdown's
    # `_1`) by accepting the base slug when it exists.
    base = re.match(r"^(?P<base>.+)[-_]\d+$", frag)
    return bool(base and base.group("base") in anchors)


def resolve_target(md_file: Path, target: str) -> Path:
    """Resolve a local link target (fragment stripped) relative to its file."""
    path_part = unquote(target.split("#", 1)[0])
    if path_part.startswith("/"):
        return (REPO_ROOT / path_part.lstrip("/")).resolve()
    return (md_file.parent / path_part).resolve()


def check_file(md_file: Path) -> List[str]:
    """Return a list of problem descriptions for one Markdown file."""
    broken: List[str] = []
    try:
        text = md_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return broken

    for match in LINK_RE.finditer(text):
        target = match.group("target")
        if target.lower().startswith(("http:", "https:", "mailto:")):
            continue

        path_part, _, frag = target.partition("#")
        path_part = unquote(path_part)
        if not path_part and not frag:
            continue  # empty link / bare '#'

        if path_part:
            resolved = resolve_target(md_file, target)
            if not resolved.exists():
                broken.append(target)  # missing file
                continue
            anchor_file = resolved
        else:
            anchor_file = md_file  # pure in-page anchor

        if frag and anchor_file.suffix.lower() == ".md":
            if not _anchor_ok(frag, get_anchors(anchor_file)):
                where = "this file" if anchor_file == md_file else _rel(anchor_file)
                broken.append(f"{target}  (no anchor '#{unquote(frag)}' in {where})")

    return broken


def main(argv: Optional[List[str]] = None) -> int:
    total_files = 0
    broken_count = 0

    for md_file in iter_markdown_files():
        total_files += 1
        for problem in check_file(md_file):
            broken_count += 1
            print(f"BROKEN {_rel(md_file)}: {problem}")

    if broken_count:
        print(
            f"\nlink check: {broken_count} broken local link(s)/anchor(s) across "
            f"{total_files} markdown file(s) — FAILED"
        )
        return 1

    print(f"link check: OK ({total_files} markdown files, links + anchors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
