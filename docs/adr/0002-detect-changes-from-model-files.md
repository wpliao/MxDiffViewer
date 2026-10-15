# Detect Changes from model files, never from MDL alone

A Change is detected when an Element's file under `mprcontents/` differs between Base and Target, not when its MDL differs. Only those Elements are then rendered. No Change is ever silently dropped: if mxcli can't render the Element, or renders identical MDL for a changed file, it is reported as an Opaque change, shown through the raw fallback (ADR-0003) and counted as "not fully reviewed" in the Approver summary.

This matters because mxcli prints older widgets (Data Grid, Table, Reference Selector, File Manager and others) as a one-line placeholder with no contents. On a real Studio Pro-built app, 35% of pages, snippets and layouts contained one, so a modified Data Grid column would otherwise look like no change at all. That is the worst failure for release control.

## Consequences

Detection depends on the MPR v2 layout (one file per document), which is why MPR v1 is out of scope (ADR-0004). It also makes rendering incremental, which keeps Comparisons on large apps to minutes.
