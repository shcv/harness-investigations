# Changelog for version 2.1.169

## Summary
This release introduces `--safe-mode`, a new troubleshooting flag that disables all personal customizations while leaving built-in tools and authentication fully functional. It also renames "remote sessions" and "remote agents" to "cloud sessions" and "cloud agents" throughout the UI, and adds a new `disableBundledSkills` setting for stripping out bundled skills without affecting user-created ones.


## New Features


### `--safe-mode` Flag and `CLAUDE_CODE_SAFE_MODE` Environment Variable
What: Start Claude Code with all personal customizations disabled — useful for diagnosing broken configurations, misbehaving hooks, or problematic plugins without having to manually disable each one.

Usage:
```bash
claude --safe-mode
# or
CLAUDE_CODE_SAFE_MODE=1 claude
```

Details:
- Disables: CLAUDE.md, custom skills, plugins, hooks, MCP servers, custom agents, output styles, workflows, custom themes, keybindings, and more
- Keeps working: auth, model selection, built-in tools, permission checks, and all core CLI functionality
- When your organization has managed policy settings, those still apply even in safe mode — managed hooks and policy-sourced settings remain active; user-supplied plugins, skills, CLAUDE.md, and MCP servers do not
- A persistent warning banner appears at the top of the session to remind you safe mode is active
- To exit: remove the `--safe-mode` flag or `unset CLAUDE_CODE_SAFE_MODE` and restart
- The `--agents` CLI flag is silently ignored in safe mode (user-supplied custom agents are disabled)
- `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` is also set automatically when safe mode activates

Evidence: CLI flag registered with description search for `"Start with all customizations (CLAUDE.md, skills, plugins, hooks"`) — `C9()` at line ~3322 (checks env `CLAUDE_CODE_SAFE_MODE` or `--safe-mode` argv)


### `disableBundledSkills` Setting and `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` Environment Variable
What: Strip out all skills and workflows that ship with Claude Code without touching your own `.claude/skills/`, `.claude/commands/`, or installed plugins.

Usage:
```bash
# Via environment variable
CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1 claude

# Via settings.json
{ "disableBundledSkills": true }
```

Details:
- Removes bundled skills and workflows entirely from the model's context
- Built-in slash commands remain typable by humans but are hidden from the model
- Custom plugins, `.claude/skills/`, and `.claude/commands/` directories are completely unaffected
- Equivalent to setting `disableBundledSkills: true` in any settings file

Evidence: New setting with description (search for `"Disable the skills and workflows that ship with Claude Code"`)


### Windows Sandbox Network Isolation via WFP
What: Native network filtering for the Windows sandbox using the Windows Filtering Platform (WFP) via a new `srt-win.exe` helper binary. This brings Windows network isolation up to parity with macOS and Linux.

Usage:
```bash
# One-time install (UAC prompt required)
npx sandbox-runtime windows-install

# Check status
# (internal: srt-win.exe group status / wfp status)
```

Details:
- The `srt-win.exe` binary is now bundled and located automatically; override with `SRT_WIN_PATH` env var
- After install, a logout/login is required so the discriminator group SID enters the Windows token
- New `windows` block in sandbox settings with four fields:
  - `groupName` (default: `"sandbox-runtime-net"`) — must match the group created at install time
  - `groupSid` — use instead of `groupName` when DNS resolution is unreliable (domain groups)
  - `wfpSublayerGuid` — target a custom WFP sublayer if filters were installed by enterprise tooling
  - `proxyPortRange` — `[low, high]` port range for the JS proxies; defaults to `[60080, 60089]` and must match the range passed to `srt-win wfp install --proxy-port-range`
- WFP filter-0 PERMITs all traffic before the discriminator group is in the token, so network is never disrupted during setup
- Shell execution (`cmd.exe` / `pwsh.exe`) is routed through the sandbox group via `srt-win.exe exec`

Evidence: `srt-win.exe` locator (search for `"srt-win.exe not found. Set SRT_WIN_PATH"`) — Windows settings schema (search for `"Windows-specific settings (group, WFP sublayer, proxy port range)"`)


### `allowAppleEvents` Sandbox Option (macOS)
What: New opt-in macOS sandbox flag that permits sandboxed commands to send Apple Events and make Launch Services open requests — needed for `open`, `osascript`, and anything that talks to other apps via AppleScript.

Usage:
```json
{
  "sandbox": {
    "allowAppleEvents": true
  }
}
```

Details:
- Grants `appleevent-send` and `mach-lookup` for `coreservices.appleevents`, `appleevents`, and `quarantine-resolver`
- Security trade-off: removes code-execution isolation from the sandbox — launched apps are not subject to sandbox filesystem or network restrictions, and sandboxed commands can script running apps (subject to TCC automation consent). Only enable if you need `open`/`osascript` to work inside the sandbox
- Default: `false`

Evidence: Sandbox profile section (search for `"Apple Events - opt-in; needed for open/osascript"`) — schema description (search for `"Allow sending Apple Events and Launch Services open requests from the sandbox"`)


## Improvements


### "Remote Session" / "Remote Agent" Renamed to "Cloud Session" / "Cloud Agent"
All user-facing UI text that previously referred to "remote sessions", "remote agents", and "background tasks" now uses "cloud sessions", "cloud agents", and "cloud agents" respectively. The underlying functionality is unchanged; this is purely a terminology update.

Affected strings include status messages, error messages, dialog labels, help text, and QR code prompts. Examples:
- "Remote session active" → "Cloud session active"
- "Remote agents" → "Cloud agents"
- "Background tasks require a GitHub remote" → "Cloud agents require a GitHub remote"
- "Can't archive" → "Can't delete" (for cloud session removal)

Evidence: Extensive string replacements (search for `"Cloud session active"`, `"Cloud agents"`, `"Cloud session details"`)


### MCP Reset-Project-Choices Now Surfaces Specific Failure Reasons
What: When `/mcp reset-project-choices` cannot fully reset stored approvals, it now reports the exact failure reason instead of a generic error.

Details:
- If `~/.claude.json` legacy approvals could not be cleared due to a permissions problem, a specific error is shown
- If `settings.local.json` contains validation warnings that would be lost on rewrite, a specific error is shown directing you to `/doctor` first
- When only part of the reset succeeds (e.g., legacy approvals cleared but local settings untouched), a parenthetical clarifies what was and wasn't reset
- The success message now says "Project-scoped (.mcp.json) server approvals and rejections stored for this project have been reset" (was: a generic confirmation)

Evidence: New error messages (search for `"Error: Failed to reset project choices: legacy approvals"`) — partial success message (search for `"legacy approvals in ~/.claude.json were cleared; local settings were not"`)


### Git Operations No Longer Prompt for Interactive Credentials
What: Claude Code now sets `credential.interactive=false` in the git environment before running git commands (cloning repos for cloud agents, etc.), preventing git from spawning interactive credential dialogs that would block headless sessions.

Details:
- Applies via `GIT_CONFIG_KEY_N` / `GIT_CONFIG_VALUE_N` injection, which stacks on top of any existing `GIT_CONFIG_COUNT` the user may have set
- Affects git invocations inside cloud sessions where interactive prompts cannot be answered

Evidence: New `credential.interactive` git config injection (search for `"credential.interactive"`)


### Remote Settings Load No Longer Times Out During Consent Dialogs
What: Previously, the remote settings loading promise would time out and resolve with stale/empty settings while a consent dialog was showing to the user. Now the timeout is deferred until after the dialog is dismissed.

Details:
- Prevents a race condition where settings would finalize before the user could respond to a consent prompt
- Logged as "Remote settings: Loading promise timeout deferred — consent dialog pending" when deferred

Evidence: Timeout deferral code (search for `"Remote settings: Loading promise timeout deferred — consent dialog pending"`)


### Session Resume Properly Drops Messages Retracted by Refusal Fallback
What: When resuming a saved session that experienced a model refusal with a subsequent model fallback, messages that the fallback mechanism retracted are now filtered out on resume, preventing phantom messages from reappearing.

Details:
- The `model_refusal_fallback` system messages carry a `retractedMessageUuids` list; resume now drops those UUIDs from the loaded transcript
- Telemetry tracks how many messages were dropped via `tengu_resume_retracted_dropped`

Evidence: Resume filter (search for `"model_refusal_fallback"` in the `Bh$` function context) — telemetry event `tengu_resume_retracted_dropped`


### Safe Mode Disables Plugin Hooks (Managed Settings-File Hooks Still Run)
What: Plugin hook registration is now explicitly skipped in safe mode, so plugin-defined pre/post-tool hooks don't execute even if a plugin is somehow still partially loaded.

Details:
- Logs "Safe mode: skipping plugin hook registration" when skipped
- Hooks declared directly in managed settings files (policy-level) continue to run — safe mode targets user customizations, not org policy

Evidence: Guard clause (search for `"Safe mode: skipping plugin hook registration"`)


### /goal Reports Hooks as "Restricted" Rather Than "Disabled"
What: The error message shown when `/goal` cannot run because hooks are turned off now says "restricted" instead of "disabled" to better reflect that the restriction may come from a policy setting rather than a user toggle.

Details:
- Old: `/goal can't run while hooks are disabled (disableAllHooks or allowManagedHooksOnly is set in settings or by policy).`
- New: `/goal can't run while hooks are restricted (disableAllHooks or allowManagedHooksOnly is set in settings or by policy).`

Evidence: String replacement (search for `"/goal can't run while hooks are restricted"`)


### Session Respawn Flag Allowlist Expanded
What: When Claude Code respawns a background job (e.g., a cloud agent session that resumes), more CLI flags are now preserved correctly. Previously, flags like `--chrome`, `--no-chrome`, `--bare`, `--verbose`, `--ide`, `--mcp-debug`, `--brief`, and `--remote-control` / `--rc` could be dropped on respawn.

Details:
- Flags with multiple values (`--allowed-tools`, `--disallowed-tools`, `--mcp-config`, `--betas`, `--add-dir`, `--file`, `--channels`) are now handled with a dedicated multi-value parser
- Non-allowlisted flags are stripped and logged as warnings via "[jobs] stripped non-allowlisted respawnFlags token(s)"
- `CLAUDE_SECURESTORAGE_CONFIG_DIR` is now included in the allowed environment variable passthrough for respawned jobs

Evidence: Allowlist sets (search for `"[jobs] stripped non-allowlisted respawnFlags token"`) — new env passthrough (search for `"CLAUDE_SECURESTORAGE_CONFIG_DIR"`)


### Update Status Messages No Longer Show Unicode Checkmark/X Prefixes
What: Status indicator strings in the update/connection status area have dropped the `✓` and `✗` Unicode prefix characters that could render poorly in some terminals or downstream renderers.

Details:
- "✓ Update installed · Restart to apply" → "Update installed · Restart to apply"
- "✗ Auto-update failed · Run …" → "Auto-update failed · Run …"
- "✓ Enabled and configured" → "Enabled and configured"
- Similar cleanup across connection-error, rejection, and auto-update messages

Evidence: String diff showing removal of Unicode checkmark strings (search for `"Update installed · Restart to apply"`)


### `SendFile` Tool Description Clarifies Filesystem Requirement
What: The description for the `SendFile` tool (used to surface files to the user's phone/notification channel) now explicitly states that files must already exist on the local filesystem and that the tool does not fetch URLs or render content.

Details:
- Added: "Files must already exist on the local filesystem — the tool sends files, it doesn't fetch URLs or render content. When unsure of a path, verify with ls first; absolute paths avoid ambiguity about the working directory."

Evidence: Tool description string (search for `"Files must already exist on the local filesystem — the tool sends files"`)


## Bug Fixes

- Fixed: `deleteCurrentProjectConfigFields` now refuses to write if the re-read config is missing auth that the cache has, preventing accidental auth loss. The fix references issue GH #3117. (search for `"deleteCurrentProjectConfigFields fallback: re-read config is missing auth"`)

- Fixed: Local settings validation errors are now reported separately from global settings errors in `/doctor`, so errors in `settings.local.json` are surfaced independently. (search for `"NMH"` in the local settings error path)

- Fixed: The `SiH()` function (brief transcript mode detection) now correctly reads from `h$()` (local project settings) instead of the old `C$()` path, ensuring `briefTranscript` preference is read from the right source. (search for `"briefTranscript"`)


## In Development

Features with infrastructure added but not yet enabled. These are shipped "dark" and may become available in future versions.


### Refusal Fallback Model System [In Development]
What: When the primary model refuses a request, Claude Code can automatically retry the request on an alternative "fallback" model and offer the user a choice: accept the fallback response or edit their prompt.

Status: Staged rollout — the `@internal` tag on `supportedDialogKinds` documentation is the explicit staged-release gate. SDK consumers must declare `refusal_fallback_prompt` in their `supportedDialogKinds` to receive the dialog; the CLI does not yet do this.

Details:
- New infrastructure: `refusalFallbackModelLatch` state in AppState tracks the current fallback model chain; multiple new functions manage latch set/reset/update
- The server sends a `content_block_start` with `type: "fallback"` when it switches models mid-stream
- A user-facing dialog with kind `refusal_fallback_prompt` asks: "choose: retry on fallback model or edit prompt"
- Discarded (retracted) messages from the original refusal attempt are tracked and removed from the transcript
- When the fallback is suppressed (consumer lacks dialog capability), `tengu_refusal_fallback_suppressed` is emitted
- A "retry on fallback model" banner is shown to users in sessions where it IS active
- The `switchModelsOnFlag` setting (default: enabled) and `D8H()` first-party check gate whether the client-side latch activates

Evidence: Latch infrastructure (search for `"refusalFallbackModelLatch"`) — dialog kind (search for `"refusal_fallback_prompt"`) — staged gate documentation (search for `"The @internal tag is the staged-release gate"`)


### Claude Design Contextual Tip [In Development]
What: A new contextual tip will appear for users who work on frontend/UI code, pointing to claude.ai/design ("Claude Design can mock 5 versions of your screen before you build").

Status: Feature-flagged — gated by `tengu_cedar_plume` server-side flag (default: false).

Details:
- Tip ID: `"claude-design-contextual"`; cooldown 15 sessions
- Only shown on first-party connections to users who have passed the new-user threshold
- UTM tracking: `utm_campaign=tengu_cedar_plume`

Evidence: Tip definition (search for `"https://claude.ai/design?utm_source=claude_code&utm_medium=tip&utm_campaign=tengu_cedar_plume"`)


## Notes

The Vercel and Stripe contextual plugin tips (`/plugin install vercel@...` and `/plugin install stripe@...`) have been removed from the tips rotation. If you relied on these as discoverability hints, they will no longer appear.

The terminology change from "remote session/agent" to "cloud session/agent" is cosmetic only — no underlying API or configuration changes. Scripts or integrations that parse UI strings may need updating if they match on these labels.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.169-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.169.txt`
