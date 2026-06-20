# Changelog for version 2.1.178

## Summary

This release introduces `/design-login`, a standalone OAuth command that lets API-key, Bedrock, and Vertex users authorize design-system access without a full claude.ai login. It removes `TeamCreate`/`TeamDelete` in favor of the session's single implicit team, overhauled the Fable 5 usage-credits consent flow into an interactive dialog, and expands the code review skill with a CLAUDE.md conventions angle. Foundry deployments now automatically detect and gracefully drop unsupported capabilities, and the tool-use indicator now rings a terminal bell when a long-running tool finishes.


## New Features


### /design-login — Independent Design System Authorization

What: A new `/design-login` slash command lets you authorize design-system (claude.ai/design) access with a separate OAuth credential, even when your Claude Code session is authenticated via API key, Bedrock, Vertex, or any other non-claude.ai provider.

Usage:
```
/design-login
```

Details:
- Opens a browser OAuth consent flow for read/write access to your organization's claude.ai/design projects. This is separate from your main session authentication and changes nothing else.
- If the browser doesn't open automatically, the flow shows the URL and lets you copy it (press `c`). In remote/SSH sessions where a browser can't reach the local listener, the command automatically falls back to a manual code-paste flow.
- A 5-minute timeout applies to the browser flow; after that you are prompted to retry or switch to `/design-login` for the manual path.
- Credentials are stored under `designOauth` in the local config store, protected by a `.design_oauth_refresh.lock` file-based lock that prevents concurrent refresh races across multiple Claude Code processes.
- If a credential is already stored, the flow warns "A design credential is already stored — completing this flow replaces it."
- Set `CLAUDE_CODE_DESIGN_OAUTH_CLIENT_ID` to override the built-in OAuth client ID if your build doesn't include a registered client.
- Previously, design access required a full `/login` with a claude.ai subscription. Now API-key users can run `/design-login` to unlock `/design-sync`.

Evidence: New `/design-login` command definition (search for `"design-login"`); credential storage (search for `"designOauth"`); lock file (search for `".design_oauth_refresh.lock"`)


### Fable 5 Usage Credits Consent Dialog

What: When Fable 5 switches from plan limits to usage credits—or when usage credits aren't yet enabled—Claude Code now shows an interactive multi-step consent dialog instead of a static error message.

Details:
- Consent flow states: acknowledge → verify (checks live status) → enable (in-app) or external (browser).
- The acknowledge step shows: "Fable 5 draws from usage credits instead of plan limits, billed at standard API rates. Your other models remain included in your plan." with two options — "Continue with Fable 5 on usage credits" or switch away.
- If usage credits aren't enabled yet, a second step ("Turn on usage credits") shows the starting monthly limit and a link to the Help Center. Confirming enables credits in-app; if in-app enablement is unavailable, it opens your browser.
- Per-organization consent is stored persistently so you only consent once per org (or once per account for personal plans).
- Mid-session Fable model switches now show "Fable 5 now uses usage credits" with an option to switch to the best non-Fable fallback or accept.
- The model picker description for Fable 5 now shows one of: "Draws from usage credits", "Included with your plan until [date]", or nothing (when no overage applies).
- Specific error messages for blocked states: out of credits → `/usage-credits to add funds`; org spend cap → `/usage-credits to adjust` or "ask your admin"; org disabled → `/model to switch models`; seat tier ineligible → `/model to switch models`.
- Compact is now blocked with a message when the model policy allows only Fable 5 but usage credits aren't enabled: "Compaction unavailable: your model policy only allows Fable 5, which requires usage credits · /model to set it up".

Evidence: Consent dialog (search for `"Continue using Fable 5 on usage credits?"`); in-app enable path (search for `"Setting up usage credits…"`); org consent storage (search for `"fableOverageConsent"`); model description (search for `"Draws from usage credits"`)


### Agent Tool: Remote Cloud Sandbox (`isolation: "remote"`) [Gradual Rollout]

What: The Agent tool's `isolation` parameter now accepts `"remote"` to launch a subagent in a fresh CCR cloud sandbox rather than a local worktree.

Usage:
```
Agent({
  prompt: "...",
  isolation: "remote"
})
```

Details:
- Remote agents always run in the background. You receive a notification when complete.
- The task ID and session URL are returned so you can track progress.
- When the local branch hasn't been pushed to origin, the remote agent runs against the repository's default branch instead (a warning is logged: "local branch '…' is not pushed to origin").
- Falls back gracefully when unavailable (not in a git repo, no cloud session, or inside an existing CCR session).
- Gated behind the `tengu_neapolitan` feature flag.

Evidence: Remote-agent availability check (search for `"tengu_neapolitan"`); fallback (search for `"[remote agent] isolation:'remote' is unavailable"`)


### Worker Graceful Shutdown Reason Event

What: When a Claude Code worker shuts down with a known reason, a `worker_shutting_down` system message is now emitted to the bridge event stream before the heartbeat stops.

Details:
- Includes a short snake_case `reason` field (e.g., `host_exit`, `remote_control_disabled`) set by the host CLI, not by user input.
- Allows bridge clients (e.g., the mobile app or claude.ai/code) to display why the worker disconnected instead of waiting for heartbeat timeout.
- Not emitted for hard kills or OOM — only when the teardown code path runs with an explicit reason.

Evidence: New system subtype (search for `"worker_shutting_down"`)


## Improvements


### TeamCreate and TeamDelete Removed — Implicit Team Model

The explicit `TeamCreate` and `TeamDelete` tools have been removed. Every session now has a single implicit team, initialized at startup.

- The `team_name` parameter on the Agent tool is deprecated and carries only the session-derived name for backward compatibility. It is marked `@deprecated` in the protocol schema.
- Plan-mode hint updated: "If this plan can be broken down into multiple independent tasks, consider spawning named teammates with the Agent tool (pass a `name`) to parallelize the work." (Previously suggested `TeamCreate`.)
- Teammate-spawned subagents cannot themselves spawn teammates; to spawn a subagent from a teammate, omit the `name` parameter.
- Error messages updated to remove references to `spawnTeam`, `TeamPreconditionError`, and team-name validation constraints.

Evidence: Removed tool registration (search for `"TeamCreate"` to confirm absence); deprecation notice (search for `"@deprecated Sessions have a single implicit team"`)


### Code Review: Conventions Angle

The `review` skill's finder phase now includes a CLAUDE.md-aware conventions angle.

- High-effort reviews run 8 independent finder angles: 5 correctness + 3 cleanup + 1 altitude + 1 conventions (up from 7 in the previous version — `"5 correctness angles + 3 cleanup angles + 1 altitude angle, up to 8 each"`).
- Medium-effort reviews similarly expand to 8 angles.
- The conventions angle reads the applicable CLAUDE.md files (user-level `~/.claude/CLAUDE.md`, repo root, and any `CLAUDE.md` or `CLAUDE.local.md` in directories ancestral to changed files) and flags clear rule violations — quoting the exact rule and the exact line that breaks it. Vague inferences are excluded.
- Cleanup, altitude, and conventions candidates now share the same `file`/`line`/`summary`/`failure_scenario` shape. `failure_scenario` should state concrete cost (duplication, maintenance burden, or which CLAUDE.md rule is broken) rather than a hypothetical crash.
- Review instructions also now pin the diff command, changed files, applicable CLAUDE.md files, and conventions (previously: just diff and changed files).

Evidence: Updated phase header (search for `"5 correctness angles + 3 cleanup angles + 1 altitude angle + 1 conventions angle"`); conventions angle text (search for `"Find the CLAUDE.md files that govern the changed code"`)


### Remote Control Diagnostics Overhaul

The Remote Control diagnostics panel (visible via `/doctor` or the Remote Control section) now reports more checks, uses symmetric pass/fail labels, and surfaces org-policy detail.

New/changed checks:
- "Connected to the Anthropic API (api.anthropic.com)" / "Not connected…" (was "First-party provider (api.anthropic.com)")
- "Signed in to claude.ai" / "Not signed in to claude.ai" (was "claude.ai OAuth token present")
- "claude.ai subscription active" / "claude.ai subscription auth not active" (was "claude.ai subscriber auth active")
- "Sign-in includes the user:profile scope" / "Sign-in is missing the user:profile scope" (was "OAuth token has user:profile scope")
- "Organization resolved" / "Organization not resolved" (was "Organization UUID resolved")
- New: "Org policy allows Remote Control (allow_remote_control)" / "denied" / "unavailable" — checked via `allow_remote_control` org policy; policy limits are loaded before diagnostics run.
- New: "Feature-flag evaluation enabled" / "Feature-flag evaluation disabled"
- Renamed: CCR bridge rollout check now shows "Remote Control rollout enabled for this account" / "not enabled" / "could not be verified".
- When Remote Control is enabled, the panel shows "Control this session from claude.ai/code or the Claude mobile app."

Evidence: New diagnostics function (search for `"Connected to the Anthropic API (api.anthropic.com)"`); org policy check (search for `"Org policy allows Remote Control (allow_remote_control)"`)


### Extended Thinking: `thinking_display` Bridge Parameter

The `set_max_thinking_tokens` bridge command (which backs `/thinking` for Remote Control hosts) now accepts an optional `thinking_display` parameter.

Details:
- Values: `"summarized"` or `"omitted"` to set the display mode for the rest of the session; `null` to clear it back to the API default; omitting the parameter leaves the session's `--thinking-display` start value unchanged.
- Allows bridge hosts to control thinking display per-call rather than only at session start.

Evidence: Updated `set_max_thinking_tokens` description (search for `"Sets the maximum number of thinking tokens for extended thinking. thinking_display optionally"`)


### Scoped Skills — Directory-Aware Variant Selection

The Skill tool's instructions now explain that skills can be scoped to specific directories.

- A scoped skill name looks like `apps/web:deploy`; its description says which directory it applies to.
- When both a scoped and an unscoped variant exist, invoke the most specific directory match for the files you are working on — e.g., if the files are under `apps/web/`, prefer `apps/web:deploy` over the unscoped `deploy`.
- Skills declare their scope root via `skillRoot` in the skill manifest.

Evidence: Updated Skill tool description (search for `"Some skills are scoped to a directory: their name is prefixed with the directory"`)


### Artifact Tool: Write Content Directly, Use Scratchpad

The Artifact tool's instructions are updated with two behavioral clarifications:

- Write just the page content (not a full `<!DOCTYPE html>…<body>` skeleton) — the tool wraps the content automatically at publish time.
- Unless the user names a different location, put the file in your scratchpad directory if one is listed in your system prompt.

Evidence: Updated Artifact tool description (search for `"The file is wrapped in a <!doctype html>"`)


### Agent Tool: `disallowedTools` Documents MCP Server-Level Removal

The `disallowedTools` / `denied_tools` parameter description now explicitly documents server-level MCP removal specs:

- `mcp__server` — removes every tool from the named server.
- `mcp__server__*` — removes all tools whose names match the prefix.
- `mcp__*` — removes all MCP tools entirely.

Evidence: Updated `disallowedTools` description (search for `"MCP server-level specs (mcp__server, mcp__server__*, mcp__*) remove every tool from the named server"`)


### DesignSync: Now Accessible Without claude.ai Login

The DesignSync tool description now states that sessions authenticated via API key or provider token can use `/design-login` to authorize design access separately:

- Previously: "through their claude.ai login" only.
- Now: "through their claude.ai login (or, for sessions without one, a dedicated design authorization from /design-login)."
- Error messages for auth failures are correspondingly updated to offer `/design-login` as an alternative path.
- "Could not add design scopes to the token. Run /login, select 'Claude account with subscription', and retry — or run /design-login to authorize design access separately."

Evidence: Updated DesignSync tool description (search for `"or, for sessions without one, a dedicated design authorization from /design-login"`)


### Usage View: Behaviors and Top Contributors

The `/cost` plan-usage view (formerly described as "Show the total cost and duration of the current session") now shows what's contributing to your limits, with a breakdown by behavior and top contributors.

- New description: "Show session cost, plan usage, and what's contributing to your limits."
- Shows "Last 24h" and "Last 7d" windows side by side.
- Behavior categories (shown as percentages of total cost):
  - cache miss: "% of your usage hit a >100k-token cache miss"
  - long context: "% of your usage was at >150k context"
  - subagent heavy: "% of your usage came from subagent-heavy sessions"
  - high parallel: "% of your usage was while 4+ sessions ran in parallel"
  - cron: "% of your usage came from sessions active for 8+ hours"
- Top contributors listed for: skills (prefixed with `/`), subagents, plugins, MCP servers — each with a percentage.
- Note: "Approximate, based on local sessions on this machine — does not include other devices or claude.ai. Behaviors are independent characteristics, not a breakdown."
- Behaviors with less than a minimum threshold percentage are filtered out.

Evidence: New breakdown functions (search for `"Top skills"`); behavior labels (search for `"% of your usage hit a >100k-token cache miss"`)


### Tool Indicator: Bell Notification on Long Tool Completion

The in-progress tool indicator now triggers a terminal bell notification when a tool that has been running for a while finally completes.

Details:
- The bell fires when a tool finishes after running for more than a threshold duration (debounced to prevent rapid-fire bells if multiple tools finish close together).
- Only fires when the bell/notification setting is enabled in your preferences.
- Replaces the previous static tool-spinner component with a new implementation that tracks start time.

Evidence: New tool indicator implementation (search for `"notifyBell"`); timer tracking (search for `"tool error:"` for the indicator's aria-label)


### Foundry Deployment Capability Auto-Detection

Claude Code now automatically detects when an Azure AI Foundry deployment lacks specific capabilities and gracefully works around them, rather than repeatedly failing with errors.

Details:
- Detects missing capabilities from 400-error responses containing patterns like "[feature] not supported in your workspace" or "features are not available for Azure AI Foundry workspaces."
- Detected capabilities cached per deployment endpoint so each failure is only seen once per session.
- For missing web search: shows "Web search is not available on this Foundry deployment." and fails the request with a `fail:foundry-purpose-request` code.
- For missing tool search server or structured outputs: automatically retries the request after stripping the unsupported features from the tool list (removing `defer_loading` or `strict` fields).
- Handles both `ANTHROPIC_FOUNDRY_BASE_URL` and `ANTHROPIC_FOUNDRY_RESOURCE` (constructs `https://{resource}.services.ai.azure.com`).

Evidence: Capability detection (search for `"[foundry-capabilities] deployment"`); web search error (search for `"Web search is not available on this Foundry deployment."`)


### Hyperlink Scheme Allowlist Expanded

Clickable hyperlinks in the terminal now dispatch several additional URL schemes.

New schemes added: `cursor:`, `windsurf:`, `zed:`, `jetbrains:`, `idea:`, `slack:`, `linear:`, `notion:`, `figma:`

Non-allowlisted schemes are refused with a warning (search for `"[hyperlink] refusing to dispatch clicked link with non-allowlisted scheme"`).

Evidence: Expanded scheme set (search for `"figma:"` in the scheme set)


### `agent-message` Tag Wrapping for Peer Messages

Messages delivered from remote peers (teammates or background subagents) are now wrapped in `<agent-message from="…">` tags in the transcript.

Details:
- The sender name is HTML-escaped in the `from` attribute.
- The expanded transcript view shows the sender's display name and the unwrapped message body.
- Control characters, zero-width characters, and Unicode direction overrides are stripped from sender names; names longer than 64 characters are truncated with "…".
- The reserved recipient name `"main"` routes messages to the main conversation and cannot be used as a teammate name.

Evidence: Tag wrapping (search for `"agent-message"`); sender name sanitization (search for `"<agent-message from="`)


## Bug Fixes

- WIF (Workload Identity Federation) token refresh race: when a sibling process rotates the access token, Claude Code now detects the fresher token in the credentials file and adopts it, skipping the redundant refresh grant. (search for `"wif: adopting sibling-rotated access token from credentials file"`)

- Bash prompt rule denial is now correctly classified as a `pre-ask` decision rather than `other`, making it non-approvable by the auto-classifier. This prevents the classifier from incorrectly overriding a prompt-rule denial. (search for `"Denied by Bash prompt rule"`)

- `project_write` path validation in DesignSync now distinguishes between missing files (`ENOENT`), permission errors (`EACCES`/`EPERM`), and races (inode mismatch, device mismatch, symlink replacement `ELOOP`), giving specific error messages instead of a single generic path check. Notably: `"project_write: no file exists at local_path."`, `"project_write: local_path is not readable."`, `"project_write: local_path was replaced during the upload."` (search for `"project_write: no file exists at local_path"`)

- Memory watcher stale-store check now logs failures as warnings (`"memory-watcher: stale-store check failed"`) rather than silently swallowing errors. (search for `"memory-watcher: stale-store check failed"`)

- Model fallback during compaction is now logged with a specific message: "Compact: model fallback triggered (…)". Previously the fallback was silent. (search for `"Compact: model fallback triggered"`)


## In Development

Features with infrastructure added but not yet enabled for all users.


### Tool Search Reminder System [In Development]

What: Infrastructure for periodically reminding agents about available deferred tools they haven't yet discovered or used.

Status: Gated by a complex feature flag (`juniper_shoal`) with sub-flags. Not active by default.

Details:
- The reminder fires every N turns (configurable via `marsh_lantern.stride`) when the agent has gone that many turns since its last tool search.
- Lists up to a configurable maximum of undiscovered tool names (`marsh_lantern.span`).
- Only fires when the session is in tool-search-tool mode (`tst`) and the main loop model supports it.
- Sub-flags within `juniper_shoal`:
  - `marsh_lantern` — enables the tool search reminder itself.
  - `bracken_spool` — enables strict tool parameter validation.
  - `teasel_cove` — enables empty input repair (see below).
  - `gorse_hollow` — enables a fetch rule for tool search.
- The reminder also checks whether a TODO-reminder would fire in the same turn, and skips if so.

Evidence: Reminder generation (search for `"tengu_juniper_shoal_shown"`); sub-flag parsing (search for `"marsh_lantern"`)


### Empty Input Repair for Tool Calls [In Development]

What: When a tool is called with an empty `{}` input but has required parameters, the system now generates a helpful error message showing the minimal valid call shape.

Status: Gated by `teasel_cove` within the `juniper_shoal` feature flag. Not enabled by default.

Details:
- Detects tool calls where input is an empty object but the Zod schema has required fields.
- Synthesizes a minimal example: string fields become `<fieldname>`, numbers become `0`, booleans become `false`, arrays become `[]`, enums use their first value.
- Message format: "The {tool} tool was called with an empty input object ({}), but it has required parameters: `param1`, `param2`. Minimal valid call shape: {…}. Re-issue the call with real values for each required parameter."

Evidence: Repair implementation (search for `"tool was called with an empty input object ({})"`); flag (search for `"teasel_cove"`)


### Edit Tool: Stale-File Tolerance [In Development]

What: Two new feature flags change the Edit tool's behavior when a file has been modified on disk since it was last read.

Status: Gated by `tengu_cedar_sundial` and `tengu_velvet_hammer`. Not enabled by default.

Details:
- `tengu_cedar_sundial`: When enabled and the `old_string` uniquely matches in the current file, allow the edit to proceed even if the file has changed since last read. If applied, a note is appended to the result: "(note: the file had been modified on disk since you last read it — the edit applied cleanly, but the file contains other changes not in your context. Read it before edits that depend on surrounding content.)"
- `tengu_velvet_hammer`: Suppresses the "you must read the file first" error when the file has no prior read record, falling through to a normal match attempt instead.
- These flags enable more resilient edits in agent workflows where intermediate file reads would be expensive.

Evidence: Flag checks in stale-file detector (search for `"tengu_cedar_sundial"`; `"tengu_velvet_hammer"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.178-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.178.txt`
