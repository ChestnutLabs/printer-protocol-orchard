# OctoPrint (host controller) — LAN Protocol

> **Status:** 🟡 source-read (official API docs + AGPL server source; validatable hardware-free via the official Docker
> image + bundled Virtual Printer — no printer hardware needed) · **Firmware:** n/a — OctoPrint is a **host
> controller**, not a printer protocol; it fronts the printer's own firmware over USB/serial · **Models:** any
> USB/serial FDM printer behind an OctoPrint host (and, from 2.0, a Moonraker/Bambu connector)
>
> OctoPrint is a **computer in front of a USB printer**. A client talks to OctoPrint's documented **HTTP REST API +
> SockJS push channel** and never to the firmware underneath — the physical printer is just metadata. One **API key**
> authenticates everything; the state model is push-primary with a poll backstop.

## At a glance

- **Transport:** HTTP REST rooted at `/api/*` on **`:5000`** (plain http) + a **SockJS** push channel at **`/sockjs`**.
  `https`, a URL **path prefix**, and HTTP Basic-Auth appear only when the operator fronts it with a reverse proxy.
- **Discovery:** `_octoprint._tcp` **mDNS** is the reliable channel (generic SSDP `Basic:1` is best-effort); manual
  IP/URL is the guaranteed path.
- **Auth / credential:** one **API key** (`X-Api-Key:` header, or `Authorization: Bearer`). Recommended onboarding is
  the interactive **Application Keys** approval handshake; the user can also paste a key from their own instance.
- **Read / status:** **push-primary** over SockJS (`current`/`history` frames), with a **non-zero REST poll backstop**
  (`GET /api/printer` + `GET /api/job`). Parse state off `state.flags` booleans.
- **File transfer:** `multipart/form-data POST /api/files/{local|sdcard}` (form part `file` + inline `select`/`print`
  flags) → `201`.
- **Print launch:** upload → (`select`) → `POST /api/job {command:"start"}`; or upload with `print=true` in one shot.
- **Feeders / multi-material:** **none in core** — OctoPrint exposes *multi-tool* (`extruder.count`, `tool{n}`), which
  is a toolhead concept, not a filament feeder. Filament tracking is plugin territory.
- **⚠️ The load-bearing gotcha:** `progress.completion` is a **fraction `0.0–1.0`** (×100 for a bar) **and it's
  file-byte position, not time** — two separate traps in one field. See [Reading state](#reading-state).

## Transport & connection

The chain is `client → OctoPrint instance → USB/serial (or a 2.0 connector) → printer`. OctoPrint is a **host
controller**; you drive its API and treat the machine underneath as secondary metadata. 🟡

- **REST:** plain **HTTP** on **`:5000`** by default, rooted at `/api/*`, plus a few bundled-plugin routes under
  `/plugin/*` (e.g. `/plugin/appkeys/*` for onboarding). Bodies are `application/json` (UTF-8). 🟡
- **Reverse-proxy shape:** `https`, a **path prefix** (e.g. an instance served under `/octoprint/`), and HTTP
  Basic-Auth only appear when an operator puts a proxy in front. **When a path prefix is present it must be prepended
  to every `/api/*` call.** 🟡
- **CSRF:** OctoPrint's double-submit-cookie CSRF protection applies **only** to non-`GET` requests that rely on
  *cookie* auth. **A header-key client bypasses CSRF entirely** — no token needed. 🟡
- **Push:** live state rides **SockJS**, mounted at **`/sockjs`**. SockJS is a transport with its **own handshake and
  framing** over an underlying WebSocket/XHR — *not* a raw WebSocket JSON-RPC channel, so a client needs the SockJS
  handshake, not just a bare socket. The exact sub-URL and frame envelope need a live capture to pin. 🟡 *(mount)* / ⚪
  *(exact sub-URL + envelope)*

## Discovery & identity

**mDNS / ZeroConf** advertises two services: the generic `_http._tcp` and the OctoPrint-specific **`_octoprint._tcp`**
— key on the latter. Its TXT record carries `path`, `u`, `p`, `version`, `api`, `model`, `vendor`. 🟡

> ⚠️ The TXT `u`/`p` are a **reverse-proxy Basic-Auth convenience, not the OctoPrint API key** and **not a security
> boundary** — never treat them as auth, never persist them in a capture.

**SSDP / UPnP** announces the instance as a generic `urn:schemas-upnp-org:device:Basic:1` device — that identifies
"a UPnP Basic device," not OctoPrint specifically, so it's **best-effort**; confirm any SSDP hit with `/api/version`.
🟡 Build the base URL as `http://[u[:p]@]host:port[path]` (`https` when `useSsl` is set); **manual IP/URL entry is the
first-class, always-works path.** See [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md).

**Identity endpoints:**
- `GET /api/version` → `{ api, server, text }`. `server` is the OctoPrint semver (e.g. `1.11.8`); **`text` carries the
  literal `"OctoPrint <version>"`** — the `"OctoPrint "` prefix is the positive genuineness tell. 🟡
- `GET /api/server` → `{ version, safemode }` (present from **≥1.5.0**; `safemode` names the reason it booted into safe
  mode, else `null`). 🟡

**The genuineness fingerprint (important).** Other hosts expose an **OctoPrint-compatible `/api/*` subset** (PrusaLink,
notably), so "answers `/api/version`" does **not** imply genuine OctoPrint. Use a **two-sided** discriminator:
**positive** = the `"OctoPrint "` `text` prefix (corroborated by `/api/server` answering and/or `_octoprint._tcp`
mDNS); **negative** = it must **not** answer a `/api/v1` info/status with a Prusa serial. Preserve the raw
`text`/`server` strings so a mis-fingerprint is diagnosable. 🟡 *(positive tell)* / ⚪ *(the composite two-sided rule)*

## Credentials / auth

**One credential — an API key**, a **user secret** obtained from the user's own OctoPrint install. Transmit it as
`X-Api-Key: <key>` (primary) or `Authorization: Bearer <key>`; a `?apikey=` query param exists but is **testing-only**.
Missing/invalid ⇒ **`403 Forbidden`** when access control is on (OctoPrint's default). This orchard documents the
*mechanism*, never a value — prompt the user, store it encrypted, never bundle one. 🟡

**Application Keys — the recommended interactive onboarding** (an approval handshake, not a static paste):

| Step | Request | Result / codes |
|---|---|---|
| **Probe** | `GET /plugin/appkeys/probe` | **204** ⇒ supported → else fall back to manual paste |
| **Request** | `POST /plugin/appkeys/request` — body `{ "app": "<name>", "user": <optional> }` (`app` required, case-insensitive) | **201** + polling URL in the `Location` header (+ an app token) |
| **Poll** | `GET /plugin/appkeys/request/<app_token>` **every ~1 s** | **202** pending · **200** `{ "api_key": "<key>" }` granted · **404** denied \| expired |
| *(user side)* | the owner approves/denies in the OctoPrint web UI (`POST /plugin/appkeys/decision/<user_token>` → 204) | — |

> ⚠️ **Hard constraint:** a pending request is considered **stale and deleted internally if its polling endpoint isn't
> called for more than 5 s.** Poll every ~1 s and **do not back off while pending**, or the grant is lost and
> onboarding restarts. 🟡

The granted key is **app-specific** (least privilege) — prefer it over the global/user key. Manage/revoke lives at
`GET`/`POST /api/plugin/appkeys`. Keys are **permission-scoped**: a key granted only `STATUS` can drive the read/poll
backstop but not writes (which need `CONTROL`/`PRINT`). See
[`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md).

## Reading state

**Push-primary, poll-backstop.** SockJS delivers live deltas; the REST poll is the fallback when the socket is down or
the key is authed for status only.

**SockJS handshake:** call `GET /api/login?passive=true` (carrying the key) to obtain a **`session`**, then send an
**`{"auth": "<userid>:<session>"}`** frame over the socket. This is required before any status message arrives (the
permission system withholds them from a socket lacking `STATUS`). 🟡 *(mechanism)* / ⚪ *(exact login body + pairing —
needs a capture)*

**Message-type keys** — each push is a JSON object whose single **top-level key names the type**; **ignore unknown
keys**: `connected`, `reauthRequired`, `current`, `history`, `event`, `slicingProgress`, `plugin`. `current` and
`history` share a shape — `{ state:{text,flags}, job, progress, currentZ, offsets, temps, logs, messages, resends,
plugins }`; `history` is the one-time backlog on connect, `current` is the live delta. `reauthRequired` means re-send
the `auth` frame. 🟡

**Poll surface** (same data as the pushes):
- `GET /api/printer` → `{ temperature:{ tool0:{actual,target,offset}, tool1…, bed, chamber, history? }, sd:{ready},
  state:{ text, flags, error? } }`. **Returns `409` when the printer is not operational** — treat that as a valid
  **"not connected"** signal, not a transport failure. 🟡
- `GET /api/job` → `{ job:{ file, estimatedPrintTime, averagePrintTime, lastPrintTime, filament:{tool0:{length,volume}} },
  progress:{ completion, filepos, printTime, printTimeLeft, printTimeLeftOrigin }, state, error? }`. 🟡

**State enum — parse `state.flags` booleans, never the human `state.text`.** The **9 documented flags** are
`operational, printing, paused, pausing, cancelling, sdReady, error, ready, closedOrError`. The **server source emits
11**, adding **`resuming`** and **`finishing`**; prefer those two flags when present, otherwise derive them from the
state string (a resuming/finishing printer otherwise just reports `printing:true`). 🟡 *(9 documented)* / ⚪ *(the 11-flag
set — confirm which a live instance emits)*

| Native signal (flags first) | Normalized | Notes |
|---|---|---|
| `closedOrError && !error` / text `Offline` | **offline** | not connected to the printer |
| text `Opening…`/`Detecting…`/`Connecting` (no flag) | **connecting** | transient; string-derived |
| `operational && !printing && !paused` (`Operational`) | **idle / ready** | the "ready for a job" state |
| `printing` (+ `finishing` hint) — text `Starting`/`Printing`/`Finishing` | **printing** | 3 printing-variant strings ("Printing", "Printing from SD", "Sending file to SD") — don't string-match them |
| `resuming` flag *or* text `Resuming` | **printing** (resuming) | prefer the flag; else string-derive |
| `pausing` (`Pausing`) | **pausing** | |
| `paused` (`Paused`) | **paused** | |
| `cancelling` (`Cancelling`) | **cancelling** | |
| `error` / `closedOrError && error` (`Error`/`Offline after error`) | **error** | carries the message |

> ⚠️ **`Operational` is ambiguous** — it is *both* "idle/ready" *and* the base state under which the printing/paused
> flags ride. Read `printing`/`paused`/`pausing`/`cancelling` **before** concluding idle. ⚪

**Temperatures:** `temperature.{tool0…N, bed, chamber}.{actual, target, offset}`, **°C floats**. `actual` with no
`target` = read-only monitoring; `target: 0` = heater off; `offset` is the user's manual temp offset. `chamber` is
present only if the profile has a heated chamber. 🟡

**Progress & timing** *(the load-bearing traps — see [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md)):*
- **`progress.completion` is a fraction `0.0–1.0`** (a real docs example is `0.2298…`) — **multiply by 100** for a
  percent bar; do **not** treat it as already-percent. One live-confirm remains open. 🟡
- **It is file-byte position** (`filepos/size`), **not time-based** → extrapolating an ETA from it is
  **systematically wrong near the end** of a print. For "remaining," trust the firmware-reported
  **`progress.printTimeLeft`** instead. 🟡
- **All times are in SECONDS** (`printTime`, `printTimeLeft`, `estimatedPrintTime`, `averagePrintTime`,
  `lastPrintTime`); `filepos`/`size` are **bytes**. `printTimeLeft` may be `null` early in a print. 🟡
- **`printTimeLeftOrigin`** qualifies ETA quality — `linear`, `analysis`, `estimate`, `average`, `mixed-analysis`,
  `mixed-average`. `estimate`/`linear` are coarse guesses; `analysis`/`average` are file-analysis-backed. Surface the
  ETA with a caveat (or hide it) when the origin is a bare `estimate`/`linear`. 🟡

**Missing-field rule:** everything except the state signal degrades gracefully — `chamber` absent without a heated
chamber, `temperature` partial when not operational, `progress.*` `null`/absent with no active job. A missing
temp/progress/file must **not** be read as `0`. ⚪

## Writing / control

OctoPrint exposes **structured, typed endpoints for the whole core surface** — no raw-G-code passthrough is required
for normal control. All control POSTs return **`204 No Content` with an empty body**; read the *effect* from the next
SockJS `current` push or a follow-up GET, never from the POST body.

| Neutral intent | Endpoint | Body |
|---|---|---|
| Print start / cancel / restart | `POST /api/job` | `{command:"start"\|"cancel"\|"restart"}` *(restart needs a paused job)* |
| Pause / resume | `POST /api/job` | `{command:"pause", action:"pause"\|"resume"}` — **explicit, never `toggle`** |
| Set tool temp | `POST /api/printer/tool` | `{command:"target", targets:{tool0:N}}` — °C map, `0`=off |
| Set bed / chamber temp | `POST /api/printer/{bed,chamber}` | `{command:"target", target:N}` — **gate on `heatedBed`/`heatedChamber`** |
| Jog / home / feedrate | `POST /api/printer/printhead` | `{command:"jog", x,y,z, speed, absolute}` · `{command:"home", axes:[…]}` · `{command:"feedrate", factor:105}` |
| Tool select / extrude / flowrate | `POST /api/printer/tool` | `{command:"select", tool:"tool1"}` · `{command:"extrude", amount, speed}` · `{command:"flowrate", factor:0.95}` |
| Connect / disconnect / `fake_ack` | `POST /api/connection` | host-link management, **not printing** — treat as admin/dangerous |
| SD init/refresh/release | `POST /api/printer/sd` | `{command:"init"\|"refresh"\|"release"}` |
| **Raw G-code** | `POST /api/printer/command` | `{commands:[…]}` — **can interrupt/stop a print; keep gated off by default** |

> ⚠️ **`feedrate.factor` is a PERCENT (`105` = 105 %), but `flowrate.factor` is a FRACTION (`0.95` = 95 %).** This
> asymmetry is documented and a real footgun — don't conflate them. 🟡
>
> ⚠️ **The `pause` action defaults to `toggle` when omitted** — always send an explicit `pause`/`resume`, or you race
> the true state. 🟡

**409 is a precondition, not a fault.** Control POSTs return `409` when: jog/home → not operational or currently
printing; tool commands (except `target`) → not operational; SD → card not initialized; bed/chamber → the profile
lacks that heated component. **Gate bed/chamber on `heatedBed`/`heatedChamber`** and jog/home on
`operational && !printing` **before** sending, so a `409` becomes a rare race rather than a routine outcome. 🟡

> ⚠️ Control writes drive a hot, moving machine — validate them against your own instance and gate them behind an
> explicit "enable writes" in any client. `fake_ack` (an emergency action for a stalled serial line) and
> connect/disconnect are host-management operations, not a normal workflow — keep them admin-gated.

**Print launch & file transfer.** The Files API is rooted at `/api/files`; `location` ∈ `local` (OctoPrint's uploads
folder) | `sdcard` (the printer's SD). Upload is **`multipart/form-data POST /api/files/{location}`** with the form
part **`file`** plus flag fields: `path` (subfolder), `select` (bool, default `false`), `print` (bool, default
`false`), `userdata` (a JSON string; invalid → `400`), and `foldername` (an *alternative* to `file` that creates a
folder — mutually exclusive with it). 🟡

Response is **`201`** `{ files:{ local:{…}, sdcard? }, folder?, done, effectiveSelect, effectivePrint }`:
- `done` is `false` while an **SD stream** is still in progress (final completion arrives via SockJS).
- **`effectiveSelect`/`effectivePrint` echo what actually happened** — a `print=true` the printer could not honor comes
  back `false`. **Always read them back.** 🟡
- Codes: `201` success · `400` (no `file`/`foldername`, or bad `userdata`) · `404` (bad location) · `409` (would
  interrupt an active print, or SD busy) · `415` (extension not an accepted machinecode type — `.gcode`/`.gco`/`.g`;
  model types are slicer-plugin dependent) · `500`.

Two launch flows:
1. **Upload-and-hold (recommended):** upload with `select=false, print=false` → `201`; later select
   `POST /api/files/{location}/{path} {command:"select", print:false}` → `204`; then `POST /api/job {command:"start"}`
   → `204`. This lets a client verify the stored file and keep its own job record authoritative.
2. **Upload-and-print (one-shot):** upload with `print=true` → `201`, then **read back `effectivePrint`** to confirm it
   actually started.

> **OctoPrint is the notable case where launch intent can ride *inline* in the upload** (the `select`/`print` form
> fields) rather than a separate start command — convenient, but it couples upload to start; decoupling keeps the job
> record cleaner. There is **no documented upload checksum** → rely on `201` + `done:true`; a dropped transfer means
> re-POST the whole multipart (no resume protocol). 🟡

Other Files ops: `POST /api/files/{location}/{path}` `{command: select|unselect|copy|move|slice}`;
`DELETE /api/files/{location}/{path}` → `204` (`409` if it's the *active* print). `sdcard` files expose only
`name/path/origin/size` — no `date`, no `gcodeAnalysis`, no download. A `machinecode` file also carries `gcodeAnalysis`
(`estimatedPrintTime`, `filament:{length,volume}`, `dimensions`) for additive enrichment; **thumbnails are
plugin-dependent**, not core. 🟡

> ⚠️ **Security floor — OctoPrint ≥ 1.11.8.** The upload endpoints carried a **High-severity file-exfiltration** flaw
> (CVE-2026-54134, an incomplete-fix follow-up to CVE-2025-48067; patched in 1.11.8). A client should send **only the
> documented public form fields** (`file`, `path`, `select`, `print`, `userdata`, `foldername`) — never OctoPrint's
> reserved internal upload fields — and **warn when a connected server reports `< 1.11.8` while upload is enabled.**
> 🔵 *(advisory-sourced)*

## Multi-material / feeders

**Core OctoPrint has no multi-material / spool / filament-slot model** — no per-slot type/color/material, no
active-slot, no load/unload, no per-slot runout anywhere in the documented `/api` surface. 🟡

What it *does* expose is **multi-tool**: `extruder.count` and per-tool `tool{n}` temperature channels + tool-select
(`{command:"select", tool:"tool1"}`). That is a **toolhead** concept, not a **filament feeder** — keep them separate
(see [`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md), which treats a toolchanger as
orthogonal to a feeder). `extruder.sharedNozzle` distinguishes a switching-nozzle / IDEX-style setup from truly
independent hotends (a metadata hint). 🟡

Filament tracking in the OctoPrint world is **plugin territory** (Filament Manager, SpoolManager, …), each adding its
own plugin API. An implementer should contribute **presence-only** to a neutral feeder model (at most a hint from
`extruder.count > 1` / `sharedNozzle`) and **never fabricate slot data**; keep any plugin-sourced filament data
plugin-local rather than promoting it into the neutral model. ⚪

**Capabilities & build volume** come from `GET /api/printerprofiles` → `{ profiles:{<id>:{…}} }`. Each profile carries
`model`, `heatedBed`, `heatedChamber`, `volume{ formFactor(rectangular|circular), origin, width, depth, height }`,
`axes{x,y,z,e:{speed,inverted}}`, and `extruder{ count, offsets[[x,y]], nozzleDiameter, sharedNozzle }`. Treat these as
**hints, not ground truth** — they are user-configured and can be wrong or default; allow the user to override display
metadata, gate bed/chamber control on the `heated*` flags, and read a `circular` form-factor's diameter from `width`. 🟡

## Quirks & gotchas

- **It's a host, not a printer.** You never see the firmware; the machine underneath is metadata only (`profile.model`,
  best-effort). Never route a dialect off it.
- **Fingerprint before trusting `/api/*`.** Other hosts expose an OctoPrint-compatible subset — require the
  `"OctoPrint "` `text` prefix (and *not* a Prusa `/api/v1`).
- **`progress.completion` is a fraction `0.0–1.0` (×100) *and* file-byte position, not time** — two traps in one field.
- **`feedrate` = percent, `flowrate` = fraction** — don't conflate.
- **`pause` defaults to `toggle`** — always send explicit `pause`/`resume`.
- **9 documented state flags vs 11 in source** (`resuming`/`finishing`) — prefer the flags, else derive from the string;
  and never string-match the 3 printing-variant literals.
- **`409` is a signal, not an error** — `GET /api/printer` `409` = not operational; upload/job `409` = would
  interrupt / SD busy. Gate preconditions before sending.
- **SockJS ≠ raw WebSocket** — it needs the SockJS handshake + framing, plus a passive-login `session` and an
  `{"auth":"userid:session"}` frame before any status arrives.
- **Reverse-proxy shape** — prepend the path prefix to every `/api/*` call; `https`/Basic-Auth appear only when
  proxied; the mDNS `u`/`p` are not the API key.
- **Version:** target the 1.11.x stable line (floor **1.11.8**). **2.0** was RC-only as of mid-2026; it moves comms into
  pluggable **connectors** (Serial / Moonraker / Bambu) but **keeps the same `/api/*` + SockJS surface**, adds an
  `X-OctoPrint-Api-Version` request header for API pinning, and adds native thumbnails + multi-storage — so an
  implementer stays 2.0-ready by **not hardcoding "one `local` + one `sdcard`"** and instead reading the storage list.
  🔵

## Confidence & validation

Overall **🟡 source-read** — **nothing here is hardware-validated in this pass.** The whole surface is closeable
**hardware-free**: the official `octoprint/octoprint` **Docker image + bundled Virtual Printer** reproduce
idle → printing → paused → cancelled → error → comm-error on a developer's own machine, no printer required.

- **🟡 documented first-party:** the `/api/*` endpoints, form/JSON field names, status codes, `state.flags` booleans,
  the SockJS message-type keys, the Application-Keys handshake + the **5 s poll-staleness** rule, the temperature and
  progress shapes, and the `printerprofiles` model — all from the official API docs, read-confirmed against the server
  source for exact strings.
- **⚪ open gaps (a Docker + Virtual-Printer capture closes each):**
  - the exact `/sockjs` sub-URL + frame envelope, and whether a plain WebSocket client carries SockJS framing directly
    or a SockJS handshake shim is required;
  - the passive-login `POST /api/login?passive=true` body and the `{"auth":"userid:session"}` pairing;
  - the appkeys `201/202/200/404` body shapes, and whether `/api/version`+`/api/server` answer **un**authenticated (a
    pre-auth fingerprint);
  - a live confirm that `progress.completion` is a fraction on a real 1.11.x instance;
  - multi-tool temp keys (`tool1`, `tool2`) + tool-select on a 2-extruder virtual profile;
  - whether the `409` bodies carry a machine-readable reason (not-operational vs profile-lacks-component vs printing);
  - whether 1.11.x silently ignores `X-OctoPrint-Api-Version` (safe to always send);
  - real `_octoprint._tcp` TXT contents (are `model`/`vendor` populated?);
  - whether a commonly-bundled filament plugin leaks per-slot state into `current`/`plugin` frames before finalizing
    "no feeder."

## Sources

Clean-room, facts-only. Built from OctoPrint's **official REST / Application-Keys / discovery API documentation**
(endpoint paths, JSON field names, enum/state strings, header names, status codes — interface facts), read-confirmed
against the **AGPL-3.0 `OctoPrint/OctoPrint` server repo** for the exact state strings, the SockJS mount, and the SSDP
URN **without copying code**, and cross-checked against two stale MIT community clients for field-name sanity only.
**No AGPL code was copied or vendored** — neither the server nor the same-license in-repo JS client (whose SockJS
parsing is a copy risk, not a safe reference). Version/CVE facts are from the OctoPrint release blog and GitHub security
advisories. No API keys, Basic-Auth values, hosts, or serials appear here (the API key is the user's own, obtained from
their own instance). **Hardware-unvalidated in this pass** — validatable hardware-free via the official Docker image +
bundled Virtual Printer. Passed [`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md).
