# Klipper / Moonraker (generic) — LAN Protocol

> **Status:** 🟡 source-read (transcribed from Moonraker + Klipper's own docs/source; ecosystem-corroborated, no
> first-party hardware capture in this paper) · **Firmware:** Klipper (motion) + Moonraker (API host), both open
> source · **Models:** any Moonraker host — DIY Voron / RatRig / Sovol + a large cluster of vendor Klipper *forks*
> (Qidi, Elegoo Neptune, rooted Creality, Snapmaker U1…)
>
> Moonraker is the **HTTP + WebSocket JSON-RPC API** that sits in front of Klipper on `:7125`. It is the de-facto
> LAN backbone for a whole class of printers, so "support Moonraker" really means "support a family." The one thing
> to internalize: **there is no fixed schema** — a printer exposes only the objects its config defines, so you
> *enumerate*, you don't assume.

## At a glance

- **Transport:** JSON-RPC 2.0 over **HTTP + WebSocket** on **`:7125`** (also a Unix socket; Moonraker can itself be
  an MQTT *client*). File ops are **HTTP-only**; status subscriptions are **WebSocket-only**.
- **Discovery:** **manual IP is the baseline** (what Mainsail/Fluidd assume). Optional mDNS `_moonraker._tcp` and
  SSDP exist but are **off unless configured**.
- **Auth / credential:** often **none on a trusted LAN** (`trusted_clients`); otherwise an **API key** (`X-Api-Key`)
  or a JWT. The user reads/creates their own on their own host — nothing is bundled. See
  [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md).
- **Read / status:** **subscribe (WS)** returns a **full snapshot then sparse deltas**; or one-shot **query**.
  Capabilities are **presence-based** (`printer.objects.list`).
- **File transfer:** multipart `POST /server/files/upload` (optional SHA256 `checksum`).
- **Print launch:** upload, then `printer.print.start{filename}` (or `upload?print=true` to couple them).
- **Feeders / multi-material:** **none natively** — a *software provider* (Happy Hare, AFC, native TradRack) layers it
  on Klipper. Detect the provider, not the hardware.
- **⚠️ The load-bearing gotcha:** **`progress` is file-byte position, not time.** `virtual_sdcard.progress` /
  `display_status.progress` track *bytes streamed*, so naive `elapsed/progress` ETA is **systematically wrong near
  the end**. (And the object model is per-install: assume a fixed set of objects and you break on the next config.)

## Transport & connection

Everything is **JSON-RPC 2.0**. A request is `{"jsonrpc":"2.0","method":"<method>","params":{…},"id":<n>}`; the
response echoes the matching `id`; errors come back as a JSON-RPC `error` object with a `code` + `message`. Most
methods are reachable over **both** HTTP (`POST /printer/...`, `GET /server/...`) and the WebSocket, but the mapping is
**not 1:1** — **file upload/download is HTTP-only** and **`printer.objects.subscribe` is WebSocket/Unix-socket only**.
🟡

The WebSocket lives at `ws://<host>:7125/websocket`. After it opens, a client **should identify itself** via
`server.connection.identify` (fields: `client_name`, `version`, `type` ∈ `web|mobile|desktop|display|bot|agent|other`,
`url`, plus optional `api_key` / `access_token`); the reply carries a per-connection `connection_id`. 🟡

**Notifications** are unsolicited JSON-RPC messages (no `id`), `method` + optional `params` **array**: 🟡

- `notify_status_update` → `params` is a **2-element array**: `[ { <object>: { <changed fields only> } }, <eventtime> ]`.
  Element `[0]` is a **sparse delta**; `[1]` is Klipper's float event timestamp.
- `notify_gcode_response` → `[ "<response text>" ]`.
- `notify_klippy_ready` / `notify_klippy_shutdown` / `notify_klippy_disconnected` → **no `params`** (lifecycle).
- plus `notify_proc_stat_update`, `notify_history_changed`, and others.

**Reconnect posture:** retry the WebSocket on a timer until it connects, then run the readiness handshake (query
`server.info` until `klippy_state == "ready"`, or wait for `notify_klippy_ready`); watch for
`notify_klippy_disconnected` and repeat the handshake when it fires. The docs prescribe the loop but **not a backoff
curve** — an implementer picks one (e.g. ~1 s start, ~30 s cap). ⚪ Two more standing reminders: subscriptions live on
the WS and are **not restored for you** — **re-subscribe on every reconnect**; and key liveness on the transport +
`klippy_state`, not on a heartbeat.

## Discovery & identity

**Manual IP is the guaranteed path** — Mainsail and Fluidd normally connect to a hand-entered host or the reverse-proxy
origin they are served from, *not* auto-discovery. When present, discovery is a bonus, not the assumed path: 🟡

- **mDNS:** service type `_moonraker._tcp.local.` (a Moonraker-specific type, **not** generic `_http._tcp`); the TXT
  record advertises `uuid`, `version`, `route_prefix`. **Loaded only if `[zeroconf]` is in the config** — a stock
  Moonraker advertises nothing.
- **SSDP:** device type `urn:arksine.github.io:device:Moonraker:1` on `239.255.255.250:1900`; **off unless enabled**.

**Identity probes** (read these before committing to a session):

- `GET /server/info` — `klippy_connected`, `klippy_state` (`disconnected|startup|ready|error|shutdown`),
  `moonraker_version`, `api_version`, `components[]`. 🟡
- `GET /printer/info` — **only answers when Klippy is connected**: `state`, `hostname`, `klipper_path`, `config_file`,
  `log_file`, and a `software_version` in Klipper git-describe form (e.g. `v0.12.0-85-gd785b396`). A successful,
  internally-consistent `printer.info` is the **strongest "this is a real Klippy host" signal** — the endpoint is
  gated on an actual Klippy connection. 🟡
- `GET /machine/system_info` — host detail: `cpu_info` (incl. a sometimes-present `serial_number`), `network.<iface>.
  mac_address`, `distribution`, `sd_info`, `instance_ids` (systemd unit names). None of these is *both* universal and
  tamper-resistant, so they corroborate identity rather than define it. 🟡

**Durable ID:** Moonraker mints a persistent `instance_uuid` (a random `uuid4`) stored in `.moonraker.uuid` in its data
dir and in its database (`moonraker:instance_id`); it survives reboots and IP/hostname changes, and is advertised in the
zeroconf TXT `uuid`. Caveat: it is **not listed in the documented HTTP response bodies** of `server.info` / `printer.
info` / `machine.system_info` (source-read from Moonraker's `server.py`/`database.py`/`zeroconf.py`), and a synthetic
host could fabricate one — treat it as the *preferred* correlator but pair it with a corroborating fingerprint. 🟡 If
you also expose a Moonraker-compatible surface yourself, reject a target whose `uuid` equals your own to avoid a
self-registration loop. ⚪

## Credentials / auth

The local credential is the **user's own**, obtained from their own host — never bundled (see the
[credentials pattern](../patterns/discovery-and-credentials.md)). Modes, from the `[authorization]` config: 🟡

- **`trusted_clients`** — IPs / CIDR ranges / FQDNs that **bypass authentication entirely** (no key or token needed).
  Documented constraint: an IPv4 range's last octet must be `0` (e.g. `192.0.2.0/24`). On an open LAN this is why a
  Moonraker printer frequently needs **no credential at all**.
- **API key** — a static key supplied as the `X-Api-Key` header (HTTP) or the `api_key` param to
  `server.connection.identify` (WS). The user retrieves it from Moonraker (`access.get_api_key`) or their host UI.
- **JWT** — `Authorization: Bearer <token>` (HTTP) / `access_token` on identify (WS); the access token expires after
  **~1 hour**, refreshed from a longer-lived refresh token (~weeks, derived from example timestamps ⚪).
- **Oneshot token** — a single-use `?token=…` query param that **expires in ~5 seconds**, for contexts that can't set
  headers (the WS upgrade, browser limits).
- **`force_logins: true`** makes login mandatory once any user exists, **overriding `trusted_clients`**.

`cors_domains` governs browser cross-origin access only — it is **not** an auth layer and is largely irrelevant to a
non-browser client. For a headless integration the real gate is `trusted_clients` vs. key/JWT.

## Reading state

**Subscribe (the primary path).** `printer.objects.subscribe` with `params.objects` = a map of `{ <object>: null }`
(all fields) or `{ <object>: ["field", …] }` (a subset). The **response *is* the full initial snapshot** —
`{ eventtime, status: { … } }` — explicitly usable to seed local state without a separate query. Thereafter,
`notify_status_update` delivers **only the changed fields**; **deep-merge** each delta into local state field-by-field
and order by `eventtime`. `printer.objects.query` is the one-shot equivalent (same shape, no ongoing updates). 🟡

**Capabilities are presence-based — this is the core discipline.** An object exists only if its config section does,
and **named** objects are keyed by `"<section> <user-name>"` (e.g. `heater_generic chamber`, `fan_generic exhaust`,
`temperature_sensor mcu`). So: enumerate `printer.objects.list`; **resolve named objects by prefix** (the suffix is
user-chosen and arbitrary); and treat a missing object as **"not capable" / `null`, never an error**. Tolerate unknown
enum strings by passing them through as `unknown`. 🟡

Core objects and their load-bearing fields: 🟡

| Object | Fields you'll use | Notes |
|--------|-------------------|-------|
| `print_stats` | `filename`, `state`, `print_duration`, `total_duration`, `filament_used`, `info.current_layer`/`total_layer`, `message` | durations in **seconds**; `filament_used` in **mm** |
| `virtual_sdcard` | `progress` (0.0–1.0), `file_position`, `file_size`, `is_active` | ⚠️ `progress` = **file-byte position** |
| `display_status` | `progress` (0.0–1.0), `message` | also file-byte-derived |
| `toolhead` | `position`, `homed_axes`, `axis_minimum`/`axis_maximum` | homed-axes + travel limits gate motion |
| `extruder` / `heater_bed` | `temperature`, `target`, `power`, `can_extrude` | plain **°C** |
| `fan` | `speed` (0.0–1.0), `rpm` | `rpm` only if a `tachometer_pin` is set |
| `idle_timeout` | `state` (`Idle`/`Printing`/`Ready`) | |
| `pause_resume` | `is_paused` | |
| `gcode_move` | `speed_factor`, `extrude_factor`, `homing_origin` | live speed/flow multipliers |

Optional objects follow the same rule and simply appear when configured: `heater_generic *`, `temperature_sensor *`,
`temperature_fan */controller_fan */heater_fan *`, `bed_mesh`, `exclude_object`, `probe`/`bltouch`, `filament_switch_
sensor *`/`filament_motion_sensor *`, TMC driver objects, `mcu`/`mcu <name>`, `output_pin *`, and more. Absence is the
normal case. 🟡

**State (native → normalized).** `print_stats.state` has six documented values (the enum comes from Klipper source,
not the prose docs): `standby`→standby/idle; `printing`→printing; `paused`→paused; `complete`→complete;
`cancelled`→cancelled; `error`→error. Map any other string to `unknown`. 🟡

**Progress & timing — the trap.** Both `progress` fields are **file-byte position (bytes streamed ÷ file size)**, not
elapsed-time fraction, so extrapolating an ETA from them is wrong near the end of a print. Prefer a
firmware/metadata *time remaining*, or `estimated_time − elapsed` from file metadata, and fall back to time-based
extrapolation **only** where progress is time-based (Klipper's isn't). `print_duration`/`total_duration` are **plain
seconds (×1)** — copying a minutes-based parser from another brand here is exactly how the "11-minute print shows 112
hours" 60× bug spreads. `filament_used` is **mm** → convert to grams volumetrically. This is the canonical case in
[`../patterns/timing-normalization.md`](../patterns/timing-normalization.md) (§2 file-byte, §3 seconds). 🟡

## Writing / control

**Structured methods** (each returns `"ok"`): `printer.print.start{filename}`, `printer.print.pause`, `printer.print.
resume`, `printer.print.cancel`, and `printer.emergency_stop`. 🟡

> ⚠️ **Emergency stop must use `printer.emergency_stop`** — an out-of-band administrative shutdown. **Never** render
> `M112` through `printer.gcode.script`: a queued M112 sits behind the g-code queue and won't fire immediately,
> defeating the whole point.

Everything else — temperatures, fans, speed/flow factor, homing, motion — **has no structured endpoint** and travels
through `printer.gcode.script{script}`. The safe posture is that **an implementer owns typed templates and validates/
clamps every parameter**, rather than passing user- or plugin-supplied raw g-code down this path. Recommended
templates (typed params only): 🟡

- **Temperatures (no-wait):** `SET_HEATER_TEMPERATURE HEATER=<name> TARGET=<int>` — the extended command takes an
  explicit heater *name* (unambiguous across `extruder`, `heater_bed`, `heater_generic chamber`, …), which is why it
  is preferred over `M104`/`M140` (implicit tool index). The no-wait form doesn't stall the queue; `M109`/`M190`
  *block* and are deliberately not used for a fire-and-forget "set temp".
- **Fans:** `M106 S<0..255>` / `M107` for the single primary part-cooling fan (no name needed); `SET_FAN_SPEED
  FAN=<name> SPEED=<0.0..1.0>` for any *named* fan.
- **Speed / flow:** `M220 S<percent>` (speed factor), `M221 S<percent>` (extrude factor).
- **Motion (gate carefully):** `G28`/`G28 X|Y|Z` (home) and `G0`/`G1` with an explicit `G90`/`G91` mode line are
  **state-dependent** — a move requires homed axes and is unsafe mid-print. Gate behind a confirmed *homed* state, a
  *not-printing* check, and travel-limit validation; always emit the mode line immediately before the move.

`{name}` in any template must be **validated against `printer.objects.list`**, never trusted as free text — that
blocks both typos and injection of arbitrary object names. Clamp temps to a per-heater max, fan bytes to `0..255`,
percentages to sane bounds.

**File transfer & launch.** Multipart `POST /server/files/upload`: file field `file`; optional `root` (`gcodes`
default; `gcodes`/`config` are the only writable roots), `path` (subfolder, auto-created), `checksum` (SHA256 hex — a
mismatch returns **422**, free integrity checking), and `print` (`"true"` starts the print after upload). Success is
**HTTP 201** with a `Location` header and a body carrying `item{path,root,modified,size,permissions}`,
`print_started`/`print_queued`, and `action:"create_file"`. Read `/server/files/roots` for per-root permissions
(`config` may be read-only) rather than hardcoding. 🟡

Two launch strategies: `upload?print=true` is atomic but **couples** upload and start and hides a *started-vs-queued*
decision inside Moonraker; **separate calls** (upload with `print=false`, then `printer.print.start`) give an
implementer control over conflict policy, metadata (`/server/files/metadata`, forced via `metascan`), and start-now
vs. enqueue (`/server/job_queue`, a FIFO with `ready|loading|starting|paused`). Note two documentation gaps: the exact
condition that yields `print_queued` vs `print_started`, and **upload filename-conflict behavior** (overwrite vs.
error) — both undocumented, so check existence client-side before uploading. ⚪

> ⚠️ Control writes drive a hot, moving machine. Validate against your own device and gate them behind an explicit
> "enable writes" in any client.

## Multi-material / feeders

Klipper/Moonraker has **no native feeder concept** — multi-material is provided by a **software layer** on top of
Klipper, and the right move is to **detect the provider by object presence**, never by hardware brand. The full neutral
model (one opaque slot atom, an opaque per-adapter slot key, the print-time color→slot map) lives in
[`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md) — this section is just the Klipper-side
detection map. 🔵

- **Happy Hare** — the dominant provider. One object, **`printer.mmu`**, fronts most open MMUs at once (ERCF, Box
  Turtle-on-HH, Night Owl, TradRack-on-HH, QuattroBox, 3MS…), so reading *it* covers the family. Rich per-slot data:
  `gate`/`tool` (active slot / logical tool), `gate_status[]` (0 empty / 1 available / 2 from-buffer), `gate_material[]`
  / `gate_color[]` / `gate_color_rgb[]` / `gate_spool_id[]`, `ttg_map` (tool→gate), a nozzle-side `filament` load state,
  `action`, `endless_spool_groups`, plus an **optional `mmu.encoder`** sub-object (`flow_rate`, `headroom`) on
  encoder-equipped units. User ops are `MMU_*` macros / `Tn`.
- **AFC (Armored Turtle)** — Box Turtle's *native*, **Happy-Hare-incompatible** stack. Crucially, some AFC inventory is
  published through the **Moonraker database** (`GET /server/database/item?namespace=lane_data`) *in addition to* live
  Klipper status — so a reader must consult **both surfaces** to reconstruct full per-lane inventory (material, color,
  weight, spool id, PREP/LOAD sensor state, buffer).
- **Native TradRack** — its own `printer.trad_rack` object (`curr_lane`, `active_lane`, `next_lane`, `tool_map`,
  `selector_homed`) with **sparse** inventory (no native material/color) — the neutral "remaining/material" fields must
  degrade to `null`. (A TradRack run *under* Happy Hare instead appears as `printer.mmu`.)
- **Vendor MMUs on forks** — e.g. Creality's **CFS** surfaces through a vendor `[box]` Klipper module read via
  `printer.objects.query`, **not** the `[mmu]` shape. Detect the vendor object, surface read-only, and don't assume
  Happy-Hare command semantics.

Vocabulary note: Happy Hare's **gate** and AFC/TradRack's **lane** are the *same* neutral slot; a **tool** (`Tn`) is a
*logical* color index resolved to a physical slot via a tool→slot map — it is **not** a toolchanger toolhead. Keep the
namespaces distinct. Detection rule (presence-based, no brand strings): `mmu` in the object list ⇒ Happy Hare (covers
its many kits); else `trad_rack` ⇒ native TradRack; else an AFC object / the `lane_data` DB namespace ⇒ AFC; else no
feeder. 🔵

*(Toolchangers — multiple docking toolheads with per-tool offsets, e.g. inferred from several `extruder`/`extruder1…`
objects plus `Tn` macros — are a separate, orthogonal concern from feeders; don't collapse the two.)*

## Vendor variants

Generic Moonraker is the backbone; a large cluster of printers **reuse it with deltas**. The headline risk is a
device that **"claims Klipper" but ships a restricted or forked Moonraker** — so **never assume** a current version, the
standard port, root access, open LAN trust, or standard MMU objects. Probe `server.info` / `printer.info` /
`printer.objects.list` first and degrade gracefully. 🔵

**Open / reference tier — a standard client just works.** Generic upstream Klipper+Moonraker (KIAUH / Mainsail / Fluidd
on a Pi/SBC), **Voron** 2.4 / Trident / Switchwire, **RatRig** (RatOS = stock Moonraker + macros), **VzBot**, **Sovol
SV08 / SV08 Max** (vanilla Klipper, open LAN), and Ender/Prusa Klipper conversions. Stock port `:7125`, current
Moonraker, open LAN trust, standard objects. These are the validation baseline. 🔵

**Vendor-locked forks — feature-detect + degrade.** The Moonraker contract is *reachable* but modified:

| Family | Delta an implementer must handle |
|--------|----------------------------------|
| **Qidi** (Q1 Pro / Plus4 / X-Plus 3 / X-Max 3) | Pinned-**old** Moonraker missing newer endpoints; MKS board. Feature-detect the older API; don't assume the current endpoint set. |
| **Sovol** | SV08 line is effectively open (above); other models track vanilla Klipper. |
| **Rooted / stock Creality** | K1 / K1C / K1 Max: nginx-reverse-proxied, root historically via helper script (2025 firmware *removed* the root menu). K2 / K2 Plus / K2 Pro: Fluidd+Moonraker on **`:4408`** with **reserved-path / permission-locked** dirs, plus the **CFS** vendor `[box]` MMU. Discover the actual port; expect restricted paths. |
| **Elegoo Neptune 4 / 4 Pro / 4 Plus / 4 Max** | Vendor-modified, **pinned-old** Moonraker on an MKS board; Mainsail/Fluidd present. Closest of Elegoo's to stock — feature-detect the old Moonraker. |
| **Snapmaker U1** | A Klipper+Moonraker+Fluidd fork with a **`:8100` auth-wrapper bootstrap** and 4-toolhead toolchange via per-`extruder` objects + `T0–T3` macros (no confirmed `[toolchanger]` object). Its bootstrap + toolchanger specifics get their **own paper** — see [`snapmaker.md`](snapmaker.md). |

**Not Moonraker at all (out of scope here).** The **Elegoo Centauri Carbon** is marketed as Klipper-inspired but speaks
a proprietary **SDCP** WebSocket protocol with UDP discovery — it exposes **no Moonraker**. A Moonraker client should
classify it as "Klipper-marketed, non-Moonraker" and route it to the SDCP paper, not attempt to connect. 🔵

## Quirks & gotchas

- **No fixed schema.** Enumerate `printer.objects.list`, resolve named objects by **prefix** (the suffix is
  user-chosen), and map missing → not-capable, never error.
- **`progress` is file-byte position** (`virtual_sdcard`/`display_status`), not time — ETA from it is wrong near the
  end. Time fields are **seconds (×1)** — beware the 60× copy-paste bug. (Both in the timing pattern.)
- **E-stop is the structured method**, never a queued `M112`.
- **Subscriptions are WS-only and are *not* restored on reconnect** — re-subscribe every time. **File ops are
  HTTP-only.**
- **Discovery is off by default** — don't assume mDNS/SSDP will find anything; manual host entry is the baseline.
- **The durable `instance_uuid` isn't in the documented HTTP bodies** and is forgeable — corroborate identity with a
  real `printer.info` (git-describe `software_version` + consistent filesystem paths); that same check guards against
  accidentally self-registering another Moonraker-compatible endpoint.
- **Upload overwrite behavior is undocumented** — check existence client-side; and the **camera stream bypasses
  Moonraker auth** (nginx proxies `/webcam/` straight to ustreamer/camera-streamer), so API credentials don't gate it.
- **Vendor forks** bite in four predictable ways: pinned-old Moonraker (missing endpoints), non-standard ports,
  reserved-path/permission restrictions, and vendor-specific objects (CFS `[box]`, fork toolchanger macros).

## Confidence & validation

- 🟡 **The generic protocol is source-read, not hardware-validated in this paper.** Transport, JSON-RPC, the
  subscribe-snapshot-then-delta model, auth modes, the file API, core object fields, and the `print_stats.state` enum
  are transcribed from Moonraker's official docs + source and Klipper's docs + source (reference point: Moonraker
  ~`v0.10.0` / `8e948f1a`, Klipper ~`v0.13.0` / `c707dd19`, 2026-06-19). It is heavily **ecosystem-corroborated** —
  every Mainsail/Fluidd/KlipperScreen client speaks exactly this — but the "latest" docs are a rolling channel; re-verify
  optional-object shapes against a target host's actual version.
- 🔵 **Community-sourced:** Happy Hare / AFC / TradRack field sets (their wikis; drift between releases and selector
  variants), Creality CFS `[box]`, and every vendor-fork "openness" cell — those are **snapshots** that shift with OTA
  firmware.
- ⚪ **Reported-but-unverified here:** the reconnect backoff curve; the refresh-token exact lifetime; the upload
  filename-conflict behavior; and the `print_queued` trigger. Vendor-fork ports/versions are community-sourced 🔵 (e.g.
  Creality K2 `:4408`) and drift with OTA firmware — **probe** them, never hardcode.
- **Open gaps and the capture that closes each:** delta behavior over a long print (ordering/`eventtime`
  monotonicity, how a *removed* field is signalled); object-absence on minimal configs; reconnect/Klippy-restart
  recovery; the upload conflict + queued-vs-started branch; live MMU object shapes (Happy Hare vs AFC `lane_data`);
  whether `instance_uuid` is HTTP-readable on a real host; and the exact ports/versions of each vendor fork. A single
  multi-host field rig closes most of them.
- **Validation is accretive, never complete.** Klipper's config space is effectively unbounded (user configs, MMU
  variants, vendor forks), so a hardware pass can only ever claim "validated on *these* configs," never "all Klipper
  printers."
- **Fixtures:** none ship for this family yet. The `fixtures/` layout is defined (see
  [`../fixtures/README.md`](../fixtures/README.md)); a sanitized status/delta capture set — idle, printing, MMU,
  toolchanger, TradRack, plus temperature/MMU deltas — is the highest-value contribution to close the gaps above, and a
  real 🟢 hardware trace most of all.

## Sources

Clean-room, facts-only. Generic protocol transcribed from **Moonraker's own documentation** (external API:
introduction, server, printer, machine, authorization, file_manager, job_queue, webcams, jsonrpc_notifications; plus
configuration) and **source** (`server.py`, `components/database.py`, `components/zeroconf.py` for the `instance_uuid` +
discovery facts); **Klipper documentation** (Status_Reference, Config_Reference, G-Codes) with the `print_stats.state`
enum taken from Klipper source (`klippy/extras/print_stats.py`). Multi-material from the **Happy Hare** and **AFC
(Armored Turtle)** docs/wikis and the **TradRack** repo. Vendor-variant deltas from community reports and setup docs
(Voron/RatRig/Sovol/KIAUH/Mainsail/Fluidd; Qidi, Creality K1/K2, Elegoo Neptune/Centauri, and Snapmaker U1
communities). No code was copied; all JSON shapes are described or shown as synthetic/sanitized examples; no
certificates, keys, tokens, access codes, or real IPs appear. Passed
[`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md).
