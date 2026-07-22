# Bambu Lab — LAN Protocol

> **Status:** 🟢 hardware-validated (A1 Mini fw `01.08.00.00`, AMS Lite + a third-party AMS clone; read +
> single/multi-color launch) — X1/P1/H2 specifics are 🟡 source-read · **Firmware:** proprietary Bambu · **Models:**
> X1 / P1 / A1 / P2 / X2 / H2 families
>
> Bambu printers speak two LAN transports at once — **MQTT over TLS `:8883`** for state and control, **implicit
> FTPS `:990`** for the file — both unlocked by turning **LAN mode on with a per-device access code**. There is **no
> command ack**: you confirm every write by watching the status stream.

## At a glance

- **Transport:** MQTT/TLS **`:8883`** (user `bblp`, password = the printer's access code) **plus** implicit-TLS
  FTPS **`:990`** (`bblp` / same access code). Both LAN-local.
- **Discovery:** SSDP on **`:2021`** (`urn:bambulab-com:device:<model>`, `USN` = serial); manual IP always works.
- **Auth / credential:** the **access code** shown on the printer once local access is enabled — a user secret, read
  from the machine's own screen. No client cert, no cloud token. See [Credentials](#credentials--auth).
- **Read / status:** publish a **`pushall`** for a full snapshot, then consume live deltas. `gcode_state` drives the
  lifecycle; temps/progress/AMS/faults ride along.
- **File transfer:** FTPS upload the `.3mf` to the SD-card root (a **strict, non-RFC dialect** — see the gotcha).
- **Print launch:** two transports — FTPS-upload, then MQTT `project_file` referencing the uploaded file.
- **Feeders / multi-material:** AMS (full / Lite / high-temp) + external spool. See [Multi-material](#multi-material--feeders).
- **⚠️ The load-bearing gotchas:** (1) the FTPS data channel must be TLS-handshaked **only after the `150`** — generic
  libraries that wrap it right after `connect()` hang; (2) the **serial is case-sensitive** everywhere (topic, SNI,
  cert CN) — a miscased serial connects fine but returns **zero reports**.

## Transport & connection

A printer with local access enabled exposes **two** LAN transports; a full client needs both.

| Transport | Port | TLS | Auth |
|---|---|---|---|
| MQTT | **8883** | TLS (see below) | user `bblp`, password = **access code** |
| FTPS (implicit) | **990** | implicit TLS on connect | `bblp` / access code |

**Identity per printer = `(ip, serial, access_code)`.** The **`serial`** is reused as the MQTT topic key, the TLS
**SNI** name, and the device cert **CN** — and it is **case-sensitive**. A miscased serial connects, subscribes, and
publishes without error but yields **zero reports** (the canonical silent failure — detect it as "connected but 0
inbound messages"). 🟢

**MQTT session shape.** MQTT v3.1.1; a **unique `client_id` per (re)connect** (reused ids leave zombie sessions on
the broker). Every publish uses **`qos=1`** — the printer ignores qos-0 commands while it is busy broadcasting
status. Raise the inflight ceiling well past paho's default of 20 (e.g. to ~1000): the broker's PUBACK matching is
racy against a low ceiling and **wedges the session after ~16–20 cumulative commands**. 🟡 Keepalive ~30 s, plus an
**app-level staleness timer (~60 s)**: some firmware stops publishing while the TCP socket stays alive, so treat a
silent-but-connected session as dead and **reconnect with a fresh `client_id`** (which also discards any stale qos-1
backlog so an old launch can't replay). 🟡 Bench idle streams ran ~16–28 frames / 90 s with a max silent gap ~7 s, so
the 60 s window is generous. 🟢

**TLS — two strategies.** The printer presents a self-signed-from-a-Bambu-CA cert (`CN = serial`, no SAN):
- **Verify-off** — `CERT_NONE`, hostname check off, no client cert. Works everywhere; the simplest path.
- **Proper verification (preferred)** — trust Bambu's published device-CA cert and connect with **SNI = serial**
  (you dial the IP but verify against the serial). On Python 3.13+ clear the strict-X.509 flag (the cert omits a
  key-usage extension the strict verifier rejects). **Newer device CAs** may not chain against the bundled root —
  offer **pin-the-leaf-on-first-use** (snapshot the leaf, CN-check thereafter), with verify-off as the final
  fallback. Apply the same CN-check on the FTPS and camera ports. Verified end-to-end on both `:8883` **and** `:990`
  against a real unit with no fallback firing. 🟢

**Topics & envelope — flat, no wrapper.** Subscribe `device/<serial>/report`; publish `device/<serial>/request`.
Payloads are **category-keyed JSON**, the category being one of `print` · `pushing` · `info` · `system` · `xcam` ·
`camera` · `upgrade`; the verb lives in an inner `command` field, e.g. `{"pushing":{"command":"pushall"}}`. A string
`sequence_id` (often the literal `"0"`) is **loose** correlation, not a strict request/reply map — **there is no
command ack**; confirm effects by watching the status stream (see [Reading state](#reading-state)). 🟢

## Discovery & identity

- **SSDP** on UDP **`:2021`** — service type `urn:bambulab-com:device:<model>`, `USN` = serial, `Location` = the bare
  IP, and a **`DevModel.bambu.com`** header carrying the **model_id code** (not a friendly name), plus `DevVersion`
  (firmware) and `DevName` (user's name). Confirmed live for the A-series (`N1` = A1 mini, `N2S` = A1). 🟢
- **Manual IP** always works and is the guaranteed onboarding path — see
  [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md).
- **The model is not required to connect** — it only refines feature behavior (chamber-sensor presence, FTPS quirks,
  AMS type). Read the friendly firmware/module identity from the MQTT `get_version` reply once connected. 🟢

The `model_id` code space is first-party (from Bambu's own machine profiles) and worth pinning, because the widely
copied community map is **wrong** (it maps `C11`→X1C when `C11` is **P1P**):

| code | model | · | code | model |
|---|---|---|---|---|
| `BL-P001` | X1 Carbon | · | `N1` | A1 mini |
| `BL-P002` | X1 | · | `N2S` | A1 |
| `C13` | X1E | · | `N7` | P2S |
| `C11` | **P1P** | · | `N6` | X2D |
| `C12` | **P1S** | · | `O1D` | H2D |

🟡 (A-series rows 🟢, confirmed by live SSDP capture). Treat auto-detection as a *pre-fill*, let the user confirm the
model, **never hard-fail on an unknown code** (fall back to the raw string), and **derive capabilities from live
report structure, not the model string** — e.g. detect dual-nozzle from the report's extruder-info length ≥ 2, so an
H2D is handled even if its code never made a table.

## Credentials / auth

**"Developer Mode" is just LAN mode — don't over-read the name.** Bambu's *LAN-Only Mode* disables the cloud; the
*Developer Mode* toggle inside it opens the local MQTT/FTP broker and surfaces an **access code**. That is the exact
same "**cloud off → local access via a per-device code**" posture as every other brand (Anycubic/Creality/Elegoo LAN
access, Snapmaker's auth-code, FlashForge's check-code). It is a normal onboarding precondition to surface, **not a
special gate** — see [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md). The
access code is the user's own secret, read from the printer's screen; this reference documents *how a user obtains
theirs*, never a value.

**Why the LAN path is the clean one.** On **stock (cloud) firmware**, privileged commands such as `project_file`
must carry an RSA-signed `header` envelope and a `url_enc` (the source URL AES-encrypted, the AES key RSA-wrapped
against the device cert) — and the signing key lives inside Bambu's **closed networking plugin**. Unsigned commands
are rejected with `MQTT Command verification failed` (error `84033543`). **The LAN/local path sends plain commands
and needs zero vendor secrets** — plain `url`, no signed `header`. That is why an implementer should scope strictly
to LAN mode: it both unlocks the printer and stays clear of any signing-key material. 🟡

> **Per-firmware nuance (be honest):** the signing-enforcement framing above describes a **newer firmware wave**. On
> the bench A1 Mini (`01.08.00.00`), the local broker behaved **identically with the Developer-Mode toggle off** —
> connect, subscribe, status stream, and even a would-be-privileged command all succeeded, no `verify failed`. So on
> that build the toggle is effectively cosmetic for LAN MQTT. A client should still detect and surface a
> monitor-only state for firmware that *does* enforce (see the dev-mode probe below), but must not assume every
> build enforces. The enforcing (`verify failed`) path has **not** been captured live. 🟢/🟡

**Dev-mode / write-availability probe.** X1/H2 firmware advertises a `fun` bitfield in the status object
(`dev_mode_on = (fun & 0x20000000) == 0`); **A1/P1 never send `fun`**, so probe instead: wait ≥5 s after connect
(probing too early destabilizes some brokers), send a **guaranteed no-op** write (echo the printer's own external-spool
values back at it, scraped from the snapshot — skip the probe entirely if no snapshot yet, so you never risk a real
write), and read the result: a `failed` result whose `reason` says `verify failed` ⇒ writes are gated (monitor-only);
any other response ⇒ writes available. This doubles as zombie-session detection. 🟢

## Reading state

Publish **`{"pushing":{"command":"pushall"}}`** on connect for a full snapshot, then consume live deltas off
`device/<serial>/report`. Dispatch each report by its top-level category key. **The same field can arrive at top level
or nested under `print`, and P-series firmware sends only the *changed* keys while X-series sends the full object — so
deep-merge partials, never replace.** 🟢 This is a poll-hybrid-ish push model: subscribe, snapshot, diff.

- **Lifecycle — `gcode_state`** (native → normalized "the neutral state any client needs"): 🟢

  | native | normalized |
  |---|---|
  | `IDLE` | standby |
  | `PREPARE`, `SLICING`, `RUNNING` | printing |
  | `PAUSE` | paused |
  | `FINISH` | complete |
  | `FAILED` | error |

  ⚠️ An **aborted print returns to `IDLE`**, so a *failed* job reads as plain standby unless you also surface the
  fault channels (below) — the two are otherwise indistinguishable. 🟢

- **Progress:** `mc_percent` (0–100) is a **time-based** estimate — note it **includes the calibration phase**, so
  percent can advance while `layer_num` is still 0. `mc_remaining_time` is in **minutes** (a classic cross-brand
  unit trap — see [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md)); `layer_num` /
  `total_layer_num` track layers. 🟢
- **Temperatures:** `nozzle_temper` / `bed_temper` / `chamber_temper` and their `*_target_temper` companions, plain
  °C. ⚪ Some encoded forms are reported to pack `target*65536 + current` when the value exceeds 500 — unconfirmed on
  hardware; validate per field/model. `chamber_temper` is **absent or meaningless on P1/A1-class** (the bench A1 Mini
  reported a bogus fixed ~5 °C with no chamber sensor). 🟢
- **Fans:** part (`cooling_fan_speed`), aux (`big_fan1_speed`), chamber (`big_fan2_speed`), heatbreak.
- **Firmware:** the `get_version` reply returns a `module[]` array; firmware = the `ota` module's `sw_ver`. Module
  names (`ams/N`, `n3f/N`, `ams_f1/N`, `th`, `mc`, …) also reveal hardware and AMS type. 🟢
- **Faults:** `hms[]` (an array of `{attr, code}`) plus a separate 32-bit `print_error`. See
  [Faults & HMS](#faults--hms).

## Writing / control

All commands publish to `device/<serial>/request` at **qos 1**, category-keyed. There is **no command ack** —
confirm by watching the status stream. Core verbs: 🟢/🟡

| Command | Category / shape | Purpose |
|---|---|---|
| `pause` / `resume` / `stop` | `print` | Job control |
| `print_speed` | `print`, `param` `"1".."4"` | silent / standard / sport / ludicrous |
| `ledctrl` | `system`, `led_node` `chamber_light`\|`work_light` | Lights — **the flashing params are required even for plain on/off** |
| `gcode_line` | `print`, `param` = raw G-code | Arbitrary G-code |
| `calibration` | `print`, `option` bitmask | `lidar=1, bed=1<<1, vib=1<<2, motor=1<<3` |
| `print_option` | `print` | `auto_recovery`, `filament_tangle_detect`, … |
| `skip_objects` | `print`, `obj_list:[ids]` | Cancel objects mid-print (echoes `s_obj`) |
| `xcam_control_set` | `xcam` | AI-detector toggles |
| `project_file` | `print` | Start a print (below) |
| AMS load/unload/setting | `print` | See [Multi-material](#multi-material--feeders) |

> ⚠️ Control writes drive a hot, moving machine. Validate against your own device and gate them behind an explicit
> "enable writes" in any client — a `🟡` control fact is far riskier than a `🟡` read fact.

**Print launch — two transports, then poll.** 🟢

1. **FTPS-upload** the `.3mf` to the SD-card root (dialect below), wait for the closing `226`, and **SIZE-verify**
   (server size == local size) so a partial file never gets a print command.
2. **MQTT publish** `{"print":{"command":"project_file", …}}` referencing the uploaded file. Load-bearing fields:
   - `param` = `Metadata/plate_<N>.gcode` — **this is how the 1-indexed plate is conveyed** (the gcode for that
     plate must exist inside the 3MF).
   - `url` = `ftp://<bare-name>` (**plain URL** on the local path — the stock firmware's `url_enc` is not needed),
     `file` = the same bare name.
   - `md5` = **empty string** (skip validation; a wrong synthetic digest risks *activating* validation).
   - `bed_type` = `"auto"` (or an explicit plate type).
   - Calibration flags (`timelapse`, `bed_leveling`, `flow_cali`, `vibration_cali`, `layer_inspect`) must be **JSON
     booleans for all models** (int-encoding broke H2 flow-cali). `use_ams` must **stay boolean** (an H2D Pro reads
     an int here as a nozzle index).
   - IDs (`project_id`/`task_id`/`subtask_id`/…) are **strings**. A fresh, **int32-capped** id per launch is the
     safe choice — some firmware clamps oversized epoch-ms ids and treats a reprint as a continuation, wedging in
     IDLE. 🟡
   - `ams_mapping` + `ams_mapping2` for multi-color routing; `nozzle_mapping` on multi-extruder units — see
     [Multi-material](#multi-material--feeders).
3. **Confirm by polling the status stream** — accept a transition into `{PREPARE, SLICING, RUNNING, PAUSE}` **or**
   `subtask_id` advancing to your submission id. Don't accept arbitrary state changes. ⚠️ A launch can be **accepted
   then aborted** by a printer-side precondition (e.g. the screen sitting on a menu that blocks a remote start) — the
   `subtask_id` echo proves the command *landed*, **not** that the print succeeded, so also watch `print_error` after
   dispatch. 🟢 H2D can sit at FINISH ~50 s before flipping to PREPARE, so the `subtask_id` echo is the early signal
   there. 🟡

### The FTPS dialect (implement to spec)

Bambu firmware runs a stripped FTPS server that deviates from RFC 959/4217. The rules that matter: 🟢/🟡

- **Implicit TLS on `:990`** — TLS starts on connect; there is **no `AUTH TLS`** (waiting for a plaintext `220`
  banner hangs).
- **Mandatory post-login order:** `TYPE I` → `PBSZ 0` → `PROT P`, in that order, before any data command
  (reordering makes the next `PASV` fail).
- **PASV only** (`PORT`/active is unimplemented) — and **PASV returns a bogus host IP**; discard the four host
  octets and reconnect the data socket to the *control* connection's host.
- **⭐ Delayed data-channel TLS (the #1 gotcha):** `PASV` → TCP-connect the data socket **plaintext** → send
  STOR/RETR/LIST on control → wait for `150` → **only now** TLS-handshake the data socket → transfer → read the
  `226`/`250`. Libraries that handshake right after `connect()` hang until timeout.
- **⭐ Read the closing `226` with the *transfer* timeout, not a short command timeout** — the firmware sends the
  final ack only **after flushing the whole file to storage**, so ack latency **scales with file size**. A ~16 MB
  multicolor 3MF's `226` arrives well past a typical ~15 s command budget; a post-transfer ack is part of the
  *transfer*, so budget it accordingly. (Small single-color files hide this bug.) 🟢
- **Data-channel TLS session reuse** — opt in by default (bind the control session onto the data socket); the A1
  family may instead need a **clear data channel** (`prot_c`), and P2S/X2D may need TLS **capped to 1.2**
  (auto-detect / fall back). On the bench A1 Mini the standard `PROT P` + session-reuse posture worked — the
  clear-channel lore did **not** apply to that build. 🟢 (other-model quirks 🟡)
- **No `MLSD` / `MKD` / `APPE` / `REST`** → can't create dirs, **can't resume** (a failed upload re-`STOR`s from
  byte 0); parse a plain `LIST`. `SIZE`, `DELE`, `CWD` work. Sessions idle-timeout silently at ~5 min.
- **Storage prefix varies by model** — probe once (`CWD /sdcard` → `/usb` → `/`) and cache it (X1/P1/A-series
  typically `/sdcard`; the bench A1 Mini fell through to `/`; USB-only P2S roots at the stick). The `url` must match
  where the file actually landed.
- **Filenames:** strip to the stem + a single `.3mf`, replace spaces with underscores (the firmware parses
  `ftp://{name}` as a URL — spaces break it), and reject shell/URL-illegal characters or you get an opaque `553`.
  `DELE` the remote name before re-uploading. 🟡

## Multi-material / feeders

Bambu's AMS is a **rich** feeder (per-slot RFID UUID, recommended temps, color name, live flow-K) — a superset of
what most brands expose over LAN. It folds cleanly into the neutral feeder model in
[`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md) (a bank of slots → one hotend, plus
an external spool); everything below the opaque per-slot atom (RFID, remaining %, dry-box) is optional and degrades.

**Where it arrives.** Under `print.ams` in the snapshot, **or** as partial top-level `ams`/tray objects in
incremental updates — **deep-merge at the tray level** so RFID/sub-brand/drying fields survive. External spools ride
in `vt_tray` (single dict — X1C/P1S/A1) or `vir_slot` (list — H2 series). 🟢

**Global slot addressing (keep this opaque per the pattern's `slot_key` invariant):** standard `global = ams_id*4 +
slot` (inverse `ams_id = g//4`, `slot = g%4`); **AMS-HT** units are single-tray with `id ≥ 128` and `global = id`;
**external** spools are `254` (single / left) and `255` (right, on dual-nozzle). `tray_now` is the active global tray
(`255` = none, `254` = external); a raw `0..3` is ambiguous on multi-AMS/dual-nozzle and must be disambiguated via
the load-time target you set. 🟢

**Per-slot fields** (each degrades to null): `tray_type` (base material) + `tray_sub_brands` (variant) + `tray_color`
(**RRGGBBAA** hex — normalize to `RRGGBB` at the boundary; `…00` alpha = clear), `tray_info_idx` (the filament preset
id — the load-bearing calibration key), `remain` (**percent**, RFID-estimated) × `tray_weight` (g) for grams,
`k`/`cali_idx` (live flow-K + profile index, `-1` = default), `tag_uid` + `tray_uuid` (RFID identity — the UUID is
the preferred stable id), recommended nozzle-temp window, and `state` (`9` empty / `10` present-not-fed / `11`
loaded). 🟢

**Variants** — detect by **presence of data, not by model/AMS name** (a third-party AMS clone on the bench reported
as a full "AMS Pro 2" yet had genuinely no RFID/humidity/dryer hardware, all-zero identity — so gate sub-capabilities
on real observed values, never on the unit's claimed identity): 🟢
- **Full AMS** (X1/P1/P2): 4 trays, RFID + humidity + drying.
- **AMS Lite** (A1 / A1 mini): 4 slots, **no RFID/UUID** (module name `n3f`/`n3s`/`ams_f1`; identity falls back to
  user assignment).
- **AMS-HT** (high-temp): single tray per unit, `id ≥ 128`.
- **External / virtual spool**: same tray shape; its loaded flag doubles as the runout signal.

**AMS commands** (all `{"print":{…}}`, qos 1, ack-less — watch `ams_status` main-code `1` = filament-change and
`tray_now` settling): 🟢
- **Load / unload** — `ams_change_filament`. Load passes `-1` temps (firmware picks the temp from the tray preset);
  unload and preset-less external-right loads pass the **real** current nozzle temp (the head must be hot to
  retract). Load auto-unloads whatever is present first.
- **`ams_control`** — resume/reset/pause a stuck change.
- **`ams_filament_setting`** — set a slot's material/color/temps/preset (uses the **local** tray id).
- **`extrusion_cali_sel`** — select a flow-K profile. ⚠️ Trap: this one uses the **global** tray id (unlike
  `ams_filament_setting`) and must **not** carry a `setting_id`.
- **`ams_get_rfid`** — re-read a tag; valid only when nothing is loaded (`tray_now == 255`).

**Print-time routing — emit two fields together:** 🟢
- **`ams_mapping`** — flat array indexed by 3MF filament slot, carrying global ids, **but external (254/255) and
  unmapped rewritten to `-1`** (sending raw 254/255 here triggers a "failed to get AMS mapping table" fault).
- **`ams_mapping2`** — the parallel `[{ams_id, slot_id}]` form carrying real external routing; this is the
  **firmware-preferred** form (firmware that supports both prefers it).
- **`nozzle_mapping`** (flat int array, 3MF-slot → physical nozzle) on multi-extruder / H2D only.

This color→slot map is the key to per-material accounting — see the pattern doc. Validated live: single-color
(`ams_mapping=[3]`) and 3-color (`ams_mapping=[0,2,3]` + three `ams_mapping2` entries) launches both fed the correct
slots, confirmed by `subtask_id` echo and a live `tray_now` tool-change. 🟢

## Faults & HMS

Two raw fault channels in the status object: **`hms[]`** (`{attr, code}` objects) and a separate 32-bit
**`print_error`** (`MMMM_EEEE`). Decode each: severity nibble = `(attr >> 8) & 0xF` (1 fatal / 2 serious / 3 common
/ 4 info), module = `(attr >> 24) & 0xFF`, and a `short_code` = `f"{(attr>>16)&0xFFFF:04X}_{code&0xFFFF:04X}"` for
lookup. Two **filters are essential** or the UI lights up during a normal print: 🟡
1. **Status-not-fault:** skip if the low half `< 0x4000` (firmware emits low values as normal-phase status).
2. **User-action echoes:** skip a small hand-maintained set of short codes the firmware emits during normal
   user-cancel sequences.

Fold `print_error` through the same decode/filters and dedupe it against `hms[]`. The human-readable message
catalog (~800 codes) is **not** a protocol fact and should be regenerated from Bambu's own published error-code list
— **do not copy the copyleft community dictionaries**. Retaining raw `attr`+`code` lets a client build Bambu's HMS
deep-link so unknown codes stay actionable without a complete catalog. 🟡 The live filter behavior was proven correct
on the bench (an AMS clone's steady-state zeros-HMS decoded as info/status-not-fault and was correctly dropped; an
accepted-then-aborted launch surfaced a real `≥0x4000` `print_error`). 🟢

## Quirks & gotchas

- **Serial is case-sensitive** across topic / SNI / cert CN — wrong case = connect OK, **0 reports**. 🟢
- **No command ack** anywhere — confirm every write (launch, pause, AMS change) by watching the status stream. 🟢
- **Delayed data-channel TLS** on FTPS and the **transfer-timeout on the closing `226`** — the two FTPS traps that
  cost the most hours (above). 🟢
- **P-series sends only changed keys, X-series sends the full object** → always deep-merge partials, including at the
  AMS tray level. 🟢
- **`use_ams` and the cali flags must stay booleans**; `md5` must be **empty**; the plate index rides in `param`, not
  a numeric field. 🟡
- **`fun` is absent on A1/P1** → probe for write-availability rather than reading a bit. 🟢
- **Chamber temp is bogus/absent on P1/A1-class** — filter it out for those. 🟢
- **Derive capabilities from live report structure, not the model string** — and the community model-code map is
  wrong/incomplete (e.g. `C11` is P1P, not X1C); never hard-fail on an unknown code. 🟡
- **Raise the MQTT inflight ceiling and use a fresh `client_id` on reconnect** or the session wedges after a
  handful of commands / replays stale launches. 🟡

## Confidence & validation

- 🟢 **Hardware-validated on an A1 Mini (fw `01.08.00.00`) with AMS Lite and a third-party AMS clone:** verified
  TLS (BBL-CA + SNI=serial) on both `:8883` and `:990`; MQTT connect + `pushall` + live deltas; `get_version`
  firmware; lifecycle/temps/fans/lights parse; AMS-Lite slot/color/exist-bit hygiene; the dev-mode probe; the full
  FTPS dialect (implicit TLS, `TYPE`/`PBSZ`/`PROT P`, PASV-IP discard, delayed data-TLS + session reuse, STOR +
  SIZE-verify + DELE); and **single- and multi-color `project_file` launches** confirmed by `subtask_id` echo and a
  live tool-change. SSDP identity confirmed live for the A-series (`N1`, `N2S`). The FTPS large-file transfer-timeout
  and the accepted-then-aborted launch semantics were both found and proven on this unit.
- 🟡 **Source-read (first-party docs / machine profiles, not yet hardware-confirmed):** the stock-firmware signing /
  `url_enc` details; per-model FTPS quirks beyond the A1 (`prot_c` clear-channel, TLS-1.2 cap on P2S/X2D); the X1/P1
  `fun`-bit dev-mode read; the HMS decode thresholds and severity map; the full `model_id` table beyond the
  A-series; H2D dual-nozzle `nozzle_mapping` / dual-external routing.
- ⚪ **Inferred / unconfirmed:** the `target*65536 + current` temperature encoding (which fields/models).
- **Open gaps — the captures that would close them:** the **Developer-Mode-OFF path under an *enforcing* firmware**
  (the `verify failed` / `84033543` rejection has never been seen live — needs an X1/P1-class unit or a post-update
  A1); an **X1 or P1 bench** (full AMS with RFID, the `fun` dev-mode path, full-object-not-partial reports); an
  **H2D** (dual-nozzle `tray_now` disambiguation, `nozzle_mapping`, dual-external); the **temp-encoding** confirmation;
  and a **live HMS/print_error catalog** with the exact wiki deep-link format.

## Sources

Clean-room, facts-only. Built primarily from two clean, citable public sources — **OpenBambuAPI** (GFDL-1.3
documentation: MQTT command/report shapes, ports, the TLS recipe, the device-CA cert, the LAN file behavior) and
**`scarlton/open-bambu-networking`** (MIT, clean-room: the full FTPS dialect, the signing/`url_enc` requirement, the
cross-model `project_file` field map, `nozzle_mapping`) — plus **Bambu's own first-party machine profiles** for the
`model_id` table, corroborated by **owner hardware captures** (A1 Mini + AMS Lite + a third-party AMS clone, sanitized;
sanitized wire-shape fixtures for `pushall` (X1C), `get_version`, and P1 partial / AMS-partial updates back the schema
tests). Copyleft management apps were used as **behavioral reference only — no code copied**. No certificate, key,
access code, serial, or real IP is reproduced; credentials are described as a **mechanism** (the access code the user
reads from their own printer), never a value. Bambu's closed networking plugin and the projects redistributing it are
neither used nor referenced for key material. Passed
[`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md).
