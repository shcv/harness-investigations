# Changelog for version 0.157.0

## Release Status

> **Not yet released:** `rust-v0.157.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.156.1, this snapshot enables automatic background-server startup and the fullscreen transcript by default, adds explicit gateway OAuth control for app-server clients, and connects managed application-network policy to live requests. It also improves voice continuity, remote imports, MCP resource targeting, terminal rendering, and session recovery.

The source tag `rust-v0.157.0` exists, but no published GitHub Release was found when the sync ran. This is an intermediate development snapshot; the changes below do not imply that release binaries or assets were published.

## New Features


### Explicit gateway OAuth sign-in for app-server clients

What: Clients can control secondary gateway authorization through new read, login, and cancel methods instead of relying on automatic browser authorization.

Usage:

Include this capability in the existing initialization request:

```json
{
  "method": "initialize",
  "params": {
    "clientInfo": {
      "name": "example-client",
      "version": "1.0"
    },
    "capabilities": {
      "explicitGatewayOauth": true
    }
  }
}
```

After completing initialization, probe support and credential readiness:

```json
{"id": 1, "method": "account/gatewayOAuth/read"}
```

Start or cancel authorization:

```json
{"id": 2, "method": "account/gatewayOAuth/login"}
{"id": 3, "method": "account/gatewayOAuth/cancel"}
```

Details:

- `read` returns `providerId`, `providerName`, `required`, `status`, and `error`, without refreshing credentials or opening a browser.
- `required` means the provider uses gateway OAuth, even when already authenticated. Status is `null` for other providers.
- `account/gatewayOAuth/changed` reports `notReady`, `started`, `succeeded`, or `failed`. Only the initiating connection receives the authorization URL.
- The client opens that URL in a browser that can reach the server’s callback port. The login request returns `{}` after credentials are saved.
- Cancellation affects the calling connection’s login; disconnecting also cancels it.
- Providers requiring primary authentication still require that sign-in first.
- Existing clients, including the TUI, retain automatic authorization unless explicit login has been enabled for the shared runtime.

Code references:

- Method registrations in `codex-rs/app-server-protocol/src/protocol/common.rs`.
- `InitializeCapabilities::explicit_gateway_oauth` in `codex-rs/app-server-protocol/src/protocol/v1.rs`.
- `GatewayOAuthReadResponse`, `GatewayOAuthStatus`, and `GatewayOAuthChangedNotification` in `codex-rs/app-server-protocol/src/protocol/v2/account.rs`.
- Implementation in `codex-rs/app-server/src/request_processors/account_processor/gateway_oauth.rs`.
- New schemas under `codex-rs/app-server-protocol/schema/json/v2/GatewayOAuth*.json`.


### Additional Guardian review policy

What: An additional policy field lets users and administrators supplement Guardian’s resolved policy without replacing it.

Usage:

```toml
[auto_review]
extra_policy = """
Require explicit authorization before publishing project artifacts.
"""
```

Administrators can supply the managed equivalent in `requirements.toml`:

```toml
guardian_extra_policy = """
Require explicit authorization before publishing project artifacts.
"""
```

Details:

- A nonempty managed `guardian_extra_policy` takes precedence over the user setting.
- The synchronous reviewer inserts this text into the template’s `{{ extra_policy }}` placeholder.
- Guardian v2’s classifier also incorporates the extra policy when that classifier is enabled.
- Custom review templates must include `{{ extra_policy }}` to render it through that template.
- These settings customize existing review behavior; they do not independently enable automatic review.

Code references:

- `AutoReviewToml::extra_policy` in `codex-rs/config/src/config_toml.rs`.
- `ConfigRequirementsToml::guardian_extra_policy` in `codex-rs/config/src/config_requirements.rs`.
- `GuardianPolicyInstructions` in `codex-rs/prompts/src/guardian_instructions.rs`.
- `build_guardian_review_session_config` in `codex-rs/core/src/guardian/reviewer_config.rs`.


### Cloud-skill configuration and authority

What: Cloud-hosted skills now use a dedicated configuration section and the `cloud` authority in skill-tool requests.

Usage:

```toml
[cloud.skills]
enabled = false
```

Where the host supplies a cloud-skill provider, discovery uses:

```json
{"authority": {"kind": "cloud"}}
```

as the arguments to `skills.list`.

Details:

- Cloud skills are permitted by default, but availability requires a host-supplied provider and an eligible session.
- `orchestrator.skills.enabled` remains accepted for compatibility but no longer controls discovery.
- Cloud discovery refreshes at turn start. Successful catalogs are reused until their source changes; failed or partial discovery can be retried on a subsequent turn.
- A transient failure may retain the previous catalog only within the same authorization scope. Disabling cloud skills or changing that scope invalidates it.
- This replaces the earlier orchestrator-skill integration; it is not the first introduction of remotely supplied skills.

Code references:

- `CloudToml` and `OrchestratorToml::skills` in `codex-rs/config/src/config_toml.rs`.
- `SkillToolAuthoritySelector` and `SkillToolAuthority` in `codex-rs/ext/skills/src/tools/mod.rs`.
- `SkillsThreadState::refresh_cloud_catalog` in `codex-rs/ext/skills/src/state.rs`.
- `SkillProviders::with_cloud_provider` in `codex-rs/ext/skills/src/sources.rs`.


### Unicode list and task-checkbox rendering

What: Markdown lists now render with Unicode bullets and task checkboxes, with a separate setting to retain plain markers.

Usage:

```toml
[tui.rendering]
lists = false
```

Details:

- The default is `true`: unordered lists use `•`, and task lists use `☐` and `☑`.
- Disabling the setting retains plain list markers and textual task-checkbox syntax.
- Rendering handles nested, empty, and multiline task-list items.

Code references:

- `TuiRendering::lists` in `codex-rs/config/src/tui_rendering.rs`.
- Markdown event handling in `codex-rs/tui/src/markdown_render.rs`.
- `task_list_marker` in `codex-rs/tui/src/markdown_render/task_lists.rs`.


### Externally supplied proxy MITM certificates

What: Trusted network-proxy configuration can provide an existing certificate authority and private key for HTTPS interception.

Usage:

In the proxy’s standalone JSON configuration:

```json
{
  "network": {
    "enabled": true,
    "mitm": true,
    "mitm_ca": {
      "certificate_file": "/run/proxy/ca.pem",
      "private_key_file": "/run/proxy/key.pem"
    }
  }
}
```

Details:

- This belongs to trusted proxy configuration, not ordinary sandbox settings in `config.toml`.
- Both paths must be absolute. The files must be regular files, and the certificate must match the private key.
- The certificate file must not contain a private key.
- Private-key permissions are checked on Unix. Platforms where those permissions cannot be verified reject the configuration.
- Remote exec-server proxy configuration does not support external CAs.
- Derived trust bundles contain certificates only and are stored separately from the supplied CA files.

Code references:

- `NetworkMitmCaConfig` in `codex-rs/network-proxy/src/config.rs`.
- External CA validation and trust-bundle handling in `codex-rs/network-proxy/src/certs.rs`.
- Configuration checks in `codex-rs/network-proxy/src/state.rs` and `codex-rs/network-proxy/src/remote_config.rs`.

## Improvements


### Background-server startup is enabled by default

Eligible interactive launches now automatically start or connect to the shared local background server. This promotes the existing `daemon_auto_start` feature from experimental and disabled to stable and enabled.

Usage:

```bash
codex
```

To run without the daemon for one launch:

```bash
codex --no-daemon
```

To disable automatic startup persistently:

```toml
[features]
daemon_auto_start = false
```

When required feature settings conflict with a running daemon, the TUI offers a concrete recovery choice: run without it, restart a managed daemon with the displayed settings, or cancel. The restart flow explains that shared settings persist and restarting may interrupt work. Fresh starts also preserve previously saved feature overrides.

Code references: `Feature::DaemonAutoStart` in `codex-rs/features/src/lib.rs`; recovery UI in `codex-rs/tui/src/daemon_recovery.rs`; `start_with_features` and `restart_with_features` in `codex-rs/app-server-daemon/src/launch.rs`.


### Fullscreen transcript becomes the default

The existing fullscreen transcript is now enabled by default wherever alternate-screen mode is available.

Usage:

```toml
[tui]
fullscreen_transcript = false
```

Use that setting to retain the previous opt-out behavior. Alternate-screen restrictions still take precedence.

Mouse selection also gains Shift-click extension from an existing selection. Horizontal dragging at a viewport edge no longer starts vertical autoscrolling, and highlighting better represents copied line breaks.

Code references: `Tui::fullscreen_transcript` in `codex-rs/config/src/types.rs`; default resolution in `codex-rs/core/src/config/mod.rs`; selection handling in `codex-rs/tui/src/transcript_view/input.rs`, `selection.rs`, and `text.rs`.


### Managed application-network policy now governs live traffic

The previously existing `[application.network]` requirements are now enforced across app-server HTTP and WebSocket traffic, including redirects and reused clients. Embedded TUI and exec startup also connect their application clients to the shared policy.

Usage:

For example, an administrator can restrict application destinations in managed `requirements.toml`:

```toml
[application.network]
enabled = true

[application.network.domains]
"api.openai.com" = "allow"
```

Details:

- An enabled policy denies unlisted destinations. Allowed hosts permit HTTPS and WSS; domain entries are exact names, not wildcard patterns.
- An empty enabled policy permits no external destinations. Deployments must include the hosts needed by their authentication, provider, and other application services.
- Changes take effect on explicit configuration/account reload or restart.
- Policy changes cancel requests to newly denied destinations. Account changes invalidate operations retaining the previous account’s authorization.
- Failed policy loading blocks traffic until requirements load successfully.
- Authentication and requirements discovery use narrowly restricted bootstrap clients.
- Unsupported SDK or command-based transports can be unavailable under restrictions.
- Agent shell, Git, SSH, and other subprocess networking retain their separate execution and sandbox policies.

Code references: `destination_policy` and `ConfigManager::refresh_application_network_policy` in `codex-rs/app-server/src/application_network.rs`; `EmbeddedNetworkPolicy` in `codex-rs/app-server/src/in_process_bootstrap.rs`; request enforcement in `codex-rs/http-client/src/route_aware_client_pool/execution.rs` and `codex-rs/websocket-client/src/lib.rs`.


### Voice conversations survive navigation

An active voice conversation can remain attached to its owning thread while the user navigates to another conversation or the agents overview.

Usage:

Start voice normally with `/voice`, navigate between conversations, and use `/voice mute` or `/voice stop` to control the active call.

Details:

- Global voice controls target the existing call’s owner.
- The agents overview shows a voice badge for the owning session.
- Supported function-key voice bindings work across more UI surfaces while respecting existing bindings.
- Returning to the owner restores its live voice state. Archiving or deleting the owning session stops the call.

Code references: `App::voice_owner_thread_id`, `control_voice`, and `detach_current_thread_for_navigation` in `codex-rs/tui/src/app/voice_owner.rs`; `with_voice_toggle` in `codex-rs/tui/src/keymap/chords.rs`.


### Import works through daemon and remote connections

`/import` no longer requires the embedded local app-server. It can detect and import compatible setup through the connected daemon or remote server.

Usage:

```text
/import
```

Detection uses the connected server’s filesystem and the appropriate working-directory context. Completion tracking uses the returned import ID, so another client’s import completion does not finish this client’s flow.

Code references: `handle_external_agent_config_migration_prompt` in `codex-rs/tui/src/external_agent_config_migration/flow.rs`; `AppServerSession::external_agent_config_import` and `consume_external_agent_config_import_completion` in `codex-rs/tui/src/app_server_session/external_agent_config.rs`.


### Fork directly from a locked conversation

When another client holds the conversation’s writer lock, press `f` to fork it and continue in the fork.

The TUI displays progress, prevents repeated shortcuts from starting duplicate forks, and preserves the local draft when switching to the fork.

Code references: locked-thread input handling in `codex-rs/tui/src/app/input.rs`; `AppEvent::ForkCurrentSession` handling in `codex-rs/tui/src/app/event_dispatch.rs`.


### GPT-6 Sol and Luna in the Bedrock catalog

The existing Amazon Bedrock integration adds the model identifiers `openai.gpt-6-sol` and `openai.gpt-6-luna`. GPT-6 Sol becomes the first-priority model in its static catalog, replacing GPT-5.6 Sol in that position.

Usage, with Bedrock authentication already configured:

```bash
codex -c model_provider='"amazon-bedrock"' -m openai.gpt-6-sol
```

Existing model entries remain available. These are source-catalog changes; actual use still depends on the configured Bedrock endpoint and account access.

Code references: `AMAZON_BEDROCK_GPT_6_SOL_MODEL_ID` and `AMAZON_BEDROCK_GPT_6_LUNA_MODEL_ID` in `codex-rs/model-provider-info/src/lib.rs`; `static_model_catalog` in `codex-rs/model-provider/src/amazon_bedrock/catalog.rs`; `codex-rs/model-provider/src/amazon_bedrock/runtime_catalog.rs`.


### Direct app-account targeting for MCP resource reads

The existing `mcpServer/resource/read` method accepts an explicit hosted-app target, avoiding tool discovery when the client already knows the app and account.

Usage:

```json
{
  "method": "mcpServer/resource/read",
  "params": {
    "server": "codex_apps",
    "uri": "ui://example/resource",
    "target": {
      "connectorId": "connector-id",
      "linkId": "account-link-id"
    }
  }
}
```

Details:

- `linkId` must be supplied inside `target`. A real string selects an account; explicit `null` requests no-auth access subject to backend policy.
- Empty and synthetic link identifiers are rejected.
- Explicit targets require `server: "codex_apps"` and backend support.
- `originCallId` with `threadId` retains precedence and preserves the originating call’s app/account scope.
- Omitting `target` preserves existing discovery behavior.

MCP status responses also gain `httpOrigin`: the configured HTTP endpoint’s origin without credentials, path, query, or fragment. Non-HTTP transports report `null`.

Code references: `McpResourceReadTarget` and `McpServerStatus::http_origin` in `codex-rs/app-server-protocol/src/protocol/v2/mcp.rs`; `McpRequestProcessor` in `codex-rs/app-server/src/request_processors/mcp_processor.rs`; updated schemas `McpResourceReadParams.json` and `ListMcpServerStatusResponse.json` under `codex-rs/app-server-protocol/schema/json/v2/`.


### Hosted plugin extension metadata

Plugin summaries can now include an `extensions` object describing hosted entrypoints, settings tools, file handlers, quick actions, and search-mention providers.

Usage:

```json
{"method": "plugin/installed", "params": {}}
```

Clients can inspect each returned plugin summary’s `extensions` field. Remote installed-plugin discovery requests this metadata from the backend. These declarations enable client integrations; their presence does not mean the terminal UI implements every declared surface.

Code references: `PluginSummary::extensions` in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`; `PluginExtensions` and related types in `codex-rs/app-server-protocol/src/protocol/v2/plugin_extensions.rs`; remote discovery in `codex-rs/core-plugins/src/remote.rs`; updated `PluginInstalledResponse.json`, `PluginListResponse.json`, `PluginReadResponse.json`, and `PluginShareListResponse.json` schemas.


### Lifecycle timestamps in thread-item history

`thread/items/list` now exposes item start and completion times, allowing clients to display recorded timing without inferring it from storage order.

Usage:

```json
{
  "method": "thread/items/list",
  "params": {
    "threadId": "thread-id",
    "limit": 50
  }
}
```

Each entry includes nullable `startedAtMs` and `completedAtMs` values in Unix milliseconds. Missing producer timestamps remain `null`.

Code references: `ThreadItemEntry` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`; `ThreadRequestProcessor` in `codex-rs/app-server/src/request_processors/thread_processor.rs`; `codex-rs/app-server-protocol/schema/json/v2/ThreadItemsListResponse.json`.


### More efficient resume after compaction

Compaction records now preserve additional resume state, including the multi-agent runtime version, last-started turn identity, and previous turn settings.

For compatible paginated rollouts, reconstruction can start at the latest usable compaction and read its newer history instead of searching farther backward for companion state. Older or incomplete compactions retain full-replay fallback.

Usage:

```bash
codex resume
```

Code references: `CompactionResumeMetadata` in `codex-rs/history/src/compaction_resume_metadata.rs`; reconstruction in `codex-rs/core/src/session/rollout_reconstruction.rs`; bounded scanning in `codex-rs/rollout/src/model_context.rs` and `codex-rs/thread-store/src/local/model_context.rs`.


### Guardian uses thread-owned context by default

The existing `guardianv2.thread_context` feature is now stable and enabled by default. This setting is independent of whether the experimental Guardian v2 classifier is enabled.

Guardian can also submit usable parent compaction checkpoints across differing advertised compaction hashes, leaving payload validation to the backend. Invalid checkpoints and review failures still fail closed.

Code references: `Feature::GuardianThreadContext` in `codex-rs/features/src/lib.rs`; `GuardianV2ConfigToml::thread_context` in `codex-rs/features/src/feature_configs.rs`; `ReviewContextPolicy::parent_compaction` in `codex-rs/core/src/guardian/review_session_context.rs`.


### Richer mathematical rendering

The existing terminal math renderer adds aligned equations, boxed expressions, stacked summation limits, `\underset`, `\overset`, `\substack`, calligraphic capitals, and `\widehat`.

These improvements apply when math rendering is enabled. To retain source notation:

```toml
[tui.rendering]
math = false
```

Code references: mathematical command parsing in `codex-rs/tui/src/markdown_render/math/render.rs`; structured layouts in `codex-rs/tui/src/markdown_render/math/render/structured.rs`.


### Consistent clock formatting

Usage-reset times, credit expiry, analytics displays, and expanded resume details now use the detected 12-hour or 24-hour clock format more consistently.

Code references: `ClockFormat::date_time_format` in `codex-rs/tui/src/clock_format.rs`; consumers in `codex-rs/tui/src/status/rate_limits.rs`, `chatwidget/reset_credits.rs`, `resume_picker.rs`, and `analytics/`.


### Model-specific Code Mode instructions

Model catalogs can customize Code Mode’s `exec` and `wait` descriptions, the `wait` parameter schema, deferred-tool guidance, and shared MCP TypeScript definitions.

Example model-message fragment:

```json
{
  "tools": {
    "code_mode": {
      "exec": {
        "description": "Run JavaScript. Default yield: {{ default_exec_yield_time_ms }} ms.\n{{ image_helper }}"
      }
    }
  }
}
```

Runtime tool declarations are still appended, and `exec` retains its harness-owned JavaScript grammar. Invalid custom `wait` schemas fall back to bundled parameters.

Code references: `CodeModeToolMessages` in `codex-rs/protocol/src/openai_models.rs`; `build_exec_tool_description` in `codex-rs/code-mode-protocol/src/description.rs`; `codex-rs/core/src/tools/code_mode/wait_spec.rs`.

## Bug Fixes

- File uploads retry eligible transport failures and HTTP 503 responses, reopening the content stream for each attempt. Blob transfer now has a shared five-minute deadline and at most five attempts, with supported retry-delay headers respected. (`upload_openai_file` in `codex-rs/codex-api/src/files.rs`.)

- Terminal errors recover unsent answers from the live question editor into the composer, preserving existing draft elements. Background draft updates during history search no longer replace the active search query or preview. (`take_question_drafts` and `append_question_drafts` in `codex-rs/tui/src/bottom_pane/questions.rs`; `history_search_draft.rs` under `codex-rs/tui/src/bottom_pane/chat_composer/`.)

- Wrapped URLs in user messages retain their complete hyperlink destinations across terminal widths. (`wrap_user_message` in `codex-rs/tui/src/history_cell/messages.rs`.)

- Terminal.app sessions detected over SSH use native scrollback when alternate-screen selection is automatic. Explicit alternate-screen choices remain available. (`determine_alt_screen_mode` in `codex-rs/tui/src/lib.rs`; detection in `codex-rs/tui/src/terminal_probe/terminal_identity.rs`.)

- Codex respects an explicit tmux `mouse off` setting instead of enabling mouse capture for fullscreen views and overlays. (`MouseCapture` and `read_options` in `codex-rs/tui/src/tui/tmux.rs`.)

- The agents overview identifies its list as stale while disconnected or after reconnection fails. (`codex-rs/tui/src/app/agents_overview.rs`.)

- Oversized task-tool responses preserve essential identifiers, status, cursors, and available answer text while marking truncation, instead of discarding useful structure prematurely. (`codex-rs/tui/src/dynamic_tools_response.rs`.)

- `codex doctor` identifies which databases failed integrity checks and improves path redaction in shareable output, including Windows path forms. (`codex-rs/cli/src/doctor.rs` and `codex-rs/cli/src/doctor/output.rs`.)

- MCP OAuth rejects authorization endpoints using non-HTTP(S) schemes before registration or returning a login URL. (`codex-rs/rmcp-client/src/oauth/issuer_binding.rs`.)

- Exec-server clients bound incoming requests and ordinary notifications to 8 KiB, with separate allowances for streaming notifications. Stdio stderr reading is also bounded and tolerates invalid UTF-8. (`client_inbound_message_exceeded_limit` in `codex-rs/exec-server/src/client_inbound_request_limit.rs`; `codex-rs/exec-server/src/client_transport.rs`.)

- Linux sandbox startup supports maskable ancestor bind-mount aliases while keeping privileged daemon sockets hidden. Direct socket/directory aliases and unsupported nested mounts remain rejected. (`daemon_socket_mask_paths` in `codex-rs/linux-sandbox/src/daemon_mounts.rs`; `append_daemon_socket_masks` in `codex-rs/linux-sandbox/src/bwrap.rs`.)

- Windows restricted-token defaults limit child-process and IPC access to the runner’s logon session. Shared capability identifiers no longer grant cross-launch access, and failure paths close the new token handle. (`set_default_dacl` and `create_token_with_caps_from` in `codex-rs/windows-sandbox-rs/src/token.rs`.)

- Windows filesystem sandbox environments retain `SystemDrive` and `LOCALAPPDATA` alongside `PATH`, using case-insensitive matching. (`codex-rs/exec-server/src/fs_sandbox.rs`.)

- Tool hooks use the captured local environment’s working directory when available, retaining a host-local fallback for remote workspaces. (`tool_hook_cwd` in `codex-rs/core/src/hook_runtime.rs`.)

- Interrupted child-agent creation cleans up the pending child and closes its stored spawn relationship. (`PendingSpawn` in `codex-rs/core/src/agent/control/spawn_guard.rs`.)

- Internal Guardian threads use concise review titles and previews instead of synthetic approval prompts; existing explicit names are preserved. (`is_guardian_review_source` in `codex-rs/state/src/extract.rs`; `codex-rs/state/migrations/0057_cleanup_guardian_thread_metadata.sql`.)

- Failed image-generation items retain the backend image request ID when available, improving correlation of client-visible failures. (`ImageRequestError` in `codex-rs/codex-api/src/endpoint/images.rs`; `ImageGenerationTool` in `codex-rs/ext/image-generation/src/tool.rs`.)

## In Development


### Automatic preference for the Windows MXC sandbox [Experimental]

What: A new opt-in preference selects the existing native MXC sandbox for eligible local Windows execution.

Status: Runtime-gated by `features.prefer_mxc`, which defaults to `false`.

Usage:

```toml
[features]
prefer_mxc = true
```

Details:

- Selection requires native availability and compatible local-binding policy.
- If automatic selection is ineligible, existing configured sandbox behavior applies.
- Remote executors retain their configured backend.
- Explicit `windows.sandbox = "mxc"` remains strict.
- Command failures do not trigger fallback to another backend.
- Changes apply on a subsequent launch.

Code references: `Feature::PreferMxc` in `codex-rs/features/src/lib.rs`; `network_config_allows_mxc` and `effective_local_windows_sandbox_type` in `codex-rs/core/src/config/windows_sandbox_config.rs`; selection contract in `codex-rs/mxc-sandbox/README.md`.


### Quiet reasoning status for realtime delegations [Experimental]

What: Realtime V3 clients can opt into receiving public reasoning summaries as quiet context during automatic Codex delegations.

Status: The existing experimental realtime-start API gains `backendReasoningStatus`, disabled by default.

Usage:

Add this field to an otherwise valid `thread/realtime/start` request:

```json
{
  "backendReasoningStatus": true
}
```

Details:

- Requires the experimental API capability and a compatible realtime V3 session.
- Applies to automatic handoffs, not client-managed handoffs.
- Status text is bounded and sent on the commentary channel.
- Realtime V1 and V2 ignore this path.

Code references: `ThreadRealtimeStartParams::backend_reasoning_status` in `codex-rs/app-server-protocol/src/protocol/v2/realtime.rs`; `RealtimeConversationManager::send_reasoning_status` in `codex-rs/core/src/realtime_conversation.rs`.


### Agent message-board subscription improvements [Experimental]

What: The existing experimental message board gains more predictable subscriptions and bounded notification previews.

Status: Still runtime-gated by the default-off `agent_message_board` feature.

Usage, in an existing compatible multi-agent setup:

```toml
[features]
agent_message_board = true
```

Details:

- Creating a channel while posting subscribes its author to new root discussions there.
- Posting preserves an explicit discussion unsubscribe until the agent subscribes again.
- Authors do not receive notifications for their own posts, even when explicitly targeted.
- Notifications include a bounded preview and identify when `read_post` is needed for the remainder.
- Notifications still do not start idle agents.

Code references: subscription behavior in `codex-rs/ext/agent-message-board/src/local.rs`; tool descriptions in `codex-rs/ext/agent-message-board/src/tools/spec.rs`; notification rendering in `codex-rs/core/src/context/agent_message_board_notification.rs`.

## Notes

- Replace `orchestrator.skills.enabled` with `cloud.skills.enabled`. Skill-tool integrations must also replace the `orchestrator` authority with `cloud`; the old configuration key is accepted but ineffective.
- Clients adopting explicit gateway OAuth should probe `account/gatewayOAuth/read` on every connection before authenticated startup requests. Older servers may ignore the initialization capability, so initialization alone does not establish support.
- Update strict client models for `PluginSummary.extensions`, `McpServerStatus.httpOrigin`, and the nullable lifecycle timestamps in `ThreadItemEntry`.
- Existing application-network requirements can now block traffic that previously proceeded. Review required destinations before upgrading a managed deployment.
- The bundled model catalog enables reasoning-effort updates for `gpt-6-astra`, disables its experimental-context capability, and removes the advertised `ultrafast` tier from `gpt-5.6-sol`. These are bundled-catalog changes, not guarantees about live service availability. Evidence: the corresponding entries in `codex-rs/models-manager/models.json`.
- Code references describe the `rust-v0.157.0` source snapshot relative to `rust-v0.156.1`.


Generated with:
- tool: `harness-investigations@baa381f-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.157.0.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
