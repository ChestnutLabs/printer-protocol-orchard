# Changelog

All notable changes to the Printer Protocol Orchard are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-22

First public cut of the Orchard.

### Added

- **11 protocol papers** covering consumer 3D-printer LAN control, each with
  per-fact confidence tags: Anycubic and Bambu hardware-validated (🟢), the
  remaining nine (Klipper/Moonraker, Elegoo, OctoPrint, Duet/RepRapFirmware,
  Creality, Snapmaker, FlashForge, Marlin USB-serial, and the shared
  multi-material feeder family) source-read (🟡).
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

[Unreleased]: https://github.com/ChestnutLabs/printer-protocol-orchard/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ChestnutLabs/printer-protocol-orchard/releases/tag/v0.1.0
