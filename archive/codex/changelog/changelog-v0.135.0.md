# Changelog for version 0.135.0

## Summary
Codex 0.135.0 focuses on supportability and terminal polish: `codex doctor` now gathers richer diagnostics, remote TUI sessions show connection/version information in `/status`, Vim mode gained more editing primitives, and permission-profile selection is more explicit. The diff also adds several protocol-facing improvements not called out prominently in the published notes, including experimental app-server `additionalContext`, thread-scoped MCP status lookup, and restored `ImageDetail` compatibility for `auto` and `low`.

### Richer `codex doctor` Diagnostics
What: `codex doctor` now reports more useful environment, Git, terminal, app-server, and thread inventory information for support cases.

Usage:
```bash
codex doctor
codex doctor --json
```

Details:
- The background server check now probes the app-server control socket and reports the app-server version when available.
- Thread inventory diagnostics compare rollout files with state database rows and report stale, missing, malformed, or unreadable records.
- Terminal diagnostics include additional Windows console details.
- These checks are passive or bounded so `doctor` remains safe to run during startup/debugging issues.

Code references:
- `background_server_check` in `codex-rs/cli/src/doctor/background.rs`
- `thread_inventory_check` in `codex-rs/cli/src/doctor/thread_inventory.rs`
- `probe_app_server_version` in `codex-rs/app-server-daemon/src/lib.rs`


### Remote Session Details in `/status`
What: `/status` now shows remote transport details and the app-server version when the TUI is connected to a remote app-server.

Usage:
```text
/status
```

Details:
- Remote WebSocket display addresses are sanitized before rendering, so credentials are not shown.
- Unix-socket remote sessions render as `unix://...`.
- If the remote server does not report a version, the UI displays `unknown`.

Code references:
- `RemoteAppServerClient::server_version` in `codex-rs/app-server-client/src/remote.rs`
- `remote_connection_status_value` in `codex-rs/tui/src/status/remote_connection.rs`
- `StatusHistoryCell` remote rendering in `codex-rs/tui/src/status/card.rs`


### Vim Mode Editing and Interrupt Key Configuration
What: Vim composer mode gained text objects, better word/line-end behavior, and a configurable active-turn interrupt binding.

Usage:
```toml
[tui.keymap.chat]
interrupt_turn = "f12"

[tui.keymap.vim_normal]
change_to_line_end = "C"
start_change_operator = "c"

[tui.keymap.vim_operator]
select_inner_text_object = "i"
select_around_text_object = "a"
```

Details:
- Text objects now cover words, WORDs, parentheses, brackets, braces, double quotes, single quotes, and backticks.
- The default active-turn interrupt key remains `Esc`, but it can be remapped or explicitly unbound.
- New defaults are pruned when they would conflict with existing user-configured legacy Vim bindings.

Code references:
- `TuiVimTextObjectKeymap` in `codex-rs/config/src/tui_keymap.rs`
- `TuiChatKeymap::interrupt_turn` in `codex-rs/config/src/tui_keymap.rs`
- Vim text-object handling in `codex-rs/tui/src/bottom_pane/textarea.rs`
- Keymap setup entries in `codex-rs/tui/src/keymap_setup/actions.rs`


### Named Permission Profiles in `/permissions`
What: `/permissions` can show named permission profiles, including configured custom profiles, instead of only the older approval-mode menu.

Usage:
```text
/permissions
```

Details:
- Built-in entries include Default, Auto-review, Full Access, and Read Only.
- Custom profiles display their configured id and description.
- Selecting a custom profile emits a profile selection instead of trying to project it into a legacy approval preset.

Code references:
- `open_permission_profiles_popup` in `codex-rs/tui/src/chatwidget/permissions_menu.rs`
- `CustomPermissionProfileSummary` in `codex-rs/core/src/config/mod.rs`
- `Config::custom_permission_profiles` in `codex-rs/core/src/config/mod.rs`


### Packaged Bundled Zsh Discovery
What: Packaged Codex builds can discover the bundled patched zsh helper on supported macOS and Linux package layouts.

Usage:
```text
No config change is required for packaged builds.
```

Details:
- Codex now looks up `codex-resources/zsh/bin/zsh` through the install context.
- Runtime config gets a default zsh path from the package layout instead of requiring users to set `zsh_path` manually.
- The old `zsh_path` config field was removed from top-level and profile TOML structs; see Notes for migration guidance.

Code references:
- `InstallContext::bundled_zsh_path` in `codex-rs/install-context/src/lib.rs`
- `ConfigOverrides::default_zsh_path` in `codex-rs/core/src/config/mod.rs`
- `Config::load_config_with_layer_stack` zsh path resolution in `codex-rs/core/src/config/mod.rs`


### Python SDK Sandbox Presets
What: The official notes say the Python SDK now exposes friendly `Sandbox` presets for thread and turn APIs.

Details:
- This item is part of the published release notes, but the provided raw diff is for the `codex-rs/` subtree and does not include Python SDK source changes, so I did not expand it beyond the upstream statement.

Code references:
- Outside the provided `codex-rs/` diff.

### Experimental App-Server `additionalContext`
What: App-server clients can attach keyed context fragments to `turn/start` and `turn/steer` without making those fragments ordinary user messages.

Usage:
```json
{
  "method": "turn/start",
  "params": {
    "threadId": "thread_123",
    "input": [{"type": "text", "text": "Inspect this page", "textElements": []}],
    "additionalContext": {
      "browser_info": {
        "kind": "untrusted",
        "value": "Current tab: settings"
      }
    }
  }
}
```

Details:
- `kind` is either `untrusted` or `application`.
- The API is explicitly experimental through `turn/start.additionalContext` and `turn/steer.additionalContext`.
- Values are keyed by opaque client source identifiers, merged into thread state, deduplicated across retained turns, and truncated before model input when needed.

Code references:
- `AdditionalContextKind` and `AdditionalContextEntry` in `codex-rs/app-server-protocol/src/protocol/v2/turn.rs`
- `TurnStartParams::additional_context` in `codex-rs/app-server-protocol/src/protocol/v2/turn.rs`
- `TurnSteerParams::additional_context` in `codex-rs/app-server-protocol/src/protocol/v2/turn.rs`
- New schemas `codex-rs/app-server-protocol/schema/json/v2/TurnStartParams.json` and `codex-rs/app-server-protocol/schema/json/v2/TurnSteerParams.json`
- `AdditionalContextStore` in `codex-rs/core/src/state/additional_context.rs`


### Thread-Scoped MCP Server Status
What: `mcpServerStatus/list` now accepts an optional `threadId` so clients can inspect MCP servers using a loaded thread's project-local configuration.

Usage:
```json
{
  "method": "mcpServerStatus/list",
  "params": {
    "threadId": "thread_123",
    "detail": "toolsAndAuthOnly"
  }
}
```

Details:
- Without `threadId`, the method still reads the latest global MCP config directly.
- With `threadId`, the app-server resolves MCP inventory from that thread's config context, including trusted project-local `.codex/config.toml`.

Code references:
- `ListMcpServerStatusParams::thread_id` in `codex-rs/app-server-protocol/src/protocol/v2/mcp.rs`
- `codex-rs/app-server-protocol/schema/json/v2/ListMcpServerStatusParams.json`
- `mcp_server_status_list_uses_thread_project_local_config` in `codex-rs/app-server/tests/suite/v2/mcp_server_status.rs`
- App-server README entry for `mcpServerStatus/list` in `codex-rs/app-server/README.md`


### Restored `ImageDetail` Values
What: Protocol `ImageDetail` accepts `auto` and `low` again, in addition to `high` and `original`.

Usage:
```json
{
  "image_url": "data:image/png;base64,...",
  "detail": "auto"
}
```

Details:
- This is an additive protocol compatibility change for clients that still send OpenAI-style image detail values.
- Earlier changelogs showed `auto` and `low` being removed; this release restores them in generated JSON and TypeScript schemas.

Code references:
- `ImageDetail` enum schemas in `codex-rs/app-server-protocol/schema/json/ClientRequest.json`
- `ImageDetail` enum schemas in `codex-rs/app-server-protocol/schema/json/ServerNotification.json`
- `ImageDetail` TypeScript union in `codex-rs/app-server-protocol/schema/typescript/ImageDetail.ts`

### Noninteractive Standalone Update Instructions
Standalone update prompts now recommend noninteractive install commands, which is better for scripted or terminal-embedded update flows.

Usage:
```bash
curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh
```

Code references:
- `UpdateAction` install command text in `codex-rs/tui/src/update_action.rs`
- Standalone update history snapshots in `codex-rs/tui/src/history_cell/snapshots/`


### Feedback Reports Include Windows Sandbox Logs
Feedback uploads now include `windows-sandbox.log` when a Windows sandbox log exists, improving supportability for Windows sandbox failures.

Code references:
- `WINDOWS_SANDBOX_LOG_ATTACHMENT_FILENAME` in `codex-rs/feedback/src/lib.rs`
- `windows_sandbox_log_attachment` in `codex-rs/app-server/src/request_processors/feedback_processor.rs`
- Feedback consent UI handling in `codex-rs/tui/src/bottom_pane/feedback_view.rs`

## Bug Fixes

- Markdown tables render in app-style rows with better wrapping for long paths, URLs, and compact status/count columns (`TableState` and column classification in `codex-rs/tui/src/markdown_render.rs`).
- Multiline Markdown lists are separated more readably, especially wrapped nested items (`codex-rs/tui/src/markdown_render.rs` and `codex-rs/tui/src/markdown_render_tests.rs`).
- The TUI suppresses unmanaged stderr while it owns the terminal, preventing macOS diagnostics from corrupting the composer (`TerminalStderrGuard` in `codex-rs/tui/src/tui/terminal_stderr.rs`).
- Zellij raw-output insertion keeps raw output above the composer instead of overlapping the viewport (`TerminalHistoryStrategy` in `codex-rs/tui/src/insert_history.rs`).
- Older tmux/iTerm control-mode sessions avoid unsupported keyboard enhancement setup, preserving normal `Ctrl-C` handling (`tmux_should_enable_modify_other_keys_for` in `codex-rs/tui/src/tui/keyboard_modes.rs`).
- Slash-command completion preserves draft text for commands that accept inline arguments (`slash_input` handling in `codex-rs/tui/src/bottom_pane/chat_composer/slash_input.rs`).
- `$` app mentions filter out inaccessible or disabled apps instead of offering unusable suggestions (`codex-rs/tui/src/app/plugin_mentions.rs` and related app-list handling).
- Resume flows can include non-interactive exec sessions and respect cwd overrides for idle cached threads (`codex-rs/tui/src/resume_picker.rs` and `codex-rs/app-server/src/request_processors/thread_processor.rs`).

### Standalone Web Search [In Development]
What: Infrastructure was added for an extension-backed standalone web search tool that can replace the hosted `web_search` tool path.

Usage:
```toml
[features]
standalone_web_search = true
```

Status: Runtime-gated by the under-development feature key `standalone_web_search`; default is disabled.

Details:
- The new extension exposes a `web.run` namespace tool when enabled, OpenAI-backed, and web search mode is not disabled.
- Search requests go to `/api/codex/alpha/search` and return encrypted output back into the model conversation.
- The feature is not on by default.

Code references:
- `Feature::StandaloneWebSearch` in `codex-rs/features/src/lib.rs`
- `WebSearchExtension` in `codex-rs/ext/web-search/src/extension.rs`
- `WebSearchTool` in `codex-rs/ext/web-search/src/tool.rs`
- `standalone_web_search_round_trips_encrypted_output` in `codex-rs/app-server/tests/suite/v2/web_search.rs`


### Non-Prefixed MCP Tool Names [In Development]
What: Codex can now be configured to expose MCP model-visible namespaces without the legacy `mcp__` prefix.

Usage:
```toml
[features]
non_prefixed_mcp_tool_names = true
```

Status: Runtime-gated by the under-development feature key `non_prefixed_mcp_tool_names`; default is disabled.

Details:
- By default, Codex still prefixes MCP tool namespaces with `mcp__`.
- When the feature is enabled, `Config::prefix_mcp_tool_names` disables that legacy prefix behavior.
- The older trailing namespace suffix is not restored when legacy prefixing remains enabled.

Code references:
- `Feature::NonPrefixedMcpToolNames` in `codex-rs/features/src/lib.rs`
- `Config::prefix_mcp_tool_names` in `codex-rs/core/src/config/mod.rs`
- MCP naming mode plumbing in `codex-rs/codex-mcp/src/tools.rs`

## Notes

The provided diff is from `rust-v0.134.0` to `rust-v0.135.0`, inferred from the release tag and compare URL in the official notes.

If you previously set `zsh_path` in `config.toml` or inside a config profile, remove it for 0.135.0 packaged builds. The schema no longer exposes `zsh_path`; packaged builds discover the bundled patched zsh through `InstallContext::bundled_zsh_path`.

For app-server clients, the protocol changes are additive. Clients should update generated types for `AdditionalContextEntry`, `AdditionalContextKind`, `ListMcpServerStatusParams.threadId`, and the expanded `ImageDetail` union.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.135.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.135.0.md`
