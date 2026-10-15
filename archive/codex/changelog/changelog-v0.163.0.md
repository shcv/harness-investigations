# Changelog for version 0.163.0

## Release Status

> **Not yet released:** `rust-v0.163.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

This unpublished development snapshot, compared with 0.162.1, adds an interactive `/config` panel, configurable leader shortcuts, plugin activation defaults, and a background-server restart action. It also enables existing Daybreak and Code Mode interruption features by default, improves thread listing and clipboard handling, and introduces experimental background compaction and thread read-state APIs.

The source tag `rust-v0.163.0` exists, but no published GitHub Release was found during the supplied sync. This changelog describes source changes; it does not imply that release binaries or assets were published.

## New Features


### Interactive configuration panel

What: `/config` provides a searchable interface for editing common terminal preferences.

Usage:
```text
/config
```

Details:

- Preferences are grouped under Appearance, Notifications, Input, Sessions, and Text selection.
- The panel opens existing editors for themes, keyboard shortcuts, status-line contents, and terminal titles.
- Other controls cover animations, tips, paste detection, Vim defaults, automatic recaps, session-picker layout, resume-directory behavior, and clipboard preferences.
- A notification test runs after five seconds, allowing time to switch applications.
- Changes are saved to the local user configuration. The panel reports save failures and settings overridden by another configuration layer.
- The underlying preferences and several individual editors already existed; the unified configuration browser is new.

Code references:

- `SlashCommand::Config` in `codex-rs/tui/src/slash_command.rs`
- `ConfigPanel` and `settings` in `codex-rs/tui/src/config_panel/mod.rs`
- `ChatWidget::open_config_panel` in `codex-rs/tui/src/chatwidget/config_panel.rs`
- `App::save_config_preference` in `codex-rs/tui/src/app/config_panel.rs`


### Persistent leader shortcuts

What: Keyboard bindings can share a configurable prefix using the symbolic `leader` syntax.

Usage:
```toml
[tui.keymap.global]
leader = "ctrl-x"
open_transcript = "leader t"
```

Details:

- The default leader is Ctrl+X, subject to existing explicit bindings.
- Unlike ordinary two-stroke chords, leader menus remain pending until completion, cancellation, or a context change.
- Press Escape or repeat the leader to cancel.
- Keyboard-shortcut settings display the resolved shortcut.
- Prefixes that would intercept ordinary typing or conflict with reserved actions are rejected.

Code references:

- `TuiGlobalKeymap::leader` in `codex-rs/config/src/tui_keymap.rs`
- `resolve` in `codex-rs/tui/src/keymap/leader.rs`
- `RuntimeChordKeymap::from_config` and `KeyChordMatcher` in `codex-rs/tui/src/keymap/chords.rs`


### Default activation policy for installed plugins

What: `plugins._default.enabled` controls whether installed plugins are active unless an individual plugin overrides that default.

Usage:
```toml
[plugins._default]
enabled = false

[plugins."my-plugin@my-marketplace"]
enabled = true
```

Details:

- Per-plugin settings use exact `<plugin>@<marketplace>` IDs.
- Omitting `_default` preserves existing source and account enablement.
- An explicit plugin setting overrides the configured default, but cannot activate an installation disabled at its source.
- Plugin list and read responses report effective enablement.
- A remote installation can still install a policy-disabled package, but skips MCP and Apps authentication setup.
- Capability settings such as remembered tool approvals no longer require implicitly opting a plugin into activation.

Code references:

- `PluginsDefaultConfig`, `PluginsConfigToml`, and `PluginsConfigToml::allows_plugin` in `codex-rs/config/src/types.rs`
- `PluginsManager::configured_plugin_states` in `codex-rs/core-plugins/src/manager.rs`
- Plugin response handling in `codex-rs/app-server/src/request_processors/plugins.rs`
- `PluginContributor` in `codex-rs/ext/mcp/src/plugin.rs`


### Restart the managed background server from the TUI

What: The daemon menu can restart a verified, locally managed background server.

Usage:
```text
/daemon
```

Choose **Restart background server**, then confirm.

Details:

- Codex checks that it manages the server before offering the action.
- The action is disabled while disconnected or while another restart is pending.
- The confirmation explains that active or queued work in other chats may be interrupted.
- The TUI uses its normal reconnection flow after the restart.
- This adds a TUI action around the existing daemon restart operation.

Code references:

- `App::verify_managed_daemon` and `App::confirm_daemon_restart` in `codex-rs/tui/src/app/daemon_menu.rs`
- `AppEvent::RunDaemonRestart` handling in `codex-rs/tui/src/app/event_dispatch.rs`


### Select and copy footer text

What: Mouse selection now covers registered read-only footer and status regions in the fullscreen interface.

Usage:

Drag across footer text, then use the normal copy action or automatic copy-on-select.

To clear transcript highlighting after a confirmed automatic copy:
```toml
[tui]
copy_on_select = "always"
copy_on_select_clear_selection = true
```

Details:

- Footer selections copy plain text.
- Stationary clicks still reach existing clickable controls.
- `copy_on_select_clear_selection` defaults to `false`.
- Automatic deselection depends on confirmed clipboard delivery.

Code references:

- `RenderedSelection` in `codex-rs/tui/src/rendered_selection.rs`
- `App::handle_rendered_selection_event` in `codex-rs/tui/src/app/footer_selection.rs`
- Footer registration in `codex-rs/tui/src/bottom_pane/chat_composer.rs`
- `Tui::copy_on_select_clear_selection` in `codex-rs/config/src/types.rs`


### Control date and timezone context independently

What: A new setting can omit the current date and timezone from environment context while retaining the rest of that context.

Usage:
```toml
include_environment_context_time = false
```

Details:

- Defaults to `true`, preserving previous behavior.
- Also supported in configuration profiles.
- `include_environment_context` remains the separate control for the complete environment-context block.

Code references:

- `ConfigToml::include_environment_context_time` in `codex-rs/config/src/config_toml.rs`
- `ConfigProfile` in `codex-rs/config/src/profile_toml.rs`
- Environment rendering in `codex-rs/core/src/context/world_state/environment.rs`


### Additional Windows sandbox policy controls

What: Users can explicitly disallow MXC selection, and administrators can require MXC on Windows hosts.

Usage in `config.toml`:
```toml
[windows]
allow_mxc = false
```

Alternatively, an administrator can require MXC through managed requirements:
```toml
[windows]
require_mxc = true
```

Details:

- The ordinary `allow_mxc = false` setting blocks explicit MXC configuration and automatic selection.
- Managed `require_mxc = true` rejects a final Windows configuration that selected another backend.
- Requiring MXC validates the selected backend; it does not silently switch backends or install missing support.
- MXC itself predates this snapshot.

Code references:

- `WindowsToml::allow_mxc` in `codex-rs/config/src/types.rs`
- `WindowsRequirementsToml::require_mxc` in `codex-rs/config/src/config_requirements.rs`
- `Config::validate_windows_mxc_requirement` and `config_allows_mxc` in `codex-rs/core/src/config/windows_sandbox_config.rs`


### Terminal lifecycle status integration

What: Codex reports idle, working, and blocked states through terminal status protocols.

Usage:
```bash
codex
```

Details:

- Terminal output receives OSC 7501 lifecycle updates identifying the application as `codex`.
- Direct iTerm2 sessions additionally receive OSC 21337 status, indicators, and sanitized activity details.
- iTerm2-specific updates are suppressed inside multiplexers.
- Status is cleared when Codex releases the terminal and refreshed after terminal ownership changes.
- Visible presentation depends on terminal support.

Code references:

- `ProgramStatus`, `set_terminal_program_status`, and `clear_terminal_program_status` in `codex-rs/tui/src/terminal_program_status.rs`
- Status publication in `codex-rs/tui/src/chatwidget.rs`


### Executor capability inventory endpoint becomes callable

What: Exec-server now serves the previously defined `capabilities/discoverV2` inventory contract.

Usage on an initialized executor connection:
```json
{
  "method": "capabilities/discoverV2",
  "params": {
    "cwd": "file:///workspace/project"
  }
}
```

Details:

- Returns installed-plugin metadata, standalone-skill metadata, and discovery warnings.
- Discovery supplies inventory before caller-side activation and policy decisions.
- Clients should check the executor’s `capabilityDiscoveryV2` advertisement.
- The protocol types existed in 0.162.1; this snapshot wires the request into the server router and adds the remote-environment convenience API.
- This is an exec-server endpoint, separate from the app-server protocol.

Code references:

- `DiscoverV2CapabilitiesRequest` and `DiscoverV2CapabilitiesResponse` in `codex-rs/exec-server-protocol/src/capabilities.rs`
- `build_router` in `codex-rs/exec-server/src/server/registry.rs`
- `ExecServerHandler::discover_capabilities_v2` in `codex-rs/exec-server/src/server/handler.rs`
- `Environment::discover_capabilities_v2` in `codex-rs/exec-server/src/environment/discovery_v2.rs`

## Improvements


### Daybreak is enabled by default and supports eligible API-key sessions

The existing `cli_daybreak` and `api_key_cyber_access_programs` flags now default to enabled. Eligible sessions can use `/daybreak` with either ChatGPT sign-in or an OpenAI API key.

```text
/daybreak
```

Actual availability still depends on the OpenAI provider, account entitlement, model catalog, and connected server. Compatibility handling avoids advertising API-key programs through older servers that cannot forward them. Missing discovery metadata preserves automatic server treatment.

Code references:

- `Feature::CliDaybreak` and `Feature::ApiKeyCyberAccessPrograms` in `codex-rs/features/src/lib.rs`
- `program_for_turn` in `codex-rs/exec/src/daybreak.rs` and `codex-rs/tui/src/daybreak.rs`
- `AppServerSession::constrain_api_key_models` in `codex-rs/tui/src/app_server_session/daybreak_api_key_compat.rs`


### Code Mode interruption is enabled by default

The existing `code_mode_interrupt` feature is now stable and enabled by default. Interrupting a turn terminates its active Code Mode cells without requiring a separate feature opt-in.

Code references: `Feature::CodeModeInterrupt` in `codex-rs/features/src/lib.rs`; turn-abort handling in `codex-rs/core/src/tasks/mod.rs`.


### Exclude selected threads from paginated lists

`thread/list` accepts an optional `excludedThreadIds` array. This helps clients display separately loaded threads while listing the remainder.

```json
{
  "method": "thread/list",
  "params": {
    "limit": 25,
    "excludedThreadIds": ["<thread-id>"]
  }
}
```

Exclusions apply before the result limit, and pages refill when possible. Supply the same exclusions on subsequent pages. Invalid IDs or more than 100 entries return `-32602`; duplicates count toward that limit.

Code references:

- `ThreadListParams::excluded_thread_ids` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- `ThreadRequestProcessor::thread_list_response_inner` in `codex-rs/app-server/src/request_processors/thread_processor.rs`
- Schema: `codex-rs/app-server-protocol/schema/json/v2/ThreadListParams.json`


### Unsubscribed threads remain loaded longer

The default `thread_unload_delay_secs` increases from 60 seconds to 1,800 seconds. Idle threads can remain warm for 30 minutes after losing subscribers.

```toml
thread_unload_delay_secs = 1800
```

Zero still requests immediate unloading. Changing this setting requires a server restart.

Code references: `ConfigToml::thread_unload_delay_secs` in `codex-rs/config/src/config_toml.rs`; unloading logic in `codex-rs/app-server/src/request_processors/thread_lifecycle.rs`.


### Bedrock GPT-6.1 Sol gains the Ultrafast tier

The existing Bedrock GPT-6.1 Sol catalog entries now advertise `ultrafast`, extending the treatment already provided for GPT-6 Astra.

For an appropriately configured Bedrock provider:
```toml
model = "global.openai.gpt-6.1-sol"
service_tier = "ultrafast"
```

The catalog change covers Mantle and the supported global/US Runtime model IDs. It does not introduce the model or provider.

Code references: `normalize_bundled_bedrock_catalog` in `codex-rs/model-provider/src/amazon_bedrock/catalog.rs`.


### Custom metrics exporters operate independently of analytics consent

`analytics.enabled = false` now disables the built-in OpenAI metrics exporter without disabling explicitly configured OTLP metrics collectors.

To disable both:
```toml
[analytics]
enabled = false

[otel]
metrics_exporter = "none"
```

Code references: metrics-exporter selection in `codex-rs/core/src/otel_init.rs`; `AnalyticsConfigToml` and `OtelConfigToml` in `codex-rs/config/src/types.rs`.


### Remote-control preferences survive daemon restarts

Non-ephemeral remote-control enable and disable requests now also persist `remoteControlEnabled` in daemon settings.

Persistence preserves other settings and avoids waiting on a concurrent daemon lifecycle operation.

Code references: `RemoteControlRequestProcessor::enable`, `disable`, and `persist_daemon_preference` in `codex-rs/app-server/src/request_processors/remote_control_processor.rs`.


### Clearer shutdown errors for clients

Requests rejected during graceful shutdown now include a machine-readable reason:

```json
{
  "code": -32600,
  "message": "Server is draining; retry after reconnecting",
  "data": {
    "reason": "serverShuttingDown"
  }
}
```

The agents overview uses this distinction to explain why new sessions are temporarily unavailable and whether automatic reconnection applies.

Code references: `server_draining_error` in `codex-rs/app-server/src/error_code.rs`; session-start error handling in `codex-rs/tui/src/app/agents_overview_new.rs`.


### More informative user-verification cancellations

MCP user-verification responses can carry a bounded diagnostic reason under `_meta["openai/userVerificationReason"]`, distinguishing conditions such as cancellation, missing credentials, unavailable biometrics, interruption, and invalid proofs.

```json
{
  "action": "cancel",
  "content": null,
  "_meta": {
    "openai/userVerificationReason": "credentialMissing"
  }
}
```

These reasons explain outcomes; they are not verification proofs or authorization decisions.

Code references: `UserVerificationReason` in `codex-rs/rmcp-client/src/user_verification.rs`; `from_client_result` in `codex-rs/app-server/src/user_verification_response.rs`.


### Optional executor connection diagnostics

`environment/add` accepts `websocketRequestId`, which supplies `X-Request-ID` during the direct WebSocket upgrade and reconnects. It requires secure transport or a loopback destination.

```json
{
  "method": "environment/add",
  "params": {
    "environmentId": "remote-a",
    "execServerUrl": "wss://executor.example",
    "websocketRequestId": "support-session-123"
  }
}
```

The method retains its existing experimental status.

Code references: `EnvironmentAddParams::websocket_request_id` in `codex-rs/app-server-protocol/src/protocol/v2/environment.rs`; connection configuration in `codex-rs/app-server/src/request_processors/environment_processor.rs`.

## Bug Fixes

- **Remote command output:** Remote execution now waits for output closure when collecting foreground results, preventing buffered output from being lost merely because process exit arrived first. Explicit termination still stops collection. (`OutputDrainPolicy` in `codex-rs/core/src/unified_exec/process.rs`; output retention in `codex-rs/core/src/unified_exec/process_manager.rs`.)

- **Approval replies across session switches:** Pending approvals and questions retain their originating connection, preventing replies from following the currently selected session. Reply handles share single-use completion state. (`AppServerReplyHandle` in `codex-rs/app-server-client/src/server_request.rs`; `PendingAppServerRequests` in `codex-rs/tui/src/app/app_server_requests.rs`.)

- **Abandoned MCP prompts:** Unanswered elicitation requests can be withdrawn when their source disappears, avoiding stale prompts. (`ElicitationAbandonedEvent` in `codex-rs/protocol/src/approvals.rs`; elicitation lifecycle handling in `codex-rs/codex-mcp/src/elicitation.rs`.)

- **Code Mode exit semantics:** `exit()` now terminates JavaScript execution rather than throwing a catchable sentinel. Getters, serialization callbacks, and exception handlers cannot continue emitting results or launching tools after exit. (`exit_callback` in `codex-rs/code-mode-runtime/src/runtime/callbacks.rs`; `completion_state` in `codex-rs/code-mode-runtime/src/runtime/module_loader.rs`.)

- **Code Mode runtime replacement:** Queued execution and wait requests detect runtime replacement rather than silently crossing into a fresh session. The error explains that stored values and running cells were lost and external operations may already have completed. (`ReconnectInner::binding_for_request` in `codex-rs/code-mode/src/grpc_session/reconnect.rs`.)

- **Code Mode serialization:** Reserved Serde JSON object keys are rejected before conversion can reinterpret them or bypass normal recursion limits. (`v8_value_to_json` in `codex-rs/code-mode-runtime/src/runtime/value.rs`.)

- **Dynamic-tool cancellation:** Cancellation now stops pending dynamic-tool waits and allows the handler to publish its terminal outcome. Readiness and admission remain cancellable. (`request_dynamic_tool` in `codex-rs/core/src/tools/handlers/dynamic.rs`; `ToolCallRuntime` in `codex-rs/core/src/tools/parallel.rs`.)

- **Incomplete response accounting:** Terminal incomplete responses preserve reported token usage and are classified as non-retryable instead of generic retryable stream failures. Already-received usage is still accounted for if cancellation races the response. (`ResponseIncompleteError` in `codex-rs/protocol/src/error.rs`; `process_responses_event` in `codex-rs/codex-api/src/sse/responses.rs`; sampling handling in `codex-rs/core/src/session/turn.rs`.)

- **Thread-list failures:** State-database-only listing reports database failures instead of implying empty history. Repeated pagination cursors now produce an error instead of appearing to indicate exhaustion. (`ThreadRequestProcessor` in `codex-rs/app-server/src/request_processors/thread_processor.rs`; listing in `codex-rs/thread-store/src/local/mod.rs`.)

- **Resumed permissions:** Thread resume can restore an unnamed persisted permission profile while respecting explicit overrides and current managed requirements. (`ResumeConfigState` in `codex-rs/app-server/src/request_processors/thread_processor.rs`; `ConfigOverrides::persisted_permission_profile` in `codex-rs/core/src/config/mod.rs`.)

- **Subagent lifecycle:** V2 child eviction distinguishes busy, evicted, and replaced runtimes, avoiding teardown of a replacement or a child still in use. Child creation also carries the issuing turn’s disabled-plugin selection. (`ThreadEvictionOutcome` in `codex-rs/core/src/agent/control/residency.rs`; `spawn` in `codex-rs/core/src/thread_spawn.rs`.)

- **Goal continuation:** Interrupted automatic turns no longer reset empty-response tracking unconditionally, allowing the existing safeguard to stop repeated empty continuations. (`GoalAccountingState` in `codex-rs/ext/goal/src/accounting.rs`; abort handling in `codex-rs/ext/goal/src/extension.rs`.)

- **Guardian authorization races:** Final authorization validation occurs before publishing a reusable reviewer checkpoint, and retries retain the issuing project instructions. Inherited manual approvals are excluded from a child’s trusted approval evidence. (`ReviewAuthorization::invalidation` in `codex-rs/core/src/guardian/review_request.rs`; `PreparedReview` in `codex-rs/core/src/guardian/review_session_setup.rs`; `is_inherited_manual_approval` in `codex-rs/guardian-context/src/transcript.rs`.)

- **Network policy enforcement:** Unapproved hosts are rejected before DNS resolution. Network approvals cannot bypass explicit deny rules or private-address restrictions. Duplicate `Host` headers are rejected, and MITM hook policy is checked before brokered credentials are injected through provider aliases. (`host_blocked_with_lookup` in `codex-rs/network-proxy/src/runtime.rs`; `evaluate_host_policy` in `codex-rs/network-proxy/src/network_policy.rs`; `http_plain_proxy` in `codex-rs/network-proxy/src/http_proxy.rs`.)

- **Updater network policy:** Daemon updates propagate configuration errors and apply managed application-network restrictions instead of falling back to default networking. (`updater_http_client_factory` in `codex-rs/cli/src/main.rs`.)

- **WSL clipboard hangs:** Copying tries the Windows clipboard before WSLg initialization. Windows clipboard reads use a dedicated reader so stalled process startup does not block the shared copy worker. (`copy_to_clipboard` in `codex-rs/tui/src/clipboard_copy.rs`; `reader` in `codex-rs/tui/src/clipboard_paste/text.rs`; `codex-rs/tui/src/clipboard_copy/wsl.rs`.)

- **Clipboard paste targeting:** Supported keyboard paste can fall back from image to text, including active history and Vim searches. Pending paste is checked against its original target before delivery. (`App::handle_clipboard_key_action` in `codex-rs/tui/src/app/clipboard.rs`; `ClipboardPasteTarget` in `codex-rs/tui/src/bottom_pane/chat_composer/mouse.rs`.)

- **Clipboard forwarding in Herdr:** Copy operations also forward clipboard data to the attached terminal when `HERDR_ENV=1`. (`CopyEnvironment` in `codex-rs/tui/src/clipboard_copy.rs`.)

- **Windows sandbox setup:** ACL updates avoid unnecessarily requesting `MAXIMUM_ALLOWED` on active executables and DLLs, reducing sharing violations. Setup diagnostics retain native ACL failure causes. (`codex-rs/windows-sandbox-rs/src/acl.rs`; `record_acl_failure` in `codex-rs/windows-sandbox-rs/src/setup_acl_error.rs`.)

- **Windows MCP launches:** Stdio-server environments retain `SYSTEMDRIVE` and `LOCALAPPDATA`, while explicit configured values take precedence. (`ExecutorStdioServerLauncher` in `codex-rs/rmcp-client/src/stdio_server_launcher.rs`.)

- **Plugin and MCP recovery:** Previously discovered Apps tools remain available through transient startup failures, and skill dependency installation merges new servers into current session state. (`McpConnectionSet` in `codex-rs/codex-mcp/src/connection_manager/tool_catalog.rs`; `Session::refresh_mcp_servers_now` in `codex-rs/core/src/session/mcp.rs`.)

- **Marketplace paths and command pipelines:** Local marketplace lookup handles normalized Windows paths and retains the resolved source when an alias is retargeted. Piping `codex plugin list` into an early-exiting consumer no longer treats a broken pipe as failure. (`MarketplaceInstallMetadata::matches_config` in `codex-rs/core-plugins/src/marketplace_add/metadata.rs`; `write_plugin_list` in `codex-rs/cli/src/plugin_cmd.rs`.)

- **Imported instructions:** Migration preserves recognized URLs and email addresses while continuing to rewrite source-specific instruction filenames, including filename references with line suffixes. (`RewriteProfile::rewrite` in `codex-rs/external-agent-migration/src/rewrite.rs`.)

- **Terminal rendering and session switching:** Wrapped hyperlinks clamp cursor sentinels to visible text, limited-color terminals receive suitable status-line colors, and stale pet loads cannot replace a newer widget’s pet. (`remap_source_wrapped_line` in `codex-rs/tui/src/terminal_hyperlinks.rs`; `status_line_from_segments_with_resolver` in `codex-rs/tui/src/bottom_pane/status_line_style.rs`; `ChatWidget::finish_configured_pet_load` in `codex-rs/tui/src/chatwidget/pets.rs`.)

- **GovCloud guidance:** Guidance is checked against the connected server’s selected provider during startup, including already-configured sessions, and acknowledgment is persisted. (`check_gov_cloud` in `codex-rs/tui/src/onboarding/bedrock.rs`; startup handling in `codex-rs/tui/src/lib.rs`.)

## In Development


### Durable thread read receipts [Experimental]

What: Clients can inspect and update read/unread state for eligible durable local user threads.

Status: Updating receipts and receiving notifications requires `initialize.capabilities.experimentalApi`.

Usage:
```json
{
  "method": "thread/readState/update",
  "params": {
    "threadId": "<thread-id>",
    "expectedRevision": "<revision-from-thread-read>",
    "operation": {"type": "read"}
  }
}
```

Details:

- `thread/read` exposes `readState`; `thread/list` exposes a page-scoped `readStates` map.
- A receipt contains `firstUnread` and an opaque `revision`.
- Use `{"type":"unread"}` to explicitly mark the thread unread.
- Both operations require the revision actually seen. Conflicts return `-32600` with `reason: "readStateConflict"` and the current state.
- New durable, visible terminal results advance the receipt. Merely loading history does not acknowledge it.
- Notifications use `thread/readState/changed` and existing thread subscriptions.
- Ephemeral, unpersisted, subagent, and product-owned threads are ineligible. This adds protocol support, not a general CLI unread command.

Code references:

- `ThreadReadState`, `ThreadReadStateUpdateParams`, and related types in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- Method registration in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `codex-rs/app-server/src/request_processors/thread_read_state.rs`
- Schema: `codex-rs/app-server-protocol/schema/json/v2/ThreadReadStateChangedNotification.json`


### Retrieve specific persisted thread items [Experimental]

What: `thread/items/read` retrieves selected items from one persisted turn.

Status: Experimental app-server method.

Usage:
```json
{
  "method": "thread/items/read",
  "params": {
    "threadId": "<thread-id>",
    "turnId": "<turn-id>",
    "itemIds": ["<item-id>"]
  }
}
```

Details:

- Accepts 1–100 item IDs.
- Returns `data` in canonical stored order, with turn association and available timestamps.
- Uses the configured thread store; unsupported stores return a method-not-found error.

Code references: `ThreadItemsReadParams` and `ThreadItemsReadResponse` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`; `thread_items_read_response_inner` in `codex-rs/app-server/src/request_processors/thread_processor.rs`.


### Prediction-oriented ephemeral forks [Experimental]

What: `thread/fork` can inherit a loaded parent’s effective state to maximize prompt-cache reuse.

Status: Experimental `experimentalPredictionMode` parameter.

Usage:
```json
{
  "method": "thread/fork",
  "params": {
    "threadId": "<loaded-parent-thread-id>",
    "ephemeral": true,
    "experimentalPredictionMode": true
  }
}
```

Details:

- Requires a loaded, persisted parent and an ephemeral child.
- Inherits effective configuration, tools, environments, history, and thread settings.
- Cannot be combined with configuration overrides, a path, or turn cutoffs.
- Enables reasoning-effort override on the fork and disables automatic compaction for that inherited context.

Code references: `ThreadForkParams::experimental_prediction_mode` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`; fork handling in `codex-rs/app-server/src/request_processors/thread_processor.rs`; `AutoCompactionDisabled` in `codex-rs/core/src/compact.rs`.


### Background compaction [Experimental]

What: Codex can prepare remote compaction while foreground work continues.

Status: `features.async_compaction` is off by default.

Usage:
```toml
[features.async_compaction]
enabled = true
model_async_compact_threshold_percent = 65
```

Details:

- Defaults to starting at 65% of the model’s full context window.
- Valid thresholds are 1–100; a threshold alone does not enable the feature.
- Requires remote compaction V2 and is disabled when token-budget mode is active.
- Prepared results are checked against current history, model, and authentication state before adoption.
- Completed speculative work still contributes usage even if its result is discarded.

Code references: `AsyncCompactionConfigToml` in `codex-rs/features/src/feature_configs.rs`; `AsyncCompactionState` and `enabled` in `codex-rs/core/src/session/async_compaction.rs`; installation handling in `codex-rs/core/src/compact_remote_v2_installation.rs`.


### Separate credential-masking opt-in [Experimental]

What: A dedicated feature enables credential brokerage through an already-enabled network proxy.

Status: `features.credential_masking` is off by default.

Usage:
```toml
[features]
network_proxy = true
credential_masking = true
```

Details:

- Credential brokerage existed previously; the separate feature switch is new.
- Masking does not activate a disabled proxy.
- Codex warns when masking is inactive because sandboxing or the proxy is disabled, or provider environment overrides conflict.
- In those cases, commands may receive unmasked credentials.

Code references: `Feature::CredentialMasking` in `codex-rs/features/src/lib.rs`; `build_network_proxy_spec` and `Config::credential_masking_warning` in `codex-rs/core/src/config/mod.rs`.


### Retain client-supplied tool outputs across compaction [Experimental]

What: Clients can request retention of named standalone function outputs in model history.

Status: Cross-window retention requires `features.retain_client_tool_outputs`, off by default.

Usage:
```toml
[features]
retain_client_tool_outputs = true
```

Then submit:
```json
{
  "method": "turn/start",
  "params": {
    "threadId": "<thread-id>",
    "input": [],
    "toolOutput": {
      "name": "host_context",
      "namespace": null,
      "output": "Context to preserve",
      "retain": true
    }
  }
}
```

Details:

- `TurnToolOutput.retain` defaults to `false`.
- Core callers can supply the equivalent `AnnotatedResponseItem` annotation.
- Eligible outputs share the normal history budget and are retained whole or dropped.
- The field requests retention; it is not an unlimited-storage guarantee.

Code references: `TurnToolOutput` in `codex-rs/app-server-protocol/src/protocol/v2/turn.rs`; `AnnotatedResponseItem` in `codex-rs/protocol/src/turn_input.rs`; `is_retained_tool_output` in `codex-rs/core/src/compact_retained_tool_outputs.rs`.


### Encrypted sampled-output replay [Experimental]

What: OpenAI requests can ask for encrypted output metadata intended for token-preserving replay.

Status: `features.output_token_replay` is off by default.

Usage:
```toml
[features]
output_token_replay = true
```

Details:

- Requests add `output.encrypted_content` for the OpenAI provider.
- Response items preserve additional encrypted content and status fields; output text preserves annotations and log probabilities.
- Non-OpenAI forwarding strips unsupported encrypted output metadata.
- Backend support is required; the flag does not itself establish availability.

Code references: `ModelClient` request construction in `codex-rs/core/src/client.rs`; `ResponseItem` and `ContentItem::OutputText` in `codex-rs/protocol/src/models.rs`.


### Additional multi-agent inheritance controls [Experimental]

What: Optional settings preserve full-fork prefixes, use model-default child context limits, or hide native delegation tools.

Status: New controls are opt-in; `preserve_fork_prefix` and `disable_native_tools` default to `false`.

Usage:
```toml
[features]
subagent_default_context_limits = true

[features.multi_agent_v2]
enabled = true
preserve_fork_prefix = true
disable_native_tools = false
```

Details:

- `preserve_fork_prefix` retains the parent’s model-visible history and appends child instructions. Legacy compaction without a reusable baseline still rebuilds context.
- `subagent_default_context_limits` clears inherited context-window and auto-compaction overrides so child models use their own defaults.
- Hosts providing their own delegation tools can set `disable_native_tools = true` while retaining the V2 runtime.

Code references: `MultiAgentV2ConfigToml` in `codex-rs/features/src/feature_configs.rs`; fork preparation in `codex-rs/core/src/agent/control/spawn.rs`; `build_agent_shared_config` in `codex-rs/core/src/agent/child_config.rs`; `collab_tools_enabled` in `codex-rs/core/src/tools/spec_plan.rs`.


### Message-board descriptions and access metadata [Experimental]

What: Agent message boards gain channel descriptions, permission metadata, and explicitly scoped local connections.

Status: Automatic boards retain the existing off-by-default `agent_message_board` gate and V2 requirements. Embedding hosts can supply explicit connections.

Usage:
```toml
[features]
multi_agent_v2 = true
agent_message_board = true
```

Example `create_channel` arguments:
```json
{
  "channel_name": "findings",
  "description": "Verified findings for the current task",
  "subscribe": true
}
```

Details:

- Descriptions are limited to 512 UTF-8 bytes.
- Channel discovery can report board permissions, and channel summaries can report channel permissions.
- Permission denials carry structured action/resource information.
- Embedders can grant read-only or read-write `LocalBoardConnection` handles, including to isolated ephemeral runtimes. Connections must be supplied again for a cold resume or fork.

Code references: `ChannelDescription` in `codex-rs/ext/agent-message-board/src/api.rs`; `ChannelPage` in `codex-rs/ext/agent-message-board/src/types.rs`; `LocalBoard` and `LocalBoardConnection` in `codex-rs/ext/agent-message-board/src/local/connection.rs`.


### Preferred MCP sandbox capability and verified launcher [Experimental]

What: MCP servers can receive sandbox state under `codex/sandbox-state`, plus a verified local Codex launcher when available.

Status: Opt-in experimental MCP capability.

Usage: Advertise:
```json
{
  "experimental": {
    "codex/sandbox-state": {}
  }
}
```

Details:

- Tool-call `_meta` includes identical opaque policy values under `codex/sandbox-state` and the deprecated `codex/sandbox-state-meta` alias.
- Optional `codex/sandbox-launcher` metadata contains an absolute `codexExecutable` path.
- Servers forward the complete opaque state to `codex sandbox --sandbox-state-json`.
- Launcher metadata is limited to verified local stdio arrangements. Its absence does not authorize PATH discovery or unsandboxed fallback.
- Sandbox metadata itself existed previously; the preferred name and launcher envelope are additions.

Code references: capability constants, `SandboxState`, and `augment_metadata` in `codex-rs/codex-mcp/src/sandbox_metadata.rs`; `McpBinding::sandbox_codex_executable` in `codex-rs/codex-mcp/src/binding.rs`.


### Alternative Code Mode transport and description ordering [Experimental]

What: Code Mode gains an optional process-owned gRPC-over-stdio transport and independently configurable tool-description ordering.

Status: Both new flags are off by default.

Usage:
```toml
[features]
code_mode_host_grpc = true
code_mode_tool_description_first = true
```

Details:

- The gRPC option uses pipes for the local host connection and shares existing session-recovery behavior.
- It requires an available Code Mode host.
- `code_mode_tool_description_first` places tool descriptions before namespace descriptions in Code Mode presentations.
- Neither flag is required for the default Code Mode interruption behavior.

Code references: `ProcessOwnedGrpcCodeModeSessionProvider` in `codex-rs/core/src/code_mode_host.rs`; `process_code_mode_session_provider` in `codex-rs/core/src/thread_manager.rs`; `prepare_code_mode_tool_definitions` in `codex-rs/core/src/tools/code_mode/tool_definitions.rs`.


### Expanded realtime V3 voice catalog [Experimental]

What: Realtime voice discovery now returns a separate V3 catalog with additional accepted voice names.

Status: The existing `thread/realtime/listVoices` protocol method remains experimental.

Usage:
```json
{
  "method": "thread/realtime/listVoices",
  "params": {}
}
```

Details:

- `RealtimeVoicesList` gains `v3`.
- Added names include `aube`, `bubbie`, `haetsal`, `hanul`, `himari`, `leher`, `miko`, `neer`, `porto`, `rindo`, `rio`, `rivage`, `selva`, `sonna`, `tinta`, and `viola`.
- Validation uses the selected realtime version’s catalog. V1 and V2 do not automatically accept V3-only voices.

Code references: `RealtimeVoice` and `RealtimeVoicesList::builtin` in `codex-rs/protocol/src/protocol.rs`; `validate_realtime_voice` in `codex-rs/core/src/realtime_conversation.rs`.


### Guardian trust for orchestrator-provided connectors [Experimental]

What: Guardian V2 can recognize host-attested connector identities supplied by the plugin-service orchestrator.

Status: `features.guardian_trust_orchestrator_connectors` is off by default and requires the applicable Guardian V2 flow.

Usage:
```toml
[features]
guardian_trust_orchestrator_connectors = true
```

Details:

- Applies to connector-sourced tools with a nonempty connector identity.
- Introduces `TrustedToolSource::PluginServiceOrchestrator`.
- This extends the reviewer’s trusted-source context; arbitrary tool arguments do not establish that provenance.

Code references: `trusted_tool_context` in `codex-rs/ext/guardian-v2/src/async_scorer/trusted_tools.rs`; `TrustedToolSource` in `codex-rs/guardian-context/src/trusted_tool.rs`.


### Keyboard transcript-selection infrastructure [In Development]

What: Transcript code gains a keyboard-owned cursor and mark state.

Status: `begin_select_mode` has no production caller in this snapshot; there is no verified user-facing activation shortcut.

Details:

- Implemented handlers cover arrow and Vim-style movement, marking, copying, and exit.
- The entry point is explicitly marked as awaiting a later integration layer.
- These bindings should not yet be presented as available CLI functionality.

Code references: `SelectMode` and `TranscriptView::begin_select_mode` in `codex-rs/tui/src/transcript_view/select_mode.rs`; movement support in `codex-rs/tui/src/transcript_view/select_mode/motion.rs`.

## Notes

- **Remove retired patched-zsh flags.** `features.shell_zsh_fork` and `features.unified_exec_zsh_fork` are deprecated and ignored. Commands use the standard shell executor; managed requirements for the removed flags are also ignored with a warning. References: `legacy_usage_notice` in `codex-rs/features/src/lib.rs`; `codex-rs/core/src/config/managed_features.rs`.

- **Review network-domain patterns.** Domain matching now rejects brace alternatives, character classes, backslash escapes, slash-containing patterns, and unsupported repeated wildcards. Replace constructs such as `{api,cdn}.example.com` with separate hosts. Exact names, scoped `*`/`?` patterns, and the documented `*.`/`**.` prefixes remain supported. References: `DomainPatternSet::new` in `codex-rs/network-proxy/src/domain_matcher.rs`.

- **Review custom metrics export settings.** If you previously relied on `analytics.enabled = false` to suppress a custom OTLP metrics exporter, explicitly set `otel.metrics_exporter = "none"`.

- **Handle additive protocol fields and errors.** Clients should tolerate unavailable read receipts and the new realtime voice catalog, preserve opaque sandbox-state fields, and distinguish thread-list failures from successful exhaustion. Read-state revisions are equality tokens; conflicting edits require a fresh user action, not a blind retry.


Generated with:
- tool: `harness-investigations@a570285-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.163.0.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
