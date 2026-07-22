# PrusaLink (Prusa host controller) — LAN Protocol

> **Status:** 🟡 source-read (official OpenAPI 3.0.1 spec) · **hardware-unvalidated / partial** · **Firmware:**
> PrusaLink on Buddy firmware (MK4/MK4S/MK3.9, MINI/MINI+, XL, Core One) and the Raspberry Pi `Prusa-Link` app
> (MK3S+); SL1/SL1S (SLA) · **Models:** the Prusa fleet that runs PrusaLink
>
> PrusaLink is a **host-side, LAN-local, plain-HTTP REST API** with **no push channel of any kind** — every piece of
> live state is obtained by **polling `GET /api/v1/status`**. It is the simplest of the networked stacks: one HTTP
> port, HTTP Digest auth, and a raw-`PUT` file upload.

## At a glance

- **Transport:** HTTP **`:80`** only (HTTPS only if the owner fronts it with their own reverse proxy). **No MQTT, no
  WebSocket, no SSE, no push.** State is **poll-only** — synthesize a change-event stream from the diffs (see
  [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md) §5, *poll-synth*).
- **Discovery:** manual IP is the guaranteed path; mDNS is advertised but the **service type is unconfirmed** (see
  Quirks). Identity via `GET /api/v1/info`.
- **Auth / credential:** **HTTP Digest** on the modern API (username `maker`, password set on the printer). A legacy
  OctoPrint-compatible tier uses an `X-Api-Key` header (disabled by default). Both are **user-owned** — read from the
  owner's own printer, never bundled.
- **Read / status:** **poll** `GET /api/v1/status` (printer block required; `job`/`transfer`/`storage`/`camera`
  optional). `job.progress` is **time-based**; times are in **seconds**.
- **File transfer:** a single **`PUT` of the raw file body** (`application/octet-stream`) to
  `/api/v1/files/{storage}/{path}`.
- **Print launch:** one-shot — `PUT` the file with a `Print-After-Upload: ?1` header; or upload then `POST` the same
  path to start.
- **Feeders / multi-material:** **presence only** — `info.mmu` is a bare boolean; the documented API exposes no
  per-slot filament state and no per-tool XL telemetry.
- **⚠️ The load-bearing gotcha:** there is **no setpoint control in the documented v1 API** — no endpoint to set nozzle
  or bed temperature, fan, or speed, and no emergency-stop. The core write surface is **job control + start only**;
  everything else is read-only. Treat temp/fan/speed as observable-not-settable.

## Transport & connection

A single plain-**HTTP** service on port **`:80`**. HTTPS appears only when the owner puts their own reverse proxy in
front — the device itself serves cleartext HTTP on the LAN. There is **no MQTT, no WebSocket, no SockJS, no SSE — no
subscribe of any kind**, so the entire live feed is **poll-derived**: an implementer runs a periodic
`GET /api/v1/status` (plus `GET /api/v1/job` when a job exists) and diffs successive snapshots into events. 🟡

Two API tiers live on the same host:

| Tier | Base path | Auth | Role |
|------|-----------|------|------|
| **Modern** | `/api/v1/*` | HTTP **Digest** | Primary surface: status, info, job control, files, storage, cameras, update. **Use this.** |
| **Legacy** | `/api/*` | **`X-Api-Key`** | An **OctoPrint-compatible subset** (`/api/version`, `/api/printer`, `/api/job`, `/api/files`) kept for slicer compatibility; ETag directory caching. |

Because the legacy tier is OctoPrint-shaped, an implementer targeting Prusa specifically should consume the native
`/api/v1` surface and use only `/api/version` from the legacy tier (for fingerprinting) — the rest of `/api/*` is
better handled by an OctoPrint client. 🟡

Error bodies are **content-negotiated** via `Accept`: `text/plain` **or** `application/json`. JSON error bodies carry
an optional `code` (a Prusa error identifier) and `url` (a help link); `Accept-Language` localizes some strings (e.g.
storage names). Sending `Accept: application/json` and surfacing `code`/`message` is the clean path. Standard HTTP
status codes apply (`400/401/403/404/408/409/503`). 🟡

## Discovery & identity

**Manual IP is the guaranteed path** and should be first-class in onboarding. PrusaLink is also discoverable over
mDNS, but **which service type it advertises is unconfirmed** (candidates include `_prusalink._tcp`, `_octoprint._tcp`,
or `_http._tcp`) and the TXT keys are unverified — treat auto-discovery as a nice-to-have layered on top of manual IP.
See [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md) §3. ⚪

Two identity endpoints:

- **`GET /api/v1/info`** → `serial` (the durable correlator), `hostname`, `name`, `location`, `mmu` (bool),
  `nozzle_diameter`, `min_extrusion_temp`, `sd_ready`, `farm_mode`, `active_camera`, `port`, `network_error_chime`. 🟡
- **`GET /api/version`** → `api`, `server`/`version`, `printer`, `firmware`, and a `capabilities` block that includes
  **`upload-by-put`** (whether the raw-PUT upload dialect is supported, vs a legacy multipart POST). 🟡

**Fingerprint:** the presence of `/api/v1/info` returning a Prusa `serial` (plus `capabilities.upload-by-put`)
distinguishes a real Prusa host from a **generic OctoPrint** (which lacks the `/api/v1` surface). Read identity first —
it lets a client confirm the device and pick the right client before committing to a session. 🟡

## Credentials / auth

Two mechanisms, one per tier — both **user-owned, obtained from the owner's own printer**:

1. **HTTP Digest** on `/api/v1/*` (`WWW-Authenticate: Digest` on an unauthenticated `401`). The username is the fixed
   literal **`maker`**; the **password is set on the printer** (PrusaLink settings / the printer's own screen). Digest
   is a standard challenge/response — the client answers the server's realm+nonce with an MD5 digest; any mature HTTP
   client with Digest support handles it with no extra dependency. This orchard documents *where the owner reads their
   password*, never a value. 🟡
2. **`X-Api-Key`** header on the legacy `/api/*` tier. The key is **disabled by default** (Digest is the preferred
   path) and, when enabled, is retrievable/regenerable from the printer's settings. 🟡

Validate a credential with an authenticated `GET /api/v1/info` (expect `200` and a Prusa `serial`). Community reports
suggest `X-Api-Key` may *also* be accepted on `/api/v1/*`, but this is **unspecified — do not rely on it**. See
[`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md) §2. 🔵

## Reading state

**Poll-only.** An implementer polls `GET /api/v1/status` — a combined object where only the `printer` block is
required and the rest degrade gracefully:

| Sub-object | Fields |
|---|---|
| `printer` (required) | `state` (enum below), `temp_nozzle`, `target_nozzle`, `temp_bed`, `target_bed`, `axis_x`, `axis_y`, `axis_z` *(axes present only when not moving)*, `flow` (%), `speed` (%), `fan_hotend`, `fan_print`, `status_printer{ok,message}`, `status_connect{ok,message}` |
| `job` (opt) | mirror of `GET /api/v1/job` |
| `transfer` (opt) | mirror of `GET /api/v1/transfer` |
| `storage` (opt) | mirror of `GET /api/v1/storage` |
| `camera` (opt) | active-camera summary |

`GET /api/v1/job` returns the current job: `id` (int), `state`, `progress` (%), `time_printing` (s),
`time_remaining` (s, optional), `inaccurate_estimates` (bool, optional), `file{name, display_name, path, size,
metadata, refs}`, and `serial_print` (bool — printing from the serial line). It returns **`204 No Content` when
idle**. **`job.id` is required to address every job command** (pause/resume/stop) — capture it from this endpoint. 🟡

- **Temperatures:** plain °C (`temp_nozzle`/`target_nozzle`, `temp_bed`/`target_bed`). 🟡
- **Times:** `time_printing` and `time_remaining` are in **seconds** (×1 — no minute/ms conversion). `transfer`'s
  `time_transferring`/`time_remaining` are seconds too. A common cross-brand unit trap — see
  [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md) §3. 🟡
- **Progress:** `job.progress` is **time-based** (a fraction of *time*, so `elapsed/progress − elapsed` extrapolation
  is valid), unlike file-byte-position progress on Klipper/OctoPrint. See
  [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md) §2. 🟡
- **Missing-field rule:** every field except `printer.state` is optional. `axis_*` is **intentionally absent while
  moving** — do not treat absence as `0`. A missing temp/fan/job block degrades gracefully.

**State enum (native → normalized).** `printer.state ∈` `IDLE`, `BUSY`, `PRINTING`, `PAUSED`, `FINISHED`, `STOPPED`,
`ERROR`, `ATTENTION`, `READY`. A reasonable normalization: 🟡

| Native | Normalized | Notes |
|---|---|---|
| `IDLE` | standby | no job |
| `READY` | standby (ready hint) | distinct from `IDLE` on Buddy firmware; collapse to standby but keep a `ready` hint |
| `BUSY` | printing (transient) | mid-operation (homing, loading) — not acceptable for a new job |
| `PRINTING` | printing | |
| `PAUSED` | paused | |
| `FINISHED` | complete | |
| `STOPPED` | cancelled | user/host stopped |
| `ERROR` | error | carries `status_printer.message` and an error `code` |
| `ATTENTION` | error / needs-user | **the printer is waiting on a human** (filament runout, MMU error, "remove print" dialog) — no clean cross-brand analogue (see Quirks) |

Job-level `job.state ∈` `PRINTING`, `PAUSED`, `FINISHED`, `STOPPED`, `ERROR` and maps the same way, driving the
progress fields any client needs (see [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md)).

**Poll cadence (implementer's choice, hardware-unvalidated):** roughly a 1–2 s status poll while active, backed off
when idle; hit `/api/v1/info` and `/api/version` only on connect and occasional refresh. Confirm the printer (a MINI's
modest CPU especially) tolerates the cadence on real hardware. ⚪

## Writing / control

PrusaLink exposes **typed, structured endpoints** for its whole control surface — there is **no raw-gcode passthrough
requirement** for the core operations (unlike Klipper, where temp/fan/speed need a gcode script). The trade-off is
that the surface is **narrow**:

| Intent | Endpoint | Result |
|---|---|---|
| Pause | `PUT /api/v1/job/{id}/pause` | `204` |
| Resume | `PUT /api/v1/job/{id}/resume` | `204` |
| Continue (after timelapse) | `PUT /api/v1/job/{id}/continue` | `204` |
| Stop / cancel | `DELETE /api/v1/job/{id}` | `204` |
| Start print (existing file) | `POST /api/v1/files/{storage}/{path}` | `204` — starts only if no job is running |
| Upload (+optionally start) | `PUT /api/v1/files/{storage}/{path}` | `201 Created` |

> ⚠️ **No documented setpoint endpoints** exist in `/api/v1` for nozzle/bed temperature, print speed, fan, or
> emergency stop. A client should declare those capabilities **absent** rather than assume a hidden path. Whether any
> setpoint control lives on the legacy `/api/printer` command surface is unconfirmed. 🟡

**File transfer & storage.** Storage roots come from `GET /api/v1/storage` → an array of `{name, type, path,
free_space, total_space}`. The first path segment `{storage}` selects the root; common roots are `usb` and a
local/`sdcard` root, but **which roots exist and which are print-capable is per-model and unconfirmed** — resolve them
from `/api/v1/storage` at connect rather than hardcoding. 🟡

The file endpoint `/api/v1/files/{storage}/{path}` supports:

| Method | Purpose | Key headers / body | Success |
|---|---|---|---|
| `GET` | file/folder metadata | `Accept`, `Accept-Language` | file/folder info + `metadata`/`refs` |
| `PUT` | **upload** file (or create folder) | body = raw bytes `application/octet-stream`; `Content-Length` (required); `Print-After-Upload: ?0\|?1`; `Overwrite: ?0\|?1` | `201 Created` |
| `POST` | **start print** if idle | — | `204 No Content` |
| `HEAD` | presence / state check | — | headers `Read-Only`, `Currently-Printed` (bool) |
| `DELETE` | delete file/folder | `Force: ?0\|?1` (force a non-empty folder) | `204 No Content` |

Boolean headers use the **`?0` / `?1` structured-header syntax** (`?1` = true) — a trap if a client sends `true`/`1`. 🟡

**Print-launch sequencing.** The one-shot flow is preferred: `PUT` the raw file body with `Content-Length`,
`Print-After-Upload: ?1` (and `Overwrite: ?1` only when replacing), get `201`, then **confirm by polling**
`GET /api/v1/job` / `GET /api/v1/status` for `state = PRINTING` and a `job.id`. The two-step flow — `PUT` without the
header, then `POST` the same path — is useful when you want to `HEAD`-verify the file landed before committing, or to
print a pre-existing file. **There is no synchronous "print started" ack** beyond the HTTP status; confirmation is by
state-poll (the stack is poll-only regardless). A `409 Conflict` signals a job already running or a busy file. 🟡

**In-flight transfer status.** `GET /api/v1/transfer` reports an upload/download in progress: `type ∈` `NO_TRANSFER`,
`FROM_WEB`, `FROM_CONNECT`, `FROM_PRINTER`, `FROM_SLICER`, `FROM_CLIENT`, `TO_CONNECT`, `TO_CLIENT` — plus
`display_name`, `path`, `progress` (%), `transferred` (bytes), `time_transferring` (s), `to_print` (bool), and
optional `url`/`size`/`time_remaining`. `DELETE /api/v1/transfer/{id}` aborts one. The `FROM_CONNECT`/`TO_CONNECT`
types reveal that the printer *also* talks to Prusa's **Connect cloud**; a LAN client only needs to **observe** these
(a file may be arriving from the cloud), never to drive Connect. 🟡

**File formats.** Buddy printers prefer **`.bgcode`** (binary gcode) and accept `.gcode`; SLA uses `.sl1`/`.sl1s`. A
client just streams the bytes; whether a given model rejects a non-`.bgcode` upload is unconfirmed. 🟡

**Cameras.** `GET /api/v1/cameras` lists cameras (`camera_id`, `config{path,name,driver,resolution}`, and
`connected`/`detected`/`stored`/`linked` flags — `linked` = registered to Connect). Snapshots come from
`GET /api/v1/cameras/snap` (default) or `/cameras/{id}/snap` → a **PNG** (or `204` if unavailable). This is
**snapshot-based, not a continuous stream** — surface it as a camera capability with a snapshot URL. 🟡

## Multi-material / feeders

**Presence-only — this is the headline finding.** The documented local API exposes multi-material as a single boolean:

- **`info.mmu` is a bare boolean.** There is **no per-slot filament state on the wire** — no per-slot type/color/
  material, no active-slot, no load/unload, no per-slot runout. (Prusa's MMU3 is a 5-slot unit; none of that detail is
  in the documented v1 surface.) 🟡
- **XL toolchanger:** the documented API has **no per-tool fields** at all — no per-toolhead temperature, offset, or
  active-tool. 🟡
- **SLA (SL1/SL1S):** no resin-tank/exposure telemetry appears in the shared schema. ⚪

So PrusaLink contributes only `has_multimaterial` to any neutral feeder model and must **not fabricate slot data** — a
clean example of a feeder member that supplies *presence* and degrades everything else. This is exactly the tolerance
the cross-vendor model is built for; see
[`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md). Whether *any* per-slot/per-tool
detail exists outside the documented v1 surface (e.g. on the legacy `/api/printer` telemetry) is an **open gap**. 🟡

## Quirks & gotchas

- **No setpoint control** (the big one, above): the documented v1 API has no temp/fan/speed/e-stop write. Job control
  + start is the entire write surface. 🟡
- **Poll-only, no push at all** — there is no notification channel; a client must poll and diff. Pick one definition
  of "elapsed"/"progress" and keep it.
- **`ATTENTION` and `READY` are near-unique states.** `ATTENTION` = "waiting on a human" (runout, MMU swap, a "remove
  print" dialog); it is not a hard error and not a clean run, and has no crisp analogue in the Anycubic/Klipper/Bambu
  enums. `READY` is distinct from `IDLE` on Buddy firmware. Map `ATTENTION` to a needs-user signal, not silently to
  plain `error`. 🟡
- **`axis_*` disappears while moving** — treat its absence as "unknown", never `0`.
- **Boolean headers are `?0`/`?1`**, not `true`/`false` or `0`/`1` — the structured-header convention on
  `Print-After-Upload`, `Overwrite`, `Force`.
- **`job.id` is mandatory to control a job**; read it from `/api/v1/job` first (which returns `204` when idle).
- **`.bgcode` preference** — Buddy firmware wants binary gcode; the acceptance of plain `.gcode` per model is
  unconfirmed.
- **The legacy `/api/*` tier is OctoPrint-shaped** — a client fingerprinting via `/api/version` + `/api/v1/info`
  should route real Prusa hosts to this surface and generic OctoPrint hosts to an OctoPrint client, to avoid two
  clients fighting over the same legacy paths.
- **Error bodies are content-negotiated** (`text/plain` or JSON with `code`+`url`) — send `Accept: application/json`.

## Confidence & validation

- 🟡 **Source-read from the vendor's own published OpenAPI 3.0.1 spec.** The API *shape* — paths, methods, field
  names, enum values, header names, the Digest/`X-Api-Key` split, the poll-only/no-push transport, the PUT-octet-stream
  upload, `info.mmu` being a boolean, and the absence of per-tool XL telemetry — is first-party-correct. **Nothing here
  is confirmed on real hardware**; this is an honest **partial / first-pass** paper.
- **Open gaps** (each closes with a capture from a hardware owner):
  - **mDNS service type + TXT keys** — sniff Avahi/Bonjour on a live printer, or read it off PrusaSlicer's *Physical
    Printers → Browse*. ⚪
  - **Digest realm/nonce behavior**, and whether `X-Api-Key` is genuinely accepted on `/api/v1/*` — an authenticated
    probe against hardware. 🔵
  - **Any per-slot MMU3 / per-tool XL data anywhere** (legacy `/api/printer`? a status sub-object?), and **whether any
    temp/fan/speed setpoint endpoint exists** — capture from a real MMU3 and a real XL. This is the single most
    valuable capture, since it decides whether "presence-only" and "read-only setpoints" hold.
  - **Per-model storage root names** and which are print-capable — `GET /api/v1/storage` on each model.
  - **`ATTENTION` triggers** and how to distinguish them from `ERROR` — induce a runout / MMU error.
  - **SLA (SL1/SL1S) telemetry shape** vs FDM (resin tank, exposure) — capture from an SL1S.
  - **Firmware/version skew:** the Buddy-firmware PrusaLink vs the Raspberry Pi `Prusa-Link` Python app — probe both
    for API parity.
  - **`POST`-to-start vs `Print-After-Upload` semantics** when a job is already queued/running — a hardware trial.
  - **Tolerable poll cadence** (rate limits, CPU on a MINI) — a sustained-poll trial.
  - **Per-model file-format acceptance** (`.bgcode` vs `.gcode`) — upload trials.

## Sources

Clean-room, facts-only. The primary source is Prusa's **own published OpenAPI 3.0.1 spec** for the local HTTP API
(`prusa3d/Prusa-Link-Web`, `spec/openapi.yaml`, AGPLv3) — used for *interface facts only* (paths, methods, field/enum
names, headers), not copied text. Cross-checked against the `prusa3d/Prusa-Link` server repository (behavior reference
only — **no code copied or vendored**, AGPLv3), the `home-assistant-libs/pyprusalink` client and the Home Assistant
PrusaLink integration (field-name cross-check), a generated DeepWiki API reference, and community notes (a
Raspberry-Pi-PrusaLink-over-HTTPS guide for the `:80`-default fact, Prusa forum threads for mDNS/Connect scope). No
AGPLv3 Prusa source code was reproduced; no secrets, certificates, passwords, API keys, serials, or real IPs appear —
credentials are described only as a mechanism (the owner reads their own Digest password from the printer). Passed
[`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md).
