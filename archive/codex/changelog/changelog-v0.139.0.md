# Changelog for version 0.139.0

## Official Release Highlights

This release enables web search in Code mode with plaintext results, broadens JSON Schema support to include `oneOf` and `allOf` in tool definitions, and improves `codex doctor` with editor and pager environment details. Plugin marketplace lists now include the source of each marketplace in JSON output and can return from the cached remote catalog immediately while refreshing in the background. Several bug fixes land for `codex resume/fork --last`, MCP startup duplicate warnings, image edit path routing, TUI URL linkification with tildes, cloud-requirement preservation across thread resets, and proxy-only network enforcement in the sandbox.

## New Features


### Web search enabled in Code mode with plaintext results

What: Standalone web search now works inside Code mode, including when invoked from nested JavaScript tool calls, and search results are returned as readable plaintext instead of opaque encrypted blobs.

Details:
- The `WebSearchTool` exposure changed from `ToolExposure::DirectModelOnly` to `ToolExposure::Direct`, making it available in Code mode.
- The internal `EncryptedSearchOutput` type was replaced by `SearchOutput`, which emits `FunctionCallOutputContentItem::InputText` instead of `FunctionCallOutputContentItem::EncryptedContent`.
- The `contains_external_context()` flag is set on search output, so the `memories.disable_on_external_context` setting takes effect for standalone searches just as it does for hosted web search.
- Web search citation instructions were updated: results now use inline markdown links rather than `turnX`-style citation markers.

Code references:
- `SearchOutput` replacing `EncryptedSearchOutput` in `codex-rs/ext/web-search/src/output.rs`
- `ToolExposure::Direct` in `codex-rs/ext/web-search/src/tool.rs`
- Updated citation prompt in `codex-rs/ext/web-search/web_run_description.md`


### `oneOf` and `allOf` preserved in tool input schemas

What: Tool and connector schemas that use `oneOf` or `allOf` composition keywords now pass through correctly to the model rather than being dropped or flattened, improving compatibility with richer MCP tools.

Details:
- `SCHEMA_CHILD_KEYS` now includes `"oneOf"` and `"allOf"` alongside `"items"` and `"anyOf"`, so the schema traversal and sanitization logic applies to all composition keywords consistently.
- New `JsonSchema::one_of()` and `JsonSchema::all_of()` constructors are available for building schemas programmatically.
- The schema compaction depth limit increased from 2 to 3 (`MAX_COMPACT_TOOL_SCHEMA_DEPTH`), so larger schemas preserve one additional level of shallow structure before collapsing.
- A new `prune_schema_compositions` compaction pass is added as the last resort: for very large schemas that still exceed the byte budget, any node with a composition keyword is collapsed to an empty object rather than left verbatim.

Code references:
- `COMPOSITION_SCHEMA_KEYS`, `JsonSchema::one_of`, `JsonSchema::all_of` in `codex-rs/tools/src/json_schema.rs`
- `prune_schema_compositions` in `codex-rs/tools/src/json_schema.rs`


### `codex doctor` reports editor and pager environment

What: The `system.environment` check in `codex doctor` now collects and displays the `VISUAL`, `EDITOR`, `PAGER`, `GIT_PAGER`, `GH_PAGER`, and `LESS` environment variables alongside the existing locale details.

Usage:
```
codex doctor
```

Details:
- In the human-readable report, the full values are shown so they can be read locally.
- In the JSON output (e.g., when `--json` is passed or the report is attached to a feedback submission), the values for these variables are redacted to `"set"` or `"not set"` to avoid leaking editor arguments, inline env assignments, or API keys that sometimes appear in pager command lines.

Code references:
- `EDITOR_ENV_VARS`, `PAGER_ENV_VARS`, `json_detail_value()` in `codex-rs/cli/src/doctor/system.rs` and `codex-rs/cli/src/doctor.rs`
- `system_details()` in `codex-rs/cli/src/doctor/output/detail.rs`

## Improvements


### Plugin `marketplace list --json` includes each marketplace source

What: The `codex plugin marketplace list --json` response now includes a `source` field for each marketplace entry, making it possible to tell whether plugins came from the curated remote catalog, a workspace directory, or a local installation.

Code references:
- `PluginListBackgroundTaskOptions` in `codex-rs/core-plugins/src/manager.rs`
- `plugins.rs` request processor in `codex-rs/app-server/src/request_processors/plugins.rs`


### Plugin list returns from cached remote catalog immediately

What: When a cached copy of the remote plugin catalog exists locally, `codex plugin marketplace list` now returns results from that cache right away and triggers a background refresh, instead of blocking on the network. This significantly reduces perceived latency for plugin list operations when a catalog was previously fetched.

Details:
- `has_cached_global_remote_plugin_catalog()` checks whether a local cache file exists before deciding whether to serve from it.
- `GlobalRemoteCatalogCacheRefreshState` tracks an in-flight background refresh loop so at most one refresh is running at a time.
- The `PluginListBackgroundTaskOptions { refresh_global_remote_catalog_cache }` flag controls whether a refresh is scheduled after serving from cache.
- All plugin-service requests now include an `OAI-Product-Sku: codex` header so the service can identify the client.

Code references:
- `has_cached_global_remote_plugin_catalog`, `GlobalRemoteCatalogCacheRefreshState`, `run_global_remote_catalog_cache_refresh_loop` in `codex-rs/core-plugins/src/remote.rs` and `codex-rs/core-plugins/src/manager.rs`
- `OAI_PRODUCT_SKU_HEADER`, `CODEX_PRODUCT_SKU` in `codex-rs/core-plugins/src/remote.rs`


### `-P` short alias for `--permissions-profile` on sandbox subcommands

What: The `--permissions-profile` flag accepted by the `sandbox`, `seatbelt`, and landlock subcommands now has a `-P` short alias, making it faster to type for common invocations.

Usage:
```bash
codex sandbox -P :workspace -- npm test
codex sandbox -P my-profile -- cargo build
```

Code references:
- `SeatbeltCommand`, `LandlockCommand`, `WindowsCommand` in `codex-rs/cli/src/lib.rs`


### `/debug-config` shows effective sandbox modes filtered by permissions

What: The `/debug-config` TUI command now filters the `allowed_sandbox_modes` list to show only the modes that are actually reachable under the current session's `permissions` constraints, rather than showing all modes listed in requirements files. Modes blocked by `deny_read` or similar filesystem constraints are omitted from the display.

Code references:
- `sandbox_mode_is_allowed_by_permissions()` in `codex-rs/tui/src/debug_config.rs`
- Snapshot `debug_config_effective_sandbox_modes_with_deny_read` in `codex-rs/tui/src/snapshots/`


### Faster external agent session imports

What: The external agent session import flow was refactored into a dedicated `ExternalAgentSessionImporter` that uses content SHA-256 hashes for deduplication and canonical paths for stable tracking, reducing redundant I/O and improving import speed for multi-session migrations.

Code references:
- `ExternalAgentSessionImporter` in `codex-rs/app-server/src/request_processors/external_agent_session_import.rs`
- `load_session_for_import_with_content_sha256`, `PendingSessionImport::source_content_sha256` in `codex-rs/external-agent-sessions/src/export.rs`


### Main agent must now read skill files completely before acting

What: The skill usage instructions embedded in the agent system prompt were tightened: the main agent is now required to read `SKILL.md` completely (not just enough to follow the workflow) before taking any task actions, and is explicitly prohibited from delegating skill instruction reading or interpretation to subagents. This produces more consistent skill execution when skills span multiple pages or reference other files.

Code references:
- `SKILLS_HOW_TO_USE_WITH_ABSOLUTE_PATHS`, `SKILLS_HOW_TO_USE_WITH_ALIASES` in `codex-rs/core-skills/src/render.rs`

## Bug Fixes

- `codex resume --last "..."` and `codex fork --last "..."` now correctly treat the trailing argument as the initial prompt when no explicit session ID was provided, rather than misreading it as a session ID. A `SessionTuiCli` wrapper enforces the mutual exclusion between `--last` and an explicit session ID when a prompt is also present. (`SessionTuiCli`, `finalize_resume_interactive`, `finalize_fork_interactive` in `codex-rs/cli/src/main.rs`)

- MCP startup failure warnings from subagents are now scoped by thread ID. The `McpServerStatusUpdatedNotification` gained a `threadId: string | null` field in the protocol; the TUI uses it to suppress duplicate warnings for the same server failure within the same thread, preventing repeated alerts from propagating to parent threads and clearing stuck startup spinners. (`McpServerStatusUpdatedNotification` in `codex-rs/app-server-protocol/src/protocol/v2/mcp.rs`, `mcp_startup.rs` in `codex-rs/tui/src/chatwidget/`)

- Image edits now route through the explicitly referenced file paths supplied in `referenced_image_paths` rather than guessing from conversation history. The tool interface was redesigned: `action: generate | edit` is replaced by optional `referenced_image_paths` (up to 5 absolute paths) and `num_last_images_to_include` (a bounded count for pathless history images). Providing neither generates a new image; providing one or the other edits using those images; providing both is rejected with an error message. (`request_for_args`, `ImagegenArgs` in `codex-rs/ext/image-generation/src/tool.rs`)

- Bare URLs containing `~` are now linkified end to end in the TUI. The root cause was that `pulldown-cmark` splits text events around `~` characters (used for strikethrough syntax). A new `DecodedTextMerge` iterator wrapper merges adjacent text events before the renderer sees them, allowing the URL regex to match across the split. (`DecodedTextMerge` in `codex-rs/tui/src/markdown_text_merge.rs`, wired into `codex-rs/tui/src/markdown_render.rs`)

- Thread resets via `/new`, `/clear`, and `/fork` no longer drop cloud-managed requirements or enterprise policy flags. The config rebuild that runs before these transitions now receives the `cloud_config_bundle` loader, so cloud-delivered constraints survive the reload. (`config_persistence.rs` in `codex-rs/tui/src/app/`)

- Sandbox execution now enforces proxy-only networking whenever a network proxy is running, regardless of whether the proxy was activated by managed requirements or by local configuration. Previously, `enforce_managed_network` was hardcoded to `false` on the debug sandbox path; it now reflects whether any proxy is actually active. (`debug_sandbox.rs` in `codex-rs/cli/src/`)

- Remote control enrollment is now preserved when the WebSocket endpoint returns a generic 404. Only a 404 response with an explicit `{"detail": "Remote app server not found"}` body clears the enrollment; transient or infrastructure 404s leave the enrollment intact and trigger a reenrollment attempt. (`websocket.rs` in `codex-rs/app-server-transport/src/transport/remote_control/`)

## Notes

### Protocol: `McpServerStatusUpdatedNotification` gains `threadId` field

The `McpServerStatusUpdatedNotification` schema (in `ServerNotification.json`, `codex_app_server_protocol.schemas.json`, `codex_app_server_protocol.v2.schemas.json`, and `v2/McpServerStatusUpdatedNotification.json`) now includes a `threadId: string | null` field. The field is optional on the wire — existing payloads without it deserialize with `threadId: null`. No migration is required for existing clients, but client code that pattern-matches on the notification shape may need to be updated if it uses strict schema validation.


### Protocol: `ApprovalsReviewer` serializes as `auto_review`

The `ApprovalsReviewer::AutoReview` variant now serializes to `"auto_review"` instead of `"guardian_subagent"`. Both strings are still accepted for deserialization (the old value is kept as an alias), so existing stored data and incoming messages that use `"guardian_subagent"` continue to work. However, any client that compares the serialized string value against `"guardian_subagent"` will need to also accept `"auto_review"`. (`ApprovalsReviewer` in `codex-rs/app-server-protocol/src/protocol/v2/shared.rs`)


### Protocol (multi-agent v2): `close_agent` tool renamed to `interrupt_agent`

In the multi-agent v2 tool registry, the `close_agent` tool has been renamed to `interrupt_agent`. The new name better reflects the semantics (requesting that an agent stop rather than destroying it). Multi-agent v2 client code that constructs or handles tool calls with the name `"close_agent"` must be updated to use `"interrupt_agent"`. (`interrupt_agent.rs` in `codex-rs/core/src/tools/handlers/multi_agents_v2/`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/changes/changes-v0.139.0-2.diff` (filtered astdiff)
- official release notes: `archive/codex/changes/release-notes-v0.139.0.md`
