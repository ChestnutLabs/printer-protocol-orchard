# ProjectSource — local research & scratch area

This folder is a **local-only workspace** for the work that goes *into* the Orchard but should never
land *in* the published repo: raw captures, vendor-slicer clones, experiments, throwaway scripts,
working notes, and half-finished drafts.

**Its contents are git-ignored.** Only this README is tracked (via a negation rule in
[`../.gitignore`](../.gitignore)), so the convention survives a fresh clone. Everything else you put
here stays on your machine.

The clean-room scanner ([`../scripts/cleanroom_scan.py`](../scripts/cleanroom_scan.py)) also **skips
this folder** (see [`../.cleanroomignore`](../.cleanroomignore)) — so your un-sanitized research
captures won't trip the gate while they're still raw.

## What belongs here

- Raw, **un-sanitized** wire captures (real IPs, serials, access codes) *before* you scrub them.
- Local clones of vendors' open-source slicers/SDKs you're reading for facts.
- Experiments, spikes, one-off analysis scripts, scratch data.
- Personal notes, TODOs, and drafts not ready to publish.

## What does NOT belong here

Anything meant to be **published** goes in the real repo tree, not here:

- A finished protocol write-up → `protocols/<vendor>.md`
- A **sanitized** capture → `fixtures/<vendor>/…` (scrub it first — see
  [`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md) §3)
- A machine-readable spec → `schemas/<vendor>/…`
- A reference client → `examples/<paradigm>/…`

## The one rule when promoting work out of here

Everything that graduates from `ProjectSource/` into the tracked tree must pass the
[clean-room checklist](../CLEANROOM-CHECKLIST.md): facts in your own words, **no secrets**, captures
sanitized (IPs → `192.0.2.x`, serials/access-codes → placeholders). This folder is where the raw
material lives; the repo is where only the clean, publishable facts land.
