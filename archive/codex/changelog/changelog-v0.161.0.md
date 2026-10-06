# Changelog for version 0.161.0

## Release Status

> **Not yet released:** `rust-v0.161.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.160.1, this snapshot adds interactive MCP login, audio-device and microphone-channel selection, conversation forking from the agents overview, and additional administrator controls. It also enables API-key model discovery by default and improves saved-history recovery, permission handling, and Windows startup. `rust-v0.161.0` is an intermediate development source snapshot: no published GitHub Release was found during the supplied sync, so this changelog does not imply that binaries or release assets were published.

## New Features


### MCP login from the interactive session

What: Start authentication for a configured MCP server without leaving the interactive Codex session.

Usage:

```text
/mcp login my-server
```

Details:

- Codex starts the existing `mcpServer/oauth/login` flow and opens its authorization URL.
- The request uses the active thread’s MCP configuration.
- OAuth login itself already existed; the new capability is its integration into the `/mcp` command.
- Enterprise-managed authentication follows the additional requirements described under In Development.

Code references:

- `SlashCommand::Mcp` handling in `codex-rs/tui/src/chatwidget/slash_dispatch.rs`
- `AppEvent::StartMcpLogin` handling in `codex-rs/tui/src/app/event_dispatch.rs`
- `McpRequestProcessor::mcp_server_oauth_login` in `codex-rs/app-server/src/request_processors/mcp_processor.rs`


### Select voice devices and microphone channels

What: Choose microphone and speaker devices in voice settings, including which channels to mix from a multichannel microphone.

Usage:

```text
/voice settings
```

Choose the sound-device settings, then select an input or output device. Settings can also be stored in the user configuration:

```toml
[audio]
microphone = "My audio interface"
speaker = "My speakers"
microphone_channel = [1, 3]
```

Details:

- `microphone_channel` accepts a single channel number or a list.
- Channels are numbered from one. Omitting the setting mixes all input channels.
- Selected channels are averaged before audio metering and processing; empty selections and unavailable channels are rejected.
- The interactive channel picker appears for microphones with at least three channels.
- Changing microphones clears the saved channel selection.
- Device preferences are local to the computer running the terminal UI, including when connected to a remote app-server.
- Changes apply to the next voice conversation.
- Duplicate device names cannot be selected individually; the system-default choice remains available.
- Actual voice availability still depends on the supported voice backend and audio helper.

Code references:

- `MicrophoneChannels` and `RealtimeAudioToml` in `codex-rs/config/src/config_toml.rs`
- `ChatWidget::open_realtime_sound_devices`, `open_realtime_device_picker`, and `open_realtime_input_channels` in `codex-rs/tui/src/chatwidget/realtime_settings.rs`
- `App::persist_realtime_audio` in `codex-rs/tui/src/app/realtime_settings.rs`
- `InputChannel::new` in `codex-rs/voice-host/src/input_channel.rs`
- `VoiceHost::list_devices` in `codex-rs/realtime-webrtc/src/client.rs`


### Fork a conversation from the agents overview

What: Fork the selected conversation directly from `/agents` and open the resulting session.

Usage:

```text
/agents
```

Select a conversation and press `f`. The binding is configurable:

```toml
[tui.keymap.agents]
fork = "f"
search = ["f3", "/"]
```

Details:

- The source conversation and its draft are preserved.
- Attachment replay does not automatically submit queued input or resume a paused goal.
- Forking another task is blocked while a side conversation is open.
- The default search shortcuts change from `f` to `F3` or `/`; `f` now means fork.
- Conversation forking already existed elsewhere; this adds an agents-overview action.

Code references:

- `TuiAgentsKeymap::fork` in `codex-rs/config/src/tui_keymap.rs`
- Default agents bindings in `codex-rs/tui/src/keymap.rs`
- `AgentsOverviewView::handle_key_event` in `codex-rs/tui/src/app/agents_overview_view.rs`
- `AppEvent::ForkAgentsOverviewThread` in `codex-rs/tui/src/app/event_dispatch.rs`


### Administrator control over Windows MXC sandbox selection

What: Managed requirements can prohibit the MXC Windows sandbox, including automatic selection.

Usage, in administrator-managed `requirements.toml`:

```toml
[windows]
allow_mxc = false
```

Details:

- The requirement blocks both explicit `windows.sandbox = "mxc"` requests and automatic MXC selection.
- It can be combined with existing restrictions on allowed sandbox implementations.
- `allow_mxc` is a managed requirement, rather than an ordinary user preference.
- MXC itself predates this snapshot.

Code references:

- `WindowsRequirementsToml` in `codex-rs/config/src/config_requirements.rs`
- `prepare_windows_sandbox_config` and `config_allows_mxc` in `codex-rs/core/src/config/windows_sandbox_config.rs`


### Separate managed controls for browser annotation APIs and desktop Voice

What: Administrators can separately control website-driven annotation APIs and in-app Voice.

Usage, in administrator-managed `requirements.toml`:

```toml
[features]
browser_annotation_api = false
in_app_voice = false
```

Details:

- `browser_annotation_api` controls whether websites may open or customize browser annotation tools.
- Ordinary user-driven annotation is independent of that permission.
- `in_app_voice` controls permission to use desktop Voice; allowing it does not establish provider support or feature availability.
- Both permissions default to allowed when requirements do not restrict them.
- These are requirements-only controls, rather than user-configurable feature switches.

Code references:

- `Feature::BrowserAnnotationApi`, `Feature::InAppVoice`, and their `FeatureSpec` entries in `codex-rs/features/src/lib.rs`

## Improvements


### API-key model discovery is enabled by default

OpenAI API-key sessions now use model-catalog discovery by default. The existing `api_key_model_discovery` feature moves from disabled development status to stable, default-enabled behavior.

To opt out:

```toml
[features]
api_key_model_discovery = false
```

Disabling discovery also prevents the models manager from continuing to use an API-key-discovered cached catalog. This applies to supported OpenAI API-key discovery paths; it does not establish catalog discovery for every custom provider.

Code references: `Feature::ApiKeyModelDiscovery` in `codex-rs/features/src/lib.rs`; `OpenAiModelsManager::api_key_discovery_disabled` in `codex-rs/models-manager/src/manager.rs`.


### Additional Bedrock regions and preserved model capabilities

The existing Amazon Bedrock Mantle integration recognizes `us-gov-east-1` and `us-gov-west-1`, including their regional OpenAI-compatible endpoint URLs.

Bedrock catalog normalization also stops forcing the older multi-agent tool configuration and stops removing the `Ultra` reasoning option. Available options therefore follow the supplied model catalog more closely; this does not guarantee that every Bedrock model supports those capabilities.

Usage: select the configured Bedrock provider and use `/model` to choose among the options its catalog advertises.

Code references: `is_supported_amazon_bedrock_region`, `is_amazon_bedrock_gov_cloud_region`, and endpoint construction in `codex-rs/model-provider/src/amazon_bedrock/mantle.rs`; `normalize_bedrock_catalog` and `bedrock_model` in `codex-rs/model-provider/src/amazon_bedrock/catalog.rs`.


### Goal updates can identify explicit user intent

The existing `thread/goal/set` and `thread/goal/clear` methods gain an optional `origin` field:

```json
{
  "id": 1,
  "method": "thread/goal/set",
  "params": {
    "threadId": "thr_123",
    "objective": "Finish the migration and verify it",
    "origin": "user"
  }
}
```

Accepted values are `"user"` and `"automatic"`.

Explicit user-origin objective or status changes are recorded as durable user-goal updates before the goal mutation and continuation occur. Clearing a goal can likewise identify explicit user intent. Automatic updates, omitted origins, and budget-only updates do not manufacture an explicit user instruction.

The terminal UI supplies user origin for its corresponding goal actions.

Code references:

- `ThreadGoalMutationOrigin`, `ThreadGoalSetParams`, and `ThreadGoalClearParams` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- Goal request handling in `codex-rs/app-server/src/request_processors/goal_processor.rs`
- `record_user_goal_update` in `codex-rs/core/src/thread_goal_user_context.rs`
- Updated schemas `codex-rs/app-server-protocol/schema/json/v2/ThreadGoalSetParams.json` and `ThreadGoalClearParams.json`


### MCP OAuth attempts have correlatable login IDs

`mcpServer/oauth/login` responses and `mcpServer/oauth/login/completed` notifications gain an optional `loginId`. Clients can associate completion with a specific authentication attempt instead of relying solely on the server name.

The terminal UI uses this identity and the associated thread to avoid applying stale completion events after a login has been replaced or canceled. Clients supporting older servers should continue accepting messages without `loginId`.

Code references:

- `McpServerOauthLoginResponse` and `McpServerOauthLoginCompletedNotification` in `codex-rs/app-server-protocol/src/protocol/v2/mcp.rs`
- MCP login event handling in `codex-rs/tui/src/app/app_server_events.rs`
- Updated schemas `codex-rs/app-server-protocol/schema/json/v2/McpServerOauthLoginResponse.json` and `McpServerOauthLoginCompletedNotification.json`


### Protocol errors tolerate future variants

Unknown `CodexErrorInfo` string or object variants now deserialize as `Other`, rather than making the entire message fail to parse. Known structured error variants retain their existing behavior.

This improves compatibility when a newer server introduces an error category that an older client does not recognize. Generated TypeScript definitions also accommodate unknown variants.

Code references: `CodexErrorInfo` and `deserialize_other_codex_error_info` in `codex-rs/app-server-protocol/src/protocol/v2/shared.rs`; updated error schemas under `codex-rs/app-server-protocol/schema/json/v2/`.


### Earlier detection and clearer reporting of database corruption

SQLite opening now includes a bounded quick check, with a 100 ms budget per database file and checks shared across opens using the same configuration identity. Corruption classification uses SQLite error information rather than matching error-message text.

Existing backup-and-rebuild recovery is applied to recoverable databases such as state, logs, goals, memories, and queue storage. Thread-history storage follows its separate recovery handling rather than being indiscriminately rebuilt.

Recovery notices identify backup locations and explain that database-only metadata may be unavailable while saved rollout conversations remain available.

Code references:

- `SqliteConfig::open_read_write_pool_with_spec` in `codex-rs/state/src/sqlite.rs`
- `SqliteQuickCheckManager::quick_check_once` in `codex-rs/state/src/sqlite/validation.rs`
- `is_sqlite_corruption_error` in `codex-rs/state/src/runtime/recovery.rs`
- `sqlite_recovery_notice` in `codex-rs/app-server/src/lib.rs`


### Diagnostic logs receive periodic retention maintenance

The logs database now receives background maintenance at startup and every 30 minutes. Retention targets a maximum age of ten days and can shorten that window to keep occupied database pages within a 64 MiB budget.

The newest second of logs is retained even when trimming is necessary. This limits retained diagnostic data; it does not guarantee that the database file immediately shrinks, because SQLite can reuse freed pages.

Code references: `StateRuntime::start_periodic_logs_maintenance` and `prune_by_age_and_size` in `codex-rs/state/src/runtime/logs_maintenance.rs`.


### Saved-history browsing does less blocking work

History discovery moves directory scanning and metadata work to blocking workers with cancellation support. Thread-name lookup scans the session index from newest entries and stops after finding the requested IDs, while database name retrieval is batched.

History projection reading is also consolidated into blocking work. These changes reduce work on asynchronous execution paths when browsing or reopening large histories; no specific speedup is established by the diff.

Code references: `run_scan` in `codex-rs/rollout/src/list_files.rs`; `find_thread_names_by_ids` in `codex-rs/rollout/src/session_index.rs`; `read_projection_steps_sync` in `codex-rs/thread-store/src/local/thread_history_materialization.rs`.


### Feedback can include updater failure logs

Feedback submitted with log inclusion enabled can now attach bounded tails of current and previous daemon-updater stderr logs. Previous output is preserved before the launcher truncates the current log, helping retain evidence of failures across restarts.

Attachments are limited to two 256 KiB tails, with compatibility handling for the older app-server-updater log filename.

Code references: `daemon_log_attachments` in `codex-rs/feedback/src/daemon_logs.rs`; feedback handling in `codex-rs/app-server/src/request_processors/feedback_processor.rs`; `stderr_log::preserve` in `codex-rs/app-server-daemon/src/backend/stderr_log.rs`.


### Multiline pastes continue Markdown blockquotes

Pasting multiple lines into a prompt line beginning with `> ` now continues the quote prefix across the pasted lines, including blank and trailing lines.

This applies to prompt composition and embedded answer editors. Shell input, search fields, and startup input retain literal paste behavior.

Code references: `ChatComposer::handle_paste` in `codex-rs/tui/src/bottom_pane/chat_composer/paste_input.rs`.

## Bug Fixes

- Explicitly approved sandbox escalation can widen filesystem access while retaining denied-read restrictions and protected metadata. A command allow rule alone does not grant that wider access, and unsupported remote implementations reject the request with upgrade guidance. (`SandboxOverride::EscalatedSandboxWithRestrictions` in `codex-rs/core/src/tools/sandboxing.rs`; `ToolOrchestrator::run` in `codex-rs/core/src/tools/orchestrator.rs`.)

- Permission grants stay associated with the turn that requested them, including background requests. Session-scoped grants remain available across turns, while subsequent reviews use the appropriate turn context. (`TurnContext::granted_permissions` and `record_granted_permissions` in `codex-rs/core/src/session/turn_context.rs`; `StepContext::environments` in `codex-rs/core/src/session/step_context.rs`.)

- Remote and daemon-backed terminal sessions adopt the server’s effective permissions and authoritative permission catalog more consistently. Pending selections are carried through new sessions, forks, and working-directory changes; an unconfirmed custom profile is not silently applied after changing directories. (`App::adopt_server_permissions` and `select_permission_profile` in `codex-rs/tui/src/app/config_persistence.rs`; working-directory handling in `codex-rs/tui/src/app/working_directory.rs`.)

- Web-search launch overrides preserve configuration precedence instead of forwarding a locally resolved default that overwrites a remote server’s settings. (`apply_launch_override` in `codex-rs/tui/src/app_server_session/web_search.rs`.)

- Renaming a live thread persists its recorder metadata before updating SQLite, helping empty or newly created threads remain discoverable after restarting. (`update_thread_metadata` in `codex-rs/thread-store/src/local/update_thread_metadata.rs`.)

- Resuming a thread no longer reuses a history snapshot that became stale while a writer updated the rollout. Revision checks coordinate history reads with live writers. (`history_revision::read` in `codex-rs/thread-store/src/local/history_revision.rs`; resume handling in `codex-rs/thread-store/src/local/live_writer.rs`.)

- File-search results are checked against their originating query, preventing an older result snapshot from being presented as the answer to a newer search. (`snapshot::for_query` in `codex-rs/file-search/src/snapshot.rs`.)

- Pressing Enter flushes an expired paste burst before submission, avoiding lost final characters when submission occurs before the next UI tick. (Paste-burst flushing in `codex-rs/tui/src/bottom_pane/chat_composer.rs`.)

- Restored structured answers escape initial slash-command and shell-command prefixes, preventing recovered draft text from unexpectedly becoming a command. (Inline-input recovery in `codex-rs/tui/src/bottom_pane/chat_composer/inline_input.rs`.)

- Copying rendered Markdown preserves literal inline code and generated file paths more accurately while retaining Markdown formatting for mixed selections. (`CopyLine::is_literal` in `codex-rs/tui/src/markdown_copy.rs`; copy rendering in `codex-rs/tui/src/markdown_render.rs`.)

- Temporary structured-output threads no longer surface interactive approval or tool requests in the main terminal conversation. (`App::handle_app_server_request` in `codex-rs/tui/src/app/app_server_events.rs`.)

- Windows sandbox runner creation retries once for the transient `ERROR_SERVICE_ALREADY_RUNNING` failure when no runner has started. It does not replay a command that already began execution. (`retry_runner_spawn_once` in `codex-rs/windows-sandbox-rs/src/runner_client.rs`.)

- Windows sandbox provisioning grants the required profile-directory metadata access without inheriting that grant into descendants or overriding their deny permissions. (`run_setup_full` in `codex-rs/windows-sandbox-rs/src/setup_provisioning.rs`; `ensure_allow_mask_aces_with_inheritance_impl` in `codex-rs/windows-sandbox-rs/src/acl.rs`.)

- Elevated Windows CLI launches use embedded execution with a warning instead of failing daemon startup. (`run_main_inner` in `codex-rs/cli/src/startup_orchestration.rs`; `ELEVATED_LAUNCH_WARNING` in `codex-rs/cli/src/daemon_startup.rs`.)

- Background daemon and updater launches handle deleted working directories more reliably. Windows launches also separate their working directory from private state storage to avoid broadening that storage directory’s ACLs. (`set_working_directory` in `codex-rs/app-server-daemon/src/background_command.rs`; `PidBackend::start` in `codex-rs/app-server-daemon/src/backend/pid_start.rs`.)

- WebSocket reconnection delays remain at their configured cap during prolonged failures instead of resetting to faster retries. (`next_reconnect_delay` in `codex-rs/app-server-transport/src/websocket.rs`.)

- Failed Responses WebSocket upgrades preserve `Retry-After` information so retry handling can honor it before HTTP fallback. Existing retry limits still apply. (`map_ws_error` in `codex-rs/codex-api/src/endpoint/responses_websocket.rs`; `handle_response_stream_error` in `codex-rs/core/src/responses_retry.rs`.)

- Executor environment-information requests have a bounded send-and-receive timeout, and canceled RPC requests remove their pending entries. A failed probe initiates connection recovery without automatically replaying the failed request. (`ExecServerClient::force_environment_info` in `codex-rs/exec-server/src/client.rs`; `PendingRequestGuard` in `codex-rs/exec-server/src/rpc_pending_request.rs`.)

- Canceled local file reads stop further chunk work. Ordinary file reads also avoid blocking on unsupported special files such as FIFOs or Windows pipes. (`read_file` in `codex-rs/exec-server/src/local_file_system_read.rs`; regular-file opening in `codex-rs/exec-server/src/regular_file.rs`.)

- Failed or canceled shell-snapshot capture cleans up its process group instead of leaving capture processes behind. (`SnapshotCapture` in `codex-rs/exec-server/src/shell_snapshot_process.rs`.)

- Credential-storage errors avoid exposing raw credential contents in JSON-decoding and keyring failures while retaining useful operating-system error context. (`with_context` in `codex-rs/login/src/auth/storage_error.rs`; `CredentialStoreError` in `codex-rs/keyring-store/src/lib.rs`.)

## In Development


### Daybreak controls in CLI sessions [Experimental]

What: Opt-in CLI controls select Daybreak access programs using the connected model catalog and account availability.

Status: Runtime-gated by `features.cli_daybreak`, which is disabled by default and marked under development.

Usage:

```toml
daybreak = true

[features]
cli_daybreak = true
```

In an interactive session:

```text
/daybreak
```

Details:

- The top-level `daybreak` setting controls the default preference for new threads and non-interactive turns.
- The interactive command changes the selection and persists the preference.
- Resumed and forked threads can retain their saved selection; an explicit launch override can take precedence.
- Status-line and terminal-title support can display the selection.
- Automatic selection requires the OpenAI provider, supported ChatGPT authentication, and catalog-advertised access.
- Configuration does not grant account entitlement.
- Side conversations do not inherit enabled Daybreak behavior.

Code references:

- `Feature::CliDaybreak` in `codex-rs/features/src/lib.rs`
- `ConfigToml::daybreak` in `codex-rs/config/src/config_toml.rs`
- `program_for_turn` in `codex-rs/tui/src/daybreak.rs`
- `App::persist_daybreak_selection` in `codex-rs/tui/src/app/daybreak.rs`
- Non-interactive selection in `codex-rs/exec/src/daybreak.rs`


### Explicit Cyber access-program selection [Experimental]

What: Non-interactive execution can request a specific Cyber access program for a turn.

Status: The argument is explicitly experimental. API-key forwarding additionally requires `features.api_key_cyber_access_programs`, which is disabled by default.

Usage:

```bash
codex exec --cyber-access-program standard "Inspect the repository"
```

For supported OpenAI API-key authentication:

```toml
[features]
api_key_cyber_access_programs = true
```

Details:

- Accepted values are `standard`, `daybreak_blue`, and `daybreak_red`.
- Omitting the option leaves selection to server defaults.
- The option is restricted to the OpenAI provider and supported authentication.
- It is unsupported with `review`; `fork` requires a prompt.
- The server remains responsible for deciding whether the requested access is available.
- This explicit argument is distinct from the `cli_daybreak` automatic-selection gate.

Code references: `CyberAccessProgramCliArg` and `SharedCliOptions::cyber_access_program` in `codex-rs/exec/src/cli.rs`; authentication checks in `codex-rs/core/src/cyber_access_program.rs`.


### Enterprise-managed MCP authentication becomes operational [Experimental]

What: Configured enterprise-managed MCP servers can authenticate through a shared enterprise identity-provider grant.

Status: Runtime-gated by `features.use_xaa`, disabled by default and marked under development. Enterprise authentication configuration existed previously; this snapshot connects it to login and authenticated MCP requests.

Usage:

```toml
[features]
use_xaa = true
```

After an administrator has supplied a trusted enterprise identity-provider configuration and a directly configured MCP server using `auth = "ema_auth"`:

```text
/mcp login company-server
```

Details:

- The implementation supports directly configured Streamable HTTP MCP servers.
- Login stores a shared identity-provider refresh credential, then exchanges it for resource-specific MCP access tokens.
- Token use is confined to the authorized endpoint; redirects and automatic replay of an unauthorized operation are not used to broaden access.
- Replacement and cancellation coordinate the login listener and completion lifecycle.
- Enterprise authentication supplied through plugin overlays is disabled rather than treated as ordinary OAuth.
- Successful login or newly admitted configuration may require a fresh session. Existing sessions can lose authorization after revocation but do not automatically gain new enterprise admission through reload.
- Logging out an enterprise server removes the shared enterprise grant, potentially affecting other resources using that grant.
- Configuration reload fails closed for rejected enterprise changes. A reported reload failure can occur after other refresh work has already been applied.

Code references:

- `McpRequestProcessor::mcp_server_oauth_login` in `codex-rs/app-server/src/request_processors/mcp_processor.rs`
- `EnterpriseLoginState` in `codex-rs/app-server/src/request_processors/account_processor/enterprise_login.rs`
- `McpServerIdpOAuthConfig::credential_name` in `codex-rs/config/src/mcp_ema.rs`
- `EmaAuthenticatedHttpClient` in `codex-rs/rmcp-client/src/ema_http_client.rs`
- Enterprise token exchange in `codex-rs/rmcp-client/src/ema_auth.rs`


### Remote message-board configuration and live notifications [Experimental]

What: Multi-agent sessions can select a provisioned remote message board and receive its notifications during active turns.

Status: Opt-in configuration under `multi_agent_v2`, which is disabled by default. The remote-board client already existed; the additions wire it into session configuration and turn lifecycles.

Usage:

```toml
[features.multi_agent_v2]
enabled = true

[features.multi_agent_v2.message_board_remote]
url = "https://board.example"
bearer_token_env_var = "CODEX_BOARD_TOKEN"
```

Details:

- A research host must provision the board and establish the appropriate session and agent-tree membership.
- Remote configuration selects the remote backend instead of local storage.
- Active turns install an SSE notification connection before inference and retry connection failures.
- Notifications are delivered only to their owning active turn; invalid notifications are skipped.
- Missed messages are not automatically replayed by reconnecting. Board searches using `after_message_id` provide a recovery path.
- The credential can come from the named environment variable instead of being stored directly in configuration.

Code references:

- `RemoteMessageBoardConfigToml` and `MultiAgentV2ConfigToml::message_board_remote` in `codex-rs/features/src/feature_configs.rs`
- `install_agent_message_board` in `codex-rs/core/src/agent_message_board.rs`
- `install_notifications` in `codex-rs/agent-message-board-client/src/notifications.rs`


### Agent model catalog in conversation context [Experimental]

What: Available spawn-model choices can be supplied as updated conversation context instead of being embedded in tool descriptions.

Status: Runtime-gated by `features.model_catalog_in_context`, disabled by default and marked under development.

Usage:

```toml
[features]
model_catalog_in_context = true
```

Details:

- A bounded catalog description is appended through developer context.
- Catalog updates can reflect refreshed model choices without rewriting earlier messages.
- The setting changes how model choices are communicated; it does not independently enable multi-agent spawning.

Code references: `ModelCatalogState` in `codex-rs/core/src/context/world_state/model_catalog.rs`; `SpawnAgentToolOptions` in `codex-rs/core/src/tools/spec/multi_agents_spec.rs`.


### Stateful Guardian classification [Experimental]

What: Guardian’s asynchronous classifier can retain completed classification history across reviews in a parent task.

Status: Available through the existing, default-disabled `guardianv2` feature. Conversation mode is a new configurable option; otherwise the model’s default is used, falling back to snapshots.

Usage:

```toml
[features.guardianv2]
enabled = true
async_classifier_mode = "conversation"
async_classifier_conversation_token_limit = 100000
```

Details:

- Conversation mode sends new evidence while retaining completed prior classifications and review identities.
- Incomplete or superseded classifications are not committed to retained history.
- Authentication changes, instruction changes, compaction changes, or the configured projected token budget can reset that history.
- The default retained-history threshold is 100,000 estimated tokens.
- Fresh requests remain subject to the classifier model’s independent input limit.

Code references:

- `AsyncClassifierMode` in `codex-rs/protocol/src/openai_models/guardian_v2.rs`
- `GuardianV2ConfigToml` in `codex-rs/features/src/feature_configs.rs`
- `GuardianV2Config::classifier_mode` in `codex-rs/ext/guardian-v2/src/async_scorer/config.rs`
- Conversation classifier implementation in `codex-rs/ext/guardian-v2/src/async_scorer/conversation.rs`


### Keep bundled tools available after login-shell startup [Experimental]

What: Restore executor-provided package directories when login-shell initialization replaces `PATH`.

Status: Runtime-gated by `features.login_shell_package_path`, disabled by default and exposed as an experimental feature.

Usage:

```toml
[features]
login_shell_package_path = true
```

Details:

- Supported Bash, Zsh, and `sh` login-shell invocations restore the executor’s prepended package directories after startup.
- This helps bundled tools such as ripgrep remain discoverable.
- An explicit `PATH` override takes precedence.
- Unsupported shell invocations and read-only environment cases are not rewritten.

Code references: `Feature::LoginShellPackagePath` in `codex-rs/features/src/lib.rs`; `ShellInvocation::derive_exec_args_with_path_prepends` in `codex-rs/core/src/shell.rs`; unified execution handling in `codex-rs/core/src/tools/runtimes/unified_exec.rs`.


### Bedrock GovCloud configuration advisory [Experimental]

What: App-server clients can check whether the active Bedrock configuration resolves to GovCloud and whether managed requirements meet a specific baseline.

Status: Implemented, but registered as an experimental app-server method; clients must negotiate experimental API access.

Usage:

```json
{
  "id": 1,
  "method": "account/bedrock/checkGovCloudRequirements",
  "params": {}
}
```

Example result:

```json
{
  "isGovCloud": true,
  "shouldWarn": true
}
```

Details:

- The check loads current authentication and configuration, making it suitable after login or setup.
- Official Bedrock endpoint hostnames take precedence when resolving the region.
- For GovCloud, the baseline checks for API-only managed login requirements and an enabled application-network policy explicitly allowing the active endpoint domain.
- `shouldWarn: false` is not a general certification of network configuration.
- Configuration and region-resolution failures remain RPC errors.

Code references:

- `"account/bedrock/checkGovCloudRequirements"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `BedrockCheckGovCloudRequirementsParams` and `BedrockCheckGovCloudRequirementsResponse` in `codex-rs/app-server-protocol/src/protocol/v2/bedrock.rs`
- `AccountRequestProcessor::bedrock_check_gov_cloud_requirements` in `codex-rs/app-server/src/request_processors/account_processor/bedrock_gov_cloud.rs`


### Thread prediction protocol [In Development]

What: Protocol definitions describe requesting a prediction from a completed source turn and receiving its eventual result.

Status: The experimental method is registered, but its handler returns a method-not-found error stating that it is not implemented.

Declared request shape:

```json
{
  "id": 1,
  "method": "thread/prediction/request",
  "params": {
    "threadId": "thr_123",
    "sourceTurnId": "turn_456"
  }
}
```

Details:

- The defined immediate response is empty.
- A corresponding `thread/prediction/updated` notification describes completed or failed results; completed results can include text.
- These are protocol preparations, not a usable prediction feature in this snapshot.
- Negotiating experimental API access does not implement the missing handler.

Code references:

- `"thread/prediction/request"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `ThreadPredictionRequestParams`, `ThreadPredictionUpdatedNotification`, and `ThreadPredictionResult` in `codex-rs/app-server-protocol/src/protocol/v2/thread_prediction.rs`
- Unimplemented handler in `codex-rs/app-server/src/message_processor.rs`
- New schema `codex-rs/app-server-protocol/schema/json/v2/ThreadPredictionUpdatedNotification.json`


### Writable executor file-stream protocol [In Development]

What: Executor protocol types prepare for opening replacement streams and writing file blocks.

Status: Unimplemented. The server rejects writable streams, and `fileWriteStreaming` defaults to false.

Declared write request shape:

```json
{
  "method": "fs/writeBlock",
  "params": {
    "handleId": "handle_123",
    "offset": 0,
    "chunk": "SGVsbG8="
  }
}
```

Details:

- `FsOpenMode` defines read and replacement modes; replacement is intended to create or truncate a file.
- Omitting the open mode preserves read-only behavior for existing clients.
- `chunk` carries base64-encoded bytes.
- Writable open and write requests currently fail with `exec-server does not support writable file streams`.
- Client capability checks prevent a writable request from being sent to an older server that could silently ignore its mode.
- These methods belong to the executor protocol, not the public app-server JSON-RPC API.

Code references: `FsOpenMode`, `FsWriteBlockParams`, and `FsWriteBlockResponse` in `codex-rs/exec-server-protocol/src/protocol.rs`; `FileSystemHandler::write_block` in `codex-rs/exec-server/src/server/file_system_handler.rs`; `ExecServerClient::fs_open` in `codex-rs/exec-server/src/client.rs`.

## Notes

- Agents-overview users should update shortcut expectations or custom bindings: `f` now forks, while `F3` and `/` search.
- Goal clients should send `origin: "user"` only for an actual explicit user action. Existing requests without the field remain accepted, but omission does not establish user authorization.
- MCP clients should tolerate missing `loginId` when communicating with older servers and use it to correlate attempts when present.
- Enterprise MCP deployments should use trusted, directly configured servers. Plugin-overlay enterprise authentication is disabled, and removing a shared enterprise grant can affect multiple servers.
- The terminal client stops forwarding its local `personality` override, including the previously forwarded `"none"` opt-out. This is a frontend behavior change; it does not remove personality fields from the app-server protocol. Code references: `config_request_overrides_from_config` and turn-start request construction in `codex-rs/tui/src/app_server_session.rs`.
- All examples describe behavior present in the source snapshot. The supplied release status does not establish publication or availability of a corresponding binary.


Generated with:
- tool: `harness-investigations@4f625f7-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.161.0.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
