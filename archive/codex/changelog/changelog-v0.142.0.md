# Changelog for version 0.142.0

## Summary

This release delivers six major features: usage-limit credit redemption from `/usage`, a reorganized `/plugins` panel with curated/workspace/shared sections, configurable rollout token budgets that abort turns when exhausted, per-thread and per-turn multi-agent delegation mode, an indexed web-search mode, and scheduled time reminders. It also fixes Linux TUI rendering after Ctrl+Z suspension, improves exec-server resilience across disconnects, and hardens remote environment support for native paths, shells, and AGENTS.md loading.

## Official Release Highlights

### Redeem usage-limit reset credits from /usage

What: The `/usage` command now opens a menu with two options: "Show usage" (the previous default) and "Redeem usage limit reset". Selecting the redemption option checks available credits, shows how many you have, and lets you confirm spending one to reset your current usage window. The menu re-fetches credit availability when it opens if none are known.

Details:
- Shows credit count with singular/plural labeling ("1 reset" vs "2 resets")
- Adapts the reset description based on your plan type (monthly vs. 5-hour/weekly windows)
- Handles the confirmation flow with retry and an updated count after redemption
- If the backend check fails, shows a "Couldn't load" error and lets you try again
- A hint badge appears in the chat transcript when resets become available

Code references:
- `open_usage_menu()` / `show_rate_limit_reset_loading_popup()` / `finish_rate_limit_reset_credits_refresh()` in `codex-rs/tui/src/chatwidget/usage.rs` (new file)
- `ConsumeRateLimitResetCredit` / `RefreshRateLimits` in `codex-rs/tui/src/app_event.rs`


### /plugins panel organized into OpenAI Curated, Workspace, and Shared with me sections

What: The `/plugins` overlay now groups remote plugins into labeled sections rather than a flat list, and eligible agent turns can recommend and install plugins inline.

Details:
- Sections: OpenAI Curated, Workspace (directory-scoped), Shared with me, Shared with me (link), Local, and generic Other
- Workspace and Shared sections show a loading shimmer while the remote catalog fetches, and fall back to a descriptive empty state if none are available
- Sections are ordered: Workspace → Shared with me → Local → Other/Curated
- Plugin recommendations from the model appear during turns that involve matching tool usage, with a one-click install prompt
- Plugin install errors are now reported with a download status preserved in the UI rather than silently swallowed

Code references:
- New file `codex-rs/tui/src/chatwidget/plugin_catalog.rs` (1996 lines) with `MarketplaceProduct` enum (`OpenAiCurated`, `Workspace`, `SharedWithMe`, `SharedWithMeLink`, `Local`, `Other`)
- `REMOTE_MARKETPLACE_SECTIONS` in same file
- `REMOTE_WORKSPACE_MARKETPLACE_NAME`, `REMOTE_WORKSPACE_SHARED_WITH_ME_MARKETPLACE_NAME` in `codex-rs/core-plugins/`


### Configurable rollout token budgets

What: Rollout token budgets track cumulative token usage across agent threads within a rollout and abort turns when the budget is exhausted. Remaining-budget reminders are sent at configurable thresholds.

Details:
- Budget is tracked across all agent turns in the rollout
- Configurable reminder thresholds notify the agent when nearing the limit
- Turns are aborted (not paused) when the budget is fully consumed
- A compaction reminder is injected into context based on the token budget

Code references: `codex-rs/core/` and `codex-rs/app-server/` (rollout budget PRs #28746, #28494, #28707, #29255, #29423)


### Multi-agent delegation mode (per-thread and per-turn)

What: App-server clients can now configure how aggressively the model delegates to sub-agents, independently at the thread level and overridden at the turn level.

Details:
- Three values: `none` (tools available, no delegation instructions injected), `explicitRequestOnly` (delegate only when explicitly asked), `proactive` (delegate when it would help)
- Thread-level default set in `thread/start` or `thread/resume` params
- Turn-level override sent in `turn/start` params
- The effective mode is reflected in thread start/resume/fork responses as `multi_agent_mode`

Usage:
```json
{"method": "thread/start", "params": {"multiAgentMode": "proactive", ...}}
{"method": "turn/start", "params": {"multiAgentMode": "explicitRequestOnly", ...}}
```

Code references:
- New `MultiAgentMode` type in `codex-rs/app-server-protocol/schema/json/v2/ThreadStartParams.json` and `TurnStartParams.json`
- New `MultiAgentMode` TypeScript type in `codex-rs/app-server-protocol/schema/typescript/MultiAgentMode.ts`
- `multi_agent_mode` field added to `ThreadStartResponse`, `ThreadResumeResponse`, `ThreadForkResponse`


### Indexed web-search mode

What: A new `indexed` web-search mode permits live search queries while restricting direct page access to server-approved URLs only, sitting between the existing `cached` (no live queries) and `live` (full access) modes.

Usage:
```json
{"webSearchMode": "indexed"}
```

Code references:
- `WebSearchMode` enum in `codex-rs/app-server-protocol/schema/typescript/WebSearchMode.ts` updated from `"disabled" | "cached" | "live"` to `"disabled" | "cached" | "indexed" | "live"`
- Same change in `codex-rs/app-server-protocol/schema/json/v2/ConfigReadResponse.json` and `ConfigRequirementsReadResponse.json`


### Scheduled time reminders and current-time queries

What: Codex can now receive UTC time reminders at scheduled intervals and query the current wall-clock time directly, including through a client-provided clock injected via the app-server.

Details:
- App-server exposes a clock tool that agents can call to get the current UTC time
- Clients can supply their own clock implementation through the app-server API
- Config enables per-session time reminder scheduling

Code references: `codex-rs/app-server/` (PRs #28822, #28824, #28835, #29011 — clock, time reminder config, and app-server wiring)


### Bug Fixes (Official)

- Linux TUI rendering is now reliable after suspending with Ctrl+Z and resuming with `fg`. After `suspend_process()` returns, the TUI re-applies raw mode, re-probes the cursor position (accounting for the shell's job-control output), and flushes stale buffered input before resuming rendering. (`codex-rs/tui/src/tui/job_control.rs`)

- Exec-server processes and stdio MCP sessions now survive transient network disconnects. Sessions reconnect automatically after disconnect, signed URLs are refreshed on reconnect, and stdin writes use a retry-safe path. (PRs #28512, #28374, #28546, #28895)

- Remote environments now receive the correct working directory in executor-native path syntax, load AGENTS.md from foreign host filesystems, inherit the executor's native shell, preserve sandbox intent across the exec-server boundary, and report sandbox denials with semantic error types rather than opaque failures. (PRs #28146, #28152, #28958, #28983, #29099, #29108, #29113, #29424)

- Plugin loading now handles root-level marketplace layouts (not just nested), supports manifests that supply a list of skill paths rather than a single path, falls back to an alternate manifest path when the primary is absent, reports download errors with an actionable message, and immediately refreshes tool caches after a remote install. (PRs #28771, #28789, #28790, #28863, #28951)

- Parent agents now receive terminal subagent errors in their context. Previously, a subagent that exited with an error would look like an empty successful completion to the orchestrator. (PR #28375, `codex-rs/core/`)

- Goal-first threads are now persisted to the thread store and returned by `thread/list` and `thread/search`. (PR #28808)


## Additional Changes Beyond Official Notes


### Amazon Bedrock credential source exposed in account/read

What: The `account/read` response for Amazon Bedrock accounts now includes a `credentialSource` field indicating whether credentials are managed by Codex or by the AWS SDK.

Details:
- Values: `"codexManaged"` or `"awsManaged"` (default)
- Allows clients to display which credential path is active

Code references:
- New `AmazonBedrockCredentialSource` type in `codex-rs/app-server-protocol/schema/typescript/AmazonBedrockCredentialSource.ts`
- `credentialSource` field in `Account.amazonBedrock` variant of `codex-rs/app-server-protocol/schema/typescript/v2/Account.ts`
- Schema: `codex-rs/app-server-protocol/schema/json/v2/GetAccountResponse.json`


### New JSON-RPC method: account/workspaceMessages/read

What: Clients can fetch workspace-scoped messages (headlines and announcements) from the backend via a new request method. The TUI uses this to display a headline in the status line, refreshed every five minutes.

Usage:
```json
{"method": "account/workspaceMessages/read", "params": null}
```

Response:
```json
{
  "featureEnabled": true,
  "messages": [
    {"messageId": "id", "messageType": "headline", "messageBody": "...", "createdAt": 1234567890}
  ]
}
```

Details:
- `messageType` is `"headline"`, `"announcement"`, or `"unknown"`
- `featureEnabled: false` means the backend route is not available for this client; clients should suppress the UI element rather than retry
- TUI polls every 5 minutes (`WORKSPACE_HEADLINE_REFRESH_INTERVAL`) and shows the first non-empty headline in the status line

Code references:
- New schema `codex-rs/app-server-protocol/schema/json/v2/GetWorkspaceMessagesResponse.json`
- New TypeScript types `GetWorkspaceMessagesResponse`, `WorkspaceMessage`, `WorkspaceMessageType` in `codex-rs/app-server-protocol/schema/typescript/v2/`
- `account/workspaceMessages/read` request added to `codex-rs/app-server-protocol/schema/json/ClientRequest.json`
- TUI implementation in `codex-rs/tui/src/workspace_messages.rs` (new file) and `codex-rs/tui/src/chatwidget/status_surfaces.rs`


### New JSON-RPC method: externalAgentConfig/import/readHistories

What: Clients can retrieve the history of completed external agent config import operations, including per-item-type success and failure records.

Usage:
```json
{"method": "externalAgentConfig/import/readHistories", "params": null}
```

Response schema: `ExternalAgentConfigImportHistoriesReadResponse` — an array of `ExternalAgentConfigImportHistory` objects, each containing `importId`, `completedAtMs`, `successes[]`, and `failures[]` keyed by item type (AGENTS_MD, CONFIG, SKILLS, PLUGINS, MCP_SERVER_CONFIG, SUBAGENTS, HOOKS, COMMANDS, SESSIONS).

Code references:
- New schema `codex-rs/app-server-protocol/schema/json/v2/ExternalAgentConfigImportHistoriesReadResponse.json`
- `externalAgentConfig/import/readHistories` request added to `codex-rs/app-server-protocol/schema/json/ClientRequest.json`


### New notification: externalAgentConfig/import/progress

What: The server now emits live progress updates while an `externalAgentConfig/import` operation is running, rather than only the final `completed` notification.

Notification:
```json
{
  "method": "externalAgentConfig/import/progress",
  "params": {
    "importId": "...",
    "itemTypeResults": [{"itemType": "PLUGINS", "successes": [...], "failures": [...]}]
  }
}
```

Code references:
- New schema `codex-rs/app-server-protocol/schema/json/v2/ExternalAgentConfigImportProgressNotification.json`
- `ExternalAgentConfigImportProgressNotification` TypeScript type in `codex-rs/app-server-protocol/schema/typescript/v2/`
- `externalAgentConfig/import/progress` notification added to `codex-rs/app-server-protocol/schema/json/ServerNotification.json`


### New notification: model/safetyBuffering/updated

What: The server now emits a notification when model safety buffering state changes during a turn, giving clients visibility into when output is being held back and why.

Notification:
```json
{
  "method": "model/safetyBuffering/updated",
  "params": {
    "threadId": "...",
    "turnId": "...",
    "model": "gpt-5.5",
    "reasons": ["..."],
    "useCases": ["..."]
  }
}
```

Code references:
- New schema `codex-rs/app-server-protocol/schema/json/v2/ModelSafetyBufferingUpdatedNotification.json`
- `ModelSafetyBufferingUpdatedNotification` TypeScript type in `codex-rs/app-server-protocol/schema/typescript/v2/`
- `model/safetyBuffering/updated` notification added to `codex-rs/app-server-protocol/schema/json/ServerNotification.json`


### MCP tool-call items gain structured app context

What: MCP tool call items in thread history now carry an `appContext` object with `connectorId`, `linkId`, and `resourceUri`, replacing the deprecated flat `mcpAppResourceUri` field.

Details:
- `appContext.connectorId` is required; `linkId` and `resourceUri` are optional
- `mcpAppResourceUri` remains present for backward compatibility but is now documented as deprecated
- Affects `ItemCompletedNotification`, `ItemStartedNotification`, `ThreadListResponse`, and other responses that embed history items

Code references:
- New `McpToolCallAppContext` type in `codex-rs/app-server-protocol/schema/json/v2/ItemCompletedNotification.json` and TypeScript equivalent `codex-rs/app-server-protocol/schema/typescript/v2/McpToolCallAppContext.ts`
- `appContext` field added to MCP tool call thread items in all response schemas embedding `ThreadItem`


### MCP server openai/form elicitation capability

What: Clients can now declare support for the `openai/form` extended elicitation mode at initialize time. When enabled, MCP servers may send `openai/form` mode elicitation requests (in addition to the standard `form` mode) to collect structured input.

Usage:
```json
{"method": "initialize", "params": {"capabilities": {"mcpServerOpenaiFormElicitation": true}}}
```

Details:
- Off by default; clients must explicitly opt in
- When enabled, elicitation requests may carry `"mode": "openai/form"` with a `requestedSchema` payload

Code references:
- `mcp_server_openai_form_elicitation: bool` field on `InitializeCapabilities` in `codex-rs/app-server-client/src/lib.rs`
- `mcpServerOpenaiFormElicitation` in `codex-rs/app-server-protocol/schema/json/v1/InitializeParams.json` and all v2 schemas
- `openai/form` mode variant added to `McpServerElicitationRequestParams` schemas
- `mcp_server_openai_form_elicitation` in `codex-rs/app-server-protocol/schema/typescript/v2/McpServerElicitationRequestParams.ts`


### Permission profiles now report availability

What: `PermissionProfileSummary` in the `permissions/list` response now includes an `allowed` boolean indicating whether the current requirement constraints permit selecting that profile.

Details:
- `allowed: false` means the profile exists but cannot be selected given active session requirements (e.g., a minimum sandbox level is mandated)
- Clients should visually disable or grey out profiles where `allowed` is false

Code references:
- `allowed: boolean` added to `PermissionProfileSummary` in `codex-rs/app-server-protocol/schema/json/v2/PermissionProfileListResponse.json`
- TypeScript: `codex-rs/app-server-protocol/schema/typescript/v2/PermissionProfileSummary.ts`


### Thread recency ordering

What: Threads now carry a `recencyAt` timestamp for sidebar ordering, and `thread/list` accepts `recency_at` as a sort key.

Details:
- `recencyAt` is a nullable Unix timestamp (seconds) that reflects the most recent meaningful activity, which may differ from `updatedAt`
- `ThreadSortKey` gains a `recency_at` value alongside `created_at` and `updated_at`
- Reflects work from #28671 (restore thread recency with compatible migration history)

Code references:
- `recencyAt` field in `Thread` type across all response schemas (`ThreadListResponse.json`, `ThreadReadResponse.json`, `ThreadStartResponse.json`, `ThreadResumeResponse.json`, `ThreadForkResponse.json`, etc.)
- `recency_at` variant in `ThreadSortKey` in `codex-rs/app-server-protocol/schema/json/v2/ThreadListParams.json`
- TypeScript: `recencyAt` in `codex-rs/app-server-protocol/schema/typescript/v2/Thread.ts`, `ThreadSortKey.ts`


### Apps default config gains default_tools_approval_mode

What: The `apps._default` config block now accepts a `default_tools_approval_mode` field of type `AppToolApproval | null`, allowing a per-app default tool approval behavior to be set alongside existing fields like `destructive_enabled`.

Code references:
- `default_tools_approval_mode` field in `AppsDefaultConfig` schema in `codex-rs/app-server-protocol/schema/json/v2/ConfigReadResponse.json`
- TypeScript: `codex-rs/app-server-protocol/schema/typescript/v2/AppsDefaultConfig.ts`


### ConversationTextRole gains assistant variant

What: The `ConversationTextRole` enum now includes an `"assistant"` variant alongside `"user"` and `"developer"`, enabling conversation text items to be attributed to the assistant in the response history.

Code references:
- `ConversationTextRole` in `codex-rs/app-server-protocol/schema/json/ClientRequest.json` and consolidated schemas


### ChatGPT account email is now optional

What: The `email` field on the `chatgpt` account variant in `account/read` is now `string | null` rather than a required string, allowing Codex to support ChatGPT accounts that have no associated email address.

Code references:
- `email: string | null` in `codex-rs/app-server-protocol/schema/typescript/v2/Account.ts`
- `AgentIdentityJwtClaims.email: Option<String>` in `codex-rs/agent-identity/src/lib.rs`
- PR #28991


### Response item id fields are now nullable

What: The `id` field on several raw response item variants in the protocol is now `string | null` instead of required `string`. The `id` field is also no longer required in the JSON schema for the function call output item. Clients should handle absent IDs gracefully.

Code references: `codex-rs/app-server-protocol/schema/json/v2/RawResponseItemCompletedNotification.json` and all schemas embedding raw response items.


### response item metadata field renamed

What: The internal `metadata` field on raw response items (previously `ResponseItemMetadata`) is renamed to `internal_chat_message_metadata_passthrough` and typed as `InternalChatMessageMetadataPassthrough`. The old `ResponseItemMetadata` type is removed. The `writeOnly: true` constraint is also dropped from several status fields.

Details:
- Existing clients reading the `metadata` field must update to `internal_chat_message_metadata_passthrough`
- The type shape is identical (`{ turn_id: string | null }`)

Code references:
- `InternalChatMessageMetadataPassthrough` type in `codex-rs/app-server-protocol/schema/json/v2/RawResponseItemCompletedNotification.json` and all schemas embedding response items
- TypeScript: `codex-rs/app-server-protocol/schema/typescript/InternalChatMessageMetadataPassthrough.ts` (new file), `ResponseItemMetadata.ts` removed


### Truncated tool output carries a warning prefix and original token count

What: When code-mode or shell tool output is truncated, the formatted message now begins with `Warning: truncated output (original token count: N)` on its own line before the existing `Total output lines: M` line. The token count is computed on the original (pre-truncation) content, giving the model accurate sizing information.

Code references:
- `formatted_truncate_text()` in `codex-rs/utils/output-truncation/src/lib.rs`


### /resume blocked while a turn is pending or running

What: The `/resume` slash command is now blocked both while a task is running and while a user turn is pending start or an agent turn is already running, preventing double-submission. Previously the block only applied when a task was marked running.

Code references:
- `slash_command_blocked_by_active_task()` in `codex-rs/tui/src/chatwidget/slash_dispatch.rs`


### /model, /personality, and /permissions now defer input until settings apply

What: Opening the model, personality, or permissions popup via slash command now defers any queued input until the settings change is confirmed, preventing input from being submitted before the new setting takes effect.

Code references:
- `defer_input_until_settings_applied()` calls added in `codex-rs/tui/src/chatwidget/slash_dispatch.rs`


### externalAgentConfig/import gains source field

What: The `externalAgentConfig/import` request params now accept an optional `source` string identifying which product generated the migration items (e.g., `"claude"`, `"cursor"`). Import failure records also now carry an `errorType` field for programmatic error classification.

Code references:
- `source` field in `ExternalAgentConfigImportParams` in `codex-rs/app-server-protocol/schema/json/v2/ExternalAgentConfigImportParams.json`
- `errorType` field in `ExternalAgentConfigImportItemTypeFailure`


### C++ module files highlighted in TUI diff view

What: The TUI diff renderer now applies syntax highlighting to `.ixx` C++ module interface files (Visual C++ module extension), in addition to existing `.cpp`/`.cc`/`.cxx` extensions.

Code references: `codex-rs/tui/src/render/highlight.rs`


## Notes

Migration guidance for protocol clients:

- The `metadata` field on raw response items is renamed to `internal_chat_message_metadata_passthrough`. Update any client code that reads this field by name.
- The `id` field on some raw response item variants is now nullable. Clients that assumed it was always present should add null checks.
- `mcpAppResourceUri` on MCP tool call items is deprecated; prefer `appContext.resourceUri`.
- `ApiPathString` is renamed to `LegacyAppPathString` in all schemas. The wire shape is identical (plain string), but TypeScript imports from `./ApiPathString` must update to `./LegacyAppPathString`.
- `RealtimeConversationArchitecture` is removed; the enum is no longer part of the protocol surface.
- `ResponseItemMetadata` TypeScript type is removed; replace with `InternalChatMessageMetadataPassthrough`.


Generated with:
- tool: `harness-investigations@0c752ef-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.142.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.142.0.md`
