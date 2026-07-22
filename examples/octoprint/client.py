#!/usr/bin/env python3
# Reference example — facts-only, no warranty; supply your own printer + credentials.
"""OctoPrint (host controller) reference client — REST + SockJS paradigm.

Demonstrates the "host controller" paradigm: a client talks to an OctoPrint
instance's documented HTTP REST API (never to the printer firmware underneath),
authenticating with a single API key. Covers any USB/serial FDM printer fronted
by an OctoPrint host (and, from OctoPrint 2.0, its Serial / Moonraker / Bambu
connectors — the /api/* surface is unchanged).

Live push rides a SockJS channel at /sockjs/ (its own handshake + framing, not a
raw WebSocket) — noted below but NOT implemented here; this minimal example uses
REST polling of /api/job + /api/printer as the poll backstop the paper documents.

Protocol paper: ../../protocols/octoprint.md
License: MIT.

Reads everything from the environment / argv — nothing is hardcoded:
  OCTOPRINT_HOST     e.g. 192.0.2.10:5000  (host[:port], or a full http/https URL)
  OCTOPRINT_API_KEY  an Application/User API key you generate in YOUR OctoPrint
                     (Settings > Application Keys, or the per-user API key). This
                     script never contains a key; it only reads the mechanism.

Dependencies: requests (only).
"""
import os
import sys
import requests


def base_url(host: str) -> str:
    """Normalize host[:port] or a full URL into an http(s) base with no trailing slash."""
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host.rstrip("/")


def get_json(base: str, path: str, key: str):
    """GET an /api/* endpoint with the X-Api-Key header. Returns (status, parsed-or-None)."""
    resp = requests.get(base + path, headers={"X-Api-Key": key}, timeout=10)
    try:
        body = resp.json()
    except ValueError:
        body = None
    return resp.status_code, body


def read_state(base: str, key: str) -> None:
    """Print live identity, printer temps/state, and job progress via the REST poll backstop."""
    st, ver = get_json(base, "/api/version", key)
    if st == 403:
        print("403 Forbidden — the API key is missing or invalid for this instance.")
        return
    # The "OctoPrint " prefix in `text` is the positive genuineness tell.
    print(f"version: {ver}  (server={ver.get('server') if ver else '?'})")

    # /api/printer returns 409 when the printer is not operational — a valid
    # "not connected" signal, not a transport failure.
    st, pr = get_json(base, "/api/printer", key)
    if st == 409:
        print("printer: not operational (409) — host is up but no printer connected.")
    elif st == 200 and pr:
        flags = pr.get("state", {}).get("flags", {})
        print(f"printer state: {pr.get('state', {}).get('text')}  flags={flags}")
        for name, ch in (pr.get("temperature") or {}).items():
            if isinstance(ch, dict):
                print(f"  {name}: actual={ch.get('actual')} target={ch.get('target')} °C")
    else:
        print(f"printer: unexpected status {st}")

    # /api/job — note: progress.completion is a FRACTION 0.0-1.0 (x100 for a bar)
    # and is file-byte position, not time. Trust progress.printTimeLeft (seconds)
    # for "remaining", and printTimeLeftOrigin qualifies its quality.
    st, job = get_json(base, "/api/job", key)
    if st == 200 and job:
        prog = job.get("progress") or {}
        comp = prog.get("completion")
        pct = f"{comp * 100:.1f}%" if isinstance(comp, (int, float)) else "n/a"
        print(f"job: {(job.get('job') or {}).get('file', {}).get('name')}  "
              f"completion={pct}  printTimeLeft={prog.get('printTimeLeft')}s "
              f"(origin={prog.get('printTimeLeftOrigin')})")


def upload_and_launch(base: str, key: str, gcode_path: str, start: bool) -> None:
    """Upload a machinecode file to the `local` storage; optionally launch it.

    Guarded behind the --print flag because printing drives a hot, moving machine.
    Upload is multipart POST /api/files/local with the form part `file`; select/print
    can ride inline. We upload-and-hold, then read back effectiveSelect/effectivePrint.
    """
    name = os.path.basename(gcode_path)
    with open(gcode_path, "rb") as fh:
        files = {"file": (name, fh, "application/octet-stream")}
        # Upload-and-hold: do not start inline; decide below so the job record stays clean.
        data = {"select": "true", "print": "false"}
        resp = requests.post(base + "/api/files/local",
                             headers={"X-Api-Key": key}, files=files, data=data, timeout=60)
    print(f"upload: HTTP {resp.status_code}")
    if resp.status_code == 201:
        body = resp.json()
        print(f"  effectiveSelect={body.get('effectiveSelect')} "
              f"effectivePrint={body.get('effectivePrint')} done={body.get('done')}")
    else:
        print(f"  upload failed (415=bad extension, 409=would interrupt, 400=bad field): {resp.text[:200]}")
        return

    if not start:
        print("  (not starting — pass --print to launch; select+start shown next)")
        return

    # Explicit start on the selected file. Control POSTs return 204 with an empty body;
    # read the effect from a follow-up GET /api/job, never from this response.
    resp = requests.post(base + "/api/job", headers={"X-Api-Key": key},
                        json={"command": "start"}, timeout=10)
    print(f"start: HTTP {resp.status_code} (204 = accepted)")


def usage() -> None:
    print(__doc__)
    print("Usage:\n"
          "  OCTOPRINT_HOST=192.0.2.10:5000 OCTOPRINT_API_KEY=... python client.py\n"
          "  ... python client.py upload example.gcode          # upload + select, hold\n"
          "  ... python client.py upload example.gcode --print   # upload, then START a print\n"
          "Host/key may also be passed as: python client.py <host> <api_key> [upload <file> [--print]]")


if __name__ == "__main__":
    argv = sys.argv[1:]
    host = os.environ.get("OCTOPRINT_HOST")
    key = os.environ.get("OCTOPRINT_API_KEY")
    # Allow leading positional host/key when env is not set.
    if argv and argv[0] not in ("upload",) and not host:
        host = argv.pop(0)
        if argv and argv[0] not in ("upload",) and not key:
            key = argv.pop(0)

    if not host or not key:
        usage()
        sys.exit(1)

    base = base_url(host)
    if argv and argv[0] == "upload":
        if len(argv) < 2:
            usage()
            sys.exit(1)
        upload_and_launch(base, key, argv[1], start="--print" in argv[2:])
    else:
        read_state(base, key)
