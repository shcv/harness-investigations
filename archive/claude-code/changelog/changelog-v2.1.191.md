# Changelog for version 2.1.191

## Summary

This release introduces a major new AI-powered contextual tips system that watches your conversation and occasionally suggests a relevant feature when it detects friction — covering over 25 common situations from MCP discovery to worktree parallelism. It also adds team discovery (showing which MCP servers and skills your teammates use), remote session history prefetching for faster attach, and several user-facing improvements including compliance taint notifications, a voice-mode policy message, Files API restriction surfacing, config auto-repair, and MCP tool permission policies.


## New Features


### Contextual Tips System [Gradual Rollout]

What: An AI classifier runs as a side query after each turn and occasionally shows a 1–2 sentence tip when it detects a pattern of friction that a Claude Code feature would relieve. The default outcome is silence — tips appear only when all of: a clear pattern exists, a specific feature applies, the user hasn't already discovered it, and the moment feels helpful rather than interrupting.

Details:
- The classifier watches the last 30 turns of conversation and compares against a catalog of 25+ situations
- At most 3 tips per session; the same tip won't reappear for 50 sessions
- After a tip is shown, a second classifier measures reception from subsequent turns (acted on, positive/neutral/negative)
- Tips include a direct action: a slash command, keyboard shortcut, or copyable snippet
- When teammates' MCP servers or skills are known, tips reference them by name and usage count instead of generic suggestions
- The system requires at least 3 conversation turns and 5 turns between attempts

Situation catalog (eligible ids): `mcp-discovery`, `mcp-expand`, `web-docs-paste`, `exploration-without-planning`, `permission-fatigue`, `undo-changes`, `diff-request`, `correction-spiral`, `image-description-friction`, `long-running-wait`, `context-filling-up`, `code-review-before-ship`, `manual-polling`, `goal-loop`, `remote-scheduling`, `hooks-automation`, `repeated-workflow`, `outside-working-dir`, `parallel-investigation`, `previous-session-reference`, `at-mention-paths`, `ide-copy-paste`, `verbose-preference`, `queue-while-working`, `multi-step-no-todos`, `persistent-memory`, `worktree-parallel-branches`, `push-notif-stepping-away`, `statusline-discovery`, `high-effort-low-yield`, `opus-on-pro-near-limit`, `large-context-stale-files`, `pro-compact-threshold`, `side-question-during-work`, `background-agents-list`, `tmux-claude-agents`, `too-many-subagents`, `workflow-orchestration`, `workflow-size-control`

Individual entries within the catalog may be gated: `opus-on-pro-near-limit` requires `tengu_cobalt_heron`, `large-context-stale-files` requires `tengu_slate_moth`, `remote-scheduling` requires `tengu_surreal_dali`.

Evidence: Central classifier function gated by `Cs("allow_context_tips")` (search for `"allow_context_tips"`) and catalog defined under `"emit_context_tip"` tool name (search for `"emit_context_tip"`)


### Team Discovery [Feature-flagged: `tengu_team_discovery`]

What: Fetches which MCP servers and skills your teammates are using from the Claude platform and surfaces that information in contextual tips, giving social-proof suggestions specific to your team.

Details:
- Retrieves data from `/api/claude_code/discovery/team_usage` on session start when the feature is enabled
- Result is cached for 1 hour in `~/.claude/cache/team-discovery.json`
- When a tip fires about MCP or skills, the tip names the specific tool and teammate count: "11 teammates use the Atlassian MCP"
- Requires being logged into Claude.ai (`To()` check)

Evidence: Endpoint string (search for `"/api/claude_code/discovery/team_usage"`) and cache file name (search for `"team-discovery.json"`)


### Remote Session History Prefetch

What: When attaching to a remote background session, event history is now prefetched in the background before the attach completes, so the session loads with full context faster.

Details:
- Triggered for sessions with valid CCR session IDs
- History is fetched from `/v1/code/sessions/{id}/events` and written to a temp file under `cc-history-prefetch-{pid}/` in the OS temp directory
- Supports pagination — walks up to 10 pages of events
- Temp dir is cleaned up on process exit

Evidence: Temp dir prefix (search for `"cc-history-prefetch-"`) and log prefix (search for `"[historyPrefetch]"`)


### MCP Tool Permission Policies

What: Individual tools within an HTTP or SSE MCP server can now declare a `permission_policy` field (`"always_allow"`, `"always_ask"`, or `"always_deny"`) that pre-populates Claude Code's allow/deny/ask rules for that tool, avoiding per-use permission prompts for tools the server operator has already classified.

Details:
- Applied at session start from the server's tool list
- Maps into `alwaysAllowRules.mcpServerPolicy`, `alwaysDenyRules.mcpServerPolicy`, and `alwaysAskRules.mcpServerPolicy` in the session permissions object
- Only tools with `scope: "dynamic"` in the active server config are processed
- Highest-priority policy wins if the same tool appears multiple times

Evidence: Policy value strings (search for `"always_allow"`) in the new `ZTr`/`Sms` functions


## Improvements


### Design-Login MCP Authentication

MCP servers configured with `first_party_design_auth` now automatically authenticate using your stored `/design-login` credential, matching the behavior of `claude login` for first-party servers. If the credential is rejected (HTTP 401 or 403), the error message now directs you to run `/design-login` from an interactive session to re-authorize.

Evidence: Auth type string (search for `"first_party_design_auth"`) and re-auth message (search for `"Run /design-login from an interactive session"`)


### Compliance Taint Notifications

When the compliance subsystem marks the current session with a taint (a restriction flag applied by your organization), a notification now appears in the UI: `<taint name> · some features are restricted · /status for details`. The notification fires immediately and re-queues if preempted.

Evidence: Notification key prefix (search for `"compliance-taint-"`) and status hint string (search for `"some features are restricted"`)


### Voice Mode Policy Message

When voice mode is blocked by your organization's policy, Claude Code now shows "Voice mode is disabled by your organization's policy." instead of the generic "Voice mode is not available." message.

Evidence: New policy-specific error string (search for `"Voice mode is disabled by your organization's policy"`)


### Files API Unavailability Messages

Two new error messages surface Files API restrictions that were previously silent failures:

- "Files API is unavailable for HIPAA-regulated organizations"
- "Files API is unavailable on third-party providers (data-residency)"

Evidence: Search for `"Files API is unavailable"`


### Config File Auto-Repair

When `saveConfigWithLock` reads a corrupted config during a lock cycle, it now automatically repairs from the in-memory cached config rather than failing. The repair is logged at warn level referencing GH #3117.

Evidence: Repair log message (search for `"saveConfigWithLock: re-read hit a parse error; auto-repairing"`)


### GitHub App Install Link Improvement

The GitHub app installation URL is now referenced from a shared constant rather than duplicated inline, ensuring the link is consistent across the "autofix" webhook message and the repo-level error message. The autofix message now names the specific `{owner}/{repo}` where the app needs to be installed.

Evidence: Link constant and new autofix message (search for `"Autofix is on, but webhook events won't arrive until"`)


### Vim Mode Hint in Completions Menu

When vim keybindings are active, the completions menu and suggestion overlay now show a dim hint "Esc i / for slash commands" to help new vim-mode users discover how to enter slash commands.

Evidence: Hint string (search for `"esc i / for slash commands"`)


### Linux File Manager Integration

On Linux desktops with an active session (DISPLAY or WAYLAND\_DISPLAY), Claude Code can now open files directly in the native file manager using the D-Bus `org.freedesktop.FileManager1.ShowItems` interface instead of falling back to generic browser-open behavior.

Evidence: D-Bus interface string (search for `"org.freedesktop.FileManager1.ShowItems"`)


### Sandbox Filesystem "Relaxed" Policy Mode

A new `filesystemPolicy: "relaxed"` value in settings disables filesystem sandbox restrictions (sets `disabled: true` on the sandbox filesystem config). This is intended for environments where the sandbox is managed externally.

Evidence: Policy value string (search for `"filesystemPolicy"`) — the relaxed branch adds `{ disabled: true }` to the filesystem config


### Windows Drive-Relative Path Safety Check

Paths of the form `C:path` (a drive letter followed by a relative path, with no leading slash) are now explicitly rejected on Windows with a clear explanation: "Path '…' is drive-relative (resolves against the per-drive current directory, which cannot be statically validated) and requires manual approval." Previously these could be accepted with unpredictable resolution.

Evidence: Error message (search for `"drive-relative"`)


### Scroll Height High-Water Mark

The scroll container now tracks a high-water mark for scroll height when sticky scroll is disabled, preventing layout jumps when content is removed above the current view.

Evidence: Internal change in scroll container update logic (search for `"scrollHeightHwm"`)


## Bug Fixes

- Fixed sandbox ask-callback: previously approved hosts were not being cached between requests in the same session, causing redundant approval prompts for the same host (search for `"addSessionAllowedHost"`)
- Fixed permission dialog description sanitization — agent descriptions are now run through the script-control-character filter (`pw()`) before display, preventing hidden control characters from appearing in approval dialogs (search for `"script contains control characters that would be hidden"`)
- Fixed MCP completions filtering to exclude model-specific tool names using an explicit allowlist (search for `"Nns"` allowlist)


## Removed

### Memory Synthesis UI

The "Recalled from memory" display that appeared in conversation turns — including the [Good] / [Bad] rating buttons and source citation tracking — has been removed. The underlying memory file system still exists; only the inline recall annotation and its feedback mechanism were removed.

Evidence: Removed `pGa` component contained strings `"Recalled from memory"` and `"tiny_memory"` rating type


### Memory Prompt Templates

Internal system prompt templates for the memory subsystem were removed, including the "Dream: Memory Pruning" background task that periodically pruned stale memory files. This is an internal architectural change; user-visible memory behavior (reading and writing CLAUDE.md) is unchanged.

Evidence: Removed `TAi` function contained `"# Dream: Memory Pruning"` string


### Insights HTML Report Generator

The internal function that generated a "Claude Code Insights" HTML report (with project area breakdowns, friction analysis, feature suggestion cards, and time-of-day histograms) was removed. This was a server-side analytics tool, not a user-facing CLI command.

Evidence: Removed `mwf` function contained `"Claude Code Insights"` string


### Sandbox Schema `.describe()` Strings

The verbose Zod `.describe()` documentation strings on the sandbox configuration schema (covering network allow/deny domains, filesystem paths, credential handling, Windows WFP settings, etc.) were removed. The schema itself remains; only the inline documentation strings were dropped, likely moved to external documentation.

Evidence: Large `H8r` initializer removed, containing strings like `"Domains to route through the MITM proxy"` and `"Windows-specific settings"`


Generated with:
- tool: `harness-investigations@0c752ef-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.191.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.191.txt`
