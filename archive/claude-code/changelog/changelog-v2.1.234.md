# Changelog for version 2.1.234

## Summary

This release adds artifact asset management, an optional automatic continuation flow for Claude.ai usage limits, and support for inline managed-policy helpers. It also improves recovery and safety around goals, artifact comment auto-replies, and account-synced skills.

## New Features

### Artifact asset management

What: Claude can now upload, list, download, and permanently delete image, video, PDF, and font assets attached to a published Artifact.

Usage:

```text
Ask Claude to upload ./chart.png to an existing Artifact, then reference the returned _blob/{id} URL in the page.
```

Details:

- `upload_asset` adds a local file; `list_assets` enumerates stored files.
- `read_asset` saves an asset locally, while `delete_asset` removes it permanently.
- The Artifact must declare the `assets` capability, and only local files are accepted for upload.
- Deletion is intentionally explicit because pages or database rows that still reference the asset will break.

Evidence: Artifact actions `upload_asset`, `list_assets`, `read_asset`, and `delete_asset` (search for `"Artifact assets"` or `"upload_asset"`).


### Automatic continuation at usage limits [Gradual Rollout]

What: Claude Code can wait for a Claude.ai usage limit to reset and automatically continue the interrupted task.

Usage:

```text
Open /config and enable “Continue automatically at usage limit”.
```

Details:

- The new `autoContinueAtUsageLimit` setting defaults to on when the rollout is enabled.
- The limit dialog can arm or cancel the wait; press `esc` to cancel while waiting.
- Claude Code stops automatic continuation when the reset is more than 24 hours away, after repeated renewed limits, or when a session moves to another environment.
- This is limited to eligible Claude.ai subscription sessions and is controlled by the `tengu_marble_heron` rollout flag.

Evidence: Usage-limit continuation setting (search for `"Continue automatically at usage limit"` and `tengu_marble_heron`).


### Inline managed-policy helpers

What: Administrators can define managed settings helpers as inline scripts instead of requiring a helper executable on disk.

Usage:

```json
{
  "policyHelpers": {
    "linux": {
      "interpreter": "sh",
      "script": "printf '%s\n' '{\"permissions\":{\"defaultMode\":\"plan\"}}'"
    }
  }
}
```

Details:

- Inline helpers are accepted only from admin-controlled policy sources.
- Scripts are passed to a fixed interpreter over standard input and are never written to disk.
- macOS, Linux, and WSL use `sh`; Windows uses a fixed-location `pwsh`, never `PATH`.
- A helper can still provide `defaultSettings` as a fallback.

Evidence: Managed policy helper schema (search for `"Inline helper script, delivered to the fixed interpreter over stdin"`).


### Resume Artifact comment auto-replies

What: Claude can resume automatic replies to Artifact comments after they were stopped during the current live session.

Usage:

```text
Ask Claude to resume automatic replies for the Artifact.
```

Details:

- Resuming requires an explicit user-approved action and re-arms the live watch.
- It is unavailable in remote sessions and cannot reverse the session-wide “kill all agents” disarm.
- Comments received while replies were stopped are retained as history rather than bulk-replied.

Evidence: Artifact action `resume_replies` (search for `"Auto-replies resumed on"`).


### Claude.ai account-synced skills [Gradual Rollout]

What: Eligible Claude.ai accounts can make enabled Claude.ai skills available across Claude Code sessions, with a setting to disable syncing.

Usage:

```json
{
  "syncClaudeAiSkills": false
}
```

Details:

- Setting `syncClaudeAiSkills` to `false` stops downloads and hides synced skills.
- In user or managed settings, previously synced skills are moved to `~/.claude/skills/.trash` on the next launch and later cleaned up according to `cleanupPeriodDays`.
- Local settings and `--settings` apply only to that workspace or invocation.
- The account feature remains server-controlled and requires the `tengu_account_skills_sync_enabled` rollout flag; setting the value to `true` does not enable it early.

Evidence: Account-synced skills setting (search for `"syncClaudeAiSkills"` and `tengu_account_skills_sync_enabled`).

## Improvements

### Safer handling of Artifact comment monitors

Claude Code now prevents renderer switches and updates that would silently stop active Artifact comment auto-replies. It tells you to stop the monitor through `/tasks` first, rather than restarting and losing the reply workflow.

Evidence: Restart protection (search for `"Can't restart while auto-replying to artifact comments"`).


### Clearer remote Artifact watch guidance

When Artifact watching is unavailable in a remote session, Claude Code now explains that notifications cannot arrive there and directs users to run a local watch instead.

Evidence: Remote-watch guidance (search for `"Error: --watch-artifact isn't supported yet from remote sessions"`).

## Bug Fixes

- Goals are now cleared after an unrecoverable evaluation error, with a warning that explains how to restart the workflow using `/goal`. (search for `"Goal cleared after an unrecoverable error"`)


Generated with:
- tool: `harness-investigations@ed247a5-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.234.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.234.txt`
