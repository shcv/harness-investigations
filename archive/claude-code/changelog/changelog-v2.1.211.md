# Changelog for version 2.1.211

## Summary

This release introduces `RefreshMcpTools`, a new built-in tool that lets Claude re-sync MCP server tool lists without restarting, and a `--forward-subagent-text` flag for surfacing subagent messages in stream-json output. It also overhauls the Claude Design durable write grant system, fixes macOS terminal bell handling, and adds Windows Registry-based browser detection for Claude in Chrome.

## New Features


### RefreshMcpTools Built-in Tool

What: A new native Claude Code tool that re-queries connected MCP servers and updates the live tool list, reporting exactly which tools were added or removed per server.

Details:
- Available automatically whenever any MCP server is connected
- Refresh all servers at once or target a single server by name
- Returns per-server status: `refreshed`, `error`, or `not_connected`
- Reports `toolCount`, `added`, and `removed` tool name arrays per server
- Useful when a device or app was opened after Claude Code started (missed the initial tool announcement) or when a server's connection recovered and its tools look stale
- This tool never dials new connections — it only re-reads the list over an existing connection

Usage:
```
RefreshMcpTools                          # refresh all connected servers
RefreshMcpTools({ server: "myserver" })  # refresh one specific server
```

Evidence: tool name constant `"RefreshMcpTools"`, description text (search for `"Re-queries the tool list of connected MCP servers"`)


### `--forward-subagent-text` CLI Flag

What: Streams subagent text and thinking blocks back to the caller as `assistant`/`user` messages with `parent_tool_use_id` set, allowing the host process to observe subagent reasoning in real time.

Usage:
```bash
claude --print --output-format=stream-json --forward-subagent-text ...
```

Details:
- Requires both `--print` and `--output-format=stream-json`; passing the flag without those two will produce an error
- Intended for programmatic callers that orchestrate subagents and need live insight into what a subagent is doing before it finishes

Evidence: flag string (search for `"--forward-subagent-text"`)


### `CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS` Environment Variable

What: Controls whether Claude Code will attempt to resume an interrupted turn when a session restarts unexpectedly (e.g. after a process crash or SIGKILL).

Usage:
```bash
# Resume only turns interrupted within the last 10 minutes
export CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS=600000

# Disable interrupted-turn resumption entirely
export CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS=0
```

Details:
- When not set, interrupted turns are not automatically resumed (opt-in behavior)
- Set to a positive number of milliseconds to enable: turns older than this value are skipped
- Set to `0` to explicitly disable resumption even if the variable is present
- When resumption fires, Claude sees: "Continue from where you left off. Note: this session was automatically restarted after its process exited unexpectedly; the user has not sent a new message since the restart. Re-verify anything time-sensitive."

Evidence: function reads `process.env.CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS` (search for `"CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS"`)

## Improvements


### Claude Design: Durable Per-Project Write Grants

The project-scope authorization model for Claude Design was overhauled. Instead of a 4-hour session grant, writes are now governed by durable grants tied to the project, revocable at any time from `claude.ai/design` settings.

Details:
- `finalize_plan scope:"project"` is no longer supported — Claude will instruct you to write directly (the first write triggers the approval flow)
- The first write to a project pops a one-time approval dialog; after approval, all future writes to that project proceed without prompting
- Durable grants survive session restarts and process restarts
- Grants are revocable per-project at `claude.ai/design`
- Projects shared from another organization cannot hold durable grants; those still use the per-batch plan flow
- The new `/v1/design/grants` API endpoint backs this system

Evidence: approval text (search for `"first write under a project grant — approval mints a durable write grant for this project, revocable at claude.ai/design settings"`)


### macOS Terminal: Disable Audible Bell (Corrected)

Claude Code's macOS Terminal.app setup previously switched to a "visual bell," which left audio still potentially active in some contexts. It now properly disables the audible bell outright (skipped if screen-reader mode is active, which relies on the bell for feedback).

Details:
- Screen-reader mode: bell setting is left unchanged
- New status messages distinguish: "Disabled the audible bell", "Left the audible bell setting unchanged (screen-reader mode uses it)", "No Terminal.app changes needed."
- Better failure messages if Terminal.app profiles cannot be updated

Evidence: new status string (search for `"Disabled the audible bell"`)


### Windows: Registry-Based Browser Detection for Claude in Chrome

On Windows, Claude in Chrome now consults the Windows Registry `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths` and `HKLM` equivalent to locate browser executables (Chrome, Edge, Vivaldi), rather than relying solely on `rundll32 url,OpenURL`.

Details:
- Resolves `chrome.exe`, `msedge.exe`, `vivaldi.exe` via App Paths registry before falling back to `rundll32`
- Handles environment variable expansion in registry path values (`%ProgramFiles%`, etc.)
- Skips candidates that resolve to directories or match the `WindowsApps` sparse-package directory with unusual stat results
- Falls back gracefully to `rundll32` if App Paths lookup fails or times out

Evidence: registry key string (search for `"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths"`)


### New "Server Temporarily Limiting Requests" Rate-Limit Message

A new server-side throttle message distinguishes Anthropic API server rate limiting from a user's own usage credit exhaustion.

Details:
- Old behavior: server throttling was surfaced through the same messaging as usage limits, causing confusion
- New message: "Server is temporarily limiting requests (not your usage limit)"
- Appears when the server responds with a 529 or equivalent overload signal unrelated to the account's credit balance

Evidence: new message string (search for `"Server is temporarily limiting requests (not your usage limit)"`)


### Screenshot Save-to-Disk: Dedicated Temp Directory and Better Errors

The `save_to_disk` option for screenshot tools (Claude in Chrome) now routes images through a dedicated secure temp directory under `/tmp/claude-chrome-screenshots-*` and provides clearer per-failure messages.

Details:
- Screenshots saved to the temp dir include the path in the tool result: "Screenshot saved to: /tmp/claude-chrome-screenshots-.../screenshot-*.png"
- If the directory cannot be created: "Note: save_to_disk failed — the screenshot directory could not be created. The image is included inline above."
- If `save_to_disk` has no effect (not configured for this session): "Note: save_to_disk had no effect — screenshots are not persisted to disk in this session."
- If at least one image fails to write: individual failure note; successfully saved images still include paths
- Directory is ownership-verified before use (uid check) and falls back to a new temp dir if validation fails

Evidence: prefix string (search for `"Screenshot saved to: "`)


### Claude in Chrome File Upload Security Hardening

File uploads via the Claude in Chrome bridge now perform stricter pre-upload validation.

Details:
- Non-regular files (sockets, devices, FIFOs) are rejected: `": not a regular file."`
- Files with multiple hard links are rejected — hard links can alias a file outside the session's allowed directories (common with Bun/pnpm `node_modules` store): `": the file has multiple hard links..."`
- Total upload size is checked against a per-call limit
- Path is re-validated after lstat to catch TOCTOU races: `": path moved during validation."`
- File is checked to not have grown between stat and read: `": file grew during read."`
- Only files the session is permitted to read can be uploaded
- Network paths and suspicious Windows path patterns are rejected
- Added support for PowerPoint (`application/vnd.ms-powerpoint`) and TSV (`text/tab-separated-values`) MIME types

Evidence: error string (search for `"the file has multiple hard links, which can alias"`)


### OAuth Refresh Lock: Compromise Detection and Longer Stale Threshold

The distributed lock guarding OAuth token refreshes now exposes a compromise signal and uses a longer stale threshold to avoid false contention errors.

Details:
- Lock stale timeout raised from 10,000 ms to 60,000 ms
- New `update` interval of 5,000 ms keeps the lock file timestamp fresh under long refreshes
- Lock now returns an `isCompromised()` predicate and an AbortController signal; callers can abort in-flight refresh work if the lock is compromised
- A new `OAuthRefreshLockContendedError` is thrown (with that name visible in error messages) when the legacy lock is already held by another process

Evidence: error class name (search for `"OAuthRefreshLockContendedError"`)


### `--callback-port` Range Validation

The MCP OAuth callback port flag now validates the value is an integer within [1, 65535].

Details:
- Old error: "Error: --callback-port must be a positive integer"
- New error: "Error: --callback-port must be an integer in [1, 65535]"
- Port 0 (which was accepted before) is no longer valid

Evidence: new error text (search for `"--callback-port must be an integer in [1, 65535]"`)


### Consent Store Canonicalization: Ownership Verification

Before resolving `localSettings` to the canonical git root path, Claude Code now verifies that the root directory, its `.git` entry, and its `.claude` entry are all owned by the current user.

Details:
- Prevents a symlink-based escalation where a repo root symlinks to a directory owned by another user, which could cause consent settings from that directory to apply
- Logs a warning and keeps the session cwd as the consent store if ownership verification fails
- On platforms without uid semantics (Windows), canonicalization is skipped with a warning
- On POSIX, if `realpath` of the home directory is unavailable, canonicalization is skipped

Evidence: warning text (search for `"localSettings: not canonicalizing the consent store"`)


### JetBrains Plugin Docs URL Updated

The "No available IDEs detected" message now links to `https://code.claude.com/docs/en/jetbrains` instead of the old `https://docs.claude.com/s/claude-code-jetbrains`.

Evidence: new URL (search for `"https://code.claude.com/docs/en/jetbrains"`)


### Browser Tool Error Classification

Chrome bridge tool errors are now classified into structured error types (e.g. `js_timeout`, `tab_not_found`, `computer_action_failed`, `navigation_blocked`) for better telemetry and error reporting to Claude.

Evidence: error type constant (search for `"tab_not_found"` in the context of bridge error classification)


### Agent Subagent Guidance Improvements

The system prompt guidance for agents managing background subagents was tightened with explicit anti-fabrication rules.

Details:
- New rule: "Don't race: after launching a background agent, you know nothing about its results. Never fabricate or predict them in any format — not as prose, summary, or structured output."
- New reminder: "Trust but verify: an agent's summary describes what it intended to do, not necessarily what it did. When an agent writes or edits code, check the actual changes before reporting the work as done."

Evidence: guidance string (search for `"Don't race: after launching a background agent"`)


### Auto-Inject Tab Context for Chrome Navigate

When calling `navigate` without a `tabId`, Claude in Chrome now automatically queries `tabs_context_mcp` in the background and injects the resolved tab ID before the navigate call.

Details:
- `url: "back"` and `url: "forward"` still require an explicit `tabId` (error if omitted)
- If the hidden lookup exceeds a timeout, a clear error is returned: "The hidden tabs_context_mcp lookup did not respond within Xs. The Chrome extension may be slow to start or waiting on a permission prompt."
- The resolved tab context is appended to the tool result for transparency

Evidence: error text (search for `"The hidden tabs_context_mcp lookup did not respond within"`)

## Bug Fixes

- `--callback-port` accepted out-of-range values (e.g. port 0 or ports above 65535) as valid; now rejects them with a clear range error (search for `"must be an integer in [1, 65535]"`)
- macOS Terminal.app setup reported "Switched to visual bell" but did not fully disable the audible bell in all configurations; now correctly disables it (search for `"Disabled the audible bell"`)

## In Development

Features with infrastructure added but not yet enabled for all users.


### Org Memory Writes [In Development]

What: Allows Claude to write back to the organization-wide shared memory store (not just read from it), making memory updates durable across all sessions for the org.

Status: Feature-flagged — requires `tengu_silk_ledger` server flag to be enabled

Details:
- New `/config` toggle: "Org memory writes (enable reads first)" — only offered when org memory reads are already on
- When enabled for a directory, a note is appended to writes: "Note: org-memory writes are enabled for this directory (the 'Org memory writes' /config setting), so this file syncs to the org-wide shared memory store."
- Writes are blocked if the org policy is read-only, if the session identity can't be verified, or if memory reads are disabled
- The `orgMemoryWritesAccount` field ties the write grant to a specific account

Evidence: feature flag (search for `"tengu_silk_ledger"`), config string (search for `"Org memory writes (enable reads first)"`)


### PR Footer Surface Suffix [In Development]

What: Appends the invocation surface to the "🤖 Generated with Claude Code" footer in pull requests — e.g. "via GitHub Actions", "via Claude Tag in Slack", "via Claude Tag in Teams".

Status: Feature-flagged — requires `tengu_pr_footer_surface_suffix` server flag

Details:
- Supported surfaces: GitHub Actions, Claude Tag in Slack, Claude Tag in Teams, Claude Desktop, Mobile, Cowork
- When running from a surface not in the list (standard CLI), the footer is unchanged
- Lets teams trace which automation surface opened a PR at a glance

Evidence: feature flag (search for `"tengu_pr_footer_surface_suffix"`)


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.211.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.211.txt`
