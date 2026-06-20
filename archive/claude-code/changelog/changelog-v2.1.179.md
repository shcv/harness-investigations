# Changelog for version 2.1.179

## Summary

This release hardens plugin security with SHA pin verification enforced at install time, overhauls the teammate UI by removing the in-process preview panel in favor of per-agent spinner state, and improves shell analysis safety for zsh glob and `-m/+m` flag patterns. Connection error messages are now more specific, worktree exit gracefully recovers when the original directory is gone, and artifact share-mode display is significantly improved.


## New Features


### Plugin SHA Commit Pin Verification

What: Plugin installations now verify that the checked-out commit matches the declared SHA pin, refusing to complete if there is a mismatch.

Details:
- After checking out a pinned commit, Claude Code runs `git rev-parse HEAD` and compares it to the expected SHA
- If the HEAD does not match, installation aborts with a clear error
- Applies to both plugin clone and plugin update operations
- Protects against renamed refs or upstream resets that could silently land the wrong code

Evidence: SHA verification gate (search for `"SHA pin verification failed: expected HEAD to be"` and `"plugin SHA pin verification failed"`)


### Claude-Session Attribution in Remote Git Commits

What: When running in remote mode, Claude Code now appends a `Claude-Session: <session-id>` trailer to git commit messages and PR descriptions it creates, so each commit is traceable back to the session that produced it.

Details:
- Appears as `Claude-Session: <id>` in commit trailers and as an appended line in PR bodies
- Only active when `CLAUDE_CODE_ENTRYPOINT` is remote
- Opt out with `CLAUDE_CODE_SUPPRESS_SESSION_ATTRIBUTION=1`
- Has no effect in local interactive sessions

Evidence: Session attribution injector (search for `"Claude-Session:"` and `"CLAUDE_CODE_SUPPRESS_SESSION_ATTRIBUTION"`)


### AltGr Key Handling on Windows Terminal

What: A new environment variable `CLAUDE_CODE_ALTGR_AS_TEXT` controls how the AltGr key is interpreted when using Claude Code in Windows Terminal.

Details:
- Set `CLAUDE_CODE_ALTGR_AS_TEXT=true` to always treat AltGr+letter as a text character (useful for European keyboard layouts)
- Set `CLAUDE_CODE_ALTGR_AS_TEXT=false` to disable AltGr-as-text entirely
- Default is `auto`: AltGr-as-text is active when the `WT_SESSION` environment variable is set (Windows Terminal is detected)
- Resolves issues where AltGr combinations (e.g. AltGr+E for `€`) were misinterpreted as Ctrl+Meta shortcuts

Evidence: AltGr detector (search for `"CLAUDE_CODE_ALTGR_AS_TEXT"`)


### OTEL Diagnostic Logging to Stderr

What: A new `CLAUDE_CODE_OTEL_DIAG_STDERR` environment variable enables OpenTelemetry diagnostic messages to be printed to stderr, useful when debugging third-party OTEL integrations.

Details:
- When set, OTEL SDK internal diagnostic errors are forwarded to stderr with the prefix `"[3P telemetry] OTEL diag error:"`
- Intended for users and operators diagnosing OTEL pipeline issues

Evidence: OTEL diag stderr routing (search for `"CLAUDE_CODE_OTEL_DIAG_STDERR"`)


## Improvements


### Worktree Exit: Graceful CWD Recovery

What: When leaving a worktree (`ExitWorktree`) whose original directory no longer exists on disk, the session now recovers to a valid fallback directory instead of erroring.

Details:
- Fallback order: the worktree path itself → home directory → current directory
- Recovery is logged: `ExitWorktree: original directory "…" no longer exists; session cwd recovered to "…"`
- If the fallback ended up being the worktree itself (not the original directory), the session message warns: `Consider restarting Claude from an existing directory.`
- Worktree cleanup `chdir` errors are now caught and logged rather than propagating as uncaught exceptions

Evidence: Recovery logic (search for `"no longer exists; session cwd recovered to"` and `"Consider restarting Claude from an existing directory."`)


### Clearer Connection Error Messages

What: Three distinct error messages now appear when the API connection is interrupted mid-response, replacing a generic failure.

Details:
- `": Connection closed mid-response. The response above may be incomplete."` — when the stream cuts off after at least one content block was yielded
- `": Connection closed while thinking, before producing a response. Try again."` — when the connection drops during the thinking phase before any output
- `": Connection to the API was lost (…)"` — for other mid-stream disconnections
- `"block(s) yielded — finalizing partial response"` appears in logs when a partial response is being finalized

Evidence: Connection error strings (search for `"Connection closed mid-response"` and `"Connection closed while thinking"`)


### Artifact Share-Mode Display Improvements

What: The display text for shared artifacts is now specific about who can see them, rather than always showing a generic "shared" label.

Details:
- `"on claude.ai (viewers see updates immediately)"` — for live-shared artifacts
- `"a page on claude.ai (viewers see a pinned earlier version)"` — for pinned share
- `"a page shared with specific users"` — when shared with selected users
- `"a page shared with your organization"` — when shared org-wide
- `"a private page on claude.ai"` — when not shared
- `"a page on claude.ai (share status could not be confirmed)"` — on probe failure

Evidence: Share-mode resolver (search for `"specific users"` and `"your organization"`)


### Auto Mode Classifier Now Always Fails Closed

What: When the auto-mode permission classifier is unavailable (e.g. network timeout), Claude Code now denies the action with retry guidance instead of silently falling through to normal permission prompting.

Details:
- Previously: classifier unavailable → fall back to standard permission handling (fail open)
- Now: classifier unavailable → deny with "Auto mode classifier unavailable, denying with retry guidance (fail closed)" and prompt the user to retry
- This is a security posture change: unavailability no longer grants implicit permission

Evidence: Classifier fail-closed path (removed string `"Auto mode classifier unavailable, falling back to normal permission handling (fail open)"`)


### Zsh Shell Analysis: -m/+m Flags and Glob Patterns

What: The static shell analyzer now correctly rejects zsh `declare`/`typeset` commands with `-m` or `+m` flags as too complex to model safely, and detects glob metacharacters `*`, `?`, and `[` as needing dynamic evaluation.

Details:
- `declare -m pattern`, `typeset +m pattern`, and similar pattern-assign forms are flagged: `zsh -m/+m pattern-assigns every matching variable; cannot statically model target set`
- Applies in both the direct command path and the wrapped/quoted path
- Glob characters `*`, `?`, `[` in unquoted word positions are now treated as complex expressions requiring dynamic execution context
- Four new zsh read-only variables added to the known set: `PPID`, `ARGC`, `ZSH_SUBSHELL`, `TTYIDLE`, `status`

Evidence: zsh flag handler (search for `"zsh -m/+m pattern-assigns every matching variable"`)


### Bash NUL Redirection: Skip Complex Commands

What: The NUL-redirector replacement (`/dev/null` normalization) now skips commands that contain shell expansions or backticks, avoiding incorrect transformations.

Details:
- Previously the replacer ran on all commands containing `NUL` (case-insensitive)
- Now commands containing `<`, `$`, or `` ` `` are passed through unchanged
- Prevents false-positive rewrites in commands like `echo "NUL"` or `$(cmd > NUL)`

Evidence: NUL redirect guard (search for `"$1/dev/null"` near the new condition)


### MCP Tool Display Names via Annotations

What: Tool calls from MCP servers are now displayed using the human-readable title from `tool.annotations.title` when the server provides one, rather than the raw wire name.

Details:
- The display name is stored in a new `tool_use_meta` array on each assistant message
- If the server provides `tool.annotations.title`, that value is used as `display_name`
- The MCP server's own display name appears as `server_display_name`
- Blocks whose display label equals the wire name (built-in tools) are omitted from the metadata to keep payloads small

Evidence: Tool display name extractor (search for `"display_name"` in the `tool_use_meta` schema description: `"@internal Display metadata for this message's tool_use blocks"`)


### Fable 5 Model Consent: Clearer Fallback Messages

What: When Fable 5 (claude-fable-5) cannot be activated because usage-credit consent was not granted, the session now falls back gracefully with clear status messages.

Details:
- A new `model_consent_fallback` system message is emitted when the consent gate swaps the session off the requested model, recording the `choice`, `original_model`, `fallback_model`, and whether the fallback was saved as the new default
- In the model picker, a Fable 5 model that requires consent but cannot be set for a teammate shows: `"Fable 5 needs usage-credits consent — /model to set up"`
- The status line shows `"· this session only — /model to set up"` when running Fable without full consent
- The previous terse message `"· Fable 5 requires usage credits · /model to change"` is replaced with clearer per-context text

Evidence: Consent fallback message type (search for `"model_consent_fallback"` and `"Fable 5 needs usage-credits consent"`)


### Teammate Mode Default Changed to In-Process

What: The default value for the `teammateMode` setting is now `"in-process"` instead of `"auto"`.

Details:
- Previously the default was `"auto"`, which could select tmux or in-process depending on environment
- Now the default is explicitly `"in-process"`
- This affects new installs and installs where `teammateMode` has never been explicitly set

Evidence: Default constant (search for `"in-process"` in teammate mode snapshot)


### Model Picker: Last-Used Tracking and Reset Option

What: The model picker now tracks when each model was last used and shows a "Not used recently" indicator, and a new "Reset model to the workspace default" option appears in the picker.

Details:
- Models not used in the current session show `"· Last used: …"` or `"· not used in …"` as context
- Models with no recent use show `"Not used recently"`
- A reset option is available to return to the workspace-configured default model

Evidence: Last-use tracker (search for `"Not used recently"` and `"Reset model to the workspace default"`)


### HIPAA Mode: Restricted Features Notice

What: In HIPAA-restricted environments, a status indicator `"HIPAA · some features are restricted"` now appears with a reference to `/status for details`.

Details:
- The `/status` command can be used to see which features are unavailable in the current environment
- This follows the existing pattern of environment-specific restrictions (e.g. BYOK, network policies)

Evidence: HIPAA indicator (search for `"HIPAA · some features are restricted"` and `"· /status for details"`)


### Plugin Download: Stall and Size Detection

What: The streaming plugin download path now independently detects stalled downloads and oversized plugin zips, rather than relying only on the buffered path for these checks.

Details:
- A per-chunk timeout resets on each received byte; if no data arrives within the timeout, the download is aborted with `"plugin download stream stalled"`
- A running byte counter aborts the download if the total exceeds the cap, emitting `"plugin zip exceeds download byte cap"`
- Applies to the streaming download code path (used when `CLAUDE_CODE_SYNC_PLUGINS_BUFFERED_DOWNLOAD` is not set)

Evidence: Streaming download guard (search for `"plugin download stream stalled"` and `"plugin zip exceeds download byte cap"`)


### Content Truncation Indicator

What: When a list of items is too large to include in full in a prompt, a trailing entry `"… and N more (truncated for prompt size)"` is appended instead of silently dropping items.

Evidence: Truncation message (search for `"more (truncated for prompt size)"`)


### Git Safe Flags Additions

What: Three additional `git` flags are now recognized as safe to pass without sandboxing: `--help`, `-h`, and `--shallow-file`.

Evidence: Git safe flags list (search for `"--shallow-file"` near `"--bare"`)


### PowerShell: Get-EventLog Removed from Safe Commands

What: `Get-EventLog` has been removed from the PowerShell safe-command allowlist.

Details:
- `Get-EventLog` is deprecated in PowerShell 7+ (replaced by `Get-WinEvent`)
- Removing it from the safe list prevents silent acceptance of a cmdlet that may not behave predictably across PowerShell versions

Evidence: PowerShell safe-flags table (search for `"get-winevent"` — `get-eventlog` entry is now absent)


### Remote Agent Environment Variable Propagation

What: When Claude Code spawns a child agent process in remote mode, it now forwards the relevant environment variables (previously it forwarded an empty set).

Details:
- The `ULH()` environment helper is now called when building the child process environment for remote agent spawns
- Fixes cases where agents spawned in remote environments didn't receive required configuration

Evidence: Remote spawn env (search for `"CLAUDE_AGENTS_SELECT"` near the env object change)


## Bug Fixes

- Worktree cleanup: `process.chdir()` errors during worktree deletion are now caught and logged rather than thrown, preventing silent crashes when the working directory changes mid-cleanup (search for `"Could not chdir to original directory while cleaning up worktree"`)

- Spinner state is now tracked per-agent rather than in a global singleton, preventing one agent's compaction/thinking state from overwriting another's display (search for `"isCompacting"` in the new per-agent controller `K3H`)

- Machine ID is now generated and persisted on first startup via `aO8()`, ensuring telemetry and identification are stable across sessions (search for `"getOrCreateMachineID: could not persist machineID"`)

- Broadcast notifications for completed background tasks now wait for the notification to enqueue within a timeout before exiting, with a logged warning if the deadline expires (search for `"is terminal but its completion notification did not enqueue within"`)

- Terminal cursor movement deltas are now clamped to screen bounds (`[-rows+1, rows-1]`), preventing runaway cursor positioning on tall terminals

- The `showSpinnerTree` key is now removed from stored settings during migration to prevent stale configuration (search for `"showSpinnerTree"` in the migration function)


## In Development


### Claude Design MCP Server [In Development]

What: Infrastructure for a built-in first-party MCP server called `claude_design` has been added, pointing to `https://api.anthropic.com/v1/design/mcp`.

Status: Feature-flagged — controlled by `tengu_omelette_whisk`. Also overridable via `CLAUDE_CODE_ENABLE_DESIGN_MCP` environment variable.

Details:
- When enabled, the `claude_design` server is registered as a dynamic-scope built-in MCP server
- The server URL is `https://api.anthropic.com/v1/design/mcp`
- Authentication uses the login OAuth token (auto-attach, first-party)
- The string `"Use Claude Design to mock up screens before you build ·"` was added (replacing the previous `"Designing a UI? Claude Design can mock 5 versions of your screen before you build —"`)
- This suggests Claude Design will be promoted more prominently when the flag is enabled

Evidence: Claude Design MCP registration (search for `"tengu_omelette_whisk"` and `"https://api.anthropic.com/v1/design/mcp"`)


### Precompute Compaction Setting [In Development]

What: A new `precomputeCompactionEnabled` setting will let users control whether the compaction summary is computed in the background before it is needed, reducing the pause when auto-compact triggers.

Status: Feature-flagged — controlled by `tengu_sepia_moth`. Will appear in the Experimental section of `/config` when enabled.

Details:
- The setting defaults to `true` when the flag is on
- Applies only when auto-compact is also enabled
- Described as: `"@internal Precompute the compaction summary in the background before it is needed. Only applies when auto-compact is on."`
- A `"Precompute compaction"` label appears in the settings UI

Evidence: Precompute setting schema (search for `"precomputeCompactionEnabled"` and `"tengu_sepia_moth"`)


### Client-Data Token Budget Table [In Development]

What: Infrastructure for server-driven token budget configuration via client data has been added. Anthropic can push per-window-size budget fractions for both REPL and SDK contexts without a client update.

Status: Feature-flagged — controlled by `tengu_amber_moleskin`. Uses the `rowan_thicket` and `heather_vale` client data keys.

Details:
- The budget table maps context window sizes to `{ repl: fraction, sdk: fraction }` entries
- Fallback entry (`default`) applies when no exact window size matches
- The source is reported as `"clientdata"` in token budget diagnostics (the `/config` display now shows `auto (N tokens)` for `clientdata` source, matching the `experiment` source display)

Evidence: Token budget table resolver (search for `"tengu_amber_moleskin"` and `"table_exact"`)


### Screen Reader Accessibility Mode [In Development]

What: A feature flag `tengu_ax_screen_reader` has been added, suggesting upcoming screen-reader-specific accessibility improvements to the TUI.

Status: Flag defined but no UI behaviour is yet wired to it.

Evidence: Flag constant (search for `"tengu_ax_screen_reader"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.179-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.179.txt`
