# Pattern — Discovery, LAN Mode & Credentials

Getting *connected* looks different per brand but follows a small number of shapes. Knowing them makes onboarding a new
printer predictable.

---

## 1. "LAN mode" is nearly universal

Almost every brand has a setting that **disables the vendor cloud and allows direct local-network access**. The names
differ — "LAN Only", "Developer Mode", "LAN mode", or just an access code appearing — but the posture is identical:

> **Cloud off → local access, authenticated by a per-device code.**

Don't over-read a vendor's marketing name for it. Bambu's "Developer Mode," Anycubic/Creality/Elegoo "LAN" access,
Snapmaker's auth-code pairing, FlashForge's check-code — these are the **same category**: a user toggles local access
and reads a **per-device credential** from the printer's own screen/settings. It is a normal precondition to surface in
onboarding, not a special hurdle to engineer around, and it needs **no vendor secrets** — just the user's own code.

## 2. Credentials are user secrets

The local credential (access code / auth code / check code / API key) is obtained by the **owner** from **their own
printer**. In an integration, prompt for it; never hardcode or ship one. This orchard documents *how a user gets theirs*,
never a value. A few stacks derive the working MQTT credential from the printer at connect time (via an identity
endpoint) — that's still the user's own device handing it to their own client.

Some brands add an **mTLS client cert** on top (it lives in the user's own slicer install, extracted at runtime). Same
principle: user-owned, never bundled.

## 3. Discovery: usually manual IP, sometimes a broadcast

In rough order of what you'll actually find:

- **Manual IP entry** — always works; the universal fallback. Many brands support *only* this.
- **UDP broadcast** — a vendor-specific discovery packet on the LAN; the printer replies with its IP/identity.
- **SSDP / mDNS** — some stacks (and Moonraker printers) answer standard discovery.
- **Account/cloud device list** — only in cloud mode; out of scope for LAN.

Design onboarding around **manual IP as the guaranteed path**, with auto-discovery as a nice-to-have on top.

## 4. Identity probe

Most networked printers expose a cheap **identity endpoint** (an HTTP `/info`-style GET, or a status query) that returns
model, serial, firmware, and capabilities *before* you commit to a full session. Read identity first — it lets you pick
the right dialect and validate the model before deriving credentials or connecting.

**A sleeping printer is often just silent.** Several brands' identity endpoints simply stop answering when the printer
sleeps (no error, no refusal — HTTP-silent). Treat "no answer" as *asleep/unreachable*, not as a hard failure, and
reconnect from a cached credential when it wakes.

## 5. Push vs poll (and the reconnect posture)

- **Push stacks** (MQTT / WebSocket subscriptions) deliver state changes live — subscribe and diff. Remember to
  **re-subscribe on every reconnect** (brokers don't restore subscriptions for you) and to key liveness on the
  transport connection, not a heartbeat (some printers don't send one).
- **Poll-only stacks** (HTTP REST, serial) require a periodic query; **synthesize** a change-event stream from the diffs
  (see [`../GLOSSARY.md`](../GLOSSARY.md) → *poll-synth*). Pick one definition of "elapsed"/"progress" per printer and
  keep it (see [`timing-normalization.md`](timing-normalization.md)).
- **Poll-hybrid** — a few stacks push while active but go quiet when idle, so you poll gently as a backstop and lean on
  the pushes during a print.
