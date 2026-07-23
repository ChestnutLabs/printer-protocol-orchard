# Changelog

All notable changes to the Printer Protocol Orchard are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-07-23

Resource depth + a designed docs site.

### Added

- **Neutral model** (`MODEL.md`) + machine-readable schemas (`schemas/normalized/` —
  lifecycle-state, feeder-model, job-model): the canonical state / feeder / job-timing
  shape every adapter maps *into*, reconciling the per-vendor mappings.
- **Faults, errors & recovery pattern** (`patterns/faults-and-errors.md`) — cross-vendor
  fault channels, "looks-like-a-fault-but-isn't" filters, structured emergency-stop.
- **State-enum schemas** for Creality, OctoPrint, PrusaLink, and Snapmaker (FlashForge and
  Marlin intentionally omitted — no faithfully-extractable native enum).
- **Machine-readable comparison matrix** (`data/comparison.json`).
- **Quickstart** (`QUICKSTART.md`) and **integrator security model** (`SECURITY-MODEL.md`).
- **`llms.txt`** index and **`AGENTS.md`** guide for AI consumers and coding agents.
- **Orchard theme** for the docs site (a custom Material for MkDocs theme), plus README badges.

### Changed

- **MkDocs rendering pass** — repaired tables and lists that python-markdown flattened to
  paragraphs, made heading anchors GitHub-compatible, and de-densified two dense mappings
  into tables (no technical content changed).
- CI actions bumped to the Node 24 runtime.

## [0.1.0] - 2026-07-22

First public cut of the Orchard.

### Added

- **11 protocol papers** covering consumer 3D-printer LAN control, each with
  per-fact confidence tags: Anycubic and Bambu hardware-validated (🟢), the
  remaining nine (Klipper/Moonraker, Elegoo, OctoPrint, Duet/RepRapFirmware,
  Creality, Snapmaker, FlashForge, Marlin USB-serial, and PrusaLink)
  source-read (🟡).
- **Cross-cutting patterns set** distilling behavior common to many families:
  poll/timing cadence, multi-material feeder models, discovery and credential
  mechanisms, and connection/handshake flows.
- **COVERAGE and COMPARISON maps** — a matrix of which families are documented
  to what depth, and a side-by-side of transports, discovery methods, and
  control verbs across vendors.
- **Sanitized fixtures** for Anycubic, Bambu, and Klipper — example wire
  payloads with all IPs, serials, IDs, filenames, and credentials replaced by
  RFC 5737 / placeholder values.
- **Machine-readable schemas** for the Anycubic, Bambu, Elegoo SDCP, Duet, and
  Klipper/Moonraker message shapes.
- **Per-paradigm example clients** — minimal reference clients illustrating each
  transport paradigm, reading any required credential from a user-supplied
  environment variable or CLI argument at runtime.
- **Clean-room CI gate** (`scripts/cleanroom_scan.py`) enforcing the no-secrets
  and sanitization rules on every change.
- **Documentation site** presenting the papers, patterns, and maps.

[Unreleased]: https://github.com/ChestnutLabs/printer-protocol-orchard/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ChestnutLabs/printer-protocol-orchard/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ChestnutLabs/printer-protocol-orchard/releases/tag/v0.1.0
