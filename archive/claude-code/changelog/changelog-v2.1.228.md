# Changelog for version 2.1.228

## Summary

This release adds rollout-gated synchronization between a local checkout and a Claude cloud session, and expands the diff experience behind a separate rollout flag. It also ships dark-launched templates for collaborative document and spreadsheet Artifacts; those templates are present but currently disabled.

## New Features

### Cloud-session file synchronization [Gradual Rollout]

What: Claude Code can synchronize eligible files between your local Git checkout and a connected cloud session, including changes made in either location.

Usage:

```bash
claude
/remote-control
```

Details:

- Sync starts only when the server-controlled `tengu_violin_wood` rollout is enabled and the directory has granted `container_sync` consent.
- Claude reports progress rather than blocking a prompt: for example, “File sync is still getting ready; your files go up with your next message.”
- The sync process excludes dot-directories and dependency folders, enforces file and per-turn budgets, and preserves local changes when cloud-side syncing is unavailable.
- Cloud-to-local write-back is not implemented on Windows; local changes can still sync to the cloud session.

Evidence: Cloud directory-sync implementation (search for `"File sync starts with your next message"` and `tengu_violin_wood`).


## Improvements

### Diff panel rollout behavior [Gradual Rollout]

The existing `/diff` command can now become an immediate toggle for an uncommitted-changes panel when the `tengu_willow_crate` rollout is enabled. The panel supports switching comparison bases and filtering tests/generated files; it also hides paths blocked by Read-deny rules.

Evidence: Diff-panel toggle (search for `"Toggle the diff panel showing uncommitted changes"` and `tengu_willow_crate`).


## Bug Fixes

- The diff panel now avoids displaying files covered by Read-deny permission rules, and clearly reports when all changed files are hidden. (search for `"Read-denied files are hidden in this panel"`)


## In Development

Features with infrastructure added but not yet enabled. These are shipped “dark” and may become available in future versions.


### Collaborative document and spreadsheet Artifacts [In Development]

What: Claude Code includes new `doc` and `sheet` Artifact skills for publishing live, collaborative working documents and spreadsheets.

Status: Stubbed

Details:

- The document template provides an editable, commentable, printable working document with a formatting toolbar and block-by-block persistence.
- The spreadsheet template provides editable cells, sorting, comments, a formula bar, and formulas such as cell references and aggregates.
- The skills are registered as user-invocable, but their shared availability check currently returns `!1`, so they cannot be activated in this build.

Evidence: Artifact skills (search for `"Create a document artifact"` and `"Create a spreadsheet artifact"`); availability is hardcoded off in `function rUs() { return !1; }`.


Generated with:
- tool: `harness-investigations@0ffcff1-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.228.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.228.txt`
