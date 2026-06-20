# Changelog for version 0.140.0

## Official Release Highlights

These changes appear in the upstream release notes (tag `rust-v0.140.0`, 2026-06-15) and have been verified against the diff.


### Token Usage Views (`/usage`)

What: New `/usage` command in the TUI shows token consumption over daily, weekly, and cumulative periods.

Details:
- Displays token activity for the current session and across sessions
- Three time scopes: daily, weekly, and cumulative


### Goal Input Improvements (`/goal`)

What: The `/goal` input area now handles large text, multi-line pastes, and images more reliably.

Details:
- Large text no longer truncates or misbehaves on paste
- Image attachments supported via `/goal` (consistent with inline message input)


### Permanent Session Deletion

What: Sessions can now be permanently deleted from the CLI, TUI, and programmatically via the app-server protocol.

Usage:
```bash
# Force-delete by UUID (no confirmation prompt)
codex delete --force <session-uuid>

# Delete by name (requires interactive confirmation)
codex delete <session-name>
```

TUI: type `/delete` within a session.

Details:
- `codex delete` subcommand with optional `--force` flag (UUID targets only; names require interactive confirmation)
- App-server RPC `thread/delete` deletes a thread and all sub-agent threads; server emits `thread/deleted` notifications for each removed thread ID
- Subagent threads are cleaned up before the root thread is removed; in-flight agents receive a stop signal before deletion proceeds
- Schema types: `ThreadDeleteParams`, `ThreadDeleteResponse`, `ThreadDeletedNotification` in `codex-rs/app-server-protocol/`

Code references:
- `DeleteCommand` in `codex-rs/cli/src/main.rs`
- `thread_delete` handler in `codex-rs/app-server/src/request_processors/thread_delete.rs`
- `ThreadDeleteParams` / `ThreadDeleteResponse` / `ThreadDeletedNotification` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- Schema files: `codex-rs/app-server-protocol/schema/json/v2/ThreadDeleteParams.json`, `ThreadDeleteResponse.json`, `ThreadDeletedNotification.json`


### Claude Code Session Import (`/import`)

What: New `/import` command lets you import a Claude Code session into Codex.

Details:
- Brings conversation history from Claude Code into the active Codex session


### Unified Mentions Menu (`@`) Now Default

What: The `@` mentions menu (unified file/symbol/context picker) is enabled by default, no longer behind an experimental flag.

Details:
- Previously required opt-in; now active in all TUI sessions


### Amazon Bedrock API-Key Authentication

What: Codex can now authenticate with Amazon Bedrock using a bearer API key, stored encrypted in a local secrets keychain.

Details:
- New auth mode `bedrockApiKey` in the protocol (enum variant `AuthMode::BedrockApiKey`) stores an API key and region
- Credentials are persisted to an encrypted local secrets store (`SecretsKeyringAuthStorage` via the `codex-secrets` crate) rather than plain JSON
- Auth backend selection: `AuthKeyringBackendKind::Direct` (legacy plaintext) vs. `AuthKeyringBackendKind::Secrets` (new encrypted default)
- `AuthMode::uses_codex_backend()` helper distinguishes Codex-managed vs. externally-managed auth

Code references:
- `BedrockApiKeyAuth` / `login_with_bedrock_api_key()` in `codex-rs/login/src/auth/bedrock_api_key.rs`
- `SecretsKeyringAuthStorage` / `AuthKeyringBackendKind` in `codex-rs/login/src/auth/storage.rs`
- `AuthMode::BedrockApiKey` in `codex-rs/app-server-protocol/src/protocol/v2.rs`


### SQLite Auto-Recovery

What: Corrupted or inaccessible SQLite databases are now automatically repaired rather than requiring manual intervention.

Details:
- On failure, Codex backs up the existing database file to a unique path and rebuilds a fresh database
- Handles the edge case where the database path is occupied by a directory instead of a file
- Previously required a user confirmation prompt for repair; now fully automatic


### `/review` Crash Fix

What: Pressing Esc while a `/review` is in progress no longer crashes the TUI.

Details:
- Queued guidance is now preserved correctly when the review is interrupted


### MCP Reliability Improvements

What: Model Context Protocol connections are more resilient to transient failures and misconfigured OAuth.

Details:
- Transient HTTP failures are retried automatically
- Servers with unusable OAuth credentials are now reported as logged-out rather than silently failing
- Disabled MCP servers are preserved across configuration reloads (were previously being dropped)


### Plugin Fixes

What: Two plugin management bugs fixed.

Details:
- Remote plugin uninstall route was broken and has been fixed
- Auth requirements are now surfaced at install time rather than failing silently after installation


### Update Dismissal Persistence

What: Dismissing an update notification now persists correctly across sessions.

Details:
- Previously, dismissed update prompts could reappear
- Stale hook row indicator is also cleared after acknowledgment


### Non-TTY Ctrl-C for Background Commands

What: Ctrl-C now correctly terminates background shell commands when Codex is not attached to a TTY.


### Performance Improvements

Details:
- Git fsmonitor is no longer reset on each invocation (preserves the daemon across Codex runs)
- Duplicate feature-rollout reads eliminated
- Archive session lookup is faster
- Turn-diff rendering result is cached to avoid redundant recomputation


### Realtime Voice Removed

What: The `/realtime` voice conversation feature has been removed from the TUI.

Details:
- All audio dependencies (`alsa`, `cpal`, `coreaudio-rs`, `oboe`, `dasp_sample`) and the `codex-realtime-webrtc` crate have been removed from the workspace
- The `RealtimeConversationArchitecture` enum and related `ThreadRealtimeStartParams` fields remain in the protocol for possible future use by external clients


## Additional Changes Beyond Official Notes


### Sub-Agent Activity Thread Items

What: The protocol now surfaces sub-agent lifecycle events as `SubAgentActivity` items in thread history.

Details:
- New `SubAgentActivityThreadItem` variant added to `ThreadItem` in all thread-response schemas
- `SubAgentActivityKind` enum: `started`, `interacted`, `interrupted`
- Each item carries `id`, `kind`, `agentThreadId`, and `agentPath` fields
- Clients that iterate `ThreadItem` arrays must handle the new variant

Code references:
- `SubAgentActivity` / `SubAgentActivityKind` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- `codex-rs/app-server-protocol/schema/json/v2/` (all thread-response schemas updated)


### `ThreadSource` Is Now an Open String

What: The `threadSource` field in thread metadata changed from a closed enum to an open string type, adding an extensible `Feature(String)` variant.

Details:
- Previous values `user`, `subagent`, and `memory_consolidation` remain valid
- Clients must now handle unknown string values without rejecting the response
- The Rust type uses `TryFrom<String>` with a `Feature(String)` fallback for unrecognised values

Code references:
- `ThreadSource` in `codex-rs/app-server-protocol/src/protocol/v2.rs`


### `AppSummary` Schema Change

What: `AppSummary` loses the `needsAuth` boolean field and gains a nullable `category` string field.

Details:
- `needsAuth: boolean` is removed — clients that read this field must be updated
- `category: string | null` is added; `AppTemplateSummary` also gains `category`

Code references:
- `AppSummary` in `codex-rs/app-server-protocol/schema/json/v2/`


### Auto-Resolution Timeout for User-Input Tool Requests

What: `ToolRequestUserInputParams` has a new optional `autoResolutionMs` field that lets the server specify how long to wait before automatically resolving a user-input prompt.

Code references:
- `ToolRequestUserInputParams.auto_resolution_ms` in `codex-rs/app-server-protocol/src/protocol/v2.rs`


### Remote Control Ephemeral Mode

What: The remote-control enable/disable RPCs now accept an `ephemeral` boolean that controls whether the state change persists across restarts.

Details:
- `RemoteControlEnableParams` / `RemoteControlDisableParams` both carry `ephemeral: boolean`
- The Rust daemon uses a new `RemoteControlStartupMode` enum (`EnabledEphemeral`, `DisabledEphemeral`, `ResolvePersisted`) to track this at runtime
- A dedicated `REMOTE_CONTROL_DISABLED_ENV_VAR` environment variable allows daemon-level disable
- Backward compatibility: callers that send no params still work via `NullableRemoteControlEnableParams` / `NullableRemoteControlDisableParams` wrappers
- `ConfigRequirements.allowRemoteControl` is a new optional field clients can send during initialisation

Code references:
- `RemoteControlEnableParams` / `RemoteControlDisableParams` / `RemoteControlStartupMode` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- `codex-rs/app-server-daemon/` remote-control handling


### Plugin Share URL

What: `PluginDetail` has a new optional `shareUrl` string field.

Code references:
- `PluginDetail.shareUrl` in `codex-rs/app-server-protocol/schema/json/v2/`


### Apps Default Config: Approvals Reviewer

What: `AppsDefaultConfig` gains an optional `approvals_reviewer` field for specifying which reviewer to use for app approval flows.

Code references:
- `AppsDefaultConfig.approvals_reviewer` in `codex-rs/app-server-protocol/schema/json/v2/`


### Fatal Exit Now Shows Session ID

What: When Codex exits fatally and no resume hint is available, it now prints the session UUID so the session can be resumed or deleted later.

Code references:
- Fatal-exit path in `codex-rs/cli/src/main.rs`


### Direct Input to Multi-Agent v2 Sub-Agents Rejected

What: Attempts to send direct app-server input to a v2 multi-agent sub-agent now fail with a clear error rather than silently misbehaving.


## In Development

These features have protocol or infrastructure support added in this release but are not yet enabled by default.


### Background Terminal APIs [Experimental]

What: Two new RPCs for listing and terminating background terminal sessions attached to a thread.

Status: Marked experimental in the `client_request_definitions!` macro; not wired to stable client flows.

Details:
- `thread/backgroundTerminals/list` → `ThreadBackgroundTerminalsListParams` / `ThreadBackgroundTerminalsListResponse`
- `thread/backgroundTerminals/terminate` → `ThreadBackgroundTerminalsTerminateParams` / `ThreadBackgroundTerminalsTerminateResponse`

Code references:
- `ThreadBackgroundTerminal` and related types in `codex-rs/app-server-protocol/src/protocol/v2.rs`


### Capability Root Selection [Experimental]

What: `ThreadStartParams` gains a `selectedCapabilityRoots` field for explicitly specifying which filesystem roots the agent operates on.

Status: Marked experimental; the field is optional and ignored unless the server is built with the relevant experimental flag.

Details:
- `SelectedCapabilityRoot` / `CapabilityRootLocation` types describe root paths and their roles

Code references:
- `ThreadStartParams.selected_capability_roots` in `codex-rs/app-server-protocol/src/protocol/v2.rs`


### Realtime Conversation Architecture Selection [In Development]

What: `ThreadRealtimeStartParams` gains `architecture`, `model`, and `version` fields to support multiple realtime backends (`realtimeapi`, `avas`).

Status: Infrastructure added; the `/realtime` TUI command has been removed. These fields are available to external clients that invoke the realtime RPC directly.

Details:
- `RealtimeConversationArchitecture` enum: `realtimeapi`, `avas`
- `ThreadRealtimeAppendTextParams.role` field (`ConversationTextRole`: `user` or `developer`, default `user`)

Code references:
- `RealtimeConversationArchitecture` / `ThreadRealtimeStartParams` / `ConversationTextRole` in `codex-rs/app-server-protocol/src/protocol/v2.rs`


### Code Mode Host and Protocol Crates [In Development]

What: Two new workspace crates (`codex-code-mode-host`, `codex-code-mode-protocol`) lay groundwork for a dedicated "code mode" execution path.

Status: Added to the workspace but not integrated into any user-facing command or server endpoint.

Code references:
- `codex-rs/code-mode-host/`, `codex-rs/code-mode-protocol/`


## Notes

Breaking protocol changes in this release that client authors must handle:

- `AppSummary.needsAuth` is removed. Clients that read this field to gate authentication flows must be updated before connecting to a v0.140.0 server.
- `ThreadSource` is now an open string. Clients that exhaustively match the previous closed enum (`user`, `subagent`, `memory_consolidation`) must add a catch-all branch for unknown values (the new `Feature(String)` variant and any future additions).
- `ThreadItem` now includes a `SubAgentActivity` variant. Clients that pattern-match on `ThreadItem` without a default branch will break on threads that contain sub-agent activity events.

---

Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/changes/changes-v0.140.0-2.diff` (filtered astdiff)
- official release notes: `archive/codex/changes/release-notes-v0.140.0.md`
