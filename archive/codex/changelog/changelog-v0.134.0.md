# Changelog for version 0.134.0

### Local Conversation Search

What: Codex can now search across local conversation history and return matching threads with text previews.

Usage:
```json
{
  "method": "thread/search",
  "params": {
    "searchTerm": "deployment error",
    "limit": 20,
    "sortDirection": "desc"
  }
}
```

Details:
- Search is exposed through the new app-server JSON-RPC method `"thread/search"`.
- Results include both the matching `thread` and a `snippet` preview.
- The search accepts pagination cursors, sort fields, sort direction, source filters, and an archived-thread filter.
- The implementation rejects empty `searchTerm` values and the release also makes matching case-insensitive.

Code references:
- `"thread/search"` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `ThreadSearchParams`, `ThreadSearchResult`, and `ThreadSearchResponse` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- `ThreadProcessor::thread_search` in `codex-rs/app-server/src/request_processors/thread_processor.rs`
- `search_threads` implementation in `codex-rs/thread-store/src/local/search_threads.rs`


### `--profile` Is Now the Primary Profile Selector

What: The former profile-v2 flow is promoted to the main `--profile` / `-p` CLI option, while legacy `profile = "..."`
and `[profiles.*]` config selectors are rejected with migration guidance.

Usage:
```bash
codex --profile work
codex --profile work resume
codex --profile work mcp list
codex sandbox --profile work -- echo ok
```

Details:
- `--profile-v2` is replaced by `--profile` in the shared CLI options.
- The selected profile layers `$CODEX_HOME/<name>.config.toml` on top of the base user config.
- `codex mcp` and `codex sandbox` now participate in the profile flow.
- Attempts to write legacy `profile` or `profiles.*` values through app-server config APIs now fail with explicit migration text.

Code references:
- `config_profile_v2` with `#[arg(long = "profile", short = 'p')]` in `codex-rs/utils/cli/src/shared_options.rs`
- `profile_v2_for_subcommand` in `codex-rs/cli/src/main.rs`
- `loader_overrides_for_profile` in `codex-rs/cli/src/main.rs`
- legacy write rejection in `codex-rs/app-server/src/config_manager_service.rs`
- `Config` schema removal of `profile` / `profiles` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`

Notes:
- Migrate old `[profiles.work]` settings into `$CODEX_HOME/work.config.toml`.
- Remove matching legacy `profile = "work"` or `[profiles.work]` entries from the base config before using `--profile work`.


### Host-Native `codex sandbox`

What: `codex sandbox` now selects the sandbox backend for the current OS directly, instead of requiring `codex sandbox macos`, `codex sandbox linux`, or `codex sandbox windows`.

Usage:
```bash
codex sandbox -- echo ok
codex sandbox --profile work -- echo ok
codex sandbox --log-denials -- echo ok
```

Details:
- On macOS, the command uses Seatbelt.
- On Linux, it uses the Linux sandbox.
- On Windows, it uses the restricted-token sandbox.
- The README now documents the host-native form and the `--profile NAME` layering behavior.

Code references:
- `HostSandboxArgs` in `codex-rs/cli/src/main.rs`
- `SeatbeltCommand`, `LandlockCommand`, and `WindowsCommand` profile fields in `codex-rs/cli/src/lib.rs`
- README sandbox command update in `codex-rs/README.md`


### MCP Configuration and OAuth Improvements

What: MCP setup gains explicit environment targeting and new OAuth options for streamable HTTP servers.

Usage:
```bash
codex mcp add oauth-server \
  --url https://example.com/mcp \
  --oauth-client-id eci-prd-pub-codex-123 \
  --oauth-resource https://resource.example.com
```

Config:
```toml
[mcp_servers.remote_docs]
url = "https://example.com/mcp"
environment_id = "remote"
oauth_resource = "https://resource.example.com"

[mcp_servers.remote_docs.oauth]
client_id = "eci-prd-pub-codex-123"
```

Details:
- New `--oauth-client-id` and `--oauth-resource` flags are accepted by `codex mcp add` for streamable HTTP servers.
- MCP server config now uses `environment_id`, defaulting to `"local"`, instead of the previous `experimental_environment` field.
- Remote stdio MCP servers now validate their working directory requirements against the chosen environment.

Code references:
- `AddMcpStreamableHttpArgs::oauth_client_id` and `oauth_resource` in `codex-rs/cli/src/mcp_cmd.rs`
- `McpServerOAuthConfig` use in `codex-rs/cli/src/mcp_cmd.rs`
- `DEFAULT_MCP_SERVER_ENVIRONMENT_ID` and `McpServerConfig::environment_id` in `codex-rs/config/src/mcp_types.rs`
- `McpRuntimeContext` in `codex-rs/codex-mcp/src/runtime.rs`


### Connector Tool Schema Reliability

What: Connector and dynamic-tool schemas preserve more meaningful JSON Schema structure before being sent to the model.

Details:
- Local `$ref` values are preserved.
- Reachable `$defs` and legacy `definitions` tables are kept, while unreachable definitions can be pruned.
- Oversized schemas are compacted best-effort to stay within schema-size limits while preserving important constraints.
- This matters most for connector tools with rich schemas, such as calendar, drive, email, Notion, and Slack-style APIs.

Code references:
- `parse_tool_input_schema` and `compact_large_tool_schema` in `codex-rs/tools/src/json_schema.rs`
- local definition handling around `DEFINITION_TABLE_KEYS` in `codex-rs/tools/src/json_schema.rs`
- connector schema fixtures in `codex-rs/tools/tests/fixtures/json_schema_policy/`


### Parallel Read-Only MCP Tool Calls

What: MCP tools marked read-only can now run in parallel even when the MCP server has not globally opted into parallel tool calls.

Details:
- `McpToolHandler::supports_parallel_tool_calls` now treats `annotations.read_only_hint == true` as sufficient for parallel execution.
- Server-level `supports_parallel_tool_calls` still works for broader opt-in.
- The behavior is limited to tools whose handler data identifies them as safe to parallelize.

Code references:
- `McpToolHandler::supports_parallel_tool_calls` in `codex-rs/core/src/tools/handlers/mcp.rs`
- `ToolCallRuntime` parallel execution in `codex-rs/core/src/tools/parallel.rs`
- handler lookup via `ToolRouter::tool_supports_parallel` in `codex-rs/core/src/tools/router.rs`


### Extension and Hook Context

What: Extension tools and hook inputs now receive richer context about the active session and subagents.

Details:
- Extension tool calls now include conversation history, allowing extensions to reason over prior messages and response items.
- Hook schemas include subagent identity fields so hook consumers can distinguish main-agent work from subagent work.
- Plugin hooks are no longer gated by the old `plugin_hooks` feature flag; the removed feature key is ignored for feature-toggle purposes.

Code references:
- conversation history assembly in `codex-rs/core/src/tools/handlers/extension_tools.rs`
- `ConversationHistory` support in `codex-rs/ext/extension-api/src/lib.rs`
- generated hook input schemas in `codex-rs/hooks/schema/generated/*.schema.json`
- removed plugin-hooks gating in `codex-rs/core-plugins/src/loader.rs` and `codex-rs/core/src/session/mod.rs`
- removed-feature handling for `plugin_hooks` in `codex-rs/features/src/lib.rs`


### Remote Reliability Fixes

What: Remote sessions recover from more stale or interrupted transport states.

Details:
- Disconnected exec-server websocket clients are reconnected with fresh sessions.
- Remote control retries immediately after auth recovery.
- Remote compaction v2 requests are retried when the stream fails.
- Remote compaction v2 now reports its own analytics implementation value rather than reusing the generic Responses label.

Code references:
- websocket reconnection logic in `codex-rs/app-server-transport/src/transport/remote_control/websocket.rs`
- remote control retry path in `codex-rs/exec-server/src/client.rs`
- retry loop and `responses_compaction_v2` implementation in `codex-rs/core/src/compact_remote_v2.rs`
- `CompactionImplementation::ResponsesCompactionV2` in `codex-rs/analytics/src/facts.rs`


### Windows Terminal and Sandbox Fixes

What: Windows terminal rendering and sandbox logs are more reliable.

Details:
- The TUI now restores Windows virtual terminal processing before drawing, resizing, clearing, and resuming the terminal.
- Windows sandbox setup logs now use daily rolling files rather than a single `sandbox.log`.

Code references:
- `ensure_virtual_terminal_processing` in `codex-rs/tui/src/tui.rs`
- rolling sandbox log paths via `log_file_path_for_utc_date` and `current_log_file_path` in `codex-rs/windows-sandbox-rs/src/logging.rs`


### Better Usage-Limit Messages

What: Workspace credit and spend-cap failures now show workspace-specific copy instead of falling back to generic usage-limit text.

Details:
- Workspace owner/member credit depletion and spend-cap errors now produce targeted messages.
- This makes it clearer whether the user can add credits, raise a cap, or needs a workspace owner to act.

Code references:
- `UsageLimitReachedError` display logic in `codex-rs/protocol/src/error.rs`
- workspace rate-limit variants in `codex-rs/protocol/src/protocol.rs`
- API bridge handling in `codex-rs/codex-api/src/api_bridge.rs`


### Managed Network Proxy for Node Tools

What: Node-based tools now inherit Codex’s managed network proxy environment.

Details:
- This fixes tool execution paths where Node subprocesses previously missed proxy variables that Codex had already configured.

Code references:
- managed proxy environment handling in `codex-rs/network-proxy/src/proxy.rs`
- Node tool environment plumbing in `codex-rs/rmcp-client/src/stdio_server_launcher.rs`

### Amazon Bedrock Mantle GovCloud Region

What: Amazon Bedrock Mantle now accepts the `us-gov-west-1` region.

Config:
```toml
model_provider = "amazon_bedrock"
```

Details:
- The supported Mantle region list now includes `us-gov-west-1`.
- The resulting base URL is `https://bedrock-mantle.us-gov-west-1.api.aws/openai/v1`.

Code references:
- supported region list and `base_url("us-gov-west-1")` test in `codex-rs/model-provider/src/amazon_bedrock/mantle.rs`


### Config Requirements Can Report Appshot Policy

What: Managed config requirements can now include whether appshots are allowed.

Usage:
```json
{
  "method": "configRequirements/read",
  "params": {}
}
```

Details:
- `ConfigRequirements` gains `allowAppshots`.
- The value is surfaced through the app-server protocol, JSON schemas, TypeScript bindings, and TUI debug config output.
- This appears to be a policy-reporting surface rather than a new user command.

Code references:
- `ConfigRequirements::allow_appshots` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`
- `allow_appshots` parsing and sourcing in `codex-rs/config/src/config_requirements.rs`
- debug display in `codex-rs/tui/src/debug_config.rs`
- schema `codex-rs/app-server-protocol/schema/json/v2/ConfigRequirementsReadResponse.json`


### TUI Log File Is Opt-In and Legacy Logs Are Cleaned Up

What: The TUI no longer keeps writing the legacy `codex-tui.log` by default.

Details:
- Startup removes the legacy log file under `$CODEX_HOME/log/codex-tui.log`.
- File logging remains available through the existing explicit logging path.

Code references:
- `TUI_LOG_FILE_NAME` and legacy log cleanup in `codex-rs/tui/src/lib.rs`
- tracing setup around `setup_logging` in `codex-rs/tui/src/lib.rs`

### Protocol and Client Migration Notes

- App-server clients should add support for `"thread/search"` and the new `ThreadSearchResponse.data[].snippet` shape if they expose conversation search.
- Config clients should stop reading or writing top-level `profile` and `profiles` through the v2 app-server `Config` protocol; those fields were removed from the schema.
- Clients that serialize request params may now omit false boolean defaults for fields such as `refreshToken`, `includeTurns`, `includeLogs`, and `persistExtendedHistory`; the server still defaults them on deserialize.
- MCP config writers should prefer `environment_id = "local"` or a concrete remote environment id instead of the removed `experimental_environment` name.
- Users with legacy profile config should move `[profiles.NAME]` into `$CODEX_HOME/NAME.config.toml` and invoke Codex with `--profile NAME`.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.134.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.134.0.md`
