#!/usr/bin/env python3
# Reference example — facts-only, no warranty; supply your own printer + credentials.
"""Bambu Lab LAN reference client (MQTT over TLS).

Demonstrates the "MQTT over TLS, LAN mode" paradigm: connect to a Bambu Lab
printer on your own network, subscribe to its report topic, request a full
status push, and print the first report received.

Covers the Bambu Lab families: X1 / P1 / A1 / P2 / X2 / H2. (The optional
FTPS upload + `project_file` print-launch transport is described but NOT
performed here — it would start a physical print; see the paper.)

Paradigm/paper: ../../protocols/bambu.md
License: MIT.
"""

import json
import os
import ssl
import sys
import time

import paho.mqtt.client as mqtt  # pip install paho-mqtt


def build_tls_context() -> ssl.SSLContext:
    """TLS for a self-signed LAN device.

    The printer presents a self-signed cert (CN = serial, no SAN). This is the
    normal posture for a local device you own — not a security bypass. For this
    minimal LAN example we skip verification.

    PRODUCTION MUST DO BETTER: pin the certificate on first use (snapshot the
    leaf on the first connect, then require it to match — trust-on-first-use),
    or verify against Bambu's published device-CA with SNI set to the serial.
    Verify-off here only keeps the example short and dependency-light.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def make_client(serial: str, access_code: str) -> mqtt.Client:
    # A unique client_id per (re)connect avoids leaving zombie sessions on the
    # broker. MQTT v3.1.1, user "bblp", password = the printer's access code.
    client_id = f"orchard-example-{serial}-{int(time.time())}"
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    client.username_pw_set("bblp", access_code)
    client.tls_set_context(build_tls_context())
    # Raise the inflight ceiling well past paho's default of 20 — the broker's
    # PUBACK matching is racy against a low ceiling and wedges after ~16-20
    # cumulative commands.
    client.max_inflight_messages_set(1000)
    return client


def run(host: str, serial: str, access_code: str) -> None:
    report_topic = f"device/{serial}/report"
    request_topic = f"device/{serial}/request"

    def on_connect(client, userdata, flags, rc):
        if rc != 0:
            print(f"connect failed rc={rc}", file=sys.stderr)
            return
        print(f"connected; subscribing {report_topic}")
        client.subscribe(report_topic, qos=1)
        # Force a full status snapshot; deltas follow on the same topic.
        # NOTE: the serial is case-sensitive everywhere (topic, SNI, cert CN).
        # A miscased serial connects fine but yields ZERO reports.
        client.publish(request_topic, json.dumps({"pushing": {"command": "pushall"}}), qos=1)

    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload)
        # Reports are flat, category-keyed JSON: print / pushing / info / system / ...
        # Reminder: mc_remaining_time and other status times are in MINUTES.
        print("first report:")
        print(json.dumps(payload, indent=2, sort_keys=True))
        client.disconnect()

    client = make_client(serial, access_code)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, 8883, keepalive=30)
    client.loop_forever()


USAGE = """\
Bambu Lab LAN reference client (MQTT over TLS) — reads live status.

Usage:
  BAMBU_HOST=192.0.2.10 BAMBU_SERIAL=SN-EXAMPLE BAMBU_ACCESS_CODE=... python client.py
  python client.py <host> <serial> <access_code>

Env vars (or positional args):
  BAMBU_HOST         printer IP on your LAN (enable LAN mode in the printer UI)
  BAMBU_SERIAL       the printer serial (case-sensitive!)
  BAMBU_ACCESS_CODE  the LAN access code shown on the printer's own screen

To start a print you would FTPS-upload the .3mf to the SD-card root (:990,
implicit TLS) then MQTT-publish a `project_file` command — omitted here so this
example never starts a physical print. See ../../protocols/bambu.md.
"""


if __name__ == "__main__":
    host = os.environ.get("BAMBU_HOST")
    serial = os.environ.get("BAMBU_SERIAL")
    access_code = os.environ.get("BAMBU_ACCESS_CODE")
    if len(sys.argv) == 4:
        host, serial, access_code = sys.argv[1], sys.argv[2], sys.argv[3]
    if not (host and serial and access_code):
        sys.stderr.write(USAGE)
        sys.exit(2)
    run(host, serial, access_code)
