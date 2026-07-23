---
template: home.html
hide:
  - navigation
  - toc
---

# The Printer Protocol Orchard

**Open, vendor-neutral, clean-room research on the LAN control protocols of consumer 3D printers** — so anyone building
an integration (a slicer plugin, a Home Assistant component, a farm manager, a monitoring dashboard) can skip the
reverse-engineering and start from documented facts. MIT (code) + CC BY 4.0 (prose).

<div class="grid cards" markdown>

-   __Protocols__

    ---

    One white paper per printer family — transport, discovery, auth, state, control, feeders, quirks. The core reference.

    [Browse the papers →](protocols/README.md)

-   __Comparison matrix__

    ---

    The whole landscape in one flat table — eyeball how any two protocols differ, column by column.

    [Open the matrix →](COMPARISON.md)

-   __Coverage map__

    ---

    Which families use which paradigm, and what's documented vs still open. Learn a stack once, cover a cluster.

    [See coverage →](COVERAGE.md)

-   __Cross-cutting patterns__

    ---

    The traps that bite every adapter — time/unit normalization, multi-material feeders, discovery, launch flows.

    [Read the patterns →](patterns/README.md)

-   __Research method__

    ---

    How to document a printer that isn't here yet — mine the vendor's own open-source slicer fork. Teaches you to fish.

    [Learn the method →](METHOD.md)

-   __Working with AI?__

    ---

    A machine-readable index and agent guide map the orchard for AI coding assistants and their sessions.

    [Read the agent guide →](AGENTS.md)

</div>

## Start here

1. Find your printer in **[Protocols](protocols/README.md)** (or its family — many budget printers share a stack).
2. Read the **"At a glance"** block for the one-page summary, then the section you need.
3. Check **[Confidence & validation](CONFIDENCE.md)** — some facts are read from source but not yet hardware-validated,
   and are clearly marked. Trust accordingly.
4. Not listed? **[METHOD.md](METHOD.md)** shows how to research it — and PRs are welcome.

!!! note "How it's sourced (and why you can trust it)"
    Almost every modern printer ships a customized **open-source slicer fork** (of OrcaSlicer → Bambu Studio →
    PrusaSlicer). Its device-connection code is the authoritative first-party client for the vendor's LAN protocol.
    The orchard extracts the **uncopyrightable interface facts** from that published code plus sanitized hardware
    captures — clean-room, facts-only, never copied code. See [METHOD.md](METHOD.md) and each paper's **Sources**.
