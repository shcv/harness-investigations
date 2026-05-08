# Changelog for version 0.129.0

## Official Release Highlights

Codex 0.129.0 is a large TUI and app-server release from `rust-v0.128.0` to `rust-v0.129.0`. The published notes are accurate at the headline level: the diff verifies new Vim composer support, a redesigned resume picker, raw scrollback, `/ide`, `/hooks`, keymap debugging, plugin sharing APIs, plugin-management UI improvements, hook lifecycle expansion, goal polish, and multiple sandbox reliability fixes.

The official notes also correctly distinguish several items that are not brand-new protocol concepts. For example, `marketplace/remove` and `marketplace/upgrade` already existed in `rust-v0.128.0`; 0.129.0 wires them more fully into the TUI plugin workflows rather than introducing the RPC methods themselves.

## Summary

This release makes the interactive TUI more configurable and recoverable, especially for keyboard-heavy users: Vim composer mode, raw scrollback, richer session picking, `/ide`, `/hooks`, `/keymap debug`, and workspace-aware `/diff` all landed together. Plugin and hook workflows also moved forward with app-server sharing APIs, remote skill preview, hook trust/review surfaces, and new compaction hook events. The most important protocol addition beyond the official highlights is an experimental unsandboxed `process/*` app-server API for clients that need handle-based process control.

## New Features

### Vim Composer Mode

What: The TUI composer can now run in modal Vim mode, with normal/insert state, Vim motions, operators, and a visible mode indicator.

Usage:
```toml
[tui]
vim_mode_default = true

[tui.keymap.global]
toggle_vim_mode = "ctrl-v"

[tui.keymap.vim_normal]
move_left = "h"
move_down = "j"
move_up = "k"
move_right = "l"
```

Details:
- `/vim` toggles Vim mode from inside the TUI.
- `tui.vim_mode_default` starts the composer in Vim normal mode by default.
- New configurable keymap contexts cover `tui.keymap.vim_normal` and `tui.keymap.vim_operator`.
- Normal-mode commands include movement, insert/append/open-line actions, delete/yank operators, paste, and history navigation.
- This is verified absent from 0.128.0 for the config keys and composer implementation; 0.128.0 only had incidental references to the external `vim` editor and request-input Vim-style navigation.

Code references:
- `vim_mode_default` in `codex-rs/config/src/types.rs`
- `TuiVimNormalKeymap` and `TuiVimOperatorKeymap` in `codex-rs/config/src/tui_keymap.rs`
- `SlashCommand::Vim` in `codex-rs/tui/src/slash_command.rs`
- `ChatComposer::set_vim_enabled` and Vim handling in `codex-rs/tui/src/bottom_pane/chat_composer.rs`
- `TextArea::handle_vim_input` in `codex-rs/tui/src/bottom_pane/textarea.rs`


### Raw Scrollback Mode

What: The TUI can switch into raw scrollback mode so transcript text is easier to select and copy with the terminal.

Usage:
```text
/raw
```

or as config:
```toml
[tui]
raw_output_mode = true

[tui.keymap.global]
toggle_raw_output = "alt-r"
```

Details:
- `/raw` toggles the mode during a session.
- `tui.raw_output_mode` can start the TUI in this mode.
- `toggle_raw_output` is a new global keymap action.
- This is new relative to 0.128.0; the `SlashCommand::Raw` and `raw_output_mode` surfaces are not present in the previous tag.

Code references:
- `raw_output_mode` in `codex-rs/config/src/types.rs`
- `SlashCommand::Raw` in `codex-rs/tui/src/slash_command.rs`
- `toggle_raw_output` in `codex-rs/config/src/tui_keymap.rs`
- Raw-mode rendering snapshots under `codex-rs/tui/src/snapshots/`


### Redesigned Resume And Fork Picker

What: Resume/fork session selection now uses a dedicated picker with search, sort/filter controls, compact/expanded rows, workspace filtering, and lazy transcript previews.

Usage:
```bash
codex resume
```

Details:
- The picker lists app-server threads with session metadata before transcript preview.
- Users can search, change sort/filter controls, and expand a selected session with `Ctrl+E`.
- Workspace-aware filtering uses current working directory metadata so users can resume the right project more easily.
- This is new TUI structure in 0.129.0; `SessionPickerLaunchContext` and `resume_picker` are absent from 0.128.0.

Code references:
- `SessionPickerLaunchContext` in `codex-rs/tui/src/resume_picker.rs`
- `resume_picker::transcript` in `codex-rs/tui/src/resume_picker/transcript.rs`
- `session_resume` coordination in `codex-rs/tui/src/session_resume.rs`
- `ThreadListCwdFilter` protocol usage in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`


### IDE Context Injection

What: The TUI can inject IDE context, such as selected text and open files, into the current prompt.

Usage:
```text
/ide
```

Details:
- The slash command description is “include current selection, open files, and other context from your IDE.”
- The implementation adds an `ide_context` module with IPC, prompt formatting, and Windows named-pipe support.
- This is new relative to 0.128.0; the `/ide` slash command and `tui/src/ide_context` implementation are absent from the previous tag.

Code references:
- `SlashCommand::Ide` in `codex-rs/tui/src/slash_command.rs`
- `codex-rs/tui/src/ide_context.rs`
- `codex-rs/tui/src/ide_context/ipc.rs`
- `codex-rs/tui/src/ide_context/prompt.rs`
- `codex-rs/tui/src/ide_context/windows_pipe.rs`


### Hooks Browser And Hook Review Controls

What: `/hooks` opens an interactive browser for lifecycle hooks, including event categories, handler details, review/trust status, and toggles.

Usage:
```text
/hooks
```

Details:
- The slash command description is “view and manage lifecycle hooks.”
- Startup warnings now tell users to open `/hooks` when hooks need review.
- The browser displays hook events, handler commands, sources, managed status, current hashes, trust status, and review-needed counts.
- This is new TUI functionality in 0.129.0; `hooks/list` already existed in 0.128.0, but `/hooks` and `hooks_browser_view` did not.

Code references:
- `SlashCommand::Hooks` in `codex-rs/tui/src/slash_command.rs`
- `HooksBrowserView` in `codex-rs/tui/src/bottom_pane/hooks_browser_view.rs`
- `HookTrustStatus` and `HookMetadata` in `codex-rs/app-server-protocol/src/protocol/v2/hook.rs`
- `fetch_hooks_list` in `codex-rs/tui/src/app/background_requests.rs`


### Plugin Sharing And Remote Skill Preview APIs

What: App-server clients can create, update, list, and delete plugin shares, and can read a remote plugin skill without installing the plugin bundle.

Usage:
```json
{"method":"plugin/share/save","params":{"pluginPath":"/absolute/path/to/plugin","discoverability":"private","shareTargets":[]}}
```

```json
{"method":"plugin/share/updateTargets","params":{"remotePluginId":"plugin_123","shareTargets":[]}}
```

```json
{"method":"plugin/share/list","params":{}}
```

```json
{"method":"plugin/share/delete","params":{"remotePluginId":"plugin_123"}}
```

```json
{"method":"plugin/skill/read","params":{"remoteMarketplaceName":"openai-curated","remotePluginId":"plugin_123","skillName":"example"}}
```

Details:
- These RPC methods are new in 0.129.0 and absent from 0.128.0.
- `plugin/share/save` returns `remotePluginId` and `shareUrl`.
- `plugin/share/list` returns shared plugin records including the local plugin path when known.
- `plugin/skill/read` returns remote skill markdown contents or `null`.
- Share creation supports discoverability and target principals; updating targets is a separate method.

Code references:
- `PluginShareSaveParams`, `PluginShareUpdateTargetsParams`, `PluginShareListParams`, `PluginShareDeleteParams`, and `PluginSkillReadParams` in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`
- JSON-RPC method strings in `codex-rs/app-server-protocol/src/protocol/common.rs`
- Schemas under `codex-rs/app-server-protocol/schema/json/v2/PluginShare*.json`
- Schemas `codex-rs/app-server-protocol/schema/json/v2/PluginSkillReadParams.json` and `PluginSkillReadResponse.json`
- Implementations in `codex-rs/app-server/src/request_processors/plugins.rs`


### Compaction Hooks

What: Hooks can now run before and after context compaction.

Usage:
```toml
[[hooks.PreCompact]]
command = "python3 ./hooks/pre-compact.py"

[[hooks.PostCompact]]
command = "python3 ./hooks/post-compact.py"
```

Details:
- 0.129.0 adds `PreCompact` and `PostCompact` to hook configuration and protocol enum surfaces.
- The TUI hooks browser describes these as “Before context compaction” and “After context compaction.”
- 0.128.0 hook events were `PreToolUse`, `PermissionRequest`, `PostToolUse`, `SessionStart`, `UserPromptSubmit`, and `Stop`; `PreCompact` and `PostCompact` were absent.

Code references:
- `HookEventName::{PreCompact, PostCompact}` in `codex-rs/app-server-protocol/src/protocol/v2/hook.rs`
- `ConfiguredHookMatcherGroup` fields in `codex-rs/config/src/hook_config.rs`
- `run_pre_compact_hooks` and `run_post_compact_hooks` in `codex-rs/core/src/hook_runtime.rs`
- Compaction integration in `codex-rs/core/src/compact.rs` and `codex-rs/core/src/compact_remote.rs`
- Schema updates in `codex-rs/app-server-protocol/schema/json/v2/ConfigRequirementsReadResponse.json`


### Keymap Editor And Debug Inspector

What: `/keymap` now exposes more configurable shortcuts, and `/keymap debug` helps users see which key events Codex receives from their terminal.

Usage:
```text
/keymap
/keymap debug
```

Details:
- New global actions include `toggle_vim_mode` and `toggle_raw_output`.
- The picker now shows action names, descriptions, current bindings, defaults, and whether a shortcut is custom.
- The debug view reports the detected key, the config key string, the raw terminal event, and matching actions.
- This helps users diagnose terminals that do not send a key at all, which is especially relevant for Alt/Shift/modified keys.

Code references:
- `KEYMAP_ACTIONS` in `codex-rs/tui/src/keymap_setup/actions.rs`
- `KeymapDebugView` in `codex-rs/tui/src/keymap_setup/debug.rs`
- `TuiGlobalKeymap::toggle_vim_mode` and `toggle_raw_output` in `codex-rs/config/src/tui_keymap.rs`
- `SlashCommand::Keymap` in `codex-rs/tui/src/slash_command.rs`


### Windows Sandbox Readiness RPC

What: App-server clients can query whether the Windows sandbox is ready, not configured, or needs an update.

Usage:
```json
{"method":"windowsSandbox/readiness","params":null}
```

Details:
- This RPC is new in 0.129.0 and absent from 0.128.0.
- The response status is one of `ready`, `notConfigured`, or `updateRequired`.
- It complements the existing `windowsSandbox/setupStart` flow by letting clients check setup state before prompting users to run setup again.

Code references:
- `WindowsSandboxReadiness` and `WindowsSandboxReadinessResponse` in `codex-rs/app-server-protocol/src/protocol/v2/windows_sandbox.rs`
- JSON-RPC method string `windowsSandbox/readiness` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- Schema `codex-rs/app-server-protocol/schema/json/v2/WindowsSandboxReadinessResponse.json`
- `windows_sandbox_readiness` and `determine_windows_sandbox_readiness` in `codex-rs/app-server/src/request_processors/windows_sandbox_processor.rs`

## Improvements

### Plugin Management In The TUI

Plugin management now has richer marketplace workflows: marketplace removal, marketplace upgrade loading/results, newly installed marketplace states, admin-disabled remote plugin status, source filtering, remote bundle sync, and local shared-path tracking. The `marketplace/remove` and `marketplace/upgrade` RPC methods existed in 0.128.0, so the user-facing change in 0.129.0 is the broader TUI integration and status handling rather than new RPC availability.

Code references: `PluginPopup` marketplace handlers in `codex-rs/tui/src/chatwidget/plugins.rs`, `AppEvent::MarketplaceUpgradeLoaded` and `AppEvent::MarketplaceRemoveLoaded` in `codex-rs/tui/src/app_event.rs`, `MarketplaceUpgradeParams` and `MarketplaceRemoveParams` in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`


### Workspace-Aware Diff

`/diff` now routes through workspace commands rather than assuming local process execution. This matters for remote or embedded app-server sessions because the command runs against the active workspace boundary.

Code references: `WorkspaceCommand`, `WorkspaceCommandExecutor`, and `AppServerWorkspaceCommandRunner` in `codex-rs/tui/src/workspace_command.rs`; `get_git_diff` integration in `codex-rs/tui/src/get_git_diff.rs`


### Theme-Aware Status Line And PR Summaries

The status line now uses terminal/theme palette information and can include PR and branch-change summaries. This improves readability across terminal themes and surfaces repository status without requiring a separate command.

Code references: `terminal_palette` and `terminal_probe` in `codex-rs/tui/src/terminal_palette.rs` and `codex-rs/tui/src/terminal_probe.rs`; status rendering in `codex-rs/tui/src/status/card.rs` and `codex-rs/tui/src/status_indicator_widget.rs`


### Goal Mode Polish [Experimental]

Experimental goals remain marked as experimental, but the TUI now validates oversized objectives, preserves paused goals across resume unless explicitly re-enabled, and formats multi-day goal durations more clearly.

Code references: experimental `thread/goal/*` methods in `codex-rs/app-server-protocol/src/protocol/common.rs`; goal runtime behavior in `codex-rs/core/src/goals.rs`; TUI goal validation in `codex-rs/tui/src/chatwidget/tests/goal_validation.rs`; display formatting in `codex-rs/tui/src/goal_display.rs`


### Hook Metadata And Trust Reporting

Hook list responses now carry stronger metadata for review workflows, including current hashes and trust status. This supports the `/hooks` browser and startup warnings for hooks that need review.

Code references: `HookMetadata` and `HookTrustStatus` in `codex-rs/app-server-protocol/src/protocol/v2/hook.rs`; `HooksBrowserView::review_needed_count` in `codex-rs/tui/src/bottom_pane/hooks_browser_view.rs`


### Thread And Turn Protocol Cleanup

The app-server protocol was split into more focused modules, and thread history/turn item handling moved toward the thread store. Most of this is internal, but client authors will notice schema/module churn and more consistent thread/turn response shapes.

Code references: protocol modules under `codex-rs/app-server-protocol/src/protocol/v2/`; `thread_history` in `codex-rs/app-server-protocol/src/protocol/thread_history.rs`; thread store usage in `codex-rs/app-server/src/request_processors/threads.rs`

## Bug Fixes

- `/copy` now works better inside tmux without relying on tmux passthrough behavior (`copy_response` handling in `codex-rs/tui/src/clipboard_copy.rs`).
- Alt+Enter newline handling and modified Backspace/Delete keys were restored or normalized for terminals that report enhanced keyboard events (`codex-rs/tui/src/keymap.rs`, `codex-rs/tui/src/custom_terminal.rs`).
- Large-paste placeholders and Ctrl+C-stashed drafts preserve draft history more reliably (`codex-rs/tui/src/bottom_pane/chat_composer.rs`).
- TUI startup terminal probes are bounded so unsupported terminals do not hang startup indefinitely (`DEFAULT_STARTUP_PROBE_TIMEOUT` and probe helpers in `codex-rs/tui/src/terminal_probe.rs`).
- `animations = false` is honored more consistently for live rows and screen-reader-friendly rendering (`tui.animations` in `codex-rs/config/src/types.rs`; TUI status/live-row rendering in `codex-rs/tui/src/chatwidget/status_surfaces.rs`).
- Linux sandbox startup handles older or unusable system `bwrap`, bounded mount probes, symlink-protected paths, and shared `/tmp` setups more reliably (`codex-rs/linux-sandbox/src/` and bundled `codex-rs/bwrap` crate).
- Windows sandbox execution handles named-pipe access, ConPTY teardown, PowerShell-wrapped allow rules, Git `safe.directory`, and unsafe Git option filtering more reliably (`codex-rs/windows-sandbox-rs/src/conpty/mod.rs`, `codex-rs/windows-sandbox-rs/src/elevated/command_runner_win.rs`, `codex-rs/windows-sandbox-rs/src/sandbox_utils.rs`).
- Custom CA login works better behind TLS-inspecting proxies (`codex-rs/login/src/` and rustls provider integration).
- `/status` reports the Bedrock runtime endpoint correctly instead of showing the configured base URL in cases where that is not the runtime endpoint (`format_model_provider` in `codex-rs/tui/src/status/card.rs`).
- Dangerous project-level config keys are ignored rather than applied from project config (`ConfigBuilder` and config requirement handling in `codex-rs/config/src/`).
- Heredoc redirect approval matching handles file redirects more accurately (`codex-rs/execpolicy/src/`).
- Large MCP tool outputs and hook outputs are truncated or spilled so they do not grow unbounded in rollouts or context (`codex-rs/core/src/` hook and MCP output handling).

## In Development

### Unsandboxed Process Control RPC [Experimental]

What: App-server clients can spawn and control standalone unsandboxed processes using a handle-based `process/*` protocol.

Status: Runtime-gated by app-server experimental API capability. The app-server README says clients must initialize with `capabilities.experimentalApi: true`.

Usage:
```json
{"method":"process/spawn","params":{"command":["bash","-lc","printf hello"],"processHandle":"proc-1","cwd":"/repo","streamStdoutStderr":true}}
```

```json
{"method":"process/writeStdin","params":{"processHandle":"proc-1","deltaBase64":"aGVsbG8K","closeStdin":true}}
```

```json
{"method":"process/resizePty","params":{"processHandle":"proc-1","size":{"rows":40,"cols":120}}}
```

```json
{"method":"process/kill","params":{"processHandle":"proc-1"}}
```

Details:
- The API is new in 0.129.0 and absent from 0.128.0.
- `process/spawn` returns after the process starts, not after it exits.
- Output can stream through `process/outputDelta`; completion is reported through `process/exited`.
- The API is intentionally unsandboxed and does not expose sandbox-selection fields such as `sandboxPolicy` or `permissionProfile`.
- PTY mode implies stdin/stdout streaming and supports resize by handle.

Code references:
- `ProcessSpawnParams`, `ProcessWriteStdinParams`, `ProcessKillParams`, `ProcessResizePtyParams`, `ProcessOutputDeltaNotification`, and `ProcessExitedNotification` in `codex-rs/app-server-protocol/src/protocol/v2/process.rs`
- Experimental method declarations in `codex-rs/app-server-protocol/src/protocol/common.rs`
- Schemas `codex-rs/app-server-protocol/schema/json/v2/ProcessOutputDeltaNotification.json` and `ProcessExitedNotification.json`
- Implementation in `codex-rs/app-server/src/request_processors/process_exec_processor.rs`
- Usage documentation in `codex-rs/app-server/README.md`


### Memory MCP Server [Experimental]

What: 0.129.0 adds a built-in memories MCP crate and related list/read/search improvements.

Status: In development. The diff shows a new `codex-memories-mcp` workspace member and `codex-builtin-mcps` wiring, but this is not presented as a normal end-user CLI command in the release notes.

Details:
- The official changelog lists memory MCP work such as schema generation, paginated list/search, multi-query search, line offsets, `max_lines`, context lines, normalized matching, and symlink/dot-path protections.
- This looks like infrastructure for built-in MCP-backed memory tools rather than a broadly documented stable user feature.

Code references:
- Workspace member `memories/mcp` in `codex-rs/Cargo.toml`
- `codex-builtin-mcps` package in `codex-rs/builtin-mcps/`
- Memory MCP crate under `codex-rs/memories/mcp/`

## Notes

The diff and source verification show no broad migration requirement for ordinary CLI users. Client authors should treat the new `plugin/share/*`, `plugin/skill/read`, and `windowsSandbox/readiness` methods as additive v2 protocol surface, and should treat `process/*` as experimental until the `experimentalApi` capability requirement is removed or documented as stable.

The official notes mention marketplace removal and upgrade as plugin-management improvements, but the `marketplace/remove` and `marketplace/upgrade` RPC methods themselves were already present in `rust-v0.128.0`; update client documentation accordingly if it previously labeled those two RPC methods as new in 0.129.0.

---

Generated with:
- tool: `harness-investigations@cc606f8-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/codex/changes/changes-v0.129.0-2.diff` (filtered astdiff)
- official release notes: `archive/codex/changes/release-notes-v0.129.0.md`
