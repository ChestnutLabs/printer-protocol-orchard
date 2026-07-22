# Anycubic (Kobra family) — LAN Protocol

> **Status:** 🟢 hardware-validated (Kobra X `20030` fw `1.2.0.2`; Kobra 3 `20024` write path) · **Firmware:**
> Klipper-based, Anycubic "avata" / "gkapi" cloud stack · **Models:** Kobra X, Kobra 2 / 3 / S1 (+ variants)
>
> Anycubic printers are driven over a **per-printer MQTT session on TLS `:9883`**, with a plain-HTTP `:18910`
> side-channel for identity and file upload. Two closely-related dialects — **avata** (Kobra X) and **gkapi** (Kobra
> 2/3/S1) — share one command set and differ only in a few report fields.

## At a glance

- **Transport:** MQTT over TLS **`:9883`** (client presents a slicer cert; the printer's own server cert is *not*
  verified). Plus plain-HTTP **`:18910`** for identity + file upload.
- **Discovery:** manual IP; identity via `GET http://<ip>:18910/info`. A **sleeping printer goes HTTP-silent** on
  `:18910`.
- **Auth / credential:** the MQTT username/password/device-id are **derived** from the printer via `/info`+`/ctrl`;
  the mTLS client cert/key come from the user's own Anycubic slicer install (never shipped here — see Credentials).
- **Read / status:** **poll-hybrid** — an idle printer pushes nothing (so poll ~every 48 s); an active one auto-pushes
  temperature + print reports.
- **File transfer:** multipart `POST http://<ip>:18910/gcode_upload` (needs an `X-File-Length` header).
- **Print launch:** two-step — HTTP upload, then MQTT `print:start`.
- **Feeders:** ACE multi-material (`multiColorBox`) + single external spool (`extfilbox`).
- **⚠️ The load-bearing gotcha:** a command's **action goes in the JSON payload, never in the topic**. Append the
  action to the topic and the printer silently drops it (`messageHandler not found`) while still ACKing — it looks like
  it worked.

## Transport & connection

Per-printer MQTT on **`:9883`**, TLS. The client presents an **mTLS client cert** (the Anycubic slicer's cert/key) but
sets `verify_mode = CERT_NONE` and `check_hostname = False` — the printer serves a **self-signed, expired
`O=AnyCubic`** cert and negotiates legacy TLS, so the client also lowers the OpenSSL security level
(`DEFAULT:@SECLEVEL=0`). MQTT username/password are set; keepalive 60 s. 🟡

**Message envelope** — compact JSON, `{",":"}`-separated:
```json
{"type":"<msgType>","action":"<verb>","msgid":"<uuid4>","timestamp":<epoch_ms>,"data":<any>}
```
The **gkapi** dialect extends it with `{"state":…, "code":…, "msg":…}` (emitted only when present). `msgid` is a
UUIDv4; `timestamp` is epoch **milliseconds**. 🟢

**Topic grammar:** `anycubic/anycubicCloud/v1/<channel>/<modelId>/<deviceId>/<msgType>` — **the action is in the
payload, not the topic** (see the gotcha above). Channels:
| Channel | Use |
|---------|-----|
| `slicer/printer` | slice/launch flow — `print:start`, `multiColorBox:getInfo` |
| `web/printer` | all live control + monitoring |
| `printer/public` | printer reports; subscribe the wildcard `…/printer/public/<model>/<device>/#` |

Correlation is by echoed `msgid` (with a fallback to a report-topic suffix for `getInfo`-style replies). Every command
is ACKed with a bare `{"msgid":…}` on a `…/response` topic. 🟢

## Discovery & identity

Plain-HTTP `GET http://<ip>:18910/info` returns the identity (tolerant of a bare object or a `{"code":200,"data":{…}}`
wrapper). Golden shape (values synthetic): 🟢
```json
{"deviceName":"Kobra X","deviceType":"FDM","modelId":"20030","modelName":"Kobra X","ip":"192.0.2.10",
 "rtspUrl":"rtsp://192.0.2.10/live","fileUploadurl":"http://192.0.2.10:18910/gcode_upload"}
```
Any HTTP error → treat as **unreachable/asleep**. Note: the avata `/info` omits `fileUploadurl` (take it from the MQTT
report's `urls.fileUploadurl` instead); gkapi advertises it.

## Credentials / auth

Two credentials, both user-owned:
1. **The mTLS client cert/key** live inside the user's own Anycubic slicer (`cloud_mqtt.dll` in the slicer install).
   *This orchard documents that they live there; it never ships them.* An integration extracts them from the user's own
   installation. 🟡
2. **The MQTT username/password/device-id** are derived at connect time: `GET /info` yields a `token`; then
   `POST /ctrl` with a signed request returns an AES-CBC-encrypted config blob carrying the credentials. The signature
   is `md5( md5(token[:16]) + ts + nonce )`; the config is decrypted with `key = token[16:32]`, IV = the response's
   `token`. 🟢

## Reading state

**Poll-hybrid, ~48 s baseline.** An idle printer emits nothing unsolicited, so a client polls a read-only query set
(`print:query`, `status:query`, `tempature:query`, `fan:query`, `light:query`, `multiColorBox:getInfo`). While
printing, the printer auto-pushes `tempature` and `print` reports; the poll is just a backstop. 🟢

Report `type`s: `info` (rich snapshot), `status`, `tempature` *(sic — the misspelling is the real verb)*, `fan`,
`light`, `print`, `file`, `peripherie`, `multiColorBox`, and an empty-type heartbeat.

- **Temperatures:** plain °C (`curr_/target_nozzle_temp`, `curr_/target_hotbed_temp`). 🟢
- **Progress:** `progress` **0–100, time-based** → a real time fraction (unlike file-byte-position progress on some
  brands). 🟢
- **Times:** `print_time` / `remain_time` are in **minutes** (×60 for seconds). *(A common cross-brand trap — see
  [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md).)* 🟢
- **State (native → normalized):** `free`→standby; `busy`/`printing`/`auto_leveling`/`resuming`→printing;
  `preheating`→preheating; `pausing`/`paused`→paused; `stoped`(sic)/`canceled`→cancelled; `finished`→complete;
  `failed`→error. For an `info` report, `project.state` takes precedence over the top-level `state`. 🟢

## Writing / control

Command verbs (exact `type:action`) — all on `web/printer` unless noted:
`print:start` *(slicer/)*, `print:pause/resume/stop/update`, `tempature:set` *(sic)*, `fan:setSpeed` *(not `fan:set`)*,
`light:control`, `axis:move`, `axis:turnOff` *(→ M84)*, `skip:start`, `info:setPrinterName`,
`video:startCapture/stopCapture`, plus the feeder verbs below. 🟢

**Print launch (two-step):** 🟢
1. multipart `POST <fileUploadurl>` with the file field `gcode`, a `filename` field, and header **`X-File-Length:
   <raw byte length>`**. Must be a real `.gcode.3mf`. Success = `{"code":200,"data":{"gcode":<stored_name>}}`.
2. MQTT `print:start` on `slicer/printer` referencing the uploaded file (payload carries `filename`, `md5`, and an
   `ams_box_mapping` for multi-material).

> ⚠️ Control writes drive a hot, moving machine — validate against your own device and gate them behind an explicit
> "enable writes" in any client.

## Multi-material / feeders

- **ACE** (`multiColorBox`): a bank of slots feeding one nozzle. Per-slot fields: `type`, `color` (RGB), `status`
  (**`==5` = loaded**), `sku`, `weight` (g), `consumables_percent`. Boxes carry an `id` (`-1` = the stock 4-slot
  toolhead, `0..3` = ACE units) and a `model_id` (ACE Gen 2 = `40002`). Note **brand/RFID identity is *not* on the LAN
  wire** — it's only reachable over the ACE's USB link. 🟢
- **extfilbox**: a single external spool; its `loaded` flag doubles as the runout signal. 🟢
- See [`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md) for the cross-vendor model.

## Quirks & gotchas

- **Action-in-payload** (the big one, above).
- The verb is **`tempature`** (misspelled) and **`fan:setSpeed`** — spelling matters on the wire.
- Server TLS cert is expired/self-signed by design → verify-off + legacy ciphers are required to connect.
- avata `/info` omits the upload URL; read it from the MQTT report.
- A sleeping printer is simply HTTP-silent on `:18910` (not an error to panic on).

## Confidence & validation

- 🟢 Validated on a real **Kobra X (`20030`, fw `1.2.0.2`)** for the read path and on a **Kobra 3 (`20024`)** for the
  write/command path (12 commands captured byte-for-byte).
- 🟡 The `/ctrl` credential derivation is source-read + a synthetic round-trip; the exact live response codes aren't
  pinned.
- **Open gaps** (a capture would close them): the avata ACE `multiColorBox` live shape (validated on gkapi, assumed
  identical); the keep-alive sub-protocol; other model ids (Kobra 4 / S1 variants).

## Sources

Clean-room, facts-only. Extracted from Anycubic's own open-source slicer (the "SlicerNext" OrcaSlicer fork) device
layer + a plain-HTTP `:18910` inspection + sanitized MQTT captures from an owner's Kobra X / Kobra 3. No slicer code
was copied; no certificate/key/credential values are included (the cert lives in the user's own slicer install). Passed
[`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md).
