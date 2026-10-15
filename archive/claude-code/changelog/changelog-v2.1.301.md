# Changelog for version 2.1.301

## Summary

Version 2.1.301 adds an interactive offer to compact long conversations earlier, support for local plugin marketplace-entry files, and background-command management for compatible MCP tool-host clients. It also improves worktree cleanup, plugin update notices, and compaction errors, with fixes for login refresh failures, unreliable searches, and older terminals.

## New Features


### Earlier-compaction offer [Gradual Rollout]

What: Eligible terminal sessions can now offer a smaller autocompact window through an interactive dialog.

Usage:
```text
/autocompact
```

Details:
- When the offer appears, use ↑/↓ to choose between changing the window and keeping the current setting. Use ←/→ to adjust the proposed size, Enter to confirm, or Escape to dismiss.
- The dialog explains the tradeoff: earlier compaction can reduce usage, but summaries happen more often and may lose details.
- Choosing a smaller window does not change your model.
- If the conversation already exceeds the proposed threshold, the dialog warns that the next message will trigger summarization.
- Availability depends on `tengu_binary_music`, account eligibility, and a model supporting the larger context window. Remote sessions are excluded.
- `/autocompact` already existed. The previous version recorded offer eligibility; this release adds the actual dialog and saves the response.

Evidence: Interactive offer and settings application (search for `"Want to autocompact at"`, `"We recommend compacting earlier"`, and `"tengu_binary_music"`).


### Local plugin marketplace-entry files

What: A local plugin can now carry marketplace-entry metadata and component declarations in `.claude-plugin/marketplace-entry.json`.

Usage:
```bash
claude --plugin-dir /absolute/path/to/my-plugin
```

Details:
- The loader validates the file against the marketplace-entry schema and applies its declarations when loading the plugin.
- The entry can supply manifest information when a separate plugin manifest is absent, or contribute supported metadata and components alongside an existing manifest.
- Existing rules for conflicting component declarations still apply.
- Invalid JSON, schema errors, symlinks, non-regular files, and files larger than 1 MiB are rejected with instructions to fix or remove the file.
- Changes to this entry require `/reload-plugins`; a reload triggered by saving an individual plugin file does not apply them.

Evidence: Local entry-file loading and validation (search for `"marketplace-entry.json"`, `"plugin refused by its marketplace entry file"`, and `"which a reload on save does not apply"`).


### Background commands through MCP tool hosts

What: Compatible clients can start a shell command through the tool host, let it continue in the background, inspect its status, and stop it later.

Usage: Through a compatible client, request a Bash call with `run_in_background: true`. The client can inspect retained commands with `ReadCalls` and stop one with `StopBackgroundCommand`.

Details:
- The host advertises the `"anthropic/backgroundCommands"` capability.
- Background execution requires tool-host interface version 11 or later and must not be disabled by the session.
- Status includes the task ID, output path, elapsed time, and completion or termination state.
- The command is stopped when its effective runtime limit expires or the daemon exits.
- Explicit ask or deny rules naming `run_in_background` prevent this execution path; the caller receives guidance to retry without that option.
- Background shell commands already existed in ordinary sessions. This addition extends the tool-host execution path.

Evidence: Capability negotiation, command tracking, and cancellation (search for `"anthropic/backgroundCommands"`, `"ReadCalls"`, `"StopBackgroundCommand"`, and `"keptBackgroundCommands"`).


### Separate usage-limit wait budget

What: Advanced users can cap how long the retry watchdog spends waiting on usage-limit rejections.

Usage:
```bash
CLAUDE_CODE_RETRY_WATCHDOG=1 \
CLAUDE_CODE_RETRY_WATCHDOG_MAX_USAGE_LIMIT_WAIT_MS=60000 \
claude
```

Details:
- The new variable accepts a positive integer in milliseconds.
- Usage-limit waits are tracked separately from the overall capacity-wait budget.
- When the retry watchdog is active, a reset that exceeds the remaining budget can end the retry instead of keeping the request waiting.
- Without this variable, no separate usage-limit wait ceiling is imposed by this setting.

Evidence: Separate accumulated wait budget (search for `"CLAUDE_CODE_RETRY_WATCHDOG_MAX_USAGE_LIMIT_WAIT_MS"` and `"usageLimitSpentMs"`).

## Improvements


### Clearer compaction results and failures

Compaction failures now have a distinct “Could not compact” presentation, with details distinguishing an oversized conversation from oversized attached media. Successful summaries use a cleaner “Conversation summarized” label.

Usage: Run `/compact` as before; the result now makes success and failure easier to distinguish.

Evidence: Compaction-result formatting (search for `"Could not compact"`, `"conversation too long ·"`, `"attached media too large ·"`, and `"Conversation summarized"`).


### More accurate plugin update notices

Automatic plugin update notices now distinguish updates that applied successfully from reloads that failed, were skipped, or completed with errors. When an update has not taken effect, the notice directs you to `/reload-plugins`.

Evidence: Update outcome-specific notifications (search for `"plugin-autoupdate-reload-errors"` and `"Run /reload-plugins to apply"`).


### Better explanations when Artifact replies do not resume

Sessions using Artifact comment watching now provide more specific recovery instructions when automatic replies cannot resume.

The messages distinguish replies that were explicitly stopped, another live session or background agent holding the watch, organization mismatches, publishing restrictions, and watch limits. Depending on the cause, the guidance points to `/tasks`, `claude agents`, signing into the correct organization, or asking Claude to watch and publish again.

Evidence: Watch-resume explanations (search for `"Automatic replies stayed off for"`, `"a background agent keeps them while it runs"`, and `"a public Artifact from outside your organization can't be watched"`).


### Multiline plugin text inputs

Plugin UI text fields can now request multiple visible rows. Fields remain single-line by default; with two or more rows, Shift+Enter inserts a newline while Enter submits.

Evidence: Text-field validation and interaction contract (search for `"Input props must be { key } and any of label, placeholder, value, submitLabel, rows, autoFocus"`).


### Permission-aware file reads for remote clients

A new `ReadFileForRemote` handler lets compatible remote clients request text or base64 file contents while applying the host session’s permission checks.

The handler incorporates current restrictive settings and preserves `blockReadsOutsideWorkingDirectories`. Denied reads return no file, and oversized responses are rejected.

Usage: This is a client integration capability rather than a new slash command.

Evidence: Remote read handler and response validation (search for `"ReadFileForRemote"` and `"the file is too large to send back as text"`).


### Direct MCP results for local host applications

Local host integrations can now request `result_not_for_model` when calling an MCP tool. This returns content for the host application without the usual model-context processing, such as image resizing, text truncation, or saving oversized output into tool-result files.

Details:
- Clients must check for `"mcp_call_result_not_for_model_v1"`.
- The option is honored only on eligible local process connections.
- Results exceeding 10,485,760 characters fail after the tool has run. The error explicitly warns callers to check whether the action took effect before retrying.

Evidence: Capability and direct-result contract (search for `"mcp_call_result_not_for_model_v1"`, `"result_not_for_model"`, and `"The tool ran, but its result is over the"`).

## Bug Fixes

- Worktree cleanup now checks whether the session’s worktree changed after inspection before removing it. Exit warnings also account for switching branches, commits left only on the original worktree branch, and commit counts that cannot be established. Hook-created worktrees with unknown commit state prompt instead of being silently treated as clean. Evidence: search for `"this session's worktree changed after Claude Code checked it"`, `"commitsOnlyOnWorktreeBranch"`, and `"A WorktreeCreate hook made this worktree"`.

- Full-disk and disk-quota failures during OAuth refresh now produce a specific explanation directing users to free space, rather than treating the problem as something signing in again can fix. Evidence: search for `"OAuthRefreshDiskFullError"` and `"signing in again won't help"`.

- Hosted authentication recovery detects when credentials have changed since the API client was created and retries with the replacement credentials. Evidence: search for `"Host credential replaced since the client was built"`.

- An abnormal ripgrep exit with no results is now reported as a failed search rather than a valid “no matches” result. The guidance asks for one retry and then an explicit report that searching is failing. Evidence: search for `"RipgrepAbnormalExitError"` and `"ripgrep unexpected exit with no results"`.

- Terminal capability detection skips XTVERSION queries on VTE versions before 0.53, where the query could appear as visible text. Evidence: search for `"XTVERSION: not asked (VTE before 0.53 would show the query as text)"`.

- MCP task polling temporarily retries error `-32602` responses rejecting a task ID, rather than immediately declaring the task lost. Retries remain bounded, and expired or persistently unknown tasks still fail. Evidence: search for `"the server rejected the task's id (-32602); asking again"` and `"the server accepts this task's id again"`.

- Managed-hook environment handling is more conservative when policy or environment information cannot be read. An organization HTTP hook receives unset header variables if its trusted environment cannot be composed. Evidence: search for `"no variable a person's plugin wrote is read as the organization's"` and `"header variables from could not be composed"`.

- Forwarded plugins no longer silently substitute an unavailable data directory. References to `${CLAUDE_PLUGIN_DATA}` now fail explicitly when the plugin’s originating data folder was not supplied, and affected allowed-tool declarations are dropped with an explanation. Evidence: search for `"PluginDataDirUnknownError"` and `"they name the plugin's data folder, which did not come with the plugin"`.

- Agent-proxy CA responses receive stricter validation for oversized bundles, unparseable certificates, and stray PEM framing indicating a truncated or malformed response. Evidence: search for `"ca-cert response contains a certificate that does not parse"` and `"ca-cert response has PEM framing outside its certificates"`.

- Plan-file handling validates plan slugs before accepting them as file identifiers. Evidence: search for `"refusing invalid plan slug"`.

- Background-command output now explicitly states that directory changes made by the background process do not affect subsequent session commands. Evidence: search for `"directory changes made by the backgrounded command do not apply to subsequent commands"`.

## In Development

The following capabilities have implementation in the CLI but require additional enablement or host support.


### Persistent attachment placement [In Development]

What: Supported remote sessions can place attachments under a validated user-data location.

Status: Opt-in, host-dependent infrastructure.

Details:
- Requires `CLAUDE_CODE_ATTACHMENTS_IN_USER_DATA`, a remote session ID, and the supported host environment.
- Initialization checks the storage location before using it.
- The path is not used when retention policy forbids it or retention eligibility cannot be established.
- The source does not establish general availability.

Evidence: Attachment-root initialization and policy checks (search for `"CLAUDE_CODE_ATTACHMENTS_IN_USER_DATA"`, `"attachments_in_user_data"`, and `"retention_governed"`).


### Recovery when an end-turn request accompanies a failed tool [In Development]

What: Claude can continue handling a failed tool call when another call in the same batch requested that the turn end.

Status: Feature-flagged behind `tengu_cozy_fern`, defaulting to false.

Details:
- The new path detects a failed sibling call and supplies a continuation message.
- That message tells Claude to address the failure and preserve the effects of calls that already succeeded.
- Additional guards prevent continuation after the iteration or execution budget is exhausted.

Evidence: Failed-sibling continuation (search for `"tengu_cozy_fern"` and `"The turn did not end: a tool call in your last message asked to end it"`).

## Notes

This changelog compares v2.1.300 with v2.1.301. Claims were checked against both source snapshots and, where relevant, the original Bun module sources; module ordering, wrappers, and renamed identifiers are excluded.

Server-controlled rollout availability cannot be established from these files. No extension-package features, standalone SDK release changes, or native-installer changes are claimed.


Generated with:
- tool: `harness-investigations@0fafae6-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.301.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.301.txt`
- source modules: `archive/claude-code/original/cli-v2.1.301.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
