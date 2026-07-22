#!/usr/bin/env python3
"""Schema + fixture validator for the Printer Protocol Orchard.

Every machine-readable artifact in the repo must parse as JSON, and every file
under `schemas/` must carry a `_meta` block that asserts, in-band, that it is a
facts-only, sanitized, clean-room description. This script is the mechanical
check for that contract.

What it does
------------
  * `json.load` every `schemas/**/*.json` and `fixtures/**/*.json`; a
    JSONDecodeError fails the file (with its path and the parser message).
  * For `schemas/` files it additionally requires a top-level `_meta` object with
    the keys: schema_kind, title, confidence, derived_from, facts_only, sanitized
    — and asserts `facts_only === true` and `sanitized === true`.
  * Prints one line per file (`ok <path>` / `FAIL <path>: <why>`), a summary, and
    exits 1 if any file failed, else 0.

Pure standard library, Python 3.9+. No third-party imports.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"
FIXTURES_DIR = REPO_ROOT / "fixtures"

REQUIRED_META_KEYS = (
    "schema_kind",
    "title",
    "confidence",
    "derived_from",
    "facts_only",
    "sanitized",
)


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def validate_schema_meta(data: object) -> Optional[str]:
    """Return an error string if the schema `_meta` contract is violated, else None."""
    if not isinstance(data, dict):
        return "top-level JSON is not an object (no place for _meta)"
    meta = data.get("_meta")
    if not isinstance(meta, dict):
        return "missing top-level '_meta' object"
    missing = [k for k in REQUIRED_META_KEYS if k not in meta]
    if missing:
        return f"_meta missing required key(s): {', '.join(missing)}"
    if meta.get("facts_only") is not True:
        return "_meta.facts_only must be exactly true"
    if meta.get("sanitized") is not True:
        return "_meta.sanitized must be exactly true"
    return None


def check_file(path: Path, *, require_meta: bool) -> Tuple[bool, str]:
    """Return (ok, message) for one JSON file."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        return False, f"invalid JSON: {exc}"
    except OSError as exc:
        return False, f"cannot read file: {exc}"

    if require_meta:
        err = validate_schema_meta(data)
        if err is not None:
            return False, err

    return True, "ok"


def main(argv: Optional[List[str]] = None) -> int:
    schema_files = sorted(SCHEMAS_DIR.rglob("*.json")) if SCHEMAS_DIR.is_dir() else []
    fixture_files = sorted(FIXTURES_DIR.rglob("*.json")) if FIXTURES_DIR.is_dir() else []

    failures = 0
    total = 0

    for path in schema_files:
        total += 1
        ok, msg = check_file(path, require_meta=True)
        if ok:
            print(f"ok {_rel(path)}")
        else:
            failures += 1
            print(f"FAIL {_rel(path)}: {msg}")

    for path in fixture_files:
        total += 1
        ok, msg = check_file(path, require_meta=False)
        if ok:
            print(f"ok {_rel(path)}")
        else:
            failures += 1
            print(f"FAIL {_rel(path)}: {msg}")

    if failures:
        print(f"\nschema validation: {failures} of {total} file(s) FAILED")
        return 1

    print(f"\nschema validation: OK ({total} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
