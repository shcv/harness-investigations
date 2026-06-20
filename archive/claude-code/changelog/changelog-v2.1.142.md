# Changelog for version 2.1.142

## Summary
Claude Code 2.1.142 focuses on multi-surface workflows: browser automation can now distinguish between multiple connected Chrome extensions, agent view can launch background sessions with default model/effort/permission settings, and remote/cloud sessions gain better file delivery and media-failure recovery. Plugin handling also gets more explicit: local skills can load as plugins, project plugin server components are blocked with actionable warnings, and plugin catalog metadata now comes from a richer catalog cache.

### Browser Selection Tools
What: Claude Code can now list connected Chrome extension instances and select a specific browser by `deviceId`, instead of relying only on a broadcast “switch browser” flow.

Usage:
```bash
# Exposed as browser automation tools inside Claude Code sessions:
list_connected_browsers
select_browser {"deviceId":"<device-id-from-list_connected_browsers>"}
```

Details:
- `list_connected_browsers` returns each connected extension instance with its device ID, display name, OS platform, and whether it appears to be on this computer.
- `select_browser` binds the session to a specific connected browser without broadcasting a new pairing request.
- If multiple Chrome browsers are connected and no active browser is selected, Claude Code now returns a clear prompt instructing the model to present every connected browser as a separate option.
- This requires bridge-backed browser automation; non-bridge sessions receive “Listing browsers is only available with bridge connections.”

Evidence: Browser automation tool definitions and multi-browser guard (search for `"list_connected_browsers"`, `"select_browser"`, and `"Multiple Chrome browsers are connected to this account and none has been selected for this session."`)


### Agent View Launch Defaults
What: `claude agents` can now set defaults for sessions launched from agent view: permission mode, model, and effort level.

Usage:
```bash
claude agents --permission-mode acceptEdits --model sonnet --effort high
claude agents --dangerously-skip-permissions --model opus
```

Details:
- `--permission-mode <mode>` sets the default permission mode for sessions dispatched from agent view.
- `--dangerously-skip-permissions` is accepted as an alias for `--permission-mode bypassPermissions`.
- `--model <model>` and `--effort <level>` are forwarded into sessions dispatched from the agent view.
- These options are specific to background-agent dispatch from the agent view, not a replacement for the normal session-level `--model` and `--effort` flags.

Evidence: `claude agents` command options (search for `"Default permission mode for sessions dispatched from agent view"`, `"Default model for sessions dispatched from agent view"`, and `"Default effort level for sessions dispatched from agent view"`)


### Agent View Plugin and Config Forwarding
What: Agent view launches can now preserve selected session configuration flags when relaunching or dispatching sessions.

Usage:
```bash
claude agents --plugin-dir ./my-plugin --add-dir ../shared --mcp-config ./.mcp.json
```

Details:
- New parsing handles `--plugin-dir`, `--add-dir`, `--settings`, `--mcp-config`, and `--strict-mcp-config` around the `agents` command.
- The relaunch path explicitly understands `claude agents --plugin-dir`, so session-only plugins can participate in agent-view workflows.
- This is most useful for users who start agent view with local plugins or additional working directories and expect dispatched sessions to inherit that setup.

Evidence: Agent command argument parser and relaunch hint (search for `"claude agents --plugin-dir"` and `"--strict-mcp-config"`)


### Send Files to the User
What: Remote and first-party environments now have a dedicated `SendUserFile` tool for delivering generated artifacts, screenshots, reports, and build outputs to the user.

Usage:
```bash
# Exposed as a Claude Code tool in supported remote/first-party sessions:
SendUserFile {
  "files": ["./report.html", "./screenshot.png"],
  "caption": "Final report and screenshot",
  "status": "normal"
}
```

Details:
- The tool accepts absolute or cwd-relative file paths.
- `caption` is optional.
- `status` is required and distinguishes `normal` replies from `proactive` delivery.
- It is enabled for first-party remote-style environments and gated by `tengu_send_user_file`, which defaults on.
- Delivered files are surfaced with attachment metadata and file UUIDs when available.

Evidence: Send-file tool definition and rollout gate (search for `"SendUserFile"`, `"File paths (absolute or relative to cwd) to send to the user."`, and `"tengu_send_user_file"`)


### Skills-as-Plugins from `@skills-dir`
What: User and trusted project skill folders under `.claude/skills/` can now be loaded as plugins when they contain `.claude-plugin` metadata.

Usage:
```bash
# Put a plugin-backed skill under:
.claude/skills/<name>/.claude-plugin/plugin.json

# If project trust was accepted after startup:
# run /reload-plugins or relaunch
```

Details:
- Claude Code scans user skills and trusted project skills for `.claude-plugin` directories.
- Project-scope skill plugins require workspace trust; otherwise Claude Code tells users to accept the trust dialog and run `/reload-plugins`.
- Project-supplied MCP servers, LSP servers, and monitors are stripped for now because per-item approval is not yet routed through `@skills-dir` plugins.
- Duplicate plugin names are detected, with warnings when a user plugin shadows a project plugin or another plugin with the same name.

Evidence: Skills-as-plugins loader and trust warnings (search for `"project-scope plugin"`, `"Accept the trust dialog for this workspace, then run /reload-plugins."`, and `"LSP servers from project @skills-dir plugins are not supported until per-server approval ships."`)


### More Precise Browser Automation When Multiple Browsers Are Connected
Claude Code’s existing `switch_browser` behavior was clarified so it is now used when the user wants to choose inside Chrome, while `list_connected_browsers` plus `select_browser` is preferred when the model already has a concrete `deviceId`.

Evidence: Updated `switch_browser` guidance (search for `"otherwise prefer select_browser with a known deviceId"`)


### Better Recovery from Unprocessable Images and PDFs
Claude Code now recognizes more API media-processing failures and can remove the failing image or document from the latest request, replacing it with a clear placeholder instead of only handling a narrower oversized-image case.

Evidence: Media retry classification and replacement text (search for `"could not process image"`, `"the pdf specified was not valid"`, and `"removed: the API could not process this"`)


### Remote Default Permission Modes Include `default` and `auto`
Remote sessions now accept `default` and `auto` as valid `permissions.defaultMode` values in addition to `acceptEdits` and `plan`.

Evidence: Remote default-mode validation changed from the old two-mode warning to the new four-mode warning (search for `"only acceptEdits, plan, default, and auto are allowed"`)


### Safer Auto Mode Defaults from Settings
Claude Code now ignores `permissions.defaultMode: "auto"` when it comes from repo-controllable project or local settings; only policy, user, or flag settings may grant auto mode.

Evidence: Auto-mode source check (search for `"settings defaultMode \"auto\" ignored"`)


### Richer Plugin Catalog Cache
Plugin install-count fetching was replaced by a broader plugin catalog cache that loads `plugin-details.json`, validates cache structure and staleness, and can still surface install counts from the richer catalog.

Evidence: Plugin catalog fetch/cache path (search for `"plugin-catalog-cache.json"`, `"Fetching plugin catalog from"`, and `"plugin-stats/plugin-details.json"`)


### Plugin Component Summaries Include LSP Servers
Plugin/component summaries now include LSP server names alongside commands, agents, skills, hooks, and MCP servers.

Evidence: Plugin summary UI and manifest reader (search for `"LSP Servers"` and `"lspServers"`)


### Fallback Skills Yield to Plugin or MCP Skills
Bundled or fallback skill stubs can now yield when a plugin or MCP skill with the same suffix is loaded, reducing duplicate skill entries and routing users to the canonical implementation.

Evidence: Fallback skill suppression (search for `"Dropping fallback skill"` and `"@internal — interim defense-in-depth for thin-pointer skill stubs"`)


### SDK Tool Aliases
SDK/session initialization now accepts `toolAliases`, allowing a model-emitted tool name to resolve to a different registered tool name before execution.

Evidence: SDK option schema and resolution path (search for `"Map of tool-name aliases applied before name resolution"` and `"toolAliases"`)


### Background Auth Snapshot Handling
Background sessions on macOS can now pass auth through a snapshot file instead of keeping the OAuth token directly in the child environment.

Evidence: Auth snapshot consume/write paths (search for `"Consumed bg auth snapshot from sockDir"`, `"CLAUDE_BG_AUTH_SNAPSHOT_PATH"`, and `"writeAuthSnapshot failed"`)


## Bug Fixes

- Prevented repo-controllable settings from silently enabling auto mode through `permissions.defaultMode: "auto"`; Claude Code now warns and ignores that source. Evidence: search for `"settings defaultMode \"auto\" ignored"`.

- Improved retry handling when the API rejects a document or image as unprocessable, empty, password-protected, or too large; Claude Code can strip the failing media block and tell the user what was removed. Evidence: search for `"image does not match the provided media type"`, `"pdf cannot be empty"`, and `"in the conversation could not be processed and was removed"`.

- Made project-scope skill-plugin failures actionable instead of silently connecting unsupported server components; users are told to move MCP servers to `.mcp.json` or install monitor-bearing plugins at user scope. Evidence: search for `"project-supplied servers and monitors require per-item approval"` and `"Put MCP servers in <cwd>/.mcp.json instead."`.

- Improved OAuth refresh contention handling with a lock-acquisition retry error when another process is already refreshing credentials. Evidence: search for `"Lock acquisition failed after"` and `"another process is refreshing"`.

- Preserved file permissions and avoided symlink writes in new atomic write paths, reducing the risk of unsafe writes through symlinks. Evidence: search for `"Refusing to write through symlink"` and `"Preserving file permissions"`.


## In Development

Features with infrastructure added but not yet enabled. These are shipped "dark" and may become available in future versions.


### Bridge Vivid Mode [In Development]
What: A new bridge-related feature flag appears to gate an alternate or enhanced bridge mode.

Status: Feature-flagged, default off.

Details:
- The new gate returns `tengu_bridge_vivid` with a default of `false`.
- The diff shows infrastructure but not enough user-facing text to document a usable workflow yet.
- No invocation path was found that makes this broadly available to users in this release.

Evidence: Feature flag defaults off (search for `"tengu_bridge_vivid"`)


### Ultraplan Remote Plan Refinement [In Development]
What: Claude Code contains a new “Ultraplan” handoff path that appears intended to send a plan for remote refinement and later return a web link for browser review.

Status: Dark-launched or gated.

Details:
- The exit-plan-mode UI has an `ultraplan` outcome and a new message telling Claude to hand the plan off remotely.
- The visible text says a web link will appear and that the user can edit and iterate on the plan in the browser.
- The surrounding controls suggest this is not a normal always-on plan-mode option for all users.

Evidence: Remote plan handoff text (search for `"I'm sending this plan to Ultraplan to be refined remotely"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.142.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.142.txt`
