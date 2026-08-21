# Changelog for version 2.1.239

## Summary

This release adds a gradual-rollout lower-priority continuation mode for sessions that hit their usage limit, plus support for plugins synced from claude.ai. Marketplace authors can now set a plugin-root directory for concise plugin source paths; Remote Control and connection recovery diagnostics also improve.

## New Features


### Continue at lower priority [Gradual Rollout]

What: Eligible users who reach a session limit can continue working at lower priority, subject to available capacity and a separate weekly allowance.

Usage:

```text
/low-priority
```

Details:

- The command is offered after a session limit is reached; run it again to stop lower-priority mode.
- Claude shows waiting and reset status while capacity is unavailable.
- Access requires both an eligible signed-in account and server-provided rollout configuration.

Evidence: Lower-priority command and UI text (search for `"Continue now at lower priority"` and `tengu_toasty_breeze`); it is enabled only when the account has eligible scopes and the rollout configuration is active. These strings are absent from v2.1.238.


### claude.ai-synced plugins [Gradual Rollout]

What: Claude Code can surface plugins synchronized from the user’s claude.ai account alongside local, built-in, and directory-loaded plugins.

Usage:

```text
/plugin
```

Details:

- Synced plugins appear under a `Synced from claude.ai` section.
- Local plugins take precedence when a synced plugin has the same name.
- Sync is enabled by a session/server gate; it can also be controlled in supported environments with `CLAUDE_CODE_SYNC_PLUGINS` or `CLAUDE_CODE_SYNC_SESSION_REFS`.

Evidence: Plugin source category and UI section (search for `"plugins synced from your claude.ai account"` and `"Synced from claude.ai"`); synchronization is gated through `sessionRefsGate.syncEnabled()`. These strings are absent from v2.1.238.


### Marketplace plugin root

What: Marketplace manifests can declare a base directory for bare plugin source names.

Usage:

```json
{
  "metadata": { "pluginRoot": "./plugins" },
  "plugins": [
    { "name": "formatter", "source": "formatter" }
  ]
}
```

Details:

- The example resolves `formatter` relative to `./plugins`.
- `pluginRoot` must be a relative path inside the marketplace.
- Existing explicit `./relative/path` sources remain supported.

Evidence: Marketplace validation and resolution (search for `"metadata.pluginRoot"` and `"Bare source names resolve under metadata.pluginRoot"`). These strings are absent from v2.1.238.

## Improvements


### Remote Control diagnostics in `claude doctor`

`claude doctor` now reports whether Remote Control is enabled for the account, unavailable, or could not be verified, alongside policy, sign-in, subscription, and feature-flag checks.

Evidence: Remote Control diagnostic check (search for `"Remote Control enabled for this account"`). This check is absent from v2.1.238.


### Configurable Desktop SSH worktree location

Claude Code’s settings schema now includes a worktree-location setting for Claude Code Desktop SSH sessions. It lets the Desktop app place SSH-session worktrees outside the default `<project>/.claude/worktrees` directory.

Evidence: Setting description (search for `"Directory under which Claude Code Desktop creates the worktrees of SSH sessions"`). The source explicitly notes that CLI `--worktree`, `EnterWorktree`, and agent isolation do not read this setting yet.


### Clearer streaming fallback warning

When a streaming response ends before producing complete data, Claude Code now tells the user it is retrying without streaming and suggests checking an intervening proxy or gateway if the problem persists.

Evidence: Streaming fallback notification (search for `"Streaming response ended before any complete data was received. Retrying without streaming."`). This message is absent from v2.1.238.

## Bug Fixes

- Remote sessions now attempt trusted-device re-enrollment and retry when the service rejects an event POST as an untrusted device. Evidence: search for `"[SessionsV2Client] untrusted_device on POST — re-enrolled, retrying"`.

- Remote event streams now attempt trusted-device re-enrollment and reconnect after an `untrusted_device` rejection during SSE connection setup. Evidence: search for `"[SessionsV2Client] untrusted_device on SSE connect — re-enrolled, reconnecting"`.

## In Development

Features with infrastructure added but not yet enabled for all accounts. These are shipped behind server-controlled feature flags and may become available in a future rollout.


### Multi-file Artifact access [In Development]

What: Claude will be able to list and save individual files from multi-file claude.ai Artifacts without fetching the whole page.

Status: Feature-flagged.

Usage:

```text
Artifact action: "list_files", url: "<artifact URL>"
Artifact action: "read_file", url: "<artifact URL>", path: "<published path>"
```

Details:

- `list_files` returns each published file’s path, type, and size.
- `read_file` saves a selected file under the session scratchpad by default; another output directory requires user approval.
- The feature is registered only when `tengu_cobalt_plinth_bracken` is enabled. When it is off, multi-file publishing reports that it is not enabled for the account.

Evidence: Artifact file actions (search for `"Artifact files"` and `tengu_cobalt_plinth_bracken`).


### Permanent Artifact deletion [In Development]

What: Claude will be able to permanently delete an Artifact the user owns, with a confirmation required for every deletion.

Status: Feature-flagged and unavailable in remote sessions.

Details:

- Deletion is irreversible: the Artifact link stops working for everyone.
- The action is intentionally blocked in plan mode.
- The feature requires either `CLAUDE_CODE_ARTIFACT_DELETE` or the server-controlled `tengu_cobalt_plinth_alder` flag.

Evidence: Deletion permission description (search for `"Permanently delete a published Artifact the user owns"` and `tengu_cobalt_plinth_alder`).

## Notes

No migration is required. Marketplace maintainers may optionally add `metadata.pluginRoot` to simplify plugin source declarations.


Generated with:
- tool: `harness-investigations@fd6e393-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.239.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.239.txt`
