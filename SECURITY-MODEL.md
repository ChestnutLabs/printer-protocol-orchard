# Security Model — for integrators

Guidance for anyone **building a client** against these protocols. It is the threat model and the handling rules the
papers imply, collected in one place.

> Reporting a vulnerability in this repo? That's [`SECURITY.md`](SECURITY.md). **This** page is about writing a *safe
> integration* against consumer-printer LAN protocols — a different concern.

---

## The threat model in one paragraph

Consumer 3D-printer LAN protocols were designed for a **trusted home LAN**, not a hostile network. Most are
**unauthenticated or weakly authenticated**, several **disable TLS verification by design**, and a few will **crash the
print daemon on a malformed command**. Control writes drive a **hot, moving machine**. Treat every printer as an
appliance on an untrusted segment, treat every write as dangerous, and treat the network path as your responsibility,
not the protocol's.

## 1. Authentication is thin — assume LAN-trust

Several stacks have **no auth on the control channel** (Creality stock `ws://:9999`, Elegoo SDCP, Moonraker with
`trusted_clients`, Marlin over USB where *physical access is the authorization*). Where auth exists it's a **per-device
code the user reads from their own printer** (Bambu access code, FlashForge `checkCode`, Elegoo CC2), a machine password
(Duet), or an API key (OctoPrint, Moonraker).

- **Never hardcode or ship a credential.** The orchard documents *how a user obtains their own*; it never contains a
  value. Do the same: read credentials from the environment or a secrets store, never from source or logs.
- **Anycubic's mTLS client cert lives in the user's own slicer install.** An integration extracts it from *their*
  machine; it is never bundled.
- Because LAN control is often unauthenticated, **anyone on the same network segment can drive the printer.** That is a
  network-segmentation problem for the operator to own (see §4).

## 2. TLS is frequently verify-off — know what you're giving up

Bambu and Anycubic present **self-signed / expired certs** and the working clients connect with verification **off**
(`CERT_NONE`, hostname check off, lowered OpenSSL security level for Anycubic's legacy ciphers). That is the documented
reality of the wire — but understand the tradeoff:

- Verify-off means **no protection against a man-in-the-middle** on the LAN path. It is acceptable only on a trusted
  segment.
- Prefer the **stronger option where the paper documents one** — Bambu supports proper verification against its
  published device-CA with `SNI = serial`, or pin-the-leaf-on-first-use. Offer verify-off as the *fallback*, not the
  default, and make the downgrade visible to the user.

## 3. Writes are dangerous — gate them, and confirm by state

- **Gate every control write behind an explicit "enable writes"** in your client. A `🟡` *read* fact is low-risk; a
  `🟡` *control* fact can damage hardware.
- **A malformed command can crash the printer.** Elegoo SDCP will crash the daemon (and kill an active print) on an
  unrecognized *or incomplete* start command. Send only commands you've validated against the catalog.
- **An ACK is not proof of effect.** Anycubic ACKs a command whose action was silently dropped; most families give no
  meaningful ack at all. Confirm every write by the **status-stream transition**, not the command response (see
  [`faults-and-errors.md`](patterns/faults-and-errors.md)).
- **Emergency stop must use the structured path**, never a queued `M112` that sits behind the g-code buffer (Klipper
  `printer.emergency_stop`, Marlin's emergency parser). Getting this wrong means your "stop" doesn't.

## 4. Network posture — the operator's half

- **Do not expose a printer to the WAN.** These protocols assume a LAN; port-forwarding one to the internet exposes an
  unauthenticated (or verify-off) control surface to everyone.
- Put printers on a **segmented / VLAN'd network** away from untrusted devices, and reach them through a client you
  control rather than the vendor cloud where LAN mode suffices.
- **Never place credentials in URLs or query strings**, and never log an access code, session key, or API key.

## 5. Privacy & data

- Captures and fixtures must be **sanitized** before they leave a machine — IPs → `192.0.2.x` (TEST-NET), serials/device
  ids → placeholders, any credential → redacted. See the [clean-room checklist](CLEANROOM-CHECKLIST.md) and
  [`fixtures/README.md`](fixtures/README.md).
- A printer's identity fields (serial, device id) are **device-identifying** — treat them as sensitive in telemetry.

---

*This is interoperability guidance for printers you own and operate — not a guide to bypassing cloud, DRM, or
authentication. See the [`DISCLAIMER.md`](DISCLAIMER.md).*
