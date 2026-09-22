# Changelog for version 0.156.0

## Release Status

> **Not yet released:** `rust-v0.156.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.155.1, this snapshot adds fullscreen transcript navigation, account usage analytics, per-thread plugin controls, provider gateway OAuth, and more control over background-server operation. Existing worktree and voice features become enabled by default, while `thread/rollback` and personality selection are retired.

This describes the `rust-v0.156.0` source tag. No published GitHub Release was found when synchronization ran; this is an intermediate/development snapshot, not confirmation that release binaries or assets were published.

## New Features


### Fullscreen transcript mode

What: Codex can own the fullscreen conversation view, providing transcript scrolling, searching, selection, copying, and activity inspection.

Usage:

```toml
[tui]
fullscreen_transcript = true
```

Alternatively, enter `/tui`, select Fullscreen, and restart Codex.

Details:

- Fullscreen mode is off by default. `/tui` saves the preference for the next launch.
- Default shortcuts include F3 for transcript search and F4 for activity inspection. These actions are configurable through `tui.keymap.global.find_transcript` and `focus_activity`.
- Transcript and composer selections support mouse interaction and right-click copying.
- Transcript links support ordinary clicks.
- `--no-alt-screen` and other alternate-screen restrictions take precedence.

Code references:

- `Tui::fullscreen_transcript` in `codex-rs/config/src/types.rs`
- `App::save_fullscreen_transcript` in `codex-rs/tui/src/app/tui_mode_picker.rs`
- `codex-rs/tui/src/transcript_view.rs` and `codex-rs/tui/src/transcript_view/search.rs`
- Default bindings in `codex-rs/tui/src/keymap.rs`


### Mermaid diagrams and Unicode math

What: Supported Mermaid diagrams and TeX-style mathematics can render directly in the terminal.

Usage:

```toml
[tui.rendering]
mermaid = true
math = true
tables = true
```

Details:

- The three rendering preferences default to `true` and operate independently of animation settings.
- Mermaid previews appear after a code fence closes. Unsupported syntax, rendering limits, or insufficient terminal space preserve the original code block.
- Math rendering covers inline and standalone display expressions, including supported symbols, accents, and delimiters.
- Setting an option to `false` preserves source presentation for that content type.
- Table rendering already existed; its independent configuration switch is new.

Code references:

- `TuiRendering` in `codex-rs/config/src/tui_rendering.rs`
- `render` and `has_closing_fence` in `codex-rs/tui/src/markdown_render/mermaid.rs`
- `codex-rs/tui/src/markdown_render/math.rs`


### Individual visual-effect controls

What: Separate settings now control decorative animation without disabling the underlying activity.

Usage:

```toml
[tui]
animations = true

[tui.effects]
starfield = false
shimmer = false
welcome = false
effort = true
progress = true
title = false
```

Details:

- The effects control composer stars, shimmering text, welcome artwork, reasoning-effort transitions, progress animation, and the terminal-title attention indicator.
- Each effect defaults to enabled but remains subordinate to the animation master switch.
- Effective animation settings also respect the host’s reduced-motion preference.
- Screen-reader detection defaults animations off unless the user has explicitly configured them.

Code references:

- `TuiEffects` in `codex-rs/config/src/tui_effects.rs`
- `LocalSettings::with_accessibility_preferences` in `codex-rs/tui/src/local_settings.rs`
- `codex-rs/tui/src/screen_reader.rs` and `codex-rs/tui/src/system_motion.rs`


### Account analytics dashboard

What: The existing `/usage` menu gains an authenticated dashboard for account usage history.

Usage:

```text
/usage
```

Choose **View analytics**.

Details:

- Available reports depend on the authenticated account and backend support. Views include an account summary, usage, activity, plugins, skills, credits, and top chats.
- Supported reports offer seven-day and thirty-day ranges, grouping controls, and detailed views.
- Keyboard help and mouse navigation are available.
- Account changes invalidate account-owned report data.
- Historical five-hour and weekly allowance reporting has a separate experimental flag described below.

Code references:

- `ChatWidget::usage_menu_params` in `codex-rs/tui/src/chatwidget/usage.rs`
- `AnalyticsView` in `codex-rs/tui/src/analytics.rs`
- `AnalyticsView::visible_sections` in `codex-rs/tui/src/analytics/sections.rs`
- `AnalyticsSession` in `codex-rs/backend-client/src/analytics_session.rs`


### Retained warnings viewer

What: `/warnings` opens retained warnings and diagnostic details, making startup and runtime issues easier to revisit.

Usage:

```text
/warnings
```

Details:

- A warning footer makes retained issues discoverable.
- Configuration loading now warns about unrecognized settings, including their source and setting names.
- Quota warnings remain visible instead of disappearing among routine activity.

Code references:

- `SlashCommand::Warnings` in `codex-rs/tui/src/slash_command.rs`
- `codex-rs/tui/src/bottom_pane/warnings_view.rs`
- `codex-rs/tui/src/app/startup_warnings.rs`
- `ignored_config_warning` in `codex-rs/config/src/strict_config.rs`


### Explicit background-server bypass

What: `--no-daemon` runs the interactive CLI without using the shared background server, even when one is already running.

Usage:

```bash
codex --no-daemon
codex resume --last --no-daemon
codex fork --last --no-daemon
```

Details:

- The option applies to interactive launches, including resume and fork.
- It cannot be combined with `--remote`.
- `codex agents --no-daemon` is rejected because the agents overview requires a shared server.

Code references:

- `Cli::no_daemon` in `codex-rs/tui/src/cli.rs`
- `run_interactive_tui` and `merge_interactive_cli_flags` in `codex-rs/cli/src/main.rs`


### Local daemon management menu

What: `/daemon` provides an interactive way to update the local background server or replace it with the invoking CLI’s package.

Usage:

```text
/daemon
```

The equivalent package-replacement command is:

```bash
codex app-server daemon update --from-cli
```

Details:

- The menu offers the latest public stable version or the current CLI package.
- `--from-cli` copies the complete package and pins it against automatic updates. A bare executable is insufficient.
- Add `--yes` to confirm package replacement non-interactively.
- The TUI asks for confirmation, exits to perform the update, and asks the user to relaunch afterward.
- Updating a running daemon can interrupt active or queued work. Remote servers must be managed on their host.

Code references:

- `AppServerDaemonSubcommand::Update` in `codex-rs/cli/src/main.rs`
- `App::open_daemon_menu` and `confirm_daemon_update` in `codex-rs/tui/src/app/daemon_menu.rs`
- `InstallRequest` and `update_from_cli` in `codex-rs/app-server-daemon/src/prepare_install.rs`


### Per-thread plugin exclusions

What: App-server clients can save a thread-specific list of disabled plugins.

Usage:

```json
{
  "method": "turn/start",
  "params": {
    "threadId": "THREAD_ID",
    "disabledPluginIds": ["example-plugin@example-marketplace"],
    "input": [
      {
        "type": "text",
        "text": "Continue with this plugin disabled.",
        "textElements": []
      }
    ]
  }
}
```

Details:

- IDs use the values returned by `plugin/list`.
- A supplied list replaces the selection; omission or `null` preserves it, and `[]` clears it.
- The selection is returned by thread start, resume, and fork responses.
- Runtime filtering covers plugin contributions, including MCP capabilities and hooks. Some protocol comments still say filtering is not implemented; the runtime code does apply it.
- The existing experimental `thread/settings/update` method also accepts the list.
- Changes take effect through the admitted turn’s plugin selection.

Code references:

- `TurnStartParams::disabled_plugin_ids` in `codex-rs/app-server-protocol/src/protocol/v2/turn.rs`
- `ThreadSettingsUpdateParams` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- `Session::activate_plugin_selection` in `codex-rs/core/src/session/plugin_selection.rs`
- Plugin filtering in `codex-rs/core/src/mcp.rs`
- Updated schema: `codex-rs/app-server-protocol/schema/json/v2/TurnStartParams.json`


### Per-app tool exposure settings

What: Individual connectors can now omit their tools from selected model-facing surfaces.

Usage:

```toml
[apps.example_connector]
omit_tools_from = ["code_mode", "direct"]
```

Details:

- Supported values are `code_mode`, `direct`, and `deferred`.
- Connector-level omissions combine with server-level omissions.
- An empty list clears connector-level omissions.
- This controls tool exposure; it is distinct from disabling the connector.

Code references:

- `AppConfig::omit_tools_from` in `codex-rs/config/src/types.rs`
- `ToolExposureSurface` in `codex-rs/protocol/src/config_types.rs`
- App-server `AppConfig` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`


### Gateway OAuth alongside provider authentication

What: A model provider can require a separate OAuth credential for its gateway while retaining primary provider authentication.

Usage:

```toml
model_provider = "corporate"

[model_providers.corporate]
name = "Corporate gateway"
base_url = "https://gateway.example.com/v1"
env_key = "OPENAI_API_KEY"
wire_api = "responses"

[model_providers.corporate.gateway_oauth]
authorization_url = "https://identity.example.com/authorize"
token_url = "https://identity.example.com/token"
client_id = "codex-client"
scopes = ["gateway.access"]
delivery = { kind = "header", name = "X-Gateway-Authorization" }
```

Details:

- Gateway credentials can be delivered through a custom header or named cookie.
- The credential manager supports browser authorization, token refresh, and separate encrypted storage.
- Gateway authentication is composed with primary authentication for provider requests and model discovery.
- URLs require HTTPS, except for loopback HTTP.
- Reserved authentication headers and conflicting configured headers are rejected.
- This configuration cannot be combined with AWS/Bedrock authentication.

Code references:

- `GatewayOAuthConfig` and `GatewayOAuthDelivery` in `codex-rs/model-provider-info/src/gateway_oauth.rs`
- `GatewayAuthManager` in `codex-rs/login/src/gateway_auth.rs`
- `compose_auth` in `codex-rs/model-provider/src/combined_auth.rs`


### Explicit provider model-catalog URLs

What: Providers can specify a dedicated URL for Codex-native model discovery independently of their inference endpoint.

Usage:

```toml
[model_providers.corporate]
name = "Corporate gateway"
base_url = "https://gateway.example.com/v1"
env_key = "OPENAI_API_KEY"
wire_api = "responses"
model_catalog_url = "https://gateway.example.com/codex/models"
```

Details:

- The endpoint must return the Codex-native model catalog, rather than an arbitrary `/v1/models` response.
- Catalog requests use provider authentication, including configured gateway OAuth.
- Explicit catalog URLs receive bounded response handling and redacted failure diagnostics.
- Provider/catalog identity includes the configured catalog URL.

Code references:

- `ModelProviderInfo::model_catalog_url` in `codex-rs/model-provider-info/src/lib.rs`
- `OpenAiModelsEndpoint::list_models` in `codex-rs/model-provider/src/models_endpoint.rs`
- `ModelsClient::catalog_request_url` in `codex-rs/codex-api/src/endpoint/models.rs`


### Post-response context compaction

What: An optional threshold lets Codex compact context after finishing a response.

Usage:

```toml
model_post_turn_compact_threshold_percent = 80
```

Details:

- Valid values are 0–100; omission or zero disables this behavior.
- The threshold uses the usable context window, while existing automatic-compaction limits continue to apply.
- Post-response compaction is skipped when input is pending, cancellation is active, or token-budget mode is enabled.
- Ordinary compaction failures preserve the completed response.

Code references:

- `ConfigToml::model_post_turn_compact_threshold_percent` in `codex-rs/config/src/config_toml.rs`
- `context_window_token_status_with_config` in `codex-rs/core/src/session/context_window.rs`
- Post-turn compaction in `run_turn`, `codex-rs/core/src/session/turn.rs`


### Managed model-provider requirements

What: Administrators can require a specific provider and complete provider definitions through managed requirements.

Usage, in managed requirements:

```toml
model_provider = "corporate"

[model_providers.corporate]
name = "Corporate gateway"
base_url = "https://gateway.example.com/v1"
env_key = "OPENAI_API_KEY"
wire_api = "responses"
```

Details:

- Required provider selection overrides local and session configuration.
- Required provider definitions replace corresponding configured definitions rather than partially merging them.
- Existing threads are checked before accepting relevant new work when managed requirements change.
- `model/list` and background catalog refreshes also recheck current requirements, including when a catalog is cached.
- Clients can inspect effective provider requirements and `allowedLoginMethods` through `configRequirements/read`.

Code references:

- `ConfigRequirementsToml` in `codex-rs/config/src/config_requirements.rs`
- `ConfigManager` in `codex-rs/app-server/src/config_manager.rs`
- `codex-rs/app-server/src/model_catalog.rs`
- `ConfigRequirements` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`
- Updated schema: `codex-rs/app-server-protocol/schema/json/v2/ConfigRequirementsReadResponse.json`


### Standalone network-policy proxy

What: The source adds a `codex-network-proxy` executable that runs from a standalone JSON configuration.

Usage:

```bash
codex-network-proxy --config /path/to/network-proxy.json
```

Details:

- The file contains a `network` object and must set `network.enabled` to `true`.
- Unknown configuration fields are rejected.
- Limited mode and configured MITM hooks enable the required interception behavior.
- The standalone configuration is static; it does not automatically reload changed files.
- This is a source-level executable addition, not a claim that a separately distributed binary was published.

Code references:

- `Args`, `StandaloneConfig`, and `parse_standalone_config` in `codex-rs/network-proxy/src/main.rs`

## Improvements


### Worktrees enabled by default

The existing worktree feature is now stable and enabled by default. Use `/worktree` for an isolated conversation; the agents command center also supports creating a worktree session from the project’s default branch.

Code references: `Feature::Worktrees` in `codex-rs/features/src/lib.rs`; `TuiAgentsKeymap::new_worktree` in `codex-rs/config/src/tui_keymap.rs`; default-branch resolution in `codex-rs/worktree/src/git.rs`.


### Voice enabled by default, with voice selection

Voice conversations no longer require enabling the experimental feature first. Use `/voice` or the default F8 shortcut to toggle a conversation, and `/voice settings` to choose the voice for subsequent conversations.

Voice selection does not interrupt an active conversation. Actual availability still depends on the voice service and supported local audio runtime.

Code references: `Feature::RealtimeConversation` in `codex-rs/features/src/lib.rs`; `ChatWidget::open_realtime_settings` in `codex-rs/tui/src/chatwidget/realtime_settings.rs`; `toggle_voice` in `codex-rs/tui/src/keymap.rs`.


### Expanded agent command center

The existing `/agents` view gains status filters, model grouping, task token and usage information, improved metadata editing, and Markdown task details. Tasks managed elsewhere can open as read-only history.

Default shortcuts include `n` for a session in the selected checkout and `w` for a new worktree session. Startup loading is limited to ten recent sessions, reducing initial work.

Code references: `App::open_agents_overview` and `attach_agents_overview_thread` in `codex-rs/tui/src/app/agents_overview.rs`; `codex-rs/tui/src/app/agents_overview_view.rs`; agent bindings in `codex-rs/tui/src/keymap.rs`.


### Session-only model selection

The `/model` picker can apply a model and reasoning choice only to the current session. Use its `s` action to avoid changing durable defaults.

The TUI also uses catalog display names more consistently. New TUI threads default reasoning summaries to off unless configured otherwise.

Code references: `ChatWidget::session_model_selection_action` in `codex-rs/tui/src/chatwidget/session_model_selection.rs`; `new_thread_reasoning_overrides` in `codex-rs/tui/src/app_server_session.rs`.


### Six additional terminal themes

The theme picker adds `ada`, `babbage`, `curie`, `cushman`, `dali`, and `davinci`. Theme colors also apply more consistently to accents, inline code, and file paths.

Code references: `THEMES` and `resolve` in `codex-rs/tui/src/render/model_themes.rs`; `codex-rs/tui/src/theme_picker.rs`.


### More flexible daemon installation and recovery

New daemon installations own a complete package under `CODEX_HOME/packages/app-server-daemon`. A missing installation can be seeded from a complete local CLI package instead of requiring the standalone CLI installation.

Existing daemon installations remain selected until explicitly replaced. `codex app-server daemon update` can return pinned or local managed packages to the latest stable update path while preserving the automatic-update preference. Eligible interrupted local work can continue after managed daemon restarts.

Code references: `codex-rs/app-server-daemon/src/managed_install.rs`, `prepare_install.rs`, and `manual_update.rs`; `RecoverySnapshot` and `InterruptedTurn` in `codex-rs/app-server-transport/src/daemon_recovery.rs`.


### MCP OAuth without automatically opening a browser

The existing MCP login command accepts `--no-browser`:

```bash
codex mcp login example-server --no-browser
```

It prints the authorization URL and accepts the full callback URL, making authentication practical when the browser is on another machine. The callback listener can still complete the flow when reachable.

Code references: `LoginArgs::no_browser` in `codex-rs/cli/src/mcp_cmd.rs`; `McpLoginMode` in `codex-rs/cli/src/mcp_login.rs`; `codex-rs/rmcp-client/src/oauth_callback_input.rs`.


### Portable image references and forked attachments

Image inputs can carry a file ID instead of an inline URL:

```json
{
  "method": "turn/start",
  "params": {
    "threadId": "THREAD_ID",
    "input": [{"type": "image", "fileId": "FILE_ID"}]
  }
}
```

The ID must identify an image supported by the backing attachment service; arbitrary local filenames are not file IDs. Existing URL-based image inputs remain supported.

Local TUI images can be prepared as portable attachments for remote app servers. Non-ephemeral forks also copy the source thread’s current attachment membership, with independent attachment IDs; a copy failure is logged without failing the conversation fork.

Code references: `ImageReference` in `codex-rs/app-server-protocol/src/protocol/v2/turn.rs`; `AttachmentStore` in `codex-rs/attachment-store/src/lib.rs`; `codex-rs/state/src/runtime/thread_attachments.rs`; updated `TurnStartParams.json` schema.


### Richer app-server discovery and tool presentation

Several existing responses gain information clients can use directly:

| Surface | Added information |
|---|---|
| `mcpServerStatus/list` | `serverCapabilities` from the initialized MCP connection, or `null` when unavailable |
| MCP tool-call items | `mcpAppUi`, including a resource URI and preferred inline/fullscreen display mode |
| `model/list` | `availableAccessPrograms`, including caller-specific accepted cyber selections |
| `plugin/read` | `onboardingSkill` when the declared skill is enabled and visible |
| `thread/resume` | Effective `collaborationMode` |

MCP App UI presentation survives saved-history replay, so clients need not wait for a fresh tool catalog to render known widget metadata.

Code references: `McpServerStatus`, `ThreadItem`, `Model`, `PluginDetail`, and `ThreadResumeResponse` in `codex-rs/app-server-protocol/src/protocol/v2/{mcp,item,model,plugin,thread}.rs`; corresponding updated response schemas under `codex-rs/app-server-protocol/schema/json/v2/`.


### Better network bootstrap and diagnostics

Eligible login and startup requests can retry through the system proxy after normal routing fails. This fallback defaults to enabled and can be disabled with:

```toml
[features]
system_proxy_fallback = false
```

`codex doctor` also gains bounded filesystem-path diagnostics. It reports path-resolution problems without claiming to test read/write access, skips probes under read restrictions and on Windows, and avoids exposing configuration values in configuration-error output.

Code references: `Feature::SystemProxyFallback` in `codex-rs/features/src/lib.rs`; `resolve_bootstrap_http_client_factory` in `codex-rs/core/src/config/mod.rs`; `check` in `codex-rs/cli/src/doctor/filesystem_paths.rs`; `codex-rs/cli/src/doctor/output.rs`.


### More responsive transcript and startup behavior

Streaming prose can appear before a newline arrives. Transcript layout caching and viewport-bounded rendering reduce repeated rendering work, while startup drafts can be retained and submitted once the session becomes ready.

Tool activity previews are more compact, and completion timestamps follow the system’s clock-format preference.

Code references: `codex-rs/tui/src/streaming/controller.rs`, `transcript_view.rs`, `startup_draft.rs`, `exec_cell/render.rs`, and `clock_format.rs`.

## Bug Fixes

- **Web-search JSON output:** `codex exec --json` preserves search, page-opening, and find-in-page actions instead of losing them during conversion. Search items also retain structured results when available. (`EventProcessorWithJsonOutput` in `codex-rs/exec/src/event_processor_with_jsonl_output.rs`; `WebSearchItem` in `codex-rs/exec/src/exec_events.rs`.)

- **Interrupted output:** Streamed answers and plans are preserved when turns terminate, including subagent completion, rather than losing unfinished visible text. (`codex-rs/tui/src/streaming/controller.rs` and `codex-rs/tui/src/chatwidget.rs`.)

- **Clipboard routing:** Copying works more consistently with tmux clients attached after startup and with SSH sessions. Status messages distinguish a confirmed clipboard write from an unacknowledged terminal-copy request. (`CopyStatus` in `codex-rs/tui/src/clipboard_copy.rs`; `codex-rs/tui/src/clipboard_copy/tmux.rs`.)

- **Pasting and editing:** Non-bracketed paste bursts preserve tab indentation; pastes during history search update the search query; multiline feedback notes no longer submit prematurely. (`codex-rs/tui/src/bottom_pane/paste_burst.rs`, `chat_composer/paste_input.rs`, and `feedback_note_view.rs`.)

- **Transcript navigation:** Scrolling stays anchored across updates, settings pickers preserve reading position, and “Back to bottom” is hidden when the current tail is already visible. (`codex-rs/tui/src/transcript_view.rs` and `codex-rs/tui/src/app/event_dispatch.rs`.)

- **Unavailable-thread recovery:** Recovery commands such as `/new`, `/resume`, `/agents`, and `/warnings` remain usable when the current thread cannot be written, provided the server remains connected. (`SlashCommand::available_when_thread_unavailable` in `codex-rs/tui/src/slash_command.rs`.)

- **Voice continuity:** Audio survives pauses, packet bursts, mute periods, and backlog more reliably. Captions preserve speaker ordering and history placement, including handoffs between voice and agent work. (`codex-rs/voice-host/src/playback.rs`, `playout.rs`, and `codex-rs/tui/src/chatwidget/realtime.rs`.)

- **Compaction fallback:** A failed dedicated compaction-model attempt can fall back to the current model for more error classes; explicit interruption, turn cancellation, and session-budget exhaustion remain excluded. (`should_retry_with_current_model` in `codex-rs/core/src/compact_model_fallback.rs`.)

- **Reasoning and service-tier settings:** Unsupported reasoning-effort updates are no longer sent as model configuration updates, and explicitly configured Flex tiers are preserved when catalog or fast-mode support is absent. (`codex-rs/protocol/src/openai_models.rs` and `codex-rs/core/src/client.rs`.)

- **Guardian review context:** Review handling better preserves authorization evidence, ordered assistant context, and the instruction snapshot actually applied to the parent. Cached approvals are invalidated when permission widening lacks matching review coverage. (`codex-rs/core/src/guardian/review_session.rs` and `codex-rs/ext/guardian-v2/src/async_scorer/extension.rs`.)

- **Code Mode lifecycle:** Cleared timers and completed cells release timer tasks; yielded tool calls retain their originating execution context; discarded results can be released instead of unnecessarily retained. (`codex-rs/code-mode/`, `codex-rs/code-mode-protocol/src/session.rs`, and `codex-rs/core/src/tools/code_mode/`.)

- **Plugin policy:** Thread-level exclusions are respected across plugin capabilities, including shared connectors. Plugin-install requests are restricted to the root thread. (`codex-rs/core/src/mcp.rs`; `codex-rs/core-plugins/src/manager.rs`; `RequestPluginInstallHandler` in `codex-rs/core/src/tools/handlers/request_plugin_install.rs`.)

- **MCP interaction:** Subagents can request MCP elicitation input, while root-only approval paths retain their restrictions. MCP tool requests can carry the resolved read-only policy to server-side filtering and invocation checks. (`codex-rs/core/src/mcp_tool_call.rs`; `codex-rs/codex-mcp/src/rmcp_client.rs`; `codex-rs/rmcp-client/src/rmcp_client.rs`.)

- **OAuth discovery:** A candidate-local HTTP 503 during metadata discovery can recover through OIDC discovery without incorrectly treating the failure as missing metadata. (`codex-rs/rmcp-client/src/oauth_http_client.rs`.)

- **Cross-platform permissions:** Workspace roots, filesystem denials, Unix-socket policies, and permission summaries use the execution host’s path conventions instead of assuming the controller’s operating system. (`ConfigPathContext` in `codex-rs/config/src/path_context.rs`; `ProfileWorkspaceRoot` in `codex-rs/protocol/src/permission_profile_snapshot.rs`.)

- **macOS sandbox isolation:** Restricted profiles block XPC service lookups and file-mutating `fcntl` operations that could act through read-only descriptors. Scratch-directory allowances preserve explicit exclusions, and app-server sockets remain protected. (`create_seatbelt_command_args_with_profile` in `codex-rs/sandboxing/src/seatbelt.rs`; `seatbelt_scratch.rs` and `seatbelt_daemon.rs`.)

- **Linux sandbox isolation:** Restricted commands cannot reach the privileged daemon socket through filesystem aliases. WSLg’s duplicate distribution root is masked where required, while explicit Unix-socket grants remain usable. (`append_daemon_socket_mask` in `codex-rs/linux-sandbox/src/bwrap.rs`; `codex-rs/linux-sandbox/src/wslg.rs`.)

- **Windows sandbox lifecycle:** Private desktops survive helper lifetimes more reliably; setup repairs expired sandbox-account passwords; provisioning can recover after service restarts; cleanup handles disabled accounts. (`LaunchDesktop` in `codex-rs/windows-sandbox-rs/src/desktop.rs`; `setup_provisioning/sandbox_users.rs`; `provisioning_client/refresh_retry.rs`.)

- **macOS managed configuration:** Ordinary user preferences are no longer accepted as administrator-managed configuration. Managed values must be forced preferences containing the expected encoded TOML string. (`load_managed_preference_with` in `codex-rs/config/src/loader/macos.rs`.)

- **Unicode matching:** Fuzzy-match scoring handles lowercase expansions such as `İ` without confusing character positions. (`codex-rs/utils/fuzzy-match/src/lib.rs`.)

## In Development


### Automatic background-server startup [Experimental]

What: Eligible interactive launches can automatically start and use the shared local daemon.

Status: Off by default; enable through `/experimental` or configuration.

```toml
[features]
daemon_auto_start = true
```

Details:

- Applies to eligible new, resumed, and forked sessions.
- Takes effect on the next launch.
- `--no-daemon` provides an explicit bypass.
- Configuration compatibility is checked before using the shared server.

Code references: `Feature::DaemonAutoStart` in `codex-rs/features/src/lib.rs`; `codex-rs/tui/src/daemon_startup.rs`.


### Historical plan allowances [Experimental]

What: The analytics dashboard can show historical five-hour and weekly allowance information for supported consumer accounts.

Status: Off by default.

```toml
[features]
analytics_plan_history = true
```

Details:

- Open `/usage` and choose View analytics after enabling it.
- Requires the corresponding backend report; an unavailable endpoint does not imply zero usage.
- This flag controls the plan-history view, not the entire analytics dashboard.

Code references: `Feature::AnalyticsPlanHistory` in `codex-rs/features/src/lib.rs`; `codex-rs/tui/src/analytics/plan.rs`; `PlanLimitHistory` in `codex-rs/backend-client/src/client/plan_history.rs`.


### Persistent agent message boards [Experimental]

What: Multi-Agent V2 agents can share channels, discussion threads, posts, searches, and subscriptions.

Status: Under development and off by default; requires a persistent Multi-Agent V2 runtime.

```toml
[features]
multi_agent_v2 = true
agent_message_board = true
```

Details:

- Tools include `create_channel`, `get_channels`, `list_threads`, `search_posts`, `read_thread`, `read_post`, `subscribe`, `unsubscribe`, and `post`.
- Local boards use SQLite storage and survive runtime reloads.
- Notifications reach running turns; they do not start idle agents or create a later notification backlog.
- Ephemeral runtimes do not open durable boards.
- Permanently deleting the owning root thread also removes its persisted board data.

Code references: `install_agent_message_board` in `codex-rs/core/src/agent_message_board.rs`; `NAMES` in `codex-rs/ext/agent-message-board/src/tools/spec.rs`; `LocalAgentMessageBoard` in `codex-rs/ext/agent-message-board/src/local.rs`.


### Enterprise-managed MCP authentication [Experimental]

What: Trusted host configuration can register MCP resources for enterprise identity-provider authentication.

Status: Gated by `features.use_xaa`, which is off by default.

Configuration outline:

```toml
[features]
use_xaa = true

[mcp_enterprise_managed_auth.idp]
issuer = "https://identity.example.com"
client_id = "registered-client-id"
```

Details:

- Individual MCP resources also need their enterprise registration and `ema_auth` configuration.
- Identity-provider selection must come from trusted non-project configuration.
- The path requires host-owned Streamable HTTP connections.
- Enterprise authentication does not fall back to unrelated bearer credentials or ordinary MCP OAuth.
- Plugin MCP registrations validate the declared endpoint against the host-approved endpoint.

Code references: `McpEnterpriseManagedAuthConfig` and `McpEmaRegistration` in `codex-rs/config/src/mcp_ema.rs`; `McpServerAuth` in `codex-rs/config/src/mcp_types.rs`; `PluginMcpServerEmaAuthConfig` in `codex-rs/config/src/types.rs`.


### Manual rollout compression [Experimental]

What: App-server clients can trigger a best-effort background compression pass over cold local rollout files.

Status: Requires the app-server experimental API opt-in.

```json
{"method": "rollout/compress"}
```

Details:

- The response is `{}` acknowledging the trigger, not completion.
- Existing maintenance locks, cooldowns, and cold-file checks can cause a pass to skip work.
- There are no progress notifications or cancellation method.
- Non-local thread stores are unsupported.
- This does not enable the startup compression feature; clients sharing the storage must already support compressed histories.

Code references: `"rollout/compress"` in `codex-rs/app-server-protocol/src/protocol/common.rs`; `RolloutCompressResponse` in `codex-rs/app-server-protocol/src/protocol/v2/rollout.rs`; `codex-rs/rollout/src/compression.rs`.


### Selected-workspace routing [Experimental]

What: `account/read` can expose the selected ChatGPT workspace’s resolved backend routing.

Status: `account/read.workspaceRouting` is an experimental response field.

```json
{"method": "account/read", "params": {"refreshToken": false}}
```

Details:

- `workspaceRouting` includes `chatgptAccountId`, `backendOrigin`, and `accountRoutingOverride`.
- Routing values include `us`, `us_cr`, and `NO_CONSTRAINT`.
- Signed-out and API-only accounts return `null`.
- Discovery failure for a selected workspace returns an error rather than a successful unrestricted result.
- Clients should reread account and requirements state after `account/updated`.

Code references: `GetAccountResponse`, `WorkspaceRouting`, and `AccountRoutingOverride` in `codex-rs/app-server-protocol/src/protocol/v2/account.rs`; `codex-rs/app-server/src/request_processors/account_processor/workspace_routing.rs`; updated `GetAccountResponse.json` schema.


### Initial Daybreak selection [Experimental]

What: Persistent thread creation can save an initial Daybreak preference.

Status: The new `thread/start.daybreakEnabled` parameter requires experimental API access.

```json
{
  "method": "thread/start",
  "params": {"daybreakEnabled": true}
}
```

Details:

- Omission or `null` leaves the preference unset.
- Ephemeral threads do not support it.
- Saving this preference neither grants access nor selects a turn’s `cyberAccessProgram`.
- Daybreak-related thread state already existed; initialization through `thread/start` is the addition.

Code references: `ThreadStartParams::daybreak_enabled` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`.


### Native user-verification enrollment metadata [Experimental]

What: The existing enrollment API returns public-key metadata needed by a trusted client to complete backend registration.

Status: Part of the experimental user-verification API.

```json
{"method": "userVerification/enroll", "params": {}}
```

Details:

- The response adds `algorithm` and `publicKey` alongside `credentialId`.
- The public key uses unpadded base64url SPKI-DER encoding.
- Clients must check both optional fields before attempting registration with older-server compatibility.
- Local key creation is not backend enrollment.
- Native enrollment and verification remain restricted to supported local connection and platform paths.

Code references: `UserVerificationEnrollResponse` in `codex-rs/app-server-protocol/src/protocol/v2/user_verification.rs`; experimental method registration in `codex-rs/app-server-protocol/src/protocol/common.rs`.


### Native Windows MXC execution [Build-gated]

What: The Windows sandbox can select the native MXC execution path.

Status: Windows-only implementation, explicitly selected through configuration and checked for native OS availability.

```toml
[windows]
sandbox = "mxc"
```

Details:

- Integrates with standard command execution, streaming, process control, and ConPTY.
- Supports managed networking and temporary filesystem grants.
- Native availability is checked; older AppContainer fallback backends do not satisfy that check.
- Legacy elevated/unelevated setup is separate.
- MXC managed networking defaults local binding to enabled and rejects an explicit unsupported `false` setting.

Code references: `WindowsSandboxModeToml::Mxc` in `codex-rs/config/src/types.rs`; `is_available` in `codex-rs/mxc-sandbox/src/lib.rs`; `codex-rs/exec-server/src/process_sandbox.rs`.


### Registered Windows package execution [Experimental]

What: An opt-in sandbox path can use service-managed registered packages while preserving OS-assigned package identity.

Status: Requires Windows, a suitable registered package, and the startup environment variable:

```powershell
$env:CODEX_WINDOWS_REGISTERED_CORE = "1"
codex
```

Details:

- The environment variable selects the path; it does not authorize an arbitrary executable.
- Runtime checks validate the OS package identity and exact staged runner image.
- Provisioning and cleanup are coordinated with the Windows sandbox service.

Code references: `registered_core_requested` and `verify_registered_core_runner` in `codex-rs/windows-sandbox-rs/src/app_package.rs`; `codex-rs/windows-sandbox-service/src/package_lifecycle.rs`.


### Additional opt-in agent controls [Experimental]

What: Several new switches expose narrowly scoped behavior for testing and advanced configurations.

Status: Disabled or unset by default.

```toml
[features]
send_message_to_user_async = true
nonfatal_clock_read_errors = true

[features.code_mode]
experimental_show_cell_overhead = true
```

Details:

- `send_message_to_user_async` allows the root agent to use the existing asynchronous messaging tool without requiring model-catalog support. It does not enable the tool for subagents.
- `nonfatal_clock_read_errors` reports supported clock-read failures to the model instead of failing the turn.
- `experimental_show_cell_overhead` adds handler duration, Code Mode host duration, and harness overhead to cell responses.
- `[auto_review].experimental_policy_template` additionally supports a complete Guardian prompt-template override containing `{{ tenant_policy_config }}`.

Code references: feature definitions in `codex-rs/features/src/lib.rs`; tool gating in `codex-rs/core/src/tools/spec_plan.rs`; `codex-rs/core/src/tools/handlers/current_time.rs`; `CodeModeConfigToml` in `codex-rs/features/src/feature_configs.rs`; `AutoReviewToml` in `codex-rs/config/src/config_toml.rs`.

## Notes

- **Removed `thread/rollback`:** Migrate app-server callers to the existing `thread/revert` method for paginated threads:

  ```json
  {
    "method": "thread/revert",
    "params": {
      "threadId": "THREAD_ID",
      "beforeTurnId": "TURN_ID"
    }
  }
  ```

  The selected turn and all later turns are excluded from retained history. File changes are not reverted. The response contains thread metadata and pagination cursors; reload retained turns through `thread/turns/list`. Historical rollback records remain readable. Code references: `ThreadRevertParams` and `ThreadRevertResponse` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`; removed registration in `protocol/common.rs`.

- **Editing an earlier prompt now changes the current thread:** TUI backtracking reverts before the selected prompt and restores it for editing, replacing the previous automatic-fork behavior. Use an explicit fork when you want to preserve a separate conversation branch. Code reference: `App::apply_backtrack_selection` in `codex-rs/tui/src/app_backtrack.rs`.

- **Personality selection is retired:** `/personality` is removed; `friendly` and `pragmatic` no longer select a style, and `model/list` reports `supportsPersonality: false`. Legacy settings remain accepted without rewriting existing instructions. The `none` value retains its limited instruction-preparation behavior. Code references: `codex-rs/tui/src/slash_command.rs`; personality documentation in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs` and `model.rs`.

- **Replace obsolete TUI settings:** `[features].transcript_v2` is ignored; use `[tui].fullscreen_transcript`. Replace `[tui].whimsy` with the relevant `[tui.effects]` preferences. Code references: `legacy_usage_notice` in `codex-rs/features/src/lib.rs`; `Tui` in `codex-rs/config/src/types.rs`.

- **Windows private-desktop opt-out is removed:** Legacy sandboxed commands always use private desktops. Remove `windows.sandbox_private_desktop`; its managed-requirements counterpart is also removed. Code references: `WindowsToml` in `codex-rs/config/src/types.rs`; `LaunchDesktop::prepare` in `codex-rs/windows-sandbox-rs/src/desktop.rs`.

- **Managed-provider changes can require a restart:** A running app server whose retained catalog provider no longer satisfies current requirements rejects `model/list` rather than contacting the old endpoint. Existing threads can similarly reject new work under changed provider requirements. Code references: `codex-rs/app-server/src/model_catalog.rs` and `config_manager.rs`.


Generated with:
- tool: `harness-investigations@8fe113a-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.156.0.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
