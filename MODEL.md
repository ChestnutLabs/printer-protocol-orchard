# The Neutral Model — the shape every adapter maps *into*

The orchard's whole thesis is: **each vendor speaks a different dialect, but a good integration maps them all into one
neutral shape**, so the rest of your code sees a single surface. That target shape is described piecemeal across the
[patterns](patterns/README.md) and every paper's *Reading state* section — this page **collects it in one place** and
points at the machine-readable schemas that encode it.

> **What this is / isn't.** This is a *synthesis* — the recommended neutral target, reconciled from the 11 papers and
> the cross-cutting patterns. It is not a wire format any printer speaks. The **per-vendor mappings** into it are the
> facts, and each carries its own confidence tag in its paper and schema. Where papers use slightly different words for
> the same neutral concept, this page is the reconciling authority (e.g. Duet's paper says `idle`; the neutral term is
> `standby`).

The model has three parts: **lifecycle state**, the **feeder/slot model**, and the **job/timing model**.

---

## 1. Lifecycle state

Collapse each vendor's native print state to one neutral lifecycle value. The canonical set (the union used across the
per-vendor [`state-enum.json`](schemas/README.md) schemas):

| Neutral state | Meaning |
|---------------|---------|
| `offline` | not reachable / link down |
| `connecting` | reachable but not ready — booting, updating, opening the port |
| `standby` | idle and ready, no active job *(some papers call this `idle`)* |
| `preheating` | warming up for/before a job |
| `printing` | actively printing |
| `paused` | job paused |
| `cancelled` | job cancelled / stopped by user or host |
| `complete` | job finished successfully |
| `error` | fault / halted / emergency-stopped |
| `busy` | non-print activity — homing, macro, toolchange, mid-operation |
| `unknown` | unmapped value — **degrade here, never raise** |

**Rules.**

- **Map any unrecognized native value to `unknown`, never to `error`.** A new firmware string is not a fault.
- Carry **optional sub-state hints** alongside the neutral state rather than inventing new top-level states:
  `needs-user` (PrusaLink `ATTENTION` — waiting on a human; do **not** flatten to plain `error`), `ready`
  (PrusaLink `READY` vs `IDLE` on Buddy firmware), and the transient `pausing`/`cancelling` (OctoPrint keeps these
  distinct).
- **A finished-and-failed job can read as `standby`.** Several stacks return to idle on abort (Bambu → `IDLE`), so a
  failed job looks like plain standby unless you *also* read the fault channels — see
  [`patterns/faults-and-errors.md`](patterns/faults-and-errors.md).

**Per-vendor mappings** (native → neutral) live next to each paper:

| Vendor | Native field | Schema |
|--------|--------------|--------|
| Anycubic | `state` (+ `project.state`) | [`anycubic/state-enum.json`](schemas/anycubic/state-enum.json) |
| Bambu | `gcode_state` | [`bambu/state-enum.json`](schemas/bambu/state-enum.json) |
| Creality | `state` (int `0`–`8`) | [`creality/state-enum.json`](schemas/creality/state-enum.json) |
| Duet / RRF | `state.status` (14-value) | [`duet/state-status-enum.json`](schemas/duet/state-status-enum.json) |
| Elegoo SDCP | `PrintInfo.Status` / `CurrentStatus` | [`elegoo/sdcp-state-enum.json`](schemas/elegoo/sdcp-state-enum.json) |
| Klipper / Moonraker | `print_stats.state` | [`klipper/state-enum.json`](schemas/klipper/state-enum.json) |
| OctoPrint | `state.flags` (booleans) | [`octoprint/state-enum.json`](schemas/octoprint/state-enum.json) |
| PrusaLink | `printer.state` | [`prusalink/state-enum.json`](schemas/prusalink/state-enum.json) |
| Snapmaker U1 | `print_stats.state` (Moonraker) | [`snapmaker/state-enum.json`](schemas/snapmaker/state-enum.json) |
| FlashForge | — | *no schema:* the newer path's enum lives inside a closed library and the legacy path documents no discrete tokens (see the paper) |
| Marlin (USB) | — (synthesized) | *no native enum:* state is synthesized from the stream (`M27`, `busy: processing`, `Error:`, `//action:*`); see [`marlin-serial.md`](protocols/marlin-serial.md) |

Canonical enum + sub-states as data: [`schemas/normalized/lifecycle-state.json`](schemas/normalized/lifecycle-state.json).

---

## 2. Feeder / slot model

Every multi-material unit folds into **one small neutral model** built on three invariants (full rationale:
[`patterns/multi-material-feeders.md`](patterns/multi-material-feeders.md)):

1. **An opaque per-slot atom** — reduce every vendor's slot to `{ material?, color, vendor?, sku?, source? }`, all
   optional and degrading to `null`. **Normalize `color` to an uppercase `RRGGBB` string at the boundary**, even though
   vendors send RGB tuples, `RRGGBBAA`, `#RRGGBB`, or 0.0–1.0 floats.
2. **Capability classes keyed on *presence*, never a vendor name** — three shapes cover everything: a **bank of slots →
   one hotend** (an MMU/AMS), a **single external spool**, and (orthogonally) a **toolchanger** (multiple docking
   toolheads). Detect by what's present, not by branding.
3. **An opaque, adapter-owned `slot_key`** — every vendor mints incompatible global-slot arithmetic (`box*4 + local`,
   `ams_id*4 + slot`, a `(canvas_id, tray_id)` pair, a `box:type:id` token). **Never reconcile them to a shared index**
   — keep the key opaque per adapter. This is what makes coverage total.

Everything richer (`remaining %`, RFID uuid, dry-box telemetry) is **optional and degrades** — vendors disagree wildly
on what they expose. Encoded as data: [`schemas/normalized/feeder-model.json`](schemas/normalized/feeder-model.json).

---

## 3. Job & timing model

One normalized shape so downstream code never re-does unit math (full rationale + the traps:
[`patterns/timing-normalization.md`](patterns/timing-normalization.md)):

- **Time → plain integer `seconds`** at the adapter edge. Vendors send minutes, seconds, or milliseconds; convert once,
  never multiply/divide by 60 or 3600 again downstream.
- **Filament → `grams`** (derive from `remaining %` × slot weight where only a percentage is exposed).
- **Progress → a `0.0`–`1.0` fraction**, and — critically — carry a **`progress_kind`**: `time-based` **or**
  `file-byte`. A naive `elapsed / progress` ETA is systematically wrong near the end for the `file-byte` kind (most
  Klipper/Moonraker-descended and object-model stacks), correct only for the `time-based` kind (Anycubic, Bambu,
  PrusaLink, Elegoo SDCP).
- **Remaining time by source precedence:** a firmware-reported "time remaining" first; else `estimate − elapsed` when
  the file metadata carries a total; else time-based extrapolation **only** with `time-based` progress.

Encoded as data: [`schemas/normalized/job-model.json`](schemas/normalized/job-model.json).

---

## Why this is the center of gravity

An adapter's only job is: **native wire → this neutral model**. Get the three parts right and a slicer plugin, a farm
manager, or a dashboard is written **once** against the neutral surface and inherits every printer the orchard covers —
plus any future one, the moment its adapter lands. The papers tell you *how each vendor differs*; this page tells you
*what they all become*.
