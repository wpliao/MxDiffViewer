# Diff per-Element MDL rendered by mxcli

Mendix stores its model as binary BSON, so a plain Git diff is useless. We render each changed Element to MDL with mxcli (`mxcli describe`), normalise it (strip canvas coordinates, mark Layout-only changes) and diff the text per Element.

## Considered Options

- **`mxcli diff-local`**: names documents by GUID and shows coordinate noise.
- **`mx diff` / `mx dump-mpr` (Studio Pro's mx.exe)**: needs the exact Studio Pro version per commit, crashed on a real release range of an mxcli-built app, and is very verbose for microflows.
- **A whole-project MDL export**: doesn't exist, and a single dump's order varies between commits. Per-Element output is deterministic within a commit.

## Consequences

Each `describe` is a separate process call: about 0.9 s per Element on a small app and about 5 s on a large one (2,330 Elements took 25 minutes). So we only render Changed Elements (ADR-0002), cache Snapshots (ADR-0006), and accept a wait of minutes on a first run. One long-running mxcli process is a later optimisation.
