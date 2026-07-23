# Creality (stock Creality OS) — LAN Protocol

> **Status:** 🟡 source-read _(the stock `:9999` wire is read from Creality's **own** device-manager frontend, but no
> stock device has been bench-validated here)_ · **Firmware:** Klipper-based "Creality OS" (proprietary LAN service on
> top) · **Models:** Ender-3 V3 / V3 KE / V3 Plus, K1 / K1C / K1 SE / K1 Max, K2 Plus / K2 Pro, Hi, CR-10 SE
>
> "Creality" is **three protocols wearing one brand**, split by *firmware*, not model line. This paper documents the
> **stock** bucket: an **unauthenticated plain WebSocket at `ws://<ip>:9999`** carrying a flat `{"method","params"}`
> envelope with unsolicited state pushes, plus a no-auth `:80/upload` for files. The other two buckets cross-link out.

## The three buckets (route by live service, not by model name)

| Bucket | Firmware / LAN | Representative models | Where documented |
|--------|----------------|-----------------------|------------------|
| **A — Marlin/USB** | Marlin, USB/SD, **no WiFi** | Ender-3 V3 **SE**, Ender-3 V2/S1, CR-10 classic | [`marlin-serial.md`](marlin-serial.md) |
| **B — stock Creality OS** | Klipper-based, WiFi, proprietary `ws://:9999` | Ender-3 V3 **KE**/V3/Plus, K1/K1C/K1 SE/K1 Max, K2 Plus/Pro, Hi, CR-10 SE | **this paper** |
| **C — rooted → Moonraker** | any bucket-B model after rooting → standard Moonraker `:7125` | " (after the community root script) | [`klipper-moonraker.md`](klipper-moonraker.md) |

> ⚠️ **SE vs KE are one letter apart and opposite buckets** — Ender-3 V3 **SE** is Marlin/no-WiFi (bucket A), **KE** is
> Klipper/WiFi (bucket B). Never infer the bucket from the model string; **fingerprint the live service** (see
> Discovery) and re-fingerprint on reconnect, since a firmware update can revert a rooted printer back to stock. 🟡

## At a glance

- **Transport:** plain **WebSocket `ws://<ip>:9999`** (text frames, **no TLS, no auth**) + plain-HTTP **`:80/upload`**
  for files. Not JSON-RPC, not SDCP, not MQTT — the simplest transport in the orchard.
- **Discovery:** manual IP always works; the vendor slicer also uses a **UDP broadcast**. Identity via
  `GET http://<ip>/info`.
- **Auth / credential:** **none** on the LAN socket (LAN-trust). Nothing for the user to obtain. (The separate,
  account-bound Creality Cloud path is a different transport — out of scope here.)
- **Read / status:** **push-hybrid** — the printer pushes flat state objects unsolicited; a client merges each into one
  running dict and pokes a `get` on a timer as backstop.
- **File transfer:** `POST http://<ip>:80/upload/<name>` (multipart / raw body, **no auth**).
- **Print launch:** two-step — HTTP upload, then a WebSocket `set` with `opGcodeFile: "printprt:"+<path>`.
- **Feeders / multi-material:** CFS (Creality Filament System) — up to 4 units × 4 slots; **rich** (per-slot % + RFID +
  dry-box temp/humidity).
- **⚠️ The load-bearing gotcha:** the same brand speaks **three different protocols**; and stock progress is a *percent*
  but the OS is Klipper-based, so treat it as **file-byte position, not time** until a capture proves otherwise.

## Transport & connection

One long-lived **plain WebSocket** at `ws://<ip>:9999`, no path suffix, **no subprotocol argument**, no TLS. The socket
is **unauthenticated** — no token, header, or password (LAN-trust). One JSON object per text frame. 🟡

**Message envelope — two verbs, flat, un-correlated:** 🟡
```jsonc
// the client SENDS:
{"method":"set","params":{ <paramKey>:<value>, ... }}   // control a setting / issue an action
{"method":"get","params":{ <reqKey>:1, ... }}           // ask the printer to (re)emit a data block
```
The printer **pushes** state as **bare flat objects** — often *without* the `method` wrapper, just the field bag
(e.g. `{"nozzleTemp":210.4,"printProgress":42,...}`), streamed unsolicited while connected. There is **no response
correlation**: a `set`/`get` is **fire-and-forget**, and you observe its effect in the *next* pushed object. A client
merges every inbound object into one running state dict. 🟡

**Keepalive & reconnect.** Independent community clients describe an in-band heartbeat — the printer sends
`{"ModeCode":"heart_beat"}` and the client replies the literal string `"ok"`, with a `get`-poke after ~10 s of silence.
**Neither the heartbeat string nor the advertised `wsslicer` subprotocol appears in the vendor's own frontend** — treat
both as community lore: implement the heartbeat defensively, but key liveness on the transport connection, not on it.
Reconnect with backoff. 🔵

Auxiliary services on the same host: MJPEG camera `http://<ip>:8080/?action=stream` (K1 / V3 / Hi); WebRTC
`http://<ip>:8000/call/webrtc_local` (K2 family and newer); file downloads under `http://<ip>/downloads/{gcode,video,
humbnail}/…` (the `humbnail` spelling is the vendor's, not a typo here). The older Halot **resin** line uses a
different port (`:18188`) and is **out of FDM scope**. 🔵

## Discovery & identity

**Manual IP is the guaranteed path.** The vendor slicer additionally discovers over **UDP broadcast**: it broadcasts a
prefixed probe and printers reply with a small JSON `{"answer":…,"machineIp":…}`; a classifier regex splits a rooted
Moonraker machine (a machine-type field of `"00"`) from a stock one. A community forum note mentions a possible
secondary beacon on UDP `:5353`. 🟡 (vendor slicer) / 🔵 (the `:5353` note)

**Identity probe:** `GET http://<ip>/info` returns a small JSON carrying `model` and `mac` (some firmware also `vtIp`).
It is cheap — read it before committing to a session. 🟡

**Fingerprint (which bucket?):**
```text
if  standard Moonraker answers on tcp:7125  →  ROOTED (bucket C)  → see klipper-moonraker.md
elif tcp:9999 accepts a plain WS upgrade    →  STOCK  (bucket B)  → this paper
else                                        →  not LAN-networked (bucket A / offline)
```
⚠️ Stock Creality OS **does** run Moonraker internally, but bound to **loopback behind nginx** (its web UI on `:4408` /
`:4409`), *not* LAN-reachable. Route on **LAN `:7125` reachability**, never on "Moonraker exists." Rooting rebinds
Moonraker to the LAN. Re-fingerprint on every reconnect (an OTA can revert root). 🟡

See [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md) for the cross-vendor
discovery/LAN-mode shapes.

## Credentials / auth

The stock **LAN `:9999` socket is unauthenticated** — there is **no access code, token, or client certificate** to
obtain, and none to ship. This is a pure LAN-trust model; an implementer connects directly. That is the whole story for
the local path documented here.

A separate **Creality Cloud** service exists for remote access. It is a *different* transport (an account-bound MQTT
relay), it requires the owner to bind the device to their account and hold a **per-user cloud token** (obtained through
Creality's app/site — a mechanism, never a value), and it is **region-bound and firmware-fragile** (a firmware update
can unbind it). It reaches the same printers, but **the LAN path needs none of it** and it is out of scope for this
paper. Crucially, the cloud user token is **not** any kind of LAN credential — do not conflate them.
See [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md) §1–2.

## Reading state

**Push-hybrid.** The printer streams flat state objects unsolicited; a client merges each inbound object into one
running dict and additionally pokes a `get` on a timer (~2–5 s) as a backstop, plus a `boxsInfo` poll **only when a
feeder is present** (`cfsConnect`). This sits between pure-push (Moonraker) and pure-poll — closer to a gentle poll with
live pushes during a print. See [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md)
§5.

The report is a **flat field bag**. Field spellings drift across models/firmware, so an implementer needs an **alias
map** (some targets arrive under two names). Key fields (exact wire keys): 🟡

- **Temperatures** (plain °C): nozzle `nozzleTemp` (current) / `nozzleTemp2` (target; some firmware `targetNozzleTemp`)
  / `maxNozzleTemp`; bed `bedTemp`|`bedTemp0` / `bedTemp2` (target) / `maxBedTemp` (indexed for multi-bed); chamber
  `boxTemp` / `boxTemp2`. A structured `temperature.{nozzle,bed,box}.{value,target,max}` also appears.
- **Progress:** `printProgress` (0–100 int; also `dProgress`). ⚠️ **A percent, but the OS is Klipper-based → very likely
  FILE-BYTE position, not time.** Do **not** extrapolate an ETA from it until a capture proves it is time-based. See
  [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md) §2. 🟡/⚪
- **Times:** `printLeftTime` (remaining), `printJobTime` (elapsed), `printStartTime`. Source-read as **seconds** (unlike
  the minutes some brands use), but the tick unit still wants a capture-confirm — log the raw value before any math. See
  [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md) §3. 🟡
- **Job:** `printFileName`, `layer`, `TotalLayer`.
- **Fans / light / speed:** `modelFanPct` / `caseFanPct` / `auxiliaryFanPct` (+ aliases `fan`/`fanCase`/`fanAuxiliary`);
  `lightSw` (0/1); `curFeedratePct` / `speedMode`.
- **Feed / runout:** `feedState`, `FilamentStatus`, `materialStatus` (`1` = runout); `cfsConnect` gates the feeder poll.
- **Error:** `err:{errcode,key,value,errLevel}`. `err.key` indexes a **139-entry message dictionary** the vendor
  frontend carries; the neutral fault test is `errcode != 0` (or `key ∉ {0, 30000}`), then look up `key` for the text.

**State (native `state` int → normalized).** Read from the vendor frontend's own write-gate logic, which groups the
edges: 🟡 (grouping) / ⚪ (fine labels for 6/7/8)

| `state` | native meaning | normalized |
|--------:|----------------|------------|
| 0 | idle / processing | standby |
| 1 | printing | printing |
| 2 | complete | complete |
| 3 | failed | error |
| 4 | abort / stopped | cancelled |
| 5 | paused | paused |
| 6 | pausing / paused-variant | paused *(busy edge)* |
| 7 | busy (stopping / homing?) | busy |
| 8 | printing-variant (recovery?) | printing *(busy edge)* |

The frontend treats `state ∈ {1,5,8}` as "printing in progress" and `{5,6}` as "paused", which pins 6→paused-side,
8→printing-side, 7→busy — enough to map all of 0–8 safely; only the fine label per edge wants a live capture.
⚠️ `deviceState` is a **separate** online/health integer (`-1` offline / `0` online-idle / `1` busy) — **do not conflate
it with `state`.** For an "is it safe to write?" gate, derive from the *composite* read (non-empty `printFileName` +
`printProgress` + `err.errcode` + `selfTestStep`) plus the busy set `{1,5,6,7,8}`, not a single field. 🟡

## Writing / control

All control is `{"method":"set","params":{<key>:<val>}}`, **fire-and-forget** — no ACK; confirm by watching the next
pushed state. The command shapes below are read from the vendor's own frontend (first-party **source**), but the
**runtime behavior is unvalidated on hardware** — every write drives a hot, moving machine, so gate writes behind an
explicit "enable" and validate against your own device before trusting them.

| Intent | `params` payload |
|--------|------------------|
| **Print-start** | `{"opGcodeFile":"printprt:"+<on-device path>, "enableSelfTest":0}` (`1` = start with self-test / auto-calibration) |
| Delete file | `{"opGcodeFile":"deleteprt:"+<path>}` |
| Pause / Resume | `{"pause":1}` / `{"pause":0}` |
| **Stop / cancel** | `{"stop":1}` |
| Nozzle temp | `{"nozzleTempControl":<°C>}` (multi-nozzle: `{"setNozzleTemp":{"id":<n>,"temp":<°C>}}`) |
| Bed temp | `{"bedTempControl":{"num":<idx>,"val":<°C>}}` |
| Chamber temp | `{"boxTempControl":<°C>}` |
| Speed % | `{"setFeedratePct":<int>}` (`{"speedMode":1}` = silent) |
| Light | `{"lightSw":1\|0}` |
| Fan on/off (part/aux/case) | `{"fan":1\|0}` / `{"fanAuxiliary":1\|0}` / `{"fanCase":1\|0}` |
| Fan speed % | raw `{"gcodeCmd":"M106 P<ch> S<0-255>"}` (P0 model, P1 case, P2 side) |
| Home | `{"autohome":"X Y"}` then `{"autohome":"Z"}` |
| Jog axis | `{"setPosition":"X<mm> F3000"}` (Z uses `F600`) |
| Error handling | `{"errorHandling":0\|1}` / `{"cleanErr":1}` / `{"repoPlrStatus":0\|1}` (retry / clear / power-loss-recovery) |
| **Arbitrary G-code** | `{"gcodeCmd":"<gcode>"}` — a raw escape hatch |
| E-stop | **no dedicated verb** → `{"stop":1}` (cancel) or `{"gcodeCmd":"M112"}` (⚪ inferred) |

> ⚠️ Two corrections worth internalizing: **(1) LAN light is `lightSw`, not `led`** — the `led` key is the *cloud* path
> (an HTTP POST to a cloud RPC route), not the `:9999` socket. **(2) There is no flow-rate `set` key** on the LAN;
> flow, if settable, goes via `gcodeCmd` (`M221`). The `gcodeCmd` passthrough is the **highest-risk surface** (fan,
> homing, extrude, `M112` all reachable) — gate it hardest, and validate a no-op (`M105`) before ever trusting `M112`.
> Contrast a typed emergency-stop verb on documented stacks.

**Print launch (two-step):** 🟡

1. **Upload** — `POST http://<ip>:80/upload/<url-encoded name>` (multipart or raw body), **no auth**, `200/201` = ok,
   accepts `.gcode` / `.gcode.3mf`. (Legacy machines FTP-push instead; a `:81 /server/files/upload` alternate is also
   present in vendor source — probe on hardware.) **Upload ≠ start.**
2. **Launch** — the client polls device-side file readiness ("under decompression"), then sends the print-start `set`
   frame above over `:9999`. The `<on-device path>` is the printer-side location of the just-uploaded file (files live
   under a `gcodes/` prefix); an absolute-path form sometimes cited is ⚪ unconfirmed.

**File format.** Creality Print v5.0.0+ is an **OrcaSlicer fork**, so its `.gcode` / `.gcode.3mf` carries Prusa/Orca-
style embedded base64 PNG thumbnails (`; thumbnail begin` / `; thumbnail end`) and `; key = value` metadata comments —
reuse a Prusa/Orca 3MF parser, **not** a Cura one (pre-5.0 Creality Print was Cura-based, with different markers). 🟡

## Multi-material / feeders (CFS)

CFS (Creality Filament System) is Creality's AMS-class unit — a bank of slots feeding one hotend, up to **4 units × 4
slots = 16**. Read via `{"method":"get","params":{"boxsInfo":1}}`, gated on `cfsConnect`. It sits on the **rich** end of
the feeder spectrum: per-slot remaining **%** *and* **RFID** *and* per-box **dry-box** telemetry. See
[`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md) for the neutral model. 🟡

**Read shape** — `boxsInfo.materialBoxs[]`, each unit carrying:

- `box_type` — ⚠️ **three-valued**: `0` = normal 4-slot CFS, `1` = extra box (variable slots), `2` = mini / **single-
  slot** CFS. **Do not hardcode 4 slots** — key the slot count off `box_type`.
- `cfsName` (a per-unit label), and per-box **`temp` + `humidity`** (dry-box telemetry).
- `materials[]` slots, each: `material_id` (slot index; letter A–D = `material_id % 4`), `name` / `type` / `vendor`,
  `color` (`#RRGGBB`), **`percent`** (remaining), `minTemp` / `maxTemp`, **`rfid`**, `state` (int; meanings uncaptured),
  `selected` (active slot).

Normalize `color` to an uppercase `RRGGBB` at the boundary; keep the slot key **opaque per unit** (e.g. a
`box:slot` token), not a global index; treat `rfid` as opt-in/internal (privacy). ⚠️ Wire spelling varies — reads use
`id`/`type`, the vendor desktop names them `box_id`/`box_type`; **alias both.**

**Write frames** (source-read; gate as experimental until hardware-validated): color→slot map
`{"colorMatch":{"path":<path>,"list":<mapping>}}`; feed/retract `{"feedInOrOut":{"boxId":<b>,"materialId":<s>,
"isFeed":0|1}}`; slot edit `{"modifyMaterial":{…}}`; `{"refreshBox":{"boxId":<b>,"materialId":<s>}}`; dry-box control
`{"dryBox":{…}}`. The **print-time color→slot map** rides the print-start (`colorMatchInfo`) — see the pattern's
print-time-slot-map section. 🟡

## Quirks & gotchas

- **Three protocols, one brand** — route by live service, re-fingerprint on reconnect (an OTA can revert root); SE
  (Marlin/A) vs KE (Klipper/B) are one letter apart and opposite buckets.
- **Stock runs Moonraker on loopback** behind nginx — route on LAN `:7125` reachability, not on "Moonraker exists."
- **No response correlation** — `set`/`get` is fire-and-forget; confirm via the next pushed object, never by an ACK.
- **Progress is a percent but the OS is Klipper-based** → treat it as file-byte position, not time (the classic
  absurd-ETA bug). Prefer a firmware-reported remaining-time field.
- **`lightSw`, not `led`**, for LAN light; **no flow-rate key** (use `gcodeCmd`/`M221`); **no dedicated e-stop**.
- **`gcodeCmd` is a raw passthrough** — the highest-risk write; gate hardest.
- **Vendor spellings on the wire** — a read field `nozzleMaterailStatus` and a download path `humbnail` are as-shipped;
  match them exactly.
- **`wsslicer` subprotocol and the `heart_beat`→`"ok"` keepalive are community lore**, absent from the vendor frontend
  — implement defensively, don't depend on them.
- **Single-source model quirks:** a K2-base has been reported to emit a spurious `targetBoxTemp:0`; whether the Ender-3
  V3 KE accepts a CFS kit is ambiguous — don't advertise a feeder for a KE by default.
- **Firmware drift** — every fact here is "as of mid-2026 firmware"; Creality OTAs frequently and can move fields.

## Confidence & validation

- 🟡 **Source-read (first-party):** the entire stock `:9999` wire — transport, envelope, command set, **print-start**,
  the read field-set, the `state` enum grouping, the `err` dictionary, and the CFS read/write frames — is read from
  Creality's **own** committed device-manager frontend (the LAN client shipped inside their open-source slicer). That is
  the strongest form of source-read (it is the vendor's own client, not third-party RE), but it is **shape, not
  behavior**: **no stock Creality has been bench-validated here.** The paper is source-only overall, hardware-unvalidated
  — validate live values, and especially every **write**, before shipping.
- 🔵 **Community only:** the `wsslicer` subprotocol and the `heart_beat`→`"ok"` keepalive (from independent LAN-client
  integrations; not in the vendor frontend).
- ⚪ **Inferred:** an `M112` e-stop via `gcodeCmd`, the absolute on-device path form, and the CFS slot `state`-int
  meanings.
- **Bucket C (rooted)** is high-confidence by inheritance — it is literally standard Moonraker `:7125`
  ([`klipper-moonraker.md`](klipper-moonraker.md)). **Bucket A (Marlin/USB)** is [`marlin-serial.md`](marlin-serial.md).

**Open gaps — the capture that closes each** (a hardware-owner's highest-value contribution):

- Does a real K1/KE **accept the print-start frame**, and how does the file-readiness transition sequence? → capture an
  upload → launch on a stock K1/KE.
- **Fine labels for `state` 6/7/8** → capture the `state`/`deviceState` stream across idle → print → pause → complete →
  fail.
- **Write-echo behavior** → issue each `set` (light/temp/pause/stop), confirm in the next push; validate `gcodeCmd` with
  a no-op `M105` before `M112`.
- **CFS slot `state`-int meanings** + K2-native vs K1-kit parity + whether the KE takes a CFS kit → `boxsInfo` on a real
  CFS.
- **Timing units** → confirm whether `printProgress` is file-byte, and whether the time fields are truly seconds.
- **Connection exclusivity** → does a second `:9999` socket (alongside the vendor app) destabilize the printer?
- **File-format markers** → confirm the Orca/3MF thumbnail markers + metadata keys on a real Creality Print export
  (hardware-free).

## Sources

Clean-room, facts-only. The stock `:9999` wire is documented from **Creality's own open-source slicer** (Creality Print,
an OrcaSlicer fork, GPL-3.0): its committed **device-manager frontend** (the LAN control client) for the WebSocket wire,
print-start, command set, error dictionary, and CFS frames; its send-to-printer code for the HTTP/FTP **upload**
transport; and its client code for **UDP discovery**. These are **uncopyrightable interface facts** (ports, JSON field
names, envelope shape, the error dictionary's structure), described in my own words — **no slicer, plugin, or firmware
source was copied.** Corroborated by ≥4 independent community LAN-client integrations (licenses range from AGPL-3.0 to
no-license to MIT — read for facts only, never copied) and by Creality's own AGPL cloud plugin, which echoes the same
`{"method","params"}` field vocabulary from the cloud side. The **rooted** path is standard Moonraker; the
model→firmware boundary is anchored by Creality's own GPL Klipper firmware forks (consumed only as *facts* proving the
boundary — never vendored). No certificates, keys, tokens, cloud provisioning secrets, or real device identifiers appear
(the LAN path is unauthenticated). Confidence-tagged per [`../CONFIDENCE.md`](../CONFIDENCE.md); **source-read wire ≠
hardware-validated.** Passed [`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md).
