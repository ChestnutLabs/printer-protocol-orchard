# Cross-Vendor Comparison Matrix

One screen for the whole landscape. [`COVERAGE.md`](COVERAGE.md) groups families by *paradigm* (so you learn a stack
once and cover a cluster); this page is the orthogonal view — **every family in one flat table**, column-by-column, so
you can eyeball how any two protocols differ on transport, discovery, auth, push/poll, progress semantics, and
multi-material.

This is a **distilled cross-index, not the source of truth.** Every cell is a compression of a per-family paper in
[`protocols/`](protocols/README.md) — when a cell and a paper disagree, **the paper wins.** Cells are deliberately
terse; follow the family link for the wire strings, gotchas, and confidence gaps. `—` means the paper documents no such
facet (not "unknown"); "see paper" means the answer is real but too branchy for a cell.

Confidence tags: 🟢 hardware-validated · 🟡 source-read · 🔵 community/RE · ⚪ inferred. Only **Anycubic** and **Bambu**
carry hardware validation; every other family is 🟡 source-read (wire-shape from the vendor's own slicer/SDK/docs, not
yet confirmed on a bench). Trust the **per-paper** tags on individual facts over this summary column.

> **Machine-readable:** a structured mirror of this matrix — per-family transport/ports/auth/model/progress/feeder/confidence
> plus the fingerprint routing — lives at [`data/comparison.json`](data/comparison.json), regenerated from this page.

## Main matrix

| Family | Paradigm | Transport (proto:port) | Discovery | Auth / credential | Push vs Poll | Progress semantics | Multi-material | Conf. |
|--------|----------|------------------------|-----------|-------------------|--------------|--------------------|----------------|-------|
| [Anycubic](protocols/anycubic.md) | Proprietary LAN | MQTT/TLS `:9883` + HTTP `:18910` (identity/upload) | manual IP; `GET :18910/info` (sleeping → HTTP-silent) | slicer mTLS client cert + MQTT creds **derived** from `/info` | poll-hybrid (idle pushes nothing ~48 s; active auto-pushes) | `%` + reported times | ACE per-slot (`multiColorBox`) + external spool | 🟢 |
| [Bambu](protocols/bambu.md) | Proprietary LAN | MQTT/TLS `:8883` + implicit FTPS `:990` | SSDP `:2021`; manual IP | user `bblp`, password = **access code** off the printer screen | push (`pushall` snapshot → live deltas); **no command ack** | `%` + time | AMS (full/Lite/high-temp) per-slot + external | 🟢 / 🟡 |
| [Creality (stock OS)](protocols/creality.md) | Proprietary LAN | plain WS `ws://:9999` + HTTP `:80/upload` | manual IP; vendor UDP broadcast; `GET /info` | **none** on LAN socket (LAN-trust) | push-hybrid (unsolicited state merged; `get` poll backstop) | `%` — **treat as file-byte** (Klipper under the hood) | CFS per-slot, rich (per-slot % + RFID + dry-box) | 🟡 |
| [Elegoo](protocols/elegoo.md) | Mixed (3 stacks) | Moonraker `:7125` / SDCP WS `:3030` / MQTT `:1883` + HTTP `:80` | manual; SSDP·mDNS / UDP `:3000` / UDP `:52700` | none / none (LAN-trust) / **access code** (CC2) | subscribe / passive push + poll floor / push + `1002` poll | see paper (per-backend) | CANVAS 4-slot (material/color/temp; **no qty, no RFID UID**) | 🟡 / 🔵 |
| [Klipper / Moonraker](protocols/klipper-moonraker.md) | Moonraker | HTTP + WS JSON-RPC `:7125` | manual IP baseline; optional mDNS `_moonraker._tcp` / SSDP | often **none** (`trusted_clients`); else API key (`X-Api-Key`) / JWT | subscribe (WS): full snapshot → sparse deltas; or one-shot query | **file-byte** position (not time) | **none native** — a *software provider* (Happy Hare / AFC) layers it | 🟡 |
| [Snapmaker U1](protocols/snapmaker.md) | Moonraker + wrapper | Moonraker `:7125` + HTTP `:8100/api` (pair/orchestrate) | manual IP; fingerprint by probing `:8100/api` | pairing: `authCode` (presence) + `accessCode` (session); `link_mode` lan/wan | subscribe (WS) + poll fallback | **file-byte**; time in **seconds** | **toolchanger** (filament→tool map), not a feeder | 🟡 |
| [Duet3D / RRF](protocols/duet.md) | Object-model | HTTP `:80` — standalone `rr_*` **or** SBC/DSF `/machine/*` REST + 1 WS | manual host/IP; `<name>.local` mDNS/NetBIOS where honoured | machine **password** → session → `X-Session-Key` header | standalone **poll-only** (no push); SBC push (full-model → patch) | **file-byte** fraction (state value is `processing`) | **none** (no MMU model) — toolchanger `tools[]` array | 🟡 |
| [OctoPrint](protocols/octoprint.md) | Host controller | HTTP REST `/api/*` `:5000` + SockJS `/sockjs` | mDNS `_octoprint._tcp`; manual IP/URL | one **API key** (`X-Api-Key` / Bearer); Application-Keys handshake | push-primary (SockJS `current`/`history`) + REST poll backstop | fraction `0.0–1.0`, **file-byte** (not time) | **none in core** — exposes multi-*tool*; feeders are plugins | 🟡 |
| [PrusaLink](protocols/prusalink.md) | Host controller | HTTP `:80` only — **no push channel** | manual IP; mDNS advertised (service type unconfirmed); `GET /api/v1/info` | **HTTP Digest** (user `maker`); legacy `X-Api-Key` tier (off by default) | **poll-only** (`GET /api/v1/status`) | `job.progress` **time-based**; seconds | **presence only** (`info.mmu` bare boolean) | 🟡 |
| [FlashForge](protocols/flashforge.md) | Proprietary LAN | newer: pub/sub SDK (closed DLL, MQTT-shaped) / legacy: raw-TCP G-code `:8899` | newer: UDP broadcast (per-device port); legacy: manual IP → `:8899` | newer: per-device **`checkCode`** (screen); legacy: `~M601` handshake, no code | newer: subscribe + query; legacy: poll (`~M119`/`~M105`/`~M27`) | see paper (Klipper inside newer; SD-byte on legacy) | Material Station 4-spool (AD5X, newer path only) | 🟡 / 🔵 |
| [Marlin (USB serial)](protocols/marlin-serial.md) | USB serial | USB-CDC virtual serial (`COMx` / `ttyUSB*` / `ttyACM*`); baud autodetect | **none** (OS port enum + `M115` probe); VID/PID = UART chip, not printer | **none** — physical access *is* the authorization | **poll-only** (`M105`/`M114`/`M27`; `M155` opt-in auto-report) | synthesized from `M27` SD byte position (host-stream: line count) | **none** queryable (`T<n>` lives in the sliced file) | 🟡 |

## Pick your paradigm

Route by the **live service you observe**, never by the model name (several vendors span multiple stacks; Creality and
Elegoo each span three). Fingerprint on connect and re-fingerprint on reconnect.

| You observe… | It's probably… | Paper |
|--------------|----------------|-------|
| Port `:7125` answering JSON-RPC 2.0; `printer.objects.list` works | generic Moonraker / Klipper (or a vendor fork) | [klipper-moonraker.md](protocols/klipper-moonraker.md) |
| A Moonraker host that **also** answers `:8100/api` | Snapmaker U1 (Moonraker behind a pairing wrapper) | [snapmaker.md](protocols/snapmaker.md) |
| MQTT on `:8883` wanting user `bblp` + an access code; SSDP on `:2021` | Bambu Lab | [bambu.md](protocols/bambu.md) |
| MQTT on `:9883` needing a slicer mTLS cert; `GET :18910/info` returns identity | Anycubic (Kobra) | [anycubic.md](protocols/anycubic.md) |
| A plain `ws://:9999` carrying flat `{method,params}`, no auth; `:80/upload` | Creality stock OS | [creality.md](protocols/creality.md) |
| JSON-over-WebSocket on `:3030` with topic strings; UDP discovery on `:3000` | Elegoo SDCP (Centauri Carbon 1) | [elegoo.md](protocols/elegoo.md) |
| A printer running its own MQTT broker on `:1883` + `:80` upload + access code | Elegoo CC2 | [elegoo.md](protocols/elegoo.md) |
| `GET /rr_model` (or `/rr_connect`) returns JSON; `X-Session-Key` after login | Duet / RepRapFirmware (standalone) | [duet.md](protocols/duet.md) |
| A `/machine/*` REST API + one WebSocket at `/machine` | Duet / RRF on an SBC (DSF) | [duet.md](protocols/duet.md) |
| `/api/*` with an `X-Api-Key` header + a SockJS `/sockjs` push channel | OctoPrint host | [octoprint.md](protocols/octoprint.md) |
| `GET /api/v1/status` over HTTP Digest (user `maker`); **no** push channel | PrusaLink host | [prusalink.md](protocols/prusalink.md) |
| A device answering ASCII G-code on raw TCP `:8899` (or UDP SDK discovery + `checkCode`) | FlashForge (legacy / newer) | [flashforge.md](protocols/flashforge.md) |
| A USB serial port that emits a Marlin `start` banner and answers `M115` | Marlin over USB | [marlin-serial.md](protocols/marlin-serial.md) |

## Traps that bite everyone

The same four mistakes recur across families — each has a cross-cutting pattern write-up:

- **Time units drift (minutes vs seconds vs milliseconds).** Different fields carry different units; a single slip
  turns an 11-minute print into 112 hours. Normalize to integer seconds at the adapter edge.
  → [`patterns/timing-normalization.md`](patterns/timing-normalization.md)
- **Progress is file-byte position, not time.** Most Klipper/Moonraker-descended and object-model stacks report a
  byte fraction (Klipper, Creality, Duet, OctoPrint, Snapmaker); a few are genuinely time-based (PrusaLink). Naive
  `elapsed / progress` ETA is systematically wrong near the end for the byte kind.
  → [`patterns/timing-normalization.md`](patterns/timing-normalization.md)
- **Push vs poll — synthesize the missing stream.** Poll-only stacks (PrusaLink, Duet standalone, Marlin) have no
  event channel; diff successive snapshots into a change-event stream so the rest of your code sees one shape.
  → [`patterns/discovery-and-credentials.md`](patterns/discovery-and-credentials.md) (§ poll-synth)
- **Feeder is presence, not a vendor string.** Detect a multi-material unit by the *capability it reports*, not by a
  brand name; DIY units are identified by their **software provider** (Happy Hare / AFC), and several vendor units omit
  quantity or RFID UID entirely.
  → [`patterns/multi-material-feeders.md`](patterns/multi-material-feeders.md)

---

> **Confidence footnote.** The `Conf.` column is a one-glyph summary of a whole family; individual facts inside each
> paper carry their own 🟢/🟡/🔵/⚪ tags, and those are authoritative. A 🟡 here means "wire-shape read from the
> vendor's own source, not yet confirmed on hardware" — promoting any 🟡 family to 🟢 with a real capture is the
> highest-value contribution (see each paper's *Confidence & validation* section for the exact open gaps). Sanitized
> throughout: example IPs use `192.0.2.x` (RFC 5737); credentials are described as mechanisms, never values.
