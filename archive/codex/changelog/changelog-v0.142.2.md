# Changelog for version 0.142.2

## Official Release Highlights

The upstream release notes for 0.142.2 describe four new features and several
bug fixes. These are verified and expanded below.

MCP tool search is now the default path for tool discovery: when the model
supports it, all MCP tools are routed through tool_search rather than exposed
directly, regardless of how many tools are registered. macOS authentication
clients gain full system proxy support, including PAC file and WPAD resolution
via Apple's CFNetwork framework — matching the existing Windows implementation.
Plugins can now declare a separate `logoDark` asset so clients on dark themes
use a purpose-built logo instead of inverting or masking the light-mode one.
The `model/safetyBuffering/updated` notification carries two new server-driven
fields — `showBufferingUi` and `fasterModel` — letting clients present richer
safety-buffering UI. On the bug fix side: remote plugin catalog ranking is now
propagated to the featured-plugin list; expired Amazon Bedrock credentials
produce a specific, actionable error message; remote stdio MCP servers now
accept absolute working directories written in the remote platform's path format
(e.g. Windows paths on a Linux server); remote HTTP(S) images in turn input and
dynamic tool responses are rejected at the ingress boundary with a clear
model-visible error; PowerShell commands containing AST regions the safety
classifier cannot inspect now require approval; and Code Mode warns when the
selected model does not advertise Code Mode support.

## New Features


### MCP tools now use tool search by default

What: When the connected model supports tool_search, all MCP tools — regardless
of count — are routed through it rather than exposed directly in the tool list.
The previous threshold-based logic (only deferring when the effective tool set
exceeded 100 tools) and the `ToolSearchAlwaysDeferMcpTools` feature flag are
both removed. Now, tool_search availability alone controls deferral.

Details:
- The `DIRECT_MCP_TOOL_EXPOSURE_THRESHOLD` constant and the feature-flag check
  were removed from `build_mcp_tool_exposure`. The new condition is simply
  `if !search_tool_enabled`.
- App-tool (connector) tools are deferred alongside MCP tools when tool_search
  is available.
- Models and providers that do not support tool_search continue to receive MCP
  tools directly in the tool list — no regression for older models.
- The `ToolSearchAlwaysDeferMcpTools` feature key is accepted but ignored (kept
  as a no-op for compatibility with existing configs that set it).

Code references:
- `build_mcp_tool_exposure` in `codex-rs/core/src/mcp_tool_exposure.rs`
- `Feature::ToolSearchAlwaysDeferMcpTools` marked as a compatibility no-op in
  `codex-rs/features/src/lib.rs`


### macOS system proxy, PAC file, and WPAD support

What: On macOS, Codex now reads system-level proxy settings through Apple's
CFNetwork framework, including WPAD/PAC file resolution. This is equivalent to
the Windows implementation that was already present.

Details:
- Activated when `respect_system_proxy` is enabled in the proxy configuration.
- Supports static HTTP/HTTPS proxies, PAC-by-URL
  (`CFNetworkExecuteProxyAutoConfigurationURL`), and PAC-by-JavaScript inline
  scripts (`CFNetworkExecuteProxyAutoConfigurationScript`).
- SOCKS proxies are recognised but not supported; the client falls back to the
  next candidate or direct.
- PAC execution runs synchronously on a CFRunLoop with a 5-second timeout
  (`PAC_EXECUTION_TIMEOUT`).
- Ordered PAC candidates are currently collapsed to one route, matching the
  existing Windows limitation; retry on failure is deferred to a future release.
- Requires the `system-configuration = "0.7"` crate, added as a macOS-only
  dependency in `codex-rs/codex-client/Cargo.toml`.

Code references:
- `codex-rs/codex-client/src/outbound_proxy/macos.rs` (new file, 382 lines)
- `resolve_platform_system_proxy` in `codex-rs/codex-client/src/outbound_proxy.rs`


### Plugin dark-mode logos

What: Plugins can declare a dedicated dark-mode logo. Clients on dark themes
can display it instead of the light-mode one.

Usage:
In a local plugin manifest (`plugin.json`):
```json
{
  "interface": {
    "logo": "./assets/logo.png",
    "logoDark": "./assets/logo-dark.png"
  }
}
```

In a remote catalog entry, the API response may now include `logoUrlDark`.

Details:
- `PluginInterface` gains two new optional fields: `logo_dark`
  (`Option<AbsolutePathBuf>`) for local installations and `logo_url_dark`
  (`Option<String>`) for remote catalog entries.
- Both fields are nullable and backward-compatible — existing plugins that omit
  them work exactly as before.
- The manifest validator (`codex-rs/skills/src/assets/samples/plugin-creator/`)
  was updated to validate the `logoDark` asset path the same way it validates
  `logo`.
- Interface assets from git-subdir marketplace sources (not locally installed)
  have `logo_dark` cleared, matching the existing behaviour for `logo` and
  `composerIcon`.

Code references:
- `PluginInterface::logo_dark`, `PluginInterface::logo_url_dark` in
  `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`
- `RawPluginManifestInterface::logo_dark` in
  `codex-rs/core-plugins/src/manifest.rs`
- `RemotePluginReleaseInterfaceResponse::logo_url_dark` in
  `codex-rs/core-plugins/src/remote.rs`
- Schema: `logoDark` and `logoUrlDark` in
  `codex-rs/app-server-protocol/schema/json/v2/PluginInterface.ts` and all
  `Plugin*Response.json` schema files


### Richer safety-buffering UI metadata

What: The `model/safetyBuffering/updated` notification now carries two new
server-provided fields — `showBufferingUi` (boolean) and `fasterModel`
(nullable string) — that let clients implement richer buffering UI, such as
surfacing the name of the fallback model that may complete the request faster.

Usage:
```json
{
  "method": "model/safetyBuffering/updated",
  "params": {
    "threadId": "...",
    "turnId": "...",
    "model": "current-model",
    "useCases": ["cyber"],
    "reasons": ["user_risk"],
    "showBufferingUi": true,
    "fasterModel": "faster-model"
  }
}
```

Details:
- `showBufferingUi` is a required boolean in the updated schema. Clients that
  do not need it can ignore it.
- `fasterModel` is nullable; it is populated only when `showBufferingUi` is
  true.
- The values are sourced from server-side HTTP response headers
  `x-codex-safety-buffering-enabled` and `x-codex-safety-buffering-faster-model`,
  parsed in the new `safety_buffering` module and merged into the notification
  before it is emitted.

Code references:
- `ModelSafetyBufferingUpdatedNotification::show_buffering_ui`,
  `ModelSafetyBufferingUpdatedNotification::faster_model` in
  `codex-rs/app-server-protocol/src/protocol/v2/model.rs`
- `codex-rs/codex-api/src/safety_buffering.rs` (new file)
- Schema: `codex-rs/app-server-protocol/schema/json/v2/ModelSafetyBufferingUpdatedNotification.json`


## Improvements


### Remote plugin catalog now returns featured-plugin rankings

Before this fix, featured plugin IDs were only fetched when the legacy curated
marketplace (not remote plugin) was active. The condition now also triggers for
the remote global marketplace, so the featured-plugin list is populated when
either marketplace is configured.

Code references:
- `featured_plugin_ids_for_config` call site in
  `codex-rs/app-server/src/request_processors/plugins.rs` (condition expanded
  to include `REMOTE_GLOBAL_MARKETPLACE_NAME`)


### `multiAgentMode` fields deprecated in favour of Ultra reasoning effort

The `multiAgentMode` parameter on `thread/start`, `thread/resume`,
`turn/start`, and `thread/settings/update` is now documented as
`@deprecated` and is silently ignored. All affected response fields
(`ThreadStartResponse.multiAgentMode`, `ThreadResumeResponse.multiAgentMode`,
`ThreadForkResponse.multiAgentMode`, `ThreadSettings.multiAgentMode`) always
return `explicitRequestOnly`.

Proactive multi-agent behaviour is now controlled exclusively by selecting
`effort: "ultra"` (Ultra reasoning effort). Clients that were setting
`multiAgentMode: "proactive"` should switch to `effort: "ultra"`.

Code references:
- `ThreadStartParams::multi_agent_mode` annotated `@deprecated` in
  `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- `TurnStartParams::multi_agent_mode` annotated `@deprecated` in
  `codex-rs/app-server-protocol/src/protocol/v2/turn.rs`
- `thread_settings_from_config_snapshot` returning `MultiAgentMode::ExplicitRequestOnly`
  unconditionally in `codex-rs/app-server/src/request_processors/thread_summary.rs`


### Ultra reasoning effort maps to `"max"` on the wire

When `ReasoningEffortConfig::Ultra` is selected, Codex now sends
`effort: "max"` to the model API rather than the string `"ultra"`. This
mapping is applied for both regular inference and memory summarisation.

Code references:
- `reasoning_effort_for_request` in `codex-rs/core/src/client.rs`


### Remote stdio MCP servers accept foreign-platform absolute paths

The `cwd` field for remote stdio MCP servers now stores a
`LegacyAppPathString` instead of a `PathBuf`. This allows writing a
Windows-format absolute path (e.g. `C:\Users\openai\share`) on a Linux host
for an MCP server that runs on a remote Windows environment. Previously, the
config parser rejected or misinterpreted foreign-platform path strings.

The `codex doctor` MCP check was updated to skip host-native path existence
and executable resolution checks for remote stdio servers, and instead
validates that the `cwd` is an absolute path string without requiring it to
exist locally.

Code references:
- `RawMcpServerConfig::cwd` changed from `Option<PathBuf>` to
  `Option<LegacyAppPathString>` in `codex-rs/config/src/mcp_types.rs`
- `mcp_check_from_servers` updated in `codex-rs/cli/src/doctor.rs`


### Code Mode warns when selected model lacks metadata

When `features.code_mode = true` or `features.code_mode_only = true` is
configured but the active model does not advertise Code Mode support in its
metadata, Codex now emits a warning message each turn, directing users to
either disable the feature flags or select a Code-Mode-capable model.

Code references:
- `unsupported_code_mode_warning` in
  `codex-rs/core/src/session/code_mode_warning.rs` (new file)
- Called from `codex-rs/core/src/session/mod.rs` at turn construction time


### OpenSSL updated to 3.6.3

The bundled OpenSSL was upgraded from 3.5.5 to 3.6.3 (via `openssl-src
300.6.1+3.6.3`).

Code references: `Cargo.lock` — `openssl-src` version entry


## Bug Fixes

- Expired Amazon Bedrock credentials (HTTP 401 with `"Signature expired:"`
  in the response body) now produce the message: "Amazon Bedrock rejected the
  request because its AWS signature has expired. Refresh your AWS credentials
  and retry. If `AWS_BEARER_TOKEN_BEDROCK` is set, update or unset it, then
  restart Codex." Previously, a generic authorization error was shown.
  (`BEDROCK_EXPIRED_SIGNATURE_MESSAGE` in
  `codex-rs/model-provider/src/amazon_bedrock/error.rs`, new file)

- Remote HTTP(S) images are now rejected at multiple app-server ingress points
  with the model-visible error "remote image URLs are not supported; use an
  inline data URL instead." Affected call sites: `turn/start` input, `turn/steer`
  input, `thread/inject_items` message content, and dynamic tool call responses.
  Inline data URLs (`data:image/png;base64,…`) and `localImage` remain fully
  supported. (`is_remote_image_url` / `REMOTE_IMAGE_URL_ERROR` in
  `codex-rs/app-server/src/image_url.rs`, new file; validation added in
  `codex-rs/app-server/src/request_processors/turn_processor.rs` and
  `codex-rs/app-server/src/dynamic_tools.rs`)

- PowerShell commands containing AST regions the safety classifier cannot
  inspect now require approval. New unsupported regions: `param` blocks,
  `begin`/`process`/`end`/`clean` named blocks, `using` statements, and `trap`
  blocks. The PowerShell parser script (`powershell_parser.ps1`) was updated to
  return `"unsupported"` for these patterns.
  (`codex-rs/shell-command/src/command_safety/powershell_parser.ps1`)

- Cloudflare-blocked requests (HTTP 403 with "Cloudflare" and "blocked" in the
  HTML body) now produce the user-visible message: "Access blocked by
  Cloudflare. This usually happens when connecting from a restricted region
  (status 403 Forbidden)."
  (`api_error_user_message` in `codex-rs/codex-api/src/api_bridge.rs`)

- The `internal_chat_message_metadata_passthrough` field has been removed from
  the `compaction_trigger` response item variant in all protocol schemas and the
  TypeScript generated type. Clients that read this field from `compaction_trigger`
  items will now receive an object without it. Other item types retain the field.
  (`codex-rs/app-server-protocol/schema/json/v2/RawResponseItemCompletedNotification.json`,
  `codex-rs/app-server-protocol/schema/typescript/ResponseItem.ts`)

- `codex mcp list` and `codex mcp get` now display the raw string value of
  the `cwd` field rather than the OS-interpreted `display()` form, ensuring
  foreign-platform paths are shown accurately. (`codex-rs/cli/src/mcp_cmd.rs`)


## Notes

Clients that read `multiAgentMode` from `thread/start`, `thread/resume`,
`thread/fork`, or `thread/settings/update` responses should expect
`explicitRequestOnly` regardless of what was requested. The field is retained
in the wire format for backward compatibility but carries no behavioral meaning.
To opt into proactive multi-agent behaviour, set `effort: "ultra"` on the turn
or thread.

The `turn/start`, `turn/steer`, and `thread/inject_items` methods now reject
requests that include remote HTTP(S) image URLs with a `-32600` JSON-RPC
invalid-request error. Replace remote URLs with inline data URLs
(`data:image/png;base64,…`) or `{"type":"localImage","path":"…"}` input items.


Generated with:
- tool: `harness-investigations@0c752ef-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.142.2.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.142.2.md`
