# Reference clients

Small, illustrative reference clients — one per **protocol paradigm**, not per vendor.
Each is the shortest program that exercises the load-bearing shape of one wire protocol:
connect, authenticate, read state, and (where the paper documents it) issue one command.

They exist to make the papers concrete. They are **not** a product, not a library, and not a
control panel — read the matching paper first, then run the client against a printer to see the
same field names and message shapes on the wire.

## Safety and neutrality

These clients are for **a printer you own**, on your own LAN. Nothing is bundled: every credential
(access code, API key, password, host address) is supplied by **you** at runtime, read from an
environment variable or a CLI argument — never hard-coded, never checked in. No certificates, keys,
or secrets ship in this repo. This is documented from each vendor's own open-source slicer and
public interfaces, for local interoperability.

## The six clients

| Directory | Paradigm | Families it speaks for | Paper |
| --- | --- | --- | --- |
| [`moonraker/`](./moonraker/) | JSON-RPC + REST over HTTP/WebSocket | Klipper/Moonraker: Elegoo Neptune, Snapmaker, Qidi, Sovol, rooted Creality | [`../protocols/klipper-moonraker.md`](../protocols/klipper-moonraker.md) |
| [`duet-rrf/`](./duet-rrf/) | Object-model polling over HTTP | Duet / RepRapFirmware (standalone + SBC) | [`../protocols/duet.md`](../protocols/duet.md) |
| [`sdcp/`](./sdcp/) | JSON envelope over WebSocket | Elegoo Centauri (SDCP) | [`../protocols/elegoo.md`](../protocols/elegoo.md) |
| [`octoprint/`](./octoprint/) | Host-controller REST + push | OctoPrint host controller | [`../protocols/octoprint.md`](../protocols/octoprint.md) |
| [`prusalink/`](./prusalink/) | Host-controller REST, HTTP Digest auth | PrusaLink host controller | [`../protocols/prusalink.md`](../protocols/prusalink.md) |
| [`bambu/`](./bambu/) | MQTT over TLS on the LAN | Bambu Lab LAN mode | [`../protocols/bambu.md`](../protocols/bambu.md) |

## Why per-paradigm

Many brands collapse onto one wire. A "Klipper printer" from five different vendors is the same
Moonraker JSON-RPC surface; the vendor name changes nothing on the socket. Documenting the
**paradigm** once — and naming every family that rides it — keeps the reference honest about what is
actually distinct at the protocol level, instead of implying six vendors need six different clients.
The distinct axes are the transport and the message envelope, not the logo on the case.

## Not included here (and why)

- **Anycubic** — the LAN control path uses mutual-TLS with a client certificate that the user
  imports from their own slicer install. That setup step is larger than a minimal illustrative
  snippet should carry, so it lives in the paper rather than as a runnable client here.
- **Creality (stock LAN)** and **FlashForge** — documented in their papers. Example clients are
  welcome as contributions; see [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

## Setup

Install the third-party libraries the clients use with:

```
pip install -r requirements.txt
```

Each client's own README names the environment variables / arguments it expects at runtime.
