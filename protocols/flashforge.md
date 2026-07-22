# FlashForge (Adventurer / Guider family) — LAN Protocol

> **Status:** 🟡 source-read (FlashNetwork SDK *surface*, from the vendor's GPL slicer fork) + 🔵 community (legacy
> `:8899`) — **no path yet hardware-validated** · **Firmware:** newer models run Klipper internally but speak a
> **proprietary FlashNetwork SDK** on the wire (*not* Moonraker); legacy models are Marlin ·
> **Models:** Adventurer 5M / 5M Pro / A5 / AD5X, Guider 3 Ultra / 4 / 4 Pro (newer); Adventurer 3, Guider 2s, older
> Creator / Finder (legacy)
>
> FlashForge splits into **two LAN generations selected by a device fingerprint.** The newer machines use a
> **topic-based pub/sub SDK whose on-wire encoding lives inside a closed DLL** — only its interface *surface* is
> knowable from source. The legacy machines speak the community-documented **raw-TCP G-code protocol on `:8899`**.

## At a glance

- **Transport:** two generations. **Newer (`bindType:1`)** — topic-based **pub/sub** (MQTT-shaped) driven through a
  closed **`FlashNetwork` SDK**; broker/port/TLS/topic grammar are *inside the DLL* (not observable from source).
  **Legacy (`bindType:0`)** — **raw-TCP ASCII G-code on `:8899`**, request/response.
- **Discovery:** newer path uses a UDP broadcast (inside the SDK) returning per-device records that include a
  **per-device port** (discovered, not fixed); legacy path works from **manual IP** to `:8899`.
- **Auth / credential:** newer path takes a per-device **`checkCode`** (a local access code the owner reads from the
  printer's own screen — same category as Bambu's access code); legacy `:8899` uses a `~M601` login handshake with no
  code. See [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md).
- **Read / status:** newer — **subscribe** to a status topic, plus explicit state/job query calls; legacy — **poll**
  `~M119` / `~M105` / `~M27`.
- **File transfer:** newer — SDK file-list / thumbnail / start-job / send-gcode calls; legacy — `~M28`/`~M29` SD upload
  then `~M23` select-and-print.
- **Print launch:** newer — a single start-job call referencing an on-device file; legacy — upload then `~M23`.
- **Feeders / multi-material:** **Material Station** — a 4-spool feeder on the AD5X (newer path only).
- **⚠️ The load-bearing gotcha:** the newer machines **run Klipper internally but do *not* expose Moonraker.** LAN
  control goes through the proprietary FlashNetwork SDK, and **the wire is closed** — the vendor's published header
  gives you the full call/field/auth *surface*, but never the byte encoding. Do not try to drive a 5M as a Moonraker
  printer; it will not answer.

## Transport & connection

**Two device generations, chosen by a `bindType` fingerprint.** The SDK's LAN-device descriptor carries a
`connectMode` (`0` = LAN, `1` = WAN/cloud) and a `bindType` (`0` = "old", `1` = "mqtt"). 🟡 An implementer routes on
`bindType` (equivalently: whether the printer answers on `:8899`).

**Newer path (`bindType:1`) — closed pub/sub SDK.** The connection model is **publish/subscribe over topics** even on
the LAN: a create-connection call, then subscribe / unsubscribe / send / send-multi / stop calls against topic names.
The interface is MQTT-shaped, but **the concrete broker address, port, TLS posture, topic grammar, and payload
encoding are all inside the closed `FlashNetwork` library** — the vendor's slicer loads it at runtime
(`LoadLibraryW` / `dlopen` + symbol resolution) and does **not** commit the binary. What *is* published (in the GPL
slicer fork's C header) is the complete function/struct/field surface; what is *not* is the wire. 🟡 surface / the
encoding is unobservable from source. An implementer therefore has two honest options, neither of which requires
bundling any vendor binary or secret:

1. **Drive the user's own already-installed `FlashNetwork` library out-of-process** — owners of these printers already
   have the vendor slicer installed, which ships the DLL. A small local bridge process loads *the user's own copy* and
   calls the documented surface (discover → connect with `checkCode` → control / start-job / subscribe). This mirrors
   the mTLS-cert-from-the-user's-own-slicer posture elsewhere in the orchard: user-owned, never redistributed.
2. **Reconstruct the wire from a hardware capture** — the header gives the full call surface; capturing the library
   talking to a real device recovers the broker/port/TLS/topic/payload, letting a client speak it natively with no DLL
   dependency. Higher effort and hardware-gated.

**Legacy path (`bindType:0`) — raw-TCP G-code on `:8899`.** A plain TCP request/response wire carrying ASCII G-code
lines with a leading `~` sentinel (`~M119`, `~M105`, `~M27`, `~M23`, …), the long-standing FlashForge control protocol
also used by community tooling. 🔵 Buildable directly; no DLL, no cloud.

## Discovery & identity

**Newer path.** A LAN-discovery call returns a list of device records — serial number, name, IP, **port**, VID/PID,
`connectMode`, `bindStatus` (bound/unbound), and `bindType`. A follow-up detail call returns the fuller device state.
The **port is per-device and discovered**, not a fixed constant. The discovery mechanism itself (a UDP broadcast) is
inside the SDK. Device identity for every subsequent call is the tuple **`(ip, port, serialNumber, checkCode)`**. 🟡

**Legacy path.** Manual IP to `:8899`; identity comes from the machine-info query (`~M115`) and status
(`~M119`). 🔵 See [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md) — manual IP is
the guaranteed path; broadcast discovery is a nice-to-have on top.

## Credentials / auth

**Newer path — a per-device `checkCode`.** This is a local access code the **owner reads from their own printer** (it
also appears as a `user_access_code` in the slicer's stored device config). It is passed on **every** LAN control call
alongside `(ip, port, serialNumber)`. It is a user secret in exactly the sense the orchard means — obtained by the owner
from their own hardware, never bundled or bypassed — and an integration should prompt for it and store it encrypted at
rest. 🟡

**Legacy path — a login handshake, no code.** `~M601 S<channel>` claims the control channel (and `~M602` releases it);
there is no per-device secret on the classic `:8899` wire. 🔵

The **cloud/WAN** surface (`connectMode:1`) — account binding, password/SMS token issuance, and a separate AI
image/model-generation pipeline — is out of scope for a LAN reference; a local integration targets `connectMode:0`
only. 🟡

## Reading state

**Newer path.** State is delivered by **subscribing** to a status topic on the SDK connection, backed by explicit
state-query and job-query calls. The report *shape* (field names, temperature encoding, progress semantics, timing
units) is **inside the closed library and not observable from the published surface** — so this reference cannot yet
state the newer path's state enum, temperature fields, or whether its progress is time-based or file-byte. Those are
open gaps to be closed by a capture (see Confidence & validation). What the surface *does* confirm is the presence of
distinct **state**, **job**, and **error-code** query calls, plus plate-detect and first-layer-detect signals. 🟡 An
implementer should map whatever the capture reveals into the neutral fields any client needs — a normalized state,
temperatures in °C, and a progress fraction — per
[`../patterns/timing-normalization.md`](../patterns/timing-normalization.md).

**Legacy path — poll.** Classic FlashForge `:8899` is poll-only; synthesize a change stream from the diffs. 🔵

- **Status / endstops:** `~M119` returns the machine status and endstop/axis state. 🔵
- **Temperatures:** `~M105` returns nozzle and bed temperatures in plain °C. 🔵
- **Progress:** `~M27` returns SD-print progress as **byte position** (`SD printing byte X/Y`) — this is **file-byte
  progress, not time-based**, so extrapolating an ETA from it is systematically wrong near the end of a file. 🔵 ⚠️
- **Remaining time:** where the firmware emits `~M73 R<n>`, `R` is in **minutes** (×60 for seconds) — a classic 60×
  trap. 🔵 ⚠️ Both traps are the subject of
  [`../patterns/timing-normalization.md`](../patterns/timing-normalization.md).

## Writing / control

**Newer path — the SDK control surface (`bindType:1`).** The published header exposes a full LAN control set, each call
taking the device tuple + `checkCode`. Named by function (interface facts; the encoding is closed): 🟡

| Capability | Call (by name) |
|------------|----------------|
| Temperatures | set nozzle / bed / chamber |
| Chamber light | light control |
| Air filter | air-filter control |
| Fans | fan / clear-fan control |
| Motion | move (jog), homing, extrude |
| Print control | print start / pause / stop, plus job-query and state-query |
| Detection | plate-detect, first-layer-detect |
| Errors | error-code / fault surface |
| Material Station | material-station control + config, and independent-material control + config (see below) |
| Files & jobs | list on-device g-code, fetch a g-code thumbnail, **start a job**, send raw g-code |

**Print launch (newer):** a single **start-job** call referencing a file already on the device (list the on-device
files first, or transfer one via the send-gcode path), rather than a multi-step upload-then-command dance. 🟡

**Legacy path — G-code verbs (`:8899`).** 🔵

- **Login / release:** `~M601 S<channel>` / `~M602`.
- **Motion:** `~G28` home, `~G1` moves, `~M18`/`~M84` disable steppers.
- **Temperatures:** `~M104` (nozzle), `~M140` (bed).
- **File upload:** `~M28 <size> 0:/user/<name>` opens an SD write, the file bytes follow, `~M29` closes it.
- **Print launch:** `~M23 0:/user/<name>` selects and starts the uploaded file; `~M24`/`~M25` resume/pause, `~M26`
  stop.

> ⚠️ Every control verb on either path drives a hot, moving machine. The newer path's *behavior* is unverified against
> hardware and the legacy path is community-sourced — validate against your own device and gate all writes behind an
> explicit "enable writes" switch in any client.

## Multi-material / feeders

The **AD5X** carries a **Material Station** — a **4-spool** feeder (a bank of slots feeding one hotend) on the newer
path. The SDK exposes both a **material-station** control/config surface and an **independent-material** control/config
surface (single-spool / direct-feed mode). Per-slot fields (material, color, quantity) live in the config payload,
which is **inside the closed library** — the *count* of slots and the presence of the feeder are knowable from the
surface, but the per-slot report shape is an open gap until a capture on an AD5X confirms it. 🟡 An implementer should
fold whatever the capture reveals into the neutral per-slot model (an opaque `{material?, color as RRGGBB, vendor?,
sku?}` atom, with any "remaining %" nullable) described in
[`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md), and keep the print-time color→slot
map as the key to per-material accounting. The legacy machines are single-extruder — no feeder. 🔵

## Quirks & gotchas

- **Klipper inside ≠ Moonraker on the wire.** The newer machines run Klipper internally but expose **no** Moonraker
  JSON-RPC — LAN control is the proprietary FlashNetwork SDK. A Moonraker probe will simply not answer. (This is the
  single biggest wrong assumption to make about the 5M/A5/AD5X.)
- **The wire is closed; only the surface is public.** The vendor's GPL slicer fork publishes the full C header
  (functions, structs, `checkCode` auth, pub/sub model, control verbs), but the real networking library is loaded at
  runtime and **not committed**. You can enumerate *what* the printer can do without knowing *how* the bytes look. The
  only committed binary in the fork is a small (~6 KB) config/cert blob, not the SDK.
- **Two generations, one brand.** Route on `bindType` (or on whether `:8899` answers). Assuming a single FlashForge
  protocol will strand half the fleet.
- **Per-device port.** The newer path's control port is **discovered per device**, not a fixed number — don't hardcode
  it.
- **Legacy progress is file-byte; legacy remaining is minutes.** `~M27` is a byte position (bad for ETA);
  `~M73 R` is minutes (60× trap). Normalize at the edge.
- **The `~` sentinel.** Legacy `:8899` G-code lines are prefixed with `~`; omitting it is a common first-attempt
  failure.
- **Cloud/AI surface is adjacent but out of scope.** The same SDK carries WAN account-binding, token issuance, and an
  AI generation pipeline; a LAN integration ignores all of it.

## Confidence & validation

- 🟡 **Source-read (newer path).** The FlashNetwork *interface surface* — discovery record, `checkCode` auth, the
  pub/sub connection model, the control/file/material-station call set, the two-generation `bindType` split — is read
  directly from the vendor's own published GPL slicer fork. The *shape* is first-party-correct; **nothing on this path
  is hardware-validated**, and the on-wire encoding (broker/port/TLS/topic/payload), the status report shape, the state
  enum, and all timing units are **not observable from source** because they live in the closed library.
- 🔵 **Community (legacy path).** The `:8899` raw-TCP G-code dialect (`~M601` login, `~M119`/`~M105`/`~M27` status,
  `~M28`/`~M29`/`~M23` upload-and-print, `~M73 R` minutes) is community-documented, not read from the vendor fork.
  Corroborate on a real legacy machine before relying.
- **Open gaps** (each closed by a specific capture):
  - A capture of the FlashNetwork library ↔ a real Adventurer 5M / AD5X: broker/port, TLS posture, topic names, the
    `checkCode` handshake, and the status-report JSON (this closes the state enum + timing-unit questions at once).
  - The **Material Station** config/report payload on an AD5X: `slotCnt`, per-slot material/color/quantity.
  - Confirmation of the legacy `:8899` sequence (`~M601` login → `~M28`/`~M29` upload → `~M23` start) on an
    Adventurer 3 / Guider 2s.
  - The exact `bindType` / `:8899` fingerprint used to route newer-vs-legacy on a mixed fleet.

## Sources

Clean-room, facts-only. The newer-path surface was extracted from **FlashForge's own published, GPL OrcaSlicer fork**
(the device layer under `src/slic3r/GUI/FlashForge/`, and specifically the C API header that declares the `fnet_*`
function set, the LAN-device descriptor struct with its `connectMode`/`bindType`/`bindStatus` fields, the `checkCode`
auth, the pub/sub connection calls, the `fnet_ctrlLanDev*` control verbs, and the material-station config surface) plus
the runtime-loader source that shows the networking library is `dlopen`'d at runtime and **not committed**. No slicer
code was copied — only interface facts, described in this reference's own words. The legacy `:8899` G-code dialect is
from community reverse-engineering / OctoPrint-family tooling, not the vendor fork. **No certificate, key, `checkCode`,
token, or real device identifier is reproduced here**; the `checkCode` is documented as a *mechanism* the owner reads
from their own printer, and any vendor networking DLL is the *user's own* installed copy, never bundled. Passed
[`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md).
