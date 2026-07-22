#!/usr/bin/env python3
# Reference example — facts-only, no warranty; supply your own printer + credentials.
"""Moonraker / Klipper reference client (HTTP :7125 + WebSocket JSON-RPC).

Demonstrates the "Moonraker" paradigm: a JSON-RPC 2.0 API (HTTP + WebSocket) that
fronts Klipper on port 7125. Reads live printer state one-shot over HTTP, then shows
the WebSocket subscribe path (full snapshot + sparse deltas), and — behind an explicit
flag — the upload + print-start calls.

Families this covers (any Moonraker host speaks this): generic upstream Klipper
(Voron / RatRig / Sovol SV08 …), Elegoo Neptune 4 forks, Snapmaker U1 (behind its
:8100 auth-wrapper bootstrap), Qidi, rooted/stock Creality (may use a non-standard
port such as :4408). Probe first, degrade gracefully — there is no fixed schema.

Protocol paper: ../../protocols/klipper-moonraker.md

Dependencies (install only what you use): requests, websocket-client.
    pip install requests websocket-client

SPDX-License-Identifier: MIT
"""
import json
import os
import sys

import requests  # HTTP: info, one-shot query, file upload, print start

# --- config from the environment / argv, never hardcoded --------------------
# MOONRAKER_HOST  host or host:port  (e.g. 192.0.2.10 or 192.0.2.10:4408)
# MOONRAKER_API_KEY  optional; usually unset on a trusted LAN (trusted_clients).
#   Find/create it on YOUR host: Moonraker's UI (Mainsail/Fluidd) settings, or
#   the API-key file in Moonraker's data dir. A key is a mechanism, not a value.

# Objects to read — Moonraker returns only those the printer's config defines.
QUERY_OBJECTS = ["print_stats", "heater_bed", "extruder", "toolhead", "virtual_sdcard"]


def _base(host: str) -> str:
    return host if host.startswith("http") else f"http://{host}"


def _headers() -> dict:
    key = os.environ.get("MOONRAKER_API_KEY")
    return {"X-Api-Key": key} if key else {}


def printer_info(host: str) -> dict:
    """GET /printer/info — answers only when Klippy is connected."""
    r = requests.get(f"{_base(host)}:7125/printer/info", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json().get("result", {})


def query_state(host: str, objects) -> dict:
    """One-shot GET /printer/objects/query?print_stats&heater_bed&... ."""
    qs = "&".join(objects)
    url = f"{_base(host)}:7125/printer/objects/query?{qs}"
    r = requests.get(url, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json().get("result", {}).get("status", {})


def subscribe_ws(host: str, objects, updates=3) -> None:
    """WebSocket live state: subscribe -> full snapshot, then notify_status_update deltas.

    Deltas are sparse (changed fields only); deep-merge them into local state.
    Subscriptions are WS-only and are NOT restored on reconnect — re-subscribe each time.
    """
    from websocket import create_connection  # websocket-client

    ws_host = host.split("://", 1)[-1]
    ws = create_connection(f"ws://{ws_host if ':' in ws_host else ws_host + ':7125'}/websocket")
    try:
        params = {"objects": {name: None for name in objects}}  # None = all fields
        ws.send(json.dumps({"jsonrpc": "2.0", "method": "printer.objects.subscribe",
                            "params": params, "id": 1}))
        seen = 0
        while seen < updates:
            msg = json.loads(ws.recv())
            if msg.get("id") == 1:  # subscribe reply == full initial snapshot
                print("snapshot:", json.dumps(msg["result"]["status"], indent=2))
            elif msg.get("method") == "notify_status_update":
                delta, eventtime = msg["params"]  # [ {obj: {changed fields}}, eventtime ]
                print(f"delta @ {eventtime}:", json.dumps(delta))
                seen += 1
    finally:
        ws.close()


def upload_and_print(host: str, path: str, start: bool) -> dict:
    """Multipart POST /server/files/upload (field 'file'); optional print=true.

    Alternatively upload with print=false then POST /printer/print/start?filename=<name>.
    This DRIVES A HOT, MOVING MACHINE — only runs when you pass --print explicitly.
    """
    name = os.path.basename(path)
    with open(path, "rb") as fh:
        files = {"file": (name, fh)}
        data = {"print": "true"} if start else {}
        r = requests.post(f"{_base(host)}:7125/server/files/upload",
                          headers=_headers(), files=files, data=data, timeout=60)
    r.raise_for_status()
    return r.json()


def _usage() -> None:
    print(__doc__)
    print("Usage:")
    print("  MOONRAKER_HOST=192.0.2.10 python client.py            # info + one-shot state")
    print("  MOONRAKER_HOST=192.0.2.10 python client.py --watch    # live WS deltas")
    print("  MOONRAKER_HOST=192.0.2.10 python client.py --print example.gcode  # upload+START (hot!)")
    print("\nEnv: MOONRAKER_HOST (required, host or host:port), MOONRAKER_API_KEY (optional).")


if __name__ == "__main__":
    host = os.environ.get("MOONRAKER_HOST")
    if not host:
        _usage()
        sys.exit(1)

    args = sys.argv[1:]
    try:
        print("printer.info:", json.dumps(printer_info(host), indent=2))
        print("\nstate:", json.dumps(query_state(host, QUERY_OBJECTS), indent=2))

        if "--watch" in args:
            print("\n--- live subscription ---")
            subscribe_ws(host, QUERY_OBJECTS)

        if "--print" in args:
            i = args.index("--print")
            if i + 1 >= len(args):
                print("--print needs a file path", file=sys.stderr)
                sys.exit(2)
            print("\nupload+start:", json.dumps(upload_and_print(host, args[i + 1], True)))
    except requests.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        sys.exit(3)
    except requests.ConnectionError as e:
        print(f"could not reach {host}:7125 — {e}", file=sys.stderr)
        sys.exit(4)
