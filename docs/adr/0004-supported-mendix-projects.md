# Support MPR v2 apps on Mendix 10.24 and 11.12, however they were built

v1 targets Mendix 10.24.x and 11.12.x apps in the MPR v2 format (one file per document, the default from 10.21). It must work on apps built in Studio Pro as well as apps built with mxcli, so nothing may depend on mxcli-specific conventions.

A Comparison whose Base and Target are on different Mendix versions is allowed. It raises a Dependencies & platform Risk flag ("Mendix version upgrade"), and Upgrade-only changes sit behind a filter. Refs in the old MPR v1 format are rejected with a clear error.

## Considered Options

- **Refuse cross-version Comparisons**: rejected, because upgrade releases are among the riskiest a team ships.
- **Support MPR v1 with a slow full render**: rejected. Per-file change detection (ADR-0002) doesn't work on it, and that history predates both target versions.
