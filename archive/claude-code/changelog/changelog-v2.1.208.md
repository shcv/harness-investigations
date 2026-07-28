# Changelog for version 2.1.208

## Summary

This release introduces `CLAUDE_CODE_PROCESS_WRAPPER`, a new environment variable for wrapping Claude Code sessions with a custom launcher process, and a new Linux sandbox violation monitor that streams seccomp events for policy auditing. It also adds several defensive hardening changes: null byte protection for ripgrep, a line-range size guard for the Read tool, new Bedrock content-type detection, and improved error reporting throughout. The markdown artifact viewer gains proper dark mode support, and the plan artifact template fixes its dark-mode toggle. MCP archive skill delivery (tar.gz/zip skills fetched from MCP server resources) has been fully removed.


## New Features


### CLAUDE_CODE_PROCESS_WRAPPER

What: A new environment variable that routes all Claude Code session spawns (background sessions, daemon-launched sessions) through a custom launcher binary.

Usage:
```bash
# String form — space-separated argv list, or JSON array
CLAUDE_CODE_PROCESS_WRAPPER="/usr/local/bin/my-launcher --arg" claude

# JSON array form
CLAUDE_CODE_PROCESS_WRAPPER='["/usr/local/bin/my-launcher","--arg"]' claude
```

Details:
- The launcher must be an absolute path to an executable file; bare names resolved via PATH are rejected.
- The launcher must exec into Claude Code (`exec` contract) — it must not daemonize.
- Setting it to Claude Code's own path is detected and rejected with a clear error.
- Shell metacharacters (`;`, `|`, `&`, `$`, `(`, `)`, `` ` ``, `<`, `>`) are not allowed in the string form; use JSON array form for arguments that contain spaces.
- Project-scoped settings (`.claude/settings.json`, `.claude/settings.local.json`) cannot configure this variable; it must be set in `~/.claude/settings.json` or managed settings.
- `/status` output now includes the active wrapper path, whether the daemon is aligned with it, and whether the launcher binary is currently executable.
- On Windows, the variable is accepted but ignored (sessions run unwrapped), with a warning.

Evidence: New `CLAUDE_CODE_PROCESS_WRAPPER` env var constant (search for `"CLAUDE_CODE_PROCESS_WRAPPER"`) — `n4` at line ~286393; the parser `Csg()` at line ~286334 handles both string and JSON-array forms.


### Linux Sandbox Violation Monitor

What: A Unix domain socket-based monitor that captures filesystem write violations from the Linux sandbox (seccomp/observe filter) and streams them for policy telemetry.

Details:
- Launched automatically when a Linux sandbox session starts; a log line `Started Linux seccomp violation monitor` confirms it.
- Connects to the sandbox supervisor via a socket in a temp directory; if the supervisor is unavailable, logs `[Sandbox Linux Monitor] observe socket missing` and continues.
- Violations are filtered against the session's allowed/denied write paths, and per-path ignore patterns specified in `ignoreViolations` can suppress known-benign writes.
- The monitor's socket path is exposed to the sandbox runtime so violations route back to the session.
- Errors during setup log `[Sandbox Linux Monitor] listen failed: <msg> - violation monitoring disabled` and degrade gracefully.

Evidence: New `cBc()` violation monitor function (search for `"[Sandbox Linux Monitor] stopping"`) — at line ~220360; new constant `"Started Linux seccomp violation monitor"` at line ~184.


### Bedrock Content-Type Guard

What: Claude Code now validates that Bedrock streaming responses arrive with the expected `application/vnd.amazon.eventstream` content-type and warns when a gateway or proxy is rewriting the body.

Details:
- If the content-type is wrong, the error names the type received and explains that a gateway is transforming the event-stream format, which would otherwise produce silent corruption.
- The guard can be suppressed with `CLAUDE_CODE_DISABLE_BEDROCK_CONTENT_TYPE_GUARD=1` as a temporary workaround while a gateway is fixed.

Evidence: New `BedrockUnexpectedContentTypeError` class with `code = "BedrockUnexpectedContentType"` (search for `"BedrockUnexpectedContentType"`) — at line ~171876; new env var `CLAUDE_CODE_DISABLE_BEDROCK_CONTENT_TYPE_GUARD` at line ~50497.


## Improvements


### Read Tool Line-Range Size Guard

What: The Read tool now rejects requests whose selected line range contains more data than the tool can return, producing an actionable error message instead of silently truncating or erroring out.

Details:
- The new `SelectedRangeTooLargeError` fires when the byte count of the requested range exceeds the read limit.
- The error message suggests using a smaller limit, or switching to content search if a single line is extremely large.

Evidence: New error message `"The requested line range contains over"` (search for `"The requested line range contains over"`) — at line ~617989; new `SelectedRangeTooLargeError` class registered in the error registry at line ~523713.


### Ripgrep Null Byte and Usage-Error Handling

What: Two new defensive classes harden the Grep tool against injection and confusing failures.

Details:
- `RipgrepNullByteError`: if any of the session CWD, the target path, or any argument to ripgrep contains a null byte (`\0`), the spawn is blocked with a message identifying which argument is tainted.
- `RipgrepUsageError`: when ripgrep exits non-zero with a usage error (bad pattern, invalid glob, unsupported file type), the tool now returns a structured error with the stderr message, rather than bubbling an unrecognized failure.

Evidence: New null-byte check function `U3c()` (search for `"ripgrep spawn blocked: null byte in argv"`) — at line ~231193; new `RipgrepUsageError` class (search for `"ripgrep usage error (input rejected, stderr redacted)"`) — at line ~231513.


### Markdown Artifact Viewer Dark Mode

What: The rendered Markdown HTML page (opened via the Artifact viewer or `claude artifact`) now fully supports light and dark modes.

Details:
- Previously the stylesheet was hard-coded to `color-scheme: light` with fixed RGBA values.
- The new stylesheet uses CSS custom properties (`--md-bg`, `--md-text`, `--md-muted`, etc.) and includes both a light default set and dark overrides under `@media (prefers-color-scheme: dark)`.
- The `data-theme` root attribute override is also respected, so explicit light/dark toggles work without relying on the OS setting.
- Print styles revert to the light palette.

Evidence: New CSS token constants `Hkd` (dark palette) and `xkd` (light palette) (search for `"--md-bg:#0d0d0d"`) — at line ~569984; new stylesheet variable `LDy` at line ~8668 includes `@media (prefers-color-scheme:dark)`.


### Mermaid Renderer Improvements

What: The in-page mermaid diagram renderer gains several reliability improvements.

Details:
- Uses `data-claude-mermaid-claimed` attribute to mark already-processed `<pre class="mermaid">` elements, preventing double-rendering when the renderer fires again on the same page.
- Now watches for `data-theme` attribute changes on `<html>` via `MutationObserver` and re-renders diagrams when the theme toggles (previously only `prefers-color-scheme` media query was observed).
- Skips re-initializing mermaid and re-rendering when the color key (dark/light + background color) is unchanged since the last render.
- Adds `darkMode`, `rowOdd`, `rowEven`, `attributeBackgroundColorOdd`, and `attributeBackgroundColorEven` to the mermaid `themeVariables` for proper table and attribute styling in dark mode.

Evidence: New attribute `data-claude-mermaid-claimed` in `CDy()` mermaid runtime function (search for `"data-claude-mermaid-claimed"`) — at line ~8488; `MutationObserver` on `data-theme` at line ~8555.


### Plan Artifact Dark-Mode Toggle Fix

What: Published plan artifacts now correctly follow the viewer's dark/light toggle instead of only responding to the OS preference.

Details:
- The CDS token block in the plan template uses `[data-mode="dark"]` selectors for its dark overrides.
- The viewer toggle stamps `data-theme` on `<html>`, not `data-mode`.
- A new inline script mirrors `data-theme` → `data-mode` on every attribute change via `MutationObserver`, so the CDS tokens now serve both axes (OS preference and explicit toggle).
- Without JavaScript the OS-level `prefers-color-scheme` CSS axis still themes the page.

Evidence: New `<script>` block in plan template that mirrors `data-theme` to `data-mode` (search for `"data-mode"` near `"data-theme"` in `tRs`) — at line ~8729.


### Windows Sandbox binShell Object Form

What: The `binShell` sandbox setting on Windows now accepts an object form `{"exe": "...", "args": [...]}` in addition to the existing string tokens.

Details:
- The object form allows specifying any arbitrary executable with a custom prefix-args array, useful for unconventional shell wrappers.
- The `exe` field must be an absolute path; `args` must be an array.
- The old error message only mentioned `bash.exe/sh.exe` as valid absolute-path targets; the new parser also explicitly supports `pwsh.exe` and `powershell.exe` absolute paths.
- A new `windows.srtWin.path` setting lets administrators point at a custom `srt-win.exe` binary. If the path is set but the file does not exist, a clear error is thrown at startup rather than failing silently later.

Evidence: New `jOi()` binShell parser (search for `"binShell.exe must be an absolute path"`) — at line ~220466; new `$Ze()` for `windows.srtWin.path` (search for `"windows.srtWin.path is set to'"`) — at line ~220548.


### Credential Mask `onExtractNoMatch` Option

What: The `credentials.envVars` `extract` regex field now exposes an `onExtractNoMatch` option that controls what happens when the extraction pattern matches nothing in the variable's value.

Details:
- `"warn"` (default): logs a warning and passes the variable through unprotected into the sandbox. The existing behavior.
- `"deny"`: unsets the variable entirely rather than exposing it unprotected.
- `"error"`: throws at session start, forcing the operator to fix the configuration.
- The warning message now explicitly says the variable is "left UNPROTECTED (visible as-is inside the sandbox)" to clarify the security implication.

Evidence: New `RFc()` credential masking function with `onExtractNoMatch` handling (search for `"onExtractNoMatch: \"error\""`) — at line ~218862.


### Background Session Command Restrictions

What: Interactive commands that open UI panels now produce specific error messages when invoked in a background (non-TTY) session rather than failing silently or with a generic error.

Details:
- `/login` in a background session: "Can't run /login in a background session — log in from a regular interactive terminal (`claude`), then respawn this job."
- `/install-github-app` in a background session: "Can't run /install-github-app in a background session — run it from an interactive terminal."
- MCP authentication UI in a background session: "Can't authenticate MCP servers in a background session — run this from an interactive terminal."
- MCP settings panel in a background session: "Can't open MCP settings in a background session — use `/mcp enable|disable|reconnect <server>` to steer, or run /mcp from an interactive terminal to authenticate."
- Model picker in a background session: "Can't open the model picker in a background session — use `/model <name>` to switch this session's model."
- Consent prompts for usage-credit models in a background session: now returns a clear message directing users to run `/model` from an interactive terminal.

Evidence: Search for `"Can't run /login in a background session"` and `"Can't open the model picker in a background session"`.


### GitHub App Check: Distinguish Transient vs Deterministic Failures

What: The GitHub App installation check now distinguishes between failures caused by missing token scope (deterministic, won't succeed on retry) and transient network/service failures (may succeed on retry).

Details:
- "No org UUID found (token lacks user:profile scope — deterministic)" — the token cannot be upgraded without re-auth; callers can skip retries.
- "No org UUID found (profile fetch null — possibly transient)" — a retry is worth attempting.
- The check now also returns `defaultBranch` from the API response, used by the remote session orchestrator to set up branch continuity.

Evidence: New log messages in `lZt()` (search for `"token lacks user:profile scope"`) — at line ~431390.


### Hook Cancellation Diagnostics

What: All hook event types now emit an explicit log message when they are cancelled due to a control stream teardown, instead of silently dying.

Details:
- Messages follow the pattern `"[HookType] hook cancelled (control stream closed)"` for all hook events: PreToolUse, PostToolUse, PostToolBatch, PermissionDenied, PermissionRequest, PostToolUseFailure, UserPromptSubmit, UserPromptExpansion, SessionStart, SubagentStart, TaskCreated, TaskCompleted, Stop, SDK callback, and Setup.
- This makes it easier to distinguish between "hook ran and produced no output" and "hook was never invoked."

Evidence: Search for `"PreToolUse hook cancelled (control stream closed)"` and `"SDK callback hook cancelled (control stream closed)"`.


### Vim INSERT-Mode Key Remaps Setting

What: A new `vimInsertModeKeyRemaps` setting is now documented in the settings schema for users who run Claude Code with `editorMode: "vim"`.

Details:
- Accepts an object mapping two-character key sequences (typed in INSERT mode) to `"<Esc>"` (the only supported target, returning to NORMAL mode).
- Example: `{"jj": "<Esc>"}` makes typing `jj` quickly exit INSERT mode.
- Applies only when `editorMode` is `"vim"`.

Evidence: New `.describe()` string `"Vim INSERT-mode key-sequence remaps"` (search for `"Vim INSERT-mode key-sequence remaps"`) — at line ~68609.


### CCR Default-Branch Guard

What: Remote session (CCR) branch handling gains an explicit guard for the case where a session would work on the repository's default branch.

Details:
- A new `CCR_ON_BRANCH_DEFAULT_GUARD` environment variable (values: `"enforce"`, `"observe"`, `"off"`) controls what happens when the remote session's branch turns out to be the default branch.
- A new `--on-branch` flag for `ccr-session` allows targeting a specific outcome branch by name rather than creating a fresh one.
- In `"observe"` mode the session logs the collision and continues; in `"enforce"` mode it is refused.

Evidence: New env var `CCR_ON_BRANCH_DEFAULT_GUARD` (search for `"CCR_ON_BRANCH_DEFAULT_GUARD"`) — at line ~515497; new `--on-branch` flag reference at line ~515541.


### Git Hooks Disabled for Internal Operations

What: All Claude Code–internal git invocations now pass `-c core.hooksPath=/dev/null -c core.fsmonitor=` to prevent local repository hooks from firing during Claude Code's own git operations.

Details:
- This avoids unexpected side effects (lint-staged, husky, custom hooks) when Claude Code queries branch state, resolves the default branch, or resets worktrees.
- Only affects Claude Code's internal git calls; user-initiated Bash commands are unaffected.

Evidence: New constant array `Qu = ["-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor="]` (search for `"core.hooksPath=/dev/null"`) — at line ~61464.


### Pronoun Default in System Prompt

What: Claude Code's base system prompt now includes an explicit instruction to use they/them pronouns for any person whose pronouns have not been stated.

Details:
- The instruction reads: "When you use a pronoun for someone — the user or anyone else you mention — and their pronouns haven't been stated, use they/them. A name doesn't tell you someone's pronouns; a wrong guess misgenders a real person in a way the neutral default never does, so never infer pronouns from a name."
- Applies to all user-visible text, including visible thinking.

Evidence: New system prompt string (search for `"wrong guess misgenders a real person"`) — at line ~687898.


## Bug Fixes

- Mermaid diagrams no longer render twice when the renderer re-fires on a page that already has rendered diagrams, thanks to a per-element `data-claude-mermaid-claimed` guard (search for `"data-claude-mermaid-claimed"`).

- Worktree resume: when a previously-used worktree's work was fully merged upstream, it is now automatically reset to the current base commit (log: `[worktree] reset resumed worktree … — its previous work was fully upstream`) rather than leaving stale diverged state (search for `"its previous work was fully upstream"`).

- File read/edit conflict: attempting to edit a file that is covered by a `Read` deny rule in the session's permission settings now produces the message "File is covered by a Read deny rule in your permission settings and cannot be edited." rather than an opaque failure (search for `"File is covered by a Read deny rule"`).

- `apiKeyHelper` script failure: a new status banner message "Your apiKeyHelper script is failing · This usually means you need to re-authenticate with your provider · Run /status to see the script's error output" surfaces `apiKeyHelper` errors that were previously silent in the UI (search for `"Your apiKeyHelper script is failing"`).

- `checkGithubAppInstalled` no longer logs a misleading "No org UUID found" message when the profile fetch returns null for reasons unrelated to token scope — the message now correctly distinguishes "possibly transient" from "deterministic" (search for `"token lacks user:profile scope"`).

- Ripgrep invocations with null bytes in arguments are now blocked with a clear error rather than passing the null byte to the child process, which could cause unpredictable behavior (search for `"ripgrep spawn blocked: null byte in argv"`).


## Removed

### MCP Archive Skill Distribution

The MCP archive skill system — which allowed MCP servers to distribute skills as downloadable tar.gz or zip archives fetched from MCP resource URIs — has been entirely removed. This includes:

- Archive download, decompression, and unpacking logic
- Cache layer for extracted archives
- SKILL.md discovery inside archives
- Digest verification and size/entry-count limits
- All related error codes (`skill_mcp_archive_*`)

Skills served from MCP servers via the archive resource mechanism are no longer supported. MCP servers that previously distributed skills this way will no longer load those skills. Direct (inline) MCP skills are unaffected.

Evidence: All tar/zip handling functions removed (search for `"mcp-skill-archive"` — absent from new version); the `"Downloading skill archive from"` progress message is no longer present.


### Auto-Mode Opt-In Dialog

The interactive "Enable auto mode?" dialog — shown on first use with "Yes, enable auto mode" / "No, don't ask again" buttons — has been removed. Auto mode configuration now happens through settings rather than a first-use dialog.

Evidence: Removed strings `"Enable auto mode?"`, `"Yes, enable auto mode"`, `"No, don't ask again"`, `[auto-mode] onSubmit: consent debounce pending`; `showAutoModeOptIn` state no longer exists.


## Notes

Users who relied on MCP archive skill delivery should migrate to direct skill definitions within MCP servers. The archive-based path was an experimental delivery mechanism; direct skills remain fully supported.

The `CLAUDE_CODE_PROCESS_WRAPPER` variable is validated at every session start and cannot be set via project settings — only user or managed settings. If the variable is set but the launcher binary is absent or non-executable, new background sessions refuse to start rather than running unwrapped. Existing sessions served by a daemon that validated the launcher earlier continue uninterrupted.


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.208.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.208.txt`
