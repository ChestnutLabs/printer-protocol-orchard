<!-- Thanks for contributing to the Printer Protocol Orchard. Keep it facts-only, sanitized, and neutral. -->

## Summary

<!-- What does this PR change and why? One or two sentences. -->

## Paper(s) / family touched

<!-- e.g. protocols/bambu.md · patterns/multi-material-feeders.md -->

## Clean-room checklist

Every gate from [`CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md) must pass before this can merge:

- [ ] **Facts-only / no copied source** — every claim is in my own words; no verbatim code pasted from a vendor slicer/SDK/app. Interface names and shapes described, implementations not reproduced.
- [ ] **No secrets** — no certificates, keys, access/auth/check codes, tokens, PINs, or passwords (even ones found in a public vendor repo). Credentials described as a mechanism, never as a value.
- [ ] **Sanitized captures** — IPs → `192.0.2.x`; serials/ids/MACs → `SN-EXAMPLE` / `deviceid-0001`; credential-shaped fields → `[redacted]`; filenames → `example.gcode`; topic strings carrying a device id use a placeholder.
- [ ] **Nominative branding** — vendor/product names used only to identify the device; no logos/brand assets; framing is interoperability for a device you own, not "bypass / defeat / crack."
- [ ] **Provenance + confidence tags** — Sources section cites where each fact came from; facts carry confidence tags (🟢/🟡/🔵/⚪) and nothing source-only is presented as hardware-proven.

## Confidence

<!-- What confidence level do the new/changed facts carry, and what capture would raise it? -->
Confidence: <!-- 🟢 hardware-validated · 🟡 source-read · 🔵 community/RE · ⚪ inferred -->

## Licensing (DCO)

- [ ] This contribution is my own work, and I offer it under the repository's **MIT + CC BY 4.0** licenses.
