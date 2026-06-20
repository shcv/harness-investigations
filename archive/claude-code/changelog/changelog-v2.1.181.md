# Changelog for version 2.1.181

## Summary

This release ships archive-based skill delivery via MCP servers, a new `/design` hub command for Claude Design, and a `/config key=value` shorthand for setting configuration inline. Accessibility gets a dedicated `--ax-screen-reader` flag, non-interactive `--cloud` dispatch is now supported, and write safety is strengthened with size-verification and better atomic-write fallback handling.

## New Features


### Archive Skills via MCP Servers

MCP servers can now serve skills packaged as compressed archives (`.tar.gz` or `.zip`). Claude Code downloads the archive, validates it, extracts it to a content-hash-addressed cache directory, and loads the embedded `SKILL.md` just like any other skill.

Details:
- Supported formats: tar.gz (native parser, no external tools) and zip
- Security validation: symlinks, hardlinks, and path-traversal entries are rejected; archives are size-limited (200 MB uncompressed); entry counts are capped
- Digest verification: if the MCP index declares a SHA-256 digest, it is checked against the downloaded content
- Caching: extracted archives are stored by content hash and reused across sessions
- MCP-sourced skills cannot declare hooks or allowed-tools (those frontmatter fields are ignored)
- Archives must be rooted at `SKILL.md`, not `my-skill/SKILL.md`

Evidence: tar archive parser (search for `"tar archive contains a link entry"`), cache layer (search for `"mcp-skill-archives"`), download flow (search for `"Downloading skill archive from"`)


### `/design` Hub Command

New slash command that unifies access to Claude Design (`claude.ai/design`). Instead of bundling static instructions, the command fetches live guidance from the `get_claude_design_prompt` MCP tool each time, so the behavior stays current as Claude Design evolves.

Usage:
```
/design [sync|login|import|export|status|<free-form prompt>]
```

Subcommand dispatch:
- `sync` → `/design-sync` (push local design system to claude.ai/design)
- `login` → `/design-login` (authorize design access)
- `import <project-id-or-url>` → fetches project files into the working directory
- `export [name]` → pushes working directory into a new Claude Design project, returns the URL
- `status` → shows which design system is default and whether you're authorized
- Free-form prompt → calls `get_claude_design_prompt` and executes your brief

If the Claude Design MCP server is not connected, `/design` tells you to run `/design login` (or add the MCP server) and stops.

Evidence: hub command registration (search for `"Work with Claude Design (claude.ai/design)"`)


### `/config key=value` Inline Shorthand

You can now set boolean and enum settings directly from the `/config` command without opening the full panel.

Usage:
```
/config key=value
/config key=value key2=value2
```

Examples:
```
/config thinking=true
/config verbose=true verbose=false
```

Details:
- Boolean settings accept `true`, `false`, `1`, `0`, `on`, `off`, `yes`, `no`
- Enum settings accept any valid option (case-insensitive)
- Consent-gated and managed-enum settings (model, theme, output-style) redirect you to their dedicated commands
- Unrecognized keys print a helpful "isn't a /config setting" message with a prompt to run `/config` to see what's available
- Running `/config true` or `/config false` alone prints the full list of settable keys with their types

Evidence: shorthand handler (search for `"tengu_config_shorthand"`), error messages (search for `"isn't a /config setting"`, `"Run /config to open settings, or /config key=value to set one directly"`)


### `--ax-screen-reader` Accessibility Flag

New flag that switches Claude Code into a screen-reader-friendly rendering mode: flat text output, no decorative borders, no animations.

Usage:
```bash
claude --ax-screen-reader
```

Three ways to enable it:
1. CLI flag: `--ax-screen-reader`
2. Environment variable: `CLAUDE_AX_SCREEN_READER=1`
3. Settings key: `axScreenReader: true` (in `~/.claude/settings.json`)

When active, Claude Code prints `[Accessible screen reader mode: on]` at startup. The classic (non-TUI) renderer is always used in this mode regardless of the `tui` setting.

Evidence: mode manager class (search for `"CLAUDE_AX_SCREEN_READER"`), CLI flag registration (search for `"--ax-screen-reader"`), startup message (search for `"[Accessible screen reader mode: on]"`)


### Non-Interactive `--cloud <session_id>` Message Dispatch

You can now send a single message to an existing cloud session without starting an interactive session. Previously `--cloud <session_id>` only supported interactive attachment.

Usage:
```bash
claude --cloud <session_id> "Your message here"
echo "message" | claude --cloud <session_id>
```

JSON output mode:
```bash
claude --cloud <session_id> --output-format json "message"
# → {"ok": true, "session_id": "...", "url": "..."}
```

Details:
- Requires a prompt via positional argument or stdin
- Exits after the message is dispatched (does not stream the response)
- Returns the session URL for reference
- Archived sessions return an error immediately
- `--output-format stream-json` is not supported in this mode

Evidence: headless dispatch path (search for `"Error: non-interactive --cloud <session_id> requires a prompt"`, `"Sent to cloud session."`)


### `/powerup` Discovery Banner

New users see a contextual banner announcing the `/powerup` interactive tutorial: "New here? Type /powerup for a 5-minute tour — modes, undo, @-mentions, and how to teach Claude your rules."

A complementary inline message says: "Quick lessons on the things power users do — plan mode, undo, subagents, memory. About 5 minutes. Come back any time with /powerup."

The banner is controlled by the `tengu_birch_lantern` feature flag and is part of a gradual rollout. Users who have already seen it won't see it again.

Evidence: discovery component (search for `"tengu_powerup_discovery_shown"`), banner text (search for `"New here? Type /powerup for a 5-minute tour"`)

## Improvements


### Write Verification Against Silent Truncation

After writing a file, Claude Code now checks that the on-disk file size matches the number of bytes that were written. If there is a mismatch, the write is flagged as failed with an explicit message:

> Write verification failed: `/path/to/file` is N bytes on disk, expected M. The filesystem may have silently truncated the write (network drive / cloud sync).

This catches a class of corruption that was previously invisible — cloud-synced directories, network drives, and some virtual filesystems can silently drop the end of a write.

Evidence: verification check (search for `"writeTextContent: on-disk size mismatch after write"`)


### Atomic Write Fallback Robustness

The atomic file write path now handles two more failure modes gracefully:

- `fchmod` failures on filesystems that don't support permission changes (EXFAT, some network shares) are logged as warnings instead of causing the write to fail
- `fsync` failures on filesystems that don't support fsync are similarly downgraded to warnings

When the rename-into-place step fails, the fallback in-place write now correctly handles `EACCES` errors that occur after the target file was already truncated. Content is preserved at the temporary path and the error message tells you where to find it.

Evidence: permission-flag check (search for `"fchmod unsupported on this filesystem"`, `"fsync unsupported on this filesystem"`), fallback messages (search for `"writeFileSyncAndFlush: in-place fallback write failed; content preserved at temp path"`)


### Read Tool Parameter Descriptions Clarified

The `offset` and `limit` parameters for the Read tool now carry more specific descriptions visible in the model's tool schema:

- `offset`: "Negative offsets are not supported (use `tail -N` / `Get-Content -Tail N` to read the end of a file)."
- `limit`: "Must be > 0; omit limit to read to end of file."

The platform-appropriate command (`tail -N` on POSIX, `Get-Content -Tail N` on Windows) is chosen at runtime.

Evidence: parameter description update (search for `"Negative offsets are not supported"`, `"Must be > 0; omit limit to read to end of file"`)


### Schema Hint After Repeated Validation Failures

When a tool call fails JSON schema validation multiple times in a row, the model now receives the full JSON schema alongside the error:

> This call has now failed validation N times in a row. The `<tool>` tool's input schema is: `{...}`. Match the parameter names and types exactly on the next attempt.

This helps the model self-correct without requiring user intervention.

Evidence: repeated-failure handler (search for `"This call has now failed validation"`, `"Match the parameter names and types exactly on the next attempt"`)


### UNC Path Detection in Read and Glob

New defense-in-depth check: if Claude requests a read or glob against a UNC path (`\\server\share\...`) or a UNC-style glob, the permission dialog is always shown with a note that the path may access network resources. This is a Windows-specific protection applied regardless of allowed-paths configuration.

Evidence: UNC check (search for `"UNC glob pattern detected (defense-in-depth check)"`, `"UNC path detected (defense-in-depth check)"`)


### Bedrock/Vertex Cross-Tier Opus Fallback Messaging

When Opus is unavailable on Amazon Bedrock or Google Vertex and a different-tier model is substituted, the notification now includes upgrade guidance:

- Bedrock: "… using [model]. Enable [model] in the Bedrock console to upgrade."
- Vertex: "… using [model]. Enable [model] in Model Garden to upgrade."

Same-tier fallbacks (e.g., Sonnet → Sonnet-v2) retain the existing "for this session" message.

Evidence: cross-tier branch (search for `"in the Bedrock console to upgrade"`, `"in Model Garden to upgrade"`)


### CCR Client `after_event_id` Resilience

The cloud relay client now distinguishes between two failure modes when its stored event ID is rejected by the server:

- Gate off: "rejected by server (gate off)"
- Stale anchor: "not found (stale anchor)"

In both cases the client automatically refetches from the beginning of available history rather than stopping. This prevents sessions from getting stuck when the server's event window has moved past the stored anchor.

Evidence: retry logic (search for `"CCRClient: after_event_id"`, `"refetching without anchor"`)


### MCP Policy Cold-Start Observability

Two new debug log messages make it clearer why MCP tools may not appear immediately on session start:

- `[mcp-policy-cold-start] skipped — no MCP server source visible`
- `[mcp-policy-cold-start] waiting on remote managed-settings load`

Evidence: policy startup messages (search for `"[mcp-policy-cold-start] skipped"`, `"[mcp-policy-cold-start] waiting"`)


### Away Summary Skipped When Loop Wakeup Is Pending

If an `await`-loop wakeup is already scheduled, the away summary generation is now skipped with a log line `[awaySummary] skipped: loop wakeup pending`. This avoids redundant processing when the session is about to wake up on its own.

Evidence: skip condition (search for `"[awaySummary] skipped: loop wakeup pending"`)


### REPL Inner Tool Call Watchdog

The REPL tool executor now sets a watchdog timer on in-progress inner tool calls. If a tool exceeds the configured deadline, the session is aborted and an error is reported:

> REPL inner tool call `<tool>` exceeded Nms watchdog (native timeout M). The call may be hung — try a shorter timeout on the tool itself.

Evidence: watchdog telemetry (search for `"tengu_repl_inner_watchdog_fired"`, `"REPL inner tool call"`)


### GitHub Actions Sandbox: Git Worktree Support

The GitHub Actions sandbox now pre-creates the filesystem paths needed for git worktrees: `.git/config.worktree`, `.git/commondir`, and `.git/worktrees`. Repos that use `git worktree` will work correctly inside the CI sandbox.

Evidence: worktree stub creation (search for `"/.git/config.worktree"`, `"/.git/commondir"`)

## Bug Fixes

- **Control characters in Bash commands**: Commands that contain non-printable control characters (which would be invisible in the approval dialog) are now always flagged rather than auto-allowed. (Search for `"command contains control characters that would be hidden in the approval dialog"`)

- **PowerShell symlink creation**: `New-Item -ItemType SymbolicLink/Junction/HardLink` commands now always show the permission dialog. The error message was simplified from "Compound command creates a filesystem link…" to "Command creates a filesystem link…" to cover the non-compound case as well. (Search for `"Command creates a filesystem link (New-Item -ItemType SymbolicLink/Junction/HardLink)"`)

- **CCR tail incoherence**: When the local session tail is incoherent with the server's view, the client now detects this and refetches the full transcript rather than appending in the wrong position. (Search for `"Failed to refetch full read after incoherent local tail"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.181.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.181.txt`
