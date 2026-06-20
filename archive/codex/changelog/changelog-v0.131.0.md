# Changelog for version 0.131.0

## Summary
Codex 0.131.0 is a broad release focused on operational readiness: support diagnostics with `codex doctor`, richer TUI status/rendering, plugin marketplace workflows, remote-control daemon plumbing, and a renamed Python SDK package. The diff is from `rust-v0.130.0` (`3ebb3e033d`) to `rust-v0.131.0` (`02d0ab56b9`), and the source tree at `archive/codex/source/codex-rs/` was available for verification.

### TUI session controls and display
What: The interactive TUI shows more session state directly and handles richer transcript rendering.

Usage:
```bash
codex
/fast
/standard
/status
```

Details:
- Service-tier slash commands are now data-driven from the model’s advertised tiers, and the stored config value is a string request id such as `priority` or `flex`; legacy `fast` still maps to the fast tier.
- The status line and status surfaces show blended token usage through `TokenUsage::blended_total`.
- The TUI status setup can include permissions/approval mode and effective workspace roots.
- Markdown pipe tables are detected and held back while streaming so they can render as coherent responsive tables instead of unstable partial rows.

Code references:
- `ChatWidget::current_model_service_tier_commands` in `codex-rs/tui/src/chatwidget/service_tiers.rs`
- `ServiceTier` in `codex-rs/protocol/src/config_types.rs`
- `TokenUsage::blended_total` in `codex-rs/tui/src/token_usage.rs`
- `StatusLineItem::Permissions` in `codex-rs/tui/src/bottom_pane/status_line_setup.rs`
- `TableHoldbackScanner` in `codex-rs/tui/src/streaming/table_holdback.rs`
- `table_detect` in `codex-rs/tui/src/table_detect.rs`


### Unified `@` mentions [Experimental]
What: A new mention picker can search filesystem entries, skills, and plugins from one `@` flow.

Usage:
```bash
codex --enable mentions_v2
```

Details:
- This is present in the release but is not default-enabled. `Feature::MentionsV2` is marked experimental with `default_enabled: false`.
- The picker has search modes for all results, filesystem only, and plugins/skills.
- Plugin mention inventory comes from app-server `plugin/list`, while skill metadata is merged locally into the search catalog.

Code references:
- `Feature::MentionsV2` in `codex-rs/features/src/lib.rs`
- `SearchMode` in `codex-rs/tui/src/bottom_pane/mentions_v2/search_mode.rs`
- `build_search_catalog` in `codex-rs/tui/src/bottom_pane/mentions_v2/search_catalog.rs`
- `fetch_plugin_mentions` in `codex-rs/tui/src/app/plugin_mentions.rs`


### Plugin marketplace CLI and sharing
What: Codex now has first-class plugin CLI commands and additional app-server sharing APIs.

Usage:
```bash
codex plugin marketplace add owner/repo --ref main --sparse plugins/foo
codex plugin marketplace list
codex plugin marketplace upgrade
codex plugin add sample@debug
codex plugin list --marketplace debug
codex plugin remove sample@debug
```

Details:
- `codex plugin` is new in this version; `git grep` finds no `PluginCli` or `codex-rs/cli/src/plugin_cmd.rs` in `rust-v0.130.0`.
- Marketplace management now supports add, list, upgrade, and remove.
- Plugin install/list/remove operate on configured marketplace snapshots.
- App-server clients gained `"plugin/share/checkout"` for materializing a shared remote plugin into a local plugin path.
- Plugin list/read requests no longer use the config serialization queue, reducing avoidable blocking.

Code references:
- `PluginCli` and `PluginSubcommand` in `codex-rs/cli/src/plugin_cmd.rs`
- `MarketplaceCli` and `MarketplaceSubcommand::Upgrade` in `codex-rs/cli/src/marketplace_cmd.rs`
- JSON-RPC method `"plugin/share/checkout"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `PluginShareCheckoutParams` / `PluginShareCheckoutResponse` in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`
- `RemotePluginShareCheckoutResult` in `codex-rs/core-plugins/src/remote/share/checkout.rs`
- Schemas `codex-rs/app-server-protocol/schema/json/v2/PluginShareCheckoutParams.json` and `PluginShareCheckoutResponse.json`


### Remote control and remote environments [Experimental]
What: Remote Codex workflows now have daemon-managed lifecycle commands and app-server APIs for runtime remote-control state.

Usage:
```bash
codex remote-control
codex remote-control stop
codex app-server daemon bootstrap --remote-control
codex app-server daemon start
codex app-server daemon enable-remote-control
codex app-server daemon disable-remote-control
codex app-server daemon version
```

For clients:
```json
{"method": "remoteControl/status/read", "params": null}
```

Details:
- `codex remote-control` existed in 0.130.0, but 0.131.0 changes it into a daemon-backed flow with `start` and `stop` subcommands.
- `codex app-server daemon ...` is new Unix-only lifecycle management for local app-server processes.
- Daemon commands return a single JSON object on success, including socket path and version fields.
- New experimental JSON-RPC methods support runtime enable/disable/status reads for remote control.
- New experimental `"environment/add"` lets clients register remote execution environments by id and exec-server URL.

Code references:
- `RemoteControlCommand` in `codex-rs/cli/src/main.rs`
- `AppServerDaemonSubcommand` in `codex-rs/cli/src/main.rs`
- `LifecycleCommand`, `BootstrapOptions`, and `RemoteControlOutput` in `codex-rs/app-server-daemon/src/lib.rs`
- `codex-rs/app-server-daemon/README.md`
- JSON-RPC methods `"remoteControl/enable"`, `"remoteControl/disable"`, `"remoteControl/status/read"`, and `"environment/add"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `EnvironmentAddParams` in `codex-rs/app-server-protocol/src/protocol/v2/environment.rs`


### Python SDK renamed to `openai-codex`
What: The experimental Python SDK moved from `openai-codex-app-server-sdk` / `codex_app_server` to `openai-codex` / `openai_codex`.

Usage:
```bash
pip install openai-codex
```

```python
from openai_codex import Codex, retry_on_overload

with Codex() as codex:
    thread = codex.thread_start(model="gpt-5")
    result = thread.run("summarize this repo")
```

Details:
- The package now depends on a pinned `openai-codex-cli-bin==0.131.0a4` runtime package.
- Public generated protocol types moved into `openai_codex.types`.
- `MessageRouter` routes concurrent JSON-RPC responses and turn notifications so multiple SDK operations do not compete for the same app-server stdout stream.
- The package root exports the ergonomic client API and retry helper directly.

Code references:
- Project name and runtime dependency in `sdk/python/pyproject.toml`
- `openai_codex.__all__` in `sdk/python/src/openai_codex/__init__.py`
- `openai_codex.types` in `sdk/python/src/openai_codex/types.py`
- `MessageRouter` in `sdk/python/src/openai_codex/_message_router.py`


### `codex doctor`
What: `codex doctor` generates a local diagnostic report for support and troubleshooting.

Usage:
```bash
codex doctor
codex doctor --summary
codex doctor --json
codex doctor --all --no-color --ascii
```

Details:
- This command is new in 0.131.0; no `doctor` CLI module or `DoctorCommand` is present in `rust-v0.130.0`.
- It checks installation/runtime, search availability, config loading, auth, network environment, MCP config, sandbox helpers, terminal metadata, local state, and provider reachability.
- `--json` emits a redacted machine-readable report. A failed check exits non-zero.
- Feedback upload can attach a best-effort `codex-doctor-report.json`.

Code references:
- `DoctorCommand` in `codex-rs/cli/src/doctor.rs`
- `run_doctor` in `codex-rs/cli/src/doctor.rs`
- `DoctorReport`, `DoctorCheck`, and `DoctorIssue` in `codex-rs/cli/src/doctor.rs`
- `feedback_doctor_report` in `codex-rs/app-server/src/request_processors/feedback_doctor_report.rs`


### Reliability and platform fixes
What: The release includes multiple fixes for TUI behavior, Windows sandboxing, app-server state handling, Git hooks, auth cleanup, and remote cleanup.

Details:
- TUI fixes include URL wrapping, light-mode selection contrast, Shift+Enter handling in tmux CSI-u panes, `/review` MCP startup rendering, `/side` Esc behavior, and clearer network approval history.
- Windows sandboxing now has real deny-read ACL planning and reconciliation, stricter firewall policy validation, scoped write-root capability SIDs, and safer PowerShell handling.
- Local state startup avoids destructive SQLite version bumps and can recover more gracefully from startup failures.
- Git helper commands ignore configured hooks and fsmonitor settings where appropriate.
- Superseded ChatGPT login tokens are revoked on relogin.

Code references:
- `resolve_windows_deny_read_paths` in `codex-rs/windows-sandbox-rs/src/deny_read_resolver.rs`
- `sync_persistent_deny_read_acls` in `codex-rs/windows-sandbox-rs/src/deny_read_state.rs`
- `SetupErrorCode::HelperFirewallPolicyIneffective` in `codex-rs/windows-sandbox-rs/src/bin/setup_main/win/firewall.rs`
- PowerShell stop-parsing rejection in `codex-rs/shell-command/src/command_safety/windows_safe_commands.rs`
- SQLite state handling in `codex-rs/state/src/runtime.rs`
- `revoke` flow in `codex-rs/login/src/auth/revoke.rs`

### Strict config validation
What: Users and app-server hosts can opt into failing when config files contain unknown fields.

Usage:
```bash
codex --strict-config
codex exec --strict-config "inspect the repo"
codex review --strict-config --uncommitted
codex mcp-server --strict-config
codex app-server --strict-config
```

Details:
- This is new in 0.131.0; `git grep "strict-config"` finds no matches in 0.130.0 CLI/app-server sources.
- Strict validation uses serde ignored-field tracking and also catches unknown feature keys.
- Unsupported subcommands reject root-level `--strict-config` explicitly instead of silently accepting it.

Code references:
- `config_error_from_ignored_toml_fields` in `codex-rs/config/src/strict_config.rs`
- CLI flags in `codex-rs/cli/src/main.rs`
- App-server flag in `codex-rs/app-server/src/main.rs`
- `RemoteAppServerConfig::strict_config` in `codex-rs/app-server-client/src/lib.rs`


### Multiple forced ChatGPT workspace IDs
What: `forced_chatgpt_workspace_id` can now be either one workspace id string or a TOML list of workspace ids.

Usage:
```toml
forced_chatgpt_workspace_id = "123e4567-e89b-42d3-a456-426614174000"
```

```toml
forced_chatgpt_workspace_id = [
  "123e4567-e89b-42d3-a456-426614174000",
  "123e4567-e89b-42d3-a456-426614174001",
]
```

Details:
- Comma-separated strings are rejected with guidance to use a TOML list.
- The app-server protocol exposes the same backward-compatible single-or-multiple shape.

Code references:
- `ForcedChatgptWorkspaceIds` in `codex-rs/config/src/config_toml.rs`
- `ForcedChatgptWorkspaceIds` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`
- `UserSavedConfig::forced_chatgpt_workspace_id` conversion in `codex-rs/config/src/config_toml.rs`


### App-server attestation requests
What: App-server clients can opt into generating a fresh upstream attestation token for Codex requests.

Usage:
```json
{
  "method": "initialize",
  "params": {
    "clientInfo": {"name": "desktop", "version": "0.1.0"},
    "capabilities": {"requestAttestation": true}
  }
}
```

Server request:
```json
{"method": "attestation/generate", "params": {}}
```

Details:
- This is new in 0.131.0; no `attestation/generate`, `AttestationGenerateParams`, or `request_attestation` appears in 0.130.0.
- When enabled, app-server can send `"attestation/generate"` to the capable client and wraps the returned opaque token into the upstream `x-oai-attestation` header envelope.
- Generation is timeout-bounded; failures are represented in the envelope rather than blocking indefinitely.

Code references:
- `InitializeCapabilities::request_attestation` in `codex-rs/app-server-protocol/src/protocol/v1.rs`
- `AttestationGenerateParams` / `AttestationGenerateResponse` in `codex-rs/app-server-protocol/src/protocol/v2/attestation.rs`
- `AttestationProvider` in `codex-rs/core/src/attestation.rs`
- `app_server_attestation_provider` in `codex-rs/app-server/src/attestation.rs`
- New schemas `codex-rs/app-server-protocol/schema/json/AttestationGenerateParams.json` and `AttestationGenerateResponse.json`


### Runtime workspace roots in app-server protocol [Experimental]
What: App-server clients can set runtime workspace roots independently when starting, resuming, forking, or continuing a thread.

Usage:
```json
{
  "method": "thread/start",
  "params": {
    "cwd": "/repo",
    "runtimeWorkspaceRoots": ["/repo", "/shared"],
    "permissions": "workspace-write"
  }
}
```

Details:
- `runtimeWorkspaceRoots` is new on `thread/start`, `thread/resume`, `thread/fork`, and `turn/start`.
- Responses now include the effective `runtimeWorkspaceRoots` used to materialize symbolic `:workspace_roots`.
- `permissions` is now serialized as a named profile id string for new clients; the legacy object form is still deserialized for compatibility.
- `permissionProfile` was removed from thread start/resume/fork responses; clients should use `activePermissionProfile` plus the legacy `sandbox` compatibility field.

Code references:
- `ThreadStartParams::runtime_workspace_roots` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- `ThreadResumeParams::runtime_workspace_roots` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- `ThreadForkParams::runtime_workspace_roots` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- `TurnStartParams::runtime_workspace_roots` in `codex-rs/app-server-protocol/src/protocol/v2/turn.rs`
- `PermissionProfileSelectionParams` in `codex-rs/app-server-protocol/src/protocol/v2/permissions.rs`


### Desktop-owned config namespace
What: `config.toml` and app-server config APIs now preserve an opaque `desktop` object for desktop-owned settings.

Usage:
```toml
[desktop]
someClientOwnedKey = "value"
```

Details:
- Codex stores this namespace without interpreting its contents.
- This lets desktop clients keep their own settings alongside user config without forcing the CLI to understand every key.

Code references:
- `ConfigToml::desktop` in `codex-rs/config/src/config_toml.rs`
- `UserSavedConfig::desktop` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`
- JSON schema changes in `codex-rs/app-server-protocol/schema/json/v2/ConfigReadResponse.json`

### More flexible service-tier config
`service_tier` is now a string in both top-level config and profiles, allowing backend-defined tier ids beyond the old enum values while keeping legacy `fast` behavior.

Code references: `ConfigToml::service_tier` in `codex-rs/config/src/config_toml.rs`; `ConfigProfile::service_tier` in `codex-rs/config/src/profile_toml.rs`; `ServiceTier::request_value` in `codex-rs/protocol/src/config_types.rs`


### Plugin metadata includes versions and share roles
Plugin protocol objects now carry local/remote version fields, discoverability, and role information for share targets/principals. This supports safer version-aware plugin sharing.

Code references: `PluginSummary::local_version`, `PluginSummary::remote_version`, `PluginShareTargetRole`, and `PluginSharePrincipalRole` in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`


### App-server remote transport supports Unix sockets
Remote app-server client transport now accepts either WebSocket endpoints or Unix socket endpoints, using WebSocket framing over the Unix stream.

Code references: `RemoteAppServerEndpoint::UnixSocket` in `codex-rs/app-server-client/src/remote.rs`; `UDS_WEBSOCKET_HANDSHAKE_URL` in `codex-rs/app-server-client/src/remote.rs`


### Feedback uploads can include diagnostic context
Feedback upload can attach a redacted doctor report and low-cardinality status tags when available.

Code references: `DoctorReportAttachment` and `feedback_doctor_report` in `codex-rs/app-server/src/request_processors/feedback_doctor_report.rs`

## Bug Fixes

- Fixed Windows deny-read enforcement so managed unreadable paths can become concrete ACL targets instead of being only direct-file-tool restrictions (`resolve_windows_deny_read_paths` in `codex-rs/windows-sandbox-rs/src/deny_read_resolver.rs`; `sync_persistent_deny_read_acls` in `codex-rs/windows-sandbox-rs/src/deny_read_state.rs`).
- Fixed Windows sandbox firewall setup to fail when firewall policy is ineffective rather than reporting a false success (`SetupErrorCode::HelperFirewallPolicyIneffective` in `codex-rs/windows-sandbox-rs/src/bin/setup_main/win/firewall.rs`).
- Fixed a Windows command-safety hole by rejecting PowerShell stop-parsing forms such as `--%` in otherwise read-only-looking invocations (`parser_process_rejects_stop_parsing_forms` in `codex-rs/shell-command/src/command_safety/powershell_parser.rs`; `rejects_stop_parsing_git_forms` in `codex-rs/shell-command/src/command_safety/windows_safe_commands.rs`).
- Fixed app-server startup safety around local state by preserving SQLite data across version changes and failing closed when state cannot be opened (`codex-rs/state/src/runtime.rs`; `codex-rs/app-server/tests/suite/strict_config.rs`).
- Fixed remote-client thread history redaction for ChatGPT remote clients (`thread_resume_redaction` in `codex-rs/app-server/src/request_processors/thread_resume_redaction.rs`).
- Fixed Git helper behavior so root worktree hooks are used consistently and configured hooks/fsmonitor are ignored in metadata helper paths (`codex-rs/git-utils/src/operations.rs`; `codex-rs/core/src/git_info_tests.rs`).
- Fixed login hygiene by revoking superseded ChatGPT auth tokens during relogin (`codex-rs/login/src/auth/revoke.rs`; `codex-rs/login/src/auth/manager.rs`).
- Fixed TUI rendering and interaction regressions around wrapped URLs, selection contrast, Shift+Enter in tmux, `/review` MCP startup rendering, `/side` Esc handling, and network approval history text (`codex-rs/tui/src/wrapping.rs`; `codex-rs/tui/src/markdown_render.rs`; `codex-rs/tui/src/tui/keyboard_modes.rs`; `codex-rs/tui/src/chatwidget/review.rs`; `codex-rs/tui/src/chatwidget/side.rs`; `codex-rs/tui/src/chatwidget/tests/approval_requests.rs`).

### Extension, guardian, and memories extension infrastructure [In Development]
What: New extension crates add typed contributor hooks and move guardian/memory behavior toward extension-owned plumbing.

Status: Infrastructure is present, but most of this is internal framework work rather than a direct user-invoked feature in this release.

Details:
- New workspace members include `ext/extension-api`, `ext/guardian`, and `ext/memories`.
- The API includes prompt, thread lifecycle, turn lifecycle, token usage, and config-change contributor surfaces.
- The official notes classify this as ongoing extraction of extension and tool internals, not a stable public extension authoring surface.

Code references: `codex-rs/ext/extension-api/src/lib.rs`; `codex-rs/ext/guardian/src/lib.rs`; `codex-rs/ext/memories/src/lib.rs`


### Remote environment registration [Experimental]
What: `"environment/add"` adds or replaces a remote environment by id for later selection.

Status: Experimental app-server API.

Usage:
```json
{
  "method": "environment/add",
  "params": {
    "environmentId": "remote-a",
    "execServerUrl": "ws://127.0.0.1:8765"
  }
}
```

Details:
- The method is explicitly marked experimental.
- It pairs with thread/turn `environments` fields rather than being a standalone CLI workflow.

Code references: `EnvironmentAddParams` in `codex-rs/app-server-protocol/src/protocol/v2/environment.rs`; `"environment/add"` in `codex-rs/app-server-protocol/src/protocol/common.rs`; `EnvironmentProcessor` in `codex-rs/app-server/src/request_processors/environment_processor.rs`

## Notes

- Python SDK migration: update imports from `codex_app_server` to `openai_codex`, and install `openai-codex` instead of `openai-codex-app-server-sdk`.
- App-server protocol migration: clients that consumed `permissionProfile` from thread start/resume/fork responses should switch to `activePermissionProfile` and `runtimeWorkspaceRoots`; `sandbox` remains as the legacy compatibility policy.
- Config migration: `service_tier` can now be any string request id; `fast` remains supported as a legacy alias. Unknown config fields are still tolerated unless `--strict-config` is used.
- ChatGPT workspace restriction migration: use a TOML list for multiple `forced_chatgpt_workspace_id` values; comma-separated strings are rejected.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.131.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.131.0.md`
