# Quickstart — talk to a printer over LAN

Your first integration in five steps. The orchard's papers are *reference*; this is the *on-ramp* — it walks the shape
every LAN client shares, then hands you off to the paper for your printer. The example clients referenced here live in
[`examples/`](examples/README.md).

> **You need:** a printer on your LAN with its LAN/developer mode enabled, its IP, and (for most brands) a per-device
> access code you read from *your own* printer's screen. The orchard never ships credentials — see
> [`SECURITY-MODEL.md`](SECURITY-MODEL.md).

---

## 1. Identify the paradigm — fingerprint, don't guess

Route by the **live service you observe**, never by the model name (Creality and Elegoo each span three stacks). The
[Comparison matrix](COMPARISON.md#pick-your-paradigm) has the full fingerprint table; the short version:

| You observe… | It's… | Start at |
|--------------|-------|----------|
| `:7125` answering JSON-RPC 2.0 | Moonraker / Klipper (or a vendor fork) | [`klipper-moonraker.md`](protocols/klipper-moonraker.md) |
| MQTT `:8883`, user `bblp` + access code | Bambu Lab | [`bambu.md`](protocols/bambu.md) |
| `/api/v1/status` over HTTP Digest (user `maker`) | PrusaLink | [`prusalink.md`](protocols/prusalink.md) |
| `/api/*` + `X-Api-Key` + a SockJS channel | OctoPrint | [`octoprint.md`](protocols/octoprint.md) |
| a USB serial port answering `M115` | Marlin over USB | [`marlin-serial.md`](protocols/marlin-serial.md) |

Fingerprint on connect, and **re-fingerprint on reconnect** — a vendor can change stack across a firmware update.

## 2. Pick the matching example client

Each example is a minimal, dependency-light reference for one paradigm:

- [`examples/moonraker`](examples/moonraker) — HTTP + WebSocket JSON-RPC (Klipper/Moonraker, Snapmaker, many forks)
- [`examples/bambu`](examples/bambu) — MQTT-over-TLS + FTPS
- [`examples/prusalink`](examples/prusalink) — poll-only HTTP + Digest auth
- [`examples/octoprint`](examples/octoprint) — REST + SockJS
- [`examples/duet-rrf`](examples/duet-rrf) — RRF `rr_*` / session key
- [`examples/sdcp`](examples/sdcp) — Elegoo SDCP over WebSocket

Credentials come from the environment, never hardcoded (e.g. `MOONRAKER_HOST`, `BAMBU_ACCESS_CODE`).

## 3. Connect and read state

Every client does the same three things: **connect → read a snapshot → subscribe/poll for changes**. Map the native
state to the [neutral lifecycle](MODEL.md#1-lifecycle-state) (`standby`/`printing`/`paused`/`complete`/`error`/…) using
the vendor's [`state-enum.json`](schemas/README.md) — don't hand-copy the mapping. Normalize time to **seconds**,
filament to **grams**, and progress to a **`0.0`–`1.0` fraction** at this edge (see [`MODEL.md`](MODEL.md)).

## 4. Launch a print — and confirm by the status stream

The one rule that bites everyone: **`upload != launch`**. On every family the file transfer and the print-start are
**separate operations, often on separate ports**, and the order is load-bearing (see
[`connection-flows.md`](patterns/connection-flows.md)).

1. **Upload** the sliced file on the file channel (HTTP multipart / FTPS / raw `PUT`).
2. **Start** with the launch command on the control channel.
3. **Confirm** by watching the status stream transition into a printing state — **almost no family returns a synchronous
   "print started" ack**, so never trust the command's response.

Because control drives a hot, moving machine, gate every write behind an explicit "enable writes" in your client.

## 5. Handle faults

A job that returned to idle is **not** proof of success — several stacks read a *failed* job as plain `standby` until
you also read the fault channel. Wire in [`faults-and-errors.md`](patterns/faults-and-errors.md) before you ship:
surface `is_fault` / `needs_user` distinctly, and route emergency-stop through the **structured** path, never a queued
`M112`.

---

## Where to go next

- The **paper for your printer** in [`protocols/`](protocols/README.md) — the field-level truth.
- [`MODEL.md`](MODEL.md) — the neutral shape your adapter maps into (so the rest of your app is written once).
- The [patterns](patterns/README.md) — the cross-cutting traps (timing/units, feeders, discovery, launch, faults).
- Your printer not covered? [`METHOD.md`](METHOD.md) shows how to research it, and PRs are welcome.
