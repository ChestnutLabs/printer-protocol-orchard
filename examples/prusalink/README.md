# PrusaLink reference client

A minimal, dependency-light example of the **PrusaLink paradigm**: a Prusa host
controller exposing a single plain-HTTP REST API on the LAN, authenticated with
**HTTP Digest**, and **poll-only** — there is no MQTT, WebSocket, SSE, or push
channel, so all live state comes from polling. It reads identity + live state and
(behind an opt-in flag) demonstrates the raw-`PUT` upload and one-shot print
launch.

**Confidence:** 🟡 source-read (from Prusa's own published OpenAPI 3.0.1 spec;
hardware-unvalidated). This is illustrative starting-point code, not a product.

> Reference example — facts-only, no warranty. Supply your own printer and
> credentials. It talks only to a device you own on your own LAN.

## Families covered

Prusa hosts running PrusaLink:

- **Buddy firmware:** MK4 / MK4S, MK3.9, MINI / MINI+, XL, Core One
- **Raspberry Pi `Prusa-Link` app:** MK3S+
- **SLA:** SL1 / SL1S

The script targets the modern `/api/v1` surface and falls back to the legacy
OctoPrint-shaped tier (`/api/version`, `/api/printer`, `/api/job`) on older
firmware that lacks `/api/v1`.

## What it demonstrates

- HTTP **Digest** auth against `http://<host>` (username `maker` by default).
- Reading identity: `GET /api/v1/info`.
- **Poll-only** live state: `GET /api/v1/status` and `GET /api/v1/job`
  (`/api/v1/job` returns `204 No Content` when idle — surfaced as `null`).
- Legacy fallback: `GET /api/version` + `/api/printer` + `/api/job`.
- Optional file **upload** via raw `PUT /api/v1/files/{storage}/{path}` with the
  `?0`/`?1` structured-header booleans, and one-shot print launch via
  `Print-After-Upload: ?1` (guarded behind `--upload ... --start`).

It does **not** attempt temperature / fan / speed setpoints or emergency-stop —
the documented v1 API exposes no such endpoints; that surface is read-only.

## Requirements

- Python 3.9+
- [`requests`](https://pypi.org/project/requests/) (its bundled `HTTPDigestAuth`
  is the only auth dependency)

```
pip install requests
```

## Credentials (where to find them on your own printer)

The example never hardcodes anything — you supply your host and password at
runtime:

| Variable | Meaning | How to obtain |
|---|---|---|
| `PRUSALINK_HOST` | base URL, e.g. `http://192.0.2.10` (or pass as `argv[1]`) | the printer's LAN IP (shown on the printer's network screen) |
| `PRUSALINK_PASSWORD` | the printer's LAN password (**required**) | read it from **PrusaLink settings / the printer's own screen** — it is set on the device, never bundled |
| `PRUSALINK_USER` | Digest username (optional) | defaults to the fixed literal `maker` |

The password is a **mechanism, not a value**: this repo tells you *where the
owner reads it*, never what it is.

## Running it

Read live state (default):

```
PRUSALINK_HOST=http://192.0.2.10 PRUSALINK_PASSWORD=your-lan-password \
    python client.py
```

Upload a file **without** starting a print (safe):

```
PRUSALINK_HOST=http://192.0.2.10 PRUSALINK_PASSWORD=your-lan-password \
    python client.py --upload usb example.gcode ./example.gcode
```

Upload **and** start a print (this launches a job on your printer — opt in
deliberately):

```
PRUSALINK_HOST=http://192.0.2.10 PRUSALINK_PASSWORD=your-lan-password \
    python client.py --upload usb example.gcode ./example.gcode --start
```

The `{storage}` root (e.g. `usb`, or a local/`sdcard` root) is per-model —
resolve it from `GET /api/v1/storage` rather than assuming. After a `--start`
upload there is no synchronous ack; confirm by polling status/job for
`state=PRINTING`.

## Notes / gotchas (see the paper)

- **Poll-only** — diff successive `/api/v1/status` snapshots into events; there
  is no notification channel.
- **Boolean headers are `?0`/`?1`**, not `true`/`1` (`Print-After-Upload`,
  `Overwrite`, `Force`).
- **`axis_*` is absent while moving** — treat missing as "unknown", not `0`.
- **`ATTENTION`** = waiting on a human (runout, MMU swap, "remove print"); map it
  to needs-user, not a plain error.

## Reference

Full protocol facts, field/enum maps, state normalization, and open gaps:
[`../../protocols/prusalink.md`](../../protocols/prusalink.md).

Licensed MIT (this example) / CC BY 4.0 (docs). Nominative vendor names only; no
affiliation with or endorsement by Prusa Research.
