# Mendix platform research for MxDiffViewer

Scope: the Mendix platform facts that MxDiffViewer depends on. mxcli is researched separately and is not covered here. Sources are docs.mendix.com, read from the official docs repo [github.com/mendix/docs](https://github.com/mendix/docs) at commit `59dbac0` (13 Oct 2026), plus official GitHub repos and vendor docs. Studio Pro 10 is the baseline, and differences in 11 are noted. Researched 14 Oct 2026.

## Summary

- **MPRv2 is the format to design for.** It became the default for new apps in 10.21, and Studio Pro auto-converts apps from 10.22. In MPRv2 each model document is a separate file under `mprcontents/`, so `git diff --name-only` shows which documents changed, but the file contents are only meaningful through Mendix tooling. MPRv1 is a single binary `.mpr`, so Git sees one changed file. ([repo size / MPR format](https://docs.mendix.com/refguide10/troubleshoot-repository-size/#mpr-format), [10.21](https://docs.mendix.com/releasenotes/studio-pro/10.21/), [10.22](https://docs.mendix.com/releasenotes/studio-pro/10.22/))
- **Mendix ships an official headless model diff: `mx diff BASE MINE OUTPUT`**, which writes JSON. Its schema is not documented. `mx dump-mpr` exports full model JSON using Model SDK type names, and `mx check` reports errors, warnings, deprecations and Best Practice Recommender findings. All three ship with Studio Pro and MxBuild on Windows and Linux, and each must match the app's Mendix version. ([merge/diff](https://docs.mendix.com/refguide10/mx-command-line-tool/merge/), [dump-mpr](https://docs.mendix.com/refguide10/mx-command-line-tool/dump-mpr/), [app commands](https://docs.mendix.com/refguide10/mx-command-line-tool/app/))
- **Security can be diffed from 11.0 with `mx export-security-overview -t json`.** On 10.x the Security Overview is GUI and Excel only. ([security command, 11](https://docs.mendix.com/refguide/mx-command-line-tool/security/), [Security Overview, 10](https://docs.mendix.com/refguide10/security-overview/))
- **Team Server is plain Git,** reachable at `https://git.api.mendix.com/<AppID>.git` with a PAT. Bring-your-own Git hosts (GitHub, GitLab, Azure DevOps, Bitbucket) are supported. A read-only diff tool can clone any of them. ([Team Server](https://docs.mendix.com/developerportal/repository/team-server/), [on-premises Git](https://docs.mendix.com/refguide10/on-premises-git/))
- **The Model SDK and Platform SDK are a poor fit.** They are cloud-only, Team-Server-only, and work through temporary online working copies, with no local `.mpr` support. ([SDK FAQ](https://docs.mendix.com/apidocs-mxsdk/mxsdk/sdk-faq/))
- **The Studio Pro Comparison pane can compare two arbitrary commits only from 11.12**, it has no export, and the Extensibility API (beta) runs only inside Studio Pro. MxDiffViewer fills a real gap for headless, exportable release-review reports. ([comparison pane](https://docs.mendix.com/refguide/comparison-pane/), [Extensibility API](https://docs.mendix.com/apidocs-mxsdk/apidocs/extensibility-api-10/))
- **Testing:** the Unit Testing module exposes a remote REST API that returns its own JSON, not JUnit XML. ATS is no longer sold. Mendix documents `mx-name-*` CSS classes for Selenium-style UI tests. ([Unit Testing](https://docs.mendix.com/appstore/modules/unit-testing/), [ATS](https://docs.mendix.com/appstore/partner-solutions/ats/), [Selenium support](https://docs.mendix.com/howto10/front-end/selenium-support/))
- **Quality:** AQM has been renamed QSM, which is run with SIG. Mendix documents nothing about SonarQube. SonarQube's generic issue-import JSON is the realistic route for surfacing model findings. ([QSM](https://docs.mendix.com/appstore/partner-solutions/qsm/), [Sonar generic issues](https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/importing-external-issues/generic-issue-import-format))

## Q1. Git and the MPR format

**Formats**
- **MPRv1:** the whole model is one binary `.mpr` file, a database of all documents. Git sees one changed file, and you need Studio Pro or `mx` to know which documents changed. Deltas are large, and Git stores full copies of files above 512 MB. ([repo size](https://docs.mendix.com/refguide10/troubleshoot-repository-size/#mpr-format))
- **MPRv2:** documents are stored as separate files in `mprcontents/`, and the `.mpr` becomes an index. The same page covers this. Merge docs call these files `.mxunit` files ([managing branches, 11](https://docs.mendix.com/refguide/managing-branches/)). The internal file format is not documented: **unverified** whether a `.mxunit` file is readable without Mendix tooling.
- Both formats behave the same inside Studio Pro, and v1 and v2 branches can coexist in one app ([repo size](https://docs.mendix.com/refguide10/troubleshoot-repository-size/#mpr-format)).

**Version history**

| Version | Change | Source |
| --- | --- | --- |
| 10.17 | The History dialog marks revisions where the MPR format changed. | [10.17 notes](https://docs.mendix.com/releasenotes/studio-pro/10.17/) |
| 10.18 | MPRv2 in public beta. | [10.18 notes](https://docs.mendix.com/releasenotes/studio-pro/10.18/) |
| 10.21 | MPRv2 is GA and the default for new apps. `mx create-project` defaults to v2, and `--use-mpr-format-v1` opts out. | [10.21 notes](https://docs.mendix.com/releasenotes/studio-pro/10.21/), [app commands](https://docs.mendix.com/refguide10/mx-command-line-tool/app/) |
| 10.22 and 11.0 | Existing apps are auto-converted on open. v1 files over 250 MB cannot be committed. | [10.22 notes](https://docs.mendix.com/releasenotes/studio-pro/10.22/), [11.0 notes](https://docs.mendix.com/releasenotes/studio-pro/11.0/) |

**Conversion**
- Use **File > Upgrade app to split MPR format (v2)**, or **Downgrade to combined format (v1)**. The conversion applies per branch, and you should commit first ([repo size](https://docs.mendix.com/refguide10/troubleshoot-repository-size/#mpr-format)).
- A diff between two revisions can therefore cross a format change. MxDiffViewer must handle a v1 base against a v2 head.

**Files that change per commit**
- With MPRv2, a commit changes the `.mxunit` files of the edited documents. With MPRv1, a commit changes the single `.mpr`.
- Java action stubs in `javasource/`, JavaScript actions in `javascriptsource/{module}/actions/*.js`, and theme files in `theme/` and `themesource/` are regenerated or edited alongside the model ([JavaScript actions](https://docs.mendix.com/refguide10/javascript-actions/), [custom Java](https://docs.mendix.com/refguide10/extending-your-application-with-custom-java/)).
- Studio Pro adds and removes widget files in version control automatically ([using version control, 10](https://docs.mendix.com/refguide10/using-version-control-in-studio-pro/)).
- Gradle manages `vendorlib/`, which is committed like `userlib/` together with `vendorlib-sbom.json` ([managed dependencies](https://docs.mendix.com/refguide10/managed-dependencies/)).
- Each commit made by Studio Pro carries metadata: the Studio Pro version, the changed documents, and stories. Commits made with third-party tools lack this metadata and cannot be deployed to Mendix Cloud ([using version control, 10](https://docs.mendix.com/refguide10/using-version-control-in-studio-pro/)).

**Editing and ignored files**
- Editing the `.mpr` or `mprcontents/` by hand corrupts the app, and renaming the `.mpr` is not supported ([version control](https://docs.mendix.com/refguide10/version-control/)). MxDiffViewer must stay read-only.
- MPRv2 journal files `/mprcontents/mprjournal*` are ignored ([repo size](https://docs.mendix.com/refguide10/troubleshoot-repository-size/#mpr-format)).
- docs.mendix.com does not publish the full default `.gitignore`. Release notes mention individual additions: an `svn` folder in 10.14, and `themecache.css` and temporary Java files in 10.24, 11.6 and 11.11 ([10.14](https://docs.mendix.com/releasenotes/studio-pro/10.14/), [10.24](https://docs.mendix.com/releasenotes/studio-pro/10.24/)). The import page lists these protected locations: `releases/`, `packages/`, `deployment/`, `nativemobile/builds/`, `vendorlib/temp/` ([import and export](https://docs.mendix.com/refguide10/import-and-export/)).
- The mendixlabs Gradle plugin ships an ignore template that adds the following to the folders above: `/.mendix-cache/`, `/*.mpr.bak`, `/*.mpr.lock`, `/modeler-merge-marker`, `/project-settings.user.json`, `/javasource/*/proxies/`, `/javasource/system/`, `/**/node_modules/` (except `javascriptsource`), `/.svn/`, `/mprcontents/mprjournal*` and compiled theme CSS ([gitignore.template](https://github.com/mendixlabs/mendix-gradle-plugin/blob/main/plugin/src/main/resources/mxw/gitignore.template)). **Unverified** whether Studio Pro writes exactly this list, in particular the `proxies/` entry.

## Q2. Team Server

**Git and SVN**
- Team Server is built on Git. Since Mendix 10 it supports only Git, and all SVN support was removed in 10.0 ([10.0 notes](https://docs.mendix.com/releasenotes/studio-pro/10.0/), [VC FAQ](https://docs.mendix.com/refguide10/version-control-faq/)).
- Migrating from SVN to Git requires the main line to be on 9.24.28 or later. Mendix suggests combining the migration with an upgrade to 10.24 ([migrate to Git](https://docs.mendix.com/developerportal/general/migrate-to-git/)).

**Access**
- Clone URL: `https://git.api.mendix.com/<AppID>.git`.
- Credentials: the username is your Mendix username or `pat`, and the password is a PAT with `mx:modelrepository:repo:read` or `mx:modelrepository:repo:write` scope. To clone: `git clone https://pat:{PAT}@git.api.mendix.com/{APPID}.git`. ([Team Server](https://docs.mendix.com/developerportal/repository/team-server/), [authenticating](https://docs.mendix.com/refguide10/using-version-control-in-studio-pro/#authenticating))
- Third-party clients can connect. However, Studio Pro does not support opening clones made outside Studio Pro, because it post-processes its own clones. Shallow clones are documented for CI builds of a single revision. ([using version control, 10](https://docs.mendix.com/refguide10/using-version-control-in-studio-pro/))
- For MxDiffViewer, a plain `git clone` or `git fetch` is enough to read two revisions. Don't hand that working copy to Studio Pro.
- Team Server is hosted on AWS in Frankfurt and has no pull or merge requests. Mendix suggests external tools for reviewing Java, JavaScript and theme code ([VC FAQ](https://docs.mendix.com/refguide10/version-control-faq/)). This is the gap MxDiffViewer targets.

**Third-party Git hosts**
- Supported hosts: Azure DevOps Server and Azure Repos, GitHub.com and GitHub Enterprise, GitLab.com/EE/CE, Bitbucket.org/Server/Data Center. Authentication is HTTP basic with a PAT, or Windows authentication. ([on-premises Git](https://docs.mendix.com/refguide10/on-premises-git/))
- With a third-party host you lose direct Mendix Cloud deploy, Portal builds, the App Repository/Build/Projects/Epics/User Management APIs, the Platform SDK, and AQM (now QSM) (same page).

## Q3. Studio Pro diff, merge and conflict features

**Studio Pro 10**
- **Changes pane:** a three-level view (documents, then elements, then properties), with Mine/Theirs/Original columns during conflicts and a "Show purely visual changes" toggle ([changes pane](https://docs.mendix.com/refguide10/changes-pane/)).
- **Compare with original:** opens an external tool such as TortoiseGitMerge for on-disk files only. It is not available on macOS (same page).
- **History:** a dialog per development line ([using version control, 10](https://docs.mendix.com/refguide10/using-version-control-in-studio-pro/)).
- **Merging:** "Merge Changes Here" supports cherry-pick and feature-branch merges. Changes are combined by Rebase (the default, which needs Git 2.41 or later) or by a merge commit.
- **Conflicts:** resolved at element level, including list-order conflicts. Commit messages get a `#Conflicts` tag. A merge can introduce consistency errors even without conflicts. ([merge algorithm](https://docs.mendix.com/refguide10/merge-algorithm/))

**Studio Pro 11 (differences)**
- **Comparison pane:**
  - 11.9: compare a historical revision with the current state.
  - 11.12: compare any two commits selected in the History pane, with status filters and sortable columns.
  - 11.13: details for added and deleted items. 11.14: filter out on-disk changes. 11.15: compare a revision with its parent or child.
  - Three levels, with Older/Newer property values. The only output is a per-cell **Copy**; no export is documented.
  - Sources: [comparison pane](https://docs.mendix.com/refguide/comparison-pane/), [comparing revisions](https://docs.mendix.com/refguide/comparing-revisions/), [11.12 notes](https://docs.mendix.com/releasenotes/studio-pro/11.12/).
- **Text diff:** 11.11 added a built-in text diff, so no third-party tool is needed ([11.11 notes](https://docs.mendix.com/releasenotes/studio-pro/11.11/)).
- **Cross-branch comparison: unverified.** The docs only describe selecting commits in the History pane.
- **Command-line merge:** merging MPRv2 with Git on the command line or with third-party tools is unsupported and can corrupt the branch. An `mx` merge command for MPRv2 is planned for "a future release" ([managing branches, 11](https://docs.mendix.com/refguide/managing-branches/)). `mx merge` works as a Git merge driver for MPRv1 only ([merge, 11](https://docs.mendix.com/refguide/mx-command-line-tool/merge/)).

**Limits for release review**
- Studio Pro only runs on desktop Windows or macOS and is GUI-only.
- There is no report export, no audit trail, and no SonarQube or CI integration.
- On 10.x you cannot compare two arbitrary commits.
- None of this can run in a pipeline.

## Q4. Official model access

**Model SDK and Platform SDK**
- Both are MIT-licensed npm packages. Current versions are Model SDK 4.116.0, which supports Studio Pro 11.15, and Platform SDK 5.2.0 ([Model SDK notes](https://docs.mendix.com/releasenotes/sdk/model-sdk-4/), [Platform SDK notes](https://docs.mendix.com/releasenotes/sdk/platform-sdk/)).
- They work only on Team Server apps, not on third-party Git, and require a PAT ([SDK FAQ](https://docs.mendix.com/apidocs-mxsdk/mxsdk/sdk-faq/), [on-premises Git](https://docs.mendix.com/refguide10/on-premises-git/)).
- They create a temporary **online working copy** from a branch or commit ID. Working copies are deleted after 24 h. Limits are 20,000 files and an initial `.mpk` of at most 250 MB. Creating a working copy is "resource intensive", and the Model API is hosted in the EU. ([SDK FAQ](https://docs.mendix.com/apidocs-mxsdk/mxsdk/sdk-faq/), [Platform SDK how-to](https://docs.mendix.com/apidocs-mxsdk/mxsdk/using-platform-sdk/), [SDK intro](https://docs.mendix.com/apidocs-mxsdk/mxsdk/sdk-intro/))
- No local `.mpr` mode is documented. Pricing and rate limits are **unverified** because the docs say nothing about either.

**mx command-line tool**
- `mx` ships with Studio Pro and MxBuild on Windows and Linux. 11.2 added macOS symlinks. ([mx tool](https://docs.mendix.com/refguide10/mx-command-line-tool/))

| Command | What it does | Source |
| --- | --- | --- |
| `mx diff [-l] BASE MINE OUTPUT` | Diffs two `.mpr` files and writes the result as JSON. Return codes: 0 OK, 2 conflicts, 4 unsupported version, 129 error. `--loose-version-check` auto-converts the version first. The JSON schema is **not documented**. 11.8 made it faster and lighter on memory. **Unverified** whether it works on MPRv2 checkouts; the docs only say ".mpr files". | [merge/diff](https://docs.mendix.com/refguide10/mx-command-line-tool/merge/), [11.8 notes](https://docs.mendix.com/releasenotes/studio-pro/11.8/) |
| `mx merge BASE MINE THEIRS` | Three-way merge; works as a Git merge driver for MPRv1 only. `mx git-merge` for MPRv2 appeared in 10.21 and was withdrawn in 10.22. | [merge/diff](https://docs.mendix.com/refguide10/mx-command-line-tool/merge/), [10.21](https://docs.mendix.com/releasenotes/studio-pro/10.21/), [10.22](https://docs.mendix.com/releasenotes/studio-pro/10.22/) |
| `mx dump-mpr` | Exports model JSON using Model SDK names (`$Type`, `$QualifiedName`, `dataStorageGuid`, access rules). Filters: `--unit-type`, `--module-names` (10.16), `--exclude-system-module` and `--exclude-protected-modules` (10.12). Added in 10.4. | [dump-mpr](https://docs.mendix.com/refguide10/mx-command-line-tool/dump-mpr/) |
| `mx check [-w -d -p] app.mpr [suppress.json]` | Reports errors, warnings, deprecations and performance (Best Practice Recommender) findings. The return code is a bitmask: 1, 2, 4, 8. The `.mpr` must match the `mx` version. 10.0 notes mention a JSON output option, but the reference page doesn't list it: **unverified**. | [app commands](https://docs.mendix.com/refguide10/mx-command-line-tool/app/), [10.0 notes](https://docs.mendix.com/releasenotes/studio-pro/10.0/) |
| `mx export-security-overview -t json\|xlsx [-e] -o FILE app.mpr` | Exports the security overview. **11.0 and later only.** | [security, 11](https://docs.mendix.com/refguide/mx-command-line-tool/security/) |
| Others | `convert`, `show-version`, `show-java-version`, `sync-java-dependencies` (10.20), `analyze-mpr`, `show/set-app-version`, `show/set-module-version`, `module-import`, `create-*-package`, `translate` (beta), `show/delete-private-values` | [mx tool](https://docs.mendix.com/refguide10/mx-command-line-tool/) |

**MxBuild**
- Linux builds download from `https://cdn.mendix.com/runtime/mxbuild-{ver}.tar.gz`; Windows builds are `win-mxbuild` ([MxBuild](https://docs.mendix.com/refguide10/mxbuild/)).
- Options: `--target=package|deploy|sbom`, `--write-errors=FILE` (JSON `problems`), `--generate-sbom` (CycloneDX), `--loose-version-check`, `--model-version`, `--extra-gradle-arguments` (10.23). Exit codes are 0–3.
- 11.9 added `--target=portable-app-package`. Since 11.9, web extensions can raise consistency errors in MxBuild. ([MxBuild, 11](https://docs.mendix.com/refguide/mxbuild/))

**Extensibility API (beta)**
- It runs **inside Studio Pro only**, so it cannot be used headless ([Extensibility API 10](https://docs.mendix.com/apidocs-mxsdk/apidocs/extensibility-api-10/)).
- **C# API:** model access through `CurrentApp`/`IModel`, plus an Untyped Model Access API that uses Model SDK type names. C# extensibility now receives "only critical fixes" ([C# model API](https://docs.mendix.com/apidocs-mxsdk/apidocs/interact-with-model-api-10/), [untyped model API](https://docs.mendix.com/apidocs-mxsdk/apidocs/untyped-model-access-api-10/)).
- **Web (TypeScript) API in 11:**
  - Model access is limited to building blocks, domain models, enumerations, pages and snippets. There is no microflow access ([web model API](https://docs.mendix.com/apidocs-mxsdk/apidocs/web-extensibility-api-11/model-api/)).
  - `studioPro.ui.versionControl` returns only the VCS type, branch and last commit ([version control API](https://docs.mendix.com/apidocs-mxsdk/apidocs/web-extensibility-api-11/version-control-api/)).
- It could host an in-Studio-Pro viewer later, but it can't do the diffing.

**Official diff tool:** there is no stand-alone product. `mx diff` and the Studio Pro Comparison pane are the only official model diff features.

## Q5. Testing

**Unit Testing module** ([docs](https://docs.mendix.com/appstore/modules/unit-testing/), [Marketplace 390](https://marketplace.mendix.com/link/component/390/), [github.com/mendix/UnitTesting](https://github.com/mendix/UnitTesting), latest v10.0.8 from 16 Sep 2026)
- Tests are microflows (return nothing, a Boolean, or a String error, with an optional `UnitTestContext` parameter) or JUnit 4 tests under `javasource/<module>`.
- Setup and TearDown microflows are supported, and a test run rolls back by default. Only one test run may execute at a time.
- **Remote API:** enable it with the `UnitTesting.RemoteApiEnabled` and `RemoteApiPassword` constants, and set `UnitTesting.Enabled` to run outside local development.
  - Calls are `POST /unittests/start` (returns 204) and `POST /unittests/status`, both with `{"password"}` in the body.
  - The status response is JSON: `failures`, `tests`, `runtime` (ms), `completed`, and `failed_tests[]` entries with `name`, `error` and `step`.
  - **No JUnit XML or other standard report.** CI must poll the status call and convert the result.
- **Mendix Pipelines** has a built-in Unit Test step that uses this API. It only works for licensed apps on Mendix Cloud, Kubernetes or Azure ([Mendix Pipelines](https://docs.mendix.com/developerportal/deploy/mendix-pipelines/)).
- A mendixlabs reference shows JUnit 5 and Mockito for Java actions through Gradle. It is "not officially supported" and targets 9.24.3 ([javaunittestreference](https://github.com/mendixlabs/javaunittestreference)).

**ATS:** Mendix "is no longer selling new licenses" and supports only existing contracts. ATS is built by CLEVR on Selenium ([ATS](https://docs.mendix.com/appstore/partner-solutions/ats/)). Its last release was 3.0.3 on 9 Feb 2026 ([ATS release notes](https://docs.mendix.com/releasenotes/marketplace/ats/)). The testing overview now points to Menditect (MTA) for UI and regression testing ([Testing](https://docs.mendix.com/refguide10/testing/)).

**Playwright and Selenium**
- Widget names render as `mx-name-{Name}` CSS classes, and list items get `mx-name-index-N`. Mendix recommends these as Selenium selectors ([Selenium support](https://docs.mendix.com/howto10/front-end/selenium-support/), [common widget properties](https://docs.mendix.com/refguide10/common-widget-properties/)).
- docs.mendix.com has no Playwright guidance. Playwright is mentioned only as an MCP server for Maia in 11.8 ([11.8 notes](https://docs.mendix.com/releasenotes/studio-pro/11.8/)).

**Running tests in CI**
- **Mendix Cloud:** the App Repository API and Build API create a package, the Deploy API (v1, v2, v4) stops, transports and starts the environment, and then the Unit Testing remote API runs the tests ([CI/CD with APIs](https://docs.mendix.com/developerportal/deploy/implement-cicd-pipeline/), [Build API](https://docs.mendix.com/apidocs-mxsdk/apidocs/build-api/), [Deploy API v4](https://docs.mendix.com/apidocs-mxsdk/apidocs/deploy-api-4/)). The Pipelines API also triggers Mendix Pipelines with a PAT ([Pipelines API](https://docs.mendix.com/apidocs-mxsdk/apidocs/pipelines-api/)).
- **Self-hosted or ephemeral:** build with MxBuild, then run in Docker ([docker-mendix-buildpack](https://github.com/mendix/docker-mendix-buildpack)) or as a Portable Runtime zip (`--target=portable-app-package`, available from 10.24.19 LTS, 11.6.5 MTS and 11.9).
  - The Docker Buildpack will **not support Mendix 12**, and Mendix is moving to Portable Runtime ([Docker buildpack](https://docs.mendix.com/developerportal/deploy/docker-deploy/), [Portable Runtime](https://docs.mendix.com/developerportal/deploy/portable-app-distribution-deploy/)).
  - Both need a database such as PostgreSQL.

## Q6. Quality tooling

- **AQM, now QSM:** "Application Quality Monitor (AQM)" was renamed **Quality and Security Management (QSM)**. It is a cloud service from Mendix and SIG (Sigrid) that does ISO 25010 maintainability, architecture, security and open-source health analysis.
  - Reports run nightly on the Team Server main line, and CI support is via SigridCI.
  - It is a paid price-list item.
  - Source: [QSM](https://docs.mendix.com/appstore/partner-solutions/qsm/).
  - QSM is unavailable with third-party Git ([on-premises Git](https://docs.mendix.com/refguide10/on-premises-git/)).
- **Quality Add-on (Omnext) and ACR: unverified.** Current docs have no page for either. The only mention is a third-party Marketplace link, "Omnext Software Analyses Suit" ([content creator guidelines](https://docs.mendix.com/appstore/guidelines-content-creators/)), and the Marketplace page needs a login.
- **Best Practice Recommender** (renamed from Best Practice Bot in 10.12):
  - Works offline.
  - The pane offers **Export to CSV** (suppressed items excluded) and "Limit to uncommitted".
  - The command-line equivalent is `mx check -p` ([BPR 10](https://docs.mendix.com/refguide10/best-practice-recommender/), [mx check](https://docs.mendix.com/refguide10/mx-command-line-tool/app/#check)).
  - Mendix Pipelines has a step that fails on BPR findings ([Mendix Pipelines](https://docs.mendix.com/developerportal/deploy/mendix-pipelines/)).
- **SonarQube:** docs.mendix.com never mentions SonarQube. These vendor and Mendix constraints apply:
  - **Java:** Java analysis with more than one file requires compiled classes in `sonar.java.binaries`, and libraries can be passed in `sonar.java.libraries` ([Sonar Java](https://docs.sonarsource.com/sonarqube-server/latest/analyzing-source-code/languages/java/)).
  - **Java actions:** proxies are generated, and only the import list and code between `BEGIN USER CODE` and `BEGIN EXTRA CODE` markers is kept ([custom Java](https://docs.mendix.com/refguide10/extending-your-application-with-custom-java/)). A scan therefore needs a generated and compiled project, from MxBuild or a Studio Pro deploy, and should exclude `proxies/`. MxBuild's class output path is **unverified**.
  - **JavaScript actions:** they follow the same marker convention ([JavaScript actions](https://docs.mendix.com/refguide10/javascript-actions/)).
  - **Model findings:** they can enter SonarQube through `sonar.externalIssuesReportPaths`, which takes JSON `rules` and `issues` with `primaryLocation.filePath` and `textRange`. Imported rules are not shown on the Rules page and are not part of quality profiles ([generic issue import](https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/importing-external-issues/generic-issue-import-format)). **Unverified** whether issues may point at non-indexed files such as `.mxunit`.
  - **Unit test results:** they can be mapped to `sonar.testExecutionReportPaths` in the generic XML format ([generic test data](https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/test-coverage/generic-test-data)).
- **Linters:**
  - The only linting in the mendixlabs organisation is mxcli's Starlark linter ([mendixlabs/mxcli](https://github.com/mendixlabs/mxcli)), which is out of scope here.
  - `mxlint` lives in a separate, non-Mendix organisation. It exports the model to YAML, evaluates OPA/Rego rules, and writes an xUnit `report.xml`. It says it is "early development" ([mxlint-cli](https://github.com/mxlint/mxlint-cli)). It is not official.

## Q7. Release-control concerns

**Security**
- Licensed Mendix Cloud nodes require the **Production** security level. Off and Prototype/demo are allowed only locally, on Free Apps, or in Development mode ([app security](https://docs.mendix.com/refguide10/app-security/#security-level)).
- Changes to flag: the security level, anonymous or demo users, user and module roles, entity access rules and XPath constraints, and page, microflow and nanoflow access.
- The Security Overview shows combined access per role ([Security Overview](https://docs.mendix.com/refguide10/security-overview/)). On 11 it can be exported as JSON for diffing ([security command](https://docs.mendix.com/refguide/mx-command-line-tool/security/)).

**Domain model and data loss**
- Changing an attribute's type usually **deletes the column and creates a new one**. Some conversions are attempted, and a column that can't be converted gets default values.
- Deleting an attribute and recreating it under the same name loses data, whereas renaming it is tracked.
- Narrowing an association (many-to-many to one-to-many, or one-to-many to one-to-one) makes startup fail on duplicate references.
- Source: [attribute type migration](https://docs.mendix.com/refguide10/attributes-type-migration/).
- The model's identity key is `dataStorageGuid`, which `mx dump-mpr` exposes ([dump-mpr](https://docs.mendix.com/refguide10/mx-command-line-tool/dump-mpr/)). Compare by this GUID, not by name, to tell a rename apart from a drop and re-create.
- Lost storage GUIDs cause data loss. Known issues:
  - `mx module-import replace` and `mx module-import update` lose storage GUIDs in 11.14 and 11.15 ([11.14](https://docs.mendix.com/releasenotes/studio-pro/11.14/), [11.15](https://docs.mendix.com/releasenotes/studio-pro/11.15/)).
  - "Update from file" loses them in 11.12 ([11.12](https://docs.mendix.com/releasenotes/studio-pro/11.12/)).
- Lowering the app-level decimal scale (11.6) can lose data ([11.6](https://docs.mendix.com/releasenotes/studio-pro/11.6/)).
- Database sync runs at startup, on the cluster leader, and causes downtime while it runs ([runtime server](https://docs.mendix.com/refguide10/runtime-server/), [clustered runtime](https://docs.mendix.com/refguide10/clustered-mendix-runtime/)).

**Published APIs**
- A breaking change to a published REST service needs a new major version, made by duplicating the service ([REST versioning](https://docs.mendix.com/refguide10/version-rest-service/)).
- The same applies to OData ([build OData APIs](https://docs.mendix.com/refguide10/build-odata-apis/#versioning)). Changing an entity's key properties counts as breaking ([consumed OData](https://docs.mendix.com/refguide10/consumed-odata-service/)).
- Changes to flag: edits to published operations, resources, entities or attributes inside an existing version.

**Scheduled events and constants**
- Scheduled events are enabled or disabled per environment, outside the model, and that state is tracked **by name**. If you rename an event and reuse the old name, the new event inherits the old one's enabled state ([scheduled events](https://docs.mendix.com/refguide10/scheduled-events/)).
- A new constant takes its Studio Pro default value the first time it is deployed to the cloud. Later default changes are **not** copied. Changed values need a restart, and all constants together are limited to 128 KB ([environment details](https://docs.mendix.com/developerportal/deploy/environments-details/#model-options), [constants](https://docs.mendix.com/refguide10/constants/)).
- The deploy wizard summarises changed constants and scheduled events ([deploying](https://docs.mendix.com/developerportal/deploy/mendix-cloud-deploy/deploying-an-app/)).

**Marketplace modules and Java dependencies**
- "Replace existing module" overwrites local changes, including renamed entities and the tables behind them ([use Marketplace content](https://docs.mendix.com/appstore/use-content/)).
- Module versions can be read with `mx show-module-version` ([mx tool](https://docs.mendix.com/refguide10/mx-command-line-tool/)).
- Managed dependencies are declared per module and resolved by Gradle into `vendorlib/` and `vendorlib-sbom.json`. Transitive conflicts are possible, and `userlib/` holds unmanaged jars ([managed dependencies](https://docs.mendix.com/refguide10/managed-dependencies/)).
- MxBuild `--generate-sbom` produces a CycloneDX 1.4 SBOM that covers Marketplace modules, widgets, npm packages and jars. Diffing two SBOMs gives a dependency delta ([SBOM](https://docs.mendix.com/refguide10/sbom-generation/)).

**Mendix upgrades**
- The Studio Pro version is recorded in commit metadata and in the `.mpr`, and `mx show-version` reads it ([mx tool](https://docs.mendix.com/refguide10/mx-command-line-tool/)).
- Major versions must be upgraded in order (9 to 10 to 11) ([10 to 11](https://docs.mendix.com/refguide/upgrading-from-10-to-11/), [9 to 10](https://docs.mendix.com/refguide10/upgrading-from-9-to-10/)).
- Studio Pro 10.21 and later requires Java 21, and 11 changes how empty strings and concatenation behave ([10 to 11](https://docs.mendix.com/refguide/upgrading-from-10-to-11/)).
- LTS and MTS lines: 10.24 LTS, 11.6 MTS, 11.12 LTS, and 11.18 LTS planned for December 2026 ([LTS/MTS](https://docs.mendix.com/releasenotes/studio-pro/lts-mts/)).
- An MPRv1-to-v2 conversion also shows up as a format-change revision ([repo size](https://docs.mendix.com/refguide10/troubleshoot-repository-size/#mpr-format)).

## Risks and open questions

1. **The `mx diff` JSON schema is undocumented** and may change between versions. Its MPRv2 support, its behaviour across a v1-to-v2 boundary, and its runtime on large apps are **unverified**. Prototype it against real repos before committing. `mx dump-mpr` on both revisions plus a custom JSON diff is a fallback with a documented, SDK-aligned shape.
2. **Version pinning:** `mx` and MxBuild must match each revision's Mendix version (or use `--loose-version-check`). A diff across an upgrade needs two toolchains, or a conversion that may itself introduce changes.
3. **Platform:** `mx` and MxBuild run on Windows and Linux. macOS support is limited to symlinks since 11.2. This constrains the tech stack and CI images.
4. **`.mxunit` contents are not readable as text:** **unverified**. The file list gives cheap change detection, but semantic diffs need Mendix tooling.
5. **Security diffs on 10.x** have no command-line export. They must be derived from `dump-mpr` access rules or the GUI Excel export.
6. **Test reporting:** the Unit Testing API is password-protected, single-run, and returns non-standard JSON. CI needs a running app and a database.
7. **Quality Add-on, Omnext and ACR status could not be verified** from primary sources. QSM is the documented official quality product.
8. **Unverified:** whether SonarQube accepts external issues on non-source paths such as `.mxunit`, and where MxBuild writes compiled classes.
9. **Unverified:** the default `.gitignore` written by Studio Pro, and SDK pricing and rate limits.

## Sources

docs.mendix.com, read from [github.com/mendix/docs](https://github.com/mendix/docs) at commit `59dbac0`:
- Version control: [troubleshoot repository size / MPR format](https://docs.mendix.com/refguide10/troubleshoot-repository-size/#mpr-format), [version control](https://docs.mendix.com/refguide10/version-control/), [using version control (10)](https://docs.mendix.com/refguide10/using-version-control-in-studio-pro/), [managing branches (11)](https://docs.mendix.com/refguide/managing-branches/), [merge algorithm](https://docs.mendix.com/refguide10/merge-algorithm/), [changes pane](https://docs.mendix.com/refguide10/changes-pane/), [comparison pane (11)](https://docs.mendix.com/refguide/comparison-pane/), [comparing revisions (11)](https://docs.mendix.com/refguide/comparing-revisions/), [VC FAQ](https://docs.mendix.com/refguide10/version-control-faq/), [on-premises Git](https://docs.mendix.com/refguide10/on-premises-git/), [import and export](https://docs.mendix.com/refguide10/import-and-export/)
- Team Server: [Team Server](https://docs.mendix.com/developerportal/repository/team-server/), [migrate to Git](https://docs.mendix.com/developerportal/general/migrate-to-git/)
- Command-line tools: [mx tool](https://docs.mendix.com/refguide10/mx-command-line-tool/), [mx merge/diff](https://docs.mendix.com/refguide10/mx-command-line-tool/merge/), [mx dump-mpr](https://docs.mendix.com/refguide10/mx-command-line-tool/dump-mpr/), [mx app commands](https://docs.mendix.com/refguide10/mx-command-line-tool/app/), [mx security (11)](https://docs.mendix.com/refguide/mx-command-line-tool/security/), [MxBuild (10)](https://docs.mendix.com/refguide10/mxbuild/), [MxBuild (11)](https://docs.mendix.com/refguide/mxbuild/), [SBOM](https://docs.mendix.com/refguide10/sbom-generation/), [managed dependencies](https://docs.mendix.com/refguide10/managed-dependencies/)
- Model and API docs: [SDK FAQ](https://docs.mendix.com/apidocs-mxsdk/mxsdk/sdk-faq/), [SDK intro](https://docs.mendix.com/apidocs-mxsdk/mxsdk/sdk-intro/), [Platform SDK how-to](https://docs.mendix.com/apidocs-mxsdk/mxsdk/using-platform-sdk/), [Extensibility API 10](https://docs.mendix.com/apidocs-mxsdk/apidocs/extensibility-api-10/), [C# model API](https://docs.mendix.com/apidocs-mxsdk/apidocs/interact-with-model-api-10/), [untyped model API](https://docs.mendix.com/apidocs-mxsdk/apidocs/untyped-model-access-api-10/), [web model API (11)](https://docs.mendix.com/apidocs-mxsdk/apidocs/web-extensibility-api-11/model-api/), [web version control API (11)](https://docs.mendix.com/apidocs-mxsdk/apidocs/web-extensibility-api-11/version-control-api/), [Build API](https://docs.mendix.com/apidocs-mxsdk/apidocs/build-api/), [Deploy API v4](https://docs.mendix.com/apidocs-mxsdk/apidocs/deploy-api-4/), [Pipelines API](https://docs.mendix.com/apidocs-mxsdk/apidocs/pipelines-api/)
- Testing and quality: [Testing](https://docs.mendix.com/refguide10/testing/), [Unit Testing module](https://docs.mendix.com/appstore/modules/unit-testing/), [ATS](https://docs.mendix.com/appstore/partner-solutions/ats/), [ATS release notes](https://docs.mendix.com/releasenotes/marketplace/ats/), [Selenium support](https://docs.mendix.com/howto10/front-end/selenium-support/), [common widget properties](https://docs.mendix.com/refguide10/common-widget-properties/), [QSM](https://docs.mendix.com/appstore/partner-solutions/qsm/), [Best Practice Recommender](https://docs.mendix.com/refguide10/best-practice-recommender/), [content creator guidelines](https://docs.mendix.com/appstore/guidelines-content-creators/)
- Deployment: [CI/CD with APIs](https://docs.mendix.com/developerportal/deploy/implement-cicd-pipeline/), [Mendix Pipelines](https://docs.mendix.com/developerportal/deploy/mendix-pipelines/), [Docker buildpack](https://docs.mendix.com/developerportal/deploy/docker-deploy/), [Portable Runtime](https://docs.mendix.com/developerportal/deploy/portable-app-distribution-deploy/), [deploying to Mendix Cloud](https://docs.mendix.com/developerportal/deploy/mendix-cloud-deploy/deploying-an-app/), [environment details](https://docs.mendix.com/developerportal/deploy/environments-details/#model-options)
- Security and data: [app security](https://docs.mendix.com/refguide10/app-security/#security-level), [Security Overview](https://docs.mendix.com/refguide10/security-overview/), [attribute type migration](https://docs.mendix.com/refguide10/attributes-type-migration/), [runtime server](https://docs.mendix.com/refguide10/runtime-server/), [clustered runtime](https://docs.mendix.com/refguide10/clustered-mendix-runtime/)
- Integration and modeling: [REST versioning](https://docs.mendix.com/refguide10/version-rest-service/), [build OData APIs](https://docs.mendix.com/refguide10/build-odata-apis/#versioning), [consumed OData](https://docs.mendix.com/refguide10/consumed-odata-service/), [scheduled events](https://docs.mendix.com/refguide10/scheduled-events/), [constants](https://docs.mendix.com/refguide10/constants/), [custom Java](https://docs.mendix.com/refguide10/extending-your-application-with-custom-java/), [JavaScript actions](https://docs.mendix.com/refguide10/javascript-actions/), [use Marketplace content](https://docs.mendix.com/appstore/use-content/)
- Upgrades: [upgrading 9 to 10](https://docs.mendix.com/refguide10/upgrading-from-9-to-10/), [upgrading 10 to 11](https://docs.mendix.com/refguide/upgrading-from-10-to-11/), [LTS/MTS](https://docs.mendix.com/releasenotes/studio-pro/lts-mts/)
- Studio Pro release notes: [10.0](https://docs.mendix.com/releasenotes/studio-pro/10.0/), [10.14](https://docs.mendix.com/releasenotes/studio-pro/10.14/), [10.17](https://docs.mendix.com/releasenotes/studio-pro/10.17/), [10.18](https://docs.mendix.com/releasenotes/studio-pro/10.18/), [10.21](https://docs.mendix.com/releasenotes/studio-pro/10.21/), [10.22](https://docs.mendix.com/releasenotes/studio-pro/10.22/), [10.24](https://docs.mendix.com/releasenotes/studio-pro/10.24/), [11.0](https://docs.mendix.com/releasenotes/studio-pro/11.0/), [11.6](https://docs.mendix.com/releasenotes/studio-pro/11.6/), [11.8](https://docs.mendix.com/releasenotes/studio-pro/11.8/), [11.11](https://docs.mendix.com/releasenotes/studio-pro/11.11/), [11.12](https://docs.mendix.com/releasenotes/studio-pro/11.12/), [11.14](https://docs.mendix.com/releasenotes/studio-pro/11.14/), [11.15](https://docs.mendix.com/releasenotes/studio-pro/11.15/)
- SDK release notes: [Model SDK 4](https://docs.mendix.com/releasenotes/sdk/model-sdk-4/), [Platform SDK](https://docs.mendix.com/releasenotes/sdk/platform-sdk/)

GitHub:
- [mendix/UnitTesting](https://github.com/mendix/UnitTesting)
- [mendix/docker-mendix-buildpack](https://github.com/mendix/docker-mendix-buildpack)
- [mendixlabs/mendix-gradle-plugin gitignore.template](https://github.com/mendixlabs/mendix-gradle-plugin/blob/main/plugin/src/main/resources/mxw/gitignore.template)
- [mendixlabs/javaunittestreference](https://github.com/mendixlabs/javaunittestreference)
- [mendixlabs/mxcli](https://github.com/mendixlabs/mxcli)
- [mxlint/mxlint-cli](https://github.com/mxlint/mxlint-cli) (third-party)

Vendor docs (SonarSource):
- [Sonar Java analysis](https://docs.sonarsource.com/sonarqube-server/latest/analyzing-source-code/languages/java/)
- [Generic issue import format](https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/importing-external-issues/generic-issue-import-format)
- [Generic test data](https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/test-coverage/generic-test-data)
