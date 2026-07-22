# Moonraker / Klipper — reference client example

> **Reference example — facts-only, no warranty.** Illustrative integrator code for the
> Printer Protocol Orchard. It connects to **your own** printer using credentials **you**
> supply at runtime; nothing is bundled. Clean-room, vendor-neutral. MIT-licensed.
>
> **Confidence:** 🟡 source-read — matches the protocol paper
> [`../../protocols/klipper-moonraker.md`](../../protocols/klipper-moonraker.md).

## What it demonstrates

The **Moonraker paradigm**: a JSON-RPC 2.0 API served over **HTTP + WebSocket** on
port **`7125`**, fronting Klipper. [`client.py`](client.py) shows the three moves an
integrator needs:

1. **Identity / liveness** — `GET /printer/info` (answers only when Klippy is connected).
2. **Read state** — one-shot `GET /printer/objects/query?print_stats&heater_bed&extruder&toolhead&virtual_sdcard`,
   then the live path: open `ws://<host>:7125/websocket`, call JSON-RPC
   `printer.objects.subscribe` (params `objects` → a `{name: null}` map for all fields);
   the reply **is** the full initial snapshot, and `notify_status_update` notifications
   then carry **sparse deltas** (`[ {obj: {changed fields}}, eventtime ]`) you deep-merge.
3. **Upload + launch** (guarded behind `--print`) — multipart
   `POST /server/files/upload` (file field `file`), with `print=true` to start after
   upload. Equivalently, upload with `print=false` then
   `POST /printer/print/start?filename=<name>`.

> ⚠️ There is **no fixed schema** — a printer exposes only the objects its config
> defines. Enumerate `printer.objects.list` and treat a missing object as *not capable*,
> never an error. And `virtual_sdcard.progress` is **file-byte position, not time** — do
> not derive an ETA from it.

## Families covered

Any Moonraker host speaks this protocol, including:

- Generic upstream **Klipper + Moonraker** (Voron, RatRig / RatOS, VzBot, **Sovol SV08**) — the reference tier.
- **Elegoo Neptune 4 / 4 Pro / 4 Plus / 4 Max** — pinned-old Moonraker; feature-detect.
- **Snapmaker U1** — behind its `:8100` auth-wrapper bootstrap (see `../../protocols/snapmaker.md`).
- **Qidi** (Q1 Pro / Plus4 / X-Plus 3 / X-Max 3) — pinned-old Moonraker; feature-detect.
- **Rooted / stock Creality** (K1 family; K2 family on **`:4408`**) — may use a
  non-standard port and permission-locked paths.

Not covered: the Elegoo **Centauri Carbon** is Klipper-*marketed* but speaks a
proprietary SDCP protocol — no Moonraker. Route it elsewhere.

## Requirements

Python 3.9+ and only the libraries the paths you use need:

```
pip install requests            # HTTP: info, query, upload, print start
pip install websocket-client    # only if you use --watch (WebSocket subscribe)
```

## Configuration (env / args — never hardcoded)

| Variable | Required | Meaning |
|----------|----------|---------|
| `MOONRAKER_HOST` | yes | Printer host, e.g. `192.0.2.10`, or `host:port` if the port isn't 7125 (e.g. `192.0.2.10:4408`). |
| `MOONRAKER_API_KEY` | no | Usually **unset** on a trusted LAN (Moonraker's `trusted_clients` bypasses auth). If your host requires a key, this becomes the `X-Api-Key` header. |

**Where to find the API key (a mechanism, not a value):** on **your** Moonraker host —
in the web UI (Mainsail / Fluidd) settings, or the API-key file in Moonraker's data
directory. This example never ships or embeds one; you provide your own at runtime.

## Running

```sh
# info + one-shot state snapshot
MOONRAKER_HOST=192.0.2.10 python client.py

# live subscription: prints the initial snapshot, then a few sparse deltas
MOONRAKER_HOST=192.0.2.10 python client.py --watch

# upload a file and START the print — drives a hot, moving machine; explicit opt-in
MOONRAKER_HOST=192.0.2.10 python client.py --print example.gcode
```

Run with no `MOONRAKER_HOST` to print usage. IPs above use the `192.0.2.0/24`
documentation range (RFC 5737); substitute your printer's real address.

> ⚠️ Control writes (`--print`) move a hot machine. Test against hardware you own and
> understand, and gate writes behind an explicit "enable" in any real client.

## See also

- Protocol paper: [`../../protocols/klipper-moonraker.md`](../../protocols/klipper-moonraker.md)
- Discovery & credentials pattern: [`../../patterns/discovery-and-credentials.md`](../../patterns/discovery-and-credentials.md)
- Timing normalization (the file-byte / seconds traps): [`../../patterns/timing-normalization.md`](../../patterns/timing-normalization.md)
