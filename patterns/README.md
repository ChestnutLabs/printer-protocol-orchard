# Patterns — cross-cutting design wisdom

The per-vendor papers tell you *what a printer says*. These tell you *how to model it well* — the concerns that are the
same across every brand, and the traps that cost everyone the same days. Read these once and you'll write better
adapters for printers that aren't even in the orchard yet.

| Pattern | The gist |
|---------|----------|
| [`timing-normalization.md`](timing-normalization.md) | **The units/timing traps.** Time is minutes on some brands, seconds on others, milliseconds ("ticks") on a third — and *progress is time-based on some, file-byte-position on others*. Get this wrong and an 11-minute print shows 112 hours. |
| [`multi-material-feeders.md`](multi-material-feeders.md) | **Modeling multi-material.** One neutral feeder shape that covers vendor AMS units *and* DIY MMUs — with the "capability provider vs hardware implementation" split (detect Happy Hare / AFC, not each ERCF/Box-Turtle model). |
| [`discovery-and-credentials.md`](discovery-and-credentials.md) | **Getting connected.** "LAN mode" is nearly universal (cloud-off + a per-device code); discovery is usually manual-IP; the credential is a *user* secret. The shared onboarding shape. |
| [`connection-flows.md`](connection-flows.md) | **Connect → launch sequences.** The `connect → read → upload → LAUNCH → confirm` flow per family, as diagrams — why `upload != launch`, and why you confirm by the status stream rather than a command ack. |
| [`faults-and-errors.md`](faults-and-errors.md) | **Faults, errors & recovery.** Where each family carries faults, the "looks-like-a-fault-but-isn't" filters, structured emergency-stop, and a neutral fault surface — because a failed job can read as plain idle. |

These are written **vendor-neutral** — no product, no framework. If you're building an integration, they're free
design guidance; if you're documenting a new printer, they tell you which fields to capture and why.
