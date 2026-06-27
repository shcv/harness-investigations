# Changelog for version 2.1.193

## Summary

This release strengthens enterprise policy controls with a new `disableSideloadFlags` managed setting and adds plugin rename migration support. Safety gets several upgrades: the `&` background operator now requires explicit approval, `su`/`runuser` join the privilege-escalation list, workspace trust is now enforced before applying project permissions, and file-write operations now verify that symlink targets haven't shifted since the permission check. The status bar gains an MCP authentication warning, and the auto-mode classifier gets a `classifyAllShell` option for tighter shell command control.


## New Features


### `disableSideloadFlags` Managed Setting

What: A new managed-settings-only policy that blocks the `--plugin-dir`, `--plugin-url`, `--agents`, and non-SDK `--mcp-config` CLI flags at startup, closing a bypass path around `strictKnownMarketplaces`.

Details:
- Only honored in managed settings; ignored in user, project, or local settings
- Pair with `allowedMcpServers` for per-server MCP control — this setting does not gate SDK-side `setMcpServers`, `claude mcp add`, or `.mcp.json`
- When active, attempts to pass blocked flags produce a clear error message listing which flags are disallowed and pointing to the administrator for resolution

Evidence: Setting description (search for `"When true (and set in managed settings), rejects the --plugin-dir"`)


### Plugin Rename Support in Marketplace Manifests

What: Marketplace manifests can now declare a `renames` field — an append-only map of old plugin name → new name (or `null` when a plugin has been removed). When a plugin is not found under its stored name, Claude Code follows the rename chain and automatically migrates user settings.

Details:
- The loader walks the rename chain up to a configurable depth and resolves cycles safely
- User settings (`enabledPlugins`, `pluginConfigs`) are updated automatically on successful migration
- A warning appears in the notification area if the rename target also can't be found, guiding users to update `enabledPlugins` manually
- Chain errors (cycle, missing target, too-deep chain) each produce a distinct resolution status that is reported in telemetry

Evidence: Rename map description (search for `"Append-only map of old plugin name"`)


### MCP Authentication Status in Status Bar

What: The status bar now shows a warning when one or more MCP servers require authentication, with a hint to run `/mcp` to address it.

Details:
- Appears as "N MCP server(s) need authentication · run /mcp"
- Disappears once all servers are authenticated or removed
- The count updates in real time as MCP connection state changes

Evidence: Status bar entry (search for `"servers need"` alongside `"authentication"` and `"run /mcp"`)


### `classifyAllShell` Auto Mode Option

What: A new `autoMode.classifyAllShell` setting. When `true`, every Bash/PowerShell allow rule is suspended while auto mode is active and all shell commands are routed through the classifier instead.

Details:
- Default is `false` (existing behavior: allow rules apply as normal in auto mode)
- Setting to `true` increases safety at the cost of more classifier calls per shell invocation
- Only effective in auto permission mode

Evidence: Setting description (search for `"When true, every Bash/PowerShell allow rule is suspended while auto mode is active"`)


### `OTEL_LOG_ASSISTANT_RESPONSES` Environment Variable

What: New env var that enables logging of assistant response text via OTEL. When set, assistant response bodies are included in OTEL span attributes (in addition to the existing `OTEL_LOG_USER_PROMPTS` for user prompts).

Details:
- The var is recognized alongside the existing OTEL suite (`OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_CONTENT`, etc.)
- Responses are logged only when the function `dGi()` returns true (checks `OTEL_LOG_ASSISTANT_RESPONSES` OR `OTEL_LOG_USER_PROMPTS`)
- Useful for debugging or auditing full conversation traces in OTEL-connected environments

Evidence: Env var lookup (search for `"OTEL_LOG_ASSISTANT_RESPONSES"`)


### `CLAUDE_CODE_MAX_CONTEXT_TOKENS` Now Applies to Non-Anthropic Models

What: The existing `CLAUDE_CODE_MAX_CONTEXT_TOKENS` env var (previously used only when `DISABLE_COMPACT` was set) now also overrides the context window size for third-party / non-`claude-*` models.

Usage:
```bash
CLAUDE_CODE_MAX_CONTEXT_TOKENS=128000 claude ...
```

Details:
- Takes effect only when the model name does not start with `"claude-"` and the value is a positive integer
- Allows setting a correct context window for locally-hosted or proxy models that don't have their limits registered in Claude Code
- Native Anthropic model limits are still sourced from the model registry and are unaffected

Evidence: Conditional branch (search for `"!to(qo(e)).startsWith(\"claude-\")"`) — `rhi()` at ~line 158685 in new file


### `model_refusal_no_fallback` System Event

What: A new SDK system event subtype is emitted when a model ends a stream with `stop_reason "refusal"` and no fallback model is configured, so the turn ends as an error rather than triggering a retry.

Details:
- Fields: `original_model`, `request_id`, `api_refusal_category`, `api_refusal_explanation`, `refused_user_message_uuid`
- `refused_user_message_uuid` identifies the user message that triggered the refusal — it is the rewind target and composer prefill for edit-and-retry UX
- Distinct from `model_refusal_fallback`, which covers the case where a fallback model was tried
- Absent from older CLIs

Evidence: Event schema description (search for `"Emitted when the model ends the stream with stop_reason \"refusal\" and no fallback model"`)


### `CLAUDE_CODE_DISABLE_NOTIFICATION_PRESENCE_CHECK` Environment Variable

What: New env var that disables the presence check Claude Code performs before sending desktop notifications. Useful in environments where the presence API is unavailable or unreliable.

Evidence: Condition branch (search for `"CLAUDE_CODE_DISABLE_NOTIFICATION_PRESENCE_CHECK"`)


## Improvements


### Background `&` Operator Now Requires Manual Approval

What: Shell commands that include the `&` background operator now trigger a permission prompt even when the rest of the command would normally be auto-allowed. The operator defers execution past approval-time safety checks, so it requires explicit trust.

Details:
- The parse check is applied after all other allow/deny logic
- The message shown: "This command uses the `&` background operator, which defers execution past approval-time safety checks. Approve only if you trust it."
- The classifier cannot auto-approve this; only a human can accept
- Commands with `&` that are already flagged for other reasons (e.g., deny rules) are not double-flagged

Evidence: Safety message (search for `"defers execution past approval-time safety checks"`)


### `su` and `runuser` Recognized as Privilege Escalation

What: `su` and `runuser` are now included in the set of privilege-escalation commands that Claude Code treats with extra care, joining the existing list of `sudo`, `doas`, and `pkexec`.

Evidence: Command set entry (search for `"runuser"` near `"su"` and `"sudo"`)


### Workspace Trust Enforced Before Applying Project Permissions

What: Allow rules and `additionalDirectories` entries sourced from project-scoped settings (`.claude/settings.json`, `.claude/settings.local.json`) are now silently dropped — with a visible error — in workspaces that haven't been trusted via the trust dialog.

Details:
- The error printed to stderr names the affected settings files and explains how to fix it: either run Claude Code interactively in the workspace once and accept the trust dialog, or set `projects[...].hasTrustDialogAccepted: true` in the global config
- Managed-settings-sourced rules are not affected
- The suppressed entries are counted and logged internally for telemetry

Evidence: Error message (search for `"this workspace has not been trusted. Run Claude Code interactively"`)


### Worktree Write Protection Against Symlink Drift

What: File write operations now verify that the parent-directory symlink resolution hasn't changed between when permission was checked and when the write actually executes. If it has shifted, the write is refused.

Details:
- Applies to all file-modifying tools (Write, Edit, NotebookEdit)
- At check time, the resolved paths are stashed keyed by `toolUseId`; at write time the stash is retrieved and compared against a fresh resolution
- If the paths don't match: `"Refusing to write <path>: its parent-directory symlink resolution changed after permission was checked."`
- This closes a TOCTOU window where a symlink swap could redirect a write to an unintended location

Evidence: Error message (search for `"its parent-directory symlink resolution changed after permission was checked"`)


### Worktree `.worktreeinclude` Symlink Escape Protection

What: When copying `.worktreeinclude` entries into a new worktree, entries whose resolved destination escapes the worktree boundary via a committed symlink are now skipped with a warning rather than followed.

Details:
- Applies to directory entries and individual files
- Skipped entries are logged: "Skipping .worktreeinclude entry: destination escapes worktree via committed symlink: ..."
- `settings.local.json` is subject to the same check during worktree setup

Evidence: Warning messages (search for `"destination escapes worktree via committed symlink"`)


### REPL VM Context Poisoning: Automatic Recovery

What: When REPL sandbox code makes a global variable non-configurable (preventing the host from restoring it), Claude Code now automatically resets the REPL context and presents a clear recovery message instead of leaving the session in a broken state.

Details:
- Error class: `VMContextPoisonedError`
- On detection: all timers are cleared, the console is cleared, and a fresh VM context is created
- User message: "The REPL context was reset — rerun your code; global state (variables, registered tools) starts fresh."
- The poisoning is tracked via a `WeakSet` to avoid Proxy-based fake membership attacks on attacker-controlled values

Evidence: Error class and message (search for `"REPL sandbox code made the global"` and `"REPL context was reset"`)


### GitHub Enterprise Server Host Detection Generalized

What: Multiple places that previously compared hostnames literally against `"github.com"` (or `"www.github.com"`) now use a proper URL-normalization-and-comparison function. This makes GitHub Enterprise Server (GHES) instances work more consistently across features including PR linking, `--agent` launch, and marketplace source matching.

Details:
- A new hostname normalizer strips trailing dots and strips leading `www.`
- GHES API base URLs are now computed correctly (`https://<host>/api/v3` vs `https://api.github.com`)
- GraphQL endpoint is similarly computed per host
- SSH remote URLs that use GHE hosts are now handled by the same path as `github.com`

Evidence: Generalized host check (search for `"Em(c.hostname)"` and `"ewr(t.host)"`)


### Desktop Handoff Tips Now Active

What: The three desktop-related tips (run locally, continue in Desktop shortcut, contextual Desktop suggestion) previously had their `isRelevant` functions hardcoded to return `false`. They now evaluate real conditions and can show to eligible users.

Details:
- Tips fire when the desktop handoff feature is available (`S_t()` check: `amf() && Fs("allow_desktop_handoff")`)
- Individual cooldown and enable-flag conditions still apply per tip
- Contextual tip is also gated on a relevance check based on session content

Evidence: Relevance functions (search for `"S_t() && !j$e()"`)


### Destructive Target Scope Analysis for Shell Commands

What: Shell command telemetry now includes a `destructive_target_scope` field indicating whether a potentially destructive command's targets are within the current working directory (`"cwd"`), outside it (`"outside_cwd"`), in a temp directory (`"tmp"`), or ambiguous (`"unknown"`).

Details:
- Applies to both Bash and PowerShell command execution paths
- Scope is determined by parsing shell argument tokens and resolving paths relative to the current directory
- PowerShell `-Path`/`-LiteralPath` parameters and bash redirection targets are both analyzed
- Variables (`$VAR`, `%VAR%`) and subshells (`` `...` ``, `$(...)`) cause the scope to fall back to `"unknown"`
- Common temp directories (`/tmp`, `/var/tmp`, `%TEMP%`, AppData\Local\Temp) resolve to `"tmp"`

Evidence: Parse error string (search for `"destructive-target-scope parse failed"`)


### Memory Pressure-Based Background Shell Reap

What: For background agent sessions (not terminal-attached), Claude Code now listens for OS `"memoryPressure"` events and terminates idle background shell processes that are consuming resources.

Details:
- Only fires when the main loop is not busy and no other background tasks are running
- The session must be non-interactive (no terminal) and `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP` must not be set
- Killed processes are tracked the same as timed-out ones

Evidence: Memory pressure listener (search for `"memoryPressure"` in the shell execution module)


### Session List Status Descriptions Added

What: Each section of the background sessions list (working, blocked, done) now displays a descriptive subtitle explaining what that bucket means.

Details:
- Working: "Sessions Claude is actively working on — they keep running even if you close the terminal"
- Blocked: "Sessions that have a question or need your decision land here"
- Done: "Finished sessions wait here for you to review"

Evidence: Status description map (search for `"Sessions Claude is actively working on"`)


### Autocompact Thrashing: Improved Detection and Messaging

What: The autocompact thrashing detector now tracks `consecutiveRapidRefills` as a dedicated counter and uses a fixed threshold (3 rapid refills in a row) to trip the circuit breaker. The user-facing message is also improved to be a single self-contained string.

Details:
- Previous version split the message across template literal concatenation; now a single constant
- Full message: "Autocompact is thrashing: the context refilled to the limit within 3 turns of the previous compact, 3 times in a row. A file being read or a tool output is likely too large for the context window. Try reading in smaller chunks, or use /clear to start fresh."

Evidence: Message constant (search for `"Autocompact is thrashing: the context refilled to the limit within 3 turns"`)


### Workflow Result Type Safety

What: Workflow results that are functions are now explicitly rejected with a clear error rather than being passed silently to the host where they would fail unexpectedly.

Details:
- Error: `"workflow result cannot be a function"`
- Non-primitive workflow results are also sanitized through the VM boundary walker before passing to the host

Evidence: Error string (search for `"workflow result cannot be a function"`)


### OAuth Profile Validation Tightened

What: OAuth profile fetch results are now only accepted if both `account` and `organization` fields are present. Previously, a profile with only one of these fields would silently populate account state.

Details:
- Affects the initial auth population during CLI startup
- Prevents partial-profile data from causing confusing downstream behavior (e.g., account shown but org policy not loaded)

Evidence: Condition change (search for `"l?.account && l.organization"`)


### Original Directory Fallback When Worktree Directory Is Removed

What: When a working directory no longer exists (e.g., the worktree was deleted externally), Claude Code now walks up to the nearest existing parent directory and changes to it, rather than failing outright.

Details:
- A warning is logged: "Original directory X no longer exists — returned to Y instead"
- The directory change triggers a normal `chdir` event so the rest of the session state updates correctly

Evidence: Warning message (search for `"no longer exists — returned to"`)


### `WireViolationError` for Non-Serializable Agent Wire Values

What: A new error type (`WireViolationError`) is raised when code attempts to pass a non-serializable value across the agent/workflow wire boundary. The error message identifies the violation clearly.

Details:
- Message: "The wire cannot carry this — it must become data (an Input/Event/RPC/Handle) before it can cross the seam."
- Part of broader enforcement of the boundary between agent contexts

Evidence: Error message (search for `"The wire cannot carry this"`)


### File Not Found: Better Suggestions

What: The Read tool's "file not found" error now provides a smarter suggestion message. For HTML, HTM, and Markdown files, it checks for a corresponding compiled/source file and suggests it by name.

Evidence: Error handler (search for `"File not found.*Did you mean"` in the new version's Read tool handler)


## Bug Fixes

- Shell redirection safety: commands with `>` and `>>` redirections that target denied paths are now blocked with a `"deny"` decision even when the redirection is inside an `if` or compound block. Previously, only top-level redirections were consistently checked. (search for `"denyCheckOutputRedirections"`)
- `--mcp-debug` flag removed: the previously deprecated flag (replaced by `--debug`) no longer appears in the CLI's accepted-flag list and will now be rejected at startup rather than silently ignored. (search for removed `"--mcp-debug"` entry in the flags array)
- Zsh brace expansion in the shell parser no longer incorrectly produces an `"expansion"` node when `zshBraceDiff` mismatch is detected — it now correctly falls back to `"ERROR"`, preventing false-positive safe classifications. (search for `"e.zshBraceDiff"`)
- Image format errors (`"Failed to decode image:"`, `"Failed to guess image format:"`, `"Unable to determine image format"`) are now recognized as expected error strings and handled gracefully rather than being treated as unknown errors. (search for `"Failed to decode image:"`)
- MCP tool-not-found errors now carry a `telemetryMessage` for accurate classification in error tracking, distinguishing MCP tool errors from internal ones. (search for `"Tool not found"` alongside `"telemetryMessage"`)
- Background shell timeout cap is now correctly computed per-invocation rather than using a stale closure value. (search for `"Pgl(i)"` in the shell background handler)


Generated with:
- tool: `harness-investigations@0c752ef-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.193.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.193.txt`
