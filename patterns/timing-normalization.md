# Pattern — Time & Consumption Normalization

Every printer reports time and filament in **different fields and different units**. If your integration has one
normalized shape (seconds for time, grams for filament, a 0.0–1.0 fraction for progress) and each adapter maps into it
correctly, you're fine. Get it wrong and you get the classic **"an 11-minute print shows 112 hours"** bug — always a
unit slip, never a logic bug.

---

## 1. The one rule

> **Convert every time value to plain integer SECONDS at the adapter edge, the moment you read the printer. Nothing
> downstream ever multiplies or divides a time by 60 or 3600 again** — except the final humanizer that formats seconds
> for display.

Units are an **adapter-edge concern**. Normalize once, at the boundary; keep the core in seconds, grams, and a
fraction.

## 2. ⚠️ Progress is not the same thing everywhere

The most dangerous trap, because a `0–100` field *looks* interchangeable but isn't:

| Progress semantics | Meaning | ETA-from-progress? |
|--------------------|---------|--------------------|
| **Time-based** | fraction of *time* elapsed | ✅ `remaining ≈ elapsed/progress − elapsed` works |
| **File-byte position** | fraction of the *g-code file* streamed | ❌ **systematically wrong near the end** (the last few % of a file can be a large chunk of the *time*) |

Which brands are which (see the per-family papers for the exact fields):

- **Time-based** ✅ — Anycubic (`progress`), Bambu (`mc_percent`), PrusaLink (`job.progress`), Elegoo SDCP (`Progress`,
  read verbatim).
- **File-byte** ⚠️ — Klipper/Moonraker (`virtual_sdcard.progress`), OctoPrint (`completion` = `filepos/size`), Duet/RRF
  (derived `filePosition/size`), Marlin (`M27` `SD printing byte X/Y`), and anything that *is* Moonraker underneath
  (Snapmaker, Qidi, rooted-Creality, Elegoo Neptune…). Stock Creality's `printProgress` is a percent but the OS is
  Klipper-based, so treat it as file-byte until a capture proves otherwise.

**Remaining-time source precedence** (fall through on absence):

1. A **firmware-reported "time remaining"** — best; already reflects live speed/pauses.
2. **`estimate − elapsed`** — when the file metadata carries a total estimate.
3. **Time-based extrapolation** `elapsed/progress − elapsed` — **only** with *time-based* progress; **never** with
   file-byte progress.

## 3. ⚠️ The unit traps (minutes vs seconds vs milliseconds)

The 60× (and 1000×) mistake. Membership, from real vendors:

| Unit | Brands (time fields) |
|------|----------------------|
| **Minutes (×60)** | **Anycubic**, **Bambu**, and Marlin/FlashForge `M73 R<minutes>` |
| **Seconds (×1)** | Klipper/Moonraker, PrusaLink, OctoPrint, Elegoo CC1/CC2, Duet/RRF, stock-Creality, Snapmaker |
| **Milliseconds** | ⚠️ Elegoo SDCP's `Timestamp` is Unix **ms** — but the print `CurrentTicks`/`TotalTicks` are **seconds**, *not* ms. Don't `/1000` the ticks. |

> Copying one adapter's parser to another is exactly how a 60× (or 1000×) error spreads. **Log the raw value before any
> math** at the adapter edge — the bug is always visible there.

## 4. Filament → grams

Normalize consumption to **grams**. If a printer reports **length (mm)** — common on Klipper/Duet/Marlin — convert
volumetrically: `grams = π·(d/2)²·length_mm·density`, with per-filament density (default ~1.24 g/cm³ for PLA) and
diameter (1.75 mm). Prefer a reported weight (`[g]`) when present.

**When the wire reports no consumption at all** — some multi-material feeders (e.g. Elegoo CANVAS reports no per-slot
grams; retrofit combiners and splicers report nothing) — the **only** source is the **sliced file**: parse the
`; filament used [mm]/[g]` comments and the `T<n>` tool-changes for a per-tool consumption vector. Use the file's `[g]`
if present; otherwise mm→g via density. *(A material→density table is a handy fallback; match the slicer's own density
so your grams agree with its estimate.)*

## 5. The 30-second debug

Symptom **"short print shows absurdly long time"** → a unit/scale slip. To find it, log the raw field before any math:
```
[adapter] raw remaining = 7   → 7 * 60 = 420 s      (Anycubic/Bambu: minutes ✅)
[adapter] raw duration  = 660 → 660 * 60 = 39600 ❌  (Klipper: SECONDS — must be ×1)
```
Checklist: (1) wrong factor (minutes vs seconds vs ms — §3); (2) double conversion (×60 at ingest *and* display);
(3) wrong field (a *total/estimate* where *elapsed* was expected); (4) a wall-clock duration inflated by a stale job
start time; (5) persisted bad data from an older build — recompute after fixing the math.
