# Changelog for version 2.1.174

## Summary

This release ships the claude.ai Projects integration — a new built-in tool that lets Claude read and write knowledge docs in the Project attached to the current session. It also adds a `/design-sync` skill for pushing React design systems to claude.ai/design, GLOBSTAR (`**`) support in permission patterns, and a mouse-wheel scroll acceleration setting. The advisor model now enforces a capability hierarchy so a weaker model cannot advise a stronger one.


## New Features


### Projects Tool (claude.ai Projects integration)

What: A new `Projects` tool lets Claude read and write knowledge documents inside the claude.ai Project attached to the current session. Project docs persist across sessions and surfaces (Claude chat, Claude Code, Cowork), so anything written here is visible to the user and their team in claude.ai.

Usage:

The tool is automatically available when a session is started inside a claude.ai Project. Claude dispatches on the `method` field:

- `project_info` — reads the project name, description, instructions, and full doc list
- `project_read` — reads one doc by path; large docs are written to a local temp file
- `project_search` — queries the project knowledge base (RAG-style) for relevant snippets
- `project_write` — creates or replaces a doc; pass `content` for inline text or `local_path` for a file on disk (uploaded directly, never entering context)
- `project_delete` — deletes a doc by path

Details:
- Requires a claude.ai login with subscription. Bedrock, Vertex, and other third-party providers are not supported.
- The OAuth token is automatically upgraded to include `user:projects:read` and `user:projects:write` scopes when needed.
- A budget guard tracks knowledge size and refuses writes that would push the project past the chat-injection threshold (~50k tokens). At that point, chats in the project switch from direct-injection to retrieval. Pass `force: true` to override (tradeoff is explicitly stated in the error message). There is also a hard cap; writes past it always fail.
- Agent-written docs (bare filename passed to `project_write`) land in the `claude/` namespace by default, so they're distinguishable from user uploads.
- Security: project docs may be written by other org members or other sessions. Claude treats their contents as data, not instructions.
- Blocked by HIPAA compliance policy (`allow_projects_tool` org flag), `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, or non-claude.ai providers.

Evidence: "read and write the session's attached claude.ai project" tool description (search for `"user:projects:read"`); `ProjectsApiError` class (search for `"ProjectsApiError"`); project context injected into system prompt (search for `"## When to use the Projects tool"`)


### Design Sync Skill (`/design-sync`)

What: A new built-in skill that converts a React design system into the format claude.ai/design consumes, then uploads it so the Claude Design agent builds UIs with the customer's actual components.

Usage:
```
/design-sync
```

Details:
- Supports two source shapes: Storybook-based repos and bare npm packages (auto-detected).
- For each component, emits a compiled bundle (`_ds_bundle.js`), props interface (`<Name>.d.ts`), usage reference (`<Name>.prompt.md`), and a preview card (`<Name>.html`).
- First sync: creates a new claude.ai/design project, runs a self-heal loop to fix validation errors, then optionally authors rich preview cards from the repo's own usage examples and grades them on an absolute rubric before upload.
- Re-sync: fetches `_ds_sync.json` from the remote project to compute exactly what changed, verifies only changed components, and uploads the diff.
- Writes `.design-sync/config.json` (converter config) and `.design-sync/NOTES.md` (repo-specific quirks) for reproducible future runs.

Evidence: skill definition (search for `"Push a React design system to claude.ai/design"`); `"design-sync"` skill name in the `Px9` variable


### Mouse Wheel Scroll Acceleration

What: A new settings field `wheelScrollAccelerationEnabled` ramps up scroll speed when the mouse wheel is moved quickly in fullscreen mode.

Usage:

Add to your settings file (or configure via `/config`):
```json
{
  "wheelScrollAccelerationEnabled": true
}
```

Details:
- Only applies in fullscreen (TUI) mode.
- Pairs with the existing `autoScrollEnabled` setting.

Evidence: new schema field (search for `"Ramp mouse-wheel scroll speed during fast scrolls"`)


### GLOBSTAR (`**`) Support in Permission Patterns

What: File patterns in permission rules now support `**` (GLOBSTAR) for recursive directory matching, matching paths at any depth.

Usage:
```json
{
  "permissions": {
    "allow": ["Read(src/**/*.ts)"]
  }
}
```

Details:
- Previously `*` only matched within a single directory level; `**` now matches across directory separators.
- Affects both tool permission rules and any other file-glob patterns Claude Code evaluates.

Evidence: `"\x00GLOBSTAR\x00"` replacement in pattern-matching function; `"/(?:.*/)?"`  insertion for `**` tokens


## Improvements


### Advisor Model Capability Enforcement

What: The advisor tool now validates that the advisor model is at least as capable as the main model, using a ranked capability hierarchy.

Details:
- New capability ranks: haiku-4-5 (1) < sonnet-4-6 (2) < opus-4-6 (3) < opus-4-7/4-8 (4) < fable-5/mythos-5 (5).
- If the advisor is less capable, Claude skips it for the main model with a warning: "X cannot advise Y (the advisor must be at least as capable as the main model). The advisor will not be used for the main model."
- Subagents may still use the advisor even when the main model won't.
- Background sessions (`CLAUDE_CODE_SESSION_KIND=bg`) now log a warning instead of hard-failing, so long-running jobs don't abort due to a misconfigured advisor.
- The 400 error message when the advisor is incompatible now includes actionable guidance: suggests `/advisor` for interactive sessions, or changing the `advisorModel` setting / `--advisor` flag for non-interactive use.

Evidence: `"cannot advise"` string; `"advisor must be at least as capable as the base model"` string; `"change or unset the advisorModel setting (or the --advisor flag)"` string


### Model Fallback: New Triggers and Better Messages

What: The model fallback system now handles two additional trigger types: `server_error` (retryable 5xx errors) and `last_resort` (non-retryable errors on the primary model).

Details:
- Old triggers: `model_not_found`, `permission_denied`, `overloaded`.
- New triggers: `server_error` (switches to fallback after repeated 5xx); `last_resort` (switches when primary returns a non-retryable error).
- The `last_resort` notification message now appends a truncated version of the underlying error to help diagnose why the switch happened.
- The `model_fallback` event schema is updated; consumers of the raw CCR event stream will see new trigger values.

Evidence: `"last_resort"` in the fallback trigger enum; `"server_error"` in the same enum; message in `V0f` function (search for `"Switched to"`)


### Opus 4.6 Fast Mode Deprecation Notice

What: Users running Claude Code with Opus 4.6 as the primary model will see a deprecation warning for "fast mode" (non-extended-thinking operation), with the planned removal date.

Details:
- The notice appears as an immediate-priority warning banner.
- Removal date is controlled by the `tengu_sunset_penguin_opus46` feature flag (server-set default: June 29, 2026).
- No notice is shown if the date has already passed, or if Opus 4.6 is not the active model.

Evidence: `"Opus 4.6 fast mode is deprecated and will be removed on"` string in the new `zwq` function


### tool_reference Blocks Now Available on Haiku 4.5

What: The unsupported-feature message for `tool_reference` content blocks now lists Claude Haiku 4.5 as a supported model.

Details:
- Old message: "This feature is only available on Claude Sonnet 4+, Opus 4+, and newer models."
- New message: "This feature is available on Claude Sonnet 4+, Opus 4+, Haiku 4.5+, and newer models."

Evidence: updated string (search for `"Haiku 4.5+"`)


### skillOverrides Enforcement

What: When a skill is disabled via `skillOverrides` in settings, running it now returns a clear error message instead of silently failing or executing.

Details:
- Interactive mode: "Skill X is disabled via skillOverrides. Re-enable it in /skills or remove the override from your settings to run it."
- Non-interactive / headless mode: "Skill X is disabled via skillOverrides. Remove the override from your settings to run it."
- Any arguments passed to the disabled skill are echoed back as a warning so the caller can see what was attempted.

Evidence: `"is disabled via skillOverrides. Re-enable it in /skills"` string


### Windows PowerShell Guidance Improved

What: The Bash tool now provides more precise guidance for Windows users who have PowerShell as their primary shell.

Details:
- The tool description now explicitly says "This tool runs Git Bash (POSIX sh), not cmd.exe or PowerShell" and lists concrete translation rules.
- When PowerShell is detected as primary, an additional note warns against using PowerShell here-strings (`@'…'@`) or backtick line continuation — recommending heredocs for multiline strings instead.

Evidence: `"This tool runs Git Bash (POSIX sh), not cmd.exe or PowerShell"` string; `"Do not use PowerShell here-strings"` string


### Artifact Conflict Detection

What: When two sessions race to publish an artifact and one gets behind, Claude now receives a structured conflict error with guidance on how to reconcile the edit.

Details:
- Error message: "conflict: another session published a newer version of this artifact. Re-read the current content (WebFetch the URL), reconcile your edits, then publish again."
- The error includes the live current content so Claude can merge rather than blindly overwrite.

Evidence: `"conflict: another session published a newer version of this artifact"` string in the new `K04` constant


### Org Admin Per-Tool Permission Ceiling

What: MCP server tool definitions now carry an `org_max_permission` field that lets org admins cap how permissive a tool can be, even in auto mode.

Details:
- New field on per-tool permission policy: `org_max_permission: "allow" | "ask" | "blocked"`.
- When set to `"ask"`, auto-mode silently prompt-suppresses to "ask" — the user always gets a confirmation dialog regardless of their personal settings.
- Set via the `mcp_set_servers` structured-IO message.

Evidence: `"Org admin's per-tool ceiling. Drives the auto-mode isOrgAskCeiling gate"` describe string


### Resolved Model Reported in Agent Spawns

What: The `agent_progress` notifications and `async_launched` status objects now include a `resolvedModel` field showing the actual model used by the spawned agent.

Details:
- Useful when the requested model falls back to another (e.g., overloaded Opus → Sonnet).
- Exposed in the `TaskOutput` event stream and the agent result object.

Evidence: `"Model the spawn resolved (may differ from the requested one)"` describe string in the schema


### --input-format=stream-json Validation Improved

What: Using `--input-format=stream-json` without `--print` now produces a clear error instead of a confusing mismatch about output format.

Details:
- Old error: "Error: --input-format=stream-json requires output-format=stream-json."
- New error: "Error: --input-format=stream-json requires --print."

Evidence: `"Error: --input-format=stream-json requires --print."` string


### Structured IO Environment Variable Allowlist

What: The `update_environment_variables` structured-IO message now validates keys against an allowlist, refusing any key not explicitly permitted.

Details:
- Currently allowed keys: `CLAUDE_CODE_SESSION_ACCESS_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`.
- Refused keys generate a log warning: `[structuredIO] refused update_environment_variables for non-allowlisted keys: <keys>`.
- This is a security improvement for managed Claude Code deployments that inject variables via the structured-IO channel.

Evidence: `"[structuredIO] refused update_environment_variables for non-allowlisted keys:"` string; `"CLAUDE_CODE_SESSION_ACCESS_TOKEN"` in the allowlist


### Background Session Auth Env Var Isolation

What: Subagent background processes now have provider-managed authentication environment variables stripped from their environment, preventing credential leakage through the process tree.

Details:
- Strips `ANTHROPIC_UNIX_SOCKET`, `CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST`, `CLAUDE_CODE_HOST_AUTH_ENV_VAR`, and the variable named in `CLAUDE_CODE_HOST_AUTH_ENV_VAR`.
- Applies when the host auth environment is detected (`QXq` check).

Evidence: `"CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"` in env-var filtering logic


## Bug Fixes

- Background control server bind errors now log a warning instead of crashing the server process. Previously a bind failure on the IPC socket would propagate as an unhandled error. (search for `"bg control server bind:"`)

- Skill file-change detection now correctly compares content hash maps by value, preventing spurious "skill list unchanged — skipping re-announce" false positives when skill files actually changed. (search for `"fs event(s) but skill list unchanged"`)


## In Development

Features with infrastructure added but not yet enabled.


### CCR Remote Recap / Away Summary [In Development]

What: When a CCR session goes idle and a new turn is not yet running, Claude can generate a recap summary of what it accomplished and surface it to the session as metadata.

Status: Feature-flagged (server-controlled)

Details:
- Recap generation is gated by the `tengu_harbor_moth` flag (default false). Users can also force it on with `CLAUDE_CODE_ENABLE_REMOTE_RECAP=1`.
- Only fires when the session has the "ccr" capability and `onMetadataChanged` is registered.
- The recap is dropped if a new turn starts before generation completes.
- Infrastructure complete; needs server-side flag to enable.

Evidence: `tengu_harbor_moth` flag in `dy5()` function; `"[awaySummary] ccr recap dropped: new turn already running"` string


### Malformed Tool Use Clean Retry [In Development]

What: When the model produces a response that contains an `<invoke>` XML tag (a sign of a malformed legacy tool-use format) instead of a proper tool call, Claude Code would retry the turn with a corrective prompt.

Status: Feature-flagged (server-controlled, default false)

Details:
- Gated by `tengu_malformed_tool_use_clean_retry` flag (default: false).
- Detection heuristic: scans the last text block of the conversation for `<invoke` patterns.
- Retry message: "The previous response failed to produce a valid tool call. Please retry the tool call now."
- Prevents these malformed responses from stalling the session.

Evidence: `tengu_malformed_tool_use_clean_retry` flag in `yQ4()`; `<invoke\\b` regex in `SQ4`; `"The previous response failed to produce a valid tool call"` string (in string diff)


### Claude-in-Slack Priority Routing [In Development]

What: Infrastructure for routing Slack human-turn messages with higher priority in the CCR turn queue, ensuring responses to live Slack users are not delayed by background batch work.

Status: Dark-launched (infrastructure present, not yet activated for external sessions)

Details:
- Introduces a `slack_human` inbound origin type.
- Turns from Slack human users with `verifiedSlackHumanTurn: true` are given `"later"` priority in the drain queue to allow them to be promoted ahead of other pending work.
- New helper `pB$` checks whether any in-flight drain batch contains a Slack human turn.

Evidence: `L_A = "slack_human"` constant; `"verifiedSlackHumanTurn"` field check; `X_A = new Set(["claude-in-slack", "claude_in_slack"])` set


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.174-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.174.txt`
