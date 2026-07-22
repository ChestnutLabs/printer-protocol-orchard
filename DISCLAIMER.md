# Disclaimer

## Independence & trademarks

The Printer Protocol Orchard is an **independent, community interoperability reference**. It is **not affiliated with,
authorized by, sponsored by, or endorsed by** any printer manufacturer, including (but not limited to) Anycubic, Bambu
Lab, Creality, Elegoo, Snapmaker, FlashForge, Prusa Research, Qidi, Sovol, or any other named vendor.

All product names, brand names, logos, and trademarks are the property of their respective owners. They are used here
**nominatively** — solely to identify *which* device a given document describes (e.g. "the Bambu LAN protocol"). No
affiliation or endorsement is implied.

## Purpose: interoperability, for devices you own

This material documents how consumer 3D printers communicate over a **local network**, so that owners and developers
can build **interoperable software** for **printers they own or operate**. It is:

- **not** a guide to bypassing authentication, cloud services, licensing, or DRM;
- **not** a distribution of any manufacturer's software, firmware, certificates, keys, or secrets;
- **not** an invitation to access devices you do not own or have permission to use.

Any **access code / auth code / check code** referenced is a **user credential** the owner obtains from **their own
printer's settings** — the orchard describes the mechanism, never the value.

## How the facts were obtained

Facts are extracted, clean-room, from **publicly published, open-source** vendor software (the manufacturers' own
GPL/AGPL slicer forks and SDKs) and from **sanitized captures of an owner's own device**. Only uncopyrightable
interface facts are documented; no source code is copied. See [`METHOD.md`](METHOD.md) and each paper's **Sources**
section for provenance.

## No warranty

Everything here is provided "as is," without warranty of any kind. Protocols change across firmware versions; facts
tagged 🟡 source-read or 🔵 community may be incomplete or outdated. **Verify against your own device before relying on
anything, especially for write/control operations** — you are responsible for the safety of your hardware. Sending
commands to a heater or motion system can damage equipment or cause injury; test carefully.

## Takedown / correction

If you are a rights holder and believe something here is inaccurate or oversteps nominative/interoperability use, open
an issue or contact the maintainers — we'll correct or remove it promptly.
