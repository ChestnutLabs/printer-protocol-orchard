# Licensing

**TL;DR — everything here is MIT-licensed; the prose is additionally offered under CC BY 4.0. Use it freely, keep the
attribution, don't claim vendor endorsement.**

## The dual offer

- **Code, schemas, fixtures, and scripts** → **MIT** (see [`LICENSE`](LICENSE)).
- **Documentation / prose** → **MIT and/or [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**, your choice.
  MIT works fine for prose; CC BY 4.0 is offered because it's the "native" instrument for written content and some
  reusers (wikis, docs sites) prefer it. Either way: use it, adapt it, ship commercial things with it — just credit
  "The Printer Protocol Orchard by Chestnut Labs" with a link.

Both are permissive on purpose. The goal is **maximum reach** — anyone leaps past the research hurdle. A copyleft doc
license would work against that.

## Why this is ours to license (and what we *don't* license)

We can only license **our own expression** of the facts — the prose, tables, diagrams, schemas, and organization in
this repo. Two things make that clean:

1. **The facts themselves are not copyrightable.** Protocol interface facts — ports, field names, message shapes,
   state enums, command verbs — are uncopyrightable across virtually every jurisdiction. Documenting them is free.
   Our *write-up* of them is our copyrightable work, which we license to you above.
2. **We never copy code.** Every paper is written from scratch as a clean-room description (see
   [`CLEANROOM-CHECKLIST.md`](CLEANROOM-CHECKLIST.md)). No source was pasted from any vendor's (GPL/AGPL) slicer, so
   nothing here inherits a copyleft obligation.

**What we do NOT and cannot license to you:**

- **The protocols themselves.** We describe them; we don't own them. Your right to *implement* an interoperable client
  comes from interoperability law + the facts being uncopyrightable, not from this license.
- **Vendor trademarks.** Brand and product names are used nominatively (to say *which* printer a paper describes) only.
  See [`DISCLAIMER.md`](DISCLAIMER.md).
- **Any credentials or secrets.** There are none here by policy — no certs, keys, access codes, or provision secrets.
  We describe the *mechanism* by which a user obtains their own device's credential; we never ship one.

## For contributors

By contributing you agree your contribution is your own clean-room work and is licensed under the same MIT + CC BY 4.0
terms. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

*This file explains the licensing rationale; it is not legal advice. If you are redistributing this material as part
of a commercial product, or you're unsure about trademark/nominative use in your context, consult your own counsel.*
