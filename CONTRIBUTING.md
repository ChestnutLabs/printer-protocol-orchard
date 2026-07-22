# Contributing

Thank you — this orchard gets better every time someone documents a printer they own or fixes a fact. The most valuable
contributions:

- 🟢 **Hardware-validated captures** that close an open gap (a paper's "Confidence & validation" section lists what's
  still needed — a real capture is worth more than any amount of source-reading).
- **New vendors / families** not yet covered (use [`METHOD.md`](METHOD.md) to research them).
- **Corrections** — a wrong port, a changed firmware field, a better mapping.
- **Sanitized fixtures** and **schemas** that make a paper testable.

## The one hard rule: clean-room, facts-only

Everything here must stay **freely licensable** — which means it must be **your own clean-room description of
uncopyrightable facts**, never copied source. Before you open a PR, run [`CLEANROOM-CHECKLIST.md`](CLEANROOM-CHECKLIST.md).
In short:

1. **Describe facts in your own words.** Field names, ports, message shapes, state enums, command verbs — yes. Pasted
   code from a vendor's slicer/SDK — **no** (it's GPL/AGPL and would poison the license).
2. **No secrets.** Never commit a certificate, private key, access/auth/check code, provision key, or token — yours or
   anyone's. Describe how a user gets *their own*; never include a value.
3. **Sanitize captures.** IPs → `192.0.2.x` (TEST-NET), device serials/ids → placeholders, any credential → redacted,
   filenames → generic. If you can't sanitize it, don't commit it.
4. **Nominative branding only.** Name the vendor to identify the device; don't imply affiliation or use logos.

By submitting a PR you confirm your contribution is your own work and agree to license it under the repo's MIT + CC BY
4.0 terms (see [`LICENSING.md`](LICENSING.md)).

## How to add or edit a paper

1. Copy [`protocols/_TEMPLATE.md`](protocols/_TEMPLATE.md) to `protocols/<vendor>.md` (or a `protocols/<vendor>/`
   folder if it needs fixtures/schemas).
2. Fill every section; tag facts with a confidence level ([`CONFIDENCE.md`](CONFIDENCE.md)) and cite **Sources**.
3. Be honest in **Confidence & validation**: mark what's source-read vs hardware-validated, and list the open gaps.
4. Add the vendor to [`COVERAGE.md`](COVERAGE.md).
5. If you touched a shared concept, check whether it belongs in [`patterns/`](patterns/) instead of (or in addition
   to) the per-vendor paper.

## Style

- One file per printer *family* (many budget machines share a stack — group them, note the differences).
- Lead every paper with an **"At a glance"** one-page summary.
- Prefer tables for field/command/port maps.
- Quote exact wire strings in `code font`; call out the load-bearing gotcha explicitly.
- Keep it **vendor-neutral and product-neutral** — this is a reference, not a pitch for any tool.

## Governance

Maintained by Chestnut Labs. Substantive protocol claims should carry a source or a capture; "it works on mine" is a
great start but please say so (mark it 🟢 with the model + firmware version).
