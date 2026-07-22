# Confidence Grading

Every non-obvious fact in a paper should carry a confidence tag, so readers know how far to trust it. Protocols change
across firmware; a field read from a slicer's source is *probably* right but not *proven* until someone watches a real
device do it.

| Tag | Meaning | Trust |
|-----|---------|-------|
| 🟢 **hardware-validated** | Confirmed against a real device (a capture, a working client, or a bench test). Note the model + firmware version. | High — build on it. |
| 🟡 **source-read** | Read from the vendor's own published slicer/SDK source. The wire *shape* is first-party-correct, but no one has confirmed the live values/behavior on hardware. | Good — the structure is right; validate live values before shipping writes. |
| 🔵 **community / RE** | From third-party reverse-engineering or community docs, not the vendor's own source. | Corroborate before relying. |
| ⚪ **inferred** | Deduced from adjacent facts, not directly observed. A hypothesis. | Treat as a guess; flag hard. |

## Conventions

- **Tag the paper overall** in its header (its weakest load-bearing fact sets the ceiling), *and* tag individual
  facts inline where they differ.
- **Cite the source** next to the fact or in the paper's **Sources** section (which repo/file, or which capture).
- **Be honest about gaps.** The "Confidence & validation" section lists what's *not* yet confirmed and what capture
  would close it — that's an invitation for a hardware-owner to contribute, not an admission of weakness.
- **Write operations deserve extra caution.** A 🟡 read fact is low-risk; a 🟡 *control* command can damage hardware.
  Say so.
