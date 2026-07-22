# Duet3D / RepRapFirmware (RRF) — LAN Protocol

> **Status:** 🟡 source-read (docs.duet3d.com + the RRF wiki + the LGPL `@duet3d/connectors`/`@duet3d/objectmodel`
> libraries; **no Duet on the bench**) · **Firmware:** RepRapFirmware **3.0+** · **Models:** Duet 2 / Duet 3 boards
> (WiFi/Ethernet/Mini/6HC/6XD…), incl. multi-tool machines (E3D ToolChanger, Jubilee, industrial multi-head)
>
> RRF is **one JSON Object Model behind two mutually-exclusive LAN dialects** — **standalone** (a poll-only `rr_*` HTTP
> API on `:80`) and **SBC/DSF** (a `/machine/*` REST API + one push WebSocket, served by a companion Raspberry Pi).
> Both converge on the identical Object Model, so the read logic is written once; only transport/auth/upload differ.

## At a glance

- **Transport:** HTTP **`:80`** (HTTPS only behind a reverse proxy / operator TLS). **Standalone** = poll-only `rr_*`
  endpoints, **no push channel at all**. **SBC/DSF** = `/machine/*` REST + a single push WebSocket at `/machine`.
- **Discovery:** **manual host/IP** is the guaranteed path; `M550`-configured `<name>.local` **hostname** mDNS/NetBIOS
  works where honoured. **No DNS-SD service, no TXT, no SSDP/UPnP.**
- **Auth / credential:** a **machine password** → a session → an **`X-Session-Key`** header on every later request. The
  default password is the well-known `reprap`; the owner sets/reads their own. No certs, nothing to bundle.
- **Read / status:** the **RRF Object Model** (one shared JSON tree). Standalone polls it differentially (`rr_model` +
  a `seqs` change-counter map); SBC pushes **full-model-then-patch** over the WebSocket.
- **File transfer:** a **raw-body** upload in both modes — standalone `POST /rr_upload` (+ optional CRC32); SBC
  `PUT /machine/file/{path}`. **Not** multipart.
- **Print launch:** **upload ≠ launch.** Upload the file, then send a GCode: `M32 "<path>"` (select **and** start) or
  `M23 "<path>"` + `M24` (select, then start).
- **Feeders / multi-material:** **none** (RRF has no per-slot MMU model). It is instead a **toolchanger leader** —
  `tools[]` is a first-class array of physical toolheads.
- **⚠️ The load-bearing gotcha:** the live status value for *printing* is **`processing`** (there is no value literally
  named `printing`), and **progress is a file-byte fraction, not time** — two independent traps that each silently
  corrupt state and ETA if you assume otherwise.

## Transport & connection

RRF speaks **one of two wire dialects**, never both, and a client picks between them at connect time. 🟡

**Standalone** (`rr_*` on `:80`) — the RRF web server answers a fixed set of query-style endpoints under the host root
(`http://<host>/rr_connect`, `…/rr_model`, …). There is **no MQTT, WebSocket, SockJS, or SSE** — every piece of live
state is obtained by **polling**. HTTPS appears only if a reverse proxy fronts the board; a client just prefixes each
`rr_*` path with `<protocol>//<host><basePath>`. 🟡

**SBC / DSF** (`/machine/*` + WS) — what a Duet 3 serves when paired with a Raspberry Pi running the **Duet Software
Framework**. The Pi's **DuetWebServer** hosts a REST API under `/machine/*` (default `:80`, TLS when configured) and a
**single push WebSocket at `/machine`**; DSF bridges to the mainboard over SPI. Same Object Model, different wire. 🟡

**The mode fingerprint** — the first-party connector library resolves the dialect with an **ordered probe that
short-circuits on a login-class error**: 🟡

1. **Probe standalone first:** `GET /rr_connect?password=…&sessionKey=yes`. `err:0` + a usable API level ⇒ standalone.
2. **On a *non-login* failure** (network error / 404 / non-JSON — i.e. the board doesn't speak `rr_*`), **fall through**
   to SBC: `GET /machine/connect?password=…`, then open the `/machine` WebSocket and take its first frame as the model.
3. **Stop immediately on a login-class result** (wrong password, no free session, incompatible firmware) — that means
   "right transport, bad auth/version"; do **not** try the other dialect. ⚪ *(the composite router is inferred from two
   source-read facts: the probe order and the discriminator below)*

**In-band confirmation** — once connected, the mode is unambiguous from the Object Model's top-level **`sbc`** key:
**`null`/absent in standalone, populated only in SBC** (the OM reference states it is "exclusively maintained by DSF in
SBC mode … not available in standalone mode"). DSF version reads at **`sbc.dsf.version`** — there is **no
`state.dsfVersion` field**; don't invent one. Persist the resolved mode; re-probe only on hard failure. 🟡

**Version floor = RRF 3.0.** The Object Model (and `rr_model`) were **introduced in 3.0**; 2.x has neither. The
connector rejects a board whose reported API level is absent/0 as too old. Refuse below 3.0 with a clear message — a
firmware-family floor, not a nag. Read the live version from `boards[0].firmwareName` / `boards[0].firmwareVersion`
(+ `sbc.dsf.version` in SBC mode). The RRF↔DSF↔DWC firmware **bundle** version-locks at a `3.x` minor (current aligned
line `3.6.x`); note the connector *library* is a separate version line, so don't conflate the two numbers. 🟡/🔵

## Discovery & identity

**Manual host/IP is the guaranteed add path.** A machine named with `M550 P"name"` in `config.g` resolves as
`http://<name>` / `<name>.local` on networks honouring **mDNS/NetBIOS hostname** resolution (name **not**
case-sensitive). 🟡

> ⚠️ This is **A-record hostname** resolution, *not* a DNS-SD/`_http._tcp` service advertisement with TXT metadata.
> There is **no `_duet._tcp` service type, no TXT, and no SSDP/UPnP** — a service-discovery capability remains an
> unshipped upstream wishlist request. So offer name resolution at most; do **not** promise a "scan the LAN for Duets"
> experience. ⚪ *(the absence is inferred — a `dns-sd -B` / `avahi-browse` sniff against a real board would confirm it)*

Standalone has no single "who are you" endpoint; identity is assembled from the connect response + the Object Model:
`rr_connect` returns a `boardType` string (e.g. a `duetwifi102`/`duet3mb6hc…`-style identifier) and an `isEmulated`
flag (a client should **refuse an emulated endpoint**); durable identity/hostname come from OM `boards[]` and
`network`. See [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md). 🟡

## Credentials / auth

The only credential is a **machine password**, obtained by the owner from **their own board** — never bundled, never
hardcoded (see [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md)). The RRF default
when unset is the well-known `reprap`; if **no** password is configured, RRF **auto-creates a session on any HTTP
request**. A client should prompt for the password, validate it with a successful connect, and store it encrypted; the
session key is ephemeral and should stay in memory only. 🟡

**Standalone handshake** — `GET /rr_connect?password=…&time=…&sessionKey=yes`. The response carries: 🟡

- **`err`** — `0` = ok; **`1` = invalid password**; **`2` = no free session** (session table full); any other value =
  generic login error.
- **`sessionTimeout`** — max idle time **in milliseconds** between requests before the session drops. The **board
  returns the authoritative value** on connect; a client-side seed of ~8000 ms is just a default, not a firmware
  constant. ⚪
- **`sessionKey`** (RRF **3.5-b4+**) — an integer the client must then send as the **`X-Session-Key`** header on
  **every** subsequent `rr_*` request. Older firmware ignores the request and binds the session to the client IP
  instead. 🟡
- **`apiLevel`** — absent/`0` ⇒ the board is pre-Object-Model (2.x-class) ⇒ reject; `≥1` guarantees `rr_model` exists.
- **`isEmulated`** — `true` ⇒ refuse (an emulation, not real RRF).

**Every `rr_*` request except `rr_connect` returns HTTP `401` without a valid session** (idle-expired, firmware
restarted, or another client took the last slot). The correct recovery is a **transport-level interceptor**: on `401`
(or `403`), transparently re-issue `rr_connect`, refresh the stored `X-Session-Key`, and **retry the original request
once**. A second re-handshake trigger: watch `state.upTime` (seconds) — when it **decreases** between polls the board
rebooted, so re-connect and re-seed the full model. 🟡

**SBC handshake** — `GET /machine/connect?password=…` → `{"sessionKey":"<key>"}`, then the **same `X-Session-Key`**
header on every later request. A **wrong password maps to `401` *or* `403`** (map both). DSF **older than 3.4-b4 had no
passwords** — `/machine/connect` returns `404`, and the client should fall back to **sessionless** requests. A client
not holding the WebSocket keeps the session alive by pinging **`GET /machine/noop`**; on a socket drop it re-mints the
key via `/machine/connect` and reopens the socket. 🟡

## Reading state

Both modes deliver the **same RRF Object Model** — a JSON tree keyed roughly:
`state · heat · move · boards[] · tools[] · sensors · job · network · fans[] · spindles[] · limits · directories ·
volumes[] · inputs[] · sbc (null in standalone) · seqs`. The read mapping is written **once**; only how the tree
arrives differs. The neutral fields a client needs — lifecycle, temperatures, progress, capabilities — all extract
from this one tree. 🟡

**Standalone: a differential poll.** `GET /rr_model` queries the model by `key` with `flags` characters controlling
shape: `f` = frequently-changing (live) subset, `v` = verbose, `n` = include nulls, `o` = obsolete fields, `d<N>` =
depth limit, `a<N>` = array-pagination continuation (loop on the response `next` until it is `0`). The first-party poll
loop: 🟡

1. On connect, fetch **`rr_model?key=seqs`** (the change-counter map), then each top-level key in full (`flags=d99vno`).
2. Steady state, poll **`rr_model?flags=d99fn`** (no key ⇒ the live subset, with a fresh `seqs`).
3. For any key whose **`seqs[key]` counter incremented**, re-fetch that key in full — so rarely-changing subtrees are
   only re-read on change (a bandwidth-efficient differential). `seqs.reply` signals a waiting GCode reply, and a
   per-volume change counter signals a file list needs reloading.

The library's default poll interval is ~250 ms (a browser-UI cadence); a fleet client should poll gently and **back off
when idle** — any interval comfortably under `sessionTimeout` keeps the session alive, and if it backs off past that, it
simply hits the `401`→re-connect path already required. Because standalone has no push, a client **synthesizes a
change-event stream by diffing polls** (see [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md) §5). 🟡/⚪

**SBC: full-model-then-patch over the WebSocket.** Connect `ws(s)://host/machine?sessionKey=<key>`. **Frame 1 is the
full Object Model**; the client **acks each received document with a literal `OK\n` text frame** (the server sends the
next update only after the ack). **Subsequent frames are incremental patches**, merged by **deep-merge — *not* RFC-6902
JSON Patch**. Keep-alive is a bespoke line protocol: the client sends **`PING\n`**, the server replies **`PONG\n`**.
Socket close codes **1001 / 1011** signal **DCS unavailable / incompatible DSF** — surface as a login/version error, not
a generic drop. (`GET /machine/model` returns the whole tree as a poll fallback if the socket is blocked.) 🟡

**Lifecycle — parse `state.status`, an enum of 14 exact camelCase strings, never a human label:** 🟡

`disconnected · starting · updating · off · halted · pausing · paused · resuming · cancelling · processing ·
simulating · busy · changingTool · idle`

A reasonable native→normalized mapping: `idle`→idle; **`processing`→printing** (the printing state — *not* a value
named `printing`); `simulating`→printing (a dry-run for timing — flag it, don't count it as a physical print);
`paused`→paused, `pausing`/`resuming`/`cancelling`→transient; `changingTool`→busy (+ a toolchange sub-state, below);
`busy`→busy (homing/macro/motion, not a print); `starting`/`updating`→connecting/busy (boot / firmware flash);
`halted`→error (emergency-stopped after `M112`; recover with `M999`); `off`→offline; `disconnected` is a client
pseudo-status RRF doesn't emit. **There is no distinct `completed` value** — a job returning to `idle` (with the
just-finished job's terminal flags set: cancelled / aborted / simulated) is how completion is inferred. An unlisted
value should degrade to busy/unknown, never raise. 🟡/⚪

**Temperatures — °C, but behind an index dereference.** RRF separates **heaters** (physical channels) from their
**roles**. `heat.heaters[i]` carries `current`, `active` (setpoint), `standby` (setpoint), `state`
(`off`/`standby`/`active`/**`fault`**/`tuning`/`offline`), `min`/`max`. **`heat.bedHeaters[]` and `heat.chamberHeaters[]`
are arrays of *indices into* `heat.heaters[]`** (`-1` = none) — so the bed is **not** always heater 0 on a multi-tool
machine; resolve the index first. A `heater.state == fault` is a real safety signal worth surfacing. 🟡

**Progress & timing — file-byte progress, seconds throughout.** RRF exposes **no single "percent complete"** — derive
it as `job.filePosition / job.file.size` (bytes/bytes → 0..1; guard a null file / zero size). This is a **file-byte
fraction, like Klipper's**, *not* a time fraction — so extrapolating an ETA from it is **systematically wrong near the
end**. Use the firmware's own estimators instead: `job.timesLeft` has keys `{file, filament, slicer, toPause}`, **all in
seconds** (prefer `slicer` → `filament` → `file`; `slicer` needs RRF 3.5+; there is **no** `timesLeft.layer`). Every
time field RRF reports — `job.duration`, `warmUpDuration`, `pauseDuration`, `layerTime`, `file.printTime`,
`file.simulatedTime`, `state.upTime` — is **seconds**; lengths are mm, sizes bytes, fan/PWM a 0..1 fraction. Duet needs
**no time-unit normalization** (progress is the only derived quantity). See
[`../patterns/timing-normalization.md`](../patterns/timing-normalization.md). 🟡

**Capabilities read straight off the Object Model** (no separate profile endpoint): build volume ← `move.axes[]` where
`letter ∈ {X,Y,Z}` `{min,max}` (the *configured* `M208` travel limits — treat as hints, allow override); extruder
count ← `move.extruders[]`; heated bed/chamber ← `bedHeaters`/`chamberHeaters` non-empty (**gate the control on
presence**); tool count ← `tools[].length`; machine mode ← `state.machineMode` (`FFF`/`CNC`/`Laser`). 🟡

## Writing / control

RRF is **GCode-native** — there are **no structured setpoint endpoints**; every action is a GCode string. That makes
"no raw passthrough" the primary safety boundary: a client should emit **curated, typed, safe GCode from a registry**
and gate arbitrary user GCode off by default (with tool-select, e-stop, firmware-reset, and config-file writes gated
harder still). The command channel differs by mode; the GCode vocabulary is identical. 🟡/⚪

- **Standalone:** `GET /rr_gcode?gcode=<codes>` enqueues code(s); the response is **`{"bufferSpace":<int>}`** (the wire
  field is `bufferSpace` — `0` means the buffer is full). The **reply text is fetched separately**: `GET /rr_reply`
  returns the last GCode reply as `text/plain`, and its availability is signalled by the `seqs.reply` counter. 🟡
- **SBC:** `POST /machine/code` with the raw code string as the body (`text/plain`); `async=true` returns as soon as the
  code is enqueued (no reply), otherwise the body is the reply text. 🟡

A curated intent → GCode map (each is an uncopyrightable interface fact; verify against the RRF GCode dictionary): 🟡/🔵

| Neutral intent | GCode | Notes |
|---|---|---|
| jog (relative) | `G91` → `G1 X.. Y.. Z.. F<mm/min>` → `G90` | wrap the move in relative/absolute; gate off mid-print |
| home all / axis | `G28` / `G28 X`\|`Y`\|`Z` | |
| set tool active temp | `M568 P<tool> S<°C>` | **`M568` is the modern setter** (RRF 3.3+) |
| set tool standby temp | `M568 P<tool> R<°C>` | |
| set tool state | `M568 P<tool> A0`\|`A1`\|`A2` | `A0`=off / `A1`=standby / `A2`=active |
| set tool offset | `G10 P<tool> X.. Y.. Z..` | `G10` is retained for **offsets** only |
| set bed temp | `M140 S<°C>` (`M190` = set+wait) | gate on `bedHeaters` presence |
| set chamber temp | `M141 S<°C>` | gate on `chamberHeaters` presence |
| select tool | `T<n>` (`T-1` = deselect; `T<n> P0` = skip macros) | toolchanger — dangerous-tier |
| set fan speed | `M106 P<fan> S<0–255 or 0–1>` (`M107` off) | fan 0 = part-cooling |
| set feedrate factor | `M220 S<percent>` | |
| emergency stop | `M112` (→ `halted`; recover with `M999`) | dangerous-tier, hold-to-confirm UX |

> ⚠️ **Use `M568` for tool temps/state, not `M104 T<n> S…`.** RRF migrated tool temperature/state setting from `G10` to
> `M568` in firmware 3.3; `M104 T<n> S…` is the Marlin-lineage form, not the modern RRF setter. `G10` stays valid for
> **offsets**. 🟡

**Print launch — upload, then a GCode.** Neither upload endpoint carries an auto-print flag, so **upload-and-hold is the
natural default** and launching is a deliberate separate step: 🟡

- Preferred one-shot: **`M32 "0:/gcodes/<file>"`** = *select file and start SD print* (one round-trip, minimal race).
- Two-step: **`M23 "<path>"`** (select — loads, does **not** start) then **`M24`** (start/resume). 🔵
- Pause `M25`; cancel `M0` (`M0 H1` to keep heaters). Confirm the safe cancel sequence on hardware.

There is **no synchronous "print started" ack** — **confirm by state-poll**: watch `state.status → processing` and
`job.file.fileName` matching the launched path. Gate the launch on `state.status == idle` (RRF refuses a second job
while one runs). ⚪

**File transfer — a raw body in both modes** (see the upload-dialect landscape; this is the family that uses CRC32 and
`{err}` in standalone, a bare `PUT`/`201` in SBC): 🟡

- **Standalone `POST /rr_upload?name=<path>&crc32=<hex>`** — raw file bytes in the body; the optional **CRC32** is
  **lowercase hex without a `0x` prefix**, and RRF validates it (a mismatch returns `err:1`). The first-party client
  enables CRC by default and retries an `err≠0` upload for payloads under ~350 KiB. Result is `{err:0|1}`, not a path.
- **SBC `PUT /machine/file/{path}`** — raw bytes, optional `timeModified`; **201 Created** on success; **no checksum**
  (DSF handles integrity over the SPI link — verify by re-reading `fileinfo`/size). ⚠️ On SBC, `502`/`503` means
  **DCS/DSF busy or unavailable** (the Pi↔board link) — transient, retry; distinct from a `4xx`.
- **Paths use RRF volume notation** (`0:/gcodes/<file>`, or a leading-slash relative form). The print root is
  conventionally `0:/gcodes/` but a client should read **`directories.gCodes`** and enumerate `volumes[]` rather than
  hardcode. RRF prints plain `.gcode` (no binary-gcode format). 🟡
- **Verb quirk:** the standalone file API is almost entirely **`GET` with query params** — even `rr_delete`, `rr_mkdir`,
  `rr_move` are GETs; only `rr_upload` is a POST. On SBC, **`/machine/file/move` is `multipart/form-data`** (`from`/`to`
  /optional `force`), not form-urlencoded. Metadata + thumbnails come from `rr_fileinfo` / `GET /machine/fileinfo`
  (base64 thumbnail chunks; loop while a `next` offset is non-zero). 🟡

> ⚠️ **The `503` interlock (standalone).** RRF returns HTTP **`503` when it is out of output buffers**, which typically
> means a blocking GCode reply is occupying the buffer. The correct recovery is **drain `rr_reply`, then retry** — not
> treat `503` as a hard failure. 🟡

## Multi-tool / toolchanger (not a feeder)

RRF core has **no per-slot filament changer / MMU / spool model** — multi-tool is a *toolhead* concept, not a feeder
concept, and the two are orthogonal (see
[`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md)). A client should report **no
multi-material** for core RRF and **never fabricate slots**. The only filament signal is a **name**: it lives on the
**extruder** (`move.extruders[i].filament`, assigned via `M701`/`M703`), resolved for a tool through
**`tools[n].filamentExtruder`** (the extruder index) — there is **no `tools[n].filament` field**, and no active-slot /
per-slot load-unload / per-slot runout. 🟡

Where Duet is a **leader** is the toolchanger. **`tools[]` is a native, first-class array** of physical toolheads —
each with its own heater(s), extruder(s), XYZ offset, and active/standby setpoints — a far cleaner source than
scraping a status object. The neutral tool fields a client tracks map almost directly: 🟡

- `tools[n].number` → the `T<number>`; `tools[n].name`; `tools[n].state` (`active`/`standby`/`off`).
- `tools[n].active[]` / `standby[]` are the **already-resolved setpoints** (use directly); `tools[n].heaters[]` are
  indices into `heat.heaters[]` for the live temp (`heat.heaters[heaters[0]].current` = the primary hotend).
- `tools[n].offsets[]` is a **float array ordered by axis** (X, Y, Z, …). `tools[n].extruders[]` indexes
  `move.extruders[]`; a `tools[n].spindle` maps a tool to a CNC spindle.
- **The active tool is `state.currentTool`** (int, **`-1` = none**) — authoritative, not a per-tool scan; fold `-1` to
  "none". `state.nextTool` / `state.previousTool` name the incoming/outgoing tool during a change.
- **Toolchange status is first-class:** `state.status == changingTool` is the machine-level "mid tool-change" signal
  (cleaner than firmwares that only report a generic busy). Detect a toolchanger by **presence** —
  `tools[].length > 1` with independent offsets/heaters — never a vendor string. 🟡/⚪

A `T<n>` triggers RRF's user-authored `tfree<n>.g` / `tpre<n>.g` / `tpost<n>.g` macros on the SD card; a client only
issues `T<n>` (or `T<n> P0` to suppress them), it doesn't author them. 🟡

**CNC / laser** are in-scope for RRF (`state.machineMode ∈ {FFF, CNC, Laser}`, a real `spindles[]` array) but out of
scope for FFF print semantics — read the mode + spindle **presence** as capability metadata so a UI can hide FFF-only
affordances, and build no spindle/laser control. ⚪

## Quirks & gotchas

- **`processing`, not `printing`** — the OM string enum's printing state is `processing`; the toolchange state is
  `changingTool`. The legacy `rr_status` numeric/letter enum (with a literal `printing`/`toolChange`) is a **different,
  older, deprecated** surface — don't use it.
- **Progress is file-byte** (`filePosition/size`), not time — ETA-from-progress is wrong near the end; use
  `job.timesLeft.*` (seconds).
- **Two mutually-exclusive dialects.** A standalone board answers `rr_*` and 404s `/machine/*`; an SBC box is the
  reverse. Probe standalone first, fall through on a *non-login* error, and confirm with the OM **`sbc`** key.
- **`401` on everything but `rr_connect`** (standalone) — a lost session is normal; re-connect + retry once. A
  **decreasing `state.upTime`** means the board rebooted → re-handshake and re-seed.
- **`rr_gcode` returns `bufferSpace`** (not `buff`); the `rr_model` **`a` array-continuation flag** is real but **not in
  the wiki** (it lists only `f/v/n/o/d`).
- **`503` differs by mode:** standalone `503` = out of output buffers → **drain `rr_reply`, retry**; SBC `502`/`503` =
  DCS/DSF busy → backoff-retry.
- **CRC32 is lowercase hex with no `0x`** (standalone upload); the SBC `PUT` has **no** checksum.
- **`M568` for tool temps/state; `G10` for offsets** — never `M104 T<n> S…` on RRF.
- **Default password `reprap`; an unset password auto-creates a session** on any request.
- **DSF bad-password = `401` *or* `403`** (map both); pre-3.4-b4 DSF has no password (connect 404 → sessionless).
- **`sessionTimeout` is milliseconds**; the ~8000 ms figure is a client seed, not a firmware constant — the board
  returns the real value.

## Confidence & validation

**This is a source-read paper — nothing here is hardware-validated.** There was no Duet on the bench for this pass. The
API *shape* confidence is high because it is grounded in the vendor's own documentation and its LGPL connector/object-
model libraries, but live values and behaviour are unconfirmed.

- 🟡 **Source-read (solid):** the two-dialect model + the ordered-probe/login-short-circuit fingerprint; the `sbc` mode
  discriminator and `sbc.dsf.version`; the **14-value `state.status` enum**; the top-level OM keys and `job` fields;
  the auth model (`rr_connect` `err` 0/1/2, `X-Session-Key`, DSF bad-pw `401`/`403`, 401-on-everything-but-connect); the
  full `rr_*` and `/machine/*` surfaces; **file-byte progress** (`filePosition/size`, no `fractionPrinted`); the
  seconds-native units ledger; the raw-body upload dialects (CRC32 vs bare PUT); the WS full-model-then-patch + `OK\n`
  ack; the RRF-3.0 version floor; and the first-class `tools[]` toolchanger read. `M568`'s `A0/A1/A2` states are
  confirmed against the official M568 docs (shippable without hardware).
- 🔵 **Community / lore:** the aligned firmware **bundle** numbers; the `M23`/`M24` "select does not auto-start"
  semantics (from reprap.org).
- ⚪ **Inferred (validate before trusting):** the *composite* probe-then-confirm router synthesis; the exact API-level
  values in the wild and the precise `BadVersionError` threshold; the live `sbc` subtree shape and how WS patches merge
  under array mutation (add/remove a tool/heater); the **absence** of a DNS-SD service; the numeric max-concurrent-
  session cap (commonly cited as a small table); the safe cancel sequence and the exact quoting of `M32 "<path>"`; and
  CNC/laser job semantics.

**Open gaps and the capture that closes each.** RRF has **no official virtual printer** (unlike OctoPrint), so it is
not hardware-free — but it is cheap: a **Pi + DSF software rig (no board)** validates the entire SBC/REST mode (live
`sbc` subtree, the WS patch-merge under a tool/heater mutation, the router's `sbc`-key agreement, layer-metadata
availability), and **one inexpensive Duet board** validates standalone (`rr_connect` `err`/API-level/`sessionKey`, real
`state.status` transitions, mDNS hostname, the buffer-full/`503` behaviour, and a tolerable fleet poll cadence). The
one genuinely-unsettled synthesis — worth capturing **first** — is the **two-mode connect router** on both a real
standalone board and a real SBC rig. Confirming `state.status == changingTool` actually fires during a `T<n>` needs an
E3D ToolChanger / Jubilee owner-report (no toolchanger hardware here). A `dns-sd`/`avahi-browse` sniff would settle the
DNS-SD absence, which is a network fact outside any Object-Model capture.

## Sources

Clean-room, facts-only. Built from the **official Duet3D documentation and the RRF wiki** (the `HTTP-requests` `rr_*`
reference, the Object-Model documentation, and the GCode dictionary) for the endpoint/param/`err`-code surface, the
Object-Model field names, the `state.status` enum strings, and the GCode vocabulary — all uncopyrightable interface
facts. Exact strings and the connect / mode-probe **behaviour** were read-confirmed against the **LGPL-2.1**
`@duet3d/connectors` (the shared connector library, `master` = 3.5.7) and `@duet3d/objectmodel`, and the DSF
`OpenAPI.yaml` for the `/machine/*` codes. The **GPL-3.0** RepRapFirmware and DuetWebControl repos were consulted for
*behaviour only*.

Duet's stack spans **three licenses** (GPL-3.0 firmware + web client, LGPL-2.1 connect/read libraries): **no code was
copied or line-by-line translated from any of them** — an independent client of a documented API. **No secrets:** the
sole credential is a user-entered machine password (default `reprap`), and the session key is ephemeral — none appear
here. Passed [`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md).

> **Machine-readable:** [`../schemas/duet/state-status-enum.json`](../schemas/duet/state-status-enum.json) (the 14
> `state.status` values → normalized), [`job-and-timing.json`](../schemas/duet/job-and-timing.json) (progress + the
> seconds-native unit ledger), [`tools-model.json`](../schemas/duet/tools-model.json) (the `tools[]` toolchanger +
> active-tool + heater deref), [`gcode-intent-map.json`](../schemas/duet/gcode-intent-map.json) (intent → GCode).
