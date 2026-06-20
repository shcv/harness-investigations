# Changelog for version 0.137.0

## Summary
Codex 0.137.0 expands TUI customization, enterprise account visibility, plugin automation, remote-control management, hosted tools, and multi-agent v2 behavior. The most important protocol changes are experimental remote-control RPCs, monthly spend-control fields on rate-limit snapshots, environment-scoped permission approvals, and `parentThreadId` on thread objects.

### TUI keybinding, search-menu paste, and reasoning status improvements
What: The TUI now accepts function-key bindings through F24, lets users paste into searchable selection menus, and adds reasoning-only status/title items.

Usage:
```toml
[tui.keymap.chat]
interrupt_turn = "f13"

tui_status_line = ["reasoning", "current-dir"]
tui_terminal_title = ["project", "reasoning"]
```

Details:
- Function-key parsing now accepts `f1` through `f24`; v0.136.0 only accepted F1-F12.
- Searchable list views normalize pasted text into the search query, so branch/file/plugin picker searches can be pasted instead of typed.
- Status-line and terminal-title configuration now accept `reasoning` in addition to the existing `model-with-reasoning`.

Code references:
- `MAX_FUNCTION_KEY` handling in `codex-rs/config/src/tui_keymap.rs`
- `ListSelectionView::handle_paste` in `codex-rs/tui/src/bottom_pane/list_selection_view.rs`
- `normalize_pasted_search_query` in `codex-rs/tui/src/clipboard_paste.rs`
- `StatusLineItem::Reasoning` in `codex-rs/tui/src/bottom_pane/status_line_setup.rs`
- `TerminalTitleItem::Reasoning` in `codex-rs/tui/src/bottom_pane/title_setup.rs`


### Enterprise monthly credit limits and cloud-managed config bundles
What: Enterprise and EDU account flows can now consume cloud-managed config bundles, and account status can show monthly credit-limit details.

Usage:
```text
/status
```

Details:
- Rate-limit snapshots gained an optional `individualLimit` object with `limit`, `used`, `remainingPercent`, and `resetsAt`.
- The TUI renders this as `Monthly credit limit` with remaining percentage, reset time, and usage details.
- Config layer reporting now includes an `enterpriseManaged` source for cloud-delivered config fragments.
- Hook provenance now includes `cloudManagedConfig`, so clients can distinguish cloud-managed policy hooks from local or legacy managed config hooks.

Code references:
- `SpendControlLimitSnapshot` in `codex-rs/app-server-protocol/src/protocol/v2/account.rs`
- `RateLimitSnapshot::individual_limit` in `codex-rs/protocol/src/protocol.rs`
- `SpendControlLimitSnapshotDisplay` and `Monthly credit limit` rendering in `codex-rs/tui/src/status/rate_limits.rs`
- `ConfigLayerSource::EnterpriseManaged` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`
- `CloudManagedConfig` in `codex-rs/app-server-protocol/src/protocol/v2/hook.rs`
- Cloud bundle implementation in `codex-rs/cloud-config/src/service.rs`


### Remote-control pairing and controller management [Experimental]
What: App-server clients can start remote-control pairing and manage controller-device grants through new experimental v2 RPCs.

Usage:
```json
{"method":"remoteControl/pairing/start","params":{"manualCode":true}}
```

```json
{"method":"remoteControl/client/list","params":{"environmentId":"env_123","limit":25,"order":"desc"}}
```

```json
{"method":"remoteControl/client/revoke","params":{"environmentId":"env_123","clientId":"client_456"}}
```

Details:
- `remoteControl/pairing/start` returns `pairingCode`, optional `manualPairingCode`, `environmentId`, and `expiresAt`.
- `remoteControl/client/list` returns controller metadata such as display name, platform, app version, and `lastSeenAt`, plus `nextCursor`.
- `remoteControl/client/revoke` revokes one controller grant for an environment.
- These methods are marked experimental in the protocol export path.

Code references:
- `RemoteControlPairingStartParams` and `RemoteControlPairingStartResponse` in `codex-rs/app-server-protocol/src/protocol/v2/remote_control.rs`
- `RemoteControlClientsListParams`, `RemoteControlClient`, and `RemoteControlClientsRevokeParams` in `codex-rs/app-server-protocol/src/protocol/v2/remote_control.rs`
- RPC strings `"remoteControl/pairing/start"`, `"remoteControl/client/list"`, and `"remoteControl/client/revoke"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- App-server docs in `codex-rs/app-server/README.md`
- Transport implementation in `codex-rs/app-server-transport/src/transport/remote_control/clients.rs` and `codex-rs/app-server-transport/src/transport/remote_control/enroll.rs`


### Plugin list JSON output and catalog caching
What: `codex plugin list` can now emit machine-readable JSON, optionally including available but uninstalled marketplace plugins.

Usage:
```bash
codex plugin list --json
codex plugin list --available --json
codex plugin list --marketplace debug --available --json
```

Details:
- JSON output has top-level `installed` and `available` arrays.
- Entries include `pluginId`, `name`, `marketplaceName`, `version`, install/enabled state, source metadata, install policy, and auth policy.
- `--available` requires `--json`, keeping the existing table output focused on installed plugin state.
- Remote plugin catalog data is cached for suggestions and discovery.

Code references:
- `ListPluginsArgs::json` and `ListPluginsArgs::available` in `codex-rs/cli/src/plugin_cmd.rs`
- `JsonPluginListOutput` and `JsonPluginListEntry` in `codex-rs/cli/src/plugin_cmd.rs`
- `catalog_cache` in `codex-rs/core-plugins/src/remote/catalog_cache.rs`
- Plugin discovery logic in `codex-rs/core-plugins/src/discoverable.rs`


### Hosted web and image tools in more code-mode flows
What: Hosted web search and image generation are available in more tool-planning paths, and standalone web search can run in parallel.

Usage:
```text
Ask Codex to search the web or generate/edit an image during a code-mode session.
```

Details:
- Hosted specs are no longer filtered out of code-mode-only visibility in the same way as before.
- The standalone `web.run` extension now declares support for parallel tool calls.
- Image generation extension exposure changed from `DirectModelOnly` to `Direct`, making it available through nested code-mode tool surfaces when enabled by model/provider/auth gates.

Code references:
- `hosted_model_tool_specs` and hosted spec planning in `codex-rs/core/src/tools/spec_plan.rs`
- `WebSearchTool::supports_parallel_tool_calls` in `codex-rs/ext/web-search/src/tool.rs`
- `ImageGenerationTool::exposure` in `codex-rs/ext/image-generation/src/tool.rs`


### Multi-agent v2 follow-ups, runtime metadata, and quieter spawn output
What: Multi-agent v2 now carries runtime choice with threads, uses clearer follow-up naming, and hides spawn metadata by default.

Usage:
```text
Use `spawn_agent` for a new agent, then `followup_task` to give an existing agent another task.
```

Details:
- The v2 tool formerly named internally as `assign_task` is now wired as `followup_task`.
- Per-thread multi-agent runtime is resolved from persisted metadata, so resumed threads keep the expected v1/v2 tool surface.
- `multi_agent_v2.hide_spawn_agent_metadata` now defaults to `true`.
- Thread objects now expose `parentThreadId` for subagent relationships.

Code references:
- `FollowupTaskHandler` wiring in `codex-rs/core/src/tools/spec_plan.rs`
- `MultiAgentVersion` resolution in `codex-rs/core/src/session/mod.rs` and `codex-rs/core/src/session/turn_context.rs`
- `hide_spawn_agent_metadata` default in `codex-rs/core/src/config/mod.rs`
- `Thread::parent_thread_id` in `codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs`
- Thread schema updates in `codex-rs/app-server-protocol/schema/json/v2/Thread*.json`

### `codex exec` preserves auto-review approval policy
What: Headless `codex exec` now preserves auto-review approval behavior instead of silently dropping the headless approval policy in strict auto-review flows.

Usage:
```bash
codex exec --approval-policy on-request "make the requested change"
```

Details:
- The exec path now tracks whether to preserve the headless approval policy when `approvals_reviewer` is `auto_review`.
- Guardian review can use a model-specific `auto_review_model_override` from the model catalog.

Code references:
- `preserve_headless_approval_policy` in `codex-rs/exec/src/lib.rs`
- `routes_approval_to_guardian_with_reviewer` in `codex-rs/core/src/guardian/review.rs`
- `auto_review_model_override` handling in `codex-rs/core/src/guardian/review.rs`
- Auto-review regression coverage in `codex-rs/core/tests/suite/auto_review.rs`


### App config now exposes approval-reviewer selection
What: App-server config responses can include `approvals_reviewer` inside app config, giving clients a clearer view of reviewer policy.

Usage:
```json
{"method":"config/read","params":{}}
```

Details:
- `AppConfig` now has optional `approvals_reviewer`.
- This is additive for clients; older clients should ignore the field if unused.

Code references:
- `AppConfig::approvals_reviewer` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`
- Schema update in `codex-rs/app-server-protocol/schema/json/v2/ConfigReadResponse.json`

## Bug Fixes

- Cancelling a submitted prompt before visible output now restores the draft, attachments, and collaboration mode instead of losing the composer state. Code references: `cancelled_turn_edit_restores_composer` coverage in `codex-rs/tui/src/app/tests.rs` and restore logic in `codex-rs/tui/src/chatwidget/input_restore.rs`.
- Slash-command filtering now resets selection when the filter changes, preventing stale highlighted rows. Code reference: `CommandPopup` changes in `codex-rs/tui/src/bottom_pane/command_popup.rs`.
- Footer shortcut hints now reflect running/queued state more accurately. Code reference: footer rendering updates in `codex-rs/tui/src/bottom_pane/footer.rs`.
- macOS app launches now use deep links for Codex app paths. Code reference: `codex-rs/cli/src/desktop_app/mac.rs`.
- Windows x64 release startup avoids SQLite intrinsic issues, and the Windows sandbox setup helper restores its UAC manifest. Code references: Windows SQLite release configuration and `codex-rs/windows-sandbox-rs/codex-windows-sandbox-setup.manifest`.
- Plugin loading preserves app manifest order, deduplicates local and remote curated installs, and treats malformed `skills` manifest fields as warnings. Code references: `codex-rs/core-plugins/src/loader.rs`, `codex-rs/core-plugins/src/manager.rs`, and `codex-rs/core-skills/src/loader.rs`.
- Permission approvals now carry `environmentId`, so approvals can be scoped to the environment that requested them. Code references: `PermissionsRequestApprovalParams::environment_id` in `codex-rs/app-server-protocol/src/protocol/v2/permissions.rs` and `RequestPermissionsArgs::environment_id` in `codex-rs/core/src/tools/handlers/request_permissions.rs`.
- Managed MITM proxy trust bundles are exported to child commands, and Codex-owned CA env vars are stripped when sandbox permissions escalate. Code references: `CUSTOM_CA_ENV_KEYS` handling in `codex-rs/core/src/tools/runtimes/mod.rs` and `is_managed_mitm_ca_trust_bundle_path` in `codex-rs/network-proxy/src/certs.rs`.
- Local session history can read compressed rollouts, materialize them before append, reuse compressed search snippets, and avoid stale paths after title changes. Code references: `codex-rs/rollout/src/compression.rs`, `codex-rs/rollout/src/search.rs`, and `codex-rs/rollout/src/session_index.rs`.

### Skills extension prompt injection [In Development]
What: This release adds a new skills extension scaffold that can resolve per-turn skill catalogs and inject skill instructions from turn input context.

Status: Infrastructure is present, but the release notes classify the related work as plumbing rather than a fully exposed user workflow.

Details:
- New `codex-skills-extension` crate files resolve skill sources, selection, rendering, and extension state.
- The extension contributes turn-input context rather than a new CLI command.

Code references:
- `codex-rs/ext/skills/src/extension.rs`
- `codex-rs/ext/skills/src/catalog.rs`
- `codex-rs/ext/skills/src/selection.rs`
- `codex-rs/ext/skills/src/render.rs`


### Remote-control management RPCs [Experimental]
What: The remote-control pairing/list/revoke RPCs are implemented but marked experimental in the app-server protocol.

Status: Experimental API; generated default schemas intentionally exclude these methods unless experimental schema generation is enabled.

Details:
- Use only from clients that opt into experimental app-server APIs.
- The public schema export tests verify the methods appear only in experimental generation.

Code references:
- `#[experimental("remoteControl/pairing/start")]` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `generate_json_includes_remote_control_methods_with_experimental_api` in `codex-rs/app-server-protocol/src/export.rs`

## Notes

No breaking migration was found for ordinary CLI users. App-server clients should treat the new response fields as additive:
- `RateLimitSnapshot.individualLimit`
- `Thread.parentThreadId`
- `PermissionsRequestApprovalParams.environmentId`
- `AppConfig.approvals_reviewer`
- `ConfigLayerSource.enterpriseManaged`
- `HookSource.cloudManagedConfig`

Clients that validate schemas strictly should update generated protocol bindings for v0.137.0 before consuming these fields.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.137.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.137.0.md`
