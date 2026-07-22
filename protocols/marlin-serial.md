# Marlin (USB Serial) — Direct G-code Protocol

> **Status:** 🟡 source-read — documented from public Marlin / RepRap G-code references (open-source firmware docs,
> community-proven for a decade); no hardware capture in this orchard yet · **Firmware:** Marlin 1.x / 2.x and
> Marlin-class (Repetier, Smoothieware, RepRapFirmware-over-serial, vendor forks) · **Models:** most sub-$300 FDM
> machines with a USB port and no network (Ender-3 V2/S1, CR-10, Anet, and kin)
>
> This is the one **non-network** paradigm in the orchard: line G-code streamed over a **USB serial port**, one command
> at a time, gated on an `ok` reply. There is no discovery, no auth, and no event stream — physical access *is* the
> authorization, and every bit of state is **polled**. The one thing to know: **opening the port reboots the printer.**

## At a glance

- **Transport:** a **USB-CDC / virtual serial port** — `COMx` (Windows), `/dev/ttyUSB*` (CH340/FTDI/CP2102 USB-UART
  bridge) or `/dev/ttyACM*` (native USB on 32-bit boards). Newline-terminated ASCII G-code, **no framing**. Baud is
  **autodetected** (`115200` / `250000` common).
- **Discovery:** none over any network. **OS port enumeration + probe** (open → `M115` → look for a Marlin banner). A
  USB **VID/PID identifies the UART chip, not the printer.**
- **Auth / credential:** **none.** No pairing code, no TLS, no LAN-mode toggle — whoever holds the cable can drive the
  machine.
- **Read / status:** **poll-only** (no push). `M105` temps, `M114` position, `M27` SD progress, `M119` endstops;
  `M155 S<sec>` opts into temperature auto-reporting. State is **synthesized** from the stream.
- **File transfer:** **no clean standard** — either host-stream the whole file live (`ok`-gated) or the slow
  `M28`/`M29` write-to-SD path (not universally supported).
- **Print launch:** host-stream (Path A) *or* SD select-and-start (`M28`→`M29`→`M23`→`M24`, Path B).
- **Feeders / multi-material:** none queryable on the wire; tool changes (`T<n>`) live in the sliced file.
- **⚠️ The load-bearing gotcha:** opening the port pulses **DTR/RTS and reboots the board** — expect ~1–2 s of silence,
  then a `start` banner. Treating that silence as a dead port is the classic failed-connect bug.

## Transport & connection

A Marlin printer presents a **virtual serial port** over USB. On 8-bit and many 32-bit boards a USB-UART bridge chip
(CH340, FTDI, CP2102) creates a `/dev/ttyUSB*` / `COMx` device; native-USB 32-bit boards enumerate as
`/dev/ttyACM*` (USB-CDC). The VID/PID belongs to that **bridge chip**, so it identifies the electronics family, never
the specific printer. 🟡

**There is no message framing** — the wire is a byte stream of newline-terminated ASCII G-code. Two properties define
the transport:

- **Baud is not discoverable.** Common rates are `115200` and `250000`, occasionally `230400` / `57600`. An
  implementer **autodetects** by opening at a candidate rate and checking whether `M115`/`ok` parses, cycling rates
  until it does. 🟡
- **`ok`-gated flow control.** Send one command line, **wait for `ok`, then send the next.** The printer's serial RX
  buffer is small; overrunning it without waiting corrupts the stream. (Advanced hosts pipeline within the firmware's
  advertised buffer size, but strict one-line-at-a-time `ok`-gating is the safe baseline.) 🟡

**Reliable mode — line numbers + checksum + resend.** For robustness Marlin accepts `N<line> <command>*<checksum>`
where the checksum is a byte-wise **XOR** over the line; the counter is reset with `M110 N<n>`. On a garbled line the
printer replies **`Resend: <N>`** and the host must **retransmit from that line number**. A production client either
implements this resend loop or accepts dropped/garbled commands. 🟡

**The stream is unsolicited-interleaved.** Between `ok`s the printer also emits: temperature auto-reports (if enabled),
`busy: processing` keepalives, `echo:` messages, `Error:` lines, and **host action commands** (`//action:pause`,
`//action:cancel`, `//action:out_of_filament`). A parser must **demux all of this from the single stream** and match
`ok`/`Resend:` to the outstanding command. `busy: processing` is a **keepalive** — "alive but not ready for the next
line" — and must not be read as data or as a hang. 🟡

## Discovery & identity

There is **no network discovery** (no mDNS/SSDP/UDP — there is no network). "Discovery" is **OS serial-port
enumeration**: list the candidate ports, then **probe each** by opening it, waiting out the DTR reset (below), and
sending `M115`. A Marlin-class banner in the reply confirms it's a printer and reveals the firmware. 🟡

`M115` is the **identity + fingerprint** in one query. It returns the firmware name and version and a block of
`CAP:<name>:<0|1>` capability bits — e.g. auto-report temperature, the emergency-command parser, SD support. Because
"Marlin" is really a family (see Quirks), capability detection is a **heuristic off `M115` + the firmware name string**
with conservative fallbacks, not an assumption. 🟡

> Because opening the port resets the board, an identity probe **cannot** be instantaneous — budget for the reboot
> before the first `M115` will answer. See the DTR-reset trap under Transport.

## Credentials / auth

**None.** A bare serial line has no authentication layer — no access code, no API key, no TLS, no LAN-mode toggle. The
security boundary is entirely **physical**: possession of the USB cable is the authorization. This makes onboarding
trivial (nothing to prompt for) and makes the *host* the trust boundary — anything that can open the port has full,
unauthenticated control of a hot, moving machine. Treat write access accordingly (see Writing / control). 🟡

## Reading state

**Poll-only — there is no event stream.** An implementer periodically issues read queries and **synthesizes** a
change-feed from the diffs (the poll-synth posture shared with other push-less stacks — see
[`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md) §5). The read vocabulary: 🟡

| Query | Returns |
|-------|---------|
| `M115` | Firmware name/version + `CAP:` capability bits — the fingerprint |
| `M105` | Hotend/bed temperatures (current + target), plain **°C** |
| `M114` | Current `XYZE` position |
| `M27` | SD print progress, as a line like `SD printing byte 1234/5678` — **only** while printing from SD |
| `M119` | Endstop states |
| `M155 S<sec>` | **Opt in** to periodic temperature auto-reporting (removes the need to spam `M105`), if the firmware advertises it |

**No native status verb → derive normalized state from the stream.** Unlike a networked printer with a single status
field, bare Marlin has no "what are you doing" query. An implementer synthesizes the neutral state any client needs
(see [`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md)) from stream signals: ⚪

- port open and `ok`-responsive, no active job → **idle / operational**
- `M27` shows `byte X/Y` with `X<Y`, or a host stream is in flight → **printing**
- `busy: processing` lines → still **working** (keepalive, *not* an error, *not* idle)
- a pause was issued / a `//action:pause` arrived → **paused**
- `Error:` lines or `//action:cancel` → **error / aborted**
- stream exhausted, or `M27` reaches `X==Y` → **complete**

The printer's **only unsolicited "push"** is the **host action command** (`//action:pause`, `//action:cancel`,
`//action:out_of_filament`) — the firmware asking the *host* to take action (e.g. filament runout). A reader must honor
these even though everything else is poll-driven. 🟡

**Progress is the weak spot — and it is file-position, not time.** For an SD print, `M27` reports **file-byte
position** (`byte X/Y`). For a **host-streamed** print the only progress is **lines-sent / total**, which the *host*
counts because the printer does not know the file's length. Both are **file-position** semantics: extrapolating an ETA
from them is **systematically wrong near the end of a print** (the last few percent of a file can be a large fraction
of the time). Layer counts and time estimates come from **parsing the sliced file**, not from the printer. If the
sliced G-code embeds `M73 R<minutes>` progress hints, note those are in **minutes**. See
[`../patterns/timing-normalization.md`](../patterns/timing-normalization.md) (§2 file-byte vs time-based, §3 the
minutes-vs-seconds trap). 🟡

## Writing / control

All control is **raw G-code**, and every write drives a hot, moving machine on a fragile cable — **dangerous-tier**.
An implementer should gate writes behind an explicit "enable writes" and default to observe-only. 🟡

Common verbs: `G28` home · `G0`/`G1` move · `M104`/`M140` set hotend/bed temp · `M106`/`M107` fan on/off · `M84`
steppers off · `M220`/`M221` feed/flow override. Two hazards shape the control loop:

- **Blocking commands.** `M109`/`M190` (set-temp-**and-wait**) and `G28` can **hold the command channel for minutes**.
  The client must not treat that latency as a hang — `ok` simply won't arrive until the operation finishes. 🟡
- **Emergency stop is out-of-band.** `M112` (kill), `M108` (break out of a wait), and `M410` (quickstop) are handled
  by Marlin's **emergency command parser** *ahead of* the planner buffer — so they act even when the buffer is full. A
  naive "queue `M112` and wait for `ok`" behind a full buffer would be far too slow; an implementer must deliver these
  through the emergency path (available when `M115` advertises the emergency-parser capability). 🟡

### Print launch & file transfer

There is **no robust file-transfer standard** on bare serial (contrast the networked families' multipart POST / FTPS /
JSON-RPC uploads). Two mutually-exclusive paths, each with a real cost:

**Path A — host-streamed print.** The host reads the sliced `.gcode` and **streams it line-by-line over serial,
`ok`-gated, for the entire print.** Works on *every* Marlin printer and needs no SD card; the host sees every line
(the best live progress available). The severe cost: the host must **stay connected and healthy for the whole job**
(minutes to many hours) — any serial hiccup, host reboot, USB re-enumeration, or DTR glitch **fails the print**.
Progress is lines-sent/total. 🟡

**Path B — upload to SD, then print from SD.** Write the file to the printer's SD/eMMC over serial, then start it and
disconnect: `M28 <name>` (begin write-to-SD) → stream the file body → `M29` (end) → `M23 <name>` (select) → `M24`
(start); manage with `M25` (pause) / `M27` (progress) / `M524` (abort); `M20` lists SD files. The host is only needed
during upload and the print **survives a host disconnect**, and `M27` then gives real byte progress. The cost:
**SD-write-over-serial is slow and not universally supported** — many firmwares lack `M28` or implement it flakily,
an SD/eMMC must be present, and some boards expose the SD as USB mass-storage instead. Detect support via `M115 CAP:`
or trial. 🟡

## Multi-material / feeders

Bare Marlin serial exposes **no queryable multi-material object** — there is no wire query that returns per-slot
material/color/remaining state. Multi-tool machines are driven by **`T<n>` tool-change codes embedded in the sliced
file** (and multi-extruder configs at the firmware level), so the *file*, not the printer, is the source of truth for
which filament a job used. Per-material consumption therefore comes from **parsing the sliced G-code** (`; filament
used [mm]/[g]` comments joined to the `T<n>` map), exactly the state-blind case in
[`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md) (§C) and
[`../patterns/timing-normalization.md`](../patterns/timing-normalization.md) (§4). ⚪

## Quirks & gotchas

- **DTR-reset on connect (the big one).** Opening the port toggles DTR/RTS, which **reboots** ATmega boards and many
  32-bit ones. The printer is unresponsive for ~1–2 s, then emits a `start` banner. Wait for `start`; never treat the
  initial silence as a dead port. Some boards need DTR held deliberately — behavior varies by board. 🔵
- **Baud is a guess.** No handshake advertises it; you cycle rates until `M115`/`ok` parses. 🟡
- **`busy: processing` is a keepalive, not data.** During a long op these mean "alive, not ready" — don't misread them
  as progress or as a stall. 🟡
- **Blocking heats/homes.** `M109`/`M190`/`G28` withhold `ok` for minutes by design. 🟡
- **`Resend:` must be honored.** Without the resend loop, a single line-noise event silently drops or garbles a
  command. 🟡
- **Firmware-dialect fragmentation (the maintenance tax).** "Marlin" spans Marlin 1.x/2.x **plus** Repetier,
  Smoothieware, RepRapFirmware-over-serial, and vendor forks. `M115 CAP:` bits, `M155` auto-report support, the
  `//action:` host-command set, `M28` SD-upload support, and banner formats **all vary**. Capability detection must be
  heuristic with conservative fallbacks — this long tail never fully closes. 🔵
- **OS driver tax.** CH340 driver install on Windows; the `dialout` group and `ModemManager` grabbing the port on
  Linux; `/dev/cu.*` vs `/dev/tty.*` on macOS. Perpetual, per-platform. 🔵

## Confidence & validation

- 🟡 The G-code line protocol (`ok`-gating, `N…*checksum` + `Resend:`, `M110`, the `M105`/`M114`/`M115`/`M27`/`M119`/
  `M155` read verbs, `M28`/`M29`/`M23`/`M24`/`M25`/`M524` SD flow, the `M112`/`M108`/`M410` emergency parser) is
  **read from public Marlin / RepRap G-code documentation** — first-party open-source firmware docs, community-proven
  for over a decade. The *shape* is authoritative; this orchard has not yet attached a **hardware capture** to it.
- 🔵 Board- and firmware-specific behaviors — the exact DTR-reset timing per board/chip, which firmwares actually
  implement `M28` (and how reliably), the `M115 CAP:` matrix across Marlin/Repetier/Smoothie/RRF-serial, and the
  `//action:` command set a given fork emits — are **community-known to vary** and are the least pinned.
- ⚪ The **normalized state derivation** (no native status verb → synthesize from `busy:`/`M27`/`Error:`/`//action:`)
  is an inference from the stream signals, not a single documented field.
- **Open gaps** (a capture would close each): a byte-level connect trace across CH340 / FTDI / native-ACM boards
  showing DTR-reset timing and the `start` banner; a `M115` fingerprint matrix over the common firmware forks; a live
  `M28`→`M29`→`M27` SD round-trip on a firmware that supports it (and confirmation of the ones that silently don't);
  and a filament-runout `//action:out_of_filament` capture. Because writes drive hardware, validate any control path
  on a machine you own before relying on it.

## Sources

Clean-room, facts-only. Derived from **public Marlin / RepRap G-code references** (the open-source firmware's own
documentation and the RepRap G-code wiki) — well-established protocol facts, not reverse-engineering. No firmware
source was copied; behavior is described in the author's own words. There are **no credentials to redact** (bare serial
has no auth), and no captures are bundled. The normalized-state and progress-semantics notes cross-reference
[`../patterns/timing-normalization.md`](../patterns/timing-normalization.md),
[`../patterns/multi-material-feeders.md`](../patterns/multi-material-feeders.md), and
[`../patterns/discovery-and-credentials.md`](../patterns/discovery-and-credentials.md). Passed
[`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md).
