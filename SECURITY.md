# Security Policy

The Printer Protocol Orchard is a **documentation repository**. It contains no
running network service and no printer firmware. As a result, "security" here
means something narrower than in a typical software project, and this policy is
tailored to the two things that can actually go wrong in a reference of this
kind.

## What counts as a security issue here

1. **A leaked secret accidentally committed.** The house rule of this repo is
   that it contains **no secrets, ever** — no certificates, private keys, access
   codes, provision keys, auth/check codes, tokens, passwords, or real device
   serials/IDs, and not even realistic-looking placeholders for them. If you
   spot any such value in the tree, in the git history, or in an example
   fixture, please report it **privately** (see below). We will treat it as an
   incident: remove the content, **scrub the git history** (history rewrite +
   force-push), and, where a real credential was exposed, note that the affected
   party should rotate it on their own device.

2. **A factual error that could mislead an integrator.** A wrong port number,
   an inverted enum, a mislabeled field, or a command described with the wrong
   effect can cause someone to send the wrong bytes to hardware they own. We
   treat materially misleading protocol facts as a correctness-and-safety issue.
   These can be reported publicly as a normal issue **unless** the correction
   itself would require disclosing a secret — in that case, report it privately.

## What is NOT in scope

This repository is **not a vulnerability database for the printers themselves.**
It documents interoperability facts (ports, field names, message shapes, command
verbs) for machines their owners already control on their own LAN. If you have
discovered a vulnerability in a printer's **firmware, cloud service, or vendor
app**, that is a matter for the **vendor's** own security/disclosure process,
not this repo. Please report it to the manufacturer directly. We do not
coordinate, host, or publish printer firmware exploits.

## How to report privately

For anything in category (1) — or a category (2) issue that cannot be described
without a secret — please use a **private** channel rather than opening a public
issue or pull request:

* **Preferred:** GitHub's private reporting — the **"Report a vulnerability"**
  button under the repository's **Security** tab (GitHub Security Advisories).
  This keeps the report confidential until a fix is published.
* **Alternative:** email the security contact at
  `security@chestnutlabs — see repo profile` (maintainer will publish the exact
  address on the organization profile).

Please include enough to locate the problem: the file path (and commit or line,
if known), what the exposed value or incorrect fact is, and — for a leaked
secret — do **not** paste the secret itself if it can be avoided; point to where
it lives so we can remove it.

## First line of defense: the clean-room scanner

Before anything reaches a human reviewer, every change is checked by the
automated clean-room / secret scanner at `scripts/cleanroom_scan.py`, which runs
in CI as a required gate. It flags likely credential shapes, non-sanitized IP
addresses (anything outside the `192.0.2.0/24` TEST-NET-1 range used for
examples), and other patterns that violate the repo's no-secrets and
sanitization rules. Contributors are encouraged to run it locally before opening
a pull request. The scanner is a safety net, not a substitute for care — the
authoring rules in `CONTRIBUTING.md` are what keep the corpus clean-room.

## Our commitment

We will acknowledge a private report promptly, keep it confidential while we work
the fix, credit reporters who want credit, and — for leaked-secret reports —
prioritize history scrubbing over everything else. Thank you for helping keep
this reference safe and accurate.
