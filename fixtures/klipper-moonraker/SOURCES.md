# Klipper / Moonraker fixtures — provenance

Backs [`../../protocols/klipper-moonraker.md`](../../protocols/klipper-moonraker.md) (🟡 source-read), plus the
toolchanger and multi-material material in
[`../../patterns/multi-material-feeders.md`](../../patterns/multi-material-feeders.md).

- **Values are sanitized / synthetic** examples of the object model. They contain **no** IPs, serials, MACs, tokens, or
  credentials of any kind (Moonraker status payloads never carry those). `msgid`s are synthetic constants; `timestamp`s
  are synthetic epoch-ms.
- **⚠️ Envelope caveat (read this):** the outer `{type:"status", action:"update", msgid, timestamp, data}` wrapper is a
  **normalized test envelope, not Moonraker's wire format**. On the wire Moonraker pushes
  `{"jsonrpc":"2.0","method":"notify_status_update","params":[<objects>, <eventtime>]}`. The **`data` object here is the
  real Moonraker object-model snapshot** — the object keys (`print_stats`, `virtual_sdcard`, `extruder`, `heater_bed`,
  `display_status`, `mmu`, `toolchanger`, `tool T0`, `ktc`, `trad_rack`, …) and their field names are exactly what
  `printer.objects.subscribe` / `notify_status_update` return. Implementers should parse the contents of `data`.
- **Presence-based, not fixed:** Moonraker exposes only the objects a given printer's config defines. These fixtures
  each isolate one config so the object shapes can be diffed independently.

## Core lifecycle

| Fixture | Objects | Represents |
| --- | --- | --- |
| `status_idle.json` | `print_stats`(standby), `virtual_sdcard`, `extruder`, `heater_bed`, `fan`, `gcode_move` | Cold idle snapshot. |
| `status_printing.json` | + `display_status`, `heater_generic chamber` | Active print; note `virtual_sdcard.progress` is **byte position**, not time. |
| `delta_temp.json` | `extruder`, `fan_generic aux` | Sparse delta — only changed keys (the normal steady-state push). |

## Multi-material (software providers layered on Klipper)

| Fixture | Object | Provider |
| --- | --- | --- |
| `status_mmu.json` | `mmu` | Happy Hare — full state: `num_gates`, `ttg_map`, `endless_spool_*`, per-gate `gate_status`/`material`/`color`/`temperature`/`spool_id`, `flow_rate`/`headroom`. |
| `status_mmu_ace.json` | `mmu` | Happy Hare over an ACE-class unit — gate arrays with colors + `gate_filament_name`. |
| `status_trad_rack.json` | `trad_rack` | Native TradRack — `curr_lane`/`active_lane`/`next_lane`/`tool_map`/`selector_homed`. |
| `delta_mmu.json` | `mmu` | Sparse `mmu` delta during a load (`gate`/`action`/`filament`). |

## Toolchangers

| Fixture | Objects | Module |
| --- | --- | --- |
| `status_toolchanger.json` | `toolchanger` + `tool T0`/`tool T1` | klipper-toolchanger — per-tool `gcode_[xyz]_offset`, `extruder`, `fan`, `mounted`/`active`. |
| `status_ktc.json` | `ktc` + `ktc_tool 0`/`1` | KTC — per-tool `offset_[xyz]`, `heater`, `standby_temp`, `state`. |
| `status_u1.json` | `extruder`/`extruder1..3` + `toolhead.extruder` + `save_variables.variables.currentextruder` | Snapmaker U1 multi-extruder — per-extruder `extruder_offset` and the active-extruder read path. |
