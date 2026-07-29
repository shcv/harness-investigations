# Changelog for version 0.146.0

## Summary

Codex 0.146.0 improves session organization, thread forking, plugin interoperability, remote Code Mode, and custom-provider web search. It also substantially hardens proxy routing, MCP refresh behavior, conversation persistence, terminal interaction, and Windows process cleanup.

## Official Release Highlights


### Organize named, pinned, and side conversations

What: The TUI can assign a name when creating or clearing a session, preserve pinned threads, and switch between side conversations without closing either conversation.

Usage:

```text
/new Add user authentication
/clear Investigate flaky tests
```

Details:

- Thread pin state is persisted and can be filtered through the app-server.
- The existing thread-name RPC remains available to clients; this release adds the session-creation UX around it.
- Side-conversation switching has a configurable `toggle_side_conversation` keybinding.

Code references:

- `ThreadMetadataUpdateParams.is_pinned` and `ThreadListParams.is_pinned` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- Named `/new` and `/clear` handling in `codex-rs/tui/src/chatwidget/tests/slash_commands.rs`
- `toggle_side_conversation` in `codex-rs/config/src/tui_keymap.rs`


### Use Agent Plugins and expanded plugin marketplaces

What: Codex now recognizes Agent Plugins manifests, supports workspace plugin publishing, and selects the appropriate curated marketplace for Amazon Bedrock and Claude Code integrations.

Usage:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "acme.tools",
  "description": "Project-specific Codex tools"
}
```

Details:

- Place the Agent Plugins manifest in the plugin root as `plugin.json`.
- Codex accepts the Agent Plugins schema while still allowing a `.codex-plugin/plugin.json` overlay for Codex-specific apps and hooks.
- Workspace sharing requires an authenticated workspace account.

Code references:

- `parse_agent_plugin_manifest_uri` in `codex-rs/core-plugins/src/agent_plugin_manifest.rs`
- `AGENT_PLUGIN_SCHEMA_URI` in `codex-rs/utils/plugins/src/plugin_namespace.rs`
- Workspace sharing in `codex-rs/core-plugins/src/remote/share.rs`
- Marketplace selection in `codex-rs/core-plugins/src/manager.rs`


### Fork paginated threads, including temporary forks

What: Thread forks now work with paginated history and can be marked ephemeral so the fork remains usable without appearing in normal thread listings.

Usage:

```json
{
  "method": "thread/fork",
  "params": {
    "threadId": "thread-123",
    "lastTurnId": "turn-42",
    "ephemeral": true
  }
}
```

Details:

- `lastTurnId` forks through a specified completed turn.
- `beforeTurnId` forks before a specified turn.
- `ephemeral` requests a non-listed temporary fork; clients can also request `excludeTurns` when they will page history separately.

Code references:

- `ThreadForkParams` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- Paginated fork handling in `codex-rs/thread-store/src/lib.rs`


### Connect app-server to a remote Code Mode host

What: App-server can use a Code Mode host over WebSocket instead of only a local process.

Usage:

```bash
codex app-server --code-mode-host wss://code-mode.example.test/session
```

Details:

- The endpoint must be a valid `ws://` or `wss://` URL.
- This depends on the stable, default-enabled `code_mode_host` feature.
- The app-server uses the remote host for Code Mode sessions while retaining its normal RPC interface.

Code references:

- `AppServerCodeModeHostArgs` in `codex-rs/app-server/src/code_mode_host.rs`
- `WebSocketCodeModeSessionProvider` in `codex-rs/code-mode/src/remote_session.rs`


### Enable standalone web search for compatible custom providers

What: Custom Responses-compatible providers can declare support for Codex’s standalone web-search tool.

Usage:

```toml
[model_providers.custom-responses]
env_key = "CUSTOM_RESPONSES_API_KEY"
requires_openai_auth = false
supports_standalone_web_search = true
```

Details:

- The provider must explicitly opt in with `supports_standalone_web_search = true`.
- Codex still requires the standalone-web-search feature to be enabled for the session.

Code references:

- `supports_standalone_web_search` in `codex-rs/config/src/thread_config/proto/codex.thread_config.v1.proto`
- Custom-provider coverage in `codex-rs/app-server/tests/suite/v2/web_search.rs`


### Discover executor-provided skills and read their resources safely

What: Skills supplied by an execution environment can be discovered through the skills tools, and explicitly selected skills can expose bounded resource reads.

Usage:

```text
Use skills.list, then pass the returned authority, package, and resource to skills.read.
```

Details:

- Resource reads are constrained to the discovered skill package and its selected execution environment.
- `skills.read` supports pagination through its `cursor` and `next_cursor` fields.

Code references:

- `ExecutorSkillProvider` in `codex-rs/ext/skills/src/provider/executor.rs`
- `ReadTool` in `codex-rs/ext/skills/src/tools/read.rs`
- `ExecutorCapabilityDiscoverySnapshot` in `codex-rs/exec-server/src/capability_discovery.rs`

## Additional Changes Beyond Official Notes


### Disable the `update_plan` tool through configuration

What: Administrators and users can now remove the model-visible `update_plan` tool while leaving other tools enabled.

Usage:

```toml
[tools.update_plan]
enabled = false
```

Details:

- The default remains enabled.
- When disabled, Codex does not register `update_plan` for the turn.

Code references:

- `UpdatePlanToolConfig` in `codex-rs/config/src/config_toml.rs`
- `resolve_update_plan_enabled` in `codex-rs/core/src/config/mod.rs`
- Tool registration gate in `codex-rs/core/src/tools/spec_plan.rs`


### Use merge-friendly shell-environment filters

What: Shell environment policy now supports keyed include/exclude filters that merge case-insensitively across configuration layers.

Usage:

```toml
[shell_environment_policy.filters]
"*TOKEN*" = "exclude"
"CI" = "include"
```

Details:

- This is the canonical table form for managed requirements and layered configuration.
- Existing `exclude` and `include_only` arrays remain supported for compatibility, but cannot be combined with `filters`.
- An exclude rule takes precedence over an include rule.

Code references:

- `ShellEnvironmentPolicyFilter` in `codex-rs/protocol/src/config_types.rs`
- `ShellEnvironmentPolicyToml` in `codex-rs/config/src/shell_environment_policy.rs`
- `validate_shell_environment_policy_filter_config` in `codex-rs/config/src/shell_environment_policy.rs`

## Bug Fixes

- Proxy routing is now consistently honored for authentication refreshes, plugin downloads, MCP OAuth, remote execution, WebSockets, redirects, updater requests, and LM Studio connections. (`RouteAwareClientPool` in `codex-rs/http-client/src/lib.rs`)
- MCP runtimes refresh after authentication or configuration changes, retain healthy connections, and replace closed connections instead of requiring a restart. (`McpConnectionSet` in `codex-rs/codex-mcp/src/connection_manager.rs`)
- Interrupted and replayed conversations retain submitted input, completed responses, failed-turn errors, imported timestamps, and fork approval settings. (`ThreadForkParams` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`)
- Terminal interaction is more responsive: turn interrupts no longer block the UI, keyboard handling and narrow layouts are improved, and wrapped OSC 8 hyperlinks render correctly. (`codex-rs/tui/src/app.rs`)
- Windows navigation keys work correctly, sandboxed process trees are terminated through job objects, and Guardian sessions preserve proxy configuration. (`JobObject` in `codex-rs/utils/pty/src/win/job.rs`)
- Skill catalogs preserve more entries under metadata pressure and emit a warning when truncation is unavoidable. (`codex-rs/core-skills/src/render.rs`)

## In Development


### Per-server MCP tool names without the `mcp__` prefix [Experimental]

What: The existing experimental non-prefixed-MCP feature can now target only selected MCP servers.

Status: Runtime-gated by the under-development `non_prefixed_mcp_tool_names` feature, disabled by default.

Usage:

```toml
[features.non_prefixed_mcp_tool_names]
enabled = true
server_names = ["github", "linear"]
```

Details:

- Only tools from the listed servers omit the legacy `mcp__` namespace prefix.
- Omitting `server_names` applies the feature’s existing global behavior.

Code references:

- `NonPrefixedMcpToolNamesConfigToml` in `codex-rs/features/src/feature_configs.rs`
- `Feature::NonPrefixedMcpToolNames` in `codex-rs/features/src/lib.rs`
- `Config::prefix_mcp_tool_names` in `codex-rs/core/src/config/mod.rs`


### Suppress the multi-agent `wait_agent` tool [Runtime-gated]

What: Multi-agent-v2 configurations can hide `wait_agent` from the model’s tool catalog.

Status: Requires the stable but default-disabled `multi_agent_v2` feature.

Usage:

```toml
[features.multi_agent_v2]
enabled = true
wait_agent_enabled = false
```

Details:

- The setting defaults to `true` when multi-agent v2 is enabled.
- It affects tool exposure only; it does not terminate or alter existing agents.

Code references:

- `MultiAgentV2ConfigToml.wait_agent_enabled` in `codex-rs/features/src/feature_configs.rs`
- Conditional `WaitAgentHandlerV2` registration in `codex-rs/core/src/tools/spec_plan.rs`


Generated with:
- tool: `harness-investigations@d136e7a`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.146.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.146.0.md`
