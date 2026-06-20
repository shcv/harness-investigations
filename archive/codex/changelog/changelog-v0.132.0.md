# Changelog for version 0.132.0

## Summary
Codex 0.132.0 adds a much larger Python SDK surface, improves resumed `codex exec` structured-output workflows, and tightens several app-server protocol surfaces for plugins, image inputs, permissions, and goals. The Rust diff also includes user-visible reliability fixes for remote exec-server websockets, session picker input, Windows installs, MCP output metadata, and goal continuation loops.

### Python SDK authentication and turn APIs
What: The Python SDK now exposes first-class authentication helpers and returns richer turn results for normal text workflows.

Usage:
```python
from openai_codex import Codex

codex = Codex()
codex.login_api_key("sk-...")
account = codex.account()
result = codex.thread().run("Summarize the current repository status")
print(result.final_response)
```

Details:
- Published notes call out API-key login, ChatGPT browser login, device-code login, account inspection, and logout.
- `thread.run(...)` and handle-based `run()` now return `TurnResult`, replacing the older `RunResult` docs surface.
- Plain string input is documented directly as `input: str | Input`.

Code references:
- `Codex.login_api_key`, `Codex.login_chatgpt`, `Codex.login_chatgpt_device_code`, `Codex.account`, and `Codex.logout` in `sdk/python/src/openai_codex/api.py`
- `TurnResult` in `sdk/python/src/openai_codex/_run.py`
- API docs in `sdk/python/docs/api-reference.md`


### Structured output for resumed exec sessions
What: `codex exec resume` now accepts `--output-schema`, so resumed automation can continue an existing session while still requiring a JSON-schema-shaped final response.

Usage:
```bash
codex exec resume --last --json --output-schema schema.json "continue and return JSON"
```

Details:
- `--output-schema` is now a global exec flag, so it parses after the `resume` subcommand.
- The resumed request sends the schema as strict `json_schema` text format.

Code references:
- `Cli.output_schema` in `codex-rs/exec/src/cli.rs`
- Resume coverage in `codex-rs/exec/tests/suite/resume.rs`


### Faster TUI startup
What: Terminal startup probes are batched under one deadline instead of running several serial checks before the first frame.

Details:
- Cursor position, default colors, and keyboard-enhancement support are queried through a single `startup(...)` probe on Unix.
- The startup probe result is reused by the terminal palette and TUI key handling.

Code references:
- `StartupProbe` and `startup` in `codex-rs/tui/src/terminal_probe.rs`
- `InitializedTerminal` and `init` in `codex-rs/tui/src/tui.rs`


### Remote exec-server auth and websocket reliability
What: Remote executor registration now uses Codex auth instead of the old `CODEX_EXEC_SERVER_REMOTE_BEARER_TOKEN` registry-token flow, with an Agent Identity option for containerized callers.

Usage:
```bash
codex login
codex exec-server --remote https://example.invalid --executor-id exec-123
codex exec-server --remote https://example.invalid --executor-id exec-123 --use-agent-identity-auth
```

Details:
- `--use-agent-identity-auth` reads `CODEX_ACCESS_TOKEN` and derives AgentAssertion headers.
- Websocket keepalive pings were added for outbound exec-server and relay connections.

Code references:
- `ExecServerCommand.use_agent_identity_auth` in `codex-rs/cli/src/main.rs`
- `RemoteExecutorConfig::new` in `codex-rs/exec-server/src/remote.rs`
- `WEBSOCKET_KEEPALIVE_INTERVAL` in `codex-rs/exec-server/src/connection.rs`


### Image fidelity preservation
What: App-server and protocol paths now preserve requested image detail for remote and local images, including original-resolution local images.

Usage:
```json
{
  "method": "turn/start",
  "params": {
    "input": [
      { "type": "localImage", "path": "/tmp/screenshot.png", "detail": "original" }
    ]
  }
}
```

Details:
- `UserInput::Image` and `UserInput::LocalImage` now carry optional `detail`.
- Legacy `UserMessageEvent` now stores parallel `image_details` and `local_image_details`.
- `ImageDetail` is narrowed to `high` and `original`; old `auto` and `low` values are removed from the enum.

Code references:
- `UserInput` in `codex-rs/protocol/src/user_input.rs`
- `UserMessageEvent.image_details` and `local_image_details` in `codex-rs/protocol/src/protocol.rs`
- `ImageDetail` in `codex-rs/protocol/src/models.rs`


### Goal continuation stops on usage limits and repeated blockers
What: Goal continuations can now stop as `usage limited` or `blocked` instead of continuing indefinitely.

Details:
- `ThreadGoalStatus` now includes `Blocked` and `UsageLimited`.
- The continuation prompt only allows `blocked` after the same blocker repeats for at least three consecutive goal turns.
- TUI goal menus and footer text now show `/goal resume` for blocked and usage-limited goals.

Code references:
- `ThreadGoalStatus` in `codex-rs/protocol/src/protocol.rs`
- `usage_limit_active_thread_goal_for_turn` in `codex-rs/core/src/goals.rs`
- `core/templates/goals/continuation.md`
- `goal_status_label` in `codex-rs/tui/src/chatwidget/goal_menu.rs`


### TUI and platform fixes
What: The published notes also include several direct user-experience fixes: renamed threads show clearer resume hints, session-picker paste works, MCP replay state is more accurate, shutdown gives immediate feedback, ChatGPT usage links are hidden for non-OpenAI providers, and Windows installs are more robust.

Code references:
- `resume_hint` in `codex-rs/utils/cli/src/resume_command.rs`
- `PickerState::handle_paste` in `codex-rs/tui/src/resume_picker.rs`
- `show_shutdown_feedback` in `codex-rs/tui/src/app.rs`
- `NPM_COMMAND` in `codex-rs/cli/src/doctor.rs`
- MSVC static CRT flag in `codex-rs/.cargo/config.toml`

### Installed plugin discovery RPC
What: The app-server now has a dedicated `plugin/installed` request for mention surfaces and plugin pickers that need installed plugins plus optional install suggestions.

Usage:
```json
{
  "method": "plugin/installed",
  "params": {
    "cwds": ["/path/to/workspace"],
    "installSuggestionPluginNames": ["example-plugin"]
  }
}
```

Details:
- Returns marketplace entries containing installed local plugins, selected uninstalled suggestions, and remote installed plugins where the current feature flags and auth allow it.
- Requires plugin features to be enabled; otherwise the server returns an empty result.

Code references:
- `PluginInstalledParams` and `PluginInstalledResponse` in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`
- JSON-RPC method `"plugin/installed"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- Processor implementation `plugin_installed_response` in `codex-rs/app-server/src/request_processors/plugins.rs`
- New schemas `codex-rs/app-server-protocol/schema/json/v2/PluginInstalledParams.json` and `PluginInstalledResponse.json`


### Multi-agent v2 tool namespace [Experimental]
What: Multi-agent v2 tools can now be grouped under a configured Responses API namespace instead of appearing as separate top-level tools.

Usage:
```toml
[features.multi_agent_v2]
enabled = true
tool_namespace = "agents"
```

Details:
- When namespace support is active, tools such as `spawn_agent`, `wait_agent`, and `list_agents` are exposed under the configured namespace.
- Namespaces are validated: 1-64 characters, ASCII letters/digits/underscore/hyphen only, and reserved namespaces such as `functions`, `web`, `python`, `image_gen`, and `mcp__...` are rejected.

Code references:
- `MultiAgentV2Config.tool_namespace` in `codex-rs/core/src/config/mod.rs`
- `validate_multi_agent_v2_tool_namespace` in `codex-rs/core/src/config/mod.rs`
- `MultiAgentV2NamespaceOverride` in `codex-rs/core/src/tools/spec_plan.rs`
- Schema key `tool_namespace` in `codex-rs/core/config.schema.json`


### Thread-aware experimental feature listing
What: `experimentalFeature/list` can now accept a `threadId` so clients can compute feature enablement from that thread’s refreshed config, including project-local config for the thread cwd.

Usage:
```json
{
  "method": "experimentalFeature/list",
  "params": { "threadId": "thread-id-here" }
}
```

Code references:
- `ExperimentalFeatureListParams.thread_id` in `codex-rs/app-server-protocol/src/protocol/v2/experimental_feature.rs`
- `CatalogRequestProcessor::experimental_feature_list` in `codex-rs/app-server/src/request_processors/catalog_processor.rs`
- Schema `codex-rs/app-server-protocol/schema/json/v2/ExperimentalFeatureListParams.json`

### `command/exec` permission profile now uses active profile ids
`command/exec.permissionProfile` now accepts an `ActivePermissionProfile` id instead of requiring the client to send the full concrete sandbox shape. The server resolves the selected profile through config, which keeps named profiles, workspace roots, and managed network proxy behavior aligned with normal Codex config resolution.

Usage:
```json
{
  "method": "command/exec",
  "params": {
    "command": ["bash", "-lc", "cargo test"],
    "permissionProfile": { "id": ":workspace" }
  }
}
```

Code references: `CommandExecParams.permission_profile` in `codex-rs/app-server-protocol/src/protocol/v2/command_exec.rs`; `CommandExecRequestProcessor::command_exec` in `codex-rs/app-server/src/request_processors/command_exec_processor.rs`


### Config writes support quoted dotted key segments
`config/value/write` key paths can now quote segments that contain dots or escaped punctuation, which matters for writing nested config under keys that are not simple dotted identifiers.

Code references: `parse_key_path` in `codex-rs/app-server/src/config_manager_service.rs`


### MCP JSONL output preserves result metadata
Non-interactive JSONL output now keeps MCP tool result `_meta` content instead of dropping it from `item.completed` events.

Code references: `McpToolCallItemResult.meta` in `codex-rs/exec/src/exec_events.rs`; `EventProcessorWithJsonOutput::collect_thread_events` in `codex-rs/exec/src/event_processor_with_jsonl_output.rs`


### `view_image` has an explicit `high` detail value
The `view_image` tool now documents and accepts `detail: "high"` as the explicit spelling of the default resized behavior, alongside `detail: "original"`.

Usage:
```json
{ "path": "/tmp/screenshot.png", "detail": "high" }
```

Code references: `ViewImageHandler` in `codex-rs/core/src/tools/handlers/view_image.rs`; `create_view_image_tool` in `codex-rs/core/src/tools/handlers/view_image_spec.rs`

## Bug Fixes

- `codex doctor` now invokes `npm.cmd` on Windows when checking npm-managed installs, fixing npm root detection on that platform (`NPM_COMMAND` in `codex-rs/cli/src/doctor.rs`).
- Remote exec-server and relay websocket clients now send periodic pings, reducing dropped remote sessions through idle network paths (`WEBSOCKET_KEEPALIVE_INTERVAL` in `codex-rs/exec-server/src/connection.rs`; relay keepalive in `codex-rs/exec-server/src/relay.rs`).
- TUI status cards hide the ChatGPT usage link for providers that do not require OpenAI auth (`StatusHistoryCell` in `codex-rs/tui/src/status/card.rs`).
- Session-picker paste now normalizes pasted text and appends it to the current query instead of ignoring paste input (`normalize_pasted_query` and `PickerState::handle_paste` in `codex-rs/tui/src/resume_picker.rs`).
- Exit summaries now point renamed threads to the picker item as `name (thread-id)` instead of showing only a raw resume id (`resume_hint` in `codex-rs/utils/cli/src/resume_command.rs`).

### Goal extension crate [In Development]
What: A new `codex-goal-extension` crate sketches goal tools and extension lifecycle integration, but the crate explicitly says it is not wired into the host yet.

Status: In development; infrastructure only.

Details:
- Adds `get_goal`, `create_goal`, and `update_goal` tool specs.
- Adds extension event-sink capability and async lifecycle hooks needed by future extensions.
- Several TODOs remain for host-owned goal storage, accounting, and continuation wakeups.

Code references:
- `codex-rs/ext/goal/src/lib.rs`
- `GoalExtension` in `codex-rs/ext/goal/src/extension.rs`
- `ExtensionEventSink` in `codex-rs/ext/extension-api/src/capabilities/events.rs`

## Notes

Protocol clients should update for the `command/exec.permissionProfile` shape change. In 0.131.0, `CommandExecParams.permission_profile` accepted the full app-server `PermissionProfile` object; in 0.132.0 it accepts `{ "id": "..." }` as `ActivePermissionProfile`, and the TypeScript schema files for `PermissionProfile`, `PermissionProfileFileSystemPermissions`, and `PermissionProfileNetworkPermissions` were removed from the app-server protocol export.

Image clients should also stop sending `ImageDetail` values `auto` or `low`; the current enum supports `high` and `original`.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.132.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.132.0.md`
