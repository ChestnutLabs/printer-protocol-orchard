#!/usr/bin/env python3
"""Clean-room / secret gate for the Printer Protocol Orchard.

This is the load-bearing guardrail that keeps the repository publishable under
its MIT + CC BY 4.0 terms. The Orchard documents *uncopyrightable interface facts*
(ports, field names, message shapes, enums, command verbs) for the LAN control
protocols of consumer 3D printers you own. To stay clean-room it must never carry:

  * certificate / private-key material or other credential *values*
  * concrete secrets pasted into examples (access codes, tokens, passwords, ...)
  * un-sanitized private IP addresses that leak a real network topology

This script walks the whole repository and prints a `BLOCK <file>:<line> <reason>`
line for every finding, then exits non-zero if anything was flagged. It enforces,
mechanically, the human checklist in ../CLEANROOM-CHECKLIST.md.

What it flags
-------------
  1. Forbidden binary/credential file *extensions* anywhere in the tree
     (.crt .pem .cer .key .p12 .pfx .jks .der) — cert/keystore containers have
     no place in a facts-only repo.
  2. PEM private-key / certificate headers embedded in text content.
  3. Credential-shaped assignments (`access_code`, `token`, `api_key`, ...) whose
     right-hand side is a concrete literal rather than an obvious placeholder or a
     runtime lookup (os.environ / getenv / argv / input()).
  4. Un-sanitized private IPv4 (RFC 1918: 10/8, 172.16/12, 192.168/16). Everything
     in an example must be rewritten to the RFC 5737 TEST-NET blocks.

Escape hatches
--------------
  * A line containing the marker `cleanroom:allow` is skipped (annotate *why*).
  * A repo-root `.cleanroomignore` file (one glob per line, `#` comments) excludes
    matching paths from the whole scan.

Design notes
------------
  * Pure standard library, Python 3.9+. No third-party imports.
  * Facts-only, false-positive-averse: firmware VERSION strings frequently look
    like dotted quads (e.g. `1.2.3.4`). We therefore ONLY flag the three private
    ranges above — a bare dotted-quad outside them is never flagged.
"""

from __future__ import annotations

import fnmatch
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, NamedTuple, Optional

# Repo root = parent of this scripts/ directory.
REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories we never descend into.
SKIP_DIR_NAMES = {".git", "node_modules"}


def _is_skipped_dir(name: str) -> bool:
    return name in SKIP_DIR_NAMES or name.endswith(".egg-info")


# ---------------------------------------------------------------------------
# Rule 1: forbidden credential/keystore file extensions.
# ---------------------------------------------------------------------------
FORBIDDEN_EXTENSIONS = {
    ".crt",
    ".pem",
    ".cer",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".der",
}

# ---------------------------------------------------------------------------
# Rule 2: PEM private-key / certificate headers.
# ---------------------------------------------------------------------------
PEM_HEADER_RE = re.compile(
    r"BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY|BEGIN CERTIFICATE"  # cleanroom:allow -- detector pattern, not a key
)

# ---------------------------------------------------------------------------
# Rule 3: credential-shaped assignments with a concrete value.
# ---------------------------------------------------------------------------
# key <sep> value, where key is one of the credential-ish names.
CREDENTIAL_RE = re.compile(
    r"(?i)\b(access[_-]?code|auth[_-]?code|check[_-]?code|password|passwd|"
    r"token|secret|api[_-]?key|provision[_-]?key)\b"
    r"\s*[:=]\s*"
    r"(?P<value>.+)$"
)

# Substrings that mark a value as an obvious placeholder / runtime lookup and
# therefore NOT a leaked secret. Compared case-insensitively. The ellipsis forms
# ("…" / "...") are how the papers elide a credential in an example URL or table.
PLACEHOLDER_MARKERS = (
    "example",
    "redacted",
    "<",
    ">",
    "your_",
    "xxxx",
    "***",
    "os.environ",
    "getenv",
    "argv",
    "input(",
    "${",
    "…",  # … ellipsis
    "...",
)

# A concrete secret value is a compact literal *token*, not a sentence: it has no
# internal whitespace and is drawn from the credential/base64/hex charset.
_SECRET_TOKEN_RE = re.compile(r"^[A-Za-z0-9._\-+/=]{8,}$")


def _leading_literal(raw_value: str) -> str:
    """Extract the candidate literal token that a credential is assigned to.

    Handles quoted strings (`"abc"`, `'abc'`, `` `abc` ``) and bare tokens, and
    strips surrounding markdown emphasis / punctuation. Prose values (a sentence
    describing *where* to find the credential) collapse to a short first word or
    empty string and are therefore not treated as secrets.
    """
    value = raw_value.strip()
    if not value:
        return ""
    # If the value opens with a quote/backtick, the literal is the quoted content.
    if value[0] in "\"'`":
        closing = value.find(value[0], 1)
        if closing > 0:
            return value[1:closing].strip()
        value = value[1:]
    # Otherwise take the first whitespace-delimited token and trim decoration.
    first = value.split()[0] if value.split() else ""
    return first.strip("\"'`*,;:|[]{}()")


def _is_concrete_secret(raw_value: str) -> bool:
    """True only when the RHS looks like a real, leaked credential literal.

    False for empty values, enumerated placeholders, runtime lookups, and prose
    that merely *describes* the credential mechanism ("the printer's access code").
    """
    value = raw_value.strip()
    if not value:
        return False
    lowered = value.lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker in lowered:
            return False
    token = _leading_literal(value)
    if not token:
        return False
    if not _SECRET_TOKEN_RE.match(token):
        return False
    # Require an entropy signal (digit / mixed-case) or substantial length so that
    # plain English words assigned as values ("write", "yes") are not flagged.
    has_digit = any(ch.isdigit() for ch in token)
    has_upper = any(ch.isupper() for ch in token)
    has_lower = any(ch.islower() for ch in token)
    if has_digit or (has_upper and has_lower) or len(token) >= 20:
        return True
    return False


# ---------------------------------------------------------------------------
# Rule 4: un-sanitized private IPv4.
# ---------------------------------------------------------------------------
IPV4_RE = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")


def _is_private_ipv4(octets: List[int]) -> bool:
    """RFC 1918 private ranges only (10/8, 172.16/12, 192.168/16)."""
    a, b, _c, _d = octets
    if a == 10:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    if a == 192 and b == 168:
        return True
    return False


def _find_unsanitized_ip(line: str) -> Optional[str]:
    for match in IPV4_RE.finditer(line):
        octets = [int(g) for g in match.groups()]
        if any(o > 255 for o in octets):
            continue  # not a valid dotted quad; likely a version string
        if _is_private_ipv4(octets):
            return match.group(0)
    return None


# ---------------------------------------------------------------------------
# Finding + reporting.
# ---------------------------------------------------------------------------
class Finding(NamedTuple):
    path: Path
    line: int
    reason: str


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_ignore_globs() -> List[str]:
    """Read .cleanroomignore at the repo root (one glob per line, '#' comments)."""
    ignore_file = REPO_ROOT / ".cleanroomignore"
    globs: List[str] = []
    if not ignore_file.is_file():
        return globs
    for raw in ignore_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        globs.append(line)
    return globs


def _is_ignored(rel_path: str, globs: Iterable[str]) -> bool:
    for pattern in globs:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        # Also match directory-prefix style entries (e.g. "vendor/").
        if pattern.endswith("/") and rel_path.startswith(pattern):
            return True
    return False


def iter_repo_files() -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        # Prune skipped directories in place so os.walk does not descend.
        dirnames[:] = [d for d in dirnames if not _is_skipped_dir(d)]
        for name in filenames:
            yield Path(dirpath) / name


def _read_text_lines(path: Path) -> Optional[List[str]]:
    """Return the file's lines, or None if it is binary/unreadable as text."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None  # binary; skip content scanning
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("latin-1")
        except UnicodeDecodeError:
            return None
    return text.splitlines()


def scan_file(path: Path) -> List[Finding]:
    findings: List[Finding] = []

    # Rule 1: forbidden extension (checked regardless of content readability).
    if path.suffix.lower() in FORBIDDEN_EXTENSIONS:
        findings.append(
            Finding(
                path,
                0,
                f"forbidden credential/keystore file extension '{path.suffix.lower()}'",
            )
        )
        # Do not also try to read likely-binary keystore contents.
        return findings

    lines = _read_text_lines(path)
    if lines is None:
        return findings

    for lineno, line in enumerate(lines, start=1):
        if "cleanroom:allow" in line:
            continue

        # Rule 2: PEM headers.
        if PEM_HEADER_RE.search(line):
            findings.append(
                Finding(path, lineno, "PEM private-key / certificate header in content")
            )

        # Rule 3: credential-shaped assignment with a concrete value.
        cred = CREDENTIAL_RE.search(line)
        if cred and _is_concrete_secret(cred.group("value")):
            key = cred.group(1)
            findings.append(
                Finding(
                    path,
                    lineno,
                    f"credential-shaped assignment '{key}' with a concrete value "
                    f"(use os.environ/argv/input or an EXAMPLE placeholder)",
                )
            )

        # Rule 4: un-sanitized private IPv4.
        bad_ip = _find_unsanitized_ip(line)
        if bad_ip is not None:
            findings.append(
                Finding(
                    path,
                    lineno,
                    f"un-sanitized private IPv4 '{bad_ip}' "
                    f"(rewrite to 192.0.2.x TEST-NET-1)",
                )
            )

    return findings


def main(argv: Optional[List[str]] = None) -> int:
    ignore_globs = load_ignore_globs()
    all_findings: List[Finding] = []
    scanned = 0

    for path in iter_repo_files():
        rel = _rel(path)
        if _is_ignored(rel, ignore_globs):
            continue
        scanned += 1
        all_findings.extend(scan_file(path))

    for finding in all_findings:
        print(f"BLOCK {_rel(finding.path)}:{finding.line} {finding.reason}")

    if all_findings:
        print(
            f"\nclean-room scan: {len(all_findings)} finding(s) across "
            f"{scanned} file(s) — FAILED"
        )
        return 1

    print(f"clean-room scan: OK ({scanned} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
