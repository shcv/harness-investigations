# Changelog for version 0.162.0

## Release Status

> **Not yet released:** `rust-v0.162.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.161.0, this snapshot adds managed-worktree tools to the TUI, attachment-owner lookup for app-server clients, configurable transcript scrolling, and capability overrides for custom model providers. It also expands transcript copying, separates Fast and Ultra Fast controls, and fixes sandbox, configuration, connection, and conversation-history behavior.

The source tag `rust-v0.162.0` exists, but no published GitHub Release was found when synchronization ran. This changelog describes an intermediate development snapshot; it does not imply that official release notes, binaries, or installation assets were published.

## New Features


### Managed-worktree tools in the TUI

What: The agent can now create, inspect, and track managed Git worktrees through TUI-provided tools.

Usage: In a main conversation, explicitly request a worktree:

```text
Create a managed worktree from main for this task.
```

The model-facing tool calls are:

```json
{"name":"create_worktree","arguments":{"ref":"main","allowAsync":true}}
```

```json
{"name":"get_worktree_creation_status","arguments":{"operationId":"<returned-operation-id>"}}
```

```json
{"name":"list_worktrees","arguments":{}}
```

Details:

- Requires a local workspace, a trusted source project, attachment storage support, and the existing `worktrees` feature, which defaults to enabled.
- Creation returns an operation ID immediately. Poll its status before using the checkout.
- Without `ref`, creation uses the repository’s remote default branch.
- The current conversation keeps its existing working directory. Use the returned `workspaceRoot` explicitly; filesystem permissions still apply.
- Uncommitted changes are not copied.
- Ephemeral side conversations cannot retain worktree attachments.
- If registration fails after creation, the checkout is retained for recovery. Inspect it before requesting another checkout.

Code references:

- `ManagedWorktreeTools` in `codex-rs/tui/src/managed_worktree_tools.rs`
- `specs()` in `codex-rs/tui/src/managed_worktree_tool_specs.rs`
- `AppServerSession::start_dynamic_tool_mcp()` in `codex-rs/tui/src/app_server_session.rs`


### Shared task pinning in Command Center

What: Command Center can pin tasks into the shared pinned section.

Usage: Select a task in Command Center and press `p` to pin or unpin it. Customize the shortcut with:

```toml
[tui.keymap.agents]
toggle_pin = "p"
```

Details:

- Pinning uses the existing `thread/section/move` protocol and shared pinned section.
- Pinned tasks appear ahead of ordinary groups, in their shared section order.
- Search and status filters continue to apply.
- Failed pin operations display an error.

Code references:

- `App::toggle_agents_overview_pin()` in `codex-rs/tui/src/app/agents_overview_actions.rs`
- `AgentsOverviewView::visible_indices()` in `codex-rs/tui/src/app/agents_overview_grouping.rs`
- `TuiAgentsKeymap::toggle_pin` in `codex-rs/config/src/tui_keymap.rs`


### Transcript scroll speed and saved grouping preferences

What: New TUI configuration keys control mouse-wheel scrolling and preserve Command Center grouping across launches.

Usage:

```toml
[tui]
mouse_scroll_speed = 2.0
agents_overview_grouping = "model"
```

Details:

- `mouse_scroll_speed` defaults to `1.0`, based on one transcript row per wheel event.
- Positive fractional values slow scrolling; values above `1.0` speed it up.
- Zero, negative, and non-finite values are rejected.
- `agents_overview_grouping` accepts `"project"`, `"status"`, or `"model"`; the default is `"project"`.
- Changing grouping in Command Center saves the preference automatically. The grouping modes themselves already existed.

Code references:

- `Tui::mouse_scroll_speed`, `Tui::agents_overview_grouping`, and `AgentsOverviewGrouping` in `codex-rs/config/src/types.rs`
- `deserialize()` in `codex-rs/config/src/tui_mouse_scroll.rs`
- `App::persist_agents_overview_grouping()` in `codex-rs/tui/src/app/agents_overview_grouping.rs`


### Attachment-owner lookup

What: A new app-server method finds stored threads associated with an exact attachment identity.

Usage:

```json
{
  "id": 1,
  "method": "thread/attachmentOwner/list",
  "params": {
    "attachmentType": "worktree",
    "identityKey": "<worktree-identity>",
    "archived": false,
    "limit": 50
  }
}
```

Details:

- Returns `data` entries containing `threadId` and `archived`, plus `nextCursor`.
- Omit `archived`, or set it to `null`, to include both archived and non-archived threads.
- `false` selects non-archived threads; `true` selects archived threads.
- Continue pagination with the same attachment identity and archive filter.
- Includes owners without their own user-message previews.
- Searches only the server’s configured thread store. Results represent current membership and can change after lookup.

Code references:

- `ThreadAttachmentOwnerListParams`, `ThreadAttachmentOwner`, and `ThreadAttachmentOwnerListResponse` in `codex-rs/app-server-protocol/src/protocol/v2/thread_attachment.rs`
- `"thread/attachmentOwner/list"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `ThreadRequestProcessor::thread_attachment_owner_list()` in `codex-rs/app-server/src/request_processors/thread_attachments.rs`
- New schemas `codex-rs/app-server-protocol/schema/json/v2/ThreadAttachmentOwnerListParams.json` and `ThreadAttachmentOwnerListResponse.json`


### Custom provider capability overrides

What: Responses-compatible custom providers can declare whether they support live web access and remote context compaction.

Usage:

```toml
[model_providers.my_gateway.capabilities]
external_web_access = false
remote_compaction = "unsupported"
```

For a provider that implements the V2 compaction protocol:

```toml
[model_providers.my_gateway.capabilities]
remote_compaction = "v2"
```

Details:

- Unspecified capabilities retain their existing provider defaults.
- `"unsupported"` uses local compaction.
- `"v2"` enables provider compaction using `compaction_trigger` items.
- Model and turn settings can further restrict the declared capabilities.
- The app-server capability response also removes `namespaceTools`; see migration notes below.

Code references:

- `ModelProviderInfo::capabilities` in `codex-rs/model-provider-info/src/lib.rs`
- `ModelProviderCapabilities` and `RemoteCompactionSupport` in `codex-rs/model-provider-info/src/capabilities.rs`
- `ProviderCapabilities::from_config()` in `codex-rs/model-provider/src/capabilities.rs`
- `ModelProviderCapabilitiesReadResponse` in `codex-rs/app-server-protocol/src/protocol/v2/model.rs`


### Required skills for selected environments

What: Environment registrations can require specific skills to be available before model inference starts.

Usage: In `environments.toml`:

```toml
[[environments]]
id = "training"
url = "ws://127.0.0.1:4512"

[environments.skills]
required = ["computer-use"]
```

App-server clients can supply the same requirement dynamically:

```json
{
  "id": 2,
  "method": "environment/add",
  "params": {
    "environmentId": "training",
    "execServerUrl": "ws://127.0.0.1:4512",
    "skills": {
      "required": ["computer-use"]
    }
  }
}
```

Details:

- Requirements apply to the environment that declares them.
- Names must match enabled skills in that environment’s discovered catalog.
- A skill from another environment does not satisfy the requirement.
- Missing required skills produce an error before inference.
- This checks availability; it does not automatically install missing skills.

Code references:

- `ScopedSkillsConfig` in `codex-rs/config/src/skills_config.rs`
- `EnvironmentToml::skills` in `codex-rs/exec-server/src/environment_toml.rs`
- `EnvironmentAddParams::skills` and `EnvironmentSkillsParams` in `codex-rs/app-server-protocol/src/protocol/v2/environment.rs`
- `validate_required_skills()` in `codex-rs/ext/skills/src/required.rs`


### Browser-extension request-header requirements

What: Managed browser-use requirements can now carry request headers for extension clients.

Usage: In managed requirements:

```toml
[browser_use.extension]
request_headers = [
  { name = "x-company-token", value = "<managed-value>" }
]
```

Clients retrieve the requirements through:

```json
{"id":3,"method":"configRequirements/read","params":{}}
```

Details:

- The protocol exposes headers under `browserUse.extension.requestHeaders`.
- Each entry contains `name` and `value`.
- Debug formatting redacts header values.
- This change supplies configuration metadata to clients; the Rust diff does not establish that every browser-extension client applies it.

Code references:

- `BrowserUseExtensionRequirementsToml` and `RequestHeaderToml` in `codex-rs/config/src/browser_computer_use_requirements.rs`
- `BrowserUseExtensionRequirements` and `RequestHeader` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`
- `map_browser_use_requirements_to_api()` in `codex-rs/app-server/src/request_processors/config_processor.rs`
- Updated schema `codex-rs/app-server-protocol/schema/json/v2/ConfigRequirementsReadResponse.json`


### Legacy Windows sandbox uninstall command

What: A new command removes machine-wide resources belonging to the legacy Windows sandbox.

Usage: From an administrator terminal on Windows:

```powershell
codex sandbox uninstall
```

Details:

- Stop applications using the legacy sandbox and its provisioning service before running it.
- Removes legacy machine-wide accounts and network rules.
- Preserves Codex home, including sandbox directories and filesystem permissions.
- Other platforms return an unsupported-platform error.
- To run a sandboxed executable literally named `uninstall`, use the command separator:

```bash
codex sandbox -- uninstall --help
```

Code references:

- `SandboxSubcommand::Uninstall` in `codex-rs/cli/src/main.rs`
- `SandboxUninstallCommand` in `codex-rs/cli/src/sandbox_uninstall.rs`
- `clean_up_legacy_windows_sandbox()` in `codex-rs/windows-sandbox-rs/src/uninstall_windows.rs`


### Foreground remote-control flag

What: `codex remote-control` gains `--no-daemon` to explicitly keep the app-server in the foreground.

Usage:

```bash
codex remote-control --no-daemon
```

Details:

- Bare `codex remote-control` now uses the managed daemon when eligible.
- Foreground mode runs until Ctrl-C.
- `--json` retains the foreground path.
- Configuration overrides, workload-identity authentication, an explicit executor URL, disabled daemon auto-start, and certain platform conditions make the launch ineligible for daemon use.
- `--no-daemon` cannot be combined with explicit remote-control subcommands.

Code references:

- `RemoteControlCommand::no_daemon`, `run()`, and `daemon_eligible()` in `codex-rs/cli/src/remote_control_cmd.rs`

## Improvements


### Keyboard selection for transcript copying

In the fullscreen transcript, `/copy` now enters a selection mode that starts with the latest response and lets you navigate copy targets directly.

Usage:

```text
/copy
```

Use Up/Down or `k`/`j` to move between targets, Home/End to jump, Enter to copy, and Escape to exit. Targets include whole responses, user messages, code blocks, and blockquotes. Ctrl+Insert is also recognized as a copy shortcut.

Visible text selections copy literal text while retaining a rich HTML representation where supported. Transcript selection and copying also remain available while bottom-pane modals are open.

Code references:

- `ChatWidget::show_copy_picker()` in `codex-rs/tui/src/chatwidget/copy_picker.rs`
- `TranscriptView::begin_copy_mode()` and `handle_copy_mode_key()` in `codex-rs/tui/src/transcript_view/copy_mode.rs`
- `CopyFormat` in `codex-rs/tui/src/clipboard_copy.rs`
- `is_copy_key()` in `codex-rs/tui/src/text_selection.rs`


### Independent Fast and Ultra Fast controls

Fast and Ultra Fast already existed. This snapshot adds a separate, default-enabled `ultrafast_mode` feature so the two can be controlled independently.

Usage:

```toml
[features]
fast_mode = false
ultrafast_mode = true
```

Model catalogs still determine which tiers are available. `configRequirements/read` reports `supportsIndependentSpeedModes: true` so clients can distinguish the new behavior from older servers’ shared Fast-mode gate. Legacy enterprise `rbac-fast-mode` restrictions continue to disable both accelerated modes.

Code references:

- `Feature::UltrafastMode` and `Features::service_tier_enabled()` in `codex-rs/features/src/lib.rs`
- `ConfigRequirementsReadResponse::supports_independent_speed_modes` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`
- `CloudRequirementsTomlBundle::into_layers()` in `codex-rs/config/src/cloud_config_bundle.rs`


### Ultra Fast for supported Bedrock Astra models

Bundled Amazon Bedrock catalogs now advertise `ultrafast` for the supported Astra entries. Custom Bedrock catalogs retain their own service-tier definitions instead of having them cleared.

Usage: Select a supported Astra model and choose its Ultra Fast tier, or configure:

```toml
service_tier = "ultrafast"
```

The bundled Mantle catalog enables it for its Astra entry; Runtime enables it for `global.openai.gpt-6-astra` and `us.openai.gpt-6-astra`. The default remains the implicit tier.

Code references: `normalize_bundled_bedrock_catalog()` and `normalize_bedrock_catalog()` in `codex-rs/model-provider/src/amazon_bedrock/catalog.rs`; `static_runtime_model_catalog()` in `codex-rs/model-provider/src/amazon_bedrock/runtime_catalog.rs`.


### Turn lineage for delegated work

`turn/start` accepts optional `parentTurnId` and `rootTurnId`, and returned turns expose `rootTurnId`. Clients can attribute work across threads to the original initiating turn.

Usage:

```json
{
  "id": 4,
  "method": "turn/start",
  "params": {
    "threadId": "<child-thread-id>",
    "input": [{"type":"text","text":"Continue the delegated task."}],
    "parentTurnId": "<parent-turn-id>",
    "rootTurnId": "<parent-turn-root-id>"
  }
}
```

Leave the fields unset for direct user work. If `rootTurnId` is omitted, the new turn becomes its own root. These fields are ignored when the request adds input to an already-active turn. Attribution is retained across recovery, durable sleep, and compaction; older history may have no root ID.

Code references:

- `TurnStartParams` in `codex-rs/app-server-protocol/src/protocol/v2/turn.rs`
- `Turn::root_turn_id` in `codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs`
- `TurnAttribution` in `codex-rs/protocol/src/turn_input.rs`
- Updated schemas `codex-rs/app-server-protocol/schema/json/v2/TurnStartParams.json` and `TurnStartResponse.json`


### Partial assistant answers

The message-phase enum gains `partial_answer` for stable answer text that may be followed by further assistant output or tool calls.

Example:

```json
{"phase":"partial_answer"}
```

Thread occurrence search now includes both partial and final assistant answers. Agent workflows and realtime routing also recognize partial answers.

Code references: `MessagePhase::PartialAnswer` in `codex-rs/protocol/src/models.rs`; `ThreadSearchOccurrencesParams` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`; updated schema `codex-rs/app-server-protocol/schema/typescript/MessagePhase.ts`.


### More useful subagent activity records

Subagent-start activity now records the resolved model and reasoning effort. Command Center task details also place model and effort information near the top.

Clients can read the optional `model` and `reasoningEffort` fields on `subAgentActivity` items. Older records and other activity kinds may omit them.

Code references: `ThreadItem::SubAgentActivity` in `codex-rs/app-server-protocol/src/protocol/v2/item.rs`; `handle_spawn_agent()` in `codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs`.


### Archive an active conversation

`/archive` is now available while a turn is running.

Usage:

```text
/archive
```

The confirmation explains that accepting will stop the current turn and archive the session.

Code references: `SlashCommand::allowed_during_task()` in `codex-rs/tui/src/slash_command.rs`; archive dispatch in `codex-rs/tui/src/chatwidget/slash_dispatch.rs`.


### Writable file streaming in exec-server

The existing exec-server file-handle protocol now implements replacement opens and positional block writes.

Usage, after checking the executor’s `fileWriteStreaming` capability:

```json
{
  "id": 5,
  "method": "fs/open",
  "params": {
    "handleId": "output",
    "path": "file:///workspace/result.txt",
    "mode": "replace"
  }
}
```

```json
{
  "id": 6,
  "method": "fs/writeBlock",
  "params": {
    "handleId": "output",
    "offset": 0,
    "chunk": "aGVsbG8K"
  }
}
```

Close the handle with `fs/close`. Replacement mode creates or truncates the file; blocks must be nonempty and no larger than 1 MiB. Existing requests that omit `mode` remain read-only.

Code references: `FileSystemHandler::open()` and `write_block()` in `codex-rs/exec-server/src/server/file_system_handler.rs`; `FileHandleManager::write_block()` in `codex-rs/exec-server/src/file_handle.rs`; `FsOpenMode` in `codex-rs/exec-server-protocol/src/protocol.rs`.


### Bounded persisted tool output

Paginated history now limits persisted command output and oversized serialized MCP results to 64 KiB each. This reduces oversized history records, with truncation markers or previews indicating omitted content.

This applies to the durable history representation; it is not a new execution-output limit.

Code references: `PERSISTED_COMMAND_OUTPUT_MAX_BYTES`, `PERSISTED_MCP_RESULT_MAX_BYTES`, and `persisted_rollout_item()` in `codex-rs/rollout/src/policy.rs`; `truncate_mcp_tool_result()` in `codex-rs/utils/output-truncation/src/lib.rs`.


### Terminal presentation and Command Center polish

- Wrapped URLs remain clickable in banners, warnings, approval headers, questions, verification prompts, MCP elicitations, pending-input previews, hook details, status cards, and task previews.
- Markdown links to local files preserve their supplied labels.
- Stable Markdown tables can enter scrollback during streaming instead of waiting for the whole answer.
- Fullscreen composers are bounded and scrollable; confirmation dialogs are centered over their retained backdrop.
- Command Center task renaming uses the shared text editor, including configured editing bindings and Vim behavior.
- Hook-browser titles can display hook status messages.
- `codex doctor` reports the configured TUI mode.

Code references:

- `HyperlinkParagraph` in `codex-rs/tui/src/terminal_hyperlinks/paragraph.rs`
- Local-link rendering in `codex-rs/tui/src/markdown_render/local_links.rs`
- `TableHoldbackScanner` in `codex-rs/tui/src/streaming/table_holdback.rs`
- `App::draw_owned_transcript()` in `codex-rs/tui/src/app/owned_transcript.rs`
- `AgentsOverviewView::rename_key()` in `codex-rs/tui/src/app/agent_center/input.rs`
- Hook rendering in `codex-rs/tui/src/bottom_pane/hooks_browser_render.rs`
- `config_check()` in `codex-rs/cli/src/doctor.rs`


### Connection and diagnostics improvements

- Failed Responses streams and WebSocket error events honor valid `Retry-After` advice.
- Executor and remote-control reconnections use jittered backoff; relay connection attempts are bounded.
- Larger shell snapshots can be replayed from a file.
- Managed Unix app-servers raise their soft file-descriptor limit toward 4,096, within the inherited hard limit.
- Feedback uploads can bundle rollout attachments into `rollouts.tar.gz`, with individual-attachment fallback.

Code references:

- `parse_failed_response()` in `codex-rs/codex-api/src/sse/responses_error.rs`
- `map_wrapped_websocket_error_event()` in `codex-rs/codex-api/src/endpoint/responses_websocket.rs`
- Reconnection logic in `codex-rs/exec-server/src/remote/reconnect_backoff.rs` and `codex-rs/app-server-transport/src/transport/remote_control/websocket.rs`
- Snapshot replay in `codex-rs/exec-server/src/shell_snapshot.rs`
- `raise_nofile_limit()` in `codex-rs/app-server/src/managed_daemon.rs`
- `FeedbackSnapshot::feedback_attachments()` in `codex-rs/feedback/src/lib.rs`


### Structured TCP-tunnel diagnostics

The existing, hidden `tcp-tunnel` command gains opt-in JSON diagnostics on stderr for tooling and troubleshooting.

Usage:

```bash
codex tcp-tunnel \
  --proxy-url https://proxy.example.com \
  --proxy-origins-file approved-origins.txt \
  --target host.example.com:443 \
  --auth-token-stdin \
  --diagnostics-json
```

Supply the credential through the existing stdin control mechanism. Diagnostics use credential-safe phase and error categories; stdout retains the `LISTENING` readiness contract.

Code references: `Args::diagnostics_json` and `run()` in `codex-rs/tcp-tunnel/src/lib.rs`; `Diagnostics` in `codex-rs/tcp-tunnel/src/diagnostics.rs`.

## Bug Fixes

- Patches always preserve existing line endings. The old `apply_patch_preserve_line_endings` flag no longer controls the behavior. (`ApplyPatchOptions` in `codex-rs/apply-patch/src/lib.rs`; patch application in `codex-rs/apply-patch/src/file_update.rs`.)
- Linux sandbox startup works when multiple denied files require separate empty-file mounts. (`append_empty_file_bind_data_args()` in `codex-rs/linux-sandbox/src/bwrap.rs`.)
- Pre-sandbox executable lookup rejects sandbox-writable `bwrap` and `rg` candidates. Deny-glob expansion also ignores personal ripgrep configuration. (`find_pre_sandbox_executable_in_path()` in `codex-rs/sandboxing/src/bwrap.rs`; `ripgrep_files()` in `codex-rs/linux-sandbox/src/bwrap.rs`.)
- Windows 10 drive-letter paths work with no-follow filesystem operations through a volume-path fallback. (No-follow opening in `codex-rs/exec-server/src/no_follow/windows.rs`; fallback in `codex-rs/exec-server/src/no_follow/windows_volume_fallback.rs`.)
- Windows sandbox temporary-directory permissions use the child workload’s final `TEMP` and `TMP` values. (`resolve_workload_temp_paths()` in `codex-rs/windows-sandbox-rs/src/resolved_permissions.rs`.)
- Malformed Windows deny-read bookkeeping can be rebuilt while preserving unknown historical restrictions. (`sync_persistent_deny_read_acls()` in `codex-rs/windows-sandbox-rs/src/deny_read_state.rs`.)
- Explicit registered Windows sandbox setup can start a stopped provisioning service. (`start_windows_sandbox_service_for_setup()` in `codex-rs/windows-sandbox-rs/src/provisioning_client.rs`.)
- Remote MCP launches preserve Windows runtime and temporary-directory variables when explicit environment settings activate an allowlist. (`ExecutorStdioServerLauncher` in `codex-rs/rmcp-client/src/stdio_server_launcher.rs`.)
- Unknown TUI configuration keys are detected during strict validation, including `-c` overrides. (`unknown_tui_toml_value_path()` in `codex-rs/config/src/strict_config.rs`; `validate_cli_overrides_strictly()` in `codex-rs/config/src/loader/mod.rs`.)
- Failed configuration reloads preserve live TUI settings when starting or resuming conversations. (New-thread preparation in `codex-rs/tui/src/app/new_session.rs`; resume preparation in `codex-rs/tui/src/app/resume_config.rs`.)
- Fresh connected TUI conversations honor server model, reasoning-effort, and reasoning-summary defaults instead of unintentionally imposing local defaults. (`bootstrap_server_owned_start()` in `codex-rs/tui/src/app/startup_bootstrap.rs`; `StartupLaunchChoices` in `codex-rs/tui/src/app_server_session/startup_launch.rs`.)
- Permission shortcuts use the server’s permission catalog and managed restrictions. (Shortcut handling in `codex-rs/tui/src/chatwidget/permission_shortcuts.rs`.)
- Session-name lookup uses stable pagination and reports listing failures. (`lookup()` in `codex-rs/tui/src/named_session_lookup.rs`.)
- Transcript Find uses Enter to accept and Escape to cancel, preserves readable accepted results, and limits temporary expansion to the current match. (Find handling in `codex-rs/tui/src/transcript_view/search.rs` and `search_presentation.rs`.)
- Configured shortcuts take precedence over transcript navigation, and pager bindings are respected for transcript page keys. (`App::handle_owned_transcript_event()` in `codex-rs/tui/src/app/owned_transcript.rs`; navigation in `codex-rs/tui/src/transcript_view/input.rs`.)
- Windows Terminal’s explicitly mapped Shift+Enter sequence is decoded correctly. (Sequence decoding in `codex-rs/tui/src/tui/windows_key_sequence.rs`.)
- Unix suspension waits for `SIGCONT` before restoring terminal modes. (`suspend_process()` in `codex-rs/tui/src/tui/job_control.rs`.)
- Repeated image-paste key presses are suppressed in legacy terminals. (Paste state in `codex-rs/tui/src/chatwidget.rs`.)
- `/status` restores the account email after account updates. (`ChatWidget::on_account_email_loaded()` in `codex-rs/tui/src/chatwidget/settings.rs`.)
- MCP startup notifications are limited to threads owned by the TUI, and Command Center selection stays adjacent after task removal. (Ownership handling in `codex-rs/tui/src/app/app_server_thread_ownership.rs`; removal selection in `codex-rs/tui/src/app/agents_overview_selection.rs`.)
- Selected environments retain their own capability roots and skill identity, avoiding accidental reuse of another thread’s selections. (`TurnEnvironmentSelection::new()` in `codex-rs/protocol/src/environment.rs`; `EnvironmentCapabilityRoots` in `codex-rs/protocol/src/capabilities.rs`.)
- Queued agent mail survives session eviction, and invalidated wakeups cannot start a new turn. (`InputQueue::with_controller()` and `read_mailbox()` in `codex-rs/core/src/session/input_queue.rs`; mailbox handling in `codex-rs/core/src/agent/control/mailbox.rs`.)
- Compaction replacement history preserves full context, including tool declarations and base instructions where applicable. (Replacement-history construction in `codex-rs/core/src/compact.rs` and `codex-rs/core/src/compact_remote_v2.rs`.)
- Realtime conversations persist their final transcript tail before closure without starting another inference request. (`record()` in `codex-rs/core/src/realtime_conversation/transcript_tail.rs`.)
- Ephemeral-thread intent reaches image attachment uploads. (`prepare_response_items()` in `codex-rs/core/src/image_preparation.rs`; `UploadRequest::ephemeral` in `codex-rs/attachment-store/src/lib.rs`.)
- Exec-server limits account for in-flight file opens as well as retained handles. (`FileHandleManager::open()` in `codex-rs/exec-server/src/file_handle.rs`.)
- Managed daemon update failures include a bounded installer stderr tail. Windows publication retries transient file locks and can fall back to `mklink` when junction updates are denied. (`run_installer_script()` in `codex-rs/app-server-daemon/src/update_loop.rs`; `retarget_junction()` in `codex-rs/app-server-daemon/src/prepare_install_windows.rs`.)
- Daemon auto-start is skipped when Codex home is on a Windows-mounted WSL filesystem. (`uses_wsl_drvfs()` in `codex-rs/tui/src/daemon_startup.rs`.)
- Legacy MCP tool listing follows pagination, so later pages are no longer missed. (`list_tools_for_client_uncached()` in `codex-rs/codex-mcp/src/rmcp_client.rs`.)
- MCP OAuth compatibility recognizes Mercado Pago’s specific cross-origin endpoint arrangement. (`validate_authorization_server_endpoints()` in `codex-rs/rmcp-client/src/oauth/issuer_binding.rs`.)

## In Development


### Ranked discovery and settlement streaming in Code Mode [Experimental]

What: JavaScript Code Mode gains ranked discovery of deferred tools and helpers for processing concurrent promises as they settle.

Status: Code Mode remains opt-in. Ranked discovery additionally requires the new, default-off `code_mode_tool_search` flag.

Usage:

```toml
[features]
code_mode = true
code_mode_tool_search = true
```

Within Code Mode:

```javascript
text(await tools.tool_search({ query: "find project files", limit: 8 }));
```

```javascript
for await (const result of as_settled([
  Promise.resolve("first"),
  Promise.resolve("second")
])) {
  text(result);
}
```

Details:

- Ranked search uses BM25 and returns callable names with TypeScript declarations.
- Inspect unfamiliar declarations before invoking a discovered tool in a later execution.
- `as_settled()` yields fulfilled or rejected results in settlement order.
- `stream_settled(promises, callback)` processes the same results through an awaited callback.
- Maps preserve caller-provided keys as result indexes.
- Settlement helpers are installed by the Code Mode runtime and do not require the search flag.

Code references:

- `DeferredToolDiscovery` and `TOOL_SEARCH_GUIDANCE` in `codex-rs/code-mode-protocol/src/description.rs`
- `ToolSearchHandler::search_code_mode()` in `codex-rs/core/src/tools/handlers/tool_search.rs`
- `as_settled()` and `stream_settled()` in `codex-rs/code-mode-runtime/src/runtime/settled.js`


### Strict third-party tool deferral [Experimental]

What: Code Mode Only can force eligible MCP, app, and client-defined tools to remain deferred behind JavaScript execution.

Status: Runtime-gated by the new, default-off `code_mode_only_strict_3p_tools` flag; effective tool mode must be Code Mode Only.

Usage:

```toml
[features]
code_mode = true
code_mode_only = true
code_mode_only_strict_3p_tools = true
```

Details:

- Overrides conflicting loading, exposure, and namespace-skip settings for eligible third-party tools.
- Keeps their nested execution routes available.
- Does not grant access to tools rejected by policy.

Code references: `code_mode_only_strict_3p_tools()` and `enforce_strict_3p_tools()` in `codex-rs/core/src/tools/spec_plan.rs`; `Feature::CodeModeOnlyStrictThirdPartyTools` in `codex-rs/features/src/lib.rs`.


### Incremental tool catalogs [Experimental]

What: Responses Lite can receive tool-catalog changes through conversation context.

Status: Runtime-gated by the new, default-off `incremental_tools` flag.

Usage:

```toml
[features]
incremental_tools = true
```

Details:

- Tracks top-level declarations and records catalog updates in history.
- Distinguishes namespace removals from individual tool removals.
- Preserves declaration mode across resumed context windows.
- Applies to the supporting Responses Lite path.

Code references: `Feature::IncrementalTools` in `codex-rs/features/src/lib.rs`; tool world state in `codex-rs/core/src/context/world_state/top_level_tools.rs`; `ModelClientState` in `codex-rs/core/src/client.rs`; `ResponseItem::AdditionalTools` in `codex-rs/protocol/src/models.rs`.


### Stable environment-backed tool exposure [Experimental]

What: Environment-backed tools can remain advertised before their executor is ready.

Status: Runtime-gated by the new, default-off `stable_environment_tools` flag.

Usage:

```toml
[features]
stable_environment_tools = true
```

Details:

- Stabilizes tool declarations and shell parameters across executor readiness changes.
- Actual execution still requires a usable environment and applicable permissions.

Code references: `Feature::StableEnvironmentTools` in `codex-rs/features/src/lib.rs`; tool construction in `codex-rs/core/src/tools/spec_plan.rs`; environment resolution in `codex-rs/core/src/tools/handlers/mod.rs`.


### Dynamic-tool inheritance for V2 subagents [Experimental]

What: Fresh V2 subagents can inherit client-defined dynamic tools.

Status: Runtime-gated by the new, default-off `multi_agent_v2_dynamic_tools` flag and requires V2 multi-agent mode.

Usage:

```toml
[features]
multi_agent_v2 = true
multi_agent_v2_dynamic_tools = true
```

Details:

- Extends fresh-child startup with the parent’s dynamic-tool definitions.
- Inherited tools remain subject to normal execution policy.

Code references: `Feature::MultiAgentV2DynamicTools` in `codex-rs/features/src/lib.rs`; child startup in `codex-rs/core/src/agent/control/spawn.rs`.


### Daybreak eligibility for API-key accounts [Experimental]

What: The existing Daybreak TUI controls now recognize eligible API-key accounts as well as ChatGPT accounts.

Status: CLI selection and controls require the existing, default-off `cli_daybreak` feature.

Usage:

```toml
[features]
cli_daybreak = true
```

Then use:

```text
/daybreak
```

Details:

- Requires the OpenAI provider.
- The account, model catalog, and server must support the program.
- Enabling the local flag does not establish account entitlement.

Code references: `ChatWidget::daybreak_account_eligible()` and `daybreak_turn_eligible()` in `codex-rs/tui/src/chatwidget/settings.rs`; Daybreak dispatch in `codex-rs/tui/src/chatwidget/slash_dispatch.rs`.


### Guardian transcript format and optional comparison [Experimental]

What: Guardian can use structured JSON transcripts and optionally compare its asynchronous classifier with a separate Decisions request.

Status: Guardian V2 remains opt-in. Decisions comparison has its own new, default-off flag.

Usage:

```toml
[features.guardianv2]
enabled = true
transcript_mode = "json"
```

To enable comparison:

```toml
[features]
guardianv2_decisions_comparison = true
```

Details:

- Transcript mode accepts `"line"` or `"json"`; `"line"` remains the default.
- Comparison measures results without changing approval decisions.
- It uses `CODEX_GUARDIAN_DECISIONS_API_KEY`, with an `OPENAI_API_KEY` fallback only for the default OpenAI provider without a custom base URL.
- Related fixes preserve user restrictions and trusted-tool context, recover reviews from parent checkpoints, and prevent later scores from releasing earlier unrelated reviews.

Code references:

- `GuardianV2ConfigToml::transcript_mode` in `codex-rs/features/src/feature_configs.rs`
- `TranscriptFormat` in `codex-rs/protocol/src/guardian_transcript.rs`
- `decisions_api_key()` in `codex-rs/ext/guardian-v2/src/async_scorer/startup.rs`
- Review recovery in `codex-rs/core/src/guardian/review_session_setup.rs`
- Approval reuse in `codex-rs/ext/guardian-v2/src/async_scorer/approval.rs`


### Native cloud-thread gRPC client [In Development]

What: A new Rust client provides native gRPC operations to resume an existing cloud thread and attach to live events.

Status: Source-level client infrastructure with a standalone example. Public production ingress and package publication are not established by this change.

Usage: From a checkout of this tag’s `codex-rs` directory, with caller-supplied credentials and an authorized endpoint:

```bash
cargo run -p codex-cloud-client --example attach -- \
  "$CODEX_CLOUD_GRPC_ENDPOINT" "$CODEX_CLOUD_THREAD_ID"
```

The example reads `CODEX_CLOUD_ACCESS_TOKEN` and `CODEX_CLOUD_ACCOUNT_ID`.

Details:

- `Client::resume()` supports admission-versus-readiness behavior through `ResumeRequest::wait`.
- `Client::attach()` yields live notifications and server requests as opaque protobuf payloads.
- Requires a trusted native gRPC origin, rather than the HTTP `/grpc` gateway.
- Does not yet provide history replay, approval replies, automatic reconnect, or fully typed event payloads.

Code references: `Client::resume()` and `Client::attach()` in `codex-rs/cloud-client/src/lib.rs`; `Credentials`, `ResumeRequest`, and `Event` in `codex-rs/cloud-client/src/types.rs`.

## Notes

- V2 subagent forks no longer support partial parent-history inheritance. Use `fork_turns: "all"` or `"none"`. Legacy positive integer strings are accepted but now inherit full history. (`SpawnAgentArgs::fork_mode()` in `codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs`.)
- Clients calling `modelProvider/capabilities/read` must stop requiring `namespaceTools`; that response field was removed. Tool namespace exposure no longer uses the provider capability gate. (`ModelProviderCapabilitiesReadResponse` in `codex-rs/app-server-protocol/src/protocol/v2/model.rs`; tool construction in `codex-rs/core/src/tools/spec_plan.rs`.)
- Message-phase consumers must accept `partial_answer`. Treat it as answer content that can be followed by more output, rather than a turn-completion signal. (`MessagePhase` in `codex-rs/protocol/src/models.rs`.)
- Legacy command-event and rollout consumers should use `aggregated_output`; redundant `stdout`, `stderr`, and `formatted_output` fields were removed from the consolidated execution records. (`ExecCommandEndEvent` in `codex-rs/protocol/src/protocol.rs`; `CommandExecutionItem` in `codex-rs/protocol/src/items.rs`.)
- Skill paths can now represent executor-backed locations. Clients should not assume every skill path is a host-local absolute filesystem path. (`SkillMetadata::path` and `SkillSummary::path` in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`.)
- The obsolete Figma-specific MCP OAuth endpoint exception was removed as the Mercado Pago exception was introduced. Integrations relying on the old exception should recheck their issuer and endpoint configuration. (`validate_authorization_server_endpoints()` in `codex-rs/rmcp-client/src/oauth/issuer_binding.rs`.)
- Remove reliance on `apply_patch_preserve_line_endings`; preservation is unconditional in this snapshot. (`Feature::ApplyPatchPreserveLineEndings` in `codex-rs/features/src/lib.rs`.)


Generated with:
- tool: `harness-investigations@01a4036-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.162.0.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
