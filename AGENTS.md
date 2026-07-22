# AGENTS.md

Guidance for AI coding agents (and their humans) working **in** this repository. If you are
*consuming* the protocol docs to build an integration, start at
[`llms.txt`](https://github.com/ChestnutLabs/printer-protocol-orchard/blob/main/llms.txt) and the
[`protocols/`](protocols/) papers instead — this file is about *editing the orchard itself*.

## What this repo is

The Printer Protocol Orchard is **clean-room, vendor-neutral reference documentation** for the LAN
control protocols of consumer 3D printers: one white paper per printer family, cross-cutting
patterns, a comparison matrix, machine-readable JSON schemas, sanitized wire-capture fixtures, and
minimal example clients. It is **prose and data, not an application** — there is no build to compile
and no runtime to run. The "product" is correctness.

## The one hard rule: clean-room, facts-only

Everything here must stay **freely licensable**, which constrains what you may add. This is the rule
most likely to trip up an agent, so internalize it before editing:

1. **Describe facts in your own words.** Ports, field names, message shapes, state enums, command
   verbs, sequence order — all fine (uncopyrightable interface facts). **Never paste source code**
   from a vendor's slicer/SDK/firmware — those are GPL/AGPL and copying them would poison the
   license. Read the source to learn the fact, then write the fact yourself.
2. **Never commit a secret.** No certificate, private key, access/auth/check code, provision key, or
   token — yours or anyone's, real or realistic. Document *how a user obtains their own* credential;
   never include a value. This is enforced by a scanner (see Validation).
3. **Sanitize every capture.** IPs → `192.0.2.x` (TEST-NET), serials/device ids → placeholders,
   any credential → redacted, filenames → generic. If you can't sanitize it, don't commit it.
4. **Nominative branding only.** Name a vendor to identify the device; never imply affiliation or
   use logos.

Full checklist: [`CLEANROOM-CHECKLIST.md`](CLEANROOM-CHECKLIST.md). Policy rationale:
[`CONTRIBUTING.md`](CONTRIBUTING.md) and [`LICENSING.md`](LICENSING.md).

## Validation — run these before proposing changes

Three gate scripts (pure Python 3, no third-party deps) enforce the guarantees. All three must exit
`0`; CI (`.github/workflows/ci.yml`) runs the same three on every push.

```bash
python scripts/validate_schemas.py   # every schemas/**.json is valid JSON Schema; fixtures validate against their schema
python scripts/check_links.py        # relative Markdown links resolve to real files/anchors
python scripts/cleanroom_scan.py     # no secrets / credential-shaped strings slipped in
```

If any fails, **stop and fix the cause** — do not weaken a gate to make it pass. The clean-room scan
is the security boundary; treat a hit as blocking. A local research/scratch area lives under
`ProjectSource/` (git-ignored except its `README.md`, and exempted from the scanner via
`.cleanroomignore`) — that is by design; don't "fix" it.

## Docs site (optional to touch)

The prose also builds as a MkDocs Material site. `mkdocs.yml` uses `docs_dir: .` (the repo root *is*
the docs source) via the `same-dir` plugin, and the Pages workflow builds with
`mkdocs build -d <tmp>` so the output never nests inside the source. To preview locally:

```bash
pip install -r requirements-docs.txt
mkdocs build -d /tmp/orchard-site   # or: mkdocs serve
```

The build is intentionally **not `--strict`**: papers deliberately link to excluded `.json`
fixtures/schemas, and link integrity is gated by `check_links.py` instead. If you add a new
top-level Markdown page meant for humans, add it to the `nav:` in `mkdocs.yml`.

## Adding or editing a protocol paper

1. Copy [`protocols/_TEMPLATE.md`](protocols/_TEMPLATE.md) to `protocols/<vendor>.md` (or a
   `protocols/<vendor>/` folder if it needs fixtures/schemas).
2. Fill every section and **lead with an "At a glance" one-page summary**.
3. Tag facts with a confidence level ([`CONFIDENCE.md`](CONFIDENCE.md)) and cite **Sources** — which
   repo/file you read, or which capture. Be explicit in "Confidence & validation" about what is
   source-read vs hardware-validated and what gaps remain.
4. Add the vendor to [`COVERAGE.md`](COVERAGE.md) and, if relevant, the [`COMPARISON.md`](COMPARISON.md) matrix.
5. If you touched a concept shared across vendors, it probably belongs in [`patterns/`](patterns/).
6. Re-run the three gate scripts.

## Confidence grading (tag every non-obvious fact)

| Tag | Meaning | Trust |
|-----|---------|-------|
| 🟢 hardware-validated | Confirmed against a real device (note model + firmware). | Build on it. |
| 🟡 source-read | Read from the vendor's own published slicer/SDK. Wire *shape* is right, live values unconfirmed. | Validate live values before shipping writes. |
| 🔵 community / RE | Third-party reverse-engineering or community docs. | Corroborate first. |
| ⚪ inferred | Deduced from adjacent facts, not observed. | Treat as a hypothesis. |

A paper's overall tag is set by its weakest load-bearing fact. **Write/control commands deserve
extra caution** — a wrong 🟡 read is low-risk; a wrong 🟡 control command can damage hardware.

## Style

- One file per printer **family** (group machines that share a stack; note the differences).
- Prefer tables for field/command/port maps; quote exact wire strings in `code font`.
- Call out the load-bearing gotcha explicitly.
- Keep it vendor-neutral and product-neutral — a reference, not a pitch.

## What not to do

- Don't paste vendor source, ship a secret, or commit an un-sanitized capture.
- Don't silently "correct" a protocol fact you can't source — flag it for a human, and mark
  uncertainty with the right confidence tag rather than overstating.
- Don't relax or delete a validation gate to get a green check.
- Don't add affiliation claims, marketing language, or logos.
