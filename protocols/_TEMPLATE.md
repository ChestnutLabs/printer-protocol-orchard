<!-- Copy this to protocols/<vendor>.md and fill every section. Delete these HTML comments.
     Keep it vendor-neutral and product-neutral: this is a reference, not a pitch for any tool.
     Tag facts with confidence (see ../CONFIDENCE.md); cite Sources; run ../CLEANROOM-CHECKLIST.md before publishing. -->

# <Vendor / Family> — LAN Protocol

> **Status:** 🟡 source-read _(or 🟢 hardware-validated / 🔵 community)_ · **Firmware:** <e.g. Klipper, proprietary> ·
> **Models:** <the family this covers>
>
> One or two sentences: what this printer speaks over LAN, and the one thing to know.

## At a glance

<!-- The whole protocol on one screen. A reader should be able to start from just this block. -->

- **Transport:** <e.g. MQTT over TLS `:8883` + FTPS `:990`  /  HTTP + WebSocket `:7125`>
- **Discovery:** <mDNS / SSDP / UDP broadcast / manual-IP only>
- **Auth / credential:** <access code, API key, none — and how the user obtains it>
- **Read / status:** <push (subscribe) or poll; the key status fields>
- **File transfer:** <HTTP multipart / FTPS / SD; endpoint>
- **Print launch:** <the start command/sequence>
- **Feeders / multi-material:** <feeder type, or "none">
- **⚠️ The load-bearing gotcha:** <the one thing that silently breaks an implementation>

## Transport & connection

<!-- Ports, TLS posture, the message envelope/frame shape, topic/URL grammar, correlation, reconnect. Quote exact
     wire strings in `code`. -->

## Discovery & identity

<!-- How a client finds the printer + reads its identity (model, serial, capabilities). Include the identity payload
     shape if there's an info endpoint. -->

## Credentials / auth

<!-- The auth model and how the *user* obtains their own credential (never a value). LAN-mode toggle if relevant. -->

## Reading state

<!-- Status/telemetry: the report shape, the printer-state enum (native → normalized), temperatures, and
     progress + TIMING UNITS (minutes? seconds? ms/ticks? and is progress time-based or file-byte-position?).
     See ../patterns/timing-normalization.md. -->

## Writing / control

<!-- Command vocabulary (pause/resume/stop, temps, fans, light, motion, e-stop), the print-launch sequence
     (upload → verify → start), and file-transfer specifics. Mark write ops with extra caution. -->

## Multi-material / feeders

<!-- Omit if none. The feeder type, per-slot fields, and the print-time color→slot map.
     See ../patterns/multi-material-feeders.md. -->

## Quirks & gotchas

<!-- Per-model differences, firmware-version drift, sentinel values, the mistakes that cost hours. -->

## Confidence & validation

<!-- Be honest. What is hardware-validated (model + firmware) vs source-read only. List the OPEN gaps and the exact
     capture that would close each — this is where hardware-owners can contribute. -->

## Sources

<!-- Clean-room provenance: which repo(s)/file(s) the facts came from, which sanitized captures, which community docs.
     Confirm ../CLEANROOM-CHECKLIST.md passed. -->
