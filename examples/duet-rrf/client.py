#!/usr/bin/env python3
"""Reference client — Duet3D / RepRapFirmware, object model over HTTP (standalone `rr_*`).

Demonstrates the **standalone** RRF LAN paradigm: an optional password session, a poll
of the JSON Object Model, and the upload-then-launch print flow. This is the poll-only
`rr_*` HTTP API a Duet board serves on `:80` with NO companion Pi.

Families covered: Duet 2 / Duet 3 boards (WiFi/Ethernet/Mini/6HC/6XD...) and RRF-3.0+
derivatives (E3D ToolChanger, Jubilee, and other RepRapFirmware machines) running in
standalone mode.

The SBC/DSF variant (Duet 3 + Raspberry Pi running Duet Software Framework) speaks a
different wire dialect — `GET /machine/status` to read, `POST /machine/code` to send
GCode, `PUT /machine/file/{path}` to upload, and one push WebSocket at `/machine`. It is
noted here but NOT implemented; this file is standalone-only.

Protocol paper: ../../protocols/duet.md
License: MIT. SPDX-License-Identifier: MIT

Reference example — facts-only, no warranty; supply your own printer + credentials.
"""

# Reference example — facts-only, no warranty; supply your own printer + credentials.
#
# Credentials are NEVER hardcoded. This script reads them at runtime:
#   DUET_HOST      host or IP of your board          (or argv[1])
#   DUET_PASSWORD  machine password, if one is set   (optional; default RRF is "reprap";
#                  an unset password auto-creates a session on any request)
# The machine password is the one you configured on YOUR OWN board (`M551` in config.g);
# if you never set one it is unset/"reprap". It is a MECHANISM you supply — not a value
# that lives in this file.
#
# Requires: requests  (pip install requests)

import os
import sys
import time
import requests

TIMEOUT = 10


def connect(base, password):
    """Open an optional session. Returns the X-Session-Key header dict (may be empty)."""
    r = requests.get(
        base + "/rr_connect",
        params={"password": password, "sessionKey": "yes"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    body = r.json()
    err = body.get("err", 0)
    if err == 1:
        raise SystemExit("rr_connect err:1 — invalid password.")
    if err == 2:
        raise SystemExit("rr_connect err:2 — no free session (session table full).")
    if err:
        raise SystemExit(f"rr_connect err:{err} — login error.")
    if body.get("isEmulated"):
        raise SystemExit("Endpoint reports isEmulated:true — refusing (not real RRF).")
    if not body.get("apiLevel"):
        raise SystemExit("apiLevel absent/0 — board is pre-Object-Model (RRF < 3.0).")
    # sessionKey (RRF 3.5-b4+) must ride on every later rr_* request as X-Session-Key.
    key = body.get("sessionKey")
    return {"X-Session-Key": str(key)} if key is not None else {}


def read_model(base, headers, key=None, flags="d99fn"):
    """GET /rr_model. No key => the live subset; key=state|job|heat|tools => that subtree."""
    params = {"flags": flags}
    if key:
        params["key"] = key
    r = requests.get(base + "/rr_model", params=params, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("result")


def print_state(base, headers):
    state = read_model(base, headers, key="state", flags="d99vno")
    job = read_model(base, headers, key="job", flags="d99vno")
    status = (state or {}).get("status")
    print(f"status       : {status!r}  (RRF prints as 'processing', not 'printing')")
    print(f"currentTool  : {(state or {}).get('currentTool')}  (-1 = none)")
    # Progress is a FILE-BYTE fraction, not time — derive it, and guard null/zero.
    f = (job or {}).get("file") or {}
    pos, size = (job or {}).get("filePosition"), f.get("size")
    if pos is not None and size:
        print(f"progress     : {100.0 * pos / size:.1f}%  (filePosition/file.size)")
    # Timing is seconds-native; prefer slicer -> filament -> file.
    tl = (job or {}).get("timesLeft") or {}
    eta = tl.get("slicer") or tl.get("filament") or tl.get("file")
    if eta is not None:
        print(f"timeLeft     : {eta} s  (job.timesLeft; seconds)")


def upload_and_launch(base, headers, local_path):
    """Upload a raw .gcode body, then M32 to select+start. GATED behind --print."""
    name = "0:/gcodes/example.gcode"  # RRF volume notation; read directories.gCodes to be exact
    with open(local_path, "rb") as fh:
        data = fh.read()
    r = requests.post(
        base + "/rr_upload",
        params={"name": name},  # optional &crc32=<lowercase-hex, no 0x> for integrity
        data=data,
        headers=headers,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    if r.json().get("err"):
        raise SystemExit("rr_upload returned err != 0 (CRC/write failure).")
    # Launch is a SEPARATE GCode: M32 = select file AND start SD print (one round-trip).
    g = requests.get(
        base + "/rr_gcode",
        params={"gcode": f'M32 "{name}"'},
        headers=headers,
        timeout=TIMEOUT,
    )
    g.raise_for_status()
    print(f"launched     : M32 {name}  bufferSpace={g.json().get('bufferSpace')}")
    # No synchronous "print started" ack — confirm by polling state.status -> processing.


def main(argv):
    host = (argv[1] if len(argv) > 1 else os.environ.get("DUET_HOST", "")).strip()
    # "reprap" is RepRapFirmware's public factory-default password (a documented default,
    # not a secret). Override it via the DUET_PASSWORD env var if you set your own.
    password = os.environ.get("DUET_PASSWORD", "reprap")
    if not host:
        print(__doc__)
        print("Usage: DUET_HOST=<host> [DUET_PASSWORD=<pw>] python client.py [host] [--print FILE]")
        return 2
    base = host if host.startswith("http") else "http://" + host

    headers = connect(base, password)
    try:
        print_state(base, headers)
        if "--print" in argv:
            f = argv[argv.index("--print") + 1]
            upload_and_launch(base, headers, f)
    finally:
        # Release the session slot; the key is ephemeral (in-memory only).
        try:
            requests.get(base + "/rr_disconnect", headers=headers, timeout=TIMEOUT)
        except requests.RequestException:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
