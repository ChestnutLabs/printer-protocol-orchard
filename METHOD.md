# The Method — how to research a printer that isn't here yet

The single most reusable thing in this orchard isn't any one protocol — it's the **repeatable method** for finding a
vendor's LAN protocol without guessing. If your printer isn't documented, this is how you document it (and then, ideally,
send a PR).

---

## The core insight

**Almost every modern FDM printer ships a customized slicer that is a fork of an open-source slicer** — OrcaSlicer,
which forks Bambu Studio, which forks PrusaSlicer/Slic3r. Because those upstreams are **GPL/AGPL**, the vendor forks are
almost always **open source too**. And a slicer that can "send to printer" over the network **contains the vendor's own
first-party LAN client**.

So the authoritative description of *how to talk to a printer over LAN* is usually sitting in the vendor's own published
slicer repo — better than community reverse-engineering, and legally clean (you read published code for its
uncopyrightable interface facts; you never copy it).

The three places the protocol lives:
1. **Device-connection C++** — `src/slic3r/GUI/<Vendor>/…`, `SendToPrinter`, `DeviceManager`, `print_manage/`,
   `mqtt_client`, the `send_gcode`/`send_print` bridges.
2. **A committed device bundle** — a webview/UI bundle under `resources/web/…` (the actual wire logic often lives here,
   minified).
3. **A separate first-party SDK** — sometimes the slicer just depends on a vendor SDK library (cleaner than the slicer).

---

## The steps

### 1. Find the vendor's slicer repo
Search GitHub for `<Vendor>Official/<Vendor>Print`, `<vendor>-slicer`, `<Vendor>/OrcaSlicer`, or an `OrcaSlicer` fork
under the vendor's org. Also check for a separate SDK repo (e.g. a `<vendor>-link`).

### 2. Clone it LOCALLY and grep — do **not** rely on GitHub code search
This is the load-bearing tip. **GitHub code search cannot index minified/compiled bundles** (`resources/web/*.js`, a
compiled-Dart `main.dart.js`, a wasm blob) — and the actual wire protocol frequently lives exactly there. What's
invisible to code search is trivial to `grep` on a local clone.

```bash
# sparse, blobless clone keeps it fast:
git clone --depth 1 --filter=blob:none --sparse <REPO_URL> vendor-slicer
cd vendor-slicer
git sparse-checkout set src/slic3r/GUI src/slic3r/Utils resources/web doc docs
```

### 3. Locate the device code (it isn't in the same place for every vendor)
```bash
git ls-tree -r --name-only HEAD | grep -iE 'GUI/[A-Z][a-z]+/|print_manage|SendToPrinter|device|resources/web|deps/.*link'
```
The device layer's **format varies by vendor** — expect one of:
- a **Vue/JS webview** bundle (`resources/web/<panel>/assets/*.js`),
- a **compiled Flutter** app (`resources/web/flutter_web/main.dart.js`),
- a **separate C++ SDK** dependency (no web bundle at all),
- a **closed DLL** loaded at runtime (only the header/interface is in the repo — you get the *surface*, not the wire).

### 4. Grep for the protocol tells
```bash
# in source dirs:
grep -rhoiE 'wss?://|https?://|mqtt|:[0-9]{4,5}|/upload|/server/files|printer\.(objects|print)|jsonrpc|sdcp|access_code|check_?code|discover|broadcast' src resources 2>/dev/null | sort | uniq -c | sort -rn

# in a minified/compiled bundle (streams the blob so no full checkout needed):
git cat-file blob HEAD:resources/web/<path>/main.dart.js | grep -oaiE '(wss?|https?|mqtt)://[^" )]{2,60}' | sort -u
```
You're hunting for: URL schemes + **ports**, discovery (mDNS/SSDP/UDP broadcast), the **upload** endpoint, the
**print-start** verb, the message **envelope** shape, the **state enum**, the **command vocabulary**, and the **error
catalog**. Quote the exact strings you find.

### 5. Screen by G-code flavor first
The vendor's machine profiles (`resources/profiles/<Vendor>/machine/*.json`) carry `gcode_flavor` and start-gcode.
That's a fast paradigm classifier before you read a line of device code:
- `klipper` + `PRINT_START`/`SET_*` macros → it's **Moonraker/Klipper** underneath; look for `/server/…` and
  `printer.objects` (often you're 80% done — it's the common stack).
- `reprapfirmware` / `host_type: duet` → **RRF Object Model** (`rr_*` / DSF).
- `marlin` + bare `G28`/`M104` → **Marlin over serial** (no network of its own).
- a **proprietary SDK dep or DLL** → a genuine net-new vendor protocol.

---

## The sibling method — firmware, for the parts a slicer doesn't own

A slicer knows *assignment* (tool offsets, the color→slot map, print modes) but not the *mechanism* (dock/undock,
carriage modes, load/unload macros). For those, the authoritative first-party source is the **firmware's config schema
/ object model**, read the same clone-and-grep way:
- **Klipper** — the config reference + the module source (`[dual_carriage]` for IDEX, community `[toolchanger]`/KTC,
  MMU drivers like Happy Hare / AFC).
- **RepRapFirmware** — the Object Model dictionary (`tools[]`, `move.axes`, `job.timesLeft`).
- **Marlin** — `Configuration.h` / `Configuration_adv.h` (`DUAL_X_CARRIAGE`, `M605`, `TOOLCHANGE_*`).

---

## Clean-room discipline (non-negotiable)

- Extract **facts** — endpoints, ports, field names, message shapes, state enums, command verbs. **Never copy code.**
- A **built/minified bundle is a shipped artifact**; reading its embedded string constants for interface facts is
  documentation, not decompilation of copyrighted logic.
- **Never publish secrets** — certs, keys, access/provision codes. Where a vendor bundles a credential (some do, even in
  public repos), that's a *documented fact that it exists*, never a value to reuse.
- See [`CLEANROOM-CHECKLIST.md`](CLEANROOM-CHECKLIST.md) before publishing.

## Framing (matters, and it's the honest one)

Frame the work — in notes, prompts, and the paper — as **neutral interoperability documentation**: reading published
vendor code to build a compatible LAN client for a printer the owner controls. Adversarial "reverse-engineer / bypass
the proprietary protocol" phrasing is both inaccurate (you're reading *published open source*) and needlessly
antagonistic. The high ground is real here — stay on it.
