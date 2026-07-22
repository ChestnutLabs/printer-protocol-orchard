# Fixtures — sanitized real captures

Real (scrubbed) wire captures turn a paper from *prose* into a **testable spec**: an implementer can diff their parser
against a known-good message, and a maintainer can regression-test a protocol.

## Layout

Group by family: `fixtures/<vendor>/<what>.json` (or `.jsonl` for a stream). Suggested kinds:
- `info.json` — an identity/`/info` response.
- `status-*.json` — status/telemetry reports (idle, printing, paused, error).
- `report-*.json` — push messages (per report type).
- `commands.jsonl` — captured control commands (the write path), one per line.
- `feeder-*.json` — multi-material state.

Each fixture (or a sibling `SOURCES.md`) should note the **model + firmware version** it came from.

## ⚠️ Sanitization is mandatory

Never commit a raw capture. Before adding a fixture, scrub it (and confirm [`../CLEANROOM-CHECKLIST.md`](../CLEANROOM-CHECKLIST.md) §3):

| Real value | Replace with |
|------------|--------------|
| Private IPs | `192.0.2.x` (TEST-NET-1) |
| Public IPs | remove |
| Serial / device id / MAC / USN | `SN-EXAMPLE`, `deviceid-0001` |
| Access/auth/check code, token, key, PEM | `[redacted]` |
| Filenames / project names | `example.gcode.3mf` |
| Topic strings (they embed the device id) | sanitize too |

Keep the **structure and field names intact** — those are the point. Only the *values* get scrubbed.

## No secrets, ever

If a message contains a credential you can't scrub without destroying its meaning, **don't commit it** — describe it in
the paper instead. There are zero certs/keys/codes in this repo by policy.
