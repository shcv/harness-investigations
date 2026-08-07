# Changelog for version 0.147.0

## Summary

Codex 0.147.0 expands plugin discovery and portable Agent Plugin support, adds persistent conversation sections, and introduces reviewed automation through `--approve-for-me`. It also improves external-session migration, Amazon Bedrock support, MCP interoperability, terminal reliability, and safety protections.

## Official Release Highlights

### Plugin discovery and portable Agent Plugins

What: Codex can install portable Agent Plugins and search plugin catalogs across local, personal, workspace, and remote sources.

Usage:

```json
{"method":"plugin/search","params":{"searchTerm":"database","scope":"global","limit":20}}
```

Details:

- The app-server’s experimental `plugin/search` API accepts a search term, scope (`global`, `workspace`, or `personal`), optional working directories, and pagination.
- Remote catalog search requires a Codex-backend-compatible authenticated account; local search remains available from configured marketplaces.
- Plugin bundles may now use a valid Agent Plugin manifest in addition to the legacy `.codex-plugin/plugin.json` format.

Code references:

- `PluginSearchParams` and `PluginSearchResponse` in `codex-rs/app-server-protocol/src/protocol/v2/plugin_search.rs`
- Experimental JSON-RPC method `"plugin/search"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `search_remote_plugins` in `codex-rs/core-plugins/src/remote/search.rs`
- `PluginManifestFormat::AgentPlugin` in `codex-rs/core-plugins/src/manifest.rs`


### Persistent conversation sections

What: Organize conversations into named, persistent sections, manually order threads within them, and browse long history incrementally.

Usage:

```json
{"method":"threadSection/create","params":{"name":"Release work"}}
```

```json
{"method":"thread/section/move","params":{"threadId":"thread_123","sectionId":"section_456"}}
```

Details:

- Clients can list, create, rename, and delete sections through `threadSection/*` methods.
- `thread/section/move` places a thread into, within, or out of a section; `sectionId: null` removes it from a section.
- Thread listing adds a nullable `sectionId` filter and `section_position` ordering.
- Section persistence requires the SQLite state store; the API reports the operations as unavailable without it.

Code references:

- `ThreadSectionCreateParams`, `ThreadSectionListParams`, and `ThreadSectionMoveParams` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- JSON-RPC methods `"threadSection/list"`, `"threadSection/create"`, `"threadSection/update"`, `"threadSection/delete"`, and `"thread/section/move"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `ThreadRequestProcessor::thread_section_create` in `codex-rs/app-server/src/request_processors/thread_sections.rs`


### Automatically reviewed approvals

What: Use `--approve-for-me` to route approval requests through automatic review while retaining the workspace-write sandbox.

Usage:

```bash
codex --approve-for-me
```

Details:

- The flag sets `approvals_reviewer = "auto_review"`, `approval_policy = "on-request"`, and `sandbox_mode = "workspace-write"`.
- It is available to both interactive Codex and `codex exec`.
- It conflicts with an explicitly selected sandbox mode and with the fully unsafe bypass option; it does not disable sandboxing.

Code references:

- `SharedCliOptions::auto_review` and `take_auto_review_config_overrides` in `codex-rs/utils/cli/src/shared_options.rs`


### External Claude and Cursor migration synchronization

What: Import Cursor-managed skills and update previously imported Claude and Cursor conversations without duplicating existing history.

Details:

- Claude and Cursor session records are parsed separately.
- Imports track source-file hashes and append only when an existing imported session has changed.
- Imported-session detection now includes connector attribution and session titles.

Code references:

- `ExistingSessionAppend` and `SessionImportTarget` in `codex-rs/external-agent-migration/src/sessions.rs`
- `append_existing_session` in `codex-rs/external-agent-migration/src/sessions.rs`
- `ExternalAgentSessionImporter::import_requested_session` in `codex-rs/app-server/src/external_agent_migration/session_importer.rs`


### MCP 2026-07-28 compatibility [Experimental]

What: Adds opt-in support for the MCP 2026-07-28 protocol, including discovery, pagination, multi-round operations, cached tool exposure, and startup that does not block unrelated work.

Usage:

```toml
[features]
mcp_2026_07_28 = true
```

Details:

- The protocol mode is off by default.
- Modern stdio MCP servers select the protocol with `CODEX_MCP_PROTOCOL_VERSION=2026-07-28`; unknown modern protocol markers are rejected.
- Codex can expose cached MCP tools while servers are still starting and can continue unrelated tool work during optional startup.

Code references:

- `McpProtocolMode::V20260728` in `codex-rs/rmcp-client/src/protocol_mode.rs`
- `RmcpClient::new_stdio_client_with_protocol_mode` in `codex-rs/rmcp-client/src/rmcp_client.rs`
- `Feature::Mcp20260728` in `codex-rs/features/src/lib.rs`


### Amazon Bedrock web search and remote compaction

What: Amazon Bedrock-backed Codex sessions now advertise cached web-search support and remote conversation compaction.

Details:

- Bedrock’s catalog is normalized to use text web search, avoiding unsupported multimodal search fields.
- Bedrock reports remote compaction capability level `V1`.
- These capabilities apply when Codex is configured to use the Amazon Bedrock provider.

Code references:

- `AmazonBedrockModelProvider::capabilities` in `codex-rs/model-provider/src/amazon_bedrock/mod.rs`
- `normalize_bedrock_catalog` in `codex-rs/model-provider/src/amazon_bedrock/catalog.rs`
- `RemoteCompactionSupport` in `codex-rs/model-provider/src/provider.rs`

## Additional Changes Beyond Official Notes

The following user-facing changes are present in the diff but were not called out in the published highlights.

## New Features

### Two-stroke TUI key bindings

What: TUI keymap configuration now accepts two-key chords for configurable actions.

Usage:

```toml
[tui.keymap.global]
open_transcript = "ctrl-x ctrl-t"
```

Details:

- A binding may be a single key or a two-stroke chord.
- Codex waits up to one second for the second stroke; `Esc` cancels a pending chord.
- Lists of bindings remain alternatives, not multi-key sequences.

Code references:

- `KeybindingSpec` and `normalize_keybinding_spec` in `codex-rs/config/src/tui_keymap.rs`
- `RuntimeChordKeymap` and `KeyChordMatcher` in `codex-rs/tui/src/keymap/chords.rs`


## Improvements

### Clearer stalled-goal status and fork naming

Blocked goals are displayed as stalled in the TUI, and forked chats can be named from the TUI. These changes make long-running and branched work easier to interpret and manage.

Code references: `ThreadGoalStatus` handling in `codex-rs/tui/src/chatwidget/goal_menu.rs` and fork naming flow in `codex-rs/tui/src/chatwidget/interaction.rs`


### More resilient long-history browsing

Thread and transcript loading now use paginated state-database queries, preserve page metadata through resumes, and load local session pickers from the state database first. This reduces startup and browsing work for long conversation histories.

Code references: `ThreadHistorySupport` in `codex-rs/app-server-protocol/src/protocol/thread_history.rs` and `PageLoading` in `codex-rs/tui/src/resume_picker/page_loading.rs`


### Improved OpenAI documentation skill

The bundled OpenAI documentation skill now routes targeted requests to appropriate official sources and gives clearer guidance for Codex, model selection, and API workflows.

Code references: OpenAI documentation skill routing changes in `codex-rs/core-skills/` and `Feature::OpenAiDocs` integration in `codex-rs/core/`


## Bug Fixes

- Displayed commands and replayed history redact secrets and complete bearer tokens more reliably. (`thread_resume_redaction` in `codex-rs/app-server/src/request_processors/thread_resume_redaction.rs`)
- TUI input is preserved when terminal focus returns or MCP servers initialize, avoiding lost or stalled keystrokes. (`mcp_startup` in `codex-rs/tui/src/chatwidget/mcp_startup.rs`)
- Terminal rendering handles Japanese halfwidth sound marks, emoji, hyperlinks, and viewport-edge cursor placement more accurately. (`terminal_hyperlinks` in `codex-rs/tui/src/terminal_hyperlinks.rs` and width handling in `codex-rs/tui/src/width.rs`)
- Windows interrupts now terminate non-TTY background process trees, and namespace-style Windows paths are normalized in path URIs. (`process_group` in `codex-rs/utils/pty/src/process_group.rs` and `PathUri` in `codex-rs/utils/path-uri/src/lib.rs`)
- Project configuration now requires explicit trust for unfamiliar local projects, while managed authentication restrictions are applied before credentials can be used. (`ManagedAuthPolicy` in `codex-rs/config/src/auth_policy.rs` and project-trust loading in `codex-rs/config/src/loader/mod.rs`)
- Plugin and network isolation fail closed when an allow-policy amendment cannot be applied. (`apply_network_policy` in `codex-rs/core/src/` and plugin loading in `codex-rs/core-plugins/src/loader.rs`)

## In Development

### Custom developer instructions for v2 subagents [Experimental]

What: Supply dedicated developer instructions to spawned v2 subagents.

Usage:

```toml
[features.multi_agent_v2]
enabled = true
subagent_developer_instructions = "Investigate independently, then report concise evidence."
```

Status: Runtime-gated by the `multi_agent_v2` feature.

Details:

- Codex resolves these instructions separately from the parent’s developer instructions and injects them when creating applicable v2 subagents.
- An empty value explicitly suppresses the configured subagent instructions.

Code references:

- `MultiAgentV2ConfigToml::subagent_developer_instructions` in `codex-rs/features/src/feature_configs.rs`
- `ThreadSpawnRequest` handling in `codex-rs/core/src/agent/control/spawn.rs`


### Image resize notices [Experimental]

What: Lets Codex tell the model when an attached image was resized and provide source and prepared dimensions.

Status: Runtime-gated by `[features] image_resize_notice = true`; disabled by default.

Details:

- The feature records `ImagePreparationMetadata` for the prompt image path.
- It changes model context rather than the image attachment command-line interface.

Code references:

- `Feature::ImageResizeNotice` in `codex-rs/features/src/lib.rs`
- `ImagePreparationMetadata` in `codex-rs/analytics/src/facts.rs`

## Notes

- App-server v2 clients should migrate pinning logic to sections. `ThreadMetadataUpdateParams.isPinned` and `ThreadListParams.isPinned` were removed; use the new `threadSection/*` methods, `thread/section/move`, and `sectionId` filtering instead.
- Section APIs require SQLite-backed state. Clients should handle the documented “unavailable without sqlite state” response.
- `codex exec --full-auto` has been removed. Use `codex exec --sandbox workspace-write` when that is the desired execution policy.


Generated with:
- tool: `harness-investigations@3e694c8-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.147.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.147.0.md`
