# Changelog for version 0.138.0


## Summary

This release adds personal access token (v2 PAT) support across CLI and app-server flows, a new `account/usage/read` JSON-RPC method for reading account token usage statistics, `--json` output flags on all marketplace and plugin add/remove CLI commands, and an expanded plugin detail protocol that now carries app templates with availability reasons. Reasoning effort is now an open string rather than a fixed enum, allowing models to advertise custom effort levels. Several goal workflow and TUI polish fixes ship alongside it.

## Official Release Highlights

### /app Command Handoff to Codex Desktop
On macOS and native Windows, the `/app` command can now hand off the current CLI thread into Codex Desktop. On Windows, workspace launches can also open directly into Desktop instead of stopping at a manual prompt. Windows workspace handoffs now use the `codex://threads/new?path=...` URL scheme.

Code references: `codex_new_thread_url()` in `codex-rs/cli/src/app_cmd.rs`


### Image File Paths Exposed to the Model
Local image attachments and standalone image generations now include their saved file paths in the model-facing output hint. This makes follow-up edit requests and file references more reliable because the model knows where the image was written.

Code references: `extension_image_generation_output_hint()` in `codex-rs/image-generation-extension/` (new function); `MAX_IMAGE_GENERATION_OUTPUT_HINT_BYTES` constant caps the hint at 1024 bytes.


### Reasoning Effort Flexibility
The TUI adds fallback keyboard shortcuts for terminals that do not respond to `Alt` key bindings. Model-defined reasoning effort levels now flow through in the order the model advertises them rather than being reordered. At the protocol level, `ReasoningEffort` is no longer a fixed enum — it is now an open non-empty string, letting any model advertise custom effort levels without a Codex schema update.

Code references: `ReasoningEffort` in all `codex-rs/app-server-protocol/schema/` files; `ReasoningEffortPreset` in `codex-rs/app-server/src/models.rs`


### Account Token Usage Reading
App-server integrations can now query token usage statistics for the authenticated account. Requires ChatGPT/PAT authentication.

Usage:
```json
{"method": "account/usage/read", "id": 1}
```

Response shape (`GetAccountTokenUsageResponse`):
```json
{
  "summary": {
    "lifetimeTokens": 1234567,
    "peakDailyTokens": 50000,
    "longestRunningTurnSec": 300,
    "currentStreakDays": 7,
    "longestStreakDays": 14
  },
  "dailyUsageBuckets": [
    {"startDate": "2026-06-10", "tokens": 12000}
  ]
}
```

Code references: `GetAccountTokenUsageResponse`, `AccountTokenUsageSummary`, `AccountTokenUsageDailyBucket` in `codex-rs/app-server-protocol/src/protocol/v2/account.rs`; new schema file `codex-rs/app-server-protocol/schema/json/v2/GetAccountTokenUsageResponse.json`; `AccountRequestProcessor::get_account_token_usage()` in `codex-rs/app-server/src/request_processors/account_processor.rs`


### Personal Access Token (v2 PAT) Support
Codex auth now supports v2 personal access tokens in the CLI and app-server flows. A new `personalAccessToken` value is added to the `AuthMode` enum. The `codex login status` command reports "Logged in using personal access token" when this mode is active.

Code references: `AuthMode::PersonalAccessToken` in `codex-rs/app-server-protocol/src/protocol/common.rs`; `AuthDotJson.personal_access_token` field in `codex-rs/login/`; updated `AuthMode.ts` in `codex-rs/app-server-protocol/schema/typescript/`; `auth_mode_name()` and `stored_auth_issues()` in `codex-rs/cli/src/doctor.rs`


### Plugin Automation JSON Output
All marketplace and plugin add/remove commands gain a `--json` flag for machine-readable output. Plugin list output now includes the marketplace source. Plugin detail data exposes app templates with availability reasons and remote MCP server names.

Usage:
```bash
codex marketplace add --json <source>
codex marketplace list --json
codex marketplace upgrade --json [MARKETPLACE_NAME]
codex marketplace remove --json <MARKETPLACE_NAME>
codex plugin add --json <PLUGIN>
codex plugin remove --json <PLUGIN>
```

Code references: `AddMarketplaceArgs.json`, `ListMarketplaceArgs`, `UpgradeMarketplaceArgs.json`, `RemoveMarketplaceArgs.json` in `codex-rs/cli/src/marketplace_cmd.rs`; `AddPluginArgs.json`, `RemovePluginArgs.json` in `codex-rs/cli/src/plugin_cmd.rs`; `AppTemplateSummary`, `AppTemplateUnavailableReason` in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`


### Goal Workflow Fixes
Three goal workflow bugs are fixed:

- Multiline paste in `/goal edit` no longer submits prematurely.
- Idle auto-turns no longer enter Plan mode.
- Goals no longer auto-continue after a terminal turn failure.

Code references: `codex-rs/tui/` (TUI goal editor); `codex-goal-extension` crate now wired into the app-server extension registry.


### Forked Thread Title Preservation
Forked threads now keep the user-assigned title instead of reverting to the original first-prompt name.


### TUI Polish
- The TUI no longer adds extra blank space during streaming.
- Cancelled prompts reopen with the cursor at the end of the text.
- Config write failures now display the underlying cause (validation errors, read-only filesystem issues) rather than a generic failure message.


### Startup Resilience
- `/usr/bin/bash` is now recognized as a valid shell path.
- Linux proxy socket paths are shortened to avoid exceeding the OS socket path length limit.
- Expired OAuth-backed MCP credentials are now pre-refreshed at startup.


### Workspace Instruction Loading
`AGENTS.md` loading is more accurate for remote and symlinked workspaces, so the correct files are consistently picked up. New integration tests cover the global-vs-project precedence and empty-file cases.

Code references: new tests added for `AGENTS.md` loading in `codex-rs/app-server/`

## Additional Changes Beyond Official Notes


### account/usage/read Protocol Schema (new schema file)
A standalone JSON schema file ships for the new endpoint's response type.

Code references: new `codex-rs/app-server-protocol/schema/json/v2/GetAccountTokenUsageResponse.json`; TypeScript equivalents `AccountTokenUsageDailyBucket.ts` and `AccountTokenUsageSummary.ts` under `codex-rs/app-server-protocol/schema/typescript/v2/`


### ReasoningEffort is Now an Open String (Protocol Change)
`ReasoningEffort` was previously a closed enum (`none | minimal | low | medium | high | xhigh`). It is now defined as `string` with `minLength: 1` across all protocol schemas and TypeScript types. Clients that validated effort values against the fixed set must now accept arbitrary non-empty strings to remain forward-compatible.

Code references: `ReasoningEffort` updated in all schema files under `codex-rs/app-server-protocol/schema/json/v2/` and `codex-rs/app-server-protocol/schema/typescript/ReasoningEffort.ts`


### AgentMessageResponseItem Added to ResponseItem Union
A new `agent_message` item type is added to the `ResponseItem` union. It carries `author`, `recipient`, and an array of `AgentMessageInputContent` items (currently supporting `encrypted_content` only).

Code references: `AgentMessageResponseItem`, `AgentMessageInputContent` in `codex-rs/app-server-protocol/schema/json/v2/RawResponseItemCompletedNotification.json`; `AgentMessageInputContent.ts` under `codex-rs/app-server-protocol/schema/typescript/`


### ConfigRequirements Permission Profile Restructure (Protocol Breaking Change)
The `allowedPermissions` field (an array of strings) has been replaced by two new fields:

- `allowedPermissionProfiles`: an object mapping profile name → boolean (whether the profile is shown/selectable)
- `defaultPermissions`: a nullable string naming the default permission profile

This applies to `configRequirements/read` responses and the `ConfigRequirements` schema.

Code references: `ConfigRequirements.allowed_permission_profiles`, `ConfigRequirements.default_permissions` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`; updated `ConfigRequirements.ts`, `ConfigRequirementsReadResponse.json`


### runtime_workspace_roots Now Requires Absolute Paths (Protocol Breaking Change)
The `runtimeWorkspaceRoots` field in `ThreadStartParams`, `ThreadResumeParams`, `ThreadForkParams`, and `TurnStartParams` now requires absolute paths. The previous implementation accepted relative paths and resolved them against the thread's effective `cwd`. Clients that pass relative paths will now receive an error.

Code references: field types changed from `Vec<PathBuf>` to `Vec<AbsolutePathBuf>` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs` and `turn.rs`; `resolve_runtime_workspace_roots()` helper in `codex-rs/app-server/src/request_processors.rs`


### Remote Control Pairing Status Check (Experimental)
A new `remoteControl/pairing/status` experimental request lets clients poll whether a pairing code has been claimed, without needing a WebSocket connection.

Usage:
```json
{
  "method": "remoteControl/pairing/status",
  "id": 1,
  "params": {"pairingCode": "abc-123"}
}
```

Response: `{"claimed": true}` or `{"claimed": false}`. Exactly one of `pairingCode` or `manualPairingCode` must be supplied.

Code references: `RemoteControlPairingStatusParams`, `RemoteControlPairingStatusResponse` in `codex-rs/app-server-protocol/src/protocol/v2/remote_control.rs`; `RemoteControlHandle::pairing_status()` in `codex-rs/app-server-transport/src/transport/remote_control/mod.rs`


### Turn Moderation Metadata Notification (Experimental)
A new `turn/moderationMetadata` server notification is added. It carries per-turn moderation metadata from the model backend.

Code references: `TurnModerationMetadataNotification` in `codex-rs/app-server-protocol/src/protocol/v2/model.rs`; new schema file `codex-rs/app-server-protocol/schema/json/v2/TurnModerationMetadataNotification.json`; marked `#[experimental("turn/moderationMetadata")]` in `codex-rs/app-server-protocol/src/protocol/common.rs`


### Plugin Detail Exposes App Templates and MCP Server Names
`PluginDetail` (returned by `plugin/read`) now includes an `appTemplates` array and correctly populates `mcpServers` for remote plugins. Each `AppTemplateSummary` carries a `reason` field indicating why the template is unavailable (`NOT_CONFIGURED_FOR_WORKSPACE` or `NO_ACTIVE_WORKSPACE`).

Code references: `AppTemplateSummary`, `AppTemplateUnavailableReason` in `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`; `remote_plugin_detail_to_info()` in `codex-rs/app-server/src/request_processors/plugins.rs`


### Optimized Streaming Performance
The `memchr` crate is now used in `codex-message-history` and `codex-mcp` for byte scanning, which speeds up processing of large MCP/Ollama streams and long message histories.

Code references: `memchr` added to `codex-rs/Cargo.toml` workspace dependencies; applied in `codex-rs/message-history/` and `codex-rs/mcp/`


### Faster Session Restore for Large Histories
`resume --last` now checks the state database before scanning local disk, which reduces restore time when the local session history is large.

Code references: `codex-rs/app-server/` session lookup path


### TUI Plugin Discovery Optimization
TUI startup reuses previously loaded plugin discovery results and loads only hook metadata on the critical path, reducing repeated plugin work at startup.


### LTO Changed to Thin for Release Builds
The release profile now uses `lto = "thin"` instead of `lto = "fat"`. This reduces link times with a negligible impact on binary size and runtime performance.

Code references: `[profile.release]` in `codex-rs/Cargo.toml`


### CLI README Simplified
The verbose `codex-rs/README.md` has been replaced with a single pointer to the official documentation at `https://developers.openai.com/codex/cli`.

## Notes

Migration guidance for breaking changes in this release:

`ConfigRequirements.allowedPermissions` is removed. Clients that read `configRequirements/read` responses must update to the new shape:

```typescript
// Before
{ allowedPermissions: string[] | null }

// After
{ allowedPermissionProfiles: { [name: string]: boolean } | null, defaultPermissions: string | null }
```

`runtimeWorkspaceRoots` in thread start/resume/fork and turn start params now rejects relative paths. All paths must be absolute. Update any client that constructed these lists from relative paths to resolve them against a base directory before sending.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.138.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.138.0.md`
