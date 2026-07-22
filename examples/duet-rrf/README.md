# Duet / RepRapFirmware — reference client (standalone `rr_*`)

A minimal, dependency-light example of the **Duet3D / RepRapFirmware** LAN paradigm:
the **standalone** poll-only `rr_*` HTTP API a Duet board serves on port `:80`. It opens
an optional password session, reads the RRF **Object Model**, prints live state, and
(behind a flag) shows the upload-then-launch print flow.

> Reference example — facts-only, no warranty. Supply your **own** printer and
> credentials. Interoperability with a printer you own; documented from Duet's own
> open-source documentation and connector libraries.

**Confidence: 🟡 source-read** — grounded in the official Duet3D docs, the RRF wiki, and
the LGPL `@duet3d/connectors` / `@duet3d/objectmodel` libraries. No Duet was on the bench.

## Families covered

Duet 2 / Duet 3 boards (WiFi / Ethernet / Mini / 6HC / 6XD …) and other RepRapFirmware
**3.0+** machines running in **standalone** mode — including multi-tool builds
(E3D ToolChanger, Jubilee). RRF < 3.0 has no Object Model and is refused.

The **SBC/DSF** variant (a Duet 3 paired with a Raspberry Pi running Duet Software
Framework) speaks a different dialect — `GET /machine/status`, `POST /machine/code`,
`PUT /machine/file/{path}`, and one push WebSocket at `/machine`. It is noted in the
script's comments but **not implemented here**.

## What it demonstrates

- **Session:** `GET /rr_connect?password=…&sessionKey=yes` → an `X-Session-Key` header on
  every later request. `err:1` = bad password, `err:2` = no free session.
- **Read state:** `GET /rr_model` (no key = the live subset; `key=state|job|heat|tools`
  for a subtree). Lifecycle is `state.status` — the printing value is **`processing`**,
  not `printing`.
- **Progress:** derived as `job.filePosition / job.file.size` — a **file-byte** fraction,
  not time. ETA comes from `job.timesLeft.*` (seconds).
- **Upload + launch (behind `--print`):** raw-body `POST /rr_upload?name=0:/gcodes/…`,
  then `GET /rr_gcode?gcode=M32 "…"` to select **and** start. Upload ≠ launch.

## Requirements

- Python 3.9+
- `requests`  (`pip install requests`)

## Environment / arguments

Credentials are read at runtime — **never** hardcoded.

| Variable / arg | Meaning | How you get it |
|---|---|---|
| `DUET_HOST` (or `argv[1]`) | host or IP of your board | your own network (e.g. `duet.local` or an IP) |
| `DUET_PASSWORD` | machine password | the one you set with `M551` in `config.g`; **unset ⇒ default `reprap`**, and an unset password auto-creates a session |
| `--print FILE` | optional: upload `FILE` and start it | — |

The password is a **mechanism you supply**, found on/configured on your own board — this
repo ships no credential values.

## Run

```sh
export DUET_HOST=192.0.2.50          # your board's host/IP (example uses TEST-NET-1)
export DUET_PASSWORD=reprap          # omit if you never set one
python client.py

# read-only is the default; to upload + START a print (this MOVES the machine):
python client.py 192.0.2.50 --print ./example.gcode
```

Missing host/env prints usage and exits.

## Paper

Full protocol reference: [`../../protocols/duet.md`](../../protocols/duet.md).
