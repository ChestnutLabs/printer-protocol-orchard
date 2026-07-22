# Glossary

Shared vocabulary used across the orchard. Where vendors use different names for the same idea, the neutral term is
listed first.

## Connection & transport

- **LAN mode / LAN-only mode** — the printer setting that disables the vendor cloud and allows direct local-network
  access. **Nearly every brand has one**, usually paired with a per-device local credential (see *access code*). Names
  vary ("LAN Only", "Developer Mode", "LAN mode") but the posture is the same: *cloud off, local access via a code.*
- **Access code / auth code / check code** — the per-device local credential a user reads from their own printer to
  authenticate a LAN connection. A user secret; never shipped in this orchard.
- **Discovery** — how a client finds printers on the network: mDNS/Bonjour, SSDP, UDP broadcast, or manual IP entry.
  Many brands support only manual IP; some add a broadcast.
- **Poll vs push** — whether the printer *pushes* state changes (MQTT/WebSocket subscriptions) or must be *polled*
  (periodic HTTP/serial queries). See **poll-synth**.
- **Poll-synth (synthesized state feed)** — when a printer only supports polling, the client polls on a cadence and
  *synthesizes* a change-event stream from the diffs. The standard shape for HTTP-poll and serial printers.

## Firmware & control stacks

- **Klipper / Moonraker** — a popular open firmware (Klipper) fronted by an HTTP+WebSocket API server (Moonraker,
  usually `:7125`). Many brands ship it (sometimes locked down); if a printer speaks Moonraker, most "different"
  vendors collapse to the *same* protocol.
- **Marlin** — classic firmware controlled by **G-code over USB serial** (no network of its own). The one non-network
  paradigm.
- **RepRapFirmware (RRF) / Duet** — firmware with a rich **Object Model**; a toolchanger leader.
- **G-code flavor** — which dialect the printer expects (`klipper`, `marlin`, `reprapfirmware`, …); a strong tell for
  which protocol stack it runs.

## Multi-material & tools

- **Feeder / MMU (multi-material unit)** — hardware that presents **multiple filament inputs to one hotend** (a color
  changer). Bank of spools → shared nozzle. Examples: Bambu AMS, Anycubic ACE, Elegoo CANVAS, Creality CFS, ERCF, Box
  Turtle, Happy-Hare-driven units.
- **Capability provider vs hardware** — for DIY MMUs, the **software framework** (e.g. Happy Hare) is the capability
  provider that exposes a uniform interface, and the **physical unit** (ERCF, Box Turtle, …) is an implementation
  behind it. Detect the *provider*, not each hardware model.
- **Toolchanger** — **multiple physical toolheads that dock/undock**, each with its own hotend and per-tool XYZ
  offset. Distinct from an MMU (which is N inputs → 1 hotend).
- **IDEX** (Independent Dual Extruder) — two independent X carriages. Supports **duplication** (both print the same
  object), **mirror**, and **independent** (each prints a different object at once — a *concurrent-jobs* idea, not just
  a motion mode).
- **Splicer** — a device (e.g. Palette) that joins multiple filaments into **one stream before the printer**; the
  printer sees a single spool and is *blind* to the multi-material.
- **Slot / lane / gate / tray** — a single filament position in a feeder. **Slot map / color map / ams_mapping** — the
  print-time assignment of sliced colors/tools to physical slots.

## Files & jobs

- **Print launch** — the sequence to start a job: usually *upload the sliced file* (HTTP multipart / FTPS / SD) then
  *issue a start command*. Some printers need a two-step upload; some print from SD after transfer.
- **Sliced file** — a `.gcode` or `.gcode.3mf` produced by a slicer; carries thumbnails, per-tool filament usage
  (`; filament used [mm]/[g]`), and metadata that the wire often doesn't report.

## Units & timing

- See [`patterns/timing-normalization.md`](patterns/timing-normalization.md). Key trap: **time fields are in minutes on
  some brands, seconds on others, and milliseconds ("ticks") on a third** — and **progress is time-based on some,
  file-byte-position on others** (so ETA-from-progress is wrong for the latter).
