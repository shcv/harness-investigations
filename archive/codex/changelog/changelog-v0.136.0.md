# Changelog for version 0.136.0

## Summary
Version 0.136.0 compares `rust-v0.135.0` to `rust-v0.136.0`. The headline changes are better TUI rendering, session archive commands in the CLI/TUI, app-server protocol improvements, safer command execution paths, Windows sandbox setup work, and a feature-gated standalone image-generation extension.

### Clickable TUI Links and Better Narrow Table Rendering
What: Markdown rendered in the TUI now preserves web links as terminal hyperlinks and can switch cramped tables into readable key/value records.

Details:
- Web URLs are annotated with OSC 8 hyperlink metadata while keeping visible text unchanged.
- Markdown table rendering now falls back to key/value records when columns become too narrow to scan.
- Link metadata is reattached after wrapping, so table fallback does not discard link targets.

Code references:
- `annotate_web_urls_in_line` in `codex-rs/tui/src/terminal_hyperlinks.rs`
- `insert_history_hyperlink_lines_with_mode_and_wrap_policy` in `codex-rs/tui/src/insert_history.rs`
- `TableState` / key-value fallback logic in `codex-rs/tui/src/markdown_render/table_key_value.rs`


### Session Archiving from CLI and TUI
What: Users can now archive and unarchive saved sessions from the CLI, and archive the active main session from the TUI.

Usage:
```bash
codex archive <SESSION_ID_OR_NAME>
codex unarchive <SESSION_ID_OR_NAME>
```

TUI usage:
```text
/archive
```

Details:
- The app-server `thread/archive` and `thread/unarchive` RPCs already existed in v0.135.0; what is new here is the user-facing CLI/TUI wiring.
- Archived sessions are blocked from resume/fork until restored, with guidance to run `codex unarchive`.
- `/archive` is unavailable for side conversations and disabled while a task is running.

Code references:
- `Subcommand::Archive` / `Subcommand::Unarchive` in `codex-rs/cli/src/main.rs`
- `run_session_archive_command` in `codex-rs/tui/src/session_archive_commands.rs`
- `SlashCommand::Archive` in `codex-rs/tui/src/slash_command.rs`
- archived-session resume guard in `codex-rs/app-server/src/request_processors/thread_processor.rs`


### App-Server Resume, Status, and Stdio Improvements
What: App-server clients get more efficient resume bootstrapping, richer MCP server status, and a clearer stdio launch flag.

Usage:
```bash
codex app-server --stdio
```

Protocol example:
```json
{
  "method": "thread/resume",
  "id": 13,
  "params": {
    "threadId": "thr_123",
    "excludeTurns": true,
    "initialTurnsPage": {
      "limit": 20,
      "sortDirection": "desc",
      "itemsView": "summary"
    }
  }
}
```

Details:
- `thread/resume` can return an `initialTurnsPage`, avoiding a second `thread/turns/list` request for clients that need recent history immediately.
- `mcpServerStatus/list` now includes optional MCP server presentation metadata.
- `codex app-server --stdio` is an alias for `--listen stdio://` and conflicts with `--listen`.

Code references:
- `ThreadResumeInitialTurnsPageParams` and `TurnsPage` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- `McpServerStatus.server_info` in `codex-rs/app-server-protocol/src/protocol/v2/mcp.rs`
- `McpServerInfo` in `codex-rs/protocol/src/mcp.rs`
- `AppServerCommand.stdio` in `codex-rs/cli/src/main.rs`
- schemas `codex-rs/app-server-protocol/schema/json/v2/ThreadResumeParams.json`, `ThreadResumeResponse.json`, and `ListMcpServerStatusResponse.json`


### Remote Execution and Remote Control Auth Changes
What: Remote exec-server registration can use `CODEX_API_KEY` for approved hosts, while app-server remote control now uses short-lived server tokens for websocket auth.

Usage:
```bash
CODEX_API_KEY="$OPENAI_API_KEY" codex exec-server --remote https://example.openai.com --environment-id "$ENVIRONMENT_ID"
```

Details:
- API-key remote registration is restricted to HTTPS `openai.com` / `openai.org` hosts and subdomains, or loopback hosts.
- Remote-control websocket auth now uses a refreshed `remote_control_token` instead of sending ChatGPT access tokens directly.
- Remote control still rejects API-key auth; it requires ChatGPT auth.

Code references:
- `load_exec_server_remote_auth_provider` and `validate_api_key_remote_host` in `codex-rs/cli/src/main.rs`
- `RemoteControlEnrollment::should_refresh_server_token` in `codex-rs/app-server-transport/src/transport/remote_control/enroll.rs`
- remote-control websocket bearer handling in `codex-rs/app-server-transport/src/transport/remote_control/websocket.rs`


### Windows Sandbox Setup and Requirements
What: Windows gets an alpha elevated sandbox provisioning command and app-server requirements now expose which Windows sandbox implementations are allowed.

Usage:
```bash
codex sandbox setup --elevated --current-user
codex sandbox setup --elevated --user DOMAIN\\alice --codex-home C:\\Users\\alice\\.codex
```

Details:
- The setup command is Windows-only and currently requires `--elevated`.
- Managed requirements can allow or reject `elevated` versus `unelevated` Windows sandbox setup.
- `windowsSandbox/setupStart` validates managed requirements before acknowledging setup.

Code references:
- `SandboxSetupCommand` in `codex-rs/cli/src/sandbox_setup.rs`
- `run_elevated_provisioning_setup` in `codex-rs/windows-sandbox-rs/src/setup.rs`
- `ConfigRequirements.allowed_windows_sandbox_implementations` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`
- `resolve_allowed_windows_sandbox_setup_mode` in `codex-rs/app-server/src/request_processors/windows_sandbox_processor.rs`


### Image Generation Extension [In Development]
What: A standalone image-generation extension was added, but it is gated and disabled by default.

Status: Runtime-gated by feature flag `imagegenext`, marked under development.

Details:
- The extension routes standalone image generation/edit calls through Codex’s native image artifact completion pipeline.
- It is wired into app-server extension installation but guarded by the feature system.

Code references:
- `Feature::ImageGenExt` / key `imagegenext` in `codex-rs/features/src/lib.rs`
- `install` in `codex-rs/ext/image-generation/src/extension.rs`
- app-server registration in `codex-rs/app-server/src/extensions.rs`
- crate `codex-rs/ext/image-generation/`

### Runtime Skill Roots API
What: App-server clients can replace process-local extra standalone skill roots without persisting them to config.

Usage:
```json
{
  "method": "skills/extraRoots/set",
  "id": 7,
  "params": {
    "extraRoots": ["/Users/me/generated-skills"]
  }
}
```

Details:
- Missing directories are accepted and simply load no skills until they exist.
- The setting is process-local and lost when app-server exits.
- This was absent from v0.135.0 and adds new request/response schemas in v0.136.0.

Code references:
- JSON-RPC method `"skills/extraRoots/set"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `SkillsExtraRootsSetParams` / `SkillsExtraRootsSetResponse` in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`
- handler `set_skills_extra_roots` in `codex-rs/app-server/src/request_processors/catalog_processor.rs`
- new schemas `codex-rs/app-server-protocol/schema/json/v2/SkillsExtraRootsSetParams.json` and `SkillsExtraRootsSetResponse.json`


### Client-Provided User Message IDs
What: App-server clients can attach their own user-message IDs to `turn/start` and `turn/steer`, and the resulting `userMessage` item echoes that ID as `clientId`.

Usage:
```json
{
  "method": "turn/start",
  "id": 30,
  "params": {
    "threadId": "thr_123",
    "clientUserMessageId": "client_msg_123",
    "input": [{ "type": "text", "text": "Run tests" }]
  }
}
```

Details:
- This helps clients correlate optimistic UI messages with server-emitted item events.
- The field is additive; existing clients can omit it.

Code references:
- `TurnStartParams.client_user_message_id` and `TurnSteerParams.client_user_message_id` in `codex-rs/app-server-protocol/src/protocol/v2/turn.rs`
- `ThreadItem::UserMessage { client_id, ... }` in `codex-rs/app-server-protocol/src/protocol/v2/item.rs`
- schemas `codex-rs/app-server-protocol/schema/json/v2/TurnStartParams.json` and `TurnSteerParams.json`


### Request User Input Tool Toggle
What: Config now has an explicit switch for the experimental `request_user_input` model tool.

Usage:
```toml
[tools.experimental_request_user_input]
enabled = false
```

Details:
- The tool existed in v0.135.0; the new change is the config-level enable/disable control.
- The field defaults to enabled when the section exists without `enabled = false`.

Code references:
- `ToolsToml.experimental_request_user_input` and `ExperimentalRequestUserInput` in `codex-rs/config/src/config_toml.rs`
- `Config.experimental_request_user_input_enabled` in `codex-rs/core/src/config/mod.rs`
- request-user-input tool gating in `codex-rs/core/src/tools/spec_plan.rs`
- schema entry in `codex-rs/core/config.schema.json`


### Model-Provided Tool Mode Selector
What: Model metadata can now select whether a model should use direct tools, code mode, or code-mode-only behavior.

Details:
- New `ToolMode` values are `direct`, `code_mode`, and `code_mode_only`.
- Model metadata can override feature-flag defaults, letting a remote model catalog choose the correct tool surface.
- Unknown future `tool_mode` values are treated as omitted rather than failing deserialization.

Code references:
- `ToolMode` and `ModelInfo.tool_mode` in `codex-rs/protocol/src/openai_models.rs`
- tool-mode resolution in `codex-rs/core/src/session/turn_context.rs`
- code-mode filtering in `codex-rs/core/src/tools/spec_plan.rs`
- integration coverage in `codex-rs/core/tests/suite/model_runtime_selectors.rs`

### Better MCP Diagnostics and Metadata
`mcpServerStatus/list` now carries `serverInfo`, and HTTP MCP failures have more focused diagnostics around `WWW-Authenticate` insufficient-scope challenges.

Code references:
- `McpServerInfo` in `codex-rs/protocol/src/mcp.rs`
- `collect_mcp_server_status_snapshot_with_detail` status propagation in `codex-rs/codex-mcp/src/connection_manager.rs`
- `www_authenticate` parsing in `codex-rs/rmcp-client/src/http_client_adapter/www_authenticate.rs`


### Amazon Bedrock Catalog and Auth Cleanup
Amazon Bedrock bearer-token auth now falls back to `AWS_REGION` and `AWS_DEFAULT_REGION`, GPT-5.5 appears in the Bedrock catalog, old OSS Bedrock entries were removed, and Bedrock GPT models no longer advertise unsupported service tiers.

Code references:
- `bearer_token_region` in `codex-rs/model-provider/src/amazon_bedrock/auth.rs`
- `static_model_catalog`, `gpt_5_bedrock_model`, and `with_default_only_service_tier` in `codex-rs/model-provider/src/amazon_bedrock/catalog.rs`


### Web Search Activity Rendering
Standalone web search calls now emit visible start/completion items, restore completed search activity, and include better detail for searches, page opens, and find-in-page operations.

Code references:
- `WebSearchTool::execute` in `codex-rs/ext/web-search/src/tool.rs`
- `command_action` in `codex-rs/ext/web-search/src/tool.rs`
- `WebSearchCell` in `codex-rs/tui/src/history_cell/search.rs`


### TUI Session and Editing Polish
Resumed TUI sessions seed prompt history from transcript items, multiline hook output is displayed as separate indented rows, and Vim normal-mode editing gained corrected behavior such as substitute-character handling.

Code references:
- prompt-history replay in `codex-rs/tui/src/resume_picker/transcript.rs` and `codex-rs/tui/src/chatwidget/input_restore.rs`
- multiline hook output rendering in `codex-rs/tui/src/history_cell/hook_cell.rs`
- Vim normal-mode handling in `codex-rs/tui/src/bottom_pane/textarea.rs`

## Bug Fixes

- ChatGPT auth refreshes access tokens within five minutes of expiry and treats `refresh_token_reused` 400 responses as permanent relogin-required failures instead of generic transient cloud errors (`AuthManager::should_refresh_proactively` and `classify_refresh_token_failure` in `codex-rs/login/src/auth/manager.rs`).
- `/diff` avoids repository-configured Git helpers by disabling textconv, ext-diff, dirty submodule inspection, hooks, fsmonitor, and executable filters (`diff_filter_config_overrides` and `run_git_capture_diff` in `codex-rs/tui/src/get_git_diff.rs`).
- Exec-server websocket transport rejects browser-origin handshakes carrying `Origin` headers (`codex-rs/exec-server/src/server/transport.rs`).
- PowerShell safety parsing is avoided on non-Windows hosts, preventing Windows parser assumptions from affecting Unix-like systems (`codex-rs/shell-command/src/powershell.rs`).
- Linux sandbox interruption cleanup preserves shell cleanup behavior more reliably (`codex-rs/linux-sandbox` and shell runtime cleanup paths).
- Denied-read filesystem rules stay enforced when safe-command or approval paths would otherwise bypass sandboxing (`sandbox_permissions_preserving_denied_reads` and `unsandboxed_execution_allowed` in `codex-rs/core/src/tools/sandboxing.rs`).
- Windows sandbox setup now cancels more cleanly on denied network attempts and carries workspace roots into the runner/setup path (`WindowsSandboxCancellationToken` and Windows sandbox setup request handling in `codex-rs/windows-sandbox-rs`).
- File watcher debounce batching now uses `DebouncedWatchReceiver` so later batches are not swallowed after the first debounce window (`codex-rs/file-watcher/src/lib.rs` and `codex-rs/app-server/src/fs_watch.rs`).
- Plugin install auth checks avoid a forced directory refresh during app auth checks, reducing avoidable churn in plugin flows (`codex-rs/app-server/src/request_processors/plugins.rs`).

### Standalone Image Generation Extension [In Development]
What: Infrastructure exists for a standalone image generation/edit tool backed by Codex image artifact persistence.

Status: Runtime-gated by `imagegenext`, under development and disabled by default.

Code references:
- `ImageGenerationExtension` in `codex-rs/ext/image-generation/src/extension.rs`
- `ImageGenerationTool` in `codex-rs/ext/image-generation/src/tool.rs`
- feature key `imagegenext` in `codex-rs/features/src/lib.rs`


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.136.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.136.0.md`
