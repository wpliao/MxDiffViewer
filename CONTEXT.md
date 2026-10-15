# MxDiffViewer

MxDiffViewer shows what changed in a Mendix app between two Git commits or branches, and turns that into a release report that helps an approver, reviewer and tester decide what to sign off and what to retest.

## Comparisons

**Comparison**:
One run that pairs a Base with a Target and produces the Changes between them.
_Avoid_: diff run, compare job

**Base**:
The "before" ref of a Comparison.
_Avoid_: old, mine, left, source

**Target**:
The "after" ref of a Comparison.
_Avoid_: new, theirs, right, destination

**Comparison mode**:
Why a Comparison is being made: **Release** (production tag against release candidate), **Branch review** (`main...feature`) or **Ad-hoc** (any two commits).
_Avoid_: diff type, scenario

## The model

**Element**:
Anything shown in the Explorer, such as an entity, association, microflow, page, user role or project setting, identified by its qualified name.
_Avoid_: document, object, unit, item

**Snapshot**:
The text form of a set of Elements at one commit, as rendered by mxcli and normalised.
_Avoid_: export, dump

## Changes

**Change**:
An Element that was **Added**, **Modified** or **Removed** between Base and Target.
_Avoid_: diff, delta, edit

**Layout-only change**:
A Change that only moves things on a canvas (positions, sizes, line shapes) and has no effect on behaviour.
_Avoid_: cosmetic change, noise

**Upgrade-only change**:
A Change made entirely by a Mendix version upgrade converting the model, not by a person.
_Avoid_: migration change

**Opaque change**:
A Change whose content can't be shown as MDL, either because mxcli can't render the Element or because its MDL is identical although the model changed. It's always listed and counts as not fully reviewed.
_Avoid_: hidden change, unknown change

**Possible rename**:
A Removed Element and an Added Element that may be the same thing renamed; the distinction decides whether production data survives.
_Avoid_: rename candidate

## The report

**Release report**:
The output of a Comparison that can be handed on: an Approver summary, a Tester view and the Explorer, as one self-contained file plus the same data as JSON.
_Avoid_: diff report, export

**Approver summary**:
The part of the Release report that lists Risk flags, Opaque changes, commits and ticket IDs, for whoever signs off the release.
_Avoid_: executive summary, overview

**Tester view**:
The part of the Release report that lists the Elements to retest: those Changed, plus their Impact.
_Avoid_: test plan

**Explorer**:
The App Explorer-style tree of Elements with Changes highlighted, plus the side-by-side view of an Element's Base and Target. It is the same for every reader.
_Avoid_: tree view, browser

**Risk flag**:
A finding in the Approver summary with a category (Security, Data, Published APIs, Configuration, Dependencies & platform, Navigation, Logic & UI, Custom code) and a Severity.
_Avoid_: warning, issue, alert

**Severity**:
How much attention a Risk flag needs: **High**, **Medium** or **Info**.
_Avoid_: priority, level

**Impact**:
The Elements that use a Changed Element and so may behave differently even though they weren't edited.
_Avoid_: blast radius, dependents

## Readers

**Approver**:
The person who decides whether a release goes to production.
_Avoid_: release manager, signer

**Reviewer**:
The developer who checks a branch's Changes before it's merged.

**Tester**:
The person who decides what to retest before a release.
_Avoid_: QA
