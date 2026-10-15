# The Release report is one self-contained HTML file plus JSON

A Release report is a single HTML file containing the Approver summary, the Tester view and the full Explorer, with the Base and Target of every Changed Element embedded. It can be emailed or attached to a ticket and opened without the tool. The same data is written as JSON for pipelines.

- **Risk flags** use fixed default Severities: Security, Data and Published APIs are High; Configuration, Dependencies & platform and Navigation are Medium; Logic & UI and Custom code are Info. Team overrides come later.
- **Impact** is one hop of "used by" from `mxcli impact` in v1. Full multi-hop analysis is the goal. Whether `mxcli impact` catches indirect use, such as pages reached through data-source microflows, is still unverified.
- **Git context** is the commit list with authors, plus ticket IDs extracted with a configurable pattern. There's no per-Element blame.
