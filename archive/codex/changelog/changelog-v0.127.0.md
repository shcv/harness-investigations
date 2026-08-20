# Changelog for version 0.127.0

## Summary

Codex 0.127.0 adds app-server support for inspecting configured hooks and gives plugin users finer control over plugin-provided MCP servers. It also improves external-session imports, login resilience, feedback diagnostics, and sandbox behavior.

## New Features

### Inspect configured hooks through the app-server

What: App-server clients can now discover the effective hooks for one or more working directories, including hook source, matcher, command, timeout, status text, plugin identity, and load/configuration errors.

Usage:

```json
{
  "method": "hooks/list",
  "params": {
    "cwds": ["/path/to/project"]
  }
}
```

Details:

- An empty `cwds` array uses the current session working directory.
- Results are returned per directory and include `hooks`, `warnings`, and `errors`.
- Plugin hooks are included only when the existing plugins and `plugin_hooks` features are enabled; configured hooks are returned only when the existing `codex_hooks` feature is enabled.

Code references:

- New `"hooks/list"` JSON-RPC method in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `HooksListParams`, `HooksListResponse`, and `HookMetadata` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- New schemas `codex-rs/app-server-protocol/schema/json/v2/HooksListParams.json` and `codex-rs/app-server-protocol/schema/json/v2/HooksListResponse.json`
- Hook resolution in `hooks_list_response` in `codex-rs/app-server/src/codex_message_processor.rs`


### Control MCP servers contributed by plugins

What: Plugin configuration can now override whether an individual plugin-provided MCP server starts and which of its tools are exposed or require approval.

Usage:

```toml
[plugins."example@marketplace"]
enabled = true

[plugins."example@marketplace".mcp_servers.docs]
enabled = true
default_tools_approval_mode = "never"

[plugins."example@marketplace".mcp_servers.docs.tools.search]
approval_mode = "always"
```

Details:

- Plugin manifests continue to define server transport and launch settings.
- User configuration can set `enabled`, a default approval mode, explicit enabled/disabled tool lists, and per-tool approval modes.
- This is applied as a policy overlay after Codex loads the plugin’s MCP-server definition.

Code references:

- `PluginMcpServerConfig` in `codex-rs/config/src/types.rs`
- `apply_plugin_mcp_server_policy` in `codex-rs/core-plugins/src/loader.rs`

## Improvements

### Remote plugin installations reconcile with local plugin state

ChatGPT-backed remote installed-plugin state is now fetched for global and workspace scopes and merged into Codex’s effective plugin configuration when a matching local plugin bundle is already cached. Plugin changes trigger a refresh of that cached remote state.

Code references: `fetch_remote_installed_plugins` in `codex-rs/core-plugins/src/remote.rs` and `remote_installed_plugins_to_config` in `codex-rs/core-plugins/src/loader.rs`


### External-session imports complete in the background

App-server imports of external-agent sessions now acknowledge the request before background session processing finishes. Clients can wait for the existing completion notification rather than blocking on the import request.

Usage:

```json
{"method": "externalAgentConfig/import", "params": {"migrationItems": []}}
```

Then wait for:

```json
{"method": "externalAgentConfig/import/completed", "params": {}}
```

Code references: `ExternalAgentConfigApi::validate_pending_session_imports` in `codex-rs/app-server/src/external_agent_config_api.rs` and `externalAgentConfig/import/completed` documentation in `codex-rs/app-server/README.md`


### Login can recover when the default callback port is busy

If Codex cannot reclaim its default local login callback port, it now retries using registered fallback port `1457`.

Code references: `FALLBACK_PORT` and `bind_server` in `codex-rs/login/src/server.rs`


### Feedback uploads include the auto-review rollout

When a feedback upload is associated with a thread that has an auto-review rollout, Codex includes that rollout as a separately named attachment after showing it in the consent dialog.

Code references: `auto_review_rollout_filename` in `codex-rs/app-server/src/codex_message_processor.rs` and `feedback_upload_consent_params` in `codex-rs/tui/src/bottom_pane/feedback_view.rs`

## Bug Fixes

- Cancelled executions are no longer reported as timeouts or assigned the timeout exit code. (`ExecExpirationOutcome` and `ExecExpiration::wait_with_outcome` in `codex-rs/core/src/exec.rs`)
- Linux Bubblewrap sandboxing more reliably masks protected project metadata paths such as `.git`, `.agents`, and `.codex`, including absent or transient paths. (`create_filesystem_args` support in `codex-rs/linux-sandbox/src/bwrap.rs`)
- Thread reads now prefer SQLite metadata for Git SHA, branch, and origin URL while retaining rollout data as fallback. (`read_thread_by_rollout_path` in `codex-rs/thread-store/src/local/read_thread.rs`)

## In Development

### Custom built-in Apps MCP endpoint [In Development]

What: Codex adds an experimental configuration shape to override the path used for the built-in Apps MCP server.

Status: Runtime-gated by the `apps_mcp_path_override` feature, which is marked `UnderDevelopment` and disabled by default.

Usage:

```toml
[features.apps_mcp_path_override]
enabled = true
path = "/custom/mcp"
```

Details:

- When enabled with a path, Codex appends that path to the configured ChatGPT backend base URL.
- This is intended for controlled or development deployments rather than normal user configuration.

Code references: `AppsMcpPathOverrideConfigToml` in `codex-rs/features/src/feature_configs.rs` and `codex_apps_mcp_url_for_base_url` in `codex-rs/codex-mcp/src/mcp/mod.rs`

## Notes

- The paused-goal command changed from `/goal unpause` to `/goal resume`. Update scripts, documentation, or muscle memory accordingly. (`slash_dispatch` in `codex-rs/tui/src/chatwidget/slash_dispatch.rs`)
- App-server clients that import external sessions should treat the `externalAgentConfig/import` response as an acknowledgement and use `externalAgentConfig/import/completed` to determine when import work has finished.


Generated with:
- tool: `harness-investigations@72cb14c-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.127.0.diff` (raw diff)
