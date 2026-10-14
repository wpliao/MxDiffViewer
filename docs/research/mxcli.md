# mxcli research for MxDiffViewer

Researched 2026-10-14 against `mendixlabs/mxcli` at commit `b655f1c9` (the `main` HEAD on 2026-10-14; the latest tagged release is v0.26.0 from 2026-10-11). Line links point at that commit. "Inference" means I reasoned it from the code without running it. "**Unverified**" means I found no primary source.

## Summary

- **No whole-project export command exists.** The nearest is `mxcli describe module <M> --all`, run once per module, plus separate `describe` calls for the project-level documents (settings, security, user roles, navigation, demo users). Some document types are never rendered: SOAP web services, page templates and XML schemas get at most a `-- not describable` line [M1][M2][M3].
- **Output is not byte-for-byte deterministic across revisions:**
  - Documents of the same type come out in SQLite row order, because the query has no `ORDER BY` [D1][D2].
  - Sibling sub-entities are ordered by Go map iteration, so their order is random [D3].
  - Canvas coordinates are printed: `@Position` on every entity, and `@position` on authored microflow layout [D4][D5].
  - GUIDs are not printed [D6].
  - MxDiffViewer has to put documents in canonical order itself and remove or ignore coordinates.
- **`mxcli diff-local --ref a..b` compares two git revisions, but only partly:**
  - It needs MPR v2 (Mendix 10.18+) [F1].
  - It shows real MDL for only nine unit types. Every other type is reduced to a placeholder line, so changes inside it are invisible [F2].
  - It has no JSON output [F3].
  - It is not a full release diff.
- **Mendix 10 is claimed but only partly validated:**
  - The README claims Studio Pro 8–11 [V1].
  - The same README says it was "developed and tested against Mendix 11.6, other versions are currently not validated" [V2].
  - The nightly CI does run integration tests against 10.24.24 and five 11.x versions [V3].
- **SonarQube path:**
  - `mxcli lint --format sarif` emits SARIF 2.1.0. Each result's `artifactLocation.uri` is `Module.Document` and carries no `region` [L1]. That uri is not a file path SonarQube can resolve, so MxDiffViewer must rewrite the report.
  - Generic test execution needs `<testExecutions>` XML. mxcli only writes JUnit XML [T1], and SonarQube's generic path does not read JUnit [S6].
  - Branch and PR analysis needs Developer Edition or higher, or a paid Cloud plan [S8][S9].
- **Maturity:** Apache-2.0, alpha, "largely vibe-engineered with AI". It warns that it "can corrupt your Mendix project files" [V2]. It releases about once a week, with 25 releases in 7 months [R1].

## 1. Coverage

**Per-document `describe`.** `mxcli describe <type> <Module.Name>` supports these types [M4]:

- Domain model: module, entity, external entity, association, enumeration, constant.
- Logic: microflow, nanoflow, rule, workflow, Java action, JavaScript action.
- UI: page, snippet, layout, building block (read-only), menu, navigation, image collection.
- Integration: JSON structure, import mapping, export mapping, consumed and published REST services, consumed and published OData services, business event service, database connection.
- Agent editor documents.
- Other: task queue, scheduled event, regular expression.
- Project level: module role, user role, app security, settings, demo user.
- Diagrams: `systemoverview` and `domainmodel`.

What is missing or degraded:

- **No describe handler for consumed or published SOAP web services, or for page templates** (I grepped the handler list and the executor) [M4].
- XML schemas and message definitions appear only inside module-all output.
- An import or export mapping whose source is a web service prints `-- SOURCE NOT REPRESENTABLE` [M5].
- Known describe omissions:
  - Role-based widget visibility (#1460) and conditional visibility on layout-grid rows and columns (#1461) [I1][I2].
  - The columns of a legacy DataGrid, which are printed as one opaque line (#1459) [I3].
  - A combobox's association attribute (#1236) [I4].
  - Export levels of protected modules (#1498) [I5].
  - A change to any of these properties will not show in an MDL-text diff.

**What entity describe prints.** Attributes and their types, `not null`/`unique` with error messages, calculated and default values, indexes, event handlers, regex and range validation rules, and access-rule `grant` statements [M6]. Microflow and page describe also print their `grant execute` / `grant view` lines [M7][M8].

**Whole-project export.**

- No single command exists. `mxcli describe module M --all` is the same as `DESCRIBE MODULE M WITH ALL` [M1]. It emits every describable document in the module, in a fixed order of types [M2].
- Undescribable units are listed as `-- not describable: <Kind> M.Name`. Failures are listed as `-- describe failed:` comments [M3].
- To cover a whole project, loop over `list modules` and add the project-level `describe` calls.
- The proposal doc mentions `mxcli export --format mdl`, but that is a draft idea. No such command exists in the code [M9].
- The catalog's `CATALOG.SOURCE` table holds MDL for only 11 document types, so it is not a full export either [M10].

## 2. Determinism

| Factor | Finding |
|---|---|
| Order of document types | Fixed by the module-all registry [M2]. |
| Order of documents within a type | Comes from the backend listing, which is `SELECT ... FROM Unit` with no `ORDER BY`, in both v2 [D1] and v1 [D2]. That order is SQLite row order, not alphabetical. Inference: it can differ between two revisions of the same model. |
| Entity order | Topologically sorted by generalization. `childrenOf` is built by `range parentOf` over a **Go map** [D3]. If a parent has two or more subclasses in the module, their order is random from run to run. This is a real non-determinism bug. |
| GUIDs / `$ID` | Not printed. The CHANGELOG says "the reader never surfaces a GUID" [D6]. |
| Coordinates | Entity describe always prints `@Position(x, y)` [D4]. Microflow and nanoflow describe print `@position`/`@anchor`/`@curve` only for "authored" layout, meaning layout the engine would not derive itself [D5][D7]. Flows drawn in Studio Pro will mostly keep their coordinates. No flag turns this off. |
| Timestamps | None seen in describe output. **Unverified** for every document type. |
| Translations | Serializers sort translation-map iteration [D8]. The page-title map-order bug was fixed in #1262 [D9]. |
| Canonical form | ADR-0010 gives one canonical form: describe omits defaults and derived layout (R9, R12) [D7]. `mdl 1` is frozen as a contract [D10]. |

**Recommendation:** split the output per document (one file per qualified name), sort by name, and remove the `@position`/`@anchor`/`@curve` lines or normalise them into a separate "layout changed" signal. Then diff.

## 3. Performance

- **Catalog cache.** The catalog is SQLite at `<project dir>/.mxcli/catalog.db` [P1]. It is valid only if the `.mpr` path matches and the `.mpr` mtime matches to the second [P1].
  - The maintainers accept mtime-only staleness as a known limit (#658) [I6].
  - Inference: when MxDiffViewer switches revisions in one working copy, it should delete the cache or use a separate worktree for each revision.
  - The cache file is also written into the project folder.
- **Measured figures, all from the CHANGELOG:**
  - Catalog build for a stock 11.12 app: 0.5 s [P2].
  - TestApp lint, which always builds the full catalog: 2.3 s rising to 3.1 s [P3].
  - `report` on a project with 3,259 microflows: from more than 40 minutes down to about 5 s after a fix [P4].
  - `refresh catalog source`: from about 6 hours down to minutes. A project with 993 microflows took about 3.5 min [P5].
  - A 53 s rule lookup on a 140 MB v1 app was fixed [P6].
  - There are **no published timings for whole-project describe** (**unverified**).
- Each CLI invocation reopens the project. Batch the statements in one process, with `-c "stmt; stmt"` [P7] or `mxcli exec script.mdl`.

## 4. Versions

- The README claims Studio Pro 8.x–11.x and MPR v1 and v2 [V1]. The same README says only 11.6 is tested [V2].
- CI: the nightly integration tests run against 10.24.24, 11.6.8, 11.12.2, 11.13.0, 11.14.0 and 11.15.0 [V3]. Mendix 9.24 is kept outside the blocking matrix because of "known writer bugs" [V4].
- The feature registry `sdk/versions/mendix-10.yaml` declares `supported_range: "10.0.0..10.24.99"` [V5]. Features are gated by version: for example, view entities need 10.18 or later.
- MPR v1 is used before 10.18 and v2 from 10.18 [G2]. Reading handles both formats. `diff-local` and `git note` need v2 [F1].
- Open issues on Mendix 10: `mxcli new --version 10.24.0` makes a project that cannot build (#1433) [I7]. Data grid 2 written by mxcli fails CE0463 on 10.x (#1424) [I8]. Both are write-path issues.
- No issue reports a read or describe failure that is specific to 10.x (**unverified** in practice).

## 5. Output formats

| Command | Formats |
|---|---|
| `describe` | `mdl` (default, starts with `mdl 1;` header), `json`, `mermaid`, `elk`, `svg` (domain model only) [O1]. **`json` is only an envelope `{"name","type","mdl"}` around the MDL text, not structured data** [O2]. |
| `diff-local` | `unified`, `side`, `struct`. `--json` is refused [F3]. |
| `diff` (script preview) | `unified`, `side`, `struct` [F3]. |
| `lint`, `check` | `text`, `json`, `sarif` [O1]. |
| `report` | `markdown`, `json`, `html` [O1]. |
| `test` | console output, plus `--junit <file>` [T2]. |
| `search` | `table`, `names`, `--json` [O1]. |

## 6. lint / report / test

**lint**

- Rules come in two kinds:
  - Built-in Go rules. The README says 14, but the code returns at least 22 distinct IDs as string literals [L2][L3].
  - Starlark `.star` rules, each with `RULE_ID`, `SEVERITY`, `CATEGORY` and a `check()` that returns `violation(...)` [L4]. They are loaded only from `.claude/lint-rules/` (#1242) [I9].
- Lint builds a full catalog every time [P3].
- In the SARIF output [L1]:
  - `uri` = `Module.Document`, with no `region`.
  - `rules[]` has only `id` and `shortDescription`, with no `defaultConfiguration.level`.
  - `level` maps error→`error`, warning→`warning`, info and hint→`note`.
  - The driver version is hard-coded to `0.1.0`.
- `Location` has `DocumentID` (a UUID) and `DocumentType`, but SARIF does not use them [L5].

**report**

- Each category score is `max(0, 100 − 10·errors − 3·warnings − 1·infos)` [R2].
- The overall score is a weighted average: Security 0.25, Quality 0.20, Architecture and Performance 0.15 each, Naming and Design 0.10 each, Other 0.05 [R3].
- Scores are absolute penalties and are **not normalised by project size**. The JSON `total` field counts violations, despite its "elements checked" comment [R2].
- JSON fields: `projectName`, `date`, `overallScore`, `categories[]{name,score,total,errors,warnings,infos,topActions}`, `summary` [R4].

**test**

- Test files: `.test.mdl` (MDL blocks with `@test`/`@expect` annotations) or `.test.md` (Markdown with `mdl-test` blocks) [T2].
- It **needs a running Mendix runtime**: Docker by default, or `--local` with mxcli's own runtime on PostgreSQL or `--db-type hsqldb`. MxBuild and JDK 21 are downloaded automatically [T2][T3].
- It **modifies the project**: it injects `MxTest.Test_*` microflows and changes the after-startup setting, then restores them [T2]. Run it on a copy.
- Tests in subfolders are ignored (#1363) [I10].
- The JUnit output is `<testsuites><testsuite><testcase name classname file time>` with `failure`/`error`/`skipped` [T1].

## 7. Diff

- `mxcli diff -p app.mpr script.mdl` previews what an MDL **script** would change. It does not compare revisions [F3].
- `mxcli diff-local -p app.mpr --ref main..feature` (or working tree vs a ref):
  - It is v2 only [F1].
  - It runs `git diff --name-status <ref> -- mprcontents` and then `git show <rev>:<path>` for each changed unit [F4]. No `Dir` is set, so mxcli must run with its working directory inside the repo (inference).
  - It ends with "Summary: N new, M modified, D deleted" [F5].
- **Limits of diff-local:**
  - `bsonToMDL` renders real MDL only for DomainModel, Entity, Nanoflow, Microflow, Enumeration, Page, Snippet, Layout and Module. Every other type becomes `-- Type: X`, so its changes are not visible [F2].
  - Types are matched with `strings.Contains` (inference: `Microflows$Rule` would match "Microflow", and `Security$ModuleSecurity` would match "Module").
  - The domain-model renderer here is simplified, and names are resolved against the opened working-tree project, not the revision (from reading the code). It is not the same as `describe`.
- **Git integration:**
  - `mxcli git note` computes Studio Pro's per-commit metadata note (v2 only) [F6].
  - **No textconv or diff driver is shipped.** It appears only in a draft proposal [M9].

## 8. SonarQube (docs.sonarsource.com, Server 2026.5 unless noted)

**SARIF import (`sonar.sarifReportPaths`)**

- Available in Server [S1], Community Build [S2], Cloud [S3] and in 9.8/9.9 [S4].
- The report must be SARIF 2.1.0. If a mandatory field is missing, the whole report is ignored [S1].
- Every issue gets the SECURITY quality and the CONVENTIONAL attribute [S1].
- Severity:
  - In MQR mode, `results[].level` is ignored and severity comes from `rules[].defaultConfiguration.level` [S1].
  - Cloud ignores `level` too [S3].
  - mxcli does not emit `defaultConfiguration` [L1], so mxcli severities would be lost and default to MEDIUM.
- In 9.9, `physicalLocation.region.startLine` was mandatory [S4].

**Generic issue import (`sonar.externalIssuesReportPaths`)**

- JSON with `rules[]` (`id`, `name`, `description`, `engineId`, plus `impacts` or `type`/`severity`, and `cleanCodeAttribute`) and `issues[]` (`ruleId`, `primaryLocation{message, filePath, textRange.startLine}`) [S5].
- The format changed in 10.3. From 10.8 the new format is required, or issues show as Maintainability/Medium [S5].
- This format gives control over severity and software quality, so it is better than SARIF for mxcli findings.

**Shared limits of external issues**

- External rules do not appear on the Rules page or in quality profiles. They do count toward the quality gate [S7].
- PR analysis does not report issues raised at file level [S8].
- **Unverified:** whether issues on files SonarQube did not index are dropped. The docs say neither yes nor no.
- Inference: the `.mpr` is binary and `Module.Document` is not a path. MxDiffViewer would have to write one `.mdl` file per document into `sonar.sources` and point `filePath`/`uri` and a line at it. That needs a spike.

**Test execution (`sonar.testExecutionReportPaths`)**

- Format: `<testExecutions version="1"><file path="..."><testCase name="..." duration="ms"/>` with optional `<skipped/>`, `<failure/>`, `<error/>`. `path` must be a test file [S6].
- Supported for branches only, not PRs [S10].
- JUnit is only read for Java (`sonar.junit.reportPaths`) [S10], so mxcli's JUnit has to be converted.

**Editions**

- Branch and PR analysis start at Developer Edition, which "adds branch/PR analysis … on top of SonarQube Community Build" [S9].
- Cloud Free: main-branch analysis only, and PRs only when they target main. Team and Enterprise: unlimited [S11].

**Showing report scores**

- There is no documented generic import for custom measures.
- Options:
  - Publish the scores in MxDiffViewer's own report or PR comment.
  - Rely on the external issues those scores come from.
  - Write a plugin (Java `Sensor`) or a web-app page extension [S12][S13].

## 9. Go library

- Install with `go get github.com/mendixlabs/mxcli` and open with `modelsdk.Open(path)` [G1]. Open is read-only: `ConnectReadOnly`, SQLite `mode=ro` [G3][G4].
- It returns a `backend.FullBackend` with typed `List*`/`Get*` methods for modules, domain models, microflows, nanoflows, pages, layouts, enumerations, constants and scheduled events, plus `ExportJSON()` (8 sections) [G1][G5].
- The `api` package adds fluent builders (write path) [G1].
- I walked the source imports: the root package and `api` **do not** import the generated ANTLR parser (inference from the walk).
- **MDL text (describe) lives in `mdl/executor`, which imports `mdl/visitor` and `mdl/grammar/parser`.** That parser is gitignored [G6], so `go get` alone cannot build describe, and `go install …@latest` is unsupported [G7].
- So the library gives typed model access, but not MDL. Getting MDL needs either a vendored fork that runs `make grammar` or shelling out to the CLI binary.
- No API stability is promised. The project is alpha.

## 10. Maturity / risks

- **Licence:** Apache-2.0 [R1].
- **Activity:**
  - Created 2026-03-12. Releases run from v0.2.0 to **v0.26.0 (2026-10-11)**, about weekly, plus a rolling `nightly` that the README recommends [R1][V6].
  - Contributors: ako (3,896 commits), "claude" (1,618), hjothamendix (250), engalar (185) and retran (104), plus about 15 others [R1].
  - About 133 open issues [R1].
- **Corruption:**
  - The README warns about it [V2].
  - Recent write-path issues include `alter entity` corrupting an index (#1451) [I11], and a GUID re-mint that emptied 28 attributes across 607 rows (#1119, fixed) [D6].
  - Reads are lower risk because `Open` is read-only [G3]. But `lint`, `report` and `describe` still write `.mxcli/catalog.db` into the project folder [P1].

## Risks and open questions

1. Building the full-project MDL is MxDiffViewer's job: loop over the modules and project-level documents, and accept the types that cannot be described.
2. Non-deterministic order (SQL row order, Go map order) and coordinates mean the output must be normalised after export. File an upstream issue for `sortEntitiesByGeneralization`.
3. `diff-local` does not cover enough types for release control. Use it only as a cross-check, or not at all.
4. Mendix 10 below 10.18 (MPR v1) means no `diff-local` and no `git note`. Reading v1 is claimed, but validation is thin.
5. SonarQube file mapping (SARIF/generic `filePath` vs non-indexed or virtual files) needs a spike against a real instance.
6. Describe has known blind spots (#1459–#1461, #1236, #1498). Changes in those properties will not show up.
7. **Open questions:**
   - Whole-project describe timing on a large app (unmeasured).
   - Whether SQLite row order actually changes between Studio Pro saves (untested).

## Sources

[M1]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/cmd/mxcli/main.go#L387-L388
[M2]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/describe_module_all.go#L66-L231
[M3]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/describe_module_all.go#L325-L341
[M4]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/cmd/mxcli/cmd_describe.go#L255-L345
[M5]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_export_mappings.go#L134-L141
[M6]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_entities_describe.go#L255-L431
[M7]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_microflows_show.go#L732
[M8]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_pages_describe.go#L203
[M9]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/docs/11-proposals/PROPOSAL_multi_agent_merge.md#L86-L101
[M10]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/catalog/builder_source.go
[D1]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/modelsdk/mpr/reader_units.go#L141-L146
[D2]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/modelsdk/mpr/reader_units_v1.go#L158-L163
[D3]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_modules.go#L759-L796
[D4]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_entities_describe.go#L238
[D5]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_microflows_show_helpers.go#L49-L53
[D6]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/CHANGELOG.md#L288-L292
[D7]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/docs/13-decisions/0010-mdl-canonical-syntax-rules.md#L34-L37
[D8]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/CHANGELOG.md#L2323
[D9]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/CHANGELOG.md#L232
[D10]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/CHANGELOG.md#L143
[P1]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_catalog.go#L372-L431
[P2]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/CHANGELOG.md#L11
[P3]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/CHANGELOG.md#L234
[P4]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/CHANGELOG.md#L1966
[P5]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/CHANGELOG.md#L2006
[P6]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/CHANGELOG.md#L50
[P7]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/cmd/mxcli/main.go#L362
[V1]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/README.md#L642-L646
[V2]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/README.md#L3
[V3]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/.github/workflows/nightly.yml#L16-L28
[V4]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/.github/workflows/nightly.yml#L69-L76
[V5]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/sdk/versions/mendix-10.yaml#L1-L4
[V6]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/README.md#L207
[O1]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/cmd/mxcli/main.go#L360-L430
[O2]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/format.go#L127-L156
[F1]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_diff_local.go#L26-L43
[F2]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_diff_local.go#L345-L380
[F3]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/cmd/mxcli/cmd_diff.go#L70-L159
[F4]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_diff_local.go#L119-L191
[F5]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/executor/cmd_diff_local.go#L100
[F6]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/cmd/mxcli/cmd_git.go#L17-L65
[L1]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/linter/output.go#L219-L302
[L2]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/README.md#L359
[L3]: https://github.com/mendixlabs/mxcli/tree/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/linter/rules
[L4]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/.claude/lint-rules/conv001_boolean_naming.star#L12-L40
[L5]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/linter/linter.go#L52-L80
[R1]: https://github.com/mendixlabs/mxcli/releases
[R2]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/linter/report.go#L213-L231
[R3]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/linter/report.go#L99-L108
[R4]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/linter/report.go#L12-L35
[T1]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/cmd/mxcli/testrunner/junit.go#L15-L45
[T2]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/cmd/mxcli/cmd_test_run.go#L18-L129
[T3]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/README.md#L536-L555
[G1]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/docs/GO_LIBRARY.md#L5-L270
[G2]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/docs/GO_LIBRARY.md#L329-L342
[G3]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/modelsdk.go#L186-L204
[G4]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/modelsdk/mpr/reader.go#L118-L124
[G5]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/mdl/backend/modelsdk/export_json.go#L19-L70
[G6]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/.gitignore#L42-L43
[G7]: https://github.com/mendixlabs/mxcli/blob/b655f1c92e010dfaf3b34322c9f32f18ece4775c/README.md#L216-L233
[I1]: https://github.com/mendixlabs/mxcli/issues/1460
[I2]: https://github.com/mendixlabs/mxcli/issues/1461
[I3]: https://github.com/mendixlabs/mxcli/issues/1459
[I4]: https://github.com/mendixlabs/mxcli/issues/1236
[I5]: https://github.com/mendixlabs/mxcli/issues/1498
[I6]: https://github.com/mendixlabs/mxcli/issues/658
[I7]: https://github.com/mendixlabs/mxcli/issues/1433
[I8]: https://github.com/mendixlabs/mxcli/issues/1424
[I9]: https://github.com/mendixlabs/mxcli/issues/1242
[I10]: https://github.com/mendixlabs/mxcli/issues/1363
[I11]: https://github.com/mendixlabs/mxcli/issues/1451
[S1]: https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/importing-external-issues/importing-issues-from-sarif-reports
[S2]: https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/importing-external-issues/importing-issues-from-sarif-reports
[S3]: https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/importing-external-issues/importing-issues-from-sarif-reports
[S4]: https://docs.sonarsource.com/sonarqube-server/9.9/analyzing-source-code/importing-external-issues/importing-issues-from-sarif-reports
[S5]: https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/importing-external-issues/generic-issue-import-format
[S6]: https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/test-coverage/generic-test-data
[S7]: https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/importing-external-issues/about-external-issues
[S8]: https://docs.sonarsource.com/sonarqube-server/discovering/code-analysis/pull-request-analysis
[S9]: https://docs.sonarsource.com/sonarqube-server/discovering/sonarqube-server-editions
[S10]: https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/test-coverage/test-execution-parameters
[S11]: https://docs.sonarsource.com/sonarqube-cloud/administering-sonarcloud/managing-subscription/subscription-plans
[S12]: https://docs.sonarsource.com/sonarqube-server/extension-guide/developing-a-plugin/plugin-basics
[S13]: https://docs.sonarsource.com/sonarqube-server/extension-guide/developing-a-plugin/adding-pages-to-the-webapp

- [M1] main.go describe flags (`--all`) · [M2] module-all type registry · [M3] reportUnemitted · [M4] describe type dispatch · [M5] export mapping web-service source · [M6] entity describe · [M7] microflow grants · [M8] page grants · [M9] textconv proposal (draft) · [M10] catalog source builder
- [D1]–[D2] unit queries without ORDER BY · [D3] map-ordered subclass sort · [D4] `@Position` · [D5] authored-layout filter · [D6] GUID changelog · [D7] ADR-0010 · [D8]–[D10] CHANGELOG determinism and freeze entries
- [P1] catalog cache · [P2]–[P6] CHANGELOG timings · [P7] `-c` flag
- [V1]–[V6] README compatibility and warning, nightly CI matrix, version registry, nightly recommendation
- [O1]–[O2] output formats · [F1]–[F6] diff, diff-local, git note · [L1]–[L5] lint · [R1]–[R4] releases and report scoring · [T1]–[T3] test runner · [G1]–[G7] Go library · [I1]–[I11] issues · [S1]–[S13] SonarSource docs
