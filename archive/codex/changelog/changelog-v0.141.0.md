# Changelog for version 0.141.0

## Summary

This release establishes authenticated, end-to-end encrypted Noise relay channels as the default remote executor transport, extends cross-platform remote execution with native working-directory and shell preservation, and adds several new app-server API surfaces: filtering threads by parent, consuming rate-limit reset credits, appending speech in realtime sessions, and detailed import-result accounting. Plugin discovery gains a "created-by-me" remote marketplace, executor plugins can now activate their stdio MCP servers per thread, and the TUI adds an auto-resolution countdown for user-input prompts.

## Official Release Highlights

### Encrypted Noise relay channels for remote executors

Remote executors now communicate over authenticated, end-to-end encrypted Noise protocol relay channels by default. Each connection uses a per-harness identity (`NoiseChannelIdentity`) and a pinned executor public key (`NoiseChannelPublicKey`); the websocket carries only ciphertext after the handshake completes.

App-server embedders that manage remote environments call `EnvironmentManager::upsert_noise_environment()` to register an environment backed by a `NoiseRendezvousConnectProvider`. The provider supplies a fresh `NoiseRendezvousConnectBundle` (URL, executor registration ID, pinned key, and harness-key authorization) for each physical reconnect while the harness identity persists across reconnects.

Code references:
- `NoiseRendezvousConnectProvider` trait and `NoiseRendezvousConnectBundle` in `codex-rs/exec-server/src/client_api.rs`
- `EnvironmentManager::upsert_noise_environment` in `codex-rs/exec-server/src/environment.rs`
- `NoiseChannelIdentity`, `NoiseChannelPublicKey`, `NoiseRendezvousConnectBundle`, `NoiseRendezvousConnectProvider` re-exported from `codex-rs/core-api/src/lib.rs`
- New `clatter` dependency (`Cargo.toml`) provides the Noise handshake implementation


### Cross-platform working-directory and shell preservation for remote execution

Exec-server now carries the executor's native working directory as a `PathUri` across the app-server/exec-server boundary, preserving whatever path convention the executor host uses (Windows, POSIX, or UNC). Filesystem permission paths in the protocol now use `ApiPathString` instead of `AbsolutePathBuf`, so paths round-trip without being re-interpreted by the harness host.

Code references:
- New `ApiPathString` type in `codex-rs/app-server-protocol/schema/typescript/ApiPathString.ts` and in `codex-rs/app-server-protocol/src/protocol/v2/permissions.rs`
- `AdditionalFileSystemPermissions.read`/`.write` fields changed from `Vec<AbsolutePathBuf>` to `Vec<ApiPathString>`
- Schema: `codex-rs/app-server-protocol/schema/json/v2/*.json` — `AbsolutePathBuf` refs replaced by `ApiPathString` in all permission-path fields


### Executor plugin stdio MCP servers active per thread

When a thread is started with `selectedCapabilityRoots` pointing to an executor plugin, that plugin's stdio MCP server declarations are now started inside the execution environment for that thread. HTTP MCP declarations remain inactive.

Code references:
- `codex-rs/app-server/README.md` (updated `thread/start` description)
- New `codex-rs/core-plugins/src/app_mcp_routing.rs` — `apply_app_mcp_routing_policy()` deduplicates conflicting App and MCP declarations when a plugin is active


### Plugin discovery: created-by-me remote marketplace and auth-specific curated catalog

Plugin listing now accepts `created-by-me-remote` as a `PluginListMarketplaceKind` value, letting clients request plugins the authenticated user has published. The API-curated marketplace is loaded according to the current auth mode so different account types receive appropriate catalog contents.

Code references:
- `PluginListMarketplaceKind` in `codex-rs/app-server-protocol/schema/typescript/v2/PluginListMarketplaceKind.ts` — new `"created-by-me-remote"` variant
- `codex-rs/app-server-protocol/schema/json/v2/PluginListParams.json` — enum updated


### Thread filtering by parent (experimental)

`thread/list` accepts a new experimental `parentThreadId` parameter. When set, the response returns only the direct spawned children of that thread, as recorded in persisted spawn-edge state. Review and Guardian threads are excluded because they do not participate in the spawn-edge lifecycle.

Usage:
```json
{
  "method": "thread/list",
  "id": 1,
  "params": {
    "parentThreadId": "thr_abc123"
  }
}
```

Code references:
- `ThreadListParams.parent_thread_id` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs` (`#[experimental("thread/list.parentThreadId")]`)
- `list_direct_children_of_thread()` in the thread-store SQLite layer


### External agent import result accounting

`externalAgentConfig/import` now returns an `importId` in its response so clients can correlate it with the completion notification. The `externalAgentConfig/import/completed` notification is no longer empty: it carries the same `importId` and an `itemTypeResults` array with per-item-type success and failure details.

Each entry in `itemTypeResults` includes:
- `itemType` — one of `AGENTS_MD`, `CONFIG`, `SKILLS`, `PLUGINS`, `MCP_SERVER_CONFIG`, `SUBAGENTS`, `HOOKS`, `COMMANDS`, `SESSIONS`
- `successes` — list of `ExternalAgentConfigImportItemTypeSuccess` (with `source`, `target`, `cwd`)
- `failures` — list of `ExternalAgentConfigImportItemTypeFailure` (with `failureStage`, `message`, `source`, `cwd`)

Code references:
- `ExternalAgentConfigImportResponse` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`
- `ExternalAgentConfigImportCompletedNotification`, `ExternalAgentConfigImportTypeResult`, `ExternalAgentConfigImportItemTypeSuccess`, `ExternalAgentConfigImportItemTypeFailure` in the same file
- Schema: `codex-rs/app-server-protocol/schema/json/v2/ExternalAgentConfigImportCompletedNotification.json`
- Schema: `codex-rs/app-server-protocol/schema/json/v2/ExternalAgentConfigImportResponse.json`


### Rate-limit reset credits

Clients can now read how many rate-limit reset credits an account has earned, and redeem them to reset an active rate-limit window.

`account/rateLimits/read` response gains `rateLimitResetCredits: RateLimitResetCreditsSummary | null` with `availableCount`.

New method `account/rateLimitResetCredit/consume` redeems one credit. The response `outcome` is one of:
- `"reset"` — a credit was consumed and the eligible windows were reset
- `"nothingToReset"` — no window is currently eligible for a reset
- `"noCredit"` — the account has no earned credits
- `"alreadyRedeemed"` — this idempotency key already completed a reset

Usage:
```json
{
  "method": "account/rateLimitResetCredit/consume",
  "id": 1,
  "params": { "idempotencyKey": "<uuid>" }
}
```

Code references:
- `ConsumeAccountRateLimitResetCreditParams`, `ConsumeAccountRateLimitResetCreditResponse`, `ConsumeAccountRateLimitResetCreditOutcome`, `RateLimitResetCreditsSummary` in `codex-rs/app-server-protocol/src/protocol/v2/account.rs`
- Schema: `codex-rs/app-server-protocol/schema/json/v2/ConsumeAccountRateLimitResetCreditParams.json`
- Schema: `codex-rs/app-server-protocol/schema/json/v2/ConsumeAccountRateLimitResetCreditResponse.json`
- Schema: `codex-rs/app-server-protocol/schema/json/v2/GetAccountRateLimitsResponse.json`


### Realtime: speech append, codex-response control, startup context toggle

Three additions to experimental realtime sessions:

`thread/realtime/appendSpeech` — new experimental method that appends text the realtime model should speak to the user. Returns `{}`.

```json
{
  "method": "thread/realtime/appendSpeech",
  "id": 1,
  "params": { "threadId": "thr_abc123", "text": "Your request is complete." }
}
```

`thread/realtime/start` gains two new optional parameters:
- `includeStartupContext: false` — omit Codex's generated startup context from the realtime session
- `codexResponsesAsItems: true` — send automatic Codex text responses as realtime conversation items instead of the default speakable output path; combine with `codexResponseItemPrefix` to prepend experiment instructions to those items

Code references:
- `ThreadRealtimeAppendSpeechParams` and `ThreadRealtimeAppendSpeechResponse` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `ThreadRealtimeStartParams.include_startup_context`, `.codex_responses_as_items`, `.codex_response_item_prefix` in the protocol v2 types


### TUI: auto-resolution timer for user-input prompts

`request_user_input` prompts in the TUI now auto-resolve after the configured inactivity period expires. A countdown message appears during the final 60 seconds ("auto-resolves in …") and pauses if the user interacts with the prompt.

Code references:
- `AutoResolutionTiming::VisibleCountdown` and `AUTO_RESOLUTION_VISIBLE_COUNTDOWN` in `codex-rs/tui/src/bottom_pane/request_user_input/mod.rs`


### Hook trust bypass preserved through codex exec thread start and resume

The hook trust bypass that allows non-interactive `codex exec` runs to skip hook confirmation prompts is now correctly propagated into threads started or resumed from `codex exec`. Previously, the bypass was dropped when the thread was (re-)initialized, causing hooks to prompt unexpectedly.

Code references: `codex-rs/core/` (trust bypass propagation on thread start/resume)


### Blocking PostToolUse hooks correctly reject code-mode tool calls

When a `PostToolUse` hook runs in blocking mode and sets a rejection, that rejection is now applied to code-mode tool calls. Previously, blocking rejections had no effect on code-mode paths.

Code references: `codex-rs/core/` (hook result application in code-mode paths)


### Plugin capabilities route consistently by authentication mode

Plugin auth capability filtering is now centralized: capabilities route based on the active auth mode, conflicting App and MCP server declarations from the same plugin are deduplicated, and the remote marketplace plugin ordering is preserved as delivered by the remote catalog.

Code references:
- `codex-rs/core-plugins/src/app_mcp_routing.rs` — `apps_route_available()` and `apply_app_mcp_routing_policy()`


### Windows sandbox: stale credential repair and yield floor

The Windows sandbox now automatically repairs stale sandbox credentials on startup instead of failing. PowerShell commands are given a longer yield floor before being moved to the background, reducing premature backgrounding under normal use.

Code references: `codex-rs/exec-server/` (Windows sandbox session runner, shared in new `codex-windows-sandbox` crate)


### Exec-server idle relay keepalives restored

The relay connection between the app-server and a remote exec-server now sends keepalive messages while idle, preventing the relay from dropping an established connection unnecessarily.

Code references: `codex-rs/exec-server/` (relay keepalive restore)


### Steer input interrupts wait_agent

`turn/steer` input now wakes an agent that is blocked in a `wait_agent` call, letting the turn respond immediately to new user input rather than waiting for the agent-wait to time out.

Code references: `codex-rs/core/` (steer channel wires into `wait_agent` poll)


### Bundled SQLite pinned to WAL-reset fix version

`libsqlite3-sys` is now pinned to 0.37, which bundles a SQLite version that includes the WAL-reset corruption fix. The `Cargo.toml` comment cites the fix directly: `https://www.sqlite.org/wal.html#the_wal_reset_bug`.

Code references: `codex-rs/Cargo.toml` — `libsqlite3-sys = { version = "0.37", ... }`


### TLS P-521 certificate support via aws-lc-rs

The TLS crypto provider has been switched from `ring` to `aws-lc-rs`. This adds support for P-521 certificate signatures, which are commonly used by enterprise proxies. No configuration change is required.

Code references: `codex-rs/Cargo.toml` — `rustls` feature changed from `"ring"` to `"aws_lc_rs"`


## Additional Changes Beyond Official Notes


### ResponseItemMetadata: turn_id on all response items

Every `ResponseItem` variant now carries an optional `metadata` field of type `ResponseItemMetadata`. Currently `metadata` has one field: `turn_id`, which links the item to the turn that produced it. This field is `null` for items that predate this release.

Clients that replay stored history or index items by turn can use `metadata.turn_id` directly instead of tracking turn boundaries separately.

Code references:
- `ResponseItemMetadata` in `codex-rs/app-server-protocol/schema/typescript/ResponseItemMetadata.ts`
- `ResponseItem` in `codex-rs/app-server-protocol/schema/typescript/ResponseItem.ts` — `metadata?: ResponseItemMetadata` on all variants
- Schema: `codex-rs/app-server-protocol/schema/json/v2/RawResponseItemCompletedNotification.json`


### DynamicToolSpec is now a discriminated union with explicit types

`DynamicToolSpec` changed from a plain object with an optional `namespace` field to a discriminated union. Clients that pass dynamic tools (via `thread/start` `dynamicTools`) must now include a `type` field.

Before:
```json
{
  "name": "lookup_ticket",
  "description": "Fetch a ticket by id",
  "inputSchema": { "type": "object", "properties": { "id": { "type": "string" } }, "required": ["id"] }
}
```

After — individual function tool:
```json
{
  "type": "function",
  "name": "lookup_ticket",
  "description": "Fetch a ticket by id",
  "inputSchema": { "type": "object", "properties": { "id": { "type": "string" } }, "required": ["id"] }
}
```

After — namespace grouping multiple tools:
```json
{
  "type": "namespace",
  "name": "tickets",
  "description": "Ticket management tools",
  "tools": [
    { "type": "function", "name": "lookup_ticket", "description": "...", "inputSchema": { ... } }
  ]
}
```

The old `namespace?: string` field on function tools is gone. Use the `"type": "namespace"` wrapper instead.

Code references:
- `DynamicToolSpec`, `DynamicToolFunctionSpec`, `DynamicToolNamespaceSpec`, `DynamicToolNamespaceTool` in `codex-rs/app-server-protocol/schema/typescript/v2/`
- Schema: `codex-rs/app-server-protocol/schema/json/v2/ThreadStartParams.json`


### MCP default tool timeout increased to 300 seconds

The default per-call timeout for MCP tool invocations has been raised from the previous value to 300 seconds, reducing timeout failures for long-running MCP tools.

Code references: `codex-rs/mcp/` (default timeout constant)


### Guardian review context isolated from skills and memories

The Guardian approval reviewer no longer includes skill definitions or long-term memory in its review context. This reduces noise in the reviewer's input and avoids leaking session-specific context into what should be a focused policy review.

Code references: `codex-rs/core/` (guardian review context builder)


### Remote plugin marketplace ordering preserved

Plugin listings from remote marketplaces now preserve the server-provided order rather than potentially reordering entries as they are merged into the local catalog.

Code references: `codex-rs/core-plugins/` (remote plugin directory merge)


## Bug Fixes

- External agent config import now returns an `importId` in the immediate response so clients can correlate subsequent `externalAgentConfig/import/completed` notifications even when the import completes asynchronously (`ExternalAgentConfigImportResponse` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`)
- `thread/realtime/start` no longer includes startup context when `includeStartupContext: false` is passed; previously this parameter had no effect (`ThreadRealtimeStartParams.include_startup_context` in `codex-rs/app-server-protocol/src/protocol/v2/`)
- Prompt image cache is now bounded at 64 MiB; feedback upload is limited to eight related threads (`codex-rs/core/`)
- Hook trust bypass now persists through `codex exec` thread start and resume (`codex-rs/core/`)
- Blocking `PostToolUse` hooks now correctly reject code-mode tool calls (`codex-rs/core/`)


## In Development

Features with full infrastructure merged but not yet enabled for general use.


### Sleep tool [In Development]

What: An agent-callable `sleep` tool that pauses execution for a specified duration. The sleep ends early if new input arrives for the active turn and returns elapsed wall-clock time.

Status: Runtime-gated by `Feature::SleepTool` (`stage: Stage::UnderDevelopment`, `default_enabled: false`). The tool is not visible unless the feature is explicitly enabled.

Details:
- `duration_ms` parameter; maximum 3,600,000 ms (one hour)
- Emits a `SleepThreadItem` (`{ "type": "sleep", id, durationMs }`) via `ItemStarted`/`ItemCompleted` notifications so clients can show a progress indicator
- Interrupted early if `turn/steer` input arrives while sleeping

Code references:
- `SleepHandler` in `codex-rs/core/src/tools/handlers/sleep.rs`
- `Feature::SleepTool` in `codex-rs/features/src/lib.rs`
- `SleepItem` in `codex-rs/protocol/src/items.rs`
- `ThreadItem::Sleep` in `codex-rs/app-server-protocol/src/protocol/v2/item.rs`
- Schema: `SleepThreadItem` in `codex-rs/app-server-protocol/schema/json/v2/ItemStartedNotification.json` (and related)


### Analytics event capture to file [Build-gated]

What: In debug builds (`#[cfg(debug_assertions)]`), analytics events can be captured to a local JSONL file instead of being sent over the network.

Status: Build-gated — only present in `debug_assertions` builds; release binaries are unaffected and the feature has no effect.

Details:
- Set `CODEX_ANALYTICS_EVENTS_CAPTURE_FILE=/path/to/output.jsonl` in debug builds to redirect analytics to a file
- Each batch is written as a newline-delimited JSON record; file is created with mode `0o600` on Unix
- Network delivery is disabled while capture is active

Code references:
- `ANALYTICS_EVENTS_CAPTURE_FILE_ENV_VAR` in `codex-rs/analytics/src/analytics_capture.rs`
- `AnalyticsEventsDestination::CaptureFile` variant in `codex-rs/analytics/src/client.rs`


## Notes

### DynamicToolSpec breaking protocol change

The `DynamicToolSpec` type changed from an object to a discriminated union. Clients that pass `dynamicTools` in `thread/start` must add `"type": "function"` to each tool spec. The old `namespace?: string` field is removed; tools that used it must now be wrapped in a `"type": "namespace"` spec. This change affects the `app-server-test-client` CLI as well — the `--dynamic-tools` flag now expects the new format.


### AdditionalFileSystemPermissions path type change

`AdditionalFileSystemPermissions.read` and `.write` changed from `Array<AbsolutePathBuf>` to `Array<ApiPathString>` in the TypeScript schema. Both are serialized as JSON strings; the semantic difference is that `ApiPathString` accepts any UTF-8 string without local-path validation and converts to/from `PathUri` explicitly. Clients that construct permission path lists should treat the field as an opaque path string at the API boundary.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.141.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.141.0.md`
