# OctoPrint (host controller) — reference client

A minimal, dependency-light reference client for the **OctoPrint host-controller paradigm**:
a client talks to an OctoPrint instance's documented **HTTP REST API** and treats the printer
firmware underneath as metadata. It reads live state (identity, temps/state, job progress) and
optionally demonstrates the upload + launch calls.

> **Reference example — facts-only, no warranty; supply your own printer + credentials.**
> Illustrative starting point for integrators, not a product. Confidence: **🟡 source-read**
> (validatable hardware-free via the official `octoprint/octoprint` Docker image + bundled
> Virtual Printer). See the protocol paper: [`../../protocols/octoprint.md`](../../protocols/octoprint.md).

## What it demonstrates

- **Auth:** a single API key sent as the `X-Api-Key:` header.
- **Read (poll backstop):** `GET /api/version` (identity), `GET /api/printer` (temps + `state.flags`),
  `GET /api/job` (progress). `409` from `/api/printer` is treated as a valid "not operational" signal,
  not a transport error.
- **Upload + launch:** multipart `POST /api/files/local` (form part `file`), then `POST /api/job
  {"command":"start"}` — guarded behind a `--print` flag because printing drives a hot, moving machine.
- **Live push (noted, not implemented):** OctoPrint's live state rides **SockJS** at `/sockjs/` — its own
  handshake + framing, not a raw WebSocket. This example uses REST polling for minimality; see the paper's
  *Reading state* section for the SockJS handshake mechanism.

## Families covered

Any **USB/serial FDM printer fronted by an OctoPrint host**. OctoPrint is a host controller, so the
machine underneath is secondary metadata. From **OctoPrint 2.0** the same `/api/*` + SockJS surface also
fronts the Serial / Moonraker / Bambu connectors, so this client stays 2.0-ready.

## Credentials (mechanism — nothing is bundled)

You supply your own **API key**, obtained from **your own OctoPrint install**:

- In OctoPrint, open **Settings → Application Keys** and generate/approve a key for this app, **or** use
  your per-user API key from **Settings → API**. The key is app/user-specific and permission-scoped
  (a `STATUS`-only key can poll but not write).
- The script only ever reads this key from the environment or argv — it contains no key and prints none.

## Environment / arguments

| Variable | Meaning | Example |
|---|---|---|
| `OCTOPRINT_HOST` | `host[:port]` or a full URL (default port 5000, plain http) | `192.0.2.10:5000` |
| `OCTOPRINT_API_KEY` | your API key (see above) | *(read from your instance)* |

Host and key may also be passed positionally: `python client.py <host> <api_key>`.

## Requirements

```
requests
```

Install with `pip install requests` (Python 3.9+).

## Run

Read live state:

```
OCTOPRINT_HOST=192.0.2.10:5000 OCTOPRINT_API_KEY=... python client.py
```

Upload a file and hold (select, but do not start):

```
OCTOPRINT_HOST=192.0.2.10:5000 OCTOPRINT_API_KEY=... python client.py upload example.gcode
```

Upload and then **start a print** (opt-in — this moves the machine):

```
OCTOPRINT_HOST=192.0.2.10:5000 OCTOPRINT_API_KEY=... python client.py upload example.gcode --print
```

Missing host/key prints usage and exits.

## Gotchas the code encodes

- **`progress.completion` is a fraction `0.0–1.0`** (×100 for a percent bar) **and is file-byte position,
  not time** — for "remaining" the code surfaces `progress.printTimeLeft` (seconds), qualified by
  `printTimeLeftOrigin`.
- **`409` is a signal, not a fault** — `/api/printer` `409` = not operational; upload `409` = would interrupt
  an active print / SD busy; `415` = extension not an accepted machinecode type.
- **Read back `effectiveSelect` / `effectivePrint`** — a `print=true` the printer couldn't honor comes back
  `false`. Control POSTs return `204` with an empty body; read the effect from a follow-up `GET`.
- **Security floor:** upload endpoints should target **OctoPrint ≥ 1.11.8** and send only the documented
  public form fields.

## Confidence & license

🟡 source-read (official REST API docs + AGPL server source, clean-room; no vendor code copied).
Example code is **MIT**. Protocol paper: [`../../protocols/octoprint.md`](../../protocols/octoprint.md).
