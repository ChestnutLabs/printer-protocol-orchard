# Anycubic fixtures — provenance

Backs [`../../protocols/anycubic.md`](../../protocols/anycubic.md) (🟢 hardware-validated).

Anycubic printers speak **two closely-related dialects** that share one command set and differ only in a few report
fields (see the paper). Read-path captures are split by dialect into subfolders:

- [`avata_main/`](avata_main/) — the **avata** dialect (Kobra X, model `20030`).
- [`gkapi/`](gkapi/) — the **gkapi** dialect (Kobra 2 / 3 / S1; captures from Kobra 3, model `20024`).

Each subfolder has its own `SOURCES.md` naming the model + firmware and describing every file.

## Write path — `commands.jsonl`

`commands.jsonl` is the **control / write path**: the exact MQTT command payloads observed from a live Anycubic slicer
session driving a Kobra 3 (model `20024`, gkapi dialect). One command per line. Both dialects share this command set.

- **Sanitized:** the only device-specific value present was a user-set printer name in the `info/setPrinterName`
  command, replaced with `example-printer`. The `taskid: "-1"` values are the printer's own sentinel (act-on-current-
  job), not identifiers. No IPs, serials, tokens, or credentials appear in the command payloads.
- **Load-bearing detail** (why this fixture exists): the command's action lives in the **JSON payload**
  (`type` + `action`), never in the MQTT topic. Appending the action to the topic makes the printer silently drop the
  message while still ACKing. These lines are the known-good `{type, action, data}` shapes an implementer must
  reproduce.

All values here are **sanitized / synthetic**. Field **names and structure** are the real wire schema; only the
*values* were scrubbed.
