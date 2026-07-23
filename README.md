# The Printer Protocol Orchard

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Prose: CC BY 4.0](https://img.shields.io/badge/prose-CC%20BY%204.0-lightgrey.svg)](LICENSING.md)
[![Docs site](https://img.shields.io/badge/docs-orchard-5c8a3f.svg)](https://chestnutlabs.github.io/printer-protocol-orchard/)
[![CI](https://github.com/ChestnutLabs/printer-protocol-orchard/actions/workflows/ci.yml/badge.svg)](https://github.com/ChestnutLabs/printer-protocol-orchard/actions/workflows/ci.yml)

**Open research and implementation guidance for the LAN control protocols of consumer 3D printers** — so anyone building an
integration (a slicer plugin, a Home Assistant component, a farm manager, a monitoring dashboard) can skip the
reverse-engineering and start from documented facts.

> Every printer brand speaks a different, poorly-documented protocol over the local network. Figuring out *how to talk
> to a Bambu / Creality / Anycubic / Elegoo / … over LAN* is the first and largest hurdle for every integration
> project — and everyone re-does it from scratch. This orchard is that research, done once, in the open.

Maintained by **[Chestnut Labs](https://github.com/ChestnutLabs)**. Born out of building a printer-management platform,
but the orchard itself is **vendor-neutral** — no product, no lock-in, just the protocol facts.

---

## What's here

| Path | What it is |
|------|-----------|
| [`QUICKSTART.md`](QUICKSTART.md) | **Build your first LAN client end-to-end** — the five-step on-ramp. Start here. |
| [`MODEL.md`](MODEL.md) | **The neutral model** every adapter maps *into* — normalized state, feeder, and job/timing shapes. |
| [`protocols/`](protocols/) | **One white paper per printer family** — transport, discovery, auth, read/state, write/control, feeders, quirks. The core reference. |
| [`patterns/`](patterns/) | **Cross-cutting design wisdom** every adapter-builder needs — timing/units traps, multi-material feeder modeling, discovery + LAN-credential patterns, and the [`connection-flows`](patterns/connection-flows.md) walk-through. The stuff that's the same across vendors. |
| [`COMPARISON.md`](COMPARISON.md) | **Cross-vendor comparison matrix** — the whole landscape in one table. |
| [`examples/`](examples/) | **Minimal reference clients**, one per protocol paradigm. |
| [`METHOD.md`](METHOD.md) | **How to research a printer you don't see here yet** — the repeatable method (mine the vendor's own open-source slicer). Teaches you to fish. |
| [`COVERAGE.md`](COVERAGE.md) | The map — which vendors use which protocol paradigm, and what's documented vs still open. |
| [`GLOSSARY.md`](GLOSSARY.md) | Shared vocabulary (MMU vs toolchanger vs IDEX, feeder classes, poll-synth, …). |
| [`CONFIDENCE.md`](CONFIDENCE.md) | The confidence grading every fact carries (source-read vs hardware-validated vs inferred). |
| [`fixtures/`](fixtures/) | **Sanitized real wire captures** — so a paper is a *testable* spec, not just prose. |
| [`schemas/`](schemas/) | *(growing)* machine-readable message/topic schemas for codegen + validation. |

## How to use it

1. Find your printer in [`protocols/`](protocols/) (or its family — many budget printers share a stack).
2. Read the **"At a glance"** block for the one-page protocol summary, then the section you need.
3. Check the **Confidence & validation** section — some facts are read from source but not yet hardware-validated
   (clearly marked). Trust accordingly.
4. If your printer isn't here, [`METHOD.md`](METHOD.md) shows how to research it — and PRs are welcome.

The orchard is also buildable as a browsable docs site (MkDocs Material) — see [`mkdocs.yml`](mkdocs.yml).

## How it's sourced (and why you can trust it)

Almost every modern printer ships a **customized slicer that is an open-source fork** (of OrcaSlicer → Bambu Studio →
PrusaSlicer, all GPL/AGPL). Their **device-connection code is the authoritative first-party client** for the vendor's
LAN protocol. This orchard extracts the **uncopyrightable interface facts** from that published code (plus sanitized
hardware captures) — clean-room, facts-only, never copied code. See [`METHOD.md`](METHOD.md) and each paper's
**Sources** section.

## What this is **not**

- **Not affiliated with or endorsed by any printer manufacturer.** All trademarks belong to their owners. See
  [`DISCLAIMER.md`](DISCLAIMER.md).
- **Not a credential store.** No certificates, keys, access codes, or secrets — the orchard documents *mechanisms*, not
  credentials. Access codes are user credentials you get from your *own* printer.
- **Not a bypass guide.** This is interoperability documentation for printers you own — not a way around cloud, DRM, or
  authentication.

## License

**MIT** (covers everything, including code/schemas/fixtures). The prose is *additionally* offered under
**CC BY 4.0** for those who prefer a content license. See [`LICENSING.md`](LICENSING.md). Short version: use it,
build on it, ship commercial things with it — just keep the attribution and don't claim vendor endorsement.

## Contributing

Corrections, new vendors, and — especially — **hardware-validated captures that close an open gap** are hugely
welcome. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) first; the one hard rule is the **clean-room / facts-only** policy
([`CLEANROOM-CHECKLIST.md`](CLEANROOM-CHECKLIST.md)) that keeps everything here freely licensable.

## Status legend

Papers and individual facts are tagged:
- 🟢 **hardware-validated** — confirmed against a real device.
- 🟡 **source-read** — read from the vendor's published slicer/SDK; wire-shape correct, not yet HW-confirmed.
- 🔵 **community/RE** — from third-party reverse-engineering; corroborate before trusting.
- ⚪ **inferred** — deduced from adjacent facts; treat as a hypothesis.
