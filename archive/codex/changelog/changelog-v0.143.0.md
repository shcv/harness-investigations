# Changelog for version 0.143.0

## Summary

This release enables remote plugins by default with richer TUI catalog rows, npm marketplace sources, and visible version information. It also adds system-proxy routing for authentication and Responses API traffic on macOS and Windows, a `codex remote-control pair` command for manual pairing, Amazon Bedrock `max` reasoning effort as a first-class preset, and new app-server RPCs for environment inspection, ancestor thread listing, and fork-by-turn-id.

## Official Release Highlights

### Remote Plugins Enabled by Default

Remote plugin catalogs are now active without any configuration opt-in. The TUI plugin popup displays richer catalog rows including the plugin's remote and local version side-by-side, and npm marketplace sources are listed explicitly (e.g., `npm · @acme/figma-plugin@^1.2.0`). Admin-installed plugins now carry an "Installed by admin" label in the detail view.

The `PluginSummary` schema gains a `version` field (remote marketplace version) alongside the existing `localVersion`. Clients reading `plugin/list` or `plugin/installed` responses should treat both as optional strings.

Code references:
- `PluginSummary.version` in `codex-rs/app-server-protocol/schema/json/v2/PluginListResponse.json`
- TUI snapshots in `codex-rs/tui/src/chatwidget/snapshots/`


### System Proxy Routing (macOS and Windows)

Codex can now route authentication and Responses API traffic through macOS and Windows system proxies, including PAC and WPAD configurations. When `respect_system_proxy = true` is set in config, a unified `HttpClientFactory` with `OutboundProxyPolicy::RespectSystemProxy` selects system/PAC/WPAD settings first, falls back to environment variables, then falls back to a direct connection.

Config:
```toml
respect_system_proxy = true
```

Code references:
- `OutboundProxyPolicy` enum in `codex-rs/http-client/src/outbound_proxy.rs`
- `HttpClientFactory` in `codex-rs/http-client/src/outbound_proxy.rs`
- `Config::http_client_factory()` in `codex-rs/config/src/lib.rs`


### `codex remote-control pair`

A new `pair` subcommand generates a manual pairing code from a running daemon without needing the ChatGPT app to initiate the flow. The output is a short alphanumeric code (e.g., `ABCD-EFGH`) for out-of-band entry.

Usage:
```bash
codex remote-control pair
```

With JSON output for programmatic use:
```bash
codex remote-control pair --json
```

Code references:
- `RemoteControlSubcommand::Pair` in `codex-rs/cli/src/remote_control_cmd.rs`
- `start_remote_control_pairing()` in `codex-rs/app-server-daemon/`
- `format_remote_control_pairing_output()` in `codex-rs/cli/src/remote_control_cmd.rs`


### Amazon Bedrock: `max` Reasoning Effort as First-Class Preset

GPT-5.6 Sol, Terra, and Luna models on Amazon Bedrock now list `max` reasoning effort as an explicit preset ("`ReasoningEffort::Max`") rather than as a custom string. The TUI model-selection menu shows `Max` in the reasoning effort list alongside `High`, `Extra high`, etc.

Code references:
- `ReasoningEffort::Max` in `codex-rs/model-provider/src/amazon_bedrock/catalog.rs`
- `gpt_5_6_bedrock_model()` helper updated to push `ReasoningEffort::Max` preset


### MCP Tool Search Enabled by Default

MCP tools now use tool search by default. ChatGPT-hosted MCP servers can explicitly opt into session authentication via a new `auth: chatgpt` config key. This replaces the previous OAuth-only default for servers on the trusted first-party ChatGPT origin.

Config (to use ChatGPT session auth for a hosted MCP server):
```toml
[mcp.servers.my-chatgpt-server]
transport = { type = "streamable_http", url = "https://chatgpt.com/..." }
auth = "chatgpt"
```

Details:
- The `auth` field defaults to `"oauth"` (existing behavior). Set to `"chatgpt"` only for servers hosted on the ChatGPT origin.
- If the server URL does not match the ChatGPT origin, the setting is silently downgraded to `"oauth"`.
- Session auth falls back to stored OAuth credentials when no ChatGPT session provider is available.

Code references:
- `McpServerAuth` enum in `codex-rs/config/src/lib.rs`
- Session auth wiring in `codex-rs/mcp/src/mcp_manager.rs`


### App-Server: Inspect Environments, List Descendant Threads, Fork to a Turn

Three new experimental app-server capabilities:

**`environment/info`** — Connect to a configured execution environment and return its detected shell and working directory.

```json
{"method": "environment/info", "id": 1, "params": {"environmentId": "env_abc"}}
{"id": 1, "result": {"shell": {"name": "bash", "path": "/bin/bash"}, "cwd": "file:///home/user/project"}}
```

**`thread/list` with `ancestorThreadId`** — List all spawned descendants of a thread at any depth, not just direct children. The ancestor itself is excluded; each result's `parentThreadId` still points to its immediate parent.

```json
{"method": "thread/list", "id": 2, "params": {"ancestorThreadId": "thread-root-id", "limit": 25}}
```

**`thread/fork` with `lastTurnId`** — Fork a thread's history only up to and including a specific turn. Turns after `lastTurnId` are omitted from the fork.

```json
{"method": "thread/fork", "id": 3, "params": {"threadId": "thread-abc", "lastTurnId": "turn-xyz"}}
```

Code references:
- `EnvironmentInfoParams` / `EnvironmentInfoResponse` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- `ClientRequest::EnvironmentInfo => "environment/info"` in `codex-rs/app-server-protocol/src/lib.rs`
- `ancestor_thread_id` on `ThreadListParams` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- `last_turn_id` on `ThreadForkParams` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- Schema files: `codex-rs/app-server-protocol/schema/json/v2/ThreadForkParams.json`


## Improvements


### `thread/items/list` Replaces `thread/turns/items/list`

The experimental method was renamed from `thread/turns/items/list` to `thread/items/list` and its scope was broadened. Previously it returned an unsupported-method error. Now it pages full persisted items across a thread, with an optional `turnId` filter.

```json
{"method": "thread/items/list", "id": 25, "params": {"threadId": "thr_123", "limit": 100}}
```

Omit `turnId` to page across all turns. Thread stores that do not support pagination return JSON-RPC `-32601`.

Note: Clients calling `thread/turns/items/list` must update to `thread/items/list`. The old method name is gone.

Code references:
- `ClientRequest::ThreadItemsList => "thread/items/list"` in `codex-rs/app-server-protocol/src/lib.rs`
- `ThreadItemsListParams` in `codex-rs/app-server-protocol/src/protocol/v2.rs`


### `SessionBudgetExceeded` Surfaced as Distinct Error

When a session's token budget is exhausted, Codex now reports `CodexErrorInfo::SessionBudgetExceeded` rather than `TurnAborted`. Clients listening for `codexErrorInfo` on turn events should handle the new value.

Code references:
- `CodexErrorInfo::SessionBudgetExceeded` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- `CodexErrKind::SessionBudgetExceeded` in `codex-rs/analytics/src/facts.rs`
- `codex-rs/core/src/session/rollout_budget.rs`


### Plugin Install Policy Source in API Responses

`plugin/list` and `plugin/installed` responses now include an optional `installPolicySource` field indicating whether a plugin's install policy originates from a workspace admin setting (`WORKSPACE_SETTING`) or automatic canonical-app promotion (`IMPLICIT_CANONICAL_APP`). Local plugins return `null`. The TUI plugin detail popup displays "Installed by admin" when this is `WORKSPACE_SETTING`.

Code references:
- `PluginInstallPolicySource` in `codex-rs/app-server-protocol/schema/json/v2/PluginListResponse.json`
- `installPolicySource` on `PluginInstalledResponse` schema


### MCP Startup Failure Reason in Notifications

The `MCP server status` notification now includes a nullable `failureReason` field. Currently the only value is `reauthenticationRequired`, used when an MCP server requires re-authentication to start.

Code references:
- `McpServerStartupFailureReason` in `codex-rs/app-server-protocol/schema/json/v2/`
- `failureReason` on `McpServerStatusNotification` schema


### `--permission-profile` Flag Standardized

The `codex sandbox`, `codex exec`, and related subcommands previously used `--permissions-profile` (plural). The canonical flag is now `--permission-profile` (singular). The plural form is kept as a hidden alias so existing scripts continue to work.

```bash
codex sandbox --permission-profile :workspace -- echo hello
```

Code references:
- `#[arg(long = "permission-profile", alias = "permissions-profile")]` in `codex-rs/cli/src/main.rs`


### `multi_agent_mode_hint_text` Config Key

A new `multi_agent_mode_hint_text` field in `[features.multi_agent_v2]` lets operators customize the hint text displayed when multi-agent mode is active. An empty string suppresses the default text.

Config:
```toml
[features.multi_agent_v2]
multi_agent_mode_hint_text = "Custom delegation guidance for your team."
```

Code references:
- `MultiAgentV2Config::multi_agent_mode_hint_text` in `codex-rs/config/src/lib.rs`


### npm Plugin Marketplace Sources

Marketplace manifest files can now declare npm packages as plugin sources in addition to Git repositories.

```json
{
  "type": "npm",
  "package": "@acme/figma-plugin",
  "version": "^1.2.0",
  "registry": null
}
```

`version` accepts npm version selectors. `registry` is an optional HTTPS URL; authentication stays in the user's npm config.

Code references:
- `MarketplacePluginSource::Npm` in `codex-rs/core-plugins/src/marketplace/provider.rs`
- `materialize_npm_plugin_source()` in `codex-rs/core-plugins/src/npm_source.rs`
- `NpmPluginSource` in `codex-rs/app-server-protocol/schema/json/v2/PluginListResponse.json`


### Safety Buffering Retry Prompt in TUI

When the model response enters safety buffering, the TUI now shows a dedicated popup: "This request requires additional safety checks." When a retry model is available, the user is offered "Retry with a faster model" or "Keep waiting." The completed safety-buffering prompt is now correctly dismissed when the safety check resolves.

Code references:
- TUI snapshot `codex_tui__chatwidget__tests__safety_buffering_retry_prompt` in `codex-rs/tui/src/chatwidget/snapshots/`
- Fix: `codex-rs/tui/src/chatwidget/` (clear completed safety buffering prompt)


### Provider-Aware Model Fallback for Thread Start [Experimental]

A new `allowProviderModelFallback` boolean on `thread/start` allows a provider with an authoritative static model catalog (e.g., Amazon Bedrock) to substitute its default model when the requested model is unavailable, rather than returning an error. Defaults to `false`.

```json
{"method": "thread/start", "params": {"allowProviderModelFallback": true, ...}}
```

Code references:
- `ThreadStartParams::allow_provider_model_fallback` in `codex-rs/app-server-protocol/src/protocol/v2.rs`


### Thread History Mode for New Threads [Experimental]

`thread/start` now accepts a `history_mode` parameter (`"legacy"` or `"paginated"`) that sets the thread's persisted history contract. The mode is immutable after the thread is created. Currently only `"legacy"` is accepted; `"paginated"` is reserved for future use.

```json
{"method": "thread/start", "params": {"historyMode": "legacy", ...}}
```

Code references:
- `ThreadHistoryMode` enum in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- `ThreadStartParams::history_mode` in `codex-rs/app-server-protocol/src/protocol/v2.rs`


### Thread Originator Preserved in Analytics Per Thread

Analytics events now carry the `product_client_id` of the originating connection on a per-thread basis rather than using a single connection-wide value. This means multi-client setups correctly attribute thread events (turn, compaction, tool items, reviews) to the originator that started each thread.

Code references:
- `ThreadAnalyticsState::originator` in `codex-rs/analytics/src/reducer.rs`
- `AnalyticsEventsClient::track_response_with_thread_originator()` in `codex-rs/analytics/src/client.rs`


## Bug Fixes

- Windows ConPTY input handling: line-feed and CRLF sequences are now normalized to carriage return (required by ConPTY), and backspace is encoded as DEL. (`codex-rs/windows-sandbox-rs/src/conpty/`)

- Stale TUI safety prompt: the safety-buffering prompt is now cleared when the safety check completes, so it no longer blocks further input. (`codex-rs/tui/src/chatwidget/`)

- Cancelled review leaving MCP startup busy: when a pending review is cancelled, the MCP startup busy indicator is now correctly cleared. (`codex-rs/tui/`)

- Remote-control token refresh retry storms: the remote-control server no longer spins on token refresh when it repeatedly fails, preventing runaway retry loops. (`codex-rs/remote-control/`)

- Trailing realtime transcript text preserved: the tail of a realtime transcript is now flushed before session shutdown, preserving buffered text that would otherwise be dropped. (`codex-rs/exec-server/`)

- Incremental WebSocket requests: response metadata (e.g., request IDs) is now ignored during incremental request comparison, fixing spurious mismatches that degraded streaming success rates. (`codex-rs/remote-control/`)

- Rate-limit errors now include `creditId` and `resetCreditDetails`: the `ConsumeAccountRateLimitResetCredit` endpoint accepts a nullable `creditId` parameter, and rate-limit responses preserve credit count when fetching reset-credit details fails. (`codex-rs/app-server-protocol/src/protocol/v2.rs`)

- `OnFailure` approval policy replaced by `OnRequest` in default test fixtures: internal test scaffolding was using `OnFailure` which no longer exists; updated to `OnRequest`. (Internal only, no user-facing behavior change.)

- Windows sandbox credential retry: Windows-Apps launch failures no longer trigger credential refresh, preventing unnecessary re-authentication on transient launch errors. (`codex-rs/exec-server/`)


## In Development


### Thread History: `paginated` Mode [In Development]

The `historyMode: "paginated"` value on `thread/start` is defined in the schema but not yet accepted by the server. Threads with paginated history will use `thread/items/list` for history hydration instead of the legacy inline `items` array on `Turn`.

Status: Runtime-gated — `"paginated"` value is currently rejected at thread creation time with a validation error.

Code references: `ThreadHistoryMode::Paginated` in `codex-rs/app-server-protocol/src/protocol/v2.rs`


### Code-Mode V8 JIT Control [In Development]

The code-mode runtime exposes `initialize_v8(V8JitMode::Disabled)` for environments where JIT compilation is prohibited. When called before any code-mode execution, V8 starts in `--jitless` mode. Code mode continues to work; only JIT-compiled paths are disabled.

Status: API is present and tested but not wired to any user-facing flag or config key yet.

Code references: `V8JitMode` / `initialize_v8()` in `codex-rs/code-mode/src/v8_init.rs`


### Standalone Code-Mode Process Host [In Development]

A new `codex-code-mode-host` crate provides an out-of-process code-mode session that communicates over IPC. The host binary is bundled in release packages. The in-process session provider (`InProcessCodeModeSessionProvider`) remains the default; the standalone host is not yet wired into the main execution path.

Status: Crate compiled and bundled but not activated by default.

Code references: `codex-code-mode-host/` crate, `codex-rs/code-mode/src/remote_session.rs`


### `thread/start.allowProviderModelFallback` [Experimental]

The `allowProviderModelFallback` parameter requires `capabilities.experimentalApi` to be enabled. Amazon Bedrock is currently the only provider with an authoritative static catalog that can supply a fallback model.

Status: Behind `#[experimental("thread/start.allowProviderModelFallback")]`.

Code references: `ThreadStartParams::allow_provider_model_fallback` in `codex-rs/app-server-protocol/src/protocol/v2.rs`


## Notes

### `thread/rollback` Deprecated

`thread/rollback` is marked deprecated and will be removed in a future release. Clients should stop calling this method.


### `thread/turns/items/list` Renamed

The experimental method `thread/turns/items/list` no longer exists. Clients must migrate to `thread/items/list`. The new method also supports cross-turn pagination; omit `turnId` to page all items in a thread.


### `thread/list` with `parentThreadId` vs. `ancestorThreadId`

`parentThreadId` (direct children only) and `ancestorThreadId` (all descendants) are mutually exclusive. Sending both is invalid. The documentation example has been updated to use `ancestorThreadId` for the multi-level case.


### Security: `quick-xml`, `crossbeam-epoch`, `Hono`, `fast-uri`, OpenSSL

Dependencies updated to address security advisories: `quick-xml` upgraded to 0.41.0 (RUSTSEC-2026-0194, RUSTSEC-2026-0195 acknowledged for transitive users via `plist` and `wayland-scanner`), `crossbeam-epoch` to 0.9.20 (RUSTSEC-2026-0204), and JavaScript dependencies `Hono` and `fast-uri` updated.


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.143.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.143.0.md`
