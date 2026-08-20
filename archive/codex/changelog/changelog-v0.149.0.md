# Changelog for version 0.149.0

## Summary

Codex 0.149.0 adds an interactive task dashboard, cross-session message queueing, TUI working-directory controls, and substantially better diagnostics. It also introduces several experimental app-server APIs for project organization and Amazon Bedrock setup, plus a configurable skills-catalog context budget.

## Official Release Highlights

### Shared agents dashboard

What: `codex agents` opens an interactive dashboard for finding, starting, opening, renaming, and stopping shared tasks.

Usage:

```bash
codex agents
```

Details:

- The dashboard shows root sessions and their subagents, and can group tasks by status or project.
- Local use requires Unix; other platforms require a remote server connection.
- New TUI keymap fields cover opening the dashboard and its search, new-task, rename, stop, and grouping actions.

Code references:

- `AgentsOverviewState` in `codex-rs/tui/src/app/agents_overview.rs`
- `Subcommand::Agents` in `codex-rs/cli/src/main.rs`
- `TuiAgentsKeymap` in `codex-rs/config/src/tui_keymap.rs`


### TUI working-directory commands

What: Interactive sessions can display or change their working directory without restarting.

Usage:

```text
/pwd
/cwd
/cd /path/to/project
```

Details:

- `/pwd` and `/cwd` display the current directory.
- `/cd` changes the originating idle primary thread’s directory; it is not accepted while a task is running.

Code references:

- `SlashCommand::Cd`, `SlashCommand::Pwd`, and `SlashCommand::Cwd` handling in `codex-rs/tui/src/chatwidget.rs`
- `WorkspaceCommandExecutor` in `codex-rs/tui/src/workspace_command.rs`


### Queue a message for an existing session

What: Send a text follow-up to a local or remote Codex session by UUID or exact name.

Usage:

```bash
codex queue --thread my-session --message "Please run the tests when the current task finishes."
```

Details:

- Image attachments are not supported by this command.
- Duplicate names resolve to the most recently used matching session.
- Queued messages now wake idle sessions reliably and preserve pasted/deferred command behavior.

Code references:

- `QueueCommand` and `run_queue_command` in `codex-rs/cli/src/queue_cmd.rs`
- `run_session_queue_command` in `codex-rs/tui/src/session_queue_commands.rs`
- JSON-RPC method `"thread/queue/add"` in `codex-rs/tui/src/session_queue_commands.rs`


### Expanded Vim editing

What: TUI Vim mode now supports replacing one character and additional change motions.

Usage:

```text
rX
cw
c$
cc
```

Details:

- `r` replaces the character under the cursor while preserving normal mode.
- The new key can be customized through `tui.keymap.vim_normal.replace_char`.

Code references:

- `replace_char` in `codex-rs/config/src/tui_keymap.rs`
- `VimPending::Replace` handling in `codex-rs/tui/src/textarea/vim.rs`


### More capable diagnostics

What: `codex doctor` now reports endpoint-protection, enterprise network/proxy, desktop-app security and state, and update-connectivity problems.

Usage:

```bash
codex doctor
```

Details:

- Update metadata network failures are reported as warnings so they do not hide more direct installation or configuration failures.
- Desktop-specific checks cover macOS and Windows security enforcement.

Code references:

- `DoctorCommand` in `codex-rs/cli/src/doctor.rs`
- `updates_check` in `codex-rs/cli/src/doctor/updates.rs`
- desktop diagnostic modules in `codex-rs/cli/src/doctor/desktop/`


### SDK configuration overrides and reasoning effort

What: SDK callers can provide exact CLI-style configuration overrides and request `max` or `ultra` reasoning effort.

Usage:

```ts
// Pass raw Codex configuration overrides through the SDK,
// and select the supported max/ultra reasoning level.
```

Details:

- This is an SDK surface; the archived Rust subtree verifies the related model/config plumbing but does not contain the SDK package itself.

Code references:

- `model_reasoning_effort` configuration plumbing in `codex-rs/core/src/config/mod.rs`
- `ReasoningEffort` protocol/config types in `codex-rs/protocol/`


## Additional Changes Beyond Official Notes

### Configurable skills-catalog budget

What: You can cap the context consumed by the available-skills catalog.

Usage:

```toml
[skills]
max_context_tokens = 4000
```

Details:

- Without an override, Codex budgets 2% of the selected model’s context window.
- Explicit values are capped at 10,000 tokens.
- This is useful when a large installed skill catalog competes with task context.

Code references:

- `SkillsConfig::max_context_tokens` in `codex-rs/config/src/skills_config.rs`


## Improvements

### Apps and plugins no longer require the workspace-settings gate

Apps and plugins can be used without the previous workspace-settings restriction, reducing setup friction for installed integrations.

Code references: app/plugin workspace-settings handling in `codex-rs/chatgpt/src/workspace_settings.rs`


### Amazon Bedrock credentials refresh automatically

Codex refreshes expired AWS credentials when using Bedrock, improving continuity for long-running Bedrock-backed sessions.

Code references: Bedrock credential refresh handling in `codex-rs/model-provider/src/amazon_bedrock/`


### Larger MCP tool-name allowance

MCP tool names may now be up to 128 bytes, which improves compatibility with servers that expose descriptive names.

Code references: MCP tool-catalog validation in `codex-rs/codex-mcp/src/tools.rs`


## Bug Fixes

- Resumed and forked threads restore their active permission profile rather than falling back to current defaults. (`ThreadOwnedSettings` persistence in `codex-rs/core/src/session/`)
- TUI sub-agent activity is no longer rendered twice, and notification/approval routing is constrained to the appropriate thread. (`AgentNavigationState` in `codex-rs/tui/src/app/`)
- Realtime WebRTC sideband transport reconnects after an unexpected connection loss while retaining pending transcript output. (`RealtimeWebsocketClient` in `codex-rs/codex-api/src/endpoint/realtime_websocket/methods.rs`)
- Inline TUI history remains available in Windows Terminal scrollback, and inactive thread replay output is bounded. (terminal rendering and replay-buffer changes in `codex-rs/tui/src/`)
- Queueing a message by a duplicate session name now selects the most recent session. (`run_session_queue_command` in `codex-rs/tui/src/session_queue_commands.rs`)


## In Development

### App-server project APIs [Experimental]

What: The app-server can now create, import, read, list, update, move, and delete durable projects, each with roots, metadata, ordering, and optional assigned threads.

Usage:

```json
{
  "method": "project/create",
  "params": {
    "name": "Release work",
    "roots": [{"path": "/absolute/path/to/repo"}],
    "idempotencyKey": "client-generated-key"
  }
}
```

Status: Experimental app-server protocol surface.

Details:

- Project operations include `project/list`, `project/read`, `project/create`, `project/import`, `project/update`, `project/move`, and `project/delete`.
- Clients receive `"project/changed"` and `"thread/project/updated"` notifications.
- Thread start, update, and list shapes gain project-assignment support.
- This is protocol infrastructure for experimental clients, not a new stable TUI project-management workflow.

Code references:

- `ProjectListParams`, `ProjectCreateParams`, and related types in `codex-rs/app-server-protocol/src/protocol/v2/project.rs`
- `ProjectRequestProcessor` in `codex-rs/app-server/src/request_processors/project_processor.rs`
- new schemas in `codex-rs/app-server-protocol/schema/json/v2/Project*.json`


### Amazon Bedrock setup APIs [Experimental]

What: Experimental clients can discover local AWS profiles/environment credentials and configure Bedrock authentication through the app-server.

Usage:

```json
{
  "method": "account/bedrock/discover",
  "params": {}
}
```

```json
{
  "method": "account/bedrock/setup",
  "params": {
    "type": "profile",
    "profile": "production",
    "region": "us-east-1"
  }
}
```

Status: Experimental app-server protocol surface.

Details:

- Discovery reports AWS profiles and environment credentials.
- Setup supports an AWS profile, environment credentials, or explicit access keys.
- These methods are marked experimental; client support and availability must be negotiated through the experimental protocol.

Code references:

- `BedrockDiscoverParams`, `BedrockSetupParams`, and `AwsCredentialType` in `codex-rs/app-server-protocol/src/protocol/v2/bedrock.rs`
- `"account/bedrock/discover"` and `"account/bedrock/setup"` request definitions in `codex-rs/app-server-protocol/src/protocol/v2/mod.rs`


### Asynchronous user updates from the model [Experimental]

What: Supported models can send a concise visible progress update or blocking question without ending the active turn.

Status: Runtime-gated by the selected model’s `experimental_supported_tools` catalog entry.

Details:

- The `send_user_message_async` tool accepts a non-empty `message`, immediately returns acceptance to the model, and delivers the text as an asynchronous agent message.
- It is exposed only to root agents and only when the active model catalog explicitly lists the tool.
- There is no user configuration switch for this feature.

Code references:

- `SendUserMessageAsyncHandler` in `codex-rs/core/src/tools/handlers/send_user_message_async.rs`
- tool registration in `add_core_utility_tools` in `codex-rs/core/src/tools/spec_plan.rs`


## Notes

App-server clients should treat the experimental project and Bedrock methods as additive protocol extensions, and should handle the new project notifications before relying on them. No stable configuration or CLI migration is required for existing users.


Generated with:
- tool: `harness-investigations@9a200b9-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.149.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.149.0.md`
