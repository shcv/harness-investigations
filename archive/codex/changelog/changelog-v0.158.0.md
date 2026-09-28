# Changelog for version 0.158.0

## Release Status

> **Not yet released:** `rust-v0.158.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with `rust-v0.157.1`, this snapshot adds authenticated executor WebSocket connections, MCP OAuth client secrets, configurable MCP startup readiness, and terminal clipboard settings. It also enables terminal-input approval checks by default, makes paginated history the default for new local threads, and removes plugin extension metadata from the app-server protocol.

Release status: `rust-v0.158.0` exists as a source tag, but no published GitHub Release was found when the sync ran. This changelog describes an intermediate/development snapshot; it does not establish that release binaries or assets were published.

## New Features


### Authentication for executor WebSocket listeners

What: `codex exec-server` can now require authentication when clients connect to its direct WebSocket listener.

Usage:

```bash
codex exec-server \
  --listen ws://127.0.0.1:8765 \
  --ws-auth capability-token \
  --ws-token-file /absolute/path/executor-token
```

Details:

- Supports capability tokens supplied through a token file or `--ws-token-sha256`, plus signed bearer-token authentication.
- Clients send `Authorization: Bearer TOKEN` during the WebSocket handshake.
- Authentication is checked when the connection opens. Established connections are not continuously revalidated, and credentials are loaded at startup.
- These flags do not apply to stdio, remote registration, or forwarding.
- Authentication remains opt-in. Remote deployments need a protected transport or TLS proxy.

The authentication modes previously available to app-server are now available to executor listeners; the modes themselves are not newly introduced.

Code references:

- `ExecServerCommand` in `codex-rs/cli/src/exec_server_command.rs`
- `WebsocketAuthArgs` and `authorize_upgrade` in `codex-rs/websocket-auth/src/lib.rs`
- `websocket_upgrade_handler` in `codex-rs/exec-server/src/server/transport.rs`


### Bearer tokens for configured remote executors

What: URL-based entries in `environments.toml` can now include credentials for an authenticated executor.

Usage:

```toml
[[environments]]
id = "remote"
url = "wss://executor.example"
auth_bearer_token = "TOKEN"
```

Details:

- `auth_bearer_token` is the raw token; Codex adds the `Bearer` prefix.
- Tokens require `wss://` or a loopback destination.
- Credentials are reused on reconnect and redacted in diagnostics.
- There is no automatic token refresh.
- The setting requires a URL entry and cannot be used with a `program` transport.

Code references:

- `EnvironmentToml` and `parse_environment_toml` in `codex-rs/exec-server/src/environment_toml.rs`
- `RemoteEnvironmentOptions::into_transport_params` in `codex-rs/exec-server/src/environment/connect_options.rs`


### Linux executor PID-namespace control

What: Executor operators can choose whether sandboxed operations create an isolated PID namespace or inherit the executor’s namespace.

Usage:

```bash
codex exec-server --linux-sandbox-pid-namespace=inherit
```

Details:

- `isolate` remains the default.
- `inherit` uses the existing PID namespace and `/proc` view.
- The choice applies to sandboxed process execution and filesystem helpers.
- This is a trusted startup option, not a repository-controlled setting.
- Inheritance permits signaling other same-UID processes, including the executor. It is intended for dedicated environments.
- Filesystem, network, and seccomp restrictions remain separate controls.

Code references:

- `ExecServerCommand` in `codex-rs/cli/src/exec_server_command.rs`
- `LinuxSandboxPidNamespace` in `codex-rs/sandboxing/src/linux_pid_namespace.rs`
- PID-namespace handling in `codex-rs/sandboxing/src/bwrap.rs`
- `codex-rs/linux-sandbox/README.md`


### OAuth client secrets for MCP servers

What: MCP OAuth configuration now supports confidential clients that require both a client ID and a client secret.

Usage:

```bash
codex mcp add example \
  --url https://mcp.example.com/mcp \
  --oauth-client-id CLIENT_ID \
  --oauth-client-secret CLIENT_SECRET
```

Equivalent configuration:

```toml
[mcp_servers.example]
url = "https://mcp.example.com/mcp"

[mcp_servers.example.oauth]
client_id = "CLIENT_ID"
client_secret = "CLIENT_SECRET"
```

Details:

- `--oauth-client-secret` requires a URL-based server and an OAuth client ID.
- The secret is used during authorization-code exchange and token refresh.
- It remains in server configuration rather than being copied into stored token credentials.
- If existing credentials belong to a different client ID, Codex requires a fresh login.

Pre-registered OAuth client IDs already existed; client-secret support is the addition.

Code references:

- `AddMcpStreamableHttpArgs` in `codex-rs/cli/src/mcp_cmd.rs`
- `McpServerOAuthConfig::client_secret` in `codex-rs/config/src/mcp_types.rs`
- `OAuthClientCredentials` in `codex-rs/rmcp-client/src/oauth_client_credentials.rs`
- OAuth authorization setup in `codex-rs/rmcp-client/src/perform_oauth_login.rs`


### MCP startup readiness from a cached catalog

What: Individual MCP servers can now allow startup to proceed using an eligible cached tool catalog while their live connection initializes.

Usage:

```toml
[mcp_servers.example]
url = "https://mcp.example.com/mcp"
startup_readiness = "catalog"
```

Details:

- The default, `"connection"`, retains the existing connection-based readiness behavior.
- `"catalog"` can reduce startup waiting when a usable cached catalog is available.
- This also affects required-server startup handling in non-interactive execution.
- Tool execution still requires a live connection. Cached discovery does not guarantee that the server will be available when a tool is called.
- Paths that explicitly require a live binding may still wait for it.

Code references:

- `McpStartupReadiness` and `McpServerConfig` in `codex-rs/config/src/mcp_types.rs`
- `McpConnectionSet` in `codex-rs/codex-mcp/src/connection_manager/tool_catalog.rs`
- Required-server readiness in `codex-rs/codex-mcp/src/connection_manager/required.rs`


### Per-server MCP tool-schema budgets

What: MCP server configuration can now control the input-schema size threshold used when preparing tools for the model.

Usage:

```toml
[mcp_servers.example]
url = "https://mcp.example.com/mcp"
tool_input_schema_max_bytes = 12000
```

Details:

- The value is a positive, nonzero UTF-8 byte limit.
- Ordinary MCP tools retain the existing default threshold of 5,000 bytes.
- Increasing the limit can preserve parameter descriptions that would otherwise be removed during schema compaction.
- This changes model-facing schema preparation, not the MCP server’s argument-validation rules.

Code references:

- `McpServerConfig::tool_input_schema_max_bytes` in `codex-rs/config/src/mcp_types.rs`
- `parse_mcp_tool_with_schema_max_bytes` in `codex-rs/tools/src/mcp_tool.rs`
- `mcp_tool_to_responses_api_tool` in `codex-rs/tools/src/responses_api.rs`
- Schema compaction in `codex-rs/tools/src/json_schema.rs`


### Configurable selection copying and right-click paste

What: The terminal UI adds explicit controls for copying transcript selections and pasting with the right mouse button.

Usage:

```toml
[tui]
copy_on_select = "always"
right_click_paste = "auto"
```

Details:

- `copy_on_select` accepts `"auto"`, `"always"`, or `"never"`.
- `"auto"` chooses behavior according to terminal capabilities and known terminal-specific exceptions.
- `right_click_paste` accepts `"auto"`, `"on"`, or `"off"`.
- Automatic right-click paste targets supported Windows, Linux, and WSL environments; `"on"` also permits supported macOS environments.
- Right-click paste applies to an editable fullscreen composer when there is no selection to copy.
- SSH sessions and recognized VS Code terminal cases are excluded from the application-managed paste path.
- A delayed clipboard read is discarded if the draft, thread, or input state changes before it completes.

Code references:

- `CopyOnSelect`, `RightClickPaste`, and `Tui` in `codex-rs/config/src/types.rs`
- `LocalSettings::copy_on_select` in `codex-rs/tui/src/local_settings.rs`
- `PasteEnvironment` and `App::start_right_click_paste` in `codex-rs/tui/src/app/right_click_paste.rs`


### Opt-in logging of agent responses and Guardian assessments

What: OpenTelemetry log export can now include completed agent answers and synchronous Guardian review assessments.

Usage, alongside an existing OTLP log-exporter configuration:

```toml
[otel]
log_agent_responses = true
log_guardian_assessments = true
```

Details:

- Both settings default to `false`.
- `codex.agent_response` records completed final answers from the main agent and spawned agents. Commentary, replayed history, and internal maintenance conversations are excluded.
- Answer text is capped at 65,536 UTF-8 bytes, with memory-citation markup removed.
- `codex.guardian_assessment` records synchronous review outcomes and failure metadata, including timeouts or cancellations. Cached Guardian V2 approvals are excluded.
- These records go through the log exporter; enabling them does not add the content to ordinary local feedback logs.
- Exported records may contain answer text or review rationale.

Code references:

- `OtelConfig` in `codex-rs/config/src/types.rs`
- `AgentResponseLogger` in `codex-rs/otel/src/agent_response.rs`
- Guardian assessment logging in `codex-rs/otel/src/guardian_assessment.rs`
- `codex-rs/otel/README.md`

## Improvements


### Terminal-input approval checks are enabled by default

The existing `write_stdin` approval feature moves from disabled development functionality to a stable, enabled-by-default feature.

Nonempty input sent to a running process is checked against the process’s original permissions and the current execution environment. Ordinary input within the applicable permission baseline does not automatically require another prompt, while escalated permissions or changed restrictions can require approval or a process restart.

Empty polling calls and the supported non-TTY Ctrl-C cancellation path bypass input approval.

Code references:

- `Feature::WriteStdinApproval` in `codex-rs/features/src/lib.rs`
- `ProcessEntry::stdin_approval` and `TerminalPermissions::review_requirement` in `codex-rs/core/src/unified_exec/stdin_approval.rs`


### New local threads default to paginated history

New local threads now use paginated history storage. App-server clients should follow the thread’s `historyMode` and use the existing `thread/turns/list` and `thread/items/list` methods to retrieve history.

This changes the default for newly created local threads; it does not mean all existing thread histories are converted.

Code references:

- `LocalThreadStore::default_history_mode` in `codex-rs/thread-store/src/local/mod.rs`
- Existing history methods in `codex-rs/app-server-protocol/src/protocol/common.rs`


### Explicit transparent image generation and broader edit inputs

The image-generation tool gains a `transparent_background` input:

```json
{
  "prompt": "A small illustrated fox sticker with no background",
  "transparent_background": true
}
```

The flag defaults to `false`, producing an explicitly opaque-background request rather than the previous automatic background selection.

Image editing through `num_last_images_to_include` also accepts recent images represented by file IDs, in addition to inline image data. The existing limit of five recent images remains.

Code references:

- `ImagegenArgs`, `request_for_call_args`, and `recent_images` in `codex-rs/ext/image-generation/src/tool.rs`
- `ImageEditRequest` in `codex-rs/codex-api/src/images.rs`


### Clipboard copying preserves formatting and stays responsive

Transcript selections now preserve more of the underlying Markdown, including links, emphasis, lists, inline code, tables, and significant whitespace. Selections confined to code retain literal code content.

Clipboard work runs asynchronously, keeping the UI responsive while copying. Copy status distinguishes pending work from confirmed or unconfirmed completion, and an older copy operation cannot clear a newer selection.

Code references:

- `selection` in `codex-rs/tui/src/markdown_copy.rs`
- Table copying in `codex-rs/tui/src/markdown_copy/table.rs`
- Clipboard worker in `codex-rs/tui/src/clipboard_copy/worker.rs`
- `copy_selected_text_with` in `codex-rs/tui/src/transcript_view/selection.rs`


### More robust connection prewarming

Startup and resume paths can reuse a ready prewarmed model connection, replace a closed one, and avoid duplicate preparation. Connection setup can overlap tool preparation instead of waiting for it serially.

Preconnection also handles authentication recovery and WebSocket-to-HTTP fallback. Resuming with an unchanged model and matching compaction state avoids an unnecessary model-transition compaction in more session types.

Code references:

- Startup prewarming in `codex-rs/core/src/session/startup_prewarm.rs`
- `ModelClientSession::preconnect_websocket` in `codex-rs/core/src/client.rs`
- `maybe_run_previous_model_inline_compact` in `codex-rs/core/src/session/turn.rs`


### Distinct reporting for unavailable Flex capacity

Flex-capacity failures now have a dedicated `CodexErrorInfo::FlexUnavailable` classification, serialized as `flexUnavailable`.

Users see “Flex capacity unavailable.” rather than a generic failure, and the condition does not enter the ordinary retry path. Both HTTP error responses and streamed errors can produce this classification.

Client authors should accept the additional error variant.

Code references:

- `CodexErrorInfo::FlexUnavailable` in `codex-rs/protocol/src/error.rs`
- `map_api_error` in `codex-rs/codex-api/src/api_bridge.rs`
- `parse_flex_unavailable` in `codex-rs/codex-api/src/sse/responses.rs`
- `codex-rs/app-server-protocol/schema/json/v2/ErrorNotification.json`


### Updated account-plan recognition and model migration

Account parsing recognizes the additional `promax` plan value. Display labels distinguish `Pro`, `Pro (More)`, and `Pro (Max)` where the corresponding account values are returned. This is client recognition of account data, not an announcement of plan availability or pricing.

The bundled catalogs remove GPT-5.4 entries, and startup migration handling can offer the provider-appropriate GPT-6 Sol replacement for saved GPT-5.4 selections. The migration is scoped so that unrelated custom providers are not redirected.

For Bedrock Mantle GovCloud endpoints, the default static catalog is restricted to GPT-5.6 Terra and GPT-5.6 Luna. An explicitly supplied catalog is not replaced by that default restriction.

Code references:

- `PlanType::ProMax` in `codex-rs/protocol/src/account.rs`
- `codex-rs/app-server-protocol/schema/json/v2/GetAccountResponse.json`
- `model_upgrade_for_migration` in `codex-rs/tui/src/app/startup_prompts.rs`
- `codex-rs/models-manager/models.json`
- `static_gov_model_catalog` in `codex-rs/model-provider/src/amazon_bedrock/catalog.rs`


### Expanded model-catalog tool customization

Model-catalog authors can provide namespace- or MCP-server-specific guidance for indirectly presented tools through `ToolMessages.indirect_description_prefixes`. The guidance appears in surfaces such as Code Mode documentation, `ALL_TOOLS`, and loaded tool-search namespaces.

Tool-message overrides also extend to MCP resource helpers and the parameter schema for `request_user_input_async`, which retains the existing `send_user_message_async` catalog key. Message-board channel tools accept description overrides while keeping fixed parameter schemas.

These changes affect tool presentation; they do not change the handlers’ accepted argument semantics.

Code references:

- `ToolMessages`, `IndirectDescriptionPrefixes`, `McpResourceToolMessages`, and `ToolMessage::parameters` in `codex-rs/protocol/src/openai_models.rs`
- `IndirectNamespacePrefixes` in `codex-rs/tools/src/indirect_namespace_prefixes.rs`
- `RequestUserInputAsyncHandler::spec` in `codex-rs/core/src/tools/handlers/request_user_input_async.rs`


### Better reasoning shortcuts and process previews

Reasoning-level shortcuts can now reach `Max` when the selected model advertises it. `Ultra` remains an explicit model-menu choice rather than another shortcut step.

The `/ps` process display preserves multiline command structure using a visible `↵` marker instead of discarding everything after the first line.

Code references:

- `handle_reasoning_shortcut` in `codex-rs/tui/src/chatwidget/reasoning_shortcuts.rs`
- `UnifiedExecProcessesCell` in `codex-rs/tui/src/history_cell/exec.rs`


### Clearer onboarding and contextual tips

During browser-login onboarding, pressing `c` copies the login link. Fullscreen onboarding also permits native terminal selection for login URLs and device codes.

Fresh conversations have varied welcome greetings. Tips can appear during longer-running work and after selected completed turns; the existing setting below disables them:

```toml
[tui]
show_tooltips = false
```

Code references:

- `COPY_LINK` in `codex-rs/tui/src/onboarding/keys.rs`
- `run_onboarding_screen` in `codex-rs/tui/src/onboarding.rs`
- `Greeting::choose` in `codex-rs/tui/src/empty_state_animation/greetings.rs`
- `TurnTips` in `codex-rs/tui/src/app/turn_tips.rs`


### More capable Mermaid rendering

Terminal-rendered flowcharts accept quoted node and edge labels and literal ampersands.

When a diagram cannot be rendered because its syntax is unsupported, its result is too wide, or it exceeds a size limit, the UI explains the fallback before showing the original highlighted source.

Code references:

- `flowchart_label` in `codex-rs/mermaid/src/parse.rs`
- `render` in `codex-rs/tui/src/markdown_render/mermaid.rs`


### More useful feedback when local logging fails

A SQLite log-write failure now produces a user-visible warning once, with guidance to capture feedback before closing or use `codex doctor`. Feedback collection can fall back to retained in-memory logs when SQLite logging is incomplete.

When users choose to include logs in `/feedback`, collection also includes bounded TUI client logs and relevant inherited rollout-history attachments. The additional attachments are reflected in the feedback flow.

Code references:

- `LogWriteWarningReporter` in `codex-rs/app-server/src/log_write_warning.rs`
- `collect_feedback_logs` in `codex-rs/app-server/src/request_processors/feedback_processor.rs`
- `fetch_feedback_upload` in `codex-rs/tui/src/app/feedback_upload.rs`
- `history_base_attachments` in `codex-rs/app-server/src/request_processors/feedback_rollout_history.rs`

## Bug Fixes

- **Guardian retains user intent more reliably.** Goal updates and retained instructions survive context maintenance more consistently, and repeated scheduler heartbeats do not displace newer human instructions. Assistant context remains distinct from user authorization. (`UserGoalUpdate` in `codex-rs/core/src/context/user_goal.rs`; `Session::record_user_goal_update` in `codex-rs/core/src/session/retained_context.rs`; retained instructions in `codex-rs/guardian-context/src/retained_instructions.rs`.)

- **Approval reviews use the tool’s actual execution environment.** Permission derivation accounts for the target environment, including the environment owning an existing process receiving terminal input. (`for_tool` and `for_environment` in `codex-rs/core/src/guardian/permissions.rs`.)

- **Browser connector actions receive the appropriate Guardian scope.** Node-REPL-backed browser connectors are recognized as computer-use actions. (`GuardianScope::for_mcp_connector` in `codex-rs/protocol/src/openai_models/guardian.rs`; `is_node_repl_backed_connector` in `codex-rs/protocol/src/mcp.rs`.)

- **Server-directed retry delays are preserved correctly.** `Retry-After` accepts both seconds and HTTP dates, and passing a retry deadline between layers no longer restarts the full delay. (`RetryAfter` in `codex-rs/http-client/src/retry_after.rs`; retry handling in `codex-rs/codex-client/src/retry.rs`.)

- **File uploads recover from more transient gateway failures.** Upload retries now cover HTTP 502 and 504 in addition to the existing 503 handling. (Upload retry handling in `codex-rs/codex-api/src/files.rs`.)

- **Executor preparation retries use structured error categories.** Disconnections, timeouts, and selected transient handshake failures can retry without treating authentication, TLS, or malformed-protocol failures as transient merely because of their text. (`ExecServerError::is_retryable_preparation_error` in `codex-rs/exec-server/src/client_error.rs`.)

- **Managed authentication and network policy remain attached to more extension requests.** Route-aware clients preserve the applicable account and transport policy for ChatGPT app/plugin traffic and related extension requests. (`create_transport_for_routes_async` and `create_client_with_chatgpt_cookies` in `codex-rs/login/src/auth/default_client.rs`.)

- **Network-policy inheritance preserves explicit local-binding restrictions.** An omitted `allow_local_binding` value remains distinguishable from an explicit `false`, avoiding accidental loss of inherited policy. (`EnvironmentNetworkPolicy` in `codex-rs/network-proxy/src/environment_policy.rs`; `codex-rs/core/src/config/network_proxy_spec.rs`.)

- **Command completion preserves buffered output.** Unified-execution output buffers are captured consistently when a process finishes, reducing missing output during completion races. (`OutputBuffers` in `codex-rs/core/src/unified_exec/process.rs`; `resolve_aggregated_output` in `codex-rs/core/src/unified_exec/async_watcher.rs`.)

- **Failed process launches produce consistent lifecycle events.** Launch failures retain command-start and failure reporting even if the initiating caller is cancelled. (`with_launch_failure_events` in `codex-rs/core/src/tools/runtimes/unified_exec/launch.rs`.)

- **Shell snapshots honor configured environment filtering.** Snapshot replay respects `shell_environment_policy` and does not restore an original environment value over an explicit override. (`CapturedSnapshot::render_script` in `codex-rs/shell-command/src/shell_snapshot_render.rs`; `codex-rs/core/src/shell_snapshot.rs`.)

- **Numeric reasoning-effort values remain numeric on the wire.** Supported numeric strings serialize as JSON numbers rather than strings. (`serialize_reasoning_effort` in `codex-rs/codex-api/src/common.rs`.)

- **Streaming Markdown avoids incomplete-link flicker.** Unfinished link destinations are held until they can be rendered coherently. (`ProsePreview` in `codex-rs/tui/src/streaming/prose_preview.rs`.)

- **Realtime context is captured per model request.** Realtime state is less likely to change underneath an in-flight request, and undelivered speech is not replayed into an unrelated later question. (`RealtimeConversationSnapshot` in `codex-rs/core/src/realtime_conversation.rs`; `take_undelivered_realtime_speech_for_replay` in `codex-rs/tui/src/chatwidget/realtime.rs`.)

- **Configuration aliases respect layer precedence.** Aliases are normalized before layers are merged, so a higher-priority alias can override a lower-priority canonical spelling. Configuration editing also preserves unrelated raw settings more reliably. (`normalize_key_aliases` in `codex-rs/config/src/key_aliases.rs`; `codex-rs/config/src/merge.rs`.)

- **Ephemeral threads reject unsupported revert requests explicitly.** `thread/revert` returns a clear error for ephemeral threads. (`ThreadRequestProcessor` in `codex-rs/app-server/src/request_processors/thread_processor.rs`.)

- **macOS path aliases receive consistent patch-permission checks.** System aliases such as `/tmp` and `/private/tmp` are considered when deciding whether a patch is permitted. (`LocalFileSystemPolicyMatcher` in `codex-rs/protocol/src/permissions/local_aliases.rs`; `PatchPolicyMatcher` in `codex-rs/core/src/safety.rs`.)

- **Overlapping writable roots preserve protected Git metadata.** Sandbox construction better maintains read-only restrictions for Git metadata and `.git` pointer targets when writable roots overlap. (`codex-rs/protocol/src/permissions.rs`; `create_filesystem_args` in `codex-rs/sandboxing/src/bwrap.rs`.)

- **macOS directory moves work with recursive basename exclusions.** Seatbelt policy generation allows legitimate directory moves while retaining restrictions on excluded names and their descendants. (`build_seatbelt_unreadable_glob_policy` in `codex-rs/sandboxing/src/seatbelt.rs`.)

- **Linux socket masking handles Btrfs mount identity differences.** Daemon-socket masking no longer relies on a device-identity assumption that fails on these layouts. (`daemon_socket_mask_paths` in `codex-rs/linux-sandbox/src/daemon_mounts.rs`.)

- **Windows background helpers avoid unwanted console windows.** Piped child processes, including MCP and Code Mode hosts, use appropriate no-window launch behavior. (`Command::new` in `codex-rs/utils/pty/src/child_command.rs`; `codex-rs/rmcp-client/src/stdio_server_launcher.rs`.)

- **Windows startup handles restricted detached launches more gracefully.** Automatic TUI startup can fall back to an embedded server when the launcher prevents detached execution. Explicit daemon lifecycle operations still report the restriction. (`DetachedLaunchRestricted` in `codex-rs/app-server-daemon/src/backend/windows.rs`; `codex-rs/tui/src/startup_orchestration.rs`.)

- **Large Windows sandbox launches avoid command-line limits.** Oversized launch payloads use scoped environment chunks that are removed from the child’s environment after decoding. (`needs_environment` in `codex-rs/windows-sandbox-rs/src/launch_environment.rs`; `codex-rs/windows-sandbox-rs/src/environment_transport.rs`.)

- **Windows 10 directory opening handles drive-letter links correctly.** The compatibility handling preserves checks against filesystem reparse-point traversal. (`open_directory_no_reparse` in `codex-rs/windows-sandbox-rs/src/no_reparse_dir.rs`.)

- **Windows sandbox provisioning repairs rejected stored credentials.** Repair is limited to registrations whose ownership is verified; full-access provisioning also receives corrected handling. (`credentials_need_repair` in `codex-rs/windows-sandbox-service/src/provisioning/registered.rs`; `WindowsSandboxRequestProcessor` in `codex-rs/app-server/src/request_processors/windows_sandbox_processor.rs`.)

## In Development


### Executor tokens through environment registration [Experimental]

What: The existing experimental `environment/add` RPC gains an optional `authBearerToken` parameter.

Usage, after opting into experimental app-server APIs:

```json
{
  "method": "environment/add",
  "params": {
    "environmentId": "remote",
    "execServerUrl": "wss://executor.example",
    "authBearerToken": "TOKEN"
  }
}
```

Status: Runtime-gated by the app-server experimental API capability.

Details:

- The token authenticates executor connections and reconnects.
- It follows the secure-transport requirements described for configured executor tokens.
- This is an additional parameter on an existing experimental method, not a new registration RPC.

Code references:

- `EnvironmentAddParams` in `codex-rs/app-server-protocol/src/protocol/v2/environment.rs`
- `"environment/add"` registration in `codex-rs/app-server-protocol/src/protocol/common.rs`


### Code Mode schema-size control [Experimental]

What: Code Mode gains its own configurable budget for rendered tool input types.

Usage:

```toml
[features.code_mode]
enabled = true
tool_input_schema_max_bytes = 32000
```

Status: Available through Code Mode, which remains disabled by default.

Details:

- The default and minimum effective budget are 16,000 UTF-8 bytes per rendered input type.
- For ordinary MCP tools, the effective budget is also at least the server’s explicitly configured input-schema limit.
- This supplements the new per-server MCP setting.

Code references:

- `CodeModeConfigToml::tool_input_schema_max_bytes` in `codex-rs/features/src/feature_configs.rs`
- Type rendering in `codex-rs/code-mode-protocol/src/description.rs`
- Code Mode tool preparation in `codex-rs/tools/src/code_mode.rs`


### Message-board-only multi-agent coordination [Experimental]

What: Multi-Agent V2 can disable direct-message tools and use an in-memory message board, including in ephemeral sessions.

Usage:

```toml
[features]
agent_message_board = true

[features.multi_agent_v2]
enabled = true
disable_direct_message = true
message_board_in_memory = true
```

Status: Opt-in configuration; the message-board feature remains under development and disabled by default.

Details:

- `disable_direct_message` removes `send_message` and `followup_task` from the model’s tool surface.
- Spawning, agent management, and automatic child results remain available.
- The configuration requires an exposed message-board posting tool; otherwise tool-router construction fails rather than leaving agents without the intended communication route.
- `message_board_in_memory` avoids durable board storage. Its contents do not survive the session.

Code references:

- Multi-agent configuration in `codex-rs/features/src/feature_configs.rs`
- `finalize_tool_router` in `codex-rs/core/src/tools/spec_plan.rs`
- Message-board construction in `codex-rs/core/src/agent_message_board.rs`


### Deferred mailbox interruption [Experimental]

What: An optional flag prevents pending agent mail from interrupting sampling at reasoning or commentary boundaries.

Usage:

```toml
[features]
defer_mailbox_preemption = true
```

Status: Under-development runtime feature, disabled by default.

Details:

- Pending messages remain available for delivery at the next normal processing boundary.
- This changes interruption timing; it does not disable message delivery.

Code references:

- `Feature::DeferMailboxPreemption` in `codex-rs/features/src/lib.rs`
- Mailbox-preemption handling in `codex-rs/core/src/session/turn.rs`


### Remote message-board integration [In Development]

What: A new `RemoteAgentMessageBoard` client provides an integration surface for externally hosted agent message boards.

Status: Library infrastructure; the default CLI does not wire it into normal message-board operation.

Details:

- Requires an external service implementing the expected API; this snapshot does not provide that server.
- Supports remote board operations and SSE notifications.
- Notifications cover current activity rather than replaying all prior events; persisted posts can be recovered through search.
- There is no new end-user CLI switch for selecting a remote board.

Code references:

- `RemoteAgentMessageBoard` in `codex-rs/agent-message-board-client/src/client.rs`
- `codex-rs/agent-message-board-client/README.md`


### Executor capability discovery V2 [In Development]

What: The executor protocol adds types and staged implementation for richer plugin and skill capability discovery.

Status: The `"capabilities/discoverV2"` RPC is not registered in the executor request dispatcher in this tag.

Details:

- Protocol definitions and implementation code exist.
- The local capability metadata includes a discovery-V2 capability bit.
- These additions do not make the method callable yet; clients should not infer working support from the staged metadata alone.
- No user-facing enablement switch is provided.

Code references:

- `"capabilities/discoverV2"` and its protocol types in `codex-rs/exec-server-protocol/src/capabilities.rs`
- Staged implementation in `codex-rs/exec-server/src/discoverV2/mod.rs`


### Early observation yielding for Code Mode hosts [In Development]

What: Code Mode host interfaces can yield an observation before a cell finishes while allowing the cell to continue running.

Status: Host/protocol support is present, but the core CLI call path does not supply the preemption token needed to activate the new behavior.

Details:

- Adds a `yield-observation` host capability and associated messages.
- Provides integration support for hosts that need to observe an ongoing cell early.
- It does not yet mean that ordinary CLI cells automatically yield in response to new user input or mailbox activity.

Code references:

- `yield-observation` capability in `codex-rs/code-mode-protocol/src/host/mod.rs`
- `CodeModeSession` execution interfaces
- Core calls passing `preempt: None` in `codex-rs/core/src/tools/code_mode/mod.rs`

## Notes


### Breaking app-server change: plugin extension metadata removed

`PluginSummary.extensions` is removed, along with the associated extension metadata types and generated schemas. The removed surface described entrypoints, icons, quick actions, settings, and search providers.

Affected response schemas include:

- `codex-rs/app-server-protocol/schema/json/v2/PluginListResponse.json`
- `codex-rs/app-server-protocol/schema/json/v2/PluginInstalledResponse.json`
- `codex-rs/app-server-protocol/schema/json/v2/PluginReadResponse.json`
- `codex-rs/app-server-protocol/schema/json/v2/PluginShareListResponse.json`

Client migration:

- Regenerate protocol bindings.
- Remove assumptions that plugin summaries contain `extensions`.
- Update code depending on removed types such as `PluginExtensions`, `PluginEntrypoint`, `PluginQuickAction`, `PluginSettings`, and `PluginSearchProvider`.
- No replacement for this metadata is introduced by the corresponding change.

Code references: `PluginSummary` and the removed extension types in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`.


### Guardian thread-context configuration is deprecated

`features.guardianv2.thread_context` is now ignored because thread-owned Guardian context is always enabled. Remove the setting from configuration, including profile-specific overrides; setting it to `false` no longer disables that context.

Code references:

- Guardian V2 configuration in `codex-rs/features/src/feature_configs.rs`
- Removed-feature handling in `codex-rs/features/src/lib.rs`


### Configuration and client compatibility

- `tui.whimsy` is accepted as an alias for `tui.effects.starfield`. Prefer the canonical spelling; it wins if both spellings occur in the same configuration layer. (`normalize_key_aliases` in `codex-rs/config/src/key_aliases.rs`.)
- Clients must tolerate the added `flexUnavailable` error and `promax` plan values.
- Clients displaying newly created local threads must support paginated history rather than assuming all turns arrive inline.
- Deployments using `--linux-sandbox-pid-namespace=inherit` need matching sandbox-helper support for the inherited-namespace path. (`LinuxSandboxPidNamespace` in `codex-rs/sandboxing/src/linux_pid_namespace.rs`.)


Generated with:
- tool: `harness-investigations@012a848-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.158.0.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
