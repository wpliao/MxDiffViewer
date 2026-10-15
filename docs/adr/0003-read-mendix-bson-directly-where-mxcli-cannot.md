# Read Mendix BSON directly in two narrow places

mxcli is the engine for rendering Elements, but we parse the `mprcontents/` BSON files ourselves for two things it doesn't provide:

1. **Possible rename detection.** Telling a renamed entity or attribute from a drop and re-create needs internal IDs. MDL only has names, and `mxcli bson dump` doesn't cover domain models. A Removed and Added pair is matched by ID; when matching fails, it is flagged as a Possible rename rather than guessed.
2. **The raw fallback for Opaque changes.** The Base and Target BSON are compared as JSON and only the changed paths are shown, labelled with widget names, e.g. `grid1 › columns[2] › attribute: Name → FullName`.

## Considered Options

- **Our own MDL-style renderer for older widgets**: duplicates mxcli's job. Instead we ask upstream for read-only rendering of those widgets, and the fallback gives way to it widget by widget.
- **`mx dump-mpr`** for IDs: needs a matching Studio Pro install per commit.

## Consequences

We depend on Mendix's undocumented BSON structure for domain models, which can change between Mendix versions. Keep that parsing small and covered by tests against both supported versions.
