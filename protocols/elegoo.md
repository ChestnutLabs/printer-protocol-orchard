# Elegoo (Neptune / OrangeStorm / Centauri) — LAN Protocol

> **Status:** 🟡 source-read (grounded in Elegoo's own first-party LAN SDK; SDCP additionally 🔵 community
> firmware-validated) · **Firmware:** Klipper/Moonraker (Neptune, OrangeStorm) · SDCP (Centauri Carbon 1) ·
> proprietary MQTT (Centauri Carbon 2) · **Models:** Neptune 4 family, OrangeStorm Giga, Centauri Carbon 1 / 2 / 2 Combo
>
> Elegoo is **not one protocol — it is a brand covering three unrelated LAN stacks**, plus one shared multi-material
> unit (CANVAS). Pick the backend by **model** first; everything else follows from that choice.

## At a glance

Elegoo's line splits into three wire protocols. The one thing to know: **there is no common Elegoo protocol** — an
implementer routes each model to the right stack.

| Backend | Models | Transport | Notes |
|---------|--------|-----------|-------|
| **Moonraker / Klipper** | Neptune 4 / 4 Pro / 4 Plus / 4 Max, OrangeStorm Giga | HTTP + WebSocket JSON-RPC **`:7125`** | Stock, plain Moonraker — see [`klipper-moonraker.md`](klipper-moonraker.md). Only per-model deltas here. |
| **SDCP** | Centauri Carbon **1** (+ CANVAS) | JSON-over-WebSocket **`:3030`** + UDP **`:3000`** discovery | Topic-carrying WS, **not** JSON-RPC; a genuinely separate stack. |
| **Proprietary MQTT** | Centauri Carbon **2** / 2 Combo | MQTT **`:1883`** + HTTP **`:80`** upload + UDP **`:52700`** discovery | Printer runs its own broker; access-code auth. |

- **Discovery:** manual IP is first-class on every path. Auto: SSDP/mDNS (Moonraker), UDP `M99999`→`:3000` (SDCP),
  UDP `{"id":0,"method":7000}`→`:52700` (CC2).
- **Auth / credential:** Moonraker — none per-device (optional oneshot-token handshake) · SDCP — **none at all**
  (LAN-trust) · CC2 — an **access code** the owner reads off the printer screen (see Credentials).
- **Read / status:** Moonraker — subscribe · SDCP — **passive push** (no subscribe command) + a `Cmd 0` poll floor ·
  CC2 — push + a `1002` poll.
- **Print launch:** all three are **upload-then-start** over a *separate* channel from the control channel.
- **Feeders:** CANVAS — a 4-slot RFID feeder that reports material/color/temp but **no remaining quantity and no RFID
  UID**; fetched by a **separate query**, not in the status stream.
- **⚠️ The load-bearing gotcha:** on **SDCP (CC1)**, sending an **unrecognized command — or an incomplete start
  command — can crash the printer daemon and kill an active print.** The whole SDCP control path is shaped around
  avoiding that (idle-gating, always-complete start payload, a mandatory post-upload settle).

---

## Transport & connection

### Moonraker path (Neptune 4 family, OrangeStorm Giga)

Stock, unmodified **Moonraker HTTP + WebSocket JSON-RPC on `:7125`** — the standard stack documented in
[`klipper-moonraker.md`](klipper-moonraker.md). Elegoo's own SDK ships a **model-agnostic** Moonraker client (no
per-model logic), which is first-party confirmation that these printers need no bespoke code. 🟡 Elegoo-specific
transport notes:

- The firmware is a **pinned, older Moonraker fork on a locked appliance image** (the stock config carries an explicit
  warning against updating Klipper/Fluidd/Moonraker yourself, stating the machine will otherwise stop working). Treat any newer endpoint/field as
  **maybe-absent** and degrade rather than assume. 🟡
- The **web UIs are on non-standard ports** (Fluidd `4408`, Mainsail `4409`), but **Moonraker itself is still
  `:7125`**. 🔵
- If the target Moonraker enforces auth, open with a **`GET /access/oneshot_token`** handshake before the socket —
  the SDK's client does this. 🟡

### SDCP path (Centauri Carbon 1)

**One WebSocket server, two roles.** The printer listens on **`ws://<ip>:3030/websocket`** (plain, no TLS); the same
`:3030` server also answers the HTTP file-upload endpoint. 🟡

- **Not JSON-RPC 2.0.** Each frame is a nested JSON object — an outer routing layer wrapping an inner command object:
  🟡
  ```jsonc
  { "Id": "<machine UUID>", "Topic": "sdcp/request/<MainboardID>",
    "Data": { "Cmd": 128, "Data": { /* command params */ },
              "RequestID": "<client hex>", "MainboardID": "<id>",
              "TimeStamp": 0, "From": 1 } }
  ```
- **Correlation is by an echoed `RequestID`** (a client-generated hex string), *not* a JSON-RPC `id`. Requests go on
  `sdcp/request/<MainboardID>`; the ack/result returns on `sdcp/response/<MainboardID>` echoing that `RequestID`. 🟡
- **Topic grammar** (the frame carries its own `Topic`, MQTT-like): `sdcp/request` (client→device),
  `sdcp/response` (acks, echoes `RequestID`), `sdcp/status` (**pushed** state), `sdcp/attributes` (static
  identity/caps), `sdcp/error`, `sdcp/notice` — each suffixed `/<MainboardID>`. 🟡
- **`From`** is a source enum; a LAN client sends `From:1` (the SDK does the same). Full set: `0`=PC/LAN, `1`=WEB_PC,
  `2`=WEB, `3`=APP, `4`=SERVER. 🟡
- **Connection limits:** **5 concurrent WS connections** (a 6th connect returns HTTP 500), and a **60 s idle timeout**
  closes the socket. Reuse **one long-lived, auto-reconnecting socket per printer** and keep it warm with a periodic
  `Cmd 0` (there is no subscribe command to lean on). 🔵
- **FDM-on-a-resin-envelope caveat:** the published SDCP v3.0 spec is written for resin (MSLA) machines; the Centauri
  Carbon is FDM and reuses the same envelope, discovery, and `Cmd` codes but substitutes FDM field names and
  **re-purposes the status enum** (see Reading state). 🟡

### CC2 path (Centauri Carbon 2 / 2 Combo)

**The printer runs its own MQTT broker; a client connects to it.** Control rides MQTT; file bytes ride a separate HTTP
server on the same box. 🟡

- **Transport is `tcp://<ip>:1883` only** — MQTT 3.1.1, clean session, keepalive 60 s, QoS 1. There is **no
  WebSocket / no `:9001`** (a common community claim; the first-party SDK builds only the TCP URL). 🟡
- **Serial-scoped topics:** `elegoo/<sn>/api_register` (pub), `.../<requestId>/register_response` (sub),
  `.../api_status` (pushed status, sub), `.../<clientId>/api_request` (commands, pub),
  `.../<clientId>/api_response` (sub). The **serial number `<sn>` is a literal segment of every topic.** 🟡
- **Envelope** is JSON-RPC-*ish* but not real JSON-RPC: commands are `{"id":<int>, "method":<int>, "params":{…}}`;
  replies are `{"id":<same>, "result":{…}}`, correlated on `id`. Unsolicited status pushes arrive via push method
  `6000` (attributes via `6008`). 🟡
- **`clientId` format** is `"1_PC_"` + a random 4-digit number, reused as the `requestId`. 🟡
- **Mandatory registration handshake, per connection:** subscribe the three topics above, then publish to
  `api_register`; success is a `register_response` with `error=="ok"` and a matching `client_id`. The printer keeps
  **no session state across TCP drops**, so **re-register on every reconnect.** 🟡
- **Heartbeat** is exactly `{"type":"PING"}` every ~10 s on the **command** topic (`.../api_request`), accepted on a
  JSON `type=="PONG"`; timeout ~65 s. (There is no dedicated heartbeat topic.) 🟡
- **Connection cap is printer-enforced with no numeric constant** — an over-limit register attempt returns the string
  `"too many clients"`. Don't hardcode a number. 🟡

## Discovery & identity

Manual IP entry works on all three paths; auto-discovery is a convenience. See
[`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md).

| Path | Mechanism | Identity key returned |
|------|-----------|-----------------------|
| Moonraker | SSDP / mDNS (Moonraker answers standard discovery); or manual IP | no stable vendor model id — supply a friendly name yourself |
| **SDCP (CC1)** | UDP broadcast of the 6-ASCII-byte string **`M99999`** to **`:3000`**; each board replies with one JSON datagram | **`MainboardID`** — the stable identity *and* the routing key in every topic |
| **CC2** | UDP broadcast of **`{"id":0,"method":7000}`** to **`:52700`**; reply is `{"id":…,"result":{…}}` | **serial (`sn`)** — the topic identity |

- **SDCP discovery** datagram carries `Name`, `MachineName` (e.g. the model string), `MainboardID`, `MainboardIP`
  (used as the WS host), `ProtocolVersion`, `FirmwareVersion` (stored with a leading `V` stripped). 🟡 A wrong
  `MainboardID` means you publish/subscribe to topics the printer never touches — a **silent no-op**, not an error.
- **CC2 discovery** reply carries `host_name`, `machine_model`, `sn`, `token_status` (`1` ⇒ an access code is
  required), `lan_status`, and `authMode:"accessCode"`. 🟡 A wrong `sn` is likewise a silent no-op.
- Moonraker exposes **no stable model id**, so a "model" here is a user-assisted display/geometry overlay (name +
  build volume), never a dispatch key. Advertised build volumes: Neptune 4 / 4 Pro 225×225×265, 4 Plus 320×320×385,
  4 Max 420×420×480, OrangeStorm Giga 800×800×1000 mm. 🟡 Prefer the live `toolhead.axis_maximum` when present.

## Credentials / auth

Three postures — one per path — and this is where they diverge most:

- **Moonraker (Neptune / Giga):** **no per-device credential** in the common case. If the unit enforces Moonraker
  auth, obtain a session via the standard **`GET /access/oneshot_token`** handshake before opening the socket. See
  [`klipper-moonraker.md`](klipper-moonraker.md). 🟡
- **SDCP (CC1):** **no authentication at all** — no handshake, no password, no token. The WS is open on the LAN; the
  only gates are the 5-connection cap and the 60 s idle timeout. There is no credential to collect or store, and no
  TLS. 🟡🔵 (LAN-trust; an implementer should keep the client cloud-out.)
- **CC2:** a single **access code** is both the MQTT password (with a fixed username `elegoo`) *and* the HTTP upload
  `X-Token`. The owner reads it from the printer's **network-settings screen**, and **LAN mode must be enabled**.
  Document the *mechanism*, never a value — an integration prompts the owner for their own code and, since it's a
  per-printer secret, should store it encrypted at rest. An empty/unset code falls back to a documented default, so a
  freshly-provisioned printer may accept the default until the owner sets one. 🟡 See
  [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md).

## Reading state

### Moonraker path

Standard Klipper object-model reads (temps, `print_stats`, `virtual_sdcard`, fans, etc.) — see
[`klipper-moonraker.md`](klipper-moonraker.md). Two Elegoo deltas worth flagging:

- **OrangeStorm Giga has a segmented, multi-zone bed** exposed as `heater_bed` plus `heater_generic heater_bed1/2/3`.
  These are **bed zones, not a chamber** — an implementer that folds `heater_generic *` into "chamber" will mislabel
  them; exclude `heater_generic heater_bed*` from any chamber mapping. 🔵
- The Giga's optional multi-nozzle upgrade is **IDEX (`[dual_carriage]` + `extruderN`), not a docking toolchanger** —
  it surfaces correctly as *multiple extruders*, and IDEX *mode* (copy/mirror) over the wire is uncaptured. 🟡
- **Progress is file-byte position** (Moonraker `virtual_sdcard.progress`), so ETA-from-progress is unreliable near
  the end; times are **seconds**. See [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md).

### SDCP path (CC1)

Status is a **passive push** on `sdcp/status/<MainboardID>`; a client can force a refresh with `Cmd 0` (which replies
on the same topic). **There is no subscribe command** — state simply arrives. The frame carries a top-level machine
status, a nested `PrintInfo` job block, and temperature/fan/coordinate blocks. 🟡

**Two enums, both load-bearing** (keep them distinct):

- **Top-level `CurrentStatus` (0–11)** — the *machine* state, and **the idle gate keys off `CurrentStatus == 0`**
  (IDLE). `1`=PRINTING, `2`=FILE_TRANSFERRING, `8`=FILE_CHECKING, `9`=HOMING, others busy/transient. 🟡
- **`PrintInfo.Status` (0–26)** — the *job* sub-status, the real lifecycle signal:

  | Native → normalized | Codes |
  |---------------------|-------|
  | standby | `0` IDLE |
  | preheating / startup | `1` HOMING, `15` AUTOLEVELING, `16` PREHEATING, `18` PRINT_START, `19`/`21`/`22` *_COMPLETED |
  | printing | `13` PRINTING (FDM active), `10`/`11` checking |
  | paused | `5` PAUSING, `6` PAUSED |
  | resuming | `12` RESUMING |
  | cancelled | `7` STOPPING, `8` STOPED *(sic)* |
  | complete | `9` COMPLETE |
  | error | `14` ERROR |
  | *(never fire on FDM)* | `2` DROPPING, `3` EXPOSURING, `4` LIFTING — resin-only leftovers |

  Feed phases `23`–`26` (AUTO_FEEDING / FEEDOUT…) relate to material handling. A code outside 0–26 (newer firmware)
  should normalize to *unknown* while preserving the raw value — **never to error.** 🟡

- **A separate file/launch error field `ErrorNumber` (0–5)**: `0` none, `1` MD5-check failed, `2` file-I/O failed,
  `3` invalid resolution, `4` unknown format, `5` unknown model. Any non-zero is an error. 🟡
- **Temperatures** (°C): nozzle `TempOfNozzle`/`TempTargetNozzle`, bed `TempOfHotbed`/`TempTargetHotbed`, chamber/box
  `TempOfBox`/`TempTargetBox`. 🟡
- **Fans:** a `CurrentFanSpeed` block `{ModelFan, BoxFan, AuxiliaryFan}`, each 0–100 — **read-only** (no fan-set
  command exists). 🟡

**Timing (SDCP).** ⚠️ These units are the classic trap — get them right:

- `CurrentTicks` / `TotalTicks` are **SECONDS** (int64) — **do not divide by 1000.** 🟡
- **There is no `RemainTime` field.** Remaining = `TotalTicks − CurrentTicks` (clamped ≥ 0). 🟡
- `Progress` is a **0–100 int read verbatim** from the `Progress` key — **not** derived from ticks, and normalized
  as a time fraction. Whether the percent tracks time or layer at the very end of a print is an **open** runtime
  observation — treat it cautiously (as on CC2). 🟡
- The envelope `TimeStamp` fields are **Unix milliseconds** — a different unit from the tick fields on the *same
  frame*. Don't apply one field's scaling to the other. See
  [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md).

### CC2 path

Poll `method 1002` (`GET_STATUS`) or consume the unsolicited `api_status` pushes — both carry the same `result`
object. Attributes come from `method 1001` (`sn`, `machine_model`, firmware versions). 🟡

- **`machine_status.status` (0–15)** → normalized: `1` Idle→standby, `2` Printing→printing (refine via
  `sub_status`), transient phases `0`/`3`–`13` (Initializing, Filament-Operating, Auto-Leveling, PID-Calibrating,
  Resonance-Testing, Self-Checking, Updating, Homing, File-Transferring, Video-Composing, Extruder-Operating) →
  printing/busy, **`14` Emergency-Stop → error**, **`15` Power-Loss-Recovery → paused**, and a `-1` sentinel →
  offline. 🟡
- **`machine_status.sub_status`** is the finer lifecycle signal (`0` = none). Key codes: `2075` printing, `2077`
  print-completed → complete, `2401`/`2402` resuming, `2501` pausing / `2502`/`2505` paused, `2503` stopping /
  `2504` stopped → cancelled, `1045`/`1096`/`1405`/`1906` preheating, `1081`/`1082`/`1086` downloading. Unknown ints
  fall through to *unknown*. 🟡
- **`exception_status`** is an **array of raw ints with no fixed device enum** — the SDK passes them through with no
  lookup. Treat any present code as error and surface the raw ints; per-int meanings are community lore only. 🔵
- **Temperatures** (°C): `extruder{temperature,target,filament_detected}`, `heater_bed{temperature,target}`,
  `chamber_sensor{temperature,measured_max/min_temperature}`. A multi-fan `fans` block reports part/aux/box/heater/
  controller each as `{speed, rpm?}`. 🟡

**Timing (CC2).** All time fields are **SECONDS** (int64): `print_status.remaining_time_sec` (firmware-reported →
prefer it), `print_duration` (extruding time), `total_duration` (wall clock). **`progress` is a plain 0–100 int with
no scaling** (no float, no ÷100). Whether that percent tracks time or file-position at the very end of a print is an
open runtime observation — treat it cautiously. See
[`../patterns/timing-normalization.md`](../patterns/timing-normalization.md). 🟡

## Writing / control

> ⚠️ Every command below drives a hot, moving machine — validate against your own device and gate writes behind an
> explicit opt-in. On SDCP especially, a malformed command can crash the printer (see Quirks).

### SDCP (CC1) — integer `Cmd` codes

Active command set: `0` status, `1` attributes, **`128` START**, **`129` PAUSE**, **`130` STOP**, **`131` RESUME**,
`324` canvas-read. **CC1 does have a live resume (`131`).** 🟡 There is **no live temperature / fan / light / motion /
speed write** — those codes exist only as commented-out stubs in the SDK; don't emit them. 🟡

**Print-launch sequence (upload → settle → start):**

1. **Upload** — `POST http://<ip>:3030/uploadFile/upload`, `multipart/form-data`, field `File` = a **≤1 MB** chunk.
   Per-chunk fields: `S-File-MD5` (whole-file MD5 hex, same on every chunk), `Check` (`1` = verify), `Offset`,
   `Uuid` (one value for the whole transfer), `TotalSize`. Each chunk must return `code=="000000"`; abort on
   `-1`/`-2`/`-3`/`-4`. The remote filename is the basename of the uploaded path. 🟡
2. **Settle ~1 s** — a **required** delay after the last chunk so the firmware can close the file handle. Skipping it
   risks a "file not found / read failed" ack. 🟡
3. **Start** — `Cmd 128` on `sdcp/request/…` carrying **all six** inner fields: `Filename` (must match the uploaded
   name), `StartLayer` (`0` = from the start; enables resume-from-layer), `Calibration_switch`, `PrintPlatformType`,
   `Tlp_Switch` (time-lapse), `slot_map` (`[]` for single-material). The result arrives inline at the response's
   `Ack` (`0` OK; `1` busy, `2` file-not-found, `3` MD5-failed, `4` file-read-failed, `5` invalid-format, `6`
   model-mismatch). **Confirm launch by state** (`sdcp/status` → PRINTING), not by the ack alone. 🟡

**Job control:** `Cmd 129`/`130`/`131` (pause/stop/resume) carry an empty inner `Data`. `Cmd 130` (stop) is
destructive — treat it as a dangerous, hold-to-confirm action. 🟡 **Upload-and-hold is native** — just skip the
`Cmd 128`.

### CC2 — integer `method` codes

Active set: `1001` attributes, `1002` status, **`1020` START**, **`1021` PAUSE**, **`1022` STOP**, `1043`
update-name, `2004` set-auto-refill, `2005` canvas-read, `1057`/`1058` remote-download start/cancel. 🟡

> **⚠️ There is no LAN resume on CC2.** The resume method (`1023`) is **commented out** in the SDK — the official
> client never sends it over LAN. Ship **pause + cancel only**; treat resume as unavailable (it exists on the device
> panel, just not over the wire). Home/move/set-temperature (`1026`/`1027`/`1028`) are likewise disabled over LAN. 🟡

**Print-launch sequence (upload → start):**

1. **Upload** — chunked **`PUT http://<ip>:80/upload`** over a **single keep-alive TCP connection** for all chunks,
   **1 MB** each. Per-chunk headers: `Content-Type: application/octet-stream`, `Content-Range:
   bytes <offset>-<endInclusive>/<total>` (note the space after `bytes`; the end index is the **last byte**,
   inclusive), `X-File-Name`, `X-File-MD5` (whole-file MD5 hex), `X-Token` (the access code). Each chunk returns
   `{"error_code":0}`; `1000` = bad token. 🟡
2. **Start** — MQTT `method 1020` on `api_request` with `params.storage_media` (`"local"`/`"u-disk"`/`"sd-card"`),
   `params.filename` (must match `X-File-Name`), and `params.config` = `{delay_video, printer_check, print_layout
   ("A"/"B"), bedlevel_force, slot_map}`. Success is `result.error_code == 0`. 🟡

**Job control:** `1021` pause / `1022` stop (destructive) with empty params. **Upload-and-hold is native** — skip the
`1020`.

### Moonraker path

Standard `printer.print.start / pause / resume / cancel` plus Moonraker file upload — see
[`klipper-moonraker.md`](klipper-moonraker.md). Note this is the **only** Elegoo path with a working resume across the
board.

## Multi-material / feeders — CANVAS

CANVAS is Elegoo's 4-slot RFID feeder, available on the Centauri Carbon 1 (over SDCP) and the CC2 Combo (over MQTT).
It maps onto the cross-vendor feeder model in
[`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md), where it is the **sparse outlier**
that proves per-slot "remaining %" must be nullable.

- **Same shape on both transports.** The feeder is read by a **separate on-demand query** — `Cmd 324` on SDCP, `method
  2005` on CC2 — with an empty request body; **both return the identical structure.** It is **not** in the continuous
  status push. A cheap presence flag (`canvasConnected` / an external-device block) *does* ride the status stream, so
  an implementer polls the feeder query on connect, on a presence edge, and before a multicolor print. 🟡
- **The report** (snake_case wire keys): a top level of `active_canvas_id`, `active_tray_id` (`0` = none), and
  `auto_refill`, then `canvas_list[]` of units — each unit has `canvas_id` (0–4; **multi-unit is a first-class
  concept**), `connected`, and `tray_list[]`. 🟡
- **Per-slot record (`tray_list`), exactly 9 fields:** `tray_id` (0 = empty, 1–4), `brand`, `filament_type`,
  `filament_name`, `filament_code` (a **filament-catalog code**, e.g. `"0x00000"` — **not** an RFID tag UID),
  `filament_color` (`#RRGGBB`), `min_nozzle_temp`, `max_nozzle_temp` (°C), and `status` (`0` empty / `1` pre-loaded /
  `2` loaded). 🟡
- **What CANVAS does NOT expose** (confirmed absent in the 9-field record, not merely unread): **no per-slot remaining
  quantity/grams/weight**, and **no RFID tag UID** (RFID drives auto-detect *internally* but the tag identity never
  reaches the wire). Both must degrade to null. There is also no per-slot dryer/humidity. 🟡
- **Auto-refill** (continue from an identical spool when one runs out) is toggled by `method 2004` on CC2 and read
  back as `auto_refill`; runout surfaces as an entry in the CC2 `exception_status` array, not a per-tray flag. 🔵
- **Print-time slot map** — the color→slot assignment, sent inside the start command as `slot_map`, an **array of
  `{t, canvas_id, tray_id}` integers** (snake_case). `t` is the sliced tool/color index; the pair identifies the
  physical (unit, tray). Empty for single-color prints. ⚠️ The vendor SDK also contains a camelCase
  `{t, trayId, canvasId}` form — that is the SDK's *internal* API JSON, **not** the printer wire; emit the
  **snake_case** form. The file's own color plan (which color each `t` wants) comes from a file-detail query
  (`method 1046` on CC2), joined to the slot map on the shared `t` index. 🟡
- **Per-material consumption** must come from the **sliced file** (there is no per-slot gram field on the wire) — see
  [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md) §4.

## Quirks & gotchas

- **Three protocols, one brand.** Neptune/Giga = Moonraker; Centauri Carbon 1 = SDCP/WebSocket; Centauri Carbon 2 =
  MQTT. They share only the CANVAS report shape — route by model first.
- **SDCP: unrecognized or incomplete commands can crash the printer.** Sending a `Cmd` the firmware doesn't know can
  be silently dropped and then **crash the daemon, killing an active print.** Only probe speculative commands when
  the machine is idle (`CurrentStatus == 0`). And **always send the full 6-field start payload** — a partial start
  (some third-party clients send only `{Filename, StartLayer}`) crashes the firmware. Honor the ~1 s post-upload
  settle. 🟡🔵
- **SDCP is not JSON-RPC** — no `jsonrpc`/`method`/`id`. Correlate on the echoed `RequestID`, and expect status to
  arrive **unsolicited** (there is no subscribe command; a periodic `Cmd 0` is both poll and keepalive).
- **SDCP identity is the `MainboardID`; CC2 identity is the serial.** A wrong id/serial silently addresses topics the
  printer never touches — no error, just nothing happens.
- **CC2 has no LAN resume** (see Writing). Panel-side resume exists; the wire command does not.
- **CC2 slot-map is snake_case on the wire** — the camelCase form in the SDK is internal-only.
- **CC2 re-registration is per-connection** — the printer keeps no session across TCP drops; re-run the handshake on
  every reconnect, and keep the heartbeat exactly `{"type":"PING"}` on the command topic.
- **CC2 `:9001`/WebSocket does not exist** — transport is TCP `:1883` only, despite community claims otherwise.
- **CC2 `Content-Range` is standard-but-strict** — a literal space after `bytes` and an **inclusive** end index; the
  printer validates it.
- **Moonraker is a pinned, older fork on a locked image** — don't update firmware (bricks the machine), assume older
  API surface, and don't mislabel the Giga's `heater_bed1/2/3` **bed zones** as a chamber.
- **Timing units differ by path and even by field** — SDCP ticks are **seconds** (not ms) while its `TimeStamp` is
  **ms**; CC2 times are **seconds**; Moonraker times are **seconds** but its progress is **file-byte position**.

## Confidence & validation

- **Source basis (🟡):** every wire fact — ports, envelopes, discovery payloads, method/`Cmd` tables, status enums,
  tick units, upload headers, CANVAS structure and slot-map form — is read from **Elegoo's own first-party LAN SDK**
  (Apache-2.0), which ships all three paths, plus the official (resin-oriented) SDCP v3.0 spec for the SDCP envelope
  and `From`/error spans. This makes the *shapes* first-party-correct, but **the orchard author has not hardware-
  validated the Centauri (CC1/CC2) or CANVAS paths** — there is no owner-side bench for them.
- **Community hardware corroboration (🔵):** the **SDCP path** is independently firmware-validated by more than one
  community client (tested against Centauri Carbon firmware in the ~1.1.x range) — the 5-connection cap, 60 s idle
  timeout, no-auth posture, and the crash-on-partial-start behavior come from real devices. The **Moonraker path** is
  routinely reached by third-party clients (Fluidd/Mainsail/others) on stock Neptune 4 hardware.
- **Not yet confirmed / open gaps** (a capture would close each):
  1. **CC2 push cadence** — how often `api_status` fires unsolicited (to decide whether a poll backstop is needed).
  2. **CC2 progress semantics near 100%** — whether the 0–100 percent tracks time or file position at the end.
  3. **Accepted file container/extension** on CC1 and CC2 (raw g-code vs an Elegoo sliced container) — uncaptured on
     both.
  4. **CANVAS live behavior** — which slot `status` values fire mid-multicolor-print, real multi-unit daisy-chaining,
     and the exact runout/tangle exception codes (the CANVAS data *shape* is first-party; its runtime behavior is not
     hardware-checked, since the author has no CANVAS unit).
  5. **OrangeStorm Giga** — a stock (not community-image) config capture, and the IDEX upgrade's wire shape.
  6. **A single live CC1 lifecycle trace** to confirm which of the 0–26 status codes actually emit in the wild, plus
     the exact coordinate/position field names.

## Sources

Clean-room, facts-only. The authoritative source for all three paths is **Elegoo's own first-party LAN SDK**
(`elegoo-link`, Apache-2.0), which contains the CC1 (SDCP), CC2 (MQTT), and model-agnostic Moonraker adapters plus the
shared CANVAS type definitions — consumed here as **uncopyrightable interface facts** (ports, topic strings, JSON
field names, method/`Cmd` integers, discovery payloads, upload headers). Supporting sources: the official cbd-tech
**SDCP v3.0** protocol spec (publisher-stated MIT) for the SDCP envelope, `From` enum, and error spans; Moonraker's
documented HTTP/WS API for the Neptune/OrangeStorm path; and **MIT-licensed community clients** (a Python SDCP
library, the `cassini` CLI, and a Home Assistant integration) as firmware-validated behavioral cross-checks. No SDK
or client **code** was copied; struct/field **shapes** are described, not reproduced. No Elegoo firmware source
(GPL-3.0) was vendored, and **no secrets** are included — the CC2 access code is documented as a mechanism (read from
the printer screen), never a value. Passed [`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md).

> **Machine-readable (SDCP):** [`../schemas/elegoo/sdcp-envelope.json`](../schemas/elegoo/sdcp-envelope.json) (frame +
> topics + `From`), [`sdcp-cmd-catalog.json`](../schemas/elegoo/sdcp-cmd-catalog.json) (`Cmd`/`Ack`/`ErrorNumber` +
> upload), [`sdcp-state-enum.json`](../schemas/elegoo/sdcp-state-enum.json) (the two status enums + timing).
