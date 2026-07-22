# SDCP reference client (Elegoo Centauri Carbon 1)

A tiny, dependency-light example of the **SDCP** paradigm: a nested JSON envelope over a plain
WebSocket on port **3030**, correlated by an echoed **`RequestID`** (not JSON-RPC). It discovers the
printer, opens the socket, sends `Cmd 0` (status), matches the reply by `RequestID`, and prints the
live state.

> **Reference example — facts-only, no warranty.** Interoperability with a printer **you own**, on
> your own LAN. Supply your own host; SDCP has no credential to supply.

## What it demonstrates

- **UDP discovery** — broadcasts the 6-byte probe `M99999` to `:3000`; each board replies with a JSON
  datagram carrying `MachineName`, `MainboardIP`, and the stable **`MainboardID`**.
- **The nested envelope** — `{"Id", "Topic": "sdcp/request/<MainboardID>", "Data": {"Cmd", "Data",
  "RequestID", "MainboardID", "TimeStamp", "From"}}`.
- **Correlation by `RequestID`** — a client-generated hex string echoed on the reply; unsolicited status
  pushes for other requests are skipped.
- **Reading state** — `Cmd 0` forces a status refresh (reply on `sdcp/status/<MainboardID>`).

Write commands (`128` start, `129` pause, `130` stop, `131` resume) are **intentionally not sent**: on
SDCP an unrecognized or **incomplete** command can crash the printer daemon and kill an active print.
This example stays read-only. See the paper's **Quirks & gotchas** and the launch sequence before
emitting any write.

## Families covered

- **Elegoo Centauri Carbon 1** (SDCP over `ws://<host>:3030/websocket`).

Not covered (different stacks, different examples): Elegoo **Neptune 4 / OrangeStorm Giga** use plain
**Moonraker JSON-RPC on `:7125`**; **Centauri Carbon 2 / 2 Combo** use a **proprietary MQTT** broker on
`:1883` with an access-code credential.

## Requirements

```
pip install websocket-client
```

Only `websocket-client` is used (plus the Python 3.9+ standard library). It is imported lazily, so
running with no arguments to discover printers works even before you install it.

## Credentials

**None.** SDCP has no authentication — no handshake, no password, no token (LAN-trust). The only inputs
are the printer **host** and its **MainboardID**, both of which discovery returns. Keep such a client
LAN-only and do not expose it to the cloud.

## Environment variables / arguments

| Input | Env var | Positional arg | Meaning |
|-------|---------|----------------|---------|
| Host | `SDCP_HOST` | `argv[1]` | Printer IP / hostname (the `MainboardIP` from discovery) |
| Mainboard ID | `SDCP_MAINBOARD_ID` | `argv[2]` | The `MainboardID` from discovery — the topic routing key |

Run with **no** arguments to broadcast a discovery probe and list the printers (with their MainboardIDs)
it finds, then re-run with those values.

## Run

Discover first:

```
python client.py
```

Then read status (env or positional):

```
SDCP_HOST=192.0.2.10 SDCP_MAINBOARD_ID=deviceid-0001 python client.py
python client.py 192.0.2.10 deviceid-0001
```

(`192.0.2.10` is a documentation placeholder — RFC 5737 TEST-NET-1. Use your printer's real LAN IP.)

## Gotchas this example encodes

- **`RequestID`, not JSON-RPC `id`** — SDCP frames carry no `jsonrpc`/`method`/`id`; correlate on the
  echoed `Data.RequestID`.
- **A wrong `MainboardID` is a silent no-op** — you address topics the printer never touches; no error.
- **`TimeStamp` is Unix milliseconds**, while the print `CurrentTicks`/`TotalTicks` in the status body
  are **seconds** — two units on the same frame. Don't cross-scale them.
- **Connection limits** — the printer allows ~5 concurrent WS connections (a 6th → HTTP 500) and closes
  idle sockets after ~60 s; a real client keeps one long-lived socket warm with a periodic `Cmd 0`.

## Confidence

🟡 source-read (Elegoo's first-party LAN SDK + the cbd-tech SDCP v3.0 spec) · the SDCP path is
🔵 community firmware-validated (Centauri Carbon ~1.1.x).

## See also

- Protocol paper: [`../../protocols/elegoo.md`](../../protocols/elegoo.md)
- Envelope schema: [`../../schemas/elegoo/sdcp-envelope.json`](../../schemas/elegoo/sdcp-envelope.json)
