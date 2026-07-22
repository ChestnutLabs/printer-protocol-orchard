# Schemas — machine-readable protocol specs *(growing)*

Beyond prose, structured specs make a protocol usable by **code**: validate a captured message, generate parser stubs,
or diff two firmware versions. This directory is optional and grows as papers mature — a paper is useful without a
schema, but a schema makes it *testable end-to-end*.

## Index

Each file carries a `_meta` block (kind, confidence, and the paper/section it derives from).

| Vendor | Schema | Kind |
|--------|--------|------|
| **Anycubic** | [`anycubic/state-enum.json`](anycubic/state-enum.json), [`topic-grammar.json`](anycubic/topic-grammar.json), [`command-catalog.json`](anycubic/command-catalog.json) | state-enum · topic grammar · command catalog |
| **Bambu** | [`bambu/state-enum.json`](bambu/state-enum.json) | state-enum |
| **Elegoo SDCP** (CC1) | [`elegoo/sdcp-envelope.json`](elegoo/sdcp-envelope.json), [`sdcp-cmd-catalog.json`](elegoo/sdcp-cmd-catalog.json), [`sdcp-state-enum.json`](elegoo/sdcp-state-enum.json) | envelope + topics · `Cmd`/ack/error catalog · the two status enums (machine + job) |
| **Duet / RRF** | [`duet/state-status-enum.json`](duet/state-status-enum.json), [`job-and-timing.json`](duet/job-and-timing.json), [`tools-model.json`](duet/tools-model.json), [`gcode-intent-map.json`](duet/gcode-intent-map.json) | state-enum · job/progress/units · `tools[]` toolchanger · intent→GCode map |
| **Klipper** | [`klipper/state-enum.json`](klipper/state-enum.json) | state-enum |

## What can live here

- **Message / envelope schemas** — JSON Schema for a report or command payload.
- **Topic / URL grammars** — the address structure as data (segments, allowed values).
- **State-enum tables** — native → normalized mappings as JSON, so consumers don't hand-copy them.
- **Command catalogs** — the verb set with parameters and channels.

## Layout

`schemas/<vendor>/<what>.schema.json` (JSON Schema, draft 2020-12 preferred), or `schemas/<vendor>/<what>.json` for
plain data tables. Keep them **paired with the paper** and confidence-tagged in a header comment — a schema is only as
trustworthy as the capture behind it.

## Rules

- **Facts only** — a schema describes the wire shape; it must not embed vendor code or any secret/example credential.
- **Sanitized examples** — if a schema carries an `examples:` block, scrub it like a fixture
  ([`../fixtures/README.md`](../fixtures/README.md)).
- **Version it** — note the model + firmware the schema was derived from; protocols drift.
