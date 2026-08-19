# Changelog for version 2.1.236

## Summary

This release adds Artifact types for creating private, template-based Artifacts and introduces one-shot idle notifications between local Claude Code sessions. It also improves Artifact database workflows, Auto mode setup, feedback-draft controls, and recovery from fullscreen-renderer startup failures.

## New Features


### Artifact Types [Gradual Rollout]

What: Create a new private Artifact from a published Artifact type (template or starter), optionally uploading its own data files.

Usage:

```bash
claude
# Ask Claude to create an Artifact from an Artifact type URL
```

Details:

- Supply an Artifact type URL when publishing; the new Artifact starts as a private copy of that type’s current release.
- After creation, update the new Artifact by its Artifact URL as usual.
- The type’s page, files, capabilities, and settings remain fixed; only the new Artifact’s own files can be changed.
- Availability is account/session-controlled. Claude Code explicitly reports when Artifact types are not enabled.

Evidence: Artifact-type publishing uses `"type_url"` and is gated by `"CLAUDE_CODE_ARTIFACT_TYPES"`; search for `"**Artifact types**:"` and `"Artifact types are not enabled in this session"`.


### One-shot Local Session Idle Notifications

What: Claude can request a single notification when another local Claude Code session next becomes idle or exits.

Usage:

```bash
claude
# Ask Claude to notify you when a specified local session is idle
```

Details:

- The notification is one-shot and does not require polling.
- It is limited to main conversations of Claude sessions on the same machine.
- It is unavailable for teammates, subagents, Remote Control, and cloud sessions.

Evidence: Session messaging includes `"notify_when_idle is only available from the main conversation of this session"` and `"notify_when_idle is only supported for Claude sessions on this machine"`.

## Improvements


### Artifact Database File Import and Local Export

Artifact database reads can now save returned documents under a local `out_dir`, and database writes can take a local JSON document through `file_path` instead of requiring inline data.

Usage:

```bash
claude
# Ask Claude to save Artifact database results under ./artifact-data
# or write a JSON file's object to an Artifact database document
```

Details:

- `read_db` can save documents as JSON files instead of inserting large results into the conversation.
- `write_db` accepts either inline `data` or a local JSON `file_path`.
- Local-file writes reject network paths and require a regular JSON file.

Evidence: Artifact database guidance now says `"Add \`out_dir\` to save each returned document as a JSON file"` and `"either \`data\` or \`file_path\`"`; search for `"write_db reads only local files"`.


### Auto Mode Environment Setup Prompt

Claude Code now offers an onboarding prompt to help configure Auto mode with environment context.

Usage:

```bash
claude
# Enter Auto mode, then choose Yes when prompted
```

Details:

- Eligible Auto mode users can choose `Yes`, `Not now`, or `Don't show again`.
- Accepting launches the existing `/auto-mode-setup` workflow.
- The prompt is suppressed when environment context is already present or the user has dismissed it.

Evidence: Search for `"Auto mode works better when it knows your environment. Takes about a minute."` and `"/auto-mode-setup"`.


### More Visible Controls for Claude-Drafted Feedback [Gradual Rollout]

The `/config` interface now exposes controls for model-drafted feedback where product feedback is enabled.

Details:

- `notify` shows a one-line notification when a draft is queued.
- `quiet` keeps only the footer counter.
- `off` disables the SendFeedback tool so drafts are not queued.
- Feedback remains available only in eligible first-party sessions with product feedback allowed.

Evidence: Search for `"Claude-drafted feedback"` and `"Model-drafted feedback (the SendFeedback tool)"`.


### Clearer Fable 5 Usage-Credit Handling

When a Fable 5 usage-credit confirmation cannot be answered in the current session, Claude Code now explains that nothing was sent and directs the user to answer in the originating session or switch models.

Evidence: Search for `"Fable 5 now uses usage credits"` and `"the prompt to confirm went unanswered"`.

## Bug Fixes

- Fullscreen renderer startup failures are now detected and recorded. Claude Code falls back to the classic renderer on the next launch, and disables fullscreen on that machine after repeated failed starts. Search for `"Claude Code's fullscreen renderer didn't finish starting last time"` and `"fullscreen boot canary: failure recorded"`.


Generated with:
- tool: `harness-investigations@6e353ec-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.236.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.236.txt`
