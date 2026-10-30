# Changelog for version 2.1.314

## Summary

This release adds an optional boundary for file writes, brings current-session `/insights` analysis to cloud sessions, and adds controls for batching streaming JSON output. It also improves MCP authentication recovery and long-conversation compaction, while preparing a `/send-to-project` handoff workflow. Headless automation can no longer use permission hooks to approve calls that specifically require a person’s approval.

## New Features


### Keep File Writes Within Your Working Directories

The new `permissions.blockWritesOutsideWorkingDirectories` setting confines `Write`, `Edit`, and `NotebookEdit` to the session’s working directories, even in permission modes that normally allow edits automatically.

```json
{
  "permissions": {
    "blockWritesOutsideWorkingDirectories": true
  }
}
```

- Add another permitted directory with `/add-dir`.
- A `true` value in any settings source takes precedence; allow rules cannot override it.
- Claude Code settings files are also protected, including those inside the workspace, and the worktree-switching tools are unavailable while this restriction applies.
- Session plan files, scratch files, background-job files, and the project’s normal auto-memory retain limited exceptions.
- This controls file tools; shell commands, MCP tools, hook programs, and memory tools have separate permissions. Cloud sessions do not apply this setting.


### Analyze the Current Cloud Session With `/insights`

In cloud sessions, `/insights` can now analyze the conversation currently in progress and explain its findings directly in chat. It summarizes what worked, sources of friction, and suggestions to try without pointing you to an inaccessible local HTML report.

```text
/insights
```

Local sessions retain the existing report workflow across saved sessions.


### Batch Streaming JSON Deltas

Command-line integrations can opt into briefly collecting and combining consecutive streaming deltas, reducing the number of JSON lines they need to process.

```bash
CLAUDE_CODE_STREAM_EVENT_HOLD_MS=50 \
claude -p "Explain this repository" \
  --verbose --output-format stream-json --include-partial-messages
```

`CLAUDE_CODE_STREAM_EVENT_HOLD_MS` accepts whole numbers from `1` to `2000` milliseconds. The optional `CLAUDE_CODE_STREAM_EVENT_MAX_LINE_BYTES` limits how large a combined delta line may become; leaving it unset imposes no combining limit. Output retains its existing immediate behavior unless holding is enabled.

## In Development


### Send Work to Claude Projects

A new `/send-to-project` command is implemented behind `tengu_amber_tributary_dotterel`, which defaults to off. It connects local CLI work with a cloud project on `claude.ai/code`.

The default implementation sends one message after showing a confirmation pane. You can supply the message yourself, or have Claude draft a short update from the conversation:

```text
/send-to-project "Billing service" Continue investigating the failing renewal tests.
/send-to-project
```

The command supports choosing a new project or an existing personal project, including selection by quoted name, ID, or link. It requires a Claude account, the first-party provider, and a connected Remote Control session whose conversation can be shared.

An additional mode, behind `tengu_amber_tributary_sandpiper` and also off by default, prepares a fuller handoff: a work summary, proposed instructions, suggested threads and routines, optional GitHub repository attachment, and a brief saved to project memory. Suggested threads remain on a setup card until the user starts them. Cloud-session entry points are still disabled in this build.


### Server-Only Auto Mode Checks

The `tengu_bright_dragonfly` gate introduces selective retirement of Claude Code’s local auto mode checker. Its default is `off`; other gate values select direct connections, broader connections, and optionally subagent handoffs.

When enabled, actions without a covering server verdict can be blocked instead of receiving a local fallback check. New diagnostics explain incompatible gateways, disabled experimental betas, and configurations such as `CLAUDE_CODE_AUTO_MODE_SERVER=0` that prevent the server check from running.


### Response Comparison Preferences

The settings schema now reserves `responseComparisonEnabled` for controlling prompts that show two answers and ask which is better. A corresponding `CLAUDE_CODE_DISABLE_RESPONSE_COMPARISON` environment variable is also declared.

The comparison flow and enforcement of these preferences are not wired into the inspected CLI implementation, so these declarations do not yet establish a usable feature.

## Other Changes

- Changed headless `PermissionRequest` handling to ignore hook approvals for calls that specifically require a person’s approval.
- Changed forwarded-hook handling to refuse execution until the receiving computer has loaded its organization’s managed settings.
- Added an Opus 4.8 fast-mode deprecation warning, with November 30, 2026 as the default announced removal date.
- Improved `/permissions` with a `Recently blocked` view that shows complete call inputs and prevents approval when the input cannot be adequately displayed.
- Improved blocked-call retries requested during an active turn: Claude is told about them at your next prompt.
- Improved MCP approval prompts to explain when `Don't ask again` transfers a server name and its existing permission rules to a different server.
- Improved handling of server-enforced effort caps by retrying at a lower effort and explaining the adjustment without changing your saved preference.
- Improved `/effort` status messages to distinguish `auto` from an explicitly selected effort level and show the current automatic value.
- Improved cloud and Remote Control connections with automatic long-poll fallback when repeated SSE connections receive no response bytes.
- Improved oversized-conversation recovery by selectively omitting large tool results from compaction requests and identifying what the summary could not see.
- Improved large responses by preserving streaming table structure and falling back to plain code when the syntax-highlighting budget is exhausted.
- Improved organization-required sign-in checks, including clearer refusal messages and preservation of the previous login when a replacement sign-in is rejected.
- Fixed MCP calls failing when another call’s authentication reconnect closed their connection; affected calls retry once on the replacement connection.
- Fixed MCP authentication recovery repeatedly sending a rejected stored access token when no refresh token is available.
- Fixed `claude mcp logout` and in-session sign-out reporting success when the credential store could not be read or cleared.
- Fixed TLS certificate handling for certain system-store cross-certificate loops while preserving certificates explicitly supplied through `NODE_EXTRA_CA_CERTS`.
- Fixed downloaded message attachments overwriting files already present at their destination; conflicting files are preserved and alternate saved paths are reported.
- Fixed artifact sharing accepting approval data that lacks the share-card recipient list or conflicts between organization-wide and individual sharing.

## Notes

Headless workflows that depend on `PermissionRequest` hooks may now stop on calls requiring personal approval. Run those steps in an interactive session where the approval can be shown.

With `permissions.blockWritesOutsideWorkingDirectories` enabled, use `/add-dir` to expand the writable scope. Settings-file edits must be made outside Claude’s file tools while the restriction is active.

Streaming JSON consumers that enable delta holding should accept larger combined deltas and up to the configured holding delay; event boundaries need not match the previous one-delta-per-line output.


Generated by `harness-investigations@47fd98f-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: astdiff, strings, module sources
