#!/usr/bin/env python3
"""Reference client for the PrusaLink paradigm: host controller, plain-HTTP REST,
HTTP Digest auth, poll-only (no push).

Paradigm: a single plain-HTTP service on the LAN. Every piece of live state is
obtained by polling GET /api/v1/status (plus GET /api/v1/job when a job exists);
there is no MQTT / WebSocket / SSE / push channel of any kind. File upload is a
raw PUT of the file body; print launch is one-shot via a Print-After-Upload
header or a POST to an already-uploaded file.

Families covered: Prusa hosts running PrusaLink on Buddy firmware (MK4/MK4S,
MK3.9, MINI/MINI+, XL, Core One), the Raspberry Pi Prusa-Link app (MK3S+), and
SL1/SL1S (SLA). This demonstrates the modern /api/v1 surface with a legacy
/api/printer + /api/job fallback for older firmware.

Protocol paper: ../../protocols/prusalink.md

SPDX-License-Identifier: MIT

Reference example -- facts-only, no warranty; supply your own printer +
credentials. Nothing is hardcoded: host and password come from the environment
or argv. This talks only to a device the operator owns on their own LAN.
"""

import os
import sys

import requests
from requests.auth import HTTPDigestAuth

TIMEOUT = 10
# The modern /api/v1 surface uses the fixed literal username "maker"; the
# password is set on the printer (PrusaLink settings / the printer's screen).
DIGEST_USER = os.environ.get("PRUSALINK_USER", "maker")


def make_session(password):
    """Build a requests session with HTTP Digest auth and JSON error bodies."""
    s = requests.Session()
    s.auth = HTTPDigestAuth(DIGEST_USER, password)
    s.headers.update({"Accept": "application/json"})
    return s


def get_json(session, base, path):
    """GET base+path; return parsed JSON, or None on 204 No Content."""
    resp = session.get(base + path, timeout=TIMEOUT)
    resp.raise_for_status()
    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


def read_state(session, base):
    """Poll identity + live state, with a legacy fallback for old firmware.

    Modern: GET /api/v1/info, /api/v1/status, /api/v1/job.
    Legacy: GET /api/version, /api/printer, /api/job.
    """
    try:
        info = get_json(session, base, "/api/v1/info")
        status = get_json(session, base, "/api/v1/status")
        job = get_json(session, base, "/api/v1/job")  # 204 -> None when idle
        return {"api": "v1", "info": info, "status": status, "job": job}
    except requests.HTTPError as exc:
        if exc.response is None or exc.response.status_code != 404:
            raise
        # Older firmware without the /api/v1 surface: fall back to the legacy tier.
        version = get_json(session, base, "/api/version")
        printer = get_json(session, base, "/api/printer")
        job = get_json(session, base, "/api/job")
        return {"api": "legacy", "version": version, "printer": printer, "job": job}


def upload_and_maybe_print(session, base, storage, path, local_file, start):
    """PUT the raw file body to /api/v1/files/{storage}/{path}.

    Boolean headers use the ?0/?1 structured-header syntax (NOT true/1).
    Print-After-Upload: ?1 makes it a one-shot upload-and-start. Confirm a start
    by polling status/job for state=PRINTING afterwards -- there is no
    synchronous "print started" ack beyond the 201.
    """
    with open(local_file, "rb") as fh:
        body = fh.read()
    headers = {
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(body)),
        "Print-After-Upload": "?1" if start else "?0",
    }
    url = "{}/api/v1/files/{}/{}".format(base, storage, path.lstrip("/"))
    resp = session.put(url, data=body, headers=headers, timeout=max(TIMEOUT, 60))
    resp.raise_for_status()
    return resp.status_code  # expect 201 Created


def main(argv):
    base = os.environ.get("PRUSALINK_HOST") or (argv[1] if len(argv) > 1 else None)
    password = os.environ.get("PRUSALINK_PASSWORD")
    if not base or not password:
        print(__doc__)
        print("Usage:")
        print("  PRUSALINK_HOST=http://<printer-ip> PRUSALINK_PASSWORD=<pw> \\")
        print("      python client.py [http://<printer-ip>]")
        print()
        print("Env vars:")
        print("  PRUSALINK_HOST      base URL, e.g. http://192.0.2.10 (or argv[1])")
        print("  PRUSALINK_PASSWORD  the printer's LAN password (required)")
        print("  PRUSALINK_USER      Digest username (default: maker)")
        print()
        print("Optional upload (guarded; omit --start to upload without printing):")
        print("  python client.py --upload <storage> <path> <local_file> [--start]")
        return 2

    if not base.startswith("http://") and not base.startswith("https://"):
        base = "http://" + base
    base = base.rstrip("/")

    session = make_session(password)

    # --- Upload path (opt-in; --start actually launches a print) --------------
    if "--upload" in argv:
        i = argv.index("--upload")
        try:
            storage, path, local_file = argv[i + 1], argv[i + 2], argv[i + 3]
        except IndexError:
            print("--upload needs: <storage> <path> <local_file> [--start]")
            return 2
        start = "--start" in argv
        code = upload_and_maybe_print(session, base, storage, path, local_file, start)
        print("upload HTTP {} (start={})".format(code, start))
        if start:
            print("confirm by polling status/job for state=PRINTING")
        return 0

    # --- Default path: read and print live state ------------------------------
    state = read_state(session, base)
    import json

    print(json.dumps(state, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
