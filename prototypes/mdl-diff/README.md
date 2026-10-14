# PROTOTYPE: per-document MDL diff (throwaway)

**Question:** Is a per-document, normalised mxcli MDL diff between two Git revisions of a Mendix project readable and useful for release review?

**Verdict: yes.** Use it as the core of the visual diff. Its gaps are listed under "What it doesn't give you" below.

Run on 2026-10-14 against a private Mendix 11.12.4 sample app (MPR v2, 9 modules, about 415 describable documents, 109 commits) with mxcli v0.26.0 and Studio Pro 11.12.4 `mx.exe`. The sample app and the generated reports are not in this repo.

## How it works

1. `export.py <repo> <rev> <outdir>` creates a git worktree for the revision and reads the document list from `mxcli project-tree`. It then runs `mxcli describe <type> <name>` for every describable document, 8 in parallel, and writes one `.mdl` file per document as `<type>/<Module.Name>.mdl`.
2. `diff.py <old> <new> <report.html>` normalises each document by dropping layout annotations: `@position`, `@curve`, `@merge`, `@anchor`, `@start`, and the position/size of `@annotation`. It then diffs per document and writes an HTML report grouped by module and type.

## Findings

| Test | Result |
| --- | --- |
| Same revision exported twice, with a fresh `.mxcli` cache | Byte-identical for all 415 documents. Output is deterministic within a revision. |
| One microflow bug fix | 1 document, +2 −1 lines after normalisation. `mxcli diff-local` showed the same change as about 25 lines, mostly coordinate shifts, and labelled the document by GUID. |
| One page styling fix | 1 document, +4 −1. Readable. |
| Domain model: 5 associations added | 5 added `association` documents. |
| Release range (Phase 5–7) | 23 added documents, 0 noise. |
| Release range (Phase 8–11) | 21 added, 6 modified, 0 noise. It surfaced a navigation rework, new DTO attributes, an extended microflow, and a **security change** (an extra module role granted `execute` on a microflow) as one readable `grant` line. |

- **Cost:** about 85–135 s per revision for a full export, at about 0.9 s per `mxcli describe` call (each call reloads the project). The batch mode (`mxcli -c "describe …; …"`) uses MDL grammar, which differs from the CLI type names, and one parse error aborts the whole batch. The real tool should export only the documents whose `mprcontents/` files changed (this is how `diff-local` finds them) and cache exports per commit SHA.
- **Coverage:** `pagetemplate` documents aren't describable (46 in the sample). `System.VerifyPassword` (a Java action) fails to describe. Everything else rendered.
- **Ordering noise:** the cross-revision ordering problem flagged in the research doesn't appear when you export per document, because each file is diffed on its own. The subclass-ordering bug wasn't exercised: the sample app has no sibling subclasses.
- **Security is readable:** entity access rules and microflow/page access appear as `grant` lines inside each document, and user roles, module roles, demo users and project security have their own documents. A release report can pull these out by parsing `grant` lines.
- **`mxcli diff-local --ref A..B`:** fast (about 3 s) but not usable as-is. It shows coordinate noise, labels documents by GUID instead of qualified name, and only does unified text.
- **`mx diff` (Studio Pro 11.12.4):**
  - It is structural JSON per unit. Each change has `change` (Added/Modified), a `changeDescription`, property-level `baseValue`/`mineValue`, and an `onlyVisualChanges` flag.
  - It is verbose and hard to read for microflows: a one-line fix produced about 15 KB, mostly re-pointed sequence flows.
  - On the Phase 8–11 range it **crashed**: `Objects with ID … of type DomainModels$AccessRule do not have the same properties`. This is likely because mxcli-authored access rules lack properties that later ones have. Treat `mx diff` as optional and unreliable on mxcli-built apps.
  - It is still the candidate for per-property facts such as attribute type changes.
- **Windows long paths:** cloning the sample app failed until `core.longpaths=true` was set, because of `node_modules` under `javascriptsource/`. Worktree paths should be short.

## What it doesn't give you

- **Rename versus drop and re-create** for entities and attributes, which is the data-loss risk. MDL prints no storage GUIDs, so this needs `mx dump-mpr` or the unit files.
- **Risk classification.** The diff shows *what* changed. The release report still has to classify changes: security, domain model or data, published APIs, navigation, and so on.
- **Non-model changes:** `javasource/`, `javascriptsource/`, `theme/` and `userlib/` are plain files, so a normal git diff covers them.
