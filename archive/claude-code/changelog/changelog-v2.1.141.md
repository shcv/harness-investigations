# Changelog for version 2.1.141

## Summary
Claude Code 2.1.141 is a broad CLI release focused on plugin authoring, remote/background workflows, and supportability. The most visible additions are plugin scaffolding, feedback bundle export, PR babysitting/monitoring support, `claude agents --cwd`, and hook-controlled terminal notifications. Several pieces of Remote Control live preview and plugin evaluation infrastructure are present but not yet enabled.


### Plugin Project Scaffolding
What: Claude Code can now scaffold a local plugin with a `.claude-plugin/plugin.json`, a starter skill, and optional agents, hooks, MCP, and LSP examples.

Usage:
```bash
claude plugin init my-plugin --with agents --with hooks --with mcp --with lsp
```

Details:
- Creates the plugin under the local skills/plugin area so it can auto-load in the next session.
- Adds a plugin schema reference, starter `SKILL.md`, optional `agents/example.md`, optional `hooks/hooks.json`, optional `hooks-handlers/on-session-start.ts`, optional `.mcp.json`, and optional `.lsp.json`.
- Uses `--force` to overwrite existing scaffold files.
- Validates the generated plugin before reporting success.

Evidence: Plugin scaffold writer and success message (search for `"Created plugin \""`, `"https://anthropic.com/claude-code/plugin.schema.json"`, and `"Unknown --with component"`)


### Local Feedback Bundles
What: `/feedback` can now save a redacted support bundle to disk instead of only submitting directly to Anthropic.

Usage:
```bash
/feedback
```

Details:
- When direct feedback submission is unavailable because of provider mode, gateway mode, or missing Anthropic credentials, the flow can save a ZIP bundle locally.
- The bundle contains `feedback.json` with redacted session/debug context.
- Claude Code tells users that nothing leaves the machine until they send the bundle file.
- Bundles are written under the Claude config feedback bundle directory.

Evidence: Feedback bundle export flow (search for `"Feedback bundle saved"`, `"Nothing leaves this machine until you send the bundle file"`, and `"feedback-bundles"`)


### PR Babysitting and Webhook-Backed Monitoring
What: Claude Code can now monitor a GitHub PR in the background, subscribe to CI/review/push webhook events when Remote Control is connected, and fall back to a 30-minute poll cron.

Usage:
```bash
claude
# then ask: babysit this PR until CI passes
```

Details:
- The new PR monitoring prompt checks PR state, mergeability, status checks, and review comments.
- If Remote Control is connected, webhook events arrive as user messages.
- If webhooks are not available, Claude Code registers a 30-minute polling cron as a backstop.
- Existing monitoring jobs are detected so the same PR is not duplicated.

Evidence: PR monitoring task prompt and fallback cron (search for `"Babysit PR"`, `"Webhook events (CI, reviews, pushes) will arrive as user messages"`, and `"Registered a 30-minute poll cron"`)


### Scoped Background Agent View
What: `claude agents` now supports filtering background sessions by working directory.

Usage:
```bash
claude agents --cwd /path/to/project
```

Details:
- The command description now focuses on background agents.
- `--cwd <path>` limits the agent list to sessions started under that path.
- In a TTY, the command can open the fleet/background-agent TUI directly; otherwise it falls back to the non-interactive handler.

Evidence: Agents command option (search for `"Show only background sessions started under <path>"`)


### Hook-Controlled Terminal Notifications
What: Hooks can now return a `terminalSequence` for Claude Code to emit, allowing controlled terminal/title/notification escape sequences.

Usage:
```json
{
  "terminalSequence": "\u001b]9;Build finished\u0007"
}
```

Details:
- Only OSC 0, 1, 2, 9, 99, 777, and BEL are permitted.
- Rejected sequences are dropped and logged rather than blindly emitted.
- This gives hook authors a constrained way to trigger terminal notifications or title updates.

Evidence: Hook result schema and allowlist (search for `"terminalSequence"` and `"only OSC 0/1/2/9/99/777 and BEL are permitted"`)


### Remote Control Mobile/Web Wording
Remote Control help and prompts now consistently describe control from `claude.ai/code` and the Claude mobile app, with clearer language about sessions continuing on the local machine.

Evidence: Remote Control help text (search for `"Control local sessions from claude.ai/code or the Claude mobile app"` and `"The session keeps running on this machine"`)


### Safer Destructive Shell Command Prompts [Gradual Rollout]
Claude Code adds a more specific warning for dangerous commands that target a possibly empty shell-variable path, such as `rm -rf $UNSET/*`, which can expand to a top-level filesystem path. This warning is controlled by the existing `tengu_destructive_command_warning` rollout flag.

Evidence: Dangerous variable-path warning (search for `"e.g. `rm -rf $UNSET/*` becomes `rm -rf /*`"` and `"tengu_destructive_command_warning"`)


### Clearer WorktreeCreate Hook Failures
Worktree hook errors now distinguish between a hook that did not run and a hook that ran but failed to return a worktree path. This should make custom VCS/worktree integrations easier to debug.

Evidence: Worktree hook diagnostics (search for `"WorktreeCreate hook failed: hook is configured but did not run"` and `"hook succeeded but returned no worktree path"`)


### Better WSL Voice Mode Guidance
Voice mode on WSL now gives more actionable guidance: it explains that WSL2 with WSLg provides PulseAudio and recommends installing SoX with PulseAudio support.

Evidence: WSL voice guidance (search for `"WSL2 with WSLg provides audio via PulseAudio"`)


### More Helpful MCP Config Warnings
Invalid MCP config entries now produce explicit `--mcp-config` warnings and plugin MCP URL diagnostics, instead of failing less visibly.

Evidence: MCP config diagnostics (search for `"--mcp-config:"` and `"has an invalid MCP url"`)


## Bug Fixes

- Feedback submission now reports more specific failure reasons and can fall back to a local bundle when direct upload is unavailable. Evidence: feedback availability handling (search for `"/feedback requires Anthropic credentials"` and `"Couldn't save the feedback bundle to disk"`)
- Remote Control session expiry and retry messages are clearer, including a direct `/remote-control` retry hint. Evidence: retry messaging (search for `"Remote Control session expired"` and `"Run /remote-control to retry"`)
- Terminal keybinding installation errors for Alacritty and Zed now include the underlying error message in logs. Evidence: keybinding install diagnostics (search for `"Failed to install Alacritty keybinding"` and `"Failed to install Zed Shift+Enter key binding"`)


## In Development

Features with infrastructure added but not yet enabled. These are shipped "dark" and may become available in future versions.


### Remote Control Live Preview [In Development]
What: Remote Control has new parser support for exposing local preview ports through a live-preview URL while a Remote Control session is running.

Usage:
```bash
claude remote-control --enable-live-preview --preview-port 3000
```

Status: Stubbed/disabled in this build.

Details:
- The parser recognizes `--enable-live-preview` and `--preview-port`.
- It validates preview ports as integers from 1024 to 65535.
- The current build immediately rejects these options with “not available in this build,” so users cannot use live preview yet.

Evidence: Disabled live-preview parser (search for `"--enable-live-preview and --preview-port are not available in this build"` and `"reachable from this session's livepreview URL"`)


### Plugin Trigger Evaluations [In Development]
What: Plugin authors can define `evals/*.md` files with `query` and `should_trigger` frontmatter, and Claude Code can validate and report on those evaluation files.

Usage:
```bash
claude plugin eval ./my-skill
```

Status: Partially implemented; model evaluation is not wired up.

Details:
- The evaluator reads `evals/*.md`, validates YAML frontmatter, and reports missing or invalid eval files.
- It recommends at least five eval queries.
- Trigger tests are currently skipped because model evaluation returns `null`.
- Level 2 interplay tests are explicitly not implemented yet.

Evidence: Plugin eval command and skipped evaluator (search for `"Usage: /plugin eval [path]"`, `"All trigger tests skipped — model evaluation not yet wired up"`, and `"Level 2 — interplay tests: not yet implemented"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.141.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.141.txt`
