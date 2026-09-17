# Changelog for version 0.155.0

## Release Status

> **Not yet released:** `rust-v0.155.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.154.0, this snapshot adds stored thread attachments, explicit daemon updates and update settings, and command-based AWS credential export for Amazon Bedrock. It also expands agent-dashboard controls, improves conversation recovery, and introduces opt-in voice conversations and a second memory pipeline. The `rust-v0.155.0` source tag exists, but no published GitHub Release was found when the sync ran; this changelog describes an intermediate development snapshot and does not imply published binaries or assets.

## New Features


### Stored thread attachments

What: App-server clients can associate durable resource references with stored threads without loading or resuming those threads.

Usage:

```json
{"id":20,"method":"thread/attachment/add","params":{"threadId":"<thread-id>","attachmentType":"pull_request","identityKey":"[\"github.com\",\"openai\",\"codex\",123]","payload":{"url":"https://github.com/openai/codex/pull/123"}}}
```

```json
{"id":21,"method":"thread/attachment/list","params":{"threadId":"<thread-id>","limit":100}}
```

```json
{"id":22,"method":"thread/attachment/remove","params":{"threadId":"<thread-id>","attachmentType":"pull_request","identityKey":"[\"github.com\",\"openai\",\"codex\",123]"}}}
```

Details:

- Attachments are identified by their owning thread, `attachmentType`, and `identityKey`.
- Adding the same identity again returns `outcome: "existing"` and preserves the original payload and creation time. A first addition returns `"created"`.
- Listing returns `data` and `nextCursor`. Continue with that cursor and the same thread ID.
- Each thread supports up to 100 attachments. Payloads are limited to 64 KiB; attachment types and identity keys are each limited to 256 bytes.
- Creation and removal emit `thread/attachment/updated` notifications. Duplicate additions and removal of an absent attachment do not emit updates.
- Attachments are separate from conversation history. Removing one does not delete the referenced resource; deleting its owning thread removes its stored attachments.
- The backing thread store must support attachment persistence.

Code references:

- `ThreadAttachmentAddParams`, `ThreadAttachmentListParams`, and `ThreadAttachmentRemoveParams` in `codex-rs/app-server-protocol/src/protocol/v2/thread_attachment.rs`.
- RPC registrations in `codex-rs/app-server-protocol/src/protocol/common.rs`.
- `ThreadRequestProcessor::thread_attachment_add` in `codex-rs/app-server/src/request_processors/thread_attachments.rs`.
- New schemas under `codex-rs/app-server-protocol/schema/json/v2/`, including `ThreadAttachmentAddParams.json`, `ThreadAttachmentListResponse.json`, and `ThreadAttachmentUpdatedNotification.json`.


### Explicit daemon updates and configurable update policy

What: Managed app-server installations gain an explicit update command, configurable automatic-update intervals, and a configurable shutdown grace period.

Usage:

```bash
codex app-server daemon update
```

Configure `CODEX_HOME/app-server-daemon/settings.json`:

```json
{
  "shutdownGraceSeconds": 120,
  "updater": {
    "autoUpdateEnabled": false,
    "updateIntervalMinutes": 120
  }
}
```

Apply changes to automatic-update enablement with:

```bash
codex app-server daemon restart
```

Details:

- Manual updates require an installer-owned standalone installation on the stable `latest` channel.
- The command returns JSON with an `updated`, `noUpdate`, or `unsupported` status, plus installed and running versions.
- A manual update works when automatic updates are disabled. It restarts a running managed daemon and may interrupt active or queued work.
- Automatic updates default to enabled for eligible installations, with an initial check after five minutes and subsequent checks every 60 minutes.
- `updateIntervalMinutes` must be positive. Interval changes are read at the next updater wait.
- `shutdownGraceSeconds` accepts 0–300 and defaults to 60. Zero requests immediate forced shutdown after initiating graceful shutdown.
- Managed starts and restarts now ensure the updater is running when appropriate. Explicitly pinned releases remain pinned.
- `codex doctor` reports configured update preferences.

Code references:

- `AppServerDaemonSubcommand::Update` in `codex-rs/cli/src/main.rs`.
- `UpdateOutput` and `update` in `codex-rs/app-server-daemon/src/lib.rs`.
- `DaemonSettings` and `UpdaterSettings` in `codex-rs/app-server-daemon/src/settings.rs`.
- `codex-rs/app-server-daemon/src/managed_install.rs` and `codex-rs/app-server-daemon/src/update_loop.rs`.
- `push_configured_updater` in `codex-rs/cli/src/doctor/background.rs`.


### AWS credential-export commands for Amazon Bedrock

What: The existing Bedrock provider can obtain signing credentials from a configured executable.

Usage:

```toml
model_provider = "amazon-bedrock"

[model_providers.amazon-bedrock.aws]
region = "us-west-2"

[model_providers.amazon-bedrock.aws.credential_export]
command = "/absolute/path/to/export-aws-credentials"
args = []
timeout_ms = 30000
```

The executable writes credentials to stdout:

```json
{
  "AccessKeyId": "<access-key>",
  "SecretAccessKey": "<secret-key>",
  "SessionToken": "<session-token>",
  "Expiration": "2026-09-18T12:00:00Z"
}
```

Details:

- Both flat credential JSON and an STS-style object nested under `Credentials` are accepted.
- `SessionToken` and `Expiration` are optional.
- The executable is invoked directly, without a shell. Its name must be an absolute path or a bare executable name.
- The default timeout is 30 seconds, and output is limited to 64 KiB.
- Credentials are cached in memory and refreshed ahead of their supplied expiration. Concurrent refreshes are coordinated.
- `aws.credential_export` cannot be combined with `aws.profile`.
- Bedrock setup and login refuse to replace the credential source while an exporter is configured.

Code references:

- `AwsCredentialExportConfig` and `ModelProviderInfo::validate` in `codex-rs/model-provider-info/src/lib.rs`.
- `AwsCredentialExport` and `CredentialOutput` in `codex-rs/model-provider/src/amazon_bedrock/credential_export.rs`.
- `BedrockAuthSource::CredentialExport` in `codex-rs/model-provider/src/amazon_bedrock/auth.rs`.


### Notices for older connected services

What: The TUI displays an informational notice when its connected app-server is an older stable version.

Usage:

To suppress the notice:

```toml
[tui]
show_server_version_notice = false
```

Details:

- Notices are enabled by default and also appear in the agents overview.
- The comparison targets stable versions; it does not equate every development-version difference with an outdated service.
- Disabling the notice does not disable compatibility errors or version reporting.

Code references:

- `Tui::show_server_version_notice` in `codex-rs/config/src/types.rs`.
- `App::initialize_server_version_notice` in `codex-rs/tui/src/app/server_version_notice.rs`.
- `codex-rs/tui/src/update_versions.rs`.

## Improvements


### More control from the agents overview

Open `/agents` to use additional task-management actions:

| Default shortcut | Action |
|---|---|
| `Ctrl+E` | Confirm archiving the selected task and its child agents |
| `Delete` | Confirm permanently deleting the selected task and its child agents |
| `Ctrl+W` | Hide the selected task locally without stopping it |
| Right arrow from an empty composer | Open the selected task |

Hidden tasks remain hidden through refreshes until explicitly resumed or the TUI restarts. The new shortcuts are configurable under `tui.keymap.agents`, and their defaults yield to conflicting existing custom bindings.

The overview composer also accepts image attachments for background tasks. Escape can return focus to the composer. When connected to a shared app-server, `/archive` now returns to the agents overview instead of exiting; embedded sessions retain their exit behavior.

Code references: `TuiAgentsKeymap` in `codex-rs/config/src/tui_keymap.rs`; `RuntimeKeymap` in `codex-rs/tui/src/keymap.rs`; `confirm_agents_overview_action` in `codex-rs/tui/src/app/agents_overview_actions.rs`; `handle_composer_key` in `codex-rs/tui/src/app/agents_overview_input.rs`; `archive_current_thread` in `codex-rs/tui/src/app/event_dispatch.rs`.


### Clearer activity and completion information

The live status row now follows the latest useful reasoning-summary text, rather than retaining only the first bold heading. Completed reasoning summaries remain available in the expanded transcript. New embedded threads request detailed summaries by default unless configured otherwise.

Successful turns display completion timestamps, including saved timestamps when history is restored. Elapsed duration is displayed for turns longer than 60 seconds.

Adjacent computer-use calls are grouped into compact activity entries while preserving their chronological details. `/copy` also includes completed commentary messages, making progress updates available before the final answer.

Code references: `latest_summary_line` in `codex-rs/tui/src/chatwidget/streaming.rs`; `new_thread_reasoning_overrides` in `codex-rs/tui/src/app_server_session.rs`; `FinalMessageSeparator` in `codex-rs/tui/src/history_cell/separators.rs`; `ComputerActivityCell` in `codex-rs/tui/src/history_cell/computer_activity.rs`; `TranscriptState` in `codex-rs/tui/src/chatwidget/transcript.rs`.


### Managed daemon thread recovery

Managed daemon restarts now preserve eligible loaded threads and restore their runtimes in the background through the normal cold-resume path.

Recovery covers successfully persisted, non-ephemeral root threads. It does not promise continuation of an interrupted command or restoration of every internal worker. Explicit stop and fresh-start paths discard stale recovery handoffs.

Shutdown also stops admitting new regular turns while allowing already delegated work to drain.

Code references: `ThreadRequestProcessor::daemon_recovery_candidates` in `codex-rs/app-server/src/request_processors/daemon_snapshot.rs`; `snapshot` and `start_recovery` in `codex-rs/app-server/src/daemon_thread_recovery.rs`; `codex-rs/app-server/src/turn_admission.rs`.


### User-requested goal pauses

The agent’s existing `update_goal` tool now accepts `"paused"` when the user explicitly asks to pause a goal.

Usage: Ask Codex to “Pause this goal.” The corresponding tool input is:

```json
{"status":"paused"}
```

The tool instructions require an explicit user request, prohibit autonomous pausing, and retain budget-limit precedence.

Code references: `create_update_goal_tool` in `codex-rs/ext/goal/src/spec.rs`; `GoalToolExecutor` in `codex-rs/ext/goal/src/tool.rs`.


### Fork-aware session hooks

`SessionStart` hooks can now distinguish a fork from a fresh startup using the new `source` value `"fork"`.

Usage: Hook handlers that inspect the source should accept:

```json
{"source":"fork"}
```

Forked spawned agents still dispatch through the appropriate `SubagentStart` path.

Code references: `SessionStartSource::Fork` in `codex-rs/hooks/src/events/session_start.rs`; `codex-rs/hooks/src/schema.rs`; `run_pending_session_start_hooks` in `codex-rs/core/src/hook_runtime.rs`.


### Better automatic approval review

Guardian reviews retain complete action arguments and account for the fully assembled request when checking input limits. Optional descriptions can be shortened separately from the action being reviewed.

Recoverable review failures receive bounded retries with backoff and server retry deadlines. Failure messages distinguish an incomplete review from a determination that an action is unsafe; failed reviews do not count as completed policy denials. Network reviews remain tied to the originating execution and its captured settings.

Code references: `codex-rs/core/src/guardian/input_budget.rs`; `codex-rs/core/src/guardian/request_budget.rs`; `run_with_retry` in `codex-rs/ext/guardian-reviewer/src/retry.rs`; `complete_review` in `codex-rs/ext/guardian-reviewer/src/completion.rs`; `codex-rs/core/src/tools/network_approval.rs`.


### More useful feedback responses and diagnostic attachments

The existing `feedback/upload` response adds nullable `promptHash`, allowing clients to correlate a report with its session base instructions. It is a whitespace-normalized SHA-256 hash and excludes later developer messages.

Compressed conversation logs are now attached to diagnostic reports as readable JSONL.

Code references: `FeedbackUploadResponse` in `codex-rs/app-server-protocol/src/protocol/v2/feedback.rs`; `codex-rs/app-server-protocol/schema/json/v2/FeedbackUploadResponse.json`; `FeedbackAttachmentPath::read_attachment` in `codex-rs/feedback/src/lib.rs`.


### Better MCP catalog refresh and extension control

Accepted Codex Apps tool-catalog refreshes propagate to existing threads. Cached MCP bindings can also be reused while unchanged servers remain dormant.

Extension authors can select an HTTP MCP protocol mode for an individual registration using `McpServerContribution::SetWithProtocolMode`. The override applies only if that registration wins server resolution and does not grant hosted-Apps privileges.

Code references: `codex-rs/connectors/src/connector_runtime/mod.rs`; `BindingCatalogRevision` in `codex-rs/codex-mcp/src/connection_manager/tool_catalog.rs`; `McpServerContribution::SetWithProtocolMode` in `codex-rs/ext/extension-api/src/contributors/mcp.rs`; `McpServerRegistration::with_protocol_mode` in `codex-rs/codex-mcp/src/catalog.rs`.


### Environment startup failures reach the agent

Failed environments now appear as failed in model context, with a bounded explanation. `wait_for_environment` reports the startup reason instead of only saying that the environment is unavailable.

Code references: `environment_states` in `codex-rs/core/src/context/world_state/environment.rs`; `environment_failure` in `codex-rs/core/src/tools/handlers/wait_for_environment.rs`.

## Bug Fixes

- Incoming prompts are preserved when pre-turn compaction fails, including failures other than cancellation. Error reporting follows prompt recording. (`run_turn` in `codex-rs/core/src/session/turn.rs`.)
- Disabled-plugin selections survive resume and fork without being replaced by stale ancestor settings. (`latest_disabled_plugin_ids` in `codex-rs/history/src/lib.rs`.)
- Runtime workspace roots are restored during thread resume, and forks preserve source runtime-version metadata at turn cutoffs. (`thread_resume_inner` in `codex-rs/app-server/src/request_processors/thread_processor.rs`; `load_for_fork` in `codex-rs/thread-store/src/local/model_context.rs`.)
- Tool-output truncation budgets survive resume and fork, avoiding repeated adjustment of previously saved budgets. (`CodexHarnessMetadata` in `codex-rs/history/src/lib.rs`; `codex-rs/core/src/session/rollout_budget.rs`.)
- Tool execution and history recording use settings captured for the issuing step. Image detail is normalized for the receiving model, including removal of unsupported `original` detail. (`codex-rs/core/src/session/step_context.rs`; `normalize_image_details` in `codex-rs/core/src/client_common.rs`.)
- Model catalogs are scoped to provider and authentication identity. Legacy unscoped caches are ignored, and results fetched under an outdated identity are not published. (`ModelsCacheEntry` in `codex-rs/models-manager/src/cache.rs`; `OpenAiModelsManager` in `codex-rs/models-manager/src/manager.rs`.)
- Authentication-owner changes invalidate cached Responses WebSocket state and remote-control sessions. Remote control also honors shared server `Retry-After` deadlines. (`ModelClient::new_session` in `codex-rs/core/src/client.rs`; `codex-rs/app-server-transport/src/transport/remote_control/controller.rs` and `server_api.rs`.)
- Exhausted credit and quota responses are recognized as quota errors rather than ordinary rate limits. (`map_api_error` in `codex-rs/codex-api/src/api_bridge.rs`.)
- Failed refreshes of expired MCP OAuth credentials produce authentication/reconnection signals and appear in MCP status. Elicitation cancellation applies beyond native verification, and reconnects reset stale request state. (`recover_after_failed_refresh` in `codex-rs/rmcp-client/src/oauth/refresh_transaction.rs`; `ElicitationClientService` in `codex-rs/rmcp-client/src/elicitation_client_service.rs`; `codex-rs/codex-mcp/src/connection_manager.rs`.)
- Command hooks no longer hang indefinitely while writing to unread stdin or waiting on mutually blocked pipes. Unix hooks detach from the controlling terminal. (`run_command` in `codex-rs/hooks/src/engine/command_runner.rs`.)
- App-server stdio shutdown handles Unix `SIGTERM` and bounds shutdown even when pipes remain blocked. (`start_stdio_connection` in `codex-rs/app-server-transport/src/transport/stdio.rs`.)
- Rollout compression coordinates with active writers, and cancelled startup releases writer ownership. Thread search continues past compressed rollouts that cannot be searched. (`WriterLockCoordinator` in `codex-rs/rollout/src/writer_lock.rs`; `codex-rs/thread-store/src/local/live_writer.rs`; `search_threads` in `codex-rs/thread-store/src/local/search_threads.rs`.)
- Automatic goal continuation stops with a blocked status after three consecutive empty final responses without other activity. (`GoalAccountingState::empty_response_goal` in `codex-rs/ext/goal/src/accounting.rs`; `ActiveGoalStopReason::EmptyResponse` in `codex-rs/ext/goal/src/runtime.rs`.)
- Switching threads clears queued transcript content from the previous thread. Transcript restoration, half-page scrolling, and missed tmux resize notifications are corrected. (`codex-rs/tui/src/app/session_lifecycle.rs`; `PagerView` in `codex-rs/tui/src/pager_overlay.rs`; `codex-rs/tui/src/tui/size_monitor.rs`.)
- Accepting a new prompt clears obsolete pending questions while preserving the handling of actual question answers. (`submit_user_message_with_options` in `codex-rs/tui/src/chatwidget/input_submission.rs`; `codex-rs/tui/src/chatwidget/questions.rs`.)
- Code Mode handles JavaScript `undefined` without attempting to parse it as JSON. (`v8_value_to_json` in `codex-rs/code-mode-runtime/src/runtime/value.rs`.)
- Restricted filesystem sandboxes block WSL Windows-interop escape paths and VM sockets. Legacy Landlock rejects the affected WSL configuration when unrestricted network access prevents safe isolation. (`create_bwrap_command_args` in `codex-rs/linux-sandbox/src/bwrap.rs`; `codex-rs/linux-sandbox/src/landlock.rs`; `ensure_legacy_landlock_mode_supports_policy` in `codex-rs/linux-sandbox/src/linux_run_main.rs`.)
- Windows sandbox setup uses the actual Windows account identity and repairs read/execute access on existing runtime files. Unsafe filesystem-root read-deny policies are rejected before ACL installation. (`current_account_name` in `codex-rs/windows-sandbox-rs/src/winutil.rs`; `ensure_runtime_tree_readable` in `codex-rs/windows-sandbox-rs/src/bin/setup_main/win/setup_runtime_bin.rs`; `plan_deny_read_acl_paths` in `codex-rs/windows-sandbox-rs/src/deny_read_acl.rs`.)
- Client archive/delete requests cannot remove live internal workers owned by another runtime, such as Guardian reviewers. Such requests return JSON-RPC error `-32600`. (`codex-rs/core/src/thread_manager.rs`; `codex-rs/app-server/README.md`.)

## In Development


### Live terminal voice conversations [Experimental]

What: The TUI gains live WebRTC voice conversations through `/voice`.

Status: Disabled by default behind `features.realtime_conversation`; available through `/experimental`.

Usage:

Enable “Voice conversations” in `/experimental`, restart Codex, then enter:

```text
/voice
```

Or configure:

```toml
[features]
realtime_conversation = true
```

Details:

- `/voice` starts or stops the conversation.
- A dedicated voice strip displays recording activity, mute state, and live transcripts.
- `Ctrl+X` toggles microphone capture during voice sessions. It can be remapped through `tui.keymap.chat.toggle_voice_mute`; existing conflicting bindings take precedence over the new default.
- Supported targets are macOS, MSVC-based Windows, and glibc-based Linux builds.
- Voice requires an active conversation and is unavailable in side conversations or parent-controlled input contexts.
- This adds an interactive TUI entry point to existing realtime infrastructure.

Code references: `Feature::RealtimeConversation` in `codex-rs/features/src/lib.rs`; `SlashCommand::Voice` in `codex-rs/tui/src/slash_command.rs`; `ChatWidget::toggle_realtime_conversation` in `codex-rs/tui/src/chatwidget/realtime.rs`; `codex-rs/tui/src/bottom_pane/voice_strip.rs`.


### Configurable credential brokerage [Experimental]

What: The existing network credential broker can protect custom environment-backed credential families in addition to built-in providers.

Status: Requires the opt-in network proxy and credential brokerage.

Usage:

```toml
[features.network_proxy]
enabled = true
credential_broker = true

[features.network_proxy.credentials.vendor]
env = ["VENDOR_TOKEN"]
patterns = ["vendor_[A-Za-z0-9]{32}"]
url_prefixes = ["https://api.vendor.example"]
auth = ["bearer"]
```

Details:

- Provider definitions specify credential environment variables, recognition patterns, authorized URL prefixes, and authentication formats.
- Supported formats are `bearer`, `token`, `basic`, and custom `header` authentication. Header authentication uses `header` and an optional `prefix`.
- `url_prefix_from_env` can supply an additional destination.
- Provider definitions cannot overlap built-in credential source variables. Higher-priority configuration layers can remap custom sources.
- Brokerage now handles copied credentials and embedded aliases more consistently across shell snapshots and replay.
- Destination hints survive child-environment filtering. Protected snapshots are checked before replay, and supported plaintext HTTP tunnels retain destination checks and plaintext-injection policy.
- Enabling the proxy does not itself grant network access.

Code references: `NetworkProxyConfigToml::credentials` in `codex-rs/features/src/feature_configs.rs`; `CredentialProviderConfig` in `codex-rs/network-proxy/src/credential_broker/provider_config.rs`; `ConfiguredCredentialProvider` in `codex-rs/network-proxy/src/credential_broker/configured.rs`; `codex-rs/shell-command/src/shell_snapshot_credentials.rs`; `codex-rs/network-proxy/src/brokered_tunnel.rs`.


### Memory v2, dual writing, and readiness reporting [Experimental]

What: Memory-enabled sessions can select a separate v2 pipeline or generate both memory versions while continuing to read one.

Status: Opt-in through the existing memories feature; v1 remains the default and dual writing is disabled by default.

Usage:

Generate both versions while retaining v1 context:

```toml
[features]
memories = true

[memories]
version = "v1"
dual_write = true
```

Select v2 explicitly with `version = "v2"`.

Experimental app-server clients can query readiness:

```json
{"id":30,"method":"memory/status","params":{"minConsolidatedThreads":20}}
```

Details:

- V1 artifacts remain under `CODEX_HOME/memories`; v2 uses `CODEX_HOME/memories_v2` with separate memory state.
- V2 extraction produces rollout summaries and prioritizes human input, including answers paired with their questions.
- V2 has dedicated consolidation and retrieval instructions.
- `memory/status` returns `v2ConsolidatedThreads` and `v2Ready`. The threshold defaults to 20 and accepts 1–4096.
- Readiness requires sufficient successful consolidation coverage and a valid v2 summary. The query does not switch the selected version.
- Background generation retains existing eligibility checks, including exclusions for ephemeral and subagent sessions.

Code references: `MemoriesToml` in `codex-rs/config/src/types.rs`; `MemoryVersion` in `codex-rs/protocol/src/memory_version.rs`; `start_memories_startup_task` in `codex-rs/memories/write/src/start.rs`; `serialize_tiered_input` in `codex-rs/memories/write/src/rollout_input.rs`; `MemoryStatusParams` in `codex-rs/app-server-protocol/src/protocol/v2/memory.rs`; `memory_status` in `codex-rs/app-server/src/request_processors/memory_status.rs`.


### Model discovery with OpenAI API keys [Experimental]

What: OpenAI API-key sessions can opt into remote Codex model-catalog discovery.

Status: Disabled by default behind `features.api_key_model_discovery`.

Usage:

```toml
[features]
api_key_model_discovery = true
```

Details:

- Without the opt-in, API-key sessions continue using bundled model metadata.
- For the built-in OpenAI provider without a custom base URL, catalog discovery uses the Codex backend’s `/models` endpoint.
- Inference routing remains unchanged.
- Custom OpenAI base URLs are respected. Other providers do not automatically gain this discovery capability.
- App-server also accepts this feature through its existing runtime feature-enablement API.

Code references: `Feature::ApiKeyModelDiscovery` in `codex-rs/features/src/lib.rs`; `OpenAiModelsEndpoint::list_models` in `codex-rs/model-provider/src/models_endpoint.rs`; `OpenAiModelsManager::refresh_available_models` in `codex-rs/models-manager/src/manager.rs`.


### Native macOS user verification and cancellation [Experimental]

What: Existing verification RPCs gain a native macOS implementation, and a new cancellation RPC can interrupt an outstanding local operation.

Status: Experimental protocol surface with a macOS native provider. Automatic verification UI activation is restricted to the bundled in-process TUI on supported devices.

Usage:

After opting into `experimentalApi`, a local client can query:

```json
{"id":40,"method":"userVerification/status","params":{}}
```

Cancel an outstanding operation using its original request ID:

```json
{"id":42,"method":"userVerification/cancel","params":{"requestId":41}}
```

Details:

- The implementation uses protected P-256 keys and native authentication to sign challenges.
- Keys are scoped to the authenticated workspace membership.
- Hosted Codex Apps can request verification through the bundled TUI. Third-party MCP registrations do not receive this capability merely by using a similar name.
- Remote workspaces cannot trigger local signing through the TUI; network-origin connections cannot invoke enrollment, deletion, or signing on the server’s device.
- Cancellation acknowledges the signal without waiting for native work to finish. It cannot undo completed effects.
- Enrollment currently creates a local key only. Backend registration and server-side revocation remain unfinished.

Code references: `Service::handle` in `codex-rs/app-server/src/user_verification.rs`; `NativeProvider` in `codex-rs/user-verification/src/platform_macos/provider.rs`; `UserVerificationCancelParams` in `codex-rs/app-server-protocol/src/protocol/v2/user_verification.rs`; `codex-rs/app-server/src/request_processors/initialize_processor.rs`; `server_mcp_extensions` in `codex-rs/codex-mcp/src/client_capabilities.rs`.


### Independent hosted-Apps MCP protocol selection [Experimental]

What: Hosted Codex Apps can opt into MCP protocol 2026-07-28 independently of other MCP servers.

Status: Disabled by default behind a dedicated feature flag.

Usage:

```toml
[features]
codex_apps_mcp_2026_07_28 = true
```

Details:

- The flag applies to the host-owned HTTP Apps registration.
- Discovery falls back to Legacy when the server does not support the newer protocol.
- The existing `mcp_2026_07_28` flag continues to govern eligible other servers.
- A new host-facing `list_codex_apps_resources` helper supports MIME-filtered resource pages. It is groundwork for integrations, not a new CLI command or app-server RPC; continuation requests must retain the MIME filter.

Code references: `Feature::CodexAppsMcp20260728` in `codex-rs/features/src/lib.rs`; `McpConfig::host_owned_apps_protocol_mode` in `codex-rs/codex-mcp/src/mcp/mod.rs`; `CodexAppsResourceListParams` and `McpResourceClient::list_codex_apps_resources` in `codex-rs/codex-mcp/src/resource_client.rs`.


### Worktree ownership details and deletion [Experimental]

What: The existing managed-worktree browser shows owner-thread details and offers confirmed deletion.

Status: Requires the existing opt-in `worktrees` feature and a local Git repository.

Usage:

```toml
[features]
worktrees = true
```

Open `/worktree`, choose “Browse worktrees,” then select a checkout.

Details:

- Entries show the owning thread’s title, update age, and archived or unavailable status.
- Actions include resuming an available owner, copying the working directory, and deleting the worktree.
- Deletion requires confirmation and refuses the current checkout.
- Removal does not force-delete local changes and also refuses ignored local files.

Code references: `ChatWidget::show_managed_worktrees` and related browser methods in `codex-rs/tui/src/chatwidget/worktree_picker.rs`; `Owner` in `codex-rs/tui/src/worktree_browser.rs`; `WorktreeManager::remove` in `codex-rs/worktree/src/lib.rs`.


### Enterprise OIDC login groundwork [In Development]

What: A staged enterprise sign-in implementation separates browser authorization from committing credentials.

Status: New library infrastructure; no new CLI command or app-server login endpoint is wired in this diff.

Details:

- Discovery requires published authorization metadata matching the configured issuer.
- Validated grants are committed to the keyring only after the host rechecks the active login attempt and identity.
- Logout coordination invalidates pending sign-ins so they cannot later restore deleted credentials.

Code references: `EnterpriseOAuthLoginRequest`, `EnterpriseOAuthCredentials::commit_if`, and `EnterpriseOAuthCredentialGuard` in `codex-rs/rmcp-client/src/enterprise_oauth_login.rs`.


### Native MXC permission translation [In Development]

What: Windows MXC groundwork translates Codex filesystem and network policies into native execution requests.

Status: The new policy builder is not connected to a production execution caller in this snapshot.

Details:

- Translation handles explicit paths, symbolic `:root`, volume grants, deny globs, and read-only exceptions.
- Unsupported symbolic paths produce errors.
- This does not establish a newly usable sandbox backend.

Code references: `build_request` and `PolicyError` in `codex-rs/mxc-sandbox/src/policy.rs`.

## Notes

- **Remote compaction:** Supported providers now always use streamed remote compaction through the normal Responses path. The `remote_compaction_v2` feature key is retained as a removed compatibility key and no longer selects the legacy implementation. Remove configurations that rely on setting it to `false` to restore the old path. References: `Feature::RemoteCompactionV2` in `codex-rs/features/src/lib.rs`; `codex-rs/core/src/session/turn.rs`; `codex-rs/core/src/compact_remote_v2.rs`.
- **Windows slash command:** `/sandbox-add-read-dir` has been removed. Update workflows that invoke it; this diff introduces no replacement slash command. Reference: `SlashCommand` in `codex-rs/tui/src/slash_command.rs`.
- **Bundled model catalog:** `gpt-5.2` and `gpt-5.4-mini` entries were removed from the bundled catalog. Saved `gpt-5.4-mini` selections retain migration guidance to `gpt-5.6-luna` when that target is available. This is a bundled-catalog change, not proof of universal backend availability. References: `codex-rs/models-manager/models.json`; `model_upgrade_for_migration` in `codex-rs/tui/src/app/startup_prompts.rs`.
- **Daemon installation pins:** Automatic updates require recorded stable-`latest` channel selection. Older standalone installations without that metadata remain usable but need a new `latest` installation to opt into updating. Explicit release pins are preserved. Reference: `codex-rs/app-server-daemon/src/managed_install.rs`.
- **Client compatibility:** Hook consumers should accept the new `"fork"` source. App-server clients should tolerate the added attachment notification and nullable `promptHash` response field. Experimental methods still require the appropriate initialization opt-in.


Generated with:
- tool: `harness-investigations@023fcb0-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.155.0.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
