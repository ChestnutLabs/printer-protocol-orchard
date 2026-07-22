# Coverage Map

Which printer families are documented, and which protocol *paradigm* each uses. The single most useful takeaway:
**many "different" vendors run the same underlying stack** — so once you can speak a paradigm, you cover a whole
cluster.

Status: 🟢 hardware-validated · 🟡 source-read · 🔵 community/RE · ✏️ paper published, hardware-validation welcome · ⬜ not yet started.

> **Every family below now has a paper in [`protocols/`](protocols/README.md).** Anycubic + Bambu are 🟢
> hardware-validated; the rest are 🟡 source-read (wire-shape from the vendor's own slicer/SDK/docs, not yet confirmed
> on hardware). A 🟢 capture that promotes a 🟡 paper is the highest-value contribution — each paper's *Confidence &
> validation* section lists the exact open gaps.

## By protocol paradigm

### Moonraker / Klipper (HTTP `:7125` + WebSocket JSON-RPC)
The backbone. If a printer exposes Moonraker, it speaks a common, well-understood protocol regardless of brand — often
plus a thin vendor auth/bootstrap wrapper.
| Family | Notes | Status |
|--------|-------|--------|
| Generic Klipper/Moonraker | The reference; `printer.objects.subscribe`, `printer.print.*`, `/server/files/upload` | ✏️ |
| Qidi (Q/X series) | Plain Moonraker + SSDP discovery | ✏️ |
| Sovol (SV06/07/08/ZERO) | Stock Klipper+Moonraker | ✏️ |
| Snapmaker U1 | Moonraker behind a `:8100` auth/pairing wrapper + a toolchanger extruder-map | ✏️ |
| Phrozen Arco | Moonraker on a non-standard port | ✏️ |
| Rooted Creality (K1/K2/KE) | Standard Moonraker once rooted | ✏️ |
| Elegoo Neptune / Giga | Stock Klipper+Moonraker | ✏️ |

### Proprietary LAN (vendor-specific wire)
| Family | Wire | Status |
|--------|------|--------|
| Bambu Lab (X1/P1/A1/H2D) | MQTT (TLS) + FTPS, `bblp`+access-code, LAN mode | ✏️ |
| Anycubic (Kobra series) | MQTT (TLS, slicer mTLS cert) + HTTP `:18910` identity/upload | ✏️ |
| Creality (stock OS: K1/K2/Ender-3 V3) | HTTP `:80/upload` + `ws://:9999` `{method:set/get}` + UDP-broadcast discovery | ✏️ |
| Elegoo Centauri (SDCP) | SDCP over WebSocket `:3030` + UDP discovery; CC2 over MQTT+HTTP | ✏️ |
| FlashForge (5M/AD5X/Guider) | Proprietary "FlashNetwork" SDK (topic pub/sub + check-code); legacy `:8899` raw-TCP G-code | ✏️ |

### Object-model (RepRapFirmware)
| Family | Wire | Status |
|--------|------|--------|
| Duet 3D boards / RRF | HTTP `rr_*` (standalone) or DSF REST (SBC); the RRF Object Model | ✏️ |
| SeeMeCNC (delta) | RRF over Duet, standalone `rr_*` | ✏️ |

### Host controllers (a computer in front of the printer)
| Family | Wire | Status |
|--------|------|--------|
| OctoPrint | HTTP REST + SockJS push; Application-Keys auth | ✏️ |
| PrusaLink | HTTP REST (poll-only), Digest auth | ✏️ |

### USB serial (no network)
| Family | Wire | Status |
|--------|------|--------|
| Marlin over USB | Line-based G-code over serial; `M115`/`M105`/`M27`; `ok`-gated + checksum/resend | ✏️ |

## Multi-material feeder families

See [`patterns/multi-material-feeders.md`](patterns/multi-material-feeders.md). Vendor AMS-class units (Bambu AMS,
Anycubic ACE, Elegoo CANVAS, Creality CFS, FlashForge Material Station) report per-slot state on their vendor wire;
DIY/open units (ERCF, Box Turtle, Night Owl, TradRack, 3MS, …) are driven by a **software provider** (Happy Hare, or
AFC) over Klipper/Moonraker. Retrofit combiners (CoPrint) and splicers (Palette) are near-invisible on the wire.

## Contributing coverage

The floor is laid — every family has a paper. The frontier now is **hardware validation** (promote a 🟡 source-read
paper to 🟢 with a real capture) and **new families** not yet mapped (⬜). A 🟢 capture for any 🟡 family is the
single highest-value contribution. Add a new printer via [`protocols/_TEMPLATE.md`](protocols/_TEMPLATE.md) and the
[`METHOD.md`](METHOD.md).
