# Changelog for version 0.164.0

## Release Status

> **Not yet released:** `rust-v0.164.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

This is an intermediate development snapshot: the `rust-v0.164.0` source tag exists, but no published GitHub Release was found during the sync. Major additions include reusable prompt presets, inline session settings, model-request hooks, local feedback exports, and experimental thread sampling and file transfers between environments. Client authors should handle file-backed generated images, while configuration authors should review changes to log storage, plugin-hook trust, and network credential rules.

## New Features


### Reusable Prompt and Command Presets

Save frequently used prompts and slash commands in ten numbered slots, then run them from `/presets`. The menu supports creating, editing, deleting, and saving presets from current model, permission, terminal-title, or status-line settings. Where available, the default shortcut is your configured leader followed by `p`.

```toml
[tui.presets.1]
label = "Review changes"
input = "Review my current changes for correctness and missing tests."

[tui.presets.2]
label = "Standard speed"
input = "/model --speed=standard"
```

Presets preserve your existing composer draft. Each input must be nonempty and at most 8,000 UTF-8 bytes; shell commands beginning with `!`, image attachments, and linked mention bindings cannot be saved as preset content.


### Inline Session Settings

Set model options, permissions, terminal titles, and status-line layouts directly through slash-command arguments. These commands make settings reusable in presets and apply to the current session without rewriting saved defaults.

```text
/model --reasoning=high --speed=standard
/permissions <profile-id> --approval-policy=on-request --reviewer=user
/statusline --no-colors
/title --clear
```

`/model` also accepts an available model name and `--speed=flex` or another enabled tier advertised by that model. `/permissions` accepts named profiles, granular approval-policy JSON, and `--reviewer=auto_review`; existing policy restrictions still apply. `/title` and `/statusline` accept ordered item IDs, while calling either without arguments retains its picker.


### Image Previews in the Fullscreen Transcript

The fullscreen transcript can display thumbnails of local image artifacts in terminals supporting Kitty graphics or Sixel. Expanded activity details can reveal image previews alongside their text entries.

```toml
[tui]
fullscreen_transcript = true
```

Previews are bounded in size and clipped to the visible transcript area. Unsupported terminals or images retain their text representation.


### Model-Request Lifecycle Hooks

The new `PreModelRequest` and `PostModelRequest` hooks let scripts observe model requests, including completion, failure, cancellation, and available token usage. Hook input includes the model, session, turn, working directory, and applicable subagent identity.

```toml
[[hooks.PostModelRequest]]
hooks = [
  { type = "command", command = "/absolute/path/to/record-model-request" }
]
```

These hooks observe requests: their output cannot block a response, alter the prompt, or issue control directives. Normal hook enablement and trust requirements apply. Synchronous post-request hooks complete before tool dispatch continues.


### Local Feedback Archives

App-server clients can call `feedback/save` to write a diagnostic ZIP on the server host without uploading it. The method accepts the existing feedback parameters plus `savePath` and returns `savedPath`, `threadId`, and optional `promptHash`.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "feedback/save",
  "params": {
    "classification": "bug",
    "threadId": "<thread-id>",
    "includeLogs": true,
    "savePath": "/absolute/path/to/codex-feedback.zip"
  }
}
```

The destination must be an absolute, previously unused ZIP path. Explicit local exports remain available with `[feedback] enabled = false`; the caller owns the resulting file even if the RPC connection disconnects.


### Startup Configuration Inspection

Inspect effective startup requirements without launching the app-server runtime, environments, plugins, or thread storage.

```bash
codex app-server --print-startup-config
```

The command prints one JSON value containing `appServerVersion` and `configRequirements`, or a structured error. `--startup-client-info` accepts client identity JSON. Recovery clients can add `--startup-sign-out` to sign out before reading fresh requirements; host-owned external authentication cannot be changed through this recovery path.


### GitHub Actions OIDC for the Responses API Proxy

`codex-responses-api-proxy` can exchange GitHub Actions identities for short-lived OpenAI service-account credentials, removing the need for a long-lived OpenAI API key in GitHub secrets.

```bash
printenv ACTIONS_ID_TOKEN_REQUEST_TOKEN | (
  exec env -u ACTIONS_ID_TOKEN_REQUEST_TOKEN -u NODE_OPTIONS \
    NODE_OPTIONS=--disable-sigusr1 \
    codex-responses-api-proxy \
    --github-oidc \
    --oidc-audience "$OPENAI_WIF_AUDIENCE" \
    --identity-provider-id "$OPENAI_IDENTITY_PROVIDER_ID" \
    --service-account-id "$OPENAI_SERVICE_ACCOUNT_ID" \
    --github-oidc-request-url "$ACTIONS_ID_TOKEN_REQUEST_URL"
)
```

This requires an OpenAI workload identity provider and service-account mapping, plus GitHub Actions `id-token: write` permission. Stdin carries GitHub’s request credential, not an already minted OIDC token. Credentials renew during long runs; OIDC mode supports only the default OpenAI Responses upstream.

For the npm launcher, this example requires Node.js 24 or newer. Keep the proxy’s existing privileged-process separation, and remove GitHub credential variables before launching Codex or other untrusted subprocesses.


### Frozen Cloud Skill Catalogs

App-server hosts can supply a fixed JSON skill catalog instead of contacting a live skill service.

```bash
codex app-server --cloud-skills-snapshot /absolute/path/to/skills.json
```

The snapshot supplies skill package metadata and declared resource contents and is loaded once at startup. Normal skill listing, reading, aliases, and pagination remain available; snapshot-backed search is unsupported.


### NFS Database Migration [Experimental]

`codex migrate-nfs-db` converts configured SQLite databases from WAL to DELETE journal mode, retaining the original database and WAL files in backup directories. Runtime database opening now preserves the converted journal mode.

```bash
codex migrate-nfs-db --staging-dir /local/disk/codex-staging
```

The command currently requires Unix. Stop every Codex instance and other SQLite client using these databases on every host before confirming, and keep them stopped until migration succeeds. Staging must be on local storage, and the NFS mount must support cross-client POSIX locking. An explicitly configured `log_dir` excludes the logs database from this migration.


### Single-Response Thread Sampling [Experimental]

App-server clients can request one model response from an ephemeral fork of an existing conversation. `thread/sample` inherits the source’s configuration and context, captures the response before tool execution, and cleans up the temporary thread.

After enabling experimental API access during initialization:

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "thread/sample",
  "params": {
    "threadId": "<thread-id>",
    "expectedTurnId": "<latest-finished-turn-id>",
    "prompt": "Suggest a short title for this conversation."
  }
}
```

The source must be a loaded, idle, persistent root thread, and `expectedTurnId` must identify its latest finished turn. Prompts are limited to 4,000 bytes, output to 64 KiB, and sampling to 30 seconds. Results include the response ID and available token counts; `text` is null if the model attempts a tool call or produces no usable text.

Use `thread/sample/cancel` with the original RPC `requestId` to cancel a pending sample.


### File Transfers Between Environments [Experimental]

The new `multi_env_copy_file` tool lets Codex transfer a file between two selected execution environments without loading its contents into model context.

```toml
[features]
multi_env_copy_file = true
```

Both endpoints must be available, paths must be absolute, and parent directories must already exist. Each endpoint’s permissions apply independently. Interrupted or failed transfers may leave a truncated or partially written destination.


### Live MCP Tool Catalogs [Experimental]

Codex can honor ordinary MCP servers’ tool-list change notifications during a turn, allowing the next model step to use an updated tool catalog.

```toml
[features]
mcp_tool_list_changed = true
```

Stale catalog bindings are invalidated when a notification arrives. This opt-in behavior is separate from the existing Codex Apps catalog refresh path.


### Remote Skill and Plugin Discovery V2 [Experimental]

The V2 executor discovery path integrates remote skill and plugin inventories into the prepared catalog. Skill reads can identify a particular installation, and `skills.installations` exposes installation locations without reading skill contents.

```toml
[features]
executor_capability_discovery_v2 = true
```

This requires a selected remote executor advertising V2 discovery support. Discovery alone does not authorize capabilities; plugin enablement, selected installations, and existing policies still govern use.


### Scoped Network Credential Substitution [Experimental]

Network MITM hooks can constrain credentials to a trusted origin’s scheme and port. Injected headers can require an exact placeholder value before substituting a host-held secret.

For an existing network-proxy permission profile:

```toml
[permissions.my-profile.network.mitm]
version = 2
```

Configure hook `schemes` and `ports`, and set `placeholder` on the relevant `inject_request_headers` entry. Placeholder substitution requires HTTPS on port 443; missing, mismatched, or duplicate header values fail closed. The network proxy must already be enabled.

## In Development


### Runtime Agent Authentication

A new runtime-registration library can create ephemeral runtime identities and sign assertions for OpenAI requests. Configuration scaffolding includes `features.runtime_agent_instances` and `dual_header` or `assertion_only` modes.

Registration, credential ownership checks, and request-authentication adapters are implemented, but this snapshot does not connect the new provider to the normal production authentication path. Setting the feature flag alone does not switch ordinary Codex requests to runtime assertions.


### Customer-Hosted Configuration Servers

Managed requirements gain a `config_server` enrollment block with an HTTPS base URL and optional OAuth settings. The intended bundle route is `codex/config/bundle`, and sessions enforce that the required server’s policy has been applied.

Validation and policy-provenance checks are present, but the inspected changes do not wire a built-in fetcher for this server. This remains integration groundwork rather than a ready-to-use `config.toml` feature.

## Other Changes

- Changed explicit `log_dir` settings to route the SQLite logs database there, unless managed requirements pin `sqlite_home`.
- Changed plugin-hook approval to cover plugin contents as well as hook declarations; modified bundles require renewed approval.
- Changed project configuration rules to reject changes to trusted MITM profiles or their inheritance, with a limited exception for self-contained header-stripping policies.
- Changed MITM authorization matching to reject ambiguous semicolon paths and conflicting duplicate query or header values.
- Changed `incremental_tools` and `mcp_oauth_refresh_coordination` to be enabled by default.
- Changed the Amazon Bedrock setup wizard to be enabled by default, with API-key setup available under alternative authentication methods.
- Changed V2 subagent configuration to preserve the fork prefix by default.
- Removed the effect of `features.worktrees` and `features.realtime_conversation`; worktrees are always available and TUI voice follows platform support.
- Removed the obsolete `stable_environment_tools` flag and marked the already ineffective `transcript_v2` flag as removed.
- Added opt-in `wake_on_agent_messages` to resume idle root sessions when agent mail arrives, subject to interruption and collaboration-mode rules.
- Added opt-in `subagent_thread_environments` so children inherit configured thread environments rather than temporary turn selections.
- Added opt-in `app_server_websocket_compression` with negotiated `zstd-stream-v1` compression for WebSocket and Unix-socket connections.
- Added `--executor-credential-stdin` to remote `codex exec-server` launches for rotating, environment-scoped credentials supplied by a trusted parent.
- Added confidential-client authentication options for enterprise-managed MCP login, including `client_secret_basic` and `client_secret_post`.
- Added managed Desktop storage requirements for `default_project_parent` and `projectless_workspace_root`.
- Added Windows managed-requirements lookup through `HKLM\SOFTWARE\Policies\OpenAI\Codex\RequirementsPath`.
- Added MCP status field `toolListMeta`, realtime start field `voiceSessionId`, and experimental `responsesapiClientMetadataPatch` fields on `turn/start` and `turn/steer`.
- Improved prediction forks with a `thread_unload_delay_secs` override and optional `experimentalDisablePredictionMcp` for applicable Responses Lite conversations.
- Improved the `$` picker to prioritize exact and prefix matches, then frequently selected skills and plugins, respecting history persistence settings.
- Improved keybindings with `super`, `cmd`, and `command` modifiers and consistent configured navigation across settings pickers.
- Improved mouse selection with composer copy-on-select and X11 PRIMARY selection support.
- Improved terminal status reporting with distinct completion, error, and permission/question/authentication blocking states.
- Improved Mermaid flowcharts with `<br>`, `<br/>`, and `<br />` line breaks in node labels.
- Improved managed-daemon maintenance with bounded stderr logging, pruning of obsolete releases, and feature overrides on explicit daemon restart.
- Improved SQLite contention handling and preserved rollout-file access metadata during compression changes.
- Fixed configuration overrides being lost when `-c` arguments appear on both sides of a subcommand.
- Fixed resumed threads losing persisted speed, reasoning-summary, or personality settings when no explicit override was supplied.
- Fixed transient provider model-catalog failures unnecessarily discarding usable cached models; authentication rejections still invalidate them.
- Fixed Windows proxy CONNECT authentication to support Negotiate and NTLM using the signed-in user.
- Fixed macOS protected-metadata write checks for case aliases on case-insensitive filesystems.
- Fixed embedded app-server shutdown hanging when request and notification queues are full.
- Fixed session routing across backend replacements to reject stale picker selections belonging to another backend.
- Fixed enterprise-managed MCP access surviving relevant account, policy, or thread-lifetime revocation.

## Notes

Generated-image items now contain either an inline `result` or a durable `fileId`; clients must support both instead of requiring `result` on every item. Optional `inputImages` records identify local reference files by path and SHA-256. Update strict schemas and exhaustive hook-event handling for the new `PreModelRequest` and `PostModelRequest` values.

An explicit `log_dir` changes where new SQLite logs are written. Existing logs in `sqlite_home` are not automatically migrated, although feedback collection retains a compatibility read path.

Scoped MITM hooks and placeholder substitution require `network.mitm.version = 2`. Older clients reject that key, so configurations using these capabilities require coordinated rollback. Credential-bearing MITM definitions belong in trusted user or managed configuration rather than project overlays.

For experimental turn metadata, `responsesapiClientMetadata` replaces unprotected client entries and an empty object clears them. Use `responsesapiClientMetadataPatch` to merge entries; when both are supplied, replacement runs first and the patch runs second. Reserved keys remain protected.

Remove obsolete feature toggles from configuration. Use `tui.fullscreen_transcript` for fullscreen transcript behavior; `worktrees = false` and `realtime_conversation = false` no longer disable their respective capabilities.


Generated by `harness-investigations@835da7c-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: raw diff
