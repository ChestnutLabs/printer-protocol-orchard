# Protocols

One white paper per printer **family**. Start from a paper's **"At a glance"** block, then read the section you need.
Facts are confidence-tagged ([`../CONFIDENCE.md`](../CONFIDENCE.md)); check each paper's **Confidence & validation**
section before relying on it.

New printer? Copy [`_TEMPLATE.md`](_TEMPLATE.md) → `protocols/<vendor>.md`, research it with
[`../METHOD.md`](../METHOD.md), and run [`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md) before publishing.

## Papers

| Printer family | Paradigm | Paper |
|----------------|----------|-------|
| **Anycubic** (Kobra) | MQTT `:9883` + HTTP `:18910` | [`anycubic.md`](anycubic.md) 🟢 *(worked exemplar)* |
| **Bambu Lab** (X1/P1/A1/H2D) | MQTT `:8883` + FTPS `:990`, LAN mode | [`bambu.md`](bambu.md) 🟢 |
| **Creality** (stock OS) | `ws://:9999` `{method}` + HTTP `:80/upload` | [`creality.md`](creality.md) 🟡 |
| **Elegoo** Centauri (SDCP) | WebSocket `:3030` + UDP; CC2 MQTT | [`elegoo.md`](elegoo.md) 🟡 |
| **Klipper / Moonraker** (generic + reuse cluster) | HTTP + WS JSON-RPC `:7125` | [`klipper-moonraker.md`](klipper-moonraker.md) 🟡 |
| **Snapmaker** U1 | Moonraker + `:8100` auth wrapper | [`snapmaker.md`](snapmaker.md) 🟡 |
| Qidi / Sovol / Phrozen (Moonraker) | HTTP + WS JSON-RPC | → [`klipper-moonraker.md`](klipper-moonraker.md) *(Vendor variants)* |
| **Duet / RepRapFirmware** | `rr_*` HTTP / DSF REST | [`duet.md`](duet.md) 🟡 |
| **OctoPrint** (host) | HTTP REST + SockJS | [`octoprint.md`](octoprint.md) 🟡 |
| **PrusaLink** (host) | HTTP REST (poll) | [`prusalink.md`](prusalink.md) 🟡 |
| **FlashForge** (5M/AD5X) | FlashNetwork SDK; legacy `:8899` | [`flashforge.md`](flashforge.md) 🟡 |
| **Marlin** over USB serial | line G-code over serial | [`marlin-serial.md`](marlin-serial.md) 🟡 |

> **All families are documented.** Most are 🟡 **source-read** (read from the vendor's own published slicer/SDK/docs —
> wire-shape correct, but not yet confirmed on hardware); Anycubic + Bambu are 🟢 **hardware-validated**. The
> highest-value contribution is a **🟢 hardware capture** that promotes a 🟡 paper — see each paper's *Confidence &
> validation* section for the exact open gaps. Sanitized fixtures live in [`../fixtures/`](../fixtures/).

## Conventions

- **One file per family**, not per SKU — group machines that share a stack, note the per-model deltas.
- If a family needs its own fixtures/schemas, use a folder: `protocols/<vendor>/` with the paper as `README.md`.
- Cross-cutting concepts (feeders, timing, discovery) live in [`../patterns/`](../patterns/) — link to them instead of
  repeating.
