# Changelog for version 2.1.222

## Summary

This release strengthens worktree isolation and configuration-import safety, improves fallback-model handling for agents, and makes Remote Control authentication failures clearer. It also includes dark-launched infrastructure for automatically responding to artifact comments.

## Improvements


### Safer worktree resume and agent isolation

What: Claude Code now performs much stricter validation before resuming or re-entering an isolated worktree.

Details:

- Rejects worktrees with unsafe Git metadata, symbolic-link ref stores, shared Git directories, `core.worktree` redirects, or network-spelled paths.
- Keeps recoverable bindings for transient verification failures, while clearing only invalid or missing worktrees.
- Provides actionable recovery guidance, such as recreating the tree with `git worktree add`.

Evidence: Worktree validation rejects unsafe trees rather than assuming isolation (search for `"Refusing to use"` and `"as an isolation worktree"`).


### Safer Codex skill imports

What: Importing configuration from Codex now skips skills whose `SKILL.md` begins with YAML frontmatter, preventing Claude Code from automatically activating instructions or permissions that Codex treats as plain text.

Details:

- The affected skill is left for manual review and copying.
- Import continues to enforce size and directory-readability checks.

Evidence: Import guard for `"SKILL.md starts with \`---\`"`.


### More appropriate fallback models for agents

What: When a configured subagent or teammate model is not permitted by the available-model allowlist, Claude Code now prefers the newest allowed model from the same model family before falling back to the parent/default model.

Details:

- Applies to configured subagent and teammate models.
- Preserves the requested model family where a compatible allowed version exists.

Evidence: Allowlist recovery reports `"using the newest allowed model in its family"`.


### Clearer fallback-response notices

What: Claude Code now distinguishes a completed response produced by a fallback model from a permanent switch of the session model.

Details:

- A local fallback response explicitly says the session model remains unchanged.
- Session-level fallback continues to provide a switch notice and points to `/model` for switching back.

Evidence: Fallback notice `"This response was completed by"` and `"Your session model is unchanged."`

## Bug Fixes

- Remote Control now distinguishes an invalid/rejected session token from a generic tools-fetch failure, showing `"connected · session token rejected"` when appropriate. This makes `/login` recovery clearer.

- Plugin and skill discovery now degrades to an empty result instead of failing outright when the service returns an entitlement-related 403. Evidence: `"[plugin-skill-list] degraded to empty"`.

## In Development

Features with infrastructure added but not yet enabled. These are shipped dark and may become available in future versions.


### Automatic replies to artifact comments [In Development]

What: Claude Code can scan activated artifact threads for comments explicitly sent to Claude and automatically reply to them.

Status: Feature-flagged. The implementation is controlled by `tengu_sorrel_trellis`, which defaults to false, with an internal environment override.

Details:

- Tracks comments addressed to Claude separately from ordinary viewer discussion.
- Pauses automatic replies in plan mode, under an hourly cap, or when the current permission mode is notify-only.
- Provides explicit manual-follow-up notices when an automatic reply is paused.

Evidence: Artifact-comment auto-reply gate (search for `"CLAUDE_CODE_ARTIFACT_COMMENTS_AUTOREACT"` and `"Human comments sent to Claude are waiting"`).


### Destructive MCP actions in Remote Auto Mode [In Development]

What: Remote Auto Mode gains an opt-in path to include destructive MCP operations.

Status: Feature-flagged. The path requires `tengu_remote_auto_mode_include_destructive_mcp`, which defaults to false.

Details:

- The operation must be identified as destructive by the MCP tool.
- The flag remains off by default, so destructive MCP actions are not automatically included in normal Remote Auto Mode behavior.

Evidence: Destructive-operation gate (search for `"tengu_remote_auto_mode_include_destructive_mcp"`).


Generated with:
- tool: `harness-investigations@b820743-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.222.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.222.txt`
