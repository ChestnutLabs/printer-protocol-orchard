# Bambu Lab fixtures — provenance

Backs [`../../protocols/bambu.md`](../../protocols/bambu.md) (🟢 hardware-validated on A1-class; X1/P1 specifics
🟡 source-read) and the multi-material pattern in
[`../../patterns/multi-material-feeders.md`](../../patterns/multi-material-feeders.md).

- **Values are sanitized / synthetic.** Field **names and structure are the real MQTT-report wire schema**; every
  identifier is a placeholder — module/AMS serials → `SYNTHETIC-SN-*` / `SYNTHETIC-AMS-SN-0`, RFID `tag_uid` and
  `tray_uuid` → synthetic constants, camera URL → `rtsps://synthetic.invalid/...`, `task_id` / `subtask_id` →
  synthetic sequential ids. No access code appears (the access code is the MQTT **password**, never carried in a
  report payload).
- These are the MQTT `print`/`info` report bodies (the object under the top-level `"print"` / `"info"` key), as
  published by the printer on its per-device topic.

| Fixture | Command / kind | Represents | Notes |
| --- | --- | --- | --- |
| `get_version.json` | `info.get_version` reply | X1/P1-class module inventory | `module[]` of `{name, sw_ver, hw_ver, sn}` (ota / esp32 / mc / th / ams). Synthetic `sn`s; `sw_ver`/`hw_ver` are representative firmware strings. |
| `pushall_x1c.json` | `print.push_status` (full, `msg:0`) | X1C-class full snapshot | The whole-state `pushall`: `gcode_state=RUNNING`, temps incl. `chamber_temper`, `lights_report`, `ipcam`, and a full 4-tray `ams` + external `vt_tray`. |
| `push_status_partial_p1.json` | `print.push_status` (partial, `msg:1`) | P1-class delta | Sparse delta — only changed keys. `nozzle_temper` here carries an observed **bit-packed/sentinel** value, preserved verbatim (do not read it as a plain temperature). |
| `ams_partial_update.json` | `print.push_status` (partial, `msg:1`) | AMS tool-change delta | Minimal `ams` delta during a tray switch (`tray_now`/`tray_pre`/`tray_tar`, bumped `version`). |

**Why these matter:** there is **no command ack** on Bambu — you confirm writes by diffing the status stream, so a
known-good full `pushall` plus representative partial deltas are exactly what an implementer regression-tests their
delta-merge against. `gcode_state` drives the lifecycle; temps/progress/AMS/faults ride along.
