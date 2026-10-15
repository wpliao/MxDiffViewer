# TypeScript CLI and local web UI on one core library

MxDiffViewer is TypeScript throughout: a Node core library that runs the Comparison, a command-line tool on top of it (`mxdiff report <base> <target>`, `mxdiff serve`), and a React UI with Monaco for the side-by-side view. The same UI code produces the interactive `serve` app and the self-contained Release report.

It ships as an npm package (`mxdiffviewer`, command `mxdiff`). Standalone executables come later, if people without Node need to generate reports. Windows and Linux are tested in CI; macOS is best effort.

## Considered Options

- **A Go core**, the same language as mxcli: rejected for v1 to keep one language across core and UI. Revisit if performance or mxcli integration needs it.
- **Hosted or CI-first**: later. A local tool proves the core first.

## Consequences

"Mx" in the name could suggest an official Mendix product. We accepted that; if it becomes a problem, rename before wide adoption.
