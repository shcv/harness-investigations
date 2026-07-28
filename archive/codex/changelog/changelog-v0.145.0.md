# Changelog for version 0.145.0

## Official Release Highlights

This is a large release spanning several months of work. The headlining additions are experimental paginated thread history with SQLite-backed durable storage, an expanded `/import` that migrates Cursor and Claude Code settings alongside plugins and memories, experimental Amazon Bedrock login with custom transport support, audio inputs and streaming realtime V3 conversations, a stabilized multi-agent V2 experience with model and concurrency controls, and clickable inline visualization links in the terminal UI.


## New Features


### Experimental Paginated Thread History

What: A new SQLite-backed history mode for threads that persists turns and items durably, supports efficient cursor-based resume without replaying the rollout, preserves names and sub-agent history across restarts, and integrates with memories.

Usage:
```json
{"method": "thread/start", "id": 1, "params": {"historyMode": "paginated", ...}}
```

To resume efficiently without loading all turns upfront:
```json
{"method": "thread/resume", "id": 2, "params": {"threadId": "...", "excludeTurns": true}}
```
The response includes `turnsBackwardsCursor` and `itemsBackwardsCursor`. Pass each to its list API with `sortDirection: "desc"` to hydrate history on demand; live notifications deliver subsequent items.

Details:
- Paginated threads do not support `thread/rollback` or `thread/read(includeTurns: true)`.
- Sub-agent threads spawned from a paginated root also use paginated history.
- Memories work on paginated threads.
- Git metadata is stored in SQLite alongside the rollout projection.

Code references:
- `ThreadHistoryMode::Paginated` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- `codex_thread_store::ThreadStore` trait, `codex-rs/thread-store/`
- Schema: `codex-rs/app-server-protocol/schema/json/v2/ThreadResumeParams.json` (`turnsBackwardsCursor`, `itemsBackwardsCursor` fields)
- PRs: #32234, #32289, #32923, #32928, #33109, #33152, #33364, #33432, #33930, #34085, #34229, #34382, #34386, #34407


### Thread Occurrence Search

What: New experimental `thread/searchOccurrences` JSON-RPC method finds literal, case-insensitive matches within visible user messages and summary-selected final assistant messages in one paginated thread, without replaying its rollout.

Usage:
```json
{"method": "thread/searchOccurrences", "id": 26, "params": {
  "threadId": "...",
  "searchTerm": "my query",
  "cursor": null
}}
```
The response includes `occurrences` (with `snippet`, `turnId`, `turnCursor`, and UTF-16 match offsets) and an optional `nextCursor` for pagination.

Details:
- Only available on paginated threads.
- Occurrence `turnCursor` can be passed directly to `thread/turns/list` to load the containing turn.
- Marked `[EXPERIMENTAL]`.

Code references:
- `ThreadSearchOccurrencesParams`, `ThreadSearchOccurrencesResponse` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- `thread_search_occurrences()` in `codex-rs/app-server/src/thread_request_processor.rs`
- PR: #33907


### Expanded /import: Cursor and Claude Code Support

What: The `/import` migration wizard now detects and imports settings from Cursor IDE and Claude Code, in addition to the existing import sources. Migrated items include MCP servers, plugins, sessions, slash-commands, hooks, sub-agents, and project-scoped memories.

Usage: Launch `/import` from the Codex TUI and select the detected source. The migration presents items for review before applying changes.

Details:
- Cursor session transcripts are read from `~/.cursor/projects/*/agent-transcripts/` (JSONL files, excluding sub-agent directories).
- Cursor plugin manifests use the `.cursor-plugin/plugin.json` format; Cursor marketplaces use `.cursor-plugin/marketplace.json`.
- Claude Code memory files are imported as Codex agent memories with scope and provenance preserved.
- The `MigrationDetails` object now includes `subagents`, `commands`, and `memory` fields alongside the existing `plugins`, `skills`, `sessions`, `mcpServers`, and `hooks`.
- Import source is identified to the app server via a `source` selector; the same value must be passed to both `externalAgentConfig/detect` and `externalAgentConfig/import`.

Code references:
- `codex-rs/external-agent-migration/src/detect/sessions/cur.rs` (new — Cursor session detection)
- `codex-rs/external-agent-migration/src/detect/sessions/cla.rs` (Claude Code session detection)
- `SubagentMigration`, `CommandMigration` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- `ExternalAgentConfigImportParams.source` field in the v2 JSON schema
- PRs: #31672, #33411, #33426, #33444


### Amazon Bedrock: Managed Login, Custom Transports, Default Model Update [Experimental]

What: Amazon Bedrock now supports a managed login flow through the app server, custom endpoint/transport configuration, and has GPT-5.6 Sol as the default model.

Usage:
```json
{"method": "account/login/start", "id": 1, "params": {
  "type": "amazonBedrock"
}}
```
Custom transport (e.g., custom endpoint URL or auth command) is configured in `config.toml`:
```toml
[model_providers.amazon-bedrock.auth]
command = "/path/to/credential-helper"
```

Details:
- The `Account` type for `amazonBedrock` now has `usesCodexManagedCredentials: boolean` instead of the previous `credentialSource` field — a breaking protocol change for clients reading this field.
- Bedrock login and logout flows are exposed through the app server protocol.
- GPT-5.6 Sol replaces GPT-5.4 as the default Bedrock model.
- All these Bedrock login features are marked `[UNSTABLE]`.

Code references:
- `v2::Account::AmazonBedrock { usesCodexManagedCredentials }` in `codex-rs/app-server-protocol/src/protocol/v2.rs`
- `v2::LoginAccountParams::AmazonBedrock` (new variant)
- `codex-rs/app-server-protocol/schema/json/v2/LoginAccountParams.json`
- PRs: #31327, #33170, #33175, #32288, #33695, #33848


### Audio Inputs and Streaming Realtime V3

What: Users can now attach audio to turns as user input; tool call outputs can include audio; and realtime V3 conversations stream audio output through a new notification. Common local formats (MP3, WAV, OGG, M4A, MKV, FLAC) are accepted.

Details:
- New `AudioUserInput` content type for user turns (raw audio URL).
- New `LocalAudioUserInput` type for locally-transcoded audio using the `symphonia` decoder.
- `DynamicToolCallOutputContentItem` gains an `InputAudio` variant for audio in tool outputs; audio URLs must use inline data URLs (`data:audio/...;base64,...`).
- Realtime V3 sessions stream audio through the new `thread/realtime/outputAudio/delta` server notification.
- Audio history is gated by model input modalities — models that do not support audio do not replay audio items in the conversation context.
- New `ThreadRealtimeInitialItem` type seeds V3 sessions with initial text context.

Code references:
- `AudioUserInput`, `LocalAudioUserInput` in `codex-rs/app-server-protocol/schema/typescript/ContentItem.ts` (new types)
- `DynamicToolCallOutputContentItem::InputAudio` variant in `codex-rs/app-server-protocol/`
- `InputAudioDynamicToolCallOutputContentItem` in the v2 JSON schemas
- `symphonia` dependency added in `codex-rs/Cargo.lock`
- PRs: #33261, #33856, #33923, #33929, #33932, #34067, #34080, #34385


### Multi-Agent V2 Stabilized

What: The opt-in multi-agent V2 experience is now stable and the `[agents]` config section has been reorganized with new controls for model and concurrency.

Usage:
```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 4
default_subagent_model = "gpt-5.6-terra"
default_subagent_reasoning_effort = "medium"
```

Details:
- `max_threads` is now an alias for `max_concurrent_threads_per_session`; old configs continue to work.
- New `enabled` field explicitly controls whether multi-agent tools are available (defaults to `true`; a `features.multi_agent_v2` setting takes precedence).
- New `default_subagent_model` and `default_subagent_reasoning_effort` set the defaults for spawned agents when the spawn call does not specify them.
- The deprecated `multiAgentMode` parameter on `thread/start` is now ignored; use Ultra reasoning effort for proactive multi-agent behavior instead.
- Sub-agent threads spawned by V2 are now read-only in the TUI (you view them but interact through the root thread).
- Agent roles and identities are restored correctly when resuming a root thread with live V2 sub-agents.

Code references:
- `AgentsToml` struct in `codex-rs/config/src/config_toml.rs`
- Key alias: `agents.max_threads` → `agents.max_concurrent_threads_per_session` in `codex-rs/config/src/key_aliases.rs`
- PRs: #33550, #33572, #33631, #33657, #32749, #32751, #33841, #34383


### Inline Visualization Links in the TUI

What: When the assistant emits a `::codex-inline-vis{file: "chart.html"}` directive in its response, the TUI renders a clickable terminal hyperlink that opens the generated HTML file in the browser.

Details:
- Visualization HTML fragments are expected in a thread-scoped subdirectory under `~/.codex/visualizations/`.
- When the workspace write permission includes the visualization directory, that directory is used directly.
- The directive is only rendered as a link if the referenced `.html` file exists and is within the thread's visualization directory (path-traversal safe).
- When the file is not available (e.g., on a remote device), the TUI renders `_Visualization unavailable on this device._` instead.
- Code blocks containing the directive prefix are left unchanged.

Code references:
- `DIRECTIVE_PREFIX` (`"::codex-inline-vis{"`) in `codex-rs/tui/src/inline_visualization.rs` (new file)
- `rewrite_inline_visualizations()` in the same file
- `InlineVisualizationContext` struct
- PRs: #33925, #34217, #34346


### New App/Connector Metadata APIs [Experimental]

What: Two new app-server JSON-RPC methods let clients read metadata about installed Codex Apps connectors, including their tools.

Usage:
```json
{"method": "app/read", "id": 1, "params": {"appIds": ["connector-id-1"], "includeTools": true}}
{"method": "app/installed", "id": 2, "params": {"threadId": "...", "forceRefresh": false}}
```

Details:
- `app/read` returns `AppsReadResponse` with per-app metadata; setting `includeTools: true` adds an `AppToolSummary` list (name, title, description) per app.
- `app/installed` reads the committed installed connector runtime snapshot; `forceRefresh: true` triggers a refresh before returning.
- Both methods are marked `EXPERIMENTAL`.

Code references:
- `AppsReadParams`, `AppsReadResponse` in `codex-rs/app-server-protocol/schema/json/v2/` (new files)
- `AppsInstalledParams`, `AppsInstalledResponse` in the same directory (new files)
- `AppToolSummary` in `codex-rs/app-server-protocol/schema/typescript/v2/AppToolSummary.ts` (new file)
- PRs: #33651, #33843


### SessionEnd Hook Event

What: A new `SessionEnd` hook event fires when a thread unloads, allowing scripts to run teardown logic after a session ends.

Usage:
```toml
[hooks.events.SessionEnd]
[[hooks.events.SessionEnd]]
type = "command"
command = "python3 /tmp/on_session_end.py"
timeout = 3
```

Details:
- Fires when a thread has had no subscribers and no activity for 30 minutes, and also before archive, delete, and graceful app-server shutdown.
- Only fires for root threads — not `ThreadSpawn` children or internal sub-agents.
- Hooks are advisory: their output cannot block teardown.
- Default timeout is 1 second; configured timeouts are capped at 3 seconds.
- `async: true` is accepted but runs synchronously with a configuration warning.
- The hook input always reports `reason: "other"`.
- `SessionEnd` matchers are evaluated against the reason field.

Code references:
- `HookEventName::SessionEnd` in `codex-rs/config/src/hook_config.rs`
- `HookEventsToml.session_end` field (new) in `codex-rs/config/src/hook_config.rs`
- `codex-rs/app-server/tests/suite/v2/session_end.rs` (new test file)
- PR: #33895


## Improvements


### Hook additionalContextLimit Config Field

New per-command-hook config key `additionalContextLimit` controls the approximate token threshold at which a hook's `additionalContext` is spilled to disk instead of being passed inline.

Usage:
```toml
[[hooks.events.PreToolUse]]
type = "command"
command = "python3 /tmp/pre.py"
timeout = 10
statusMessage = "checking"
additionalContextLimit = 4096
```

Details:
- Default is 2,500 tokens when unset.
- Setting `0` disables spilling for that hook.
- The threshold is evaluated against the original context size; the spilled preview includes recovery metadata.
- Omitting the key serializes as absent (no `additionalContextLimit` key in the output).

Code references:
- `HookHandlerConfig::Command { additional_context_limit }` in `codex-rs/config/src/hook_config.rs`
- PR: #34393


### Working Directory Persistence on Session Resume

When resuming a session in the TUI picker, a new option lets you use the most recently recorded working directory from the selected session rather than always prompting.

Code references:
- Option label: `"Use the latest working directory recorded in the selected session."` in `codex-rs/tui/src/session_resume.rs`
- PR: #33950


### MCP Reliability and Startup Improvements

Several changes reduce MCP-related startup delays and race conditions:

- Startup timeouts are now enforced when creating MCP clients (not just during the tool-list phase), preventing indefinitely-blocked thread starts.
- MCP OAuth credential refreshes are serialized — concurrent requests reuse a single in-flight refresh rather than racing.
- MCP tool catalogs are reused across sessions; individual servers can opt out by setting a flag.
- Concurrent stdin writes to MCP processes are serialized.
- MCP tool catalog cache uses an LRU policy (`lru` crate added to `codex-mcp`).

Code references:
- `codex-rs/mcp/` — LRU cache addition
- PRs: #32229, #32781, #32825, #33180, #33184, #33297


### Terminal Rendering Performance

Several TUI changes reduce redraws and memory copying during long sessions and streamed output:

- Markdown is now rendered incrementally as it streams, avoiding full redraws per delta.
- Redundant frame passes during streaming are coalesced.
- Finalized Markdown history cells are cached — subsequent renders reuse the computed layout.
- Streamed command output is kept bounded in the TUI (no unbounded buffer growth).
- Copy-on-write storage for history snapshots reduces allocation when history is frequently read.
- Various `Arc`/`Cow` changes eliminate unnecessary clones of thread data, file-change diffs, hyperlink text, and Responses WebSocket payloads.

Code references:
- `codex-rs/tui/src/markdown_render/streaming.rs`
- `codex-rs/tui/src/streaming/`
- PRs: #34045, #34049, #34194, #34197, #34204, #34206, #34216, #34223, #34224, #34366, #34381, #34390


### Safety and Approval Handling

- Approval rejection reasons are now propagated across tool calls so the model receives the full context.
- `rm` command detection is strengthened to cover forced-deletion patterns.
- Enabling full-access mode now always requires an explicit confirmation step.

Code references:
- PRs: #32989, #33464, #34400


### Windows Execution and Sandbox Improvements

- Windows helper console windows (filesystem, network proxy helpers) are now hidden.
- The elevated Windows sandbox is required and used for network-proxy enforcement.
- Hook command arguments are now correctly quoted on Windows.
- Windows sandbox setup requests are coalesced when multiple arrive concurrently.
- Native exec-server sandboxing now works inside the Windows exec server.
- ACEs inherited from parent directories are ignored when refreshing Windows write roots.

Code references:
- `codex-rs/windows-sandbox-rs/src/`
- `codex-rs/exec-server/`
- PRs: #32849, #32857, #33445, #33926, #34423, #34392


### GPT-5.6 Model Migration

Internal GPT-5.4 model references have been migrated to the corresponding GPT-5.6 Terra and Luna variants. The bundled OpenAI Docs skill has been updated with current GPT-5.6 resolution, prompting guidance, and migration notes.

Code references:
- PRs: #33173, #31842, #33121


### Ripgrep Bundled Binary Updated to 15.2.0

The packaged `ripgrep` binary used by the shell tool is updated from an older version to 15.2.0.

Code references:
- PR: #34384


### Concurrent Startup Optimizations

- Skill and plugin roots are now scanned concurrently on startup, reducing startup latency.
- Executor plugin declarations are loaded concurrently.
- Workspace connectors are fetched concurrently.
- TUI bootstrap requests are parallelized.
- Remote compaction now uses a more efficient history handling path.

Code references:
- PRs: #31566, #33369, #33421, #33423, #34355, #34431


## Bug Fixes

- Editing an earlier TUI prompt or retrying a safety-buffered turn now forks the conversation into a new branch, preserving the original thread, its attachments, and mention bindings. (`codex-rs/app-server/src/` — PRs #33201, #33207, #33211)
- Code-mode installation on macOS is fixed; if the external code-mode host process cannot be resolved, Codex falls back to in-process V8. (PRs #31876, #31899)
- TUI status bar visibility is no longer obscured by streamed command output. (PR #33105)
- Tabs in diffs are now correctly expanded when rendered in the TUI diff view. (PR #32461)
- Empty reasoning summaries are no longer shown in the TUI. (PR #31652)
- Slash-command popup dismissal state is now persisted across frames. (PR #32858)
- Sessions that end with an interrupted prompt now retain that prompt in the conversation history for context. (PR #33198)
- The `apply_patch` tool description has been reworded for clarity. (PR #33680)
- MCP app requests are now attributed to Codex, not the OpenAI Docs MCP server. (PR #33424)
- Guardian reviews are cleared when turns end, preventing stale review overlays. (PR #34371)
- Responses after image generation are no longer blocked. (PR #32866)
- Turns with invalid tool images are no longer retried (they are terminated cleanly). (PR #34380)
- Generated images are no longer rendered twice in the TUI. (PR #34378)
- TUI prompts are rendered before submitting user turns, preventing a visual flash. (PR #33373)


## Notes

### Breaking Protocol Change: Amazon Bedrock `Account` Type

The `Account` discriminated union variant for `amazonBedrock` has changed its credential field. The previous shape was:

```typescript
{ "type": "amazonBedrock", credentialSource: AmazonBedrockCredentialSource }
```

The new shape is:

```typescript
{ "type": "amazonBedrock", usesCodexManagedCredentials: boolean }
```

Clients that read the `account/read` response or `account/updated` notification and branch on the `credentialSource` field must update to `usesCodexManagedCredentials`.


### `[agents]` Config Key Rename

`agents.max_threads` has been renamed to `agents.max_concurrent_threads_per_session`. The old key is accepted as an alias and existing configs continue to work without modification. New configs should use the canonical name.


### Deprecated `multiAgentMode` on `thread/start`

The `multiAgentMode` experimental parameter on `thread/start` is now silently ignored. To get proactive multi-agent behavior, use Ultra reasoning effort instead.


### Paginated Thread Limitations

Paginated threads do not support `thread/rollback` or `thread/read(includeTurns: true)`. Detached review is also unsupported when the parent thread is paginated.


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.145.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.145.0.md`
