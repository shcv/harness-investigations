# Changelog for version 2.1.187

## Summary

This release renames `/toggle-memory` to `/pause-memory` with updated messaging, adds a `--bg`/`--background` CLI flag to launch background agent sessions directly, and introduces `sandbox.credentials` configuration for credential protection in sandboxed commands. There are also several improvements to MCP error handling, the GitHub App post-install flow, and the `/usage` command's skill footprint display.


## New Features


### `--bg` / `--background` Flag for Background Agent Sessions

What: Start a Claude session as a background agent and return immediately to the shell, instead of entering interactive mode. The session can then be monitored and managed with `claude agents`.

Usage:
```bash
claude --bg "implement the feature described in SPEC.md"
# or
claude --background "run the test suite and fix any failures"
```

Details:
- Claude starts the session, then detaches and returns control to your shell
- The agent runs independently and can be checked on with `claude agents`
- Useful for kicking off long-running tasks while continuing other work
- Previously `--bg` was recognized in some internal code paths but was not a documented, user-invocable CLI option

Evidence: New CLI option registered with `addOption(new oc("--bg, --background", "Start the session as a background agent and return immediately (manage with \`claude agents\`)"))`


### `sandbox.credentials` — Credential Protection Configuration

What: A new settings block `sandbox.credentials` lets you declare credential files and environment variables that the sandbox should hide from sandboxed commands.

Details:
- Configure under `sandbox.credentials` in settings (project or user)
- `files`: list of credential file paths to protect; each entry specifies a `path` and `mode: "deny"` (deny blocks reads of that path inside the sandbox)
- `envVars`: list of environment variable names to protect; `mode: "deny"` unsets the variable for sandboxed commands
- Path resolution follows the same rules as `sandbox.filesystem.*` paths (absolute, `~`-expanded, or relative to settings file root)
- Errors in the credentials block are logged and the block is dropped rather than silently applied incorrectly — a warning appears: `The credentials block was dropped; no credential protection is applied until it is fixed`
- `mode: "mask"` is reserved for a future release; attempting to use it emits an error pointing to `deny` as the current supported mode

Evidence: New schema under `sandbox.credentials` (search for `"Credential files or directories to protect"`, `"Credential mode \"mask\" is not supported yet"`)


### MCP Tool Idle Timeout

What: MCP tool calls that produce no response or progress notifications for a configurable period are now automatically aborted with a clear error message. Previously MCP tools could hang indefinitely.

Details:
- Default timeout applies to eligible tool types; set `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` (in milliseconds) to override
- Set to `0` to disable the timeout for tools that are expected to run silently for a long time
- Error shown when timeout fires: `MCP server "<name>" tool "<tool>" sent no response or progress for <N>s; aborting. Set CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT (ms) higher or to 0 if this tool is expected to run silently for longer.`
- Separate from the overall MCP response timeout; specifically tracks silence between progress notifications
- Emits `McpResponseSchemaError` events when servers return malformed results that fail schema validation

Evidence: New idle-timeout function (search for `"MCP tool idle timeout"`, `"sent no response or progress for"`, `"CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT"`)


### GitHub App Post-Install: GitHub Actions Workflow Setup

What: After successfully installing the Claude GitHub App, Claude now presents an option to also set up GitHub Actions workflows so Claude automatically responds to `@claude` mentions in issues and pull requests.

Details:
- Appears immediately after the GitHub App installation completes
- Two options: "Set up GitHub Actions workflows" or "Skip for now (you can run /install-github-app again later)"
- Can be triggered again anytime with `/install-github-app`

Evidence: New post-install UI component (search for `"GitHub App installed!"`, `"Set up GitHub Actions workflows"`, `"Run /install-github-app again anytime to set up GitHub Actions workflows."`)


### Server-Driven Startup Announcements

What: The hardcoded "Fable 5 launch" banner has been replaced with a generic announcement system. Announcements are now configured server-side via the `tengu_startup_announcements` feature flag, letting Anthropic display product news without a code release.

Details:
- Each announcement has an id, optional title, text, priority, and `maxImpressions` (how many sessions it shows before going quiet)
- Slash command mentions in announcement text are highlighted in the suggestion color
- Existing announcement history is tracked per `announcementImpressions` in user state
- The Fable 5 launch promotion, "Fable 5 is here!", "Our newest model for complex, long-running work.", and related strings are removed

Evidence: New announcement renderer (search for `"tengu_startup_announcements"`, `"startup-announcement"`)


### Skill Token Footprint in `/usage`

What: The `/usage` command now includes a "Skill-listing footprint" section for each plugin, showing how many tokens each skill's description contributes to the system prompt per turn.

Details:
- Displays a per-skill breakdown: skill name and approximate tokens per turn
- Shows a total across all model-invocable skills for the plugin
- If no model-invocable skills are loaded for a plugin, shows "No model-invocable skills loaded for this plugin"
- Redirects to `/usage` for per-skill invocation counts and cost attribution

Evidence: New usage detail component (search for `"Skill-listing footprint"`, `"What this plugin's skill descriptions add to the system prompt (cached input after the first turn). Agents and MCP tools not yet counted."`)


### Model Access Entitlements

What: The bootstrap API now returns a `model_access` entitlement list from the server. Models your organization is not entitled to are now filtered out of the model picker and unavailable for selection, in addition to the existing `availableModels` allowlist check.

Details:
- New `modelAccessCache` field in persisted state stores the entitlement list across sessions
- Plan mode messages now mention "availableModels allowlist or model_access entitlement" in error text when the plan upgrade model is blocked
- The model availability check rejects a model if it appears in the entitlement list as not entitled
- Applies for `firstParty` and `gateway` authentication providers

Evidence: New entitlement check functions (search for `"model_access entitlement"`, `"modelAccessCache"`), bootstrap fetch now stores `t.model_access`


## Improvements


### `/pause-memory` Replaces `/toggle-memory`

The automemory toggle command has been renamed from `/toggle-memory` to `/pause-memory`, and all related messaging was updated to use "paused/resumed" language instead of "disabled/re-enabled".

- Status bar now shows: `Paused for this session · /pause-memory to resume`
- When memory is paused: `Memory paused for this session · this conversation will not write or read new memories, and previously-loaded memory content should not be referenced. Run /pause-memory again to resume.`
- When resumed: `Memory resumed · memory content may be referenced and new memories can be saved.`
- Permission denial messages updated: `Cannot read/write to memory while it is paused. Run /pause-memory to resume automemory.`

Evidence: Renamed command and updated messages (search for `"Paused for this session \xB7 /pause-memory to resume"`, `"/pause-memory"`)


### Ghostty Terminal: CMD+Click Now Works

Fixed hyperlink activation with CMD+click in the Ghostty terminal on macOS. Ghostty sends CMD+click events without the SGR modifier bit that Claude Code was checking for, so clicks were silently dropped.

Evidence: New terminal quirk detection (search for `"ghostty"` in the `macCmdClickArrivesWithoutSgrModifierBit` method)


### Linux Sandbox: Symlink Resolution for Deny-Read Paths

The Linux sandbox (`bwrap`) now resolves symlinks when applying `--ro-bind /dev/null` masks for deny-read paths. Previously a symlink pointing to a denied path could bypass the deny mask because the bwrap argument used the symlink path rather than the real path.

Evidence: New `zFi` function (search for `"[Sandbox Linux] Re-applying denyRead file mask re-exposed by denyWrite bind"`, `zFi` resolves symlinks via `lstatSync`/`realpathSync`)


### `histchars` Preserved in Subprocess Shell Environment

The `histchars` environment variable is now included in the list of locale/shell variables passed through to subprocess shells. This prevents history expansion character mapping from being lost in shell subprocesses.

Evidence: Added to the env-var passthrough list (search for `"histchars"` in the shell env allowlist)


### UNC Path Filtering in File Watcher

On Windows, remote UNC paths (e.g., `\\server\share`) are now silently filtered out of the file watcher with a debug warning. Previously, attempting to watch UNC paths could produce errors or hangs.

Evidence: New filter and warning (search for `"FileChanged: dropped remote UNC watch path(s)"`)


### DesignSync Error Messages Context-Aware for Non-Interactive Sessions

DesignSync authorization failure messages are now tailored to the environment. In non-interactive sessions (remote agents, CI, claude.ai/code), the messages explain why `/design-login` is unavailable and provide environment-specific remediation steps, instead of suggesting an interactive command that won't work.

Evidence: Updated error handler (search for `"DesignSync needs design-system authorization, but /design-login requires an interactive terminal"`, `"Could not add design scopes to the token. Re-authentication is required from an interactive Claude Code terminal"`)


### MCP Permission Mode Override Accepts `auto`

The `set_mcp_permission_mode_override` control-channel request now accepts `'auto'` as a valid override mode, in addition to `'default'` and `null`. The validation message was updated to reflect this.

Evidence: Updated permission message (search for `"Permission mode override over the control channel is tighten-only ('default', 'auto', or null)"`)


### `mcp add-json`: Clear Error for Empty/Null JSON

When `mcp add-json` receives empty, invalid, or null JSON from the user, it now logs a clear error message (`mcp add-json: user-provided JSON was empty, invalid, or null`) instead of silently failing or applying a broken configuration.

Evidence: New null-check and log (search for `"mcp add-json: user-provided JSON was empty, invalid, or null"`)


### Agent Completion Messages Simplified

Agent completion status messages are now shorter and more direct. The "came to rest" phrasing is replaced with plain status strings:

- `" finished"` (completed normally)
- `" was stopped by user"` (user-cancelled)
- `" was stopped by Claude"` (Claude-terminated)
- `" returned a malformed result that failed schema validation: ..."` (schema error)

Evidence: Replacement of `"came to rest"` strings (search for `" finished"`, `" was stopped by user"`)


### Safety Message Language Polished

Safety-related model messages now say "safeguards flagged this message" instead of "has safety measures that flagged". The wording "Mythos-level capabilities" replaces "Mythos-level capability in other areas", and the trailing phrase was shortened slightly.

Evidence: Updated safety message constants (search for `"'s safeguards flagged this message (https://www.anthropic.com/legal/aup)"`, `"These measures let us bring you Mythos-level capabilities sooner"`)


### Plan Mode Exit: Verification Reminder Removed

The post-plan implementation flow no longer injects a `verify_plan_reminder` tool call. The exit-plan prompt is streamlined, removing instructions to call a verification tool after implementing the plan.

Evidence: Removal of `"verify_plan_reminder"` from the plan exit tool call list


## Bug Fixes

- Bootstrap client data is now cached per session identity (entrypoint + model + version + org UUID) rather than as a single global slot, preventing stale data from one user context bleeding into another. (search for `"tengu_client_data_cache_key"`, `"bi1-"` cache key prefix)
- Session transcript files are now also created when the first system message arrives, not only on user/assistant messages. This fixes edge cases where background-mode sessions could lose their session file. (search for `"d.type === \"system\""` in session materialization)
- Reconnecting to an existing session via `CLAUDE_BRIDGE_REATTACH_SESSION` now correctly respects the attached session state, preventing a stale reload when reattaching. (search for `"CLAUDE_BRIDGE_REATTACH_SESSION"`)
- The model picker no longer adds the current model as an option if it is not a valid model per `isModelAvailable`. Previously an invalid current model could appear in the dropdown. (search for `"Ua(n)"` guard in model option filter)


## In Development


### Memory Sync Partition Tracking [In Development]

What: Team memory backends now support a `.memory-sync` manifest file that records the partition ID of each mounted store. When a mount directory holds data from a different partition, the sync is suppressed rather than mixing data from incompatible backends.

Status: Feature-flagged — gated by `tengu_silk_almanac`

Details:
- A `.memory-sync` JSON file in each mount directory records `{ v, partition }` where `v` is the format version
- On pull, if the manifest is absent or mismatched, the remote hash basis is invalidated and sync restarts from scratch
- Mid-session partition mismatches for non-user-scope stores suppress syncing with a warning, rather than silently proceeding
- Stale mount directories from removed stores are reaped automatically

Evidence: New partition manifest functions (gated by `tengu_silk_almanac`, search for `".memory-sync"`, `"partition mismatch"`, `"memory-watcher: rebuild initial sync failed"`)


Generated with:
- tool: `harness-investigations@0c752ef-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.187.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.187.txt`
