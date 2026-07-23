# Pattern — Faults, Errors & Recovery

Error handling is where naive integrations break. Every vendor surfaces faults on a different channel, in a different
shape, and — the recurring trap — **a job that failed often reads as plain idle** unless you look somewhere else. This
page collects the cross-vendor shape so an adapter can present one neutral fault surface. Per-vendor detail lives in each
paper's *Faults* / *Quirks* sections.

---

## The three lessons that recur across every family

**1. Confirm by the status stream, not the command response.** Almost no family gives a meaningful ack. Bambu has **no
command ack** at all; Creality's `set`/`get` is fire-and-forget; OctoPrint returns a bodyless `204`; Duet and PrusaLink
give no "started" ack; Anycubic ACKs with a bare `{"msgid":…}` that proves *receipt, not effect* (append the action to
the topic and it silently drops while still ACKing). In every case the load-bearing confirmation is a **state transition
in the status stream**, and after a launch you should also watch the fault channel (Bambu's `subtask_id` echo proves the
command landed, not that the print will succeed).

**2. Emergency stop must bypass the normal command queue.** A queued stop sits behind the g-code buffer and won't fire.

- **Klipper / Moonraker / Snapmaker** — use the structured `printer.emergency_stop`; **never** send `M112` through
  `printer.gcode.script`. 🟡
- **Marlin (USB)** — `M112` (kill), `M108` (break a wait), `M410` (quickstop) are handled by the **emergency command
  parser** ahead of the planner buffer; deliver them through that path. 🟡
- **Duet / RRF** — `M112` drives `state.status → halted`; recover with `M999`. Treat as a dangerous, hold-to-confirm
  action. 🟡
- **Creality (stock)** — **no dedicated verb**; `{"stop":1}` cancels, `{"gcodeCmd":"M112"}` is ⚪ inferred (validate a
  no-op like `M105` before ever trusting it).
- **PrusaLink** and **Elegoo CC2** — **no LAN emergency stop at all**; the write surface is job-control only. Don't
  pretend one exists.

**3. "Looks like a fault, but isn't."** Filter these or your UI lights up during a normal print.

- **Bambu** — skip HMS whose low half is `< 0x4000` (firmware emits low values as normal-phase status), and skip a small
  set of short codes emitted during normal user-cancel. An aborted job also returns to `IDLE`. 🟢
- **OctoPrint** — a `409` from `GET /api/printer` is a valid **"not connected"** signal, not a transport failure.
- **PrusaLink** — `ATTENTION` is *waiting-on-a-human*, not a hard error; a `204` on `job` means idle; `axis_*` is
  **absent while moving** (absence ≠ `0`).
- **Elegoo SDCP** — resin-only codes never fire on FDM; a status code outside the known range normalizes to
  **`unknown`, never `error`**.
- **Marlin** — `busy: processing` is a **keepalive** ("alive, not ready"), not a fault and not a hang.
- **Klipper** — a **missing object** is *not capable* / `null`, never an error.

---

## Where each family carries faults

| Family | Fault channel | Recovery surface |
|--------|---------------|------------------|
| **Bambu** 🟢 | `hms[]` (`{attr, code}`) **+** 32-bit `print_error` (`MMMM_EEEE`) | `pause`/`resume`/`stop`; `ams_control` for a stuck change |
| **Creality** 🟡 | `err:{errcode,key,value,errLevel}`; `key` indexes a 139-entry dictionary | `errorHandling` / `cleanErr` / `repoPlrStatus` (retry / clear / power-loss) |
| **Duet / RRF** 🟡 | `state.status == halted`; per-heater `state == fault`; `rr_connect` `err` (`1` bad password / `2` no session) | `M112`→`halted` / `M999` reset; `M25` pause; `M0` cancel |
| **Elegoo SDCP** 🟡 | `sdcp/error` topic; `PrintInfo.Status==14`; file `ErrorNumber` (`0`–`5`); start `Ack` (`0`–`6`) | `Cmd 129/130/131` pause/stop/**resume** (CC1 has live resume) |
| **Elegoo CC2** 🔵 | `machine_status.status` `14`/`15`; `exception_status` (raw int array, no fixed enum) | **pause + cancel only — no LAN resume** |
| **Klipper / Moonraker** 🟡 | `print_stats.state==error` + `print_stats.message`; `notify_klippy_shutdown/disconnected`; `klippy_state` | structured `printer.emergency_stop` (never queued `M112`) |
| **Snapmaker U1** 🟡 | inherits Moonraker (`print_stats.state==error`, `emergency_stop`) | Moonraker `emergency_stop`; `POST /device/stop`; pause/resume/cancel |
| **OctoPrint** 🟡 | `state.flags.error` + `state.error?` string | `POST /api/job {cancel|restart}`; `fake_ack` for a stalled serial line |
| **PrusaLink** 🟡 | `printer.state` `ERROR` / **`ATTENTION`** (needs-user); error bodies `{code, url}` | job-control only (pause/resume/continue/stop) — **no e-stop, no setpoints** |
| **Anycubic** 🟢 | no dedicated channel — `state=failed`→error; gkapi envelope may add `{state, code, msg}`; runout via feeder flags | `print:pause/resume/stop`; `axis:turnOff` (→ `M84`) |
| **Marlin (USB)** 🟡 | `Error:` lines + `Resend: <N>`; host action commands `//action:pause`/`cancel`/`out_of_filament` | resend-from-`<N>` protocol; emergency parser (`M112`/`M108`/`M410`) |
| **FlashForge** 🟡/🔵 | newer: a distinct error-code/fault query call — **shape is inside the closed library (open gap)**; legacy: `~M119` | newer: start/pause/stop; legacy: `~M24`/`~M25`/`~M26` |

---

## The one worked decode — Bambu HMS

Bambu is the only family that documents fault **bit-math**, and it's the template for a neutral fault object. From an
HMS `{attr, code}`: 🟡

```text
severity   = (attr >> 8)  & 0xF     # 1 fatal / 2 serious / 3 common / 4 info
module     = (attr >> 24) & 0xFF
short_code = f"{(attr>>16)&0xFFFF:04X}_{code&0xFFFF:04X}"   # for catalog lookup
```

Fold `print_error` through the same decode and dedupe it against `hms[]`. The human-readable message catalog (~800
codes) is **not** a protocol fact — regenerate it from Bambu's own published list; do **not** copy the copyleft
community dictionaries.

---

## A neutral fault surface

Collapse all of the above into one small shape an adapter emits:

- **`is_fault`** — boolean, from the vendor's own "not-a-fault" test (Creality `errcode != 0`; Bambu after the two
  filters; a lifecycle `error`/`halted`).
- **`severity`** — `fatal | serious | common | info` where the vendor grades it (Bambu), else `serious`.
- **`needs_user`** — surfaced distinctly (PrusaLink `ATTENTION`, filament runout flags) — a stuck-but-recoverable state,
  not a hard error.
- **`code`** / **`message`** — the raw vendor identifier plus any text, passed through (never invented).
- **`recoverable`** — whether a resume/clear exists (CC1 yes, CC2 no), so the UI offers the right action.

And the golden rule from lesson 1: **a job that returned to idle is not proof of success** — reconcile lifecycle state
against the fault channel before reporting "done."
