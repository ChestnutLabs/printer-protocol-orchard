# Anycubic — avata dialect fixtures — provenance

Backs [`../../../protocols/anycubic.md`](../../../protocols/anycubic.md) (🟢 hardware-validated).

- **Model / firmware:** Kobra X (model `20030`), firmware `1.2.0.2` — Anycubic "avata" cloud stack.
- **Values are sanitized / synthetic.** Field **structure and key names are the real wire schema**; device ids / `cn` /
  `usn` / `token` / IPs are replaced with stable fakes (`192.0.2.10` TEST-NET-1, `USN-FAKE`, `CN-FAKE`, `TOKEN-FAKE`,
  `T-FAKE`). `msgid`s are synthetic UUIDv4-shaped constants; `timestamp`s are synthetic epoch-ms.
- **Envelope:** the MQTT message envelope `{type, action, msgid, timestamp, data}` is the real avata wire shape (except
  `info.json`, which is the plain-HTTP `:18910/info` identity document, not an MQTT report).

| Fixture | msg `type` | Notes |
| --- | --- | --- |
| `info.json` | (HTTP `/info`) | The `:18910` identity document — `usn`/`cn`/`token`/`rtspUrl`/`fileUploadurl`. Not an MQTT report. |
| `info_idle.json` | `info` | Cold-idle: `state="free"`, targets `0`, curr ≈ ambient; `project: null`. |
| `info_preheated.json` | `info` | Pre-heated: `state="free"`, targets set (200/60), curr near target. |
| `info_printing.json` | `info` | Active print: `state="busy"` + nested `project{state:"printing", progress, layers, times}`. |
| `tempature_report.json` | `tempature` | Flat `curr_/target_{nozzle,hotbed}_temp` (+ `taskid`). |
| `fan_report.json` | `fan` | `fan_speed_pct` (+ `taskid`). |
| `light_report.json` | `light` | `lights[].{brightness,status,type}`. |
| `print_report.json` | `print` | Job progress: `filename`/`taskid`/`progress`/`curr_layer`/`total_layers`/times. |
| `peripherie_report.json` | `peripherie` | `camera` / `multiColorBox` (ACE) / `udisk` presence. |
| `heartbeat.json` | `""` | Empty-type heartbeat (`data: null`) — ignored by the parser. |

**State values (observed live):** `info.state` is `free` (idle/ready) or `busy` (active/heating). During a print
`info.project` is populated and `info.project.state = "printing"`. `avata` exposes 4 print-speed modes indexed by
`print_speed_mode`.
