# Changelog for version 2.1.163

## Summary

This release introduces enterprise version-pinning controls that let organizations enforce exact Claude Code version ranges, along with OAuth 401 recovery for remote sessions and expanded file type support in browser automation. The plugin system gains filtering options, better MCP reload warnings, and LSP conflict detection. Cowork app users get a new built-in plugin authoring skill.


## New Features


### Organization-Enforced Version Bounds

What: Enterprise administrators can now pin a required minimum and/or maximum Claude Code version in managed policy settings. If the running version falls outside the allowed range, Claude Code exits at startup with a clear message explaining what to do.

Details:
- `requiredMinimumVersion`: If the running version is older than this, Claude Code exits with: "Claude Code {version} is older than the minimum version required by your organization ({version}). Update Claude Code using your organization's approved method…"
- `requiredMaximumVersion`: If the running version is newer than this, Claude Code exits with: "Claude Code {version} is newer than the maximum version allowed by your organization ({version})… `claude install <version>` may also work."
- Both settings are only enforced from managed (policy) settings — users cannot set them on their own to restrict themselves.
- These complement the existing user-level `minimumVersion` (prevents accidental downgrades). The new settings enforce hard bounds from IT/security policy.
- The startup check is skipped for `update`, `install`, and `doctor` commands so you can still recover.

Evidence: Version enforcement logic (search for `"is older than the minimum version required by your organization"` or `"requiredMaximumVersion '"`); schema entries (search for `"Minimum Claude Code version required to start"` and `"Maximum Claude Code version allowed to start"`)


### OAuth 401 Recovery for Remote Sessions

What: When a remote Claude Code session receives an OAuth 401 (expired/rotated token), the CLI can now wait for a fresh token and automatically resume instead of crashing.

Details:
- `CLAUDE_CODE_OAUTH_401_WAIT_MS`: How long (in ms) to poll for a new token after a 401. Defaults to 60000 (60 seconds) in remote sessions, 0 elsewhere.
- `CLAUDE_CODE_AUTH_FAIL_EXIT_MS`: If the 401 goes unrecovered for this many milliseconds (default: 600000 = 10 min), the session exits with: "OAuth 401 unrecovered past CLAUDE_CODE_AUTH_FAIL_EXIT_MS — exiting so the runner recycles this session with fresh credentials".
- Also adds dead-token disk cleanup: when a cached OAuth token is known to be dead, it is now cleared from disk so the next session starts fresh.

Evidence: Token poller (`BuK()`, searches for `"OAuth 401 recovery: waiting up to"`); exit logic (`DcH()`, searches for `"CLAUDE_CODE_AUTH_FAIL_EXIT_MS"`); dead-token cleanup (search for `"OAuth dead-token disk clear failed"`)


### Expanded File Type Support in Browser Automation

What: The browser tool (Claude in Chrome) can now handle a significantly wider range of file types when using file upload elements on web pages.

New types added:
- Images: HEIC, HEIF, AVIF, TIFF/TIF, ICO
- Video: M4V, QuickTime MOV, AVI, MKV/Matroska
- Audio: FLAC

These were already supported: PNG, JPEG, GIF, WebP, SVG, BMP, MP4, WebM, MP3, M4A, WAV, OGG, AAC, PDF, and most document types.

Evidence: MIME type map expansion (search for `"image/heic"`, `"video/quicktime"`, `"audio/flac"`)


### Plugin LSP Extension Conflict Detection

What: When two installed plugins both declare an LSP server for the same file extension, Claude Code now detects the conflict and emits a warning rather than silently using one arbitrarily.

Details:
- The conflict message includes which plugin "won" (the first one registered) and which triggered the conflict.
- Helps plugin authors and users diagnose unexpected language server behavior.

Evidence: Conflict detection in plugin loading (search for `"already registered a server for that extension"`)


### `/plugin list` Filtering Flags

What: The `/plugin list` command now accepts `--enabled` and `--disabled` flags to filter the output.

Usage:
```
/plugin list --enabled    # show only enabled plugins
/plugin list --disabled   # show only disabled plugins
/plugin list              # show all plugins (unchanged behavior)
```

Details:
- When no changes are pending, each plugin shows its status: `✓ enabled` or `✗ disabled`.
- If a plugin's status was recently changed but `/reload-plugins` hasn't been run, the output now notes "— run /reload-plugins to apply".
- Plugin output now includes version information alongside the scope.

Evidence: Filter logic and messages (search for `"Only show enabled plugins"`, `"/plugin list [--enabled|--disabled]"`)


### `/reload-plugins` Cache Impact Warning

What: When reloading plugins would add or remove MCP servers (changing the available tool set), Claude Code now warns you before invalidating the conversation cache.

Details:
- If a reload would change MCP tools, you'll see: "This reload changes MCP tools (…) — your next message will re-read the whole conversation instead of using the cache. Run /reload-plugins --force to apply."
- Use `/reload-plugins --force` to apply immediately without the warning.
- This avoids a surprise performance hit on long conversations.

Evidence: Cache impact warning (search for `"the whole conversation instead of using the cache. Run /reload-plugins --force to apply"`)


### Cowork Plugin Authoring Skill

What: A new built-in skill (`cowork-plugin`) is available in Claude Cowork (Anthropic's desktop app) to help users create new plugins or customize existing ones for their organization.

Details:
- Guides users through a five-phase conversation: discovery, component planning, design/clarifying questions, implementation, and review.
- Supports creating skills, agents, hooks, and MCP server integrations.
- Can customize existing plugins with `~~`-prefixed placeholder replacement (e.g., swapping generic `~~project tracker` with `Asana`).
- Automatically searches for matching MCP connectors and presents connection buttons.
- Packages the result as a `.plugin` file delivered directly in the chat.
- Only available when running inside Claude Cowork (`CLAUDE_CODE_ENTRYPOINT=remote_cowork`).

Evidence: Skill registration (search for `"Create a new Cowork plugin from scratch"` or `"cowork-plugin"`)


### Workflow Script: More Unsupported Syntax Detected

What: Workflow scripts now detect and clearly reject additional JavaScript syntax that cannot work across the workflow VM boundary.

New error messages:
- `'await using' declarations are not supported in workflow scripts.`
- `'with' statements are not supported in workflow scripts.`
- `import() is not available in workflow scripts.`

Details:
- Previously these constructs would fail silently or with a confusing runtime error.
- Array length validation across the VM boundary now also catches non-safe-integer lengths and arrays exceeding the maximum size, with descriptive errors.

Evidence: Syntax restriction messages (search for `"'await using' declarations are not supported in workflow scripts"`); boundary safety (search for `"array length is not a safe integer across the workflow VM boundary"`)


## Improvements


### SubagentStop Hook Gains `additionalContext` Support

What: The `SubagentStop` hook event now supports a `hookSpecificOutput.additionalContext` field, matching the behavior of the `Stop` hook. Feedback in this field is delivered back to the subagent so it can continue and act on it.

Details:
- Previously, `SubagentStop` hooks could block or approve but had no way to inject feedback that the subagent would see.
- Now you can return additional context from a `SubagentStop` hook and the subagent will receive it and continue running.
- The schema description: "additionalContext is non-error feedback delivered to the subagent; the subagent continues so it can act on it."

Evidence: Updated hook output schema (search for `"Hook-specific output for the SubagentStop event"`)


### Improved MCP Disconnected Server Notification

What: When one or more MCP servers fail to connect, the status area now shows a structured tree of which servers failed and why, instead of a generic warning.

Details:
- New message format: "MCP server(s) not connected — run /mcp to authenticate, retry, or see details:" followed by a tree listing each failed server with its status (needs authentication, config issue, or failed).
- This replaces the previous single-line warning.

Evidence: New notification component (search for `"MCP server(s) not connected — run /mcp to authenticate, retry, or see details:"`)


### Memory Store `promptIndex` Field

What: Memory store entries now support a `promptIndex` field that points to a file. Claude Code fetches this file and injects its contents into the system prompt when the memory store is active.

Details:
- This is a new configuration option in `CLAUDE_MEMORY_STORES` for providing a per-store prompt index that's injected at each session start.
- Useful for team memory setups where different mount points need different prompt preambles.

Evidence: Fetch logic for promptIndex files (search for `"promptIndex fetch for"`, `"memory-prompt-index["`)


### Updated Command Descriptions

Several commands have clearer, more concise descriptions in `/help` and tooltips:

- "Configure the Advisor Tool to consult a stronger model for guidance at key moments during a task" → "Let Claude consult a stronger model at key moments"
- "Configure the default remote environment for teleport sessions" → "Choose the default environment for cloud agents"
- "Edit Claude memory files" → "Open a memory file in your editor"
- "List and manage background tasks" → "View and manage everything running in the background"
- "List, create, and delete recurring loops and stop-hooks" → "List, create, and delete loops"
- "Open config panel" → "Open settings"
- "Open or create your keybindings configuration file" → "Open your keyboard shortcuts file"
- "Setup Claude Code on the web (requires connecting your GitHub account)" → "Set up Claude Code on the web with your GitHub account"
- "Toggle focus view (show only your prompt, a tool summary, and the final response)" → "Toggle focus view: just your prompt, summary, and response"


### `fetchSession` Error Now Shows Actual Retry Count

What: The remote session fetch error message previously hardcoded "10 times in a row" but now shows the actual retry count.

Evidence: Dynamic count in error message (search for `"fetchSession failed"` in the added strings vs `"fetchSession failed 10 times in a row"` in removed)


## In Development

Features with infrastructure added but not yet enabled for most users.


### Settings Panel with Categories [In Development]

What: The `/config` settings panel is being reorganized into labeled categories for easier navigation.

Status: Feature-flagged (`tengu_maple_sundial`)

Details:
- When the flag is enabled, settings are grouped into: "Appearance", "Model & output", "Display", "Input & controls", "Connections", "Advanced", "Experimental", "Internal".
- The `/vim` and `/output-style` slash commands will redirect to `/config` (with a note that they've moved there).
- Not visible to most users until the flag rolls out.

Evidence: Category definitions (search for `"Model & output"`, `"Input & controls"`, `"tengu_maple_sundial"`)


### Command Kind Lanes in Slash Menu [In Development]

What: The slash command menu is being reorganized into visual "lanes" grouping commands by kind: config, action, info, and agent.

Status: Feature-flagged (`tengu_mint_lanes`, or opt-in via `CLAUDE_CODE_ENABLE_MENU_KIND_LANES=1`)

Details:
- All built-in commands have been categorized: "config" (e.g., `/model`, `/permissions`), "action" (e.g., `/clear`, `/compact`), "info" (e.g., `/context`, `/version`), "agent" (e.g., `/ultraplan`, `/bugfix`).
- The lane labels appear as visual separators in the menu.
- Plugin-sourced commands are tagged with their origin (project, org, etc.).

Evidence: Command kind map (search for `"advisor"` in the action type object that lists `"config"`, `"action"`, `"info"`, `"agent"` values); lane flag (search for `"tengu_mint_lanes"`)


### Velvet Falcon Model [In Development]

What: Infrastructure for a new model variant (internally called "Velvet Falcon") is being added.

Status: Feature-flagged (`tengu_velvet_falcon_model`), or env var `CLAUDE_CODE_VELVET_FALCON`

Details:
- The feature flag or env var enables routing certain requests to the Velvet Falcon model ID.
- No user-visible behavior is currently activated.

Evidence: Model detection functions (search for `"tengu_velvet_falcon_model"`, `"CLAUDE_CODE_VELVET_FALCON"`)

---

Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.163.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.163.txt`
