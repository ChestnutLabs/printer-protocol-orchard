# Pattern — Modeling Multi-Material Feeders

Every brand's multi-material unit looks different on the wire, but they collapse into **one small neutral model**. Get
that model right and vendor AMS units, DIY MMUs, and retrofit combiners all fold into the same surface — new ones slot
in without a redesign.

---

## The three invariants (design your neutral model around these)

1. **An opaque per-slot atom.** Reduce every vendor's slot to `{ material?, color(as RRGGBB), vendor?, sku?, source? }`
   — all optional, degrade to `null`. Normalize color to an uppercase `RRGGBB` string at the boundary even though
   vendors send RGB tuples, `RRGGBBAA`, `#RRGGBB`, or 0.0–1.0 floats.
2. **Capability classes keyed on *presence*, never a vendor name.** Three shapes cover everything: a **bank of slots →
   one hotend** (an MMU/AMS), a **single external spool**, and — orthogonally — a **toolchanger** (multiple physical
   toolheads that dock). Detect by *what's present*, not by branding.
3. **An opaque, adapter-owned `slot_key`.** Each vendor mints mutually-incompatible global-slot arithmetic (one uses
   `box*4 + local`, another `ams_id*4 + slot`, another a `(canvas_id, tray_id)` pair, another a `box:type:id` token).
   Never try to reconcile them to a shared index — keep the key opaque per adapter. This single decision is what makes
   coverage total.

Everything else (remaining %, RFID, dry-box) is **optional and degrades** — because vendors disagree wildly on what
they expose (see below).

## Two kinds of feeder source

### A. Vendor AMS-class units — per-slot state on the vendor wire
Bambu AMS, Anycubic ACE, Elegoo CANVAS, Creality CFS, FlashForge Material Station. They report slots directly on their
LAN protocol, but with very different **richness**:
- **Rich:** Bambu AMS (per-slot RFID uuid, remaining grams + %, sku) and Creality CFS (per-slot %).
- **Identity-only:** Anycubic ACE (sku/color/weight on LAN; **brand/RFID only over USB**, not the wire).
- **Sparse (the outlier that proves invariant #1):** Elegoo CANVAS reports color/material but **zero remaining
  quantity and no RFID** — so a "remaining %" field *must* be nullable.

### B. DIY / open MMUs — a software *provider* over Klipper/Moonraker
ERCF, Box Turtle, Night Owl, TradRack, QuattroBox, 3MS, and more. **Detect the software provider, not the hardware:**
- **Happy Hare** is the dominant provider — one Klipper object (`printer.mmu`) fronts most open MMUs (ERCF, Box Turtle,
  Night Owl, TradRack, 3MS, …). Read *that* and you cover the whole family at once.
- **AFC (Armored Turtle)** is a *second, Happy-Hare-incompatible* provider (Box Turtle's native software) that
  publishes lane data via the **Moonraker database** rather than a `printer.mmu` object — so it needs its own reader.
- **Native TradRack** exposes its own `printer.trad_rack` object with sparse inventory.

> This mirrors the whole orchard's lesson: the *software layer* is the capability provider (like Moonraker is the
> protocol), and the *physical unit* is an implementation behind it.

### C. State-blind cases — the wire tells you nothing
- **Retrofit combiners** (e.g. CoPrint ChromaSet/KCM) run on Klipper via custom macros with **no queryable
  multi-material object** — you can detect the unit's *presence* but not per-slot state.
- **Splicers** (e.g. Palette) join filaments into one stream *before* the printer, so the printer sees **one spool** and
  is entirely blind to the multi-material.
- For both, per-material consumption must come from the **sliced file** (see below), not the wire.

## The print-time slot map (the assignment)

When a job starts, the client sends a **color→slot / filament→tool map** — the assignment of sliced colors/tools to
physical slots. Vendors name it differently (`ams_mapping`/`ams_mapping2`, `slot_map` of `{t, canvas_id, tray_id}`, an
`ams_box_mapping`, an `extruder_map_table`) but it's the same idea, and it's the **key to per-material accounting**:
it's what tells you *which physical filament* a given sliced color consumed.

## Consumption / accounting

If you care about how much of *each* filament a multi-color job used:
- **Rich feeders** report remaining grams/% on the wire — diff it.
- **Sparse / state-blind feeders** report nothing usable → read the **sliced file** (`; filament used [mm]/[g]` per
  filament + the `T<n>` map), joined to the slot map above. See
  [`timing-normalization.md`](timing-normalization.md) §4.

## Related distinctions (don't force these into the feeder model)

- **Toolchanger** — N physical toolheads that dock, each with its own hotend + per-tool XYZ offset. Orthogonal to a
  feeder (which is N inputs → 1 hotend). A tool's "active tool" is a *physical* index; a feeder's is a *logical
  filament* index — keep them separate.
- **IDEX** — two independent carriages; supports duplication/mirror (motion modes) and *independent* mode (two
  different objects at once — a concurrent-jobs concept, not a feeder). Neither is a feeder.
