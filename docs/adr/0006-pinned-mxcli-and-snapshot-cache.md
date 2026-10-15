# Pin the mxcli version and key the Snapshot cache on it

MxDiffViewer pins one mxcli version, downloads it automatically on first use, and lets the user override it with a specific binary. Snapshots are cached per commit SHA and mxcli version, because MDL output changes between mxcli releases: Snapshots rendered by different mxcli versions would produce false Changes.

## Consequences

Upgrading the pinned mxcli is a deliberate MxDiffViewer release and invalidates the cache.
