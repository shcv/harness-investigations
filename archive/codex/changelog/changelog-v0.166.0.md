# Changelog for version 0.166.0

## Release Status

> **Not yet released:** `rust-v0.166.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Version 0.166.0 is a significant development snapshot: the source tag exists, but no published GitHub Release was found during synchronization. It adds keyboard transcript selection, easier Vertex AI configuration, queue-and-resume support, and experimental workspace switching and MCP connection sharing. Compatibility changes include removing detached reviews, enforcing saved-provider consistency, and reducing the default idle-thread unload delay to one minute.

## New Features


### Keyboard Transcript Selection

Select and copy conversation text without a mouse, both in the main transcript and the transcript overlay. The default shortcut is `leader [` when that chord is available; you can assign a direct shortcut instead:

```toml
[tui.keymap.global]
select_transcript = "f6"
```

- Move with arrows, `h`/`j`/`k`/`l`, or word motions `w`/`b`/`e`.
- Start a character selection with `v` or Space, or a line selection with `V`; press `o` to swap ends.
- Search with `/` and navigate matches with `n`/`N`.
- Copy with `y` or Ctrl+C; Enter copies and returns to the latest output.


### Easier Vertex AI Configuration

The existing `gcp` provider now accepts project, location, and credential-file settings directly in `config.toml`. Without an explicit authentication command, Codex uses `gcloud auth application-default print-access-token`, avoiding the need to configure that command yourself.

```toml
model_provider = "gcp"

[model_providers.gcp]
project_id = "my-project"
location = "global"
# Optional; otherwise use Application Default Credentials:
credential_file = "/absolute/path/to/credentials.json"
```

Configured project and location values take precedence over `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`. The location defaults to `global`, and `credential_file` must be absolute.

App-server clients also gain the experimental `account/gcp/setup` method:

```json
{"id":1,"method":"account/gcp/setup","params":{"projectId":"my-project","location":"global"}}
```

Setup checks credentials before saving configuration and selecting GCP. Omitting `credentialFile` clears the active user configuration’s override, but fails without saving if an inherited override would remain. Successful setup does not establish access to a particular Vertex model.


### Queue a Message and Resume Its Chat

`codex queue --resume` queues a message and then attempts to resume the destination chat on the local daemon or selected remote server.

```bash
codex queue --thread "my-session" --message "Continue with the remaining checks" --resume
```

Queueing remains successful if the resume attempt fails; Codex prints a warning. Queued messages use the thread’s saved model.


### Focused Network Diagnostics

`codex doctor --network-only` runs configuration, network-environment, provider HTTP, and Responses WebSocket checks without running the full diagnostic set.

```bash
codex doctor --network-only
```

Diagnostics distinguish a successful WebSocket handshake from an immediate connection closure, while redacting sensitive error details.


### Managed OpenTelemetry Settings

Administrators can now enforce OpenTelemetry settings through `requirements.toml`, including exporters, content-logging controls, span attributes, and tracestate.

```toml
# requirements.toml
[otel]
environment = "production"
log_user_prompt = false
log_agent_responses = false
```

App-server clients see these requirements through `configRequirements/read` and their effective values through `config/read`. Writes that overlap managed settings are rejected. Exporter header values are redacted in configuration responses while remaining available to runtime exporters.


### Proxy-Side Request-Body Secrets

Network MITM actions can replace exact placeholder bytes in request bodies with secrets held by the proxy. This supports integrations that require credentials in a payload rather than a header.

```toml
[permissions.workspace.network.mitm.actions.body.body_secret_substitution]
port = 443
max_body_bytes = 1048576
replacements = [
  { placeholder = "codex-secret-0123456789abcdef", secret = { env_var = "BODY_SECRET" } }
]
```

A matching MITM hook must select the action, and native actions require MITM configuration version 2. Substitution is byte-exact: it does not escape JSON or form values. Compressed bodies, trailers, and supplied payload-integrity headers are rejected; body-size and replacement-work limits apply.


### ChatGPT Workspace Switching [Experimental]

App-server clients can list the active managed ChatGPT login’s workspaces and switch between them without a full logout.

```json
{"id":1,"method":"accountSession/list","params":{"refreshWorkspaceMetadata":true}}
```

Use the returned `sessionId` and a workspace’s `accountId`:

```json
{"id":2,"method":"accountSession/switch","params":{"sessionId":"<session-id>","accountId":"<workspace-id>","allowBrowserLogin":true}}
```

These methods require experimental API access. Switching workspaces closes loaded threads and emits `account/updated` after success; selecting the current workspace leaves its threads running. If SSO is required, clients that allow browser login receive `loginId` and `authUrl` and should await `account/login/completed`. Government workspaces require a separate sign-in.


### Shared Local MCP Connections [Experimental]

Compatible chats in the same process can reuse a local stdio MCP connection, reducing duplicate server launches.

```toml
[features]
mcp_connection_sharing = true
```

Sharing requires MCP `2026-07-28` and compatible server configuration and authentication context. Each chat retains its own catalog state and input-request handling. Legacy servers, servers that request input during startup, and servers requiring per-chat runtime or enterprise-managed credentials remain private.


### Incremental Skill Catalog Updates [Experimental]

Codex can append newly added or edited skills to the model’s context instead of repeatedly publishing a complete catalog. Updates share a metadata budget for the current context window; compaction starts a fresh listing and budget.

```toml
[features]
skill_catalog_deltas = true
```

A separate opt-in, `omit_skill_descriptions = true`, removes descriptions from the model-visible catalog to reduce its size.


### Named Untrusted Context [Experimental]

App-server clients can give untrusted additional context a name and have it presented to the model as a standalone tool output.

```toml
[features]
untrusted_as_tool_output = true
```

Entries in `additionalContext` on `turn/start` or `turn/steer` can include:

```json
{"value":"External material to inspect","kind":"untrusted","name":"external_material"}
```

Names must match `[a-z][a-z0-9_]{0,63}` and are accepted only for untrusted context.


### Local AWS Credential Masking [Experimental]

Local managed commands can use dummy AWS credentials while the network proxy signs authorized requests with real credentials.

```toml
[features]
credential_masking = true
```

This requires a trusted, destination-scoped `aws_sigv4` MITM action; the standard local placeholder is `CODEXMASKEDWORKSPACE`. Actions can now be configured through TOML and combined with body substitution, which runs before signing.

Masked presigned URLs, SigV4a, and AWS signed streaming requests are unsupported. With multiple credential pairs, select the intended placeholder through `AWS_ACCESS_KEY_ID`.


### Standalone Executor [Experimental]

A new `codex-exec-server` executable exposes the executor independently of the main CLI, sharing startup, configuration overrides, and sandbox helper dispatch with `codex exec-server`.

```bash
codex-exec-server --listen stdio
```

The source provides the executable target; this snapshot’s release status does not establish that a standalone binary was published.

## In Development


### Persistent Dynamic Tool Updates

Core can replace a thread’s dynamic tool catalog without starting a turn, record the update, and preserve it through compaction and restoration. Persistent-thread updates remain disabled by a host setting that defaults to `false`; there is no new public app-server method for enabling them.


### Session Browsing Across Multiple Backends

The session picker now has infrastructure for independently paginated backend sources, partial results, and routing actions to the backend that owns a row. The current entry point still supplies a single source, so combined browsing and switching across multiple backends are not yet exposed.

## Other Changes

- Removed `delivery: "detached"` from `review/start`; reviews now run inline on the supplied thread.
- Changed resume and input admission to reject chats whose saved provider differs from the configured provider or conflicts with mandatory policy.
- Changed the default `thread_unload_delay_secs` from `1800` to `60` for threads without subscribers or activity.
- Changed `codex queue` to reject unsupported inherited options, including model overrides, positional prompts, and `--cd` with `--remote`.
- Changed local `PreToolUse`, `PostToolUse`, and `PermissionRequest` hook input to report the tool or approval action’s working directory.
- Changed memory consolidation to use its own `memories.consolidation_service_tier`, defaulting to Standard (`"default"`).
- Changed `features.guardianv2.async_classifier_mode` to a deprecated, ignored setting; asynchronous classification always uses conversations.
- Changed `features.code_mode_tool_description_first` into a compatibility no-op.
- Added `startedAtMs` and `completedAtMs` to thread items returned in live notifications and history.
- Added `process/exited.outputDrainTimedOut` so clients can detect incomplete post-exit output collection.
- Added `hooks/list.threadId` to inspect a loaded thread’s hooks, including selected environments, and `environmentId` to hook metadata.
- Added `workspaceName` to ChatGPT account information and `nativeUsageUsdMicros` to thread usage.
- Added `model_providers.openai.model_catalog_url` for a trusted Codex-format catalog endpoint on an allowed HTTPS ChatGPT host.
- Added `[network_proxy]` as the managed-network requirements spelling, retaining `[experimental_network]` as an alias.
- Added `--strict` to the standalone network proxy, requiring explicit managed constraints and rejecting unknown fields at every typed level.
- Added managed `unsafe_enforce_sqlite_journal_mode` support for migrating existing NFS databases to DELETE journaling.
- Added `features.rollout_budget.enforce_limit = false` to retain budget accounting without stopping when the budget is exhausted.
- Improved policy-block explanations with selectable safer rewrites when the backend supplies recourse metadata; choosing a rewrite starts a new chat.
- Improved the status line with `profile` and `provider` items and processing-tier names such as Standard and Flex.
- Improved dollar-billed thread usage displays to use native dollar amounts rather than credit estimates.
- Improved asynchronous question and answer rendering, including Markdown answers and clearer question captions.
- Improved composer cut-and-paste to preserve image, mention, and large-paste payloads across draft clears and chat switches.
- Improved display math rendering for aligned equations, parenthesized matrices, and integral limits.
- Improved plugin discovery by prefetching catalogs at startup; disable it with `features.plugin_discovery_prefetch = false`.
- Improved FedRAMP routing defaults for marked API keys while preserving explicitly configured endpoints.
- Fixed failed session attachment replacing the active chat’s settings or composer prematurely.
- Fixed unavailable stored images causing prompt preparation problems by replacing unavailable image content with placeholders.
- Fixed Linux unreadable-path glob handling to report inspection errors instead of silently dropping a deny.
- Fixed Windows MXC startup failures involving usable network shares and inaccessible deny paths; unrelated shares are excluded from implicit reads.
- Fixed OTLP HTTP exporters rejecting PEM client identities by explicitly selecting Rustls for mutual TLS.

## Notes

Clients using detached reviews must call `thread/start` and then `review/start` with the new thread ID. To retain conversation history and supply custom review instructions, use `thread/fork` followed by `turn/start`.

Provider mismatches now return structured error data with `type` values `modelProviderMismatch`, `modelProviderNotConfigured`, or `modelProviderPolicyConflict`. Restore or select the saved provider before continuing; changing the provider in a resume request does not bypass validation. `thread/read` remains available for displaying history.

Thread items remain flat JSON objects: timestamps sit beside `type` and `id`, without a nested `payload` field. Rust clients must account for `ThreadItem` becoming a wrapper around `ThreadItemPayload`. Timestamp fields may be null or absent on older servers.

To retain the previous idle-thread timeout, set:

```toml
thread_unload_delay_secs = 1800
```

Policy publishers should continue using `[experimental_network]` until every client and policy-validation layer supports `[network_proxy]`. Do not put both spellings in one requirements layer.

The NFS migration requirement is explicitly unsafe unless other clients on every host remain stopped during replacement. Migration preserves mode bits, but not ownership or ACLs.

OpenAI catalog overrides must serve the Codex catalog format, not `/v1/models`, and receive provider credentials. They do not change inference routing or grant catalog access.


Generated by `harness-investigations@519e1c9-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: raw diff
