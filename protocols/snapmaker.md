# Snapmaker (U1) — LAN Protocol

> **Status:** 🟡 source-read (hardware-unvalidated) · **Firmware:** Klipper + Moonraker, behind a Snapmaker
> auth/pairing wrapper · **Models:** Snapmaker U1 (2026 CoreXY multi-tool). *Older networked Snapmakers
> (A-series / Artisan / J1) use a different, older HTTP-token + USB-serial stack — out of scope here.*
>
> Underneath, the U1 **is a Moonraker printer**: its own control app drives it with standard Moonraker JSON-RPC. On top
> sits a Snapmaker HTTP control/pairing API on **`:8100/api`** and a **toolchanger** filament→tool assignment.

## At a glance

- **Transport:** **Moonraker JSON-RPC 2.0** (HTTP + WebSocket) for status/control/files, *plus* a Snapmaker HTTP
  control API on **`http://<ip>:8100/api`** for pairing and high-level orchestration. See
  [`klipper-moonraker.md`](klipper-moonraker.md) for the base protocol.
- **Discovery:** **manual IP** is the guaranteed path. Fingerprint Snapmaker-vs-generic-Moonraker by probing
  `:8100/api`. mDNS / UDP broadcast unconfirmed.
- **Auth / credential:** a **device-approval pairing** — an **`authCode`** (presence proof, approved at the printer) and
  an **`accessCode`** (session credential); a **`link_mode`** flag selects `lan` (local) vs `wan` (cloud).
- **Read / status:** standard Moonraker — `printer.objects.subscribe` push over WebSocket + a poll fallback; state from
  `print_stats`; **file-byte progress**; time in **seconds**.
- **File transfer:** Moonraker multipart `POST /server/files/upload`, wrapped by a 3-step `:8100`
  create → transfer → complete orchestration.
- **Print launch:** high-level `POST :8100/api/device/play`, **or** the Moonraker `printer.print.start` JSON-RPC.
- **Feeders / multi-material:** a **true toolchanger** (multiple physical tools, each its own hotend + nozzle), not a
  feeder — a filament→tool map (`extruder_map_table` / `extruders_used`) rides the launch.
- **⚠️ The load-bearing gotcha:** it is **not yet confirmed whether Moonraker is reachable directly on the LAN or only
  behind the `:8100` auth gate** — that decides whether the session token must be injected into every Moonraker call.

## Transport & connection

The U1 speaks **two layers on the same box**:

**1. Moonraker JSON-RPC 2.0 (the real protocol).** Requests are the standard envelope — a `jsonrpc`/`method`/`params`
object where the method is a `<namespace>.<verb>` string. The namespaces observed in the vendor's own control app are
standard Moonraker: `printer.*` (e.g. `printer.info`, `printer.objects.subscribe`/`query`,
`printer.print.start`/`pause`/`resume`/`cancel`, `printer.emergency_stop`), `machine.*` (`machine.system_info`,
`machine.reboot`, `machine.services.*`), `server.*` (`server.info`, `server.connection.identify`, `server.files.*`), and
`system.*`. Two extra namespaces are Snapmaker additions: **`camera.*`** (a camera scope) and **`custom.*`** (the
U1-specific verbs — tool/material ops — treat these as device-local). 🟡

Live status arrives the standard Moonraker way: a **WebSocket** carrying server-push `notify_*` notifications
(`notify_status_update`, `notify_proc_stat_update`), *plus* two Snapmaker-only ones — `notify_link_mode_update` and
`notify_disconnecting_lan_client`. File operations hit **literal Moonraker HTTP endpoints**: `GET /server/info`,
`POST /server/files/upload`, `GET /server/files/gcodes/<name>`. 🟡

Because the wire is genuinely Moonraker, a client's entire Moonraker read/transport layer applies unchanged — Snapmaker
did **not** fork the protocol, they wrapped it with auth and added `custom.*` verbs.

**2. The Snapmaker `:8100/api` control layer.** Alongside Moonraker, the U1 exposes an HTTP control API on port
**`:8100`**, base path `/api` (the real base is resolved per-device). This is where pairing, high-level print control,
the upload orchestration, and camera live. Endpoints seen in the control app: 🟡

| Endpoint (`:8100/api` base) | Purpose |
|-----------------------------|---------|
| `/device/connect/auth` | Pairing handshake (see Credentials) |
| `/device/upload/create` → *(transfer)* → `/device/upload/completed` \| `/device/upload/cancel` | Multi-step upload orchestration (wraps the Moonraker upload) |
| `/device/play` · `/device/pause` · `/device/stop` | High-level print control |
| `/device/unbind` | Drop the pairing |
| `/device/videoPlay` · `/device/videoCall` | Camera / video |
| `/device_info` · `/device_control` | Status / control surface |
| `/status` · `/token` | Session state / token |
| `/files/upload` · `/files/gcodes/…` · `/files/filament` | File management (Snapmaker forms of the Moonraker file ops) |

> ⚠️ **Open question (the biggest one):** whether raw Moonraker (`/server/*` HTTP + the JSON-RPC WebSocket) answers
> **directly** on the LAN, or **only once paired** (i.e. the `accessCode`/token must be presented before Moonraker
> replies). The app clearly uses **both** the `:8100/api/device/*` control verbs **and** raw `/server/*` Moonraker paths,
> so the U1 certainly runs Moonraker — only the auth boundary is unconfirmed. This decides whether an implementer can
> use a stock Moonraker client verbatim or must inject the session token into every call. ⚪

## Discovery & identity

**Manual IP is the guaranteed path** — the LAN-add flow includes an explicit manual-IP entry screen. Treat
auto-discovery as a nice-to-have: whether the U1 answers mDNS or a Snapmaker UDP broadcast on the LAN is unconfirmed
(the cloud/WAN path uses the Snapmaker account API for device lists, which is not LAN discovery). 🟡

**Fingerprint** (Snapmaker vs a generic Moonraker printer): probe `:8100/api` first — a Snapmaker answers there
(`/device_info` responds), a plain Moonraker box has nothing on `:8100`. Secondary tells: the model string in
`printer.info` / `machine.system_info`, the `custom.*` methods, and the `notify_link_mode_update` notification are all
Snapmaker-specific. 🟡

**Identity** on connect is `(ip, sn [serial], authCode/accessCode)`, with `macAddress`, `nickname`, and `model` also
surfacing. 🟡 See [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md) for the shared
onboarding shape (manual-IP + identity probe + LAN mode).

## Credentials / auth

The U1 uses a **device-approval pairing flow** — you prove local presence, the way Bambu's bind / access-code and
Prusa's pairing do. Two credentials appear, **both user-owned** (the owner obtains them from their own printer; a client
prompts for them and stores them **encrypted at rest** — it never bundles or ships a value): 🟡

- **`authCode`** — a **pairing code** the user obtains via the printer; the connection is gated on it (`"authCode is
  required"`). This is the presence-proof credential.
- **`accessCode`** — the **session/access credential** carried alongside the connect request (with `clientId`, the
  serial `sn`, and the `authCode`).

**`link_mode`** selects the path: 🟡

- **`"lan"`** — a direct local connection to the printer (Moonraker + the `:8100` auth, all on the LAN, no cloud). This
  is the local-interop target; a LAN-only client should **hard-select `lan`**.
- **`"wan"`** — a cloud/remote path via Snapmaker's MQTT + account service (topic sets, a user id, `ca`/`cert`/`key`, a
  bearer token). Documented only so a client can avoid it; out of scope for local operation.

The pairing surfaces a small **connection state machine** — `authorizing → authorized | rejected | notAuthorized |
discontinue`. 🟡 The exact acquisition lifecycle (where the code is displayed, its TTL, whether a reboot forces
re-pairing) needs a hardware capture — see *Confidence & validation*.

## Reading state

The read path is **standard Moonraker** — subscribe to `printer.objects` over the WebSocket and diff, with a periodic
`printer.objects.query` as a poll backstop. The full Moonraker object set (toolhead, one extruder object per tool,
`print_stats`, `virtual_sdcard`, heaters, fans) is available; the U1 adds its material/tool state under `custom.*`. See
[`klipper-moonraker.md`](klipper-moonraker.md) for the object shapes. 🟡

- **State (native → normalized):** Moonraker's `print_stats.state` —
  `standby`→standby, `printing`→printing, `paused`→paused, `complete`→complete, `cancelled`→cancelled, `error`→error.
- **Temperatures:** plain °C from the heater objects (current + target). 🟡
- **⚠️ Progress is file-byte, not time-based.** Moonraker's `virtual_sdcard.progress` is the fraction of the *g-code
  file* streamed, **not** the fraction of *time* elapsed — so extrapolating an ETA from it is systematically wrong near
  the end of a print. Prefer a firmware-reported time-remaining or a slicer estimate. 🟡
- **Times are in seconds** (Moonraker convention) — do not multiply by 60. Both traps are covered in
  [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md).
- **Heartbeat / liveness:** the control app runs a `machineHeartbeat` keepalive, but some firmware modules answer
  *"machineHeartbeat is not supported, use get…"* and fall back to a status poll. Treat this purely as liveness — key it
  on the transport connection plus a staleness timer; don't depend on a heartbeat message existing. 🟡

## Writing / control

Two overlapping command surfaces:

- **Moonraker verbs** (JSON-RPC): `printer.print.start`/`pause`/`resume`/`cancel`, `printer.emergency_stop`, and
  arbitrary G-code via the gcode-script method — the standard Moonraker control vocabulary. 🟡
- **High-level `:8100` verbs:** `POST /device/play`, `/device/pause`, `/device/stop`. 🟡

**Print-launch sequence:** 🟡

1. **Create** — `POST :8100/api/device/upload/create` announces the file.
2. **Transfer** — the bytes go to Moonraker `POST /server/files/upload` (multipart); the Snapmaker `/files/upload` is
   the same operation under Snapmaker's naming.
3. **Complete** — `POST :8100/api/device/upload/completed` (or `/cancel` on abort).
4. **Print** — either the high-level `POST :8100/api/device/play` **or** the Moonraker `printer.print.start {filename}`.
   The **toolchanger `extruder_map_table` / `extruders_used`** assignment travels with the launch (see below).

The endpoints are source-confirmed; **which launch verb is authoritative and its exact payload — including where the
toolchanger map rides — is a hardware-capture gap.** ⚪

> ⚠️ Control writes and tool operations drive a hot, moving multi-tool machine. Validate every write against a real
> device and gate it behind an explicit "enable writes" in any client.

## Multi-material / feeders (toolchanger)

The U1 is a **true toolchanger** — multiple **physical** tools, each with its own hotend and nozzle — which is
**orthogonal to a feeder** (a feeder is N inputs → *one* hotend; a toolchanger is N docked toolheads). Model it on the
neutral tool/feeder surface but keep per-tool **nozzle geometry** first-class, which feeders don't have. See the
toolchanger distinction in [`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md). 🟡

The launch-time **filament→tool assignment** is the same idea as Bambu's `ams_mapping` and Elegoo CANVAS's `slot_map`
(the print-time slot map in that pattern). Field names seen in the control app: 🟡

| Field | Meaning |
|-------|---------|
| `extruder_map_table` | The mapping table: sliced-filament index → physical tool/extruder. The core assignment. ⚪ *(shape inferred from name)* |
| `extruders_used` | Which physical tools this job actually engages (a subset of those installed). ⚪ |
| `nozzle_diameters` / `nozzle_sizes` | Per-tool nozzle-diameter **list** (multi-tool ⇒ a list, not a scalar); drives a nozzle-mismatch check. 🟡 |
| `filament_sub_type`, `filament_edit`, `filament_exist` | Per-slot filament metadata / presence used to build the map. 🟡 |
| `toolhead`, `swap`, `extruder_velocity` | Tool-swap mechanics surfaced in the control UI. 🟡 |

The UI presents a dedicated filament→tool assignment screen before launch — the direct analog of a slicer's AMS-mapping
dialog. 🟡

**Read vs control.** A **read** is safe and standard: surface the installed tools, per-tool nozzle diameter, per-tool
filament/presence, and the active tool — all from Moonraker `printer.objects` (toolhead/extruder) plus the U1
`custom.*` material state. **Control** (tool-select, tool offsets, the `tfree`/`tpre`/`tpost` change sequence, and the
launch-time `extruder_map_table` write) is dangerous-tier — gate it behind auth + explicit writes and hardware-validate.

> ⚠️ The **exact JSON encoding** of `extruder_map_table` (array of `{filament, tool}` objects? a positional list?) and
> which launch it rides are **unconfirmed** — document the field names from source, ship any map write
> gated/experimental until a real-U1 capture confirms the join. ⚪

## Quirks & gotchas

- **The auth boundary is unconfirmed** — direct LAN Moonraker vs Moonraker-only-behind-`:8100`. The single most
  important thing to pin on hardware.
- **It's a toolchanger, not a feeder** — model per-tool nozzle geometry (diameter/offsets), don't force it into a
  single-hotend feeder shape.
- **Progress is file-byte, not time-based** (Moonraker `virtual_sdcard.progress`) — don't derive an ETA from it.
- **Times are seconds** — the Moonraker convention; no ×60.
- **`machineHeartbeat` may be unsupported** on some modules → fall back to a status poll for liveness.
- **`link_mode`** — hard-select `lan` for local operation; `wan` is the cloud/MQTT path.
- **U1 only.** The older networked Snapmakers (A150/A250/A350, Artisan, J1) run a *different, older* HTTP-token +
  USB-serial stack — a separate protocol, not this one. Don't conflate them.

## Confidence & validation

- 🟡 **Everything here is source-read and hardware-UNVALIDATED.** The wire *shape* is first-party-correct — it is read
  from the vendor's **own** control app (the string constants embedded in its compiled bundle) — but **no field has been
  confirmed against a real U1** (no bench hardware was available). Treat the structure as reliable and validate live
  values/behavior before shipping writes.
- **Open gaps** (each closes with a real-U1 capture — a LAN trace during connect + a multicolor print):
  - **Auth boundary (highest):** is Moonraker reachable directly, or only behind the `:8100` gate? Does the session
    token need injecting into every `/server/*` + JSON-RPC call?
  - **Pairing lifecycle:** where the `authCode` is displayed, its TTL, and whether a reboot forces re-pairing.
  - **`extruder_map_table` / `extruders_used`:** exact JSON shape, and which launch it rides (`printer.print.start`
    params vs the `:8100/device/play` body vs sliced-file metadata).
  - **`custom.*` catalog:** the full U1-specific method list + the material/tool object names (per-tool nozzle diameter,
    active tool, presence) to complete the toolchanger read.
  - **LAN auto-discovery:** does the U1 answer mDNS or a Snapmaker UDP broadcast, or is manual-IP the only LAN path?

## Sources

Clean-room, facts-only. Extracted from Snapmaker's own published OrcaSlicer fork (GPL) — specifically the committed
Flutter web control app that ships inside the slicer as the U1's embedded control panel, read as a **compiled/shipped
artifact** (URL, method-name, and JSON-key **string constants** survive minification, so they are interface facts, not
copied expression), plus the U1 design docs. Only interface facts (endpoints, method/field names, state enums) were
taken; **no code was copied**, and the `authCode`/`accessCode` are **user credentials** obtained by the owner from their
own printer — none is bundled or reproduced. For the underlying protocol see [`klipper-moonraker.md`](klipper-moonraker.md).
Passed [`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md).
