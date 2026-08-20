# Changelog for version 0.126.0

## Summary

Codex 0.126.0 adds a built-in update command, configurable terminal keybindings, and an experimental Agent Identity login flow. App-server clients gain provider-capability discovery, remote-control status updates, richer external-agent migration support, and an experimental persisted thread-goal API.

## New Features

### Update Codex from the CLI

What: Run the updater directly instead of manually selecting the installation-specific update command.

Usage:

```bash
codex update
```

Details:

- Detects supported release installation methods and runs the matching updater.
- Debug/source builds intentionally reject this command; update those builds manually.
- Update checks for npm and Bun installations now confirm that the latest package is available before presenting an update.

Code references:

- `Subcommand::Update` and `run_update_command` in `codex-rs/cli/src/main.rs`
- `UpdateAction::get_update_action` in `codex-rs/tui/src/update_action.rs`
- `update_versions::is_newer` in `codex-rs/tui/src/update_versions.rs`


### Configure TUI Keybindings

What: Customize supported Codex terminal shortcuts in `~/.codex/config.toml`.

Usage:

```toml
[tui.keymap.global]
copy = "ctrl-y"

[tui.keymap.composer]
submit = "ctrl-enter"
```

Details:

- Bind one key or multiple alternatives per action.
- Context-specific bindings take precedence over global bindings, which take precedence over built-in defaults.
- An empty list explicitly disables an action binding.
- Codex validates key names and normalizes common aliases such as `escape` to `esc`.
- The interactive keymap picker can write overrides to `tui.keymap.<context>.<action>`.

Code references:

- `TuiKeymap`, `TuiGlobalKeymap`, and `KeybindingsSpec` in `codex-rs/config/src/tui_keymap.rs`
- `RuntimeKeymap` in `codex-rs/tui/src/keymap.rs`
- Keybinding setup flow in `codex-rs/tui/src/keymap_setup.rs`


### Provider Capability Discovery for App-Server Clients

What: App-server clients can query capability information for the configured model provider.

Usage:

```json
{"method":"modelProvider/capabilities/read","params":{}}
```

Details:

- Lets clients adapt their UI and behavior to the active provider rather than assuming all provider features are available.
- Returns provider-level capabilities through a dedicated response shape.

Code references:

- `ModelProviderCapabilitiesReadParams` and `ModelProviderCapabilitiesReadResponse` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- New schemas `codex-rs/app-server-protocol/schema/json/v2/ModelProviderCapabilitiesReadParams.json` and `ModelProviderCapabilitiesReadResponse.json`
- Handler coverage in `codex-rs/app-server/tests/suite/v2/model_provider_capabilities_read.rs`


### Remote-Control Connection Status Notifications

What: App-server clients receive the current remote-control status at initialization and whenever it changes.

Usage:

```json
{
  "method": "remoteControl/status/changed",
  "params": {
    "status": "connected",
    "environmentId": "env_123"
  }
}
```

Details:

- Status values are `disabled`, `connecting`, `connected`, and `errored`.
- `environmentId` is cleared when enrollment becomes invalid or remote control is disabled.

Code references:

- `RemoteControlStatusChangedNotification` and `RemoteControlConnectionStatus` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- New schema `codex-rs/app-server-protocol/schema/json/v2/RemoteControlStatusChangedNotification.json`
- Remote-control transport implementation in `codex-rs/app-server/src/transport/remote_control/mod.rs`

## Improvements

### Named Permission Profiles for Sandbox Commands

Codex sandbox platform commands can resolve a named permissions profile from the active configuration stack, with an optional working directory and managed-config inclusion. This makes sandbox invocation align with configured policy rather than relying solely on the former convenience flag.

Usage:

```bash
codex sandbox linux --permissions-profile :workspace -C /path/to/project -- command arg
```

Code references: `LandlockCommand`, `SeatbeltCommand`, and `WindowsCommand` in `codex-rs/cli/src/lib.rs`; `PermissionProfile` handling in `codex-rs/core/src/config/permissions.rs`.


### Better External-Agent Configuration Migration

Codex expands its external-agent migration implementation for Claude-compatible configuration, including MCP servers, hooks, subagents, commands converted into skills, and session-related artifacts. Existing targets are preserved rather than overwritten during import.

Code references: `build_mcp_config_from_external`, `import_hooks`, `import_subagents`, and `import_commands` in `codex-rs/external-agent-migration/src/lib.rs`; `externalAgentConfig/detect` and `externalAgentConfig/import` processing in `codex-rs/app-server/src/external_agent_config_api.rs`.


### Resize-Reflow Tuning for Long Transcripts

A new terminal-resize reflow limit lets users cap how many recent rendered rows Codex replays during terminal resizing, reducing work for long conversations.

Usage:

```toml
[tui]
terminal_resize_reflow_max_rows = 500
```

Set the value to `0` to retain all rendered rows; omit it to use Codex’s terminal-specific default.

Code references: `TerminalResizeReflowConfig` and `TerminalResizeReflowMaxRows` in `codex-rs/core/src/config/types.rs`; resize handling in `codex-rs/tui/src/app/resize_reflow.rs`.


### More Informative Terminal Titles

The default terminal title now starts with an activity indicator before the project name. It spins during work and communicates when Codex is waiting for user action.

Code references: `tui_terminal_title` defaults in `codex-rs/core/src/config/types.rs`; title rendering in `codex-rs/tui/src/bottom_pane/title_setup.rs`.


### Unix-Socket App-Server Transport Uses Standard WebSocket Upgrade

Unix-socket clients now use the normal HTTP WebSocket Upgrade handshake before WebSocket frames. Clients that previously wrote raw WebSocket frames directly to the Unix socket must perform the upgrade handshake first.

Code references: Unix-socket transport in `codex-rs/app-server/src/transport/unix_socket.rs`; transport documentation in `codex-rs/app-server/README.md`.

## In Development

### Agent Identity Login [Experimental]

What: Authenticate Codex using an Agent Identity token supplied on standard input.

Usage:

```bash
printenv CODEX_AGENT_IDENTITY | codex login --with-agent-identity
```

Status: Runtime availability is subject to configured login policy; the CLI explicitly labels the token flow experimental.

Details:

- The token is read from standard input, avoiding command-line exposure.
- Codex validates and exchanges the token through the Agent Identity authentication flow.
- The flow is unavailable when configuration forces API-key-only login.

Code references: `LoginCommand::with_agent_identity` and `run_login_with_agent_identity` in `codex-rs/cli/src/main.rs` and `codex-rs/cli/src/login.rs`; `AgentIdentityJwtClaims` and `decode_agent_identity_jwt` in `codex-rs/agent-identity/src/lib.rs`.


### Persisted Thread Goals [Experimental]

What: App-server clients can create, inspect, update, and clear a single persisted objective for a thread, optionally with a token budget.

Usage:

```json
{
  "method": "thread/goal/set",
  "params": {
    "threadId": "thr_123",
    "objective": "Implement and verify the migration",
    "tokenBudget": 50000
  }
}
```

Status: Runtime-gated by `Feature::Goals`; the protocol methods are marked experimental and reject requests when the feature is disabled.

Details:

- `thread/goal/set` creates, replaces, or updates a goal.
- `thread/goal/get` returns the current goal or `null`.
- `thread/goal/clear` removes the current goal.
- Goal changes emit `thread/goal/updated` or `thread/goal/cleared`.
- The built-in model tools separate creation from completion: `create_goal` starts an objective, while `update_goal` can only mark the existing goal complete.

Code references:

- `ThreadGoalSetParams`, `ThreadGoalGetParams`, and `ThreadGoalClearParams` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- `GoalHandler` in `codex-rs/core/src/tools/handlers/goal.rs`
- Goal persistence in `codex-rs/core/src/goals.rs` and `codex-rs/state/migrations/0029_thread_goals.sql`
- Goal request processing in `codex-rs/app-server/src/request_processors/thread_goal_processor.rs`

## Notes

- If you automate `codex sandbox linux`, `codex sandbox macos`, or `codex sandbox windows`, migrate uses of `--full-auto` to a configured `--permissions-profile` invocation.
- Unix-socket app-server clients must now issue a WebSocket HTTP Upgrade handshake before exchanging WebSocket frames.


Generated with:
- tool: `harness-investigations@72cb14c-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.126.0.diff` (raw diff)
