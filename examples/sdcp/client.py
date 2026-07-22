#!/usr/bin/env python3
"""Elegoo SDCP reference client — nested-envelope + RequestID over WebSocket :3030.

Demonstrates the SDCP LAN control paradigm used by the Elegoo Centauri Carbon 1
(the same envelope, discovery, and integer `Cmd` codes the vendor's own first-party
LAN SDK uses). It:
  * discovers the printer via a UDP broadcast (optional), learning its MainboardID,
  * opens ws://<host>:3030/websocket,
  * builds the nested request envelope and sends `Cmd 0` (status),
  * correlates the reply by the echoed RequestID and prints the live state.

SDCP has NO authentication at all (LAN-trust) — there is no credential to supply,
only a host and the printer's MainboardID (which discovery returns for you).

Families covered: Elegoo Centauri Carbon 1 (SDCP). NOT the Neptune/OrangeStorm
(Moonraker :7125) or Centauri Carbon 2 (MQTT :1883) paths — those are different stacks.

Protocol paper: ../../protocols/elegoo.md
Envelope schema: ../../schemas/elegoo/sdcp-envelope.json

Reference example — facts-only, no warranty; supply your own printer + credentials.
SPDX-License-Identifier: MIT
"""

# Reference example — facts-only, no warranty; supply your own printer + credentials.
# Requires: websocket-client  (pip install websocket-client)

import json
import os
import socket
import sys
import time
import uuid

DISCOVERY_PORT = 3000  # printers listen for the M99999 broadcast here
WS_PORT = 3030
STATUS = 0      # Cmd 0 — force a status refresh (reply on sdcp/status)
ATTRIBUTES = 1  # Cmd 1 — static identity/capabilities
# Write codes exist (128 start, 129 pause, 130 stop, 131 resume) but are NOT sent here:
# on SDCP an unrecognized or incomplete command can crash the printer daemon and kill an
# active print. See the paper's "Quirks & gotchas" before emitting any write.


def discover(timeout=3.0):
    """Broadcast the 6-byte 'M99999' probe to :3000 and yield each printer's info dict."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)
    sock.sendto(b"M99999", ("255.255.255.255", DISCOVERY_PORT))
    found = []
    try:
        while True:
            data, _ = sock.recvfrom(8192)
            found.append(json.loads(data.decode("utf-8", "replace")))
    except socket.timeout:
        pass
    finally:
        sock.close()
    return found


def build_envelope(mainboard_id, cmd, params=None):
    """Build the nested SDCP request frame. Correlation key is Data.RequestID."""
    request_id = uuid.uuid4().hex
    frame = {
        "Id": uuid.uuid4().hex,  # a per-connection machine UUID; any stable id works
        "Topic": f"sdcp/request/{mainboard_id}",
        "Data": {
            "Cmd": cmd,
            "Data": params or {},
            "RequestID": request_id,
            "MainboardID": mainboard_id,
            "TimeStamp": int(time.time() * 1000),  # Unix MILLISECONDS (tick fields are seconds!)
            "From": 1,  # LAN client identifies as WEB_PC
        },
    }
    return frame, request_id


def request(ws, mainboard_id, cmd, params=None, timeout=8.0):
    """Send one command and return the first frame whose Data.RequestID matches."""
    frame, request_id = build_envelope(mainboard_id, cmd, params)
    ws.send(json.dumps(frame))
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            raw = ws.recv()
        except Exception:
            break
        if not raw:
            continue
        msg = json.loads(raw)
        if msg.get("Data", {}).get("RequestID") == request_id:
            return msg
        # else: an unsolicited push (status/notice) for another RequestID — ignore and keep reading
    return None


def main(argv):
    host = os.environ.get("SDCP_HOST") or (argv[1] if len(argv) > 1 else None)
    mainboard_id = os.environ.get("SDCP_MAINBOARD_ID") or (argv[2] if len(argv) > 2 else None)

    if not host:
        print("Discovering on the local network (UDP broadcast to :3000)...", file=sys.stderr)
        for info in discover():
            print(
                f"  {info.get('MachineName', '?')} @ {info.get('MainboardIP', '?')} "
                f"MainboardID={info.get('MainboardID', '?')}",
                file=sys.stderr,
            )
        print(
            "\nUsage: SDCP_HOST=192.0.2.10 SDCP_MAINBOARD_ID=<id> python client.py\n"
            "   or: python client.py <host> <mainboard_id>\n"
            "Host and MainboardID come from discovery above (SDCP has no auth).",
            file=sys.stderr,
        )
        return 2

    # websocket-client is imported lazily so --discover-only works without it installed.
    from websocket import create_connection  # type: ignore

    ws = create_connection(f"ws://{host}:{WS_PORT}/websocket", timeout=10)
    try:
        if not mainboard_id:
            # Without a MainboardID we can still read the unsolicited status push, but a
            # correlated request needs the right routing key — bail with guidance.
            print(
                "No MainboardID given. Run discovery (omit args) to learn it — a wrong "
                "MainboardID is a silent no-op, not an error.",
                file=sys.stderr,
            )
            return 2

        reply = request(ws, mainboard_id, STATUS)
        if reply is None:
            print("No matching reply (check host/MainboardID and the 5-connection cap).", file=sys.stderr)
            return 1
        print(json.dumps(reply.get("Data", {}).get("Data", reply), indent=2))
    finally:
        ws.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
