# Bambu Lab LAN reference client (example)

A minimal, dependency-light example of the **Bambu Lab "MQTT over TLS, LAN
mode"** paradigm: connect to a printer **you own** on your **own network**,
subscribe to its report topic, request a full status push, and print the first
report. This is illustrative starter code for interoperability, not a product.

- **Paradigm / full paper:** [`../../protocols/bambu.md`](../../protocols/bambu.md)
- **Confidence:** 🟢 hardware-validated (A1 Mini; X1/P1/H2 specifics 🟡 source-read)
- **License:** MIT · facts-only, no warranty

## Families covered

Bambu Lab **X1 / P1 / A1 / P2 / X2 / H2** families. They share one LAN control
transport: **MQTT over TLS on `:8883`**. (Bambu also exposes an implicit-TLS
FTPS file channel on `:990` used to upload a `.3mf` before a print — that
transport is described in the paper but intentionally **not** exercised by this
read-only example.)

## What it demonstrates

1. TLS connect to `<host>:8883` (self-signed LAN device — see the pinning note).
2. MQTT auth: user `bblp`, password = the printer's **access code**.
3. Subscribe to `device/<serial>/report`.
4. Publish `{"pushing":{"command":"pushall"}}` to `device/<serial>/request` to
   force a full status snapshot.
5. Print the first report and disconnect.

It does **not** upload files or start a print — those would move a hot machine.

## Requirements

- Python 3.9+
- [`paho-mqtt`](https://pypi.org/project/paho-mqtt/) — the only dependency:
  ```
  pip install paho-mqtt
  ```

## Credentials — where you find them (mechanism, not values)

You supply three things about **your own** printer at runtime; nothing is
hardcoded:

| Value | What it is | Where you get it |
|---|---|---|
| **host** | the printer's LAN IP | your router / the printer's Network screen |
| **serial** | the printer serial | printer **Settings → Device** (used as the MQTT topic key; **case-sensitive**) |
| **access code** | the LAN access code | enable **LAN mode** in the printer UI; the code is shown on the printer's own screen |

The access code is your own secret, read from the machine's screen — this
example only reads it from the environment/args you provide, never a stored
value.

## Running it

Via environment variables (IP shown is RFC 5737 documentation space — use your
own):

```
BAMBU_HOST=192.0.2.10 \
BAMBU_SERIAL=SN-EXAMPLE \
BAMBU_ACCESS_CODE=your-access-code \
python client.py
```

Or as positional args:

```
python client.py 192.0.2.10 SN-EXAMPLE your-access-code
```

Missing host/serial/access code prints usage and exits.

## Gotchas reflected in the code

- **Serial is case-sensitive** — a miscased serial connects fine but returns
  **zero reports** (the canonical silent failure).
- **Self-signed TLS** — this example uses verify-off for brevity. **Production
  must pin the certificate on first use** (trust-on-first-use) or verify against
  Bambu's device-CA with SNI = serial. The code comments call this out. This is
  standard self-signed-LAN handling, not a security bypass.
- **Fresh `client_id` per connect** and a **raised inflight ceiling** — reused
  ids leave zombie sessions; paho's default ceiling wedges the session after a
  handful of commands.
- **Status times are in MINUTES** (e.g. `mc_remaining_time`) — a cross-brand
  unit trap.
- **No command ack** — Bambu confirms writes only via the status stream; this
  read-only example just prints the first snapshot.

See [`../../protocols/bambu.md`](../../protocols/bambu.md) for the full
protocol, the FTPS upload dialect, and the `project_file` print-launch fields.
