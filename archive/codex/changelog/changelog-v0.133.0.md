# Changelog for version 0.133.0

## Summary
Codex 0.133.0 promotes Goals from experimental to default-on, makes remote control more useful as both a foreground and daemon workflow, and expands the app-server protocol around permission profiles, plugin discovery, hooks, and thread settings. The release also includes several TUI, app-server, plugin, AGENTS.md, and runtime fixes that reduce stale state, wrong working directories, and compatibility failures.

### Goals Are Enabled by Default
What: Goals are no longer experimental and are enabled by default, so persistent thread goals can be used without flipping a feature flag.

Usage:
```json
{"method": "thread/goal/set", "params": {"threadId": "thr_123", "objective": "Finish the migration", "status": "active", "tokenBudget": 200000}}
```

Details:
- `Feature::Goals` moved from `Stage::Experimental` / `default_enabled: false` to `Stage::Stable` / `default_enabled: true`.
- The existing goal RPCs `thread/goal/set`, `thread/goal/get`, and `thread/goal/clear` are no longer marked experimental.
- Goal state now has dedicated storage in `state/goals_migrations/0001_thread_goals.sql`, with separate columns for objective, status, token budget, tokens used, and time used.
- Goal progress accounting tracks active and stopped goal states, including budget-limited and usage-limited status transitions.

Code references:
- `Feature::Goals` in `codex-rs/features/src/lib.rs`
- `ThreadGoalSet`, `ThreadGoalGet`, `ThreadGoalClear` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `GoalStore` / `GoalAccountingMode` in `codex-rs/state/src/runtime/goals.rs`
- New migration `codex-rs/state/goals_migrations/0001_thread_goals.sql`


### Remote Control Can Run in Foreground or Daemon Mode
What: `codex remote-control` now starts a foreground app-server, waits until remote control is ready, prints machine status, and stays alive until interrupted; explicit daemon `start` and `stop` subcommands remain available.

Usage:
```bash
codex remote-control
codex remote-control --json
codex remote-control start
codex remote-control stop
```

Details:
- With no subcommand, Codex starts an app-server in the foreground using a private Unix socket and prints “Press Ctrl-C to stop.”
- `codex remote-control start` starts or reuses the app-server daemon and waits for `remoteControl/enable` readiness before reporting status.
- JSON output includes `mode`, `status`, `serverName`, `environmentId`, and `timedOut`; daemon output also includes managed app-server identity.
- Daemon lifecycle output now reports `managedCodexPath` and `managedCodexVersion`.

Code references:
- `RemoteControlCommand` and `run_foreground_remote_control` in `codex-rs/cli/src/remote_control_cmd.rs`
- `RemoteControlReadyOutput` and `ensure_remote_control_ready` in `codex-rs/app-server-daemon/src/lib.rs`
- `enable_remote_control_with_timeout` in `codex-rs/app-server-daemon/src/remote_control_client.rs`


### Permission Profiles Are More Discoverable and Enforceable
What: Clients can list available permission profiles, profile inheritance is exposed, managed `requirements.toml` can define allowed profiles, and Windows sandbox execution now consumes resolved permission profiles.

Usage:
```json
{"method": "permissionProfile/list", "params": {"cwd": "/repo", "limit": 50}}
```

Details:
- New `permissionProfile/list` returns paginated `PermissionProfileSummary` entries with `id`, optional `description`, and `nextCursor`.
- `ActivePermissionProfile.extends` now reports the selected profile’s parent from `extends` when present.
- Managed requirements can define profiles under `[permissions.<id>]` and restrict them with `allowed_permissions`.
- `permissions.filesystem` remains reserved for filesystem requirements and now errors if used as a profile table.
- The app-server protocol now uses `deny` as the filesystem access mode name instead of the previous `none` spelling.
- Windows sandboxing now resolves managed permission profiles through `ResolvedWindowsSandboxPermissions`.

Code references:
- `PermissionProfileListParams`, `PermissionProfileSummary`, `PermissionProfileListResponse` in `codex-rs/app-server-protocol/src/protocol/v2/permissions.rs`
- `PermissionProfileList => "permissionProfile/list"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `allowed_permissions` and `PermissionsRequirementsToml.profiles` in `codex-rs/config/src/config_requirements.rs`
- `ResolvedWindowsSandboxPermissions` in `codex-rs/windows-sandbox-rs/src/resolved_permissions.rs`


### Plugin Discovery Shows More Useful Marketplace Information
What: Plugin listing and marketplace listing now show clearer marketplace roots, plugin paths, installed versions, and marketplace kinds, including a new vertical remote collection.

Usage:
```bash
codex plugin list
codex plugin marketplace list
```

Details:
- `codex plugin list` now prints a table per marketplace with `PLUGIN`, `STATUS`, `VERSION`, and `PATH`.
- `codex plugin marketplace list` now lists every marketplace Codex is considering, not just configured user entries.
- `PluginListMarketplaceKind` gained `vertical`, allowing clients to request the OpenAI curated remote collection.
- Remote plugin marketplace naming changed from `chatgpt-global` / `ChatGPT Plugins` to `openai-curated-remote` / `OpenAI Curated Remote`.
- Installed plugin records now retain `installed_version`, so list/read responses can distinguish marketplace version from the active installed version.
- The model now has a `list_available_plugins_to_install` tool, and `request_plugin_install` now expects IDs returned by that discovery tool.

Code references:
- `run_plugin_list` in `codex-rs/cli/src/plugin_cmd.rs`
- `run_list` in `codex-rs/cli/src/marketplace_cmd.rs`
- `PluginListMarketplaceKind::Vertical` in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`
- `fetch_openai_curated_remote_collection_marketplace` in `codex-rs/core-plugins/src/remote.rs`
- `ListAvailablePluginsToInstallHandler` in `codex-rs/core/src/tools/handlers/list_available_plugins_to_install.rs`


### Hooks and Extensions See More Lifecycle Context
What: Hooks can now target subagent start/stop events, and extension tools receive richer turn/tool lifecycle metadata.

Usage:
```toml
[hooks.SubagentStart]
# matcher groups as in other hook sections

[hooks.SubagentStop]
# matcher groups as in other hook sections
```

Details:
- `HookEventName` now includes `SubagentStart` and `SubagentStop`.
- Managed hook requirements now include `SubagentStart` and `SubagentStop` arrays.
- Thread-spawned subagents run `SubagentStart` hooks at startup and `SubagentStop` hooks before ending.
- Extension tool calls now include `turn_id` and `truncation_policy`.
- Tool lifecycle contributors receive `on_tool_start` and finish/abort notifications through the new lifecycle path.

Code references:
- `HookEventsToml.subagent_start` / `subagent_stop` in `codex-rs/config/src/hook_config.rs`
- `run_pending_session_start_hooks` and `run_turn_stop_hooks` in `codex-rs/core/src/hook_runtime.rs`
- `ToolStartInput` / `ToolFinishInput` use in `codex-rs/core/src/tools/lifecycle.rs`
- `ExtensionToolAdapter::to_extension_call` in `codex-rs/core/src/tools/handlers/extension_tools.rs`


### App-Server and Schema Documentation Expanded
What: The generated app-server schemas now include previously missing stable goal schemas, permission-profile list schemas, thread settings notifications, and managed requirement fields.

Usage:
```json
{"method": "configRequirements/read", "params": null}
```

Details:
- New generated schemas include `PermissionProfileListParams.json`, `PermissionProfileListResponse.json`, `ThreadGoal*Params.json`, `ThreadGoal*Response.json`, and `ThreadSettingsUpdatedNotification.json`.
- `ConfigRequirements` now exposes `allowedPermissions` and `computerUse`.
- `ComputerUseRequirements` currently exposes `allowLockedComputerUse`.

Code references:
- `codex-rs/app-server-protocol/schema/json/v2/PermissionProfileListParams.json`
- `codex-rs/app-server-protocol/schema/json/v2/ThreadGoalSetResponse.json`
- `ConfigRequirements` and `ComputerUseRequirements` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`


### Experimental Thread Settings Update API
What: App-server clients can experimentally update a running thread’s settings for subsequent turns.

Usage:
```json
{"method": "thread/settings/update", "params": {"threadId": "thr_123", "model": "gpt-5.4", "serviceTier": "priority"}}
```

Details:
- The new experimental `thread/settings/update` method can update `cwd`, approval policy, approvals reviewer, sandbox policy, permission profile, model, service tier, reasoning effort, reasoning summary, collaboration mode, and personality.
- The server emits experimental `thread/settings/updated` notifications with the resolved `ThreadSettings`.
- The TUI syncs settings through this method when supported and gracefully downgrades when an older app-server rejects it.

Code references:
- `ThreadSettingsUpdateParams`, `ThreadSettingsUpdateResponse`, `ThreadSettingsUpdatedNotification` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- `ThreadSettingsUpdate => "thread/settings/update"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `update_thread_settings` path in `codex-rs/app-server/src/request_processors/turn_processor.rs`


### Auto-Compaction Can Count Only Post-Prefix Growth
What: A new config key controls whether auto-compaction thresholds count the whole active context or only growth after the carried prefix.

Usage:
```toml
model_auto_compact_token_limit = 120000
model_auto_compact_token_limit_scope = "body_after_prefix"
```

Details:
- `total` remains the default behavior.
- `body_after_prefix` subtracts the carried compaction-window prefix from later active-context usage, which helps avoid repeated compaction driven by the same retained prefix.

Code references:
- `model_auto_compact_token_limit_scope` in `codex-rs/config/src/config_toml.rs`
- `AutoCompactTokenLimitScope` in `codex-rs/protocol/src/config_types.rs`
- `auto_compact_window` handling in `codex-rs/core/src/state/auto_compact_window.rs`


### Exec-Server Remote Registration Uses Environment IDs
What: Remote exec-server registration has been renamed from executor terminology to environment terminology.

Usage:
```bash
codex exec-server --remote https://example.invalid --environment-id env_123 --name "Build machine"
```

Details:
- `--executor-id` was replaced with `--environment-id`.
- The internal API changed from `RemoteExecutorConfig` / `run_remote_executor` to `RemoteEnvironmentConfig` / `run_remote_environment`.
- `codex exec-server --strict-config` and root-level `codex --strict-config exec-server` are now supported, so unattended exec-server startup can reject unknown config fields.

Code references:
- `ExecServerCommand` in `codex-rs/cli/src/main.rs`
- `RemoteEnvironmentConfig` in `codex-rs/exec-server/src/remote.rs`


### Network Proxy MITM Hooks
What: The network proxy now has configuration plumbing for host-specific HTTPS MITM hooks that can match request details and strip or inject request headers.

Usage:
```toml
[permissions.workspace.network.mitm.hooks.github_write]
host = "api.github.com"
methods = ["POST", "PUT"]
path_prefixes = ["/repos/openai/"]
action = ["strip_auth"]

[permissions.workspace.network.mitm.actions.strip_auth]
strip_request_headers = ["authorization"]
```

Details:
- MITM hooks are configured under permission-profile network settings.
- Hooks can match host, methods, path prefixes, query values, headers, and reserved future body matchers.
- Actions can strip request headers or inject headers from an environment variable or secret file.
- HTTPS MITM is enabled automatically when network mode is `limited` or MITM hooks are present.

Code references:
- `MitmHookConfig`, `MitmHookMatchConfig`, `MitmHookActionsConfig` in `codex-rs/network-proxy/src/mitm_hook.rs`
- `NetworkProxySettings.mitm_hooks` in `codex-rs/network-proxy/src/config.rs`
- MITM examples in `codex-rs/network-proxy/README.md`


### MCP Tool Items Now Carry Plugin IDs
What: Thread item notifications for MCP tool calls can now include the plugin that supplied the tool.

Usage:
```json
{"method": "item/started", "params": {"item": {"type": "mcpToolCall", "pluginId": "linear@openai-curated"}}}
```

Details:
- `ThreadItem::McpToolCall` gained `plugin_id`.
- This helps clients display whether a tool call came from a plugin-backed MCP server instead of a manually configured MCP server.

Code references:
- `ThreadItem::McpToolCall.plugin_id` in `codex-rs/app-server-protocol/src/protocol/v2/item.rs`
- Generated schema updates in `codex-rs/app-server-protocol/schema/json/v2/ItemStartedNotification.json` and `ItemCompletedNotification.json`


### Function Call Outputs Can Include Encrypted Content Items
What: Function-call output content now preserves encrypted content entries in truncation paths.

Usage:
```json
{"type": "encrypted_content", "encrypted_content": "..."}
```

Details:
- `FunctionCallOutputContentItem::EncryptedContent` is now handled by output truncation instead of being ignored as plain input text only.
- This is mostly relevant to protocol clients and hosted/runtime integrations that round-trip encrypted tool output.

Code references:
- `FunctionCallOutputContentItem::EncryptedContent` handling in `codex-rs/utils/output-truncation/src/lib.rs`
- Schema updates in `codex-rs/app-server-protocol/schema/typescript/FunctionCallOutputContentItem.ts`


### Side Slash Command Alias
What: The side-panel slash command now has a shorter alias.

Usage:
```text
/btw
```

Details:
- `/btw` was added as an alias for the side slash command, making side comments quicker to enter from the TUI composer.

Code references:
- `SlashCommand` definitions in `codex-rs/tui/src/slash_command.rs`
- Slash popup snapshot updates in `codex-rs/tui/src/bottom_pane/snapshots/`


## Bug Fixes

- Fixed TUI startup state when app-server startup completes late or out of order, including queued startup input and stale startup thread cleanup (`handle_startup_thread_started` in `codex-rs/tui/src/app/session_lifecycle.rs`).
- Fixed resume/fork working-directory selection so local app-server socket reuse is not treated like a remote workspace (`uses_remote_workspace` handling in `codex-rs/tui/src/app/session_lifecycle.rs`).
- Fixed plan-mode freeform questions so Shift+Enter inserts a newline instead of submitting unless it matches the configured composer submit binding (`RequestUserInputOverlay` in `codex-rs/tui/src/bottom_pane/request_user_input/mod.rs`).
- Preserved raw code-mode exec output unless a tool call explicitly asks for `max_output_tokens` (`ExecCommandHandler` in `codex-rs/core/src/tools/handlers/unified_exec/exec_command.rs`).
- Removed stale background terminal polling after command exit by tightening background request lifecycle handling (`codex-rs/tui/src/app/background_requests.rs`).
- Routed global AGENTS.md reads through the local filesystem path and surfaced invalid UTF-8 as warnings instead of silently dropping instructions (`codex-rs/core/src/project_doc.rs` and related config/instruction loading paths).
- Serialized Unix app-server daemon startup and added better app-server-not-ready context, including managed app-server path/version and stderr tail (`Daemon::wait_until_ready` in `codex-rs/app-server-daemon/src/lib.rs`).
- Fixed plugin upgrade handling so version upgrades remain additive rather than losing existing plugin state (`codex-rs/core-plugins/src/manager.rs` and store upgrade paths).
- Fixed realtime v1 websocket compatibility in the app-server transport path (`codex-rs/app-server-transport/src/transport/`).
- Fixed Windows sandbox permission-profile enforcement by resolving managed profiles before setup/spawn and rejecting unsupported full-disk write profiles (`ResolvedWindowsSandboxPermissions` in `codex-rs/windows-sandbox-rs/src/resolved_permissions.rs`).


### Thread Settings Update [Experimental]
What: Live thread-setting changes are implemented but the protocol method and notification are explicitly experimental.

Status: Runtime-gated by app-server experimental API capability for `thread/settings/update` and `thread/settings/updated`.

Details:
- Clients should be prepared for older app-servers to reject the method.
- TUI support already treats method-not-found and experimental-capability errors as a capability downgrade.

Code references:
- `#[experimental("thread/settings/update")]` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `thread_settings_update_supported` in `codex-rs/tui/src/app_server_session.rs`


### Network Proxy Body Matching [In Development]
What: MITM hook body matching has config shape but is not enabled yet.

Status: Stubbed. `match.body` returns an error saying it is reserved for a future release.

Details:
- Header, query, method, and path matching are implemented.
- Body matching is explicitly rejected during validation.

Code references:
- `MitmHookBodyConfig` and validation error in `codex-rs/network-proxy/src/mitm_hook.rs`


## Notes
- Protocol clients that previously treated goal methods as experimental can now expose `thread/goal/set`, `thread/goal/get`, `thread/goal/clear`, `thread/goal/updated`, and `thread/goal/cleared` as stable/default surfaces.
- Protocol clients should update filesystem permission displays from `none` to `deny`.
- Exec-server wrappers using `--executor-id` should migrate to `--environment-id`.
- Plugin clients should expect the remote global marketplace key `openai-curated-remote` instead of `chatgpt-global`.
- `thread/start.permissions` and `thread/resume.permissions` are now plain profile ID strings; legacy object-shaped permission selections were removed from the v2 protocol types.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.133.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.133.0.md`
