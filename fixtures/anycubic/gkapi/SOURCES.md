# Anycubic — gkapi dialect fixtures — provenance

Backs [`../../../protocols/anycubic.md`](../../../protocols/anycubic.md) (🟢 hardware-validated).

- **Model / firmware:** Kobra 3 (model `20024`), firmware `2.4.6.7` — Anycubic "gkapi" cloud stack. (The gkapi dialect
  also covers Kobra 2 / S1.)
- **Values are sanitized / synthetic.** Field **structure and key names are the real wire schema**; device ids / `cn` /
  tokens / IPs / filenames are replaced with stable fakes (`192.0.2.20` TEST-NET-1, `T-FAKE`, `benchy.gcode`).
  `msgid`s are synthetic UUIDv4-shaped constants; `timestamp`s are synthetic epoch-ms.

## gkapi vs avata (why this dialect is captured separately)

- The `info` report is **near-identical** to avata (same `state`, nested `temp`, fans, `print_speed_mode`, `project`,
  `features`, `urls`, `version`).
- **The envelope adds `state` / `code` / `msg`** (e.g. `print` reports carry envelope `state="printing"`).
- `info` adds **`box_fan_level`** (filament-box fan).
- **3 speed modes** (`stable` / `standard` / `sport`), vs avata's 4.

| Fixture | State | Notes |
| --- | --- | --- |
| `info_idle.json` | free | targets `0`, `project: null`; envelope `state="done"`. |
| `info_printing.json` | busy / printing | `project.state="printing"`, progress 51%, speed 2. |
| `info_paused.json` | busy / paused | `pause=1`, progress 60%, speed 3 (sport). |
| `info_preheating.json` | busy / preheating | `print_status=6`, progress 0. |
| `tempature_report.json` | — | flat temps, envelope `state="done"`. |
| `print_report.json` | — | envelope `state="printing"`; gkapi extras (`display_filename`, `source_info`). |
| `heartbeat.json` | — | empty-type heartbeat (`data: null`). |

`preheating` / bare `busy` are preserved on the wire and normalized as unknown+raw pending an enum extension. The
detailed feeder reports (`extfilbox` / `multiColorBox`) are query/change-driven and were **not** seen in passive
read-only capture.
