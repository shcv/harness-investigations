# Changelog for version 2.1.317

## Summary

File permission rules such as `Read(*)` and `Edit(*)` now cover working directories rather than every path; existing configurations may need adjustment. Enterprise gateway administrators gain cost reports, and a new privacy check can ask before tools send your account email address outside the machine. Scripted runs also report unsaved session data more clearly, including a nonzero exit status for text and JSON output.

## New Features


### Gateway Cost Reports

Administrators running `claude gateway` can query spending through `GET /v1/organizations/analytics/cost`. Reports support grouping by user or RBAC group, daily buckets, filtering, sorting, and pagination.

```bash
curl --get "$GATEWAY_URL/v1/organizations/analytics/cost" \
  -H "x-api-key: $GATEWAY_ADMIN_KEY" \
  --data-urlencode "starting_at=2026-10-01T00:00:00Z" \
  --data-urlencode "ending_at=2026-10-08T00:00:00Z" \
  --data-urlencode "group_by[]=actor" \
  --data-urlencode "time_bucket_width=1d"
```

- Requires gateway administrator authentication and the native runtime used by `claude gateway`.
- Queries cover at most 31 days; spending is recorded per user per UTC day.
- Daily buckets require `ending_at`. Pagination is restricted for periods whose amounts are still changing.


### Account Email Privacy Prompt [Gradual Rollout]

Claude can now ask before a web request or network-capable shell command includes the signed-in account’s email address. This helps catch accidental disclosure when Claude uses account information in a search, URL, or command.

The built-in `cc-plugin-privacy` check is enabled by default when available, behind `tengu_wise_newt`, whose fallback is on. Existing deny decisions still take precedence.

## In Development


### Editable Plans in Claude Docs

Sessions without a local filesystem are gaining plans stored as Claude Docs. You would be able to edit the document beside the conversation and approve its current contents; Claude is instructed to read your edited version before beginning implementation.

Document creation, revision, approval, and fallback to an inline plan are implemented. Availability requires the Claude Docs connector and `tengu_inked_lantern`, off by default.


### Account Switching with Explicit Session Copying

A new account ownership check can pause a conversation when the signed-in account differs from the account that started it. The dialog offers changing login, exiting, or explicitly copying the conversation into the current account.

Copying requires a separate confirmation explaining that conversation history—including files Claude read—will be shared with the new account. The flow is wired into the interactive CLI behind `tengu_bubbly_fountain`, off by default.


### Life Sciences Use Case Selection

A new `/use-case` command lets eligible Claude subscription users choose an organization-provided Life Sciences use case. The selected use case applies to subsequent requests and can be remembered for later sessions.

The command includes selection, persistence, and recovery when a previously selected use case is no longer available. It is hidden when no use cases are offered and requires `tengu_federated_possum`, off by default.


### Gmail Attachments from Local Files

Claude is gaining the ability to attach readable local files to Gmail messages and new drafts without generating their base64 contents itself. Approval shows the recipients and attached files, and file contents are checked against their recorded SHA-256 before sending.

The implementation requires `tengu_snug_pine`, off by default, and organization policy approval. Limits are 10 attachments, 10 MB per file, and 23 MB combined. Updating an existing draft with file references is refused; Claude must create a new draft with explicit recipients.


### Understanding Changes Made in MCP App Views

A new `ReadWidgetContext` tool lets Claude read text and images shared by an interactive MCP App view. This would allow requests such as “use the options I selected” to refer to the view’s latest shared state.

The implementation supports individual views, size limits, and notices when shared content is incomplete. It requires a compatible hosted session and `tengu_amber_trellis`, off by default.


### Recovering Output Hidden by `tail`

An experimental Bash path preserves the input to `tail` so Claude can inspect earlier output without rerunning a lengthy build or test command. Eligible results include a saved-file notice such as `Full input to tail`.

The initial path targets Linux commands without a custom shell prefix, normally check commands running for at least ten seconds. It requires `tengu_peaceful_origami`, off by default.

## Other Changes

- Changed file-tool allow rules ending in `(*)` or `()` to apply within working directories, behind `bot_protected_tengu_amber_plover`, on by default; bare tool names retain their broader scope.
- Changed local scripted runs with lost transcript or configuration writes to print a disk-space warning and exit with status `1` for text or JSON output; `stream-json` reports `session_writes_lost`.
- Added `permissions.workingDirectoriesAsGiven` for launch-supplied settings, allowing hosts to keep specified working-directory boundaries from following replacement symlinks.
- Added `CLAUDE_CODE_DISABLE_MCP_TASKS=1` to disable MCP task support and preserve that choice when launching background sessions.
- Added `CLAUDE_CODE_DISABLE_SUBAGENT_HANDBACK=1` to disable the subagent handback mechanism.
- Improved startup message queuing so a submitted message is sent when initialization finishes without requiring another Enter press.
- Improved remote managed-settings notices to distinguish loading, failure, cached restrictions, and successful recovery.
- Improved warnings when personal hooks are unavailable, explaining whether setup failed, the launch mode excluded them, or the host withheld them.
- Improved Grep and Glob results to explicitly identify searches cut short by their time limit.
- Improved artifact listings with `page_token` pagination.
- Improved scheduled-task listings to warn when scheduling is disabled and listed jobs will not run.
- Fixed the gateway obscuring Bedrock’s `Input is too long.` error, preserving the message needed for image removal and compaction recovery.
- Fixed Windows sandbox handling of deny entries added after startup by supplying applicable new entries with subsequent commands.
- Fixed `/goal` accepting relayed Slack, Teams, or project-thread messages as direct instructions to change the session goal.
- Fixed duplicate plugin MCP servers being offered when the host already supplies the same server.
- Improved shell permission analysis for SSH, rsync, script interpreters, and complex shell syntax.

## Notes

Review file-tool permission rules that use `(*)` or `()`. For example, `Edit(*)` now permits edits within working directories rather than granting unrestricted path access. Prefer explicit path rules or additional working directories; use the bare tool name, such as `Edit`, only when unrestricted access is intentional.

This change covers `Read`, `Write`, `Edit`, `NotebookEdit`, `Glob`, `Grep`, `LSP`, and `SendUserFile`. Older releases retain the previous interpretation, and the server-controlled gate can restore it in this release.

Automation consuming text or JSON output should handle the new failure status when session data could not be saved. For `stream-json`, handle `session_writes_lost` and its affected session IDs; the event does not necessarily change the process’s exit status.


Generated by `harness-investigations@e99a61a-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: astdiff, strings, module sources
