# Clean-Room / Pre-Publish Checklist

Run this before publishing or merging any paper. It's what keeps the whole orchard **freely licensable and legally
clean.** If a paper can't pass every gate, fix it before it goes public.

## 1. Facts-only — no copied source

- [ ] Every claim is written **in my own words**, not pasted from a vendor's slicer/SDK/app.
- [ ] No verbatim code blocks copied from a GPL/AGPL source. *(Documenting a function's name, parameters, and behavior
      is a fact; pasting its body is copying.)*
- [ ] Struct/field/enum **names and shapes** are described (fine); their **implementation** is not reproduced.
- [ ] Where a wire example is shown, it's a **captured message** (sanitized, §3) or a **synthetic example I authored**,
      not lifted from vendor source.

> Rule of thumb: *interfaces and facts, yes; expression and implementation, no.* If you're unsure whether a passage is
> "fact" or "copied expression," rewrite it in your own words — that resolves it.

## 2. No secrets or credentials

- [ ] No certificates (`.crt`/`.pem`/`.cer`), private keys (`.key`), PKCS#12 (`.p12`), or key material of any kind.
- [ ] No access codes, auth codes, check codes, PINs, tokens, session ids, or passwords — mine or anyone's.
- [ ] No provisioning keys / API secrets, **even if they appear in a vendor's public repo** (public ≠ yours to
      republish, and they enable impersonation).
- [ ] Credentials are described as a **mechanism** ("the access code is in Settings → Network"), never as a value.
- [ ] `.gitignore` excludes `*.crt *.key *.pem *.p12` and any `secrets`/`captures-raw` dirs.

## 3. Sanitized captures & fixtures

- [ ] Private IPs → `192.0.2.x` (TEST-NET-1); public IPs removed.
- [ ] Device serial numbers / ids / MACs / USNs → placeholders (`SN-EXAMPLE`, `deviceid-0001`).
- [ ] Any credential-shaped field → `[redacted]`.
- [ ] Filenames / project names → generic (`example.gcode.3mf`).
- [ ] Topic strings sanitized (they often embed the device id).
- [ ] A one-line note records the model + firmware version the capture came from.

## 4. Trademarks & framing

- [ ] Vendor/product names used **nominatively** (to identify the device), never implying affiliation/endorsement.
- [ ] No vendor logos or brand assets committed.
- [ ] Framing is **interoperability for a device you own** — not "bypass the cloud / defeat auth / crack DRM."
- [ ] The repo-level [`DISCLAIMER.md`](DISCLAIMER.md) is present and current.

## 5. Provenance & honesty

- [ ] The paper's **Sources** section cites where each fact came from (which repo/file, or a capture).
- [ ] Facts are **confidence-tagged** ([`CONFIDENCE.md`](CONFIDENCE.md)); nothing source-only is presented as
      hardware-proven.
- [ ] The **Confidence & validation** section honestly lists open gaps + what capture would close them.
- [ ] Licensing: contribution is the author's own work, offered under the repo's MIT + CC BY 4.0.

---

**If all five sections pass, it's clean to publish.** When in doubt on §1 or §4, the safe move is: rewrite in your own
words, drop the questionable asset, and keep the framing neutral.
