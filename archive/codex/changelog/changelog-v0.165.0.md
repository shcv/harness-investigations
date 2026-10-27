# Changelog for version 0.165.0

## Release Status

> **Not yet released:** `rust-v0.165.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

This development snapshot adds a built-in Google Cloud Vertex AI provider, GPT-6.1 Terra catalog entries, finer session filtering, and configurable automatic-review deadlines. App-server clients gain experimental attached forks and memory-summary reads; trace consumers must account for schema version 2, and session lookup now defaults to the current directory rather than related worktrees. The source tag `rust-v0.165.0` exists, but no published GitHub Release was found during the supplied sync; this changelog does not imply published binaries or assets.

## New Features


### Google Cloud Vertex AI Provider

Use Google Cloud credentials and a Google Cloud project to run Codex through Vertex AI’s OpenAI-compatible endpoint. The built-in provider uses Application Default Credentials through `gcloud`, without requiring an OpenAI login.

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="your-project-id"
codex -c model_provider="gcp" -m gpt-6.1-sol
```

- `GOOGLE_CLOUD_LOCATION` selects the location; it defaults to `global`.
- The bundled catalog includes `gpt-6-astra`, `gpt-6-luna`, `gpt-6.1-sol`, and `gpt-6.1-terra`. Actual availability depends on the provider.
- `[model_providers.gcp]` accepts `base_url`, `auth`, and `http_headers` overrides. Supplying `base_url` removes the requirement for `GOOGLE_CLOUD_PROJECT`.
- This provider disables reasoning summaries, image generation, built-in web search, and Responses Lite.


### GPT-6.1 Terra Model Selection

The bundled model catalog now includes GPT-6.1 Terra, with reasoning levels from `low` through `ultra`. Both Amazon Bedrock catalogs also include its provider-specific model ID.

```bash
codex -m gpt-6.1-terra
```

For an existing Bedrock configuration:

```bash
codex -c model_provider="amazon-bedrock" -m openai.gpt-6.1-terra
```

Catalog inclusion does not guarantee account access or backend availability.


### Separate Directory and Repository Session Views

The resume and fork picker now distinguishes `Cwd`, `Repo`, and `All`. `Cwd` limits results to the current directory; `Repo` includes corresponding directories in linked Git worktrees. The `Repo` option appears when multiple local worktrees are available.

```bash
codex resume
```

Use the picker’s filter control to change scope. The Command Center also gains a `Directory` grouping alongside project, status, and model grouping. Directory grouping remains local to the current view rather than being saved to `config.toml`.


### Configurable Automatic-Review Timeout

Control how long Guardian may spend reviewing an approval request, including setup and retries.

```toml
[auto_review]
timeout_ms = 180000
```

The default remains 90,000 milliseconds. Set `timeout_ms = 0` to remove the overall review deadline; cancellation, retry limits, and independent transport timeouts still apply.


### Managed Domains That Require Review [Experimental]

Administrators can designate host patterns that must enter the network approval flow even when ordinary allow rules would permit them. Configure this in managed `requirements.toml`:

```toml
[experimental_network]
enabled = true
allowed_domains = ["**.example.com"]
review_domains = ["sensitive.example.com"]
```

Explicit denials take precedence. Existing approval caching, permission hooks, and reviewer routing still apply.

These selectors cannot be set through ordinary proxy configuration. Remote execution requires an exec-server advertising `networkProxyReviewDomains`; Codex rejects execution when the selected server cannot enforce the requirement. App-server clients can inspect the selectors through `configRequirements/read` as `reviewDomains`.


### Attached Conversation Forks [Experimental]

App-server clients can create persistent side conversations attached to a source thread while keeping them out of ordinary thread listings. After enabling experimental API access:

```json
{
  "id": 1,
  "method": "thread/fork",
  "params": {
    "threadId": "<source-thread-id>",
    "attachToSource": true
  }
}
```

Retrieve them explicitly:

```json
{
  "id": 2,
  "method": "thread/list",
  "params": {
    "attachedToThreadId": "<source-thread-id>"
  }
}
```

- Attached forks require local thread storage.
- `attachToSource` cannot be combined with `ephemeral` or `deferGoalContinuation`.
- `attachedToThreadId` cannot be combined with `parentThreadId` or `ancestorThreadId`; its results include empty attached threads.
- A source thread cannot be deleted while attached threads remain.


### Read a Thread’s Memory Summary [Experimental]

App-server clients can retrieve the memory summary selected by a loaded thread, including its thread-specific memory configuration.

```json
{
  "id": 3,
  "method": "thread/memory/read",
  "params": {
    "threadId": "<loaded-thread-id>"
  }
}
```

The response contains `summary`, either a string or `null`. Start or resume the thread first. The result is `null` when memory use is disabled or the selected summary is missing, unreadable, or blank; the method never falls back to another memory version.

## In Development


### Guardian V3 Evidence Storage

A new Guardian V3 component establishes durable, thread-owned evidence storage in a separate message-board namespace. It does not yet ingest evidence, perform reviews, start background work, or expose model tools.

The `features.guardianv3` setting is off by default. Enabling it should not be interpreted as enabling a complete replacement reviewer.


### Multiple Conversation Backends in the TUI

The TUI gains infrastructure for adopting and shutting down several backend sessions. The new `features.tui_multi_backend` flag is off by default, and the normal launch path still supplies a single backend. Automatic discovery and user-facing selection remain unfinished.


### Custom Managed-Configuration Servers

New loading and authentication components can fetch managed configuration from a custom `config_server`, with optional OAuth, authentication recovery, and caches isolated by endpoint and sign-in identity.

The snapshot adds the loader interfaces, but does not connect them to normal startup call sites. The existing configuration declaration alone should not be treated as a newly working enterprise policy-distribution flow.


### Execution-Environment Lifecycle Hooks

The hook runtime can accept managed hook declarations from individual execution environments and run command hooks through the owning environment. Tool hooks target the relevant environment; hook input uses its working directory and withholds controller-side transcript paths.

The runtime dispatch and validation are implemented, but ordinary environment configuration still needs to supply these declarations. This is groundwork for environment-owned hooks rather than a new local configuration switch.


### Proxy-Side AWS Request Signing

The network proxy gains an AWS SigV4 signing action that keeps real credentials in the trusted proxy while workloads use placeholder credentials. Signing runs after network and HTTP-hook authorization, with bounded request bodies and rejection of unsupported streaming signatures.

The signing implementation is present, but this snapshot does not expose it through the normal named MITM actions in `config.toml`.

## Other Changes

- Changed trace bundle manifests and reduced trace state to schema version 2.
- Changed fresh profiles with memories enabled to select memory v2 unless a version is explicit or `dual_write = false`; existing v1 workspaces retain v1.
- Changed `reasoning_effort_override` to enabled by default for models supporting reasoning-effort updates.
- Changed MCP catalog overlays to preserve explicit disables and managed-policy denials across replacement registrations.
- Added the `gcp` account variant and `modelNotFound` error classification to the app-server protocol.
- Added negotiated `codex/network-policy-meta` metadata for trusted ChatGPT MCP servers, carrying effective network restrictions without proxy endpoints or credentials.
- Improved prediction forks and `thread/sample` to preserve inherited tool declarations while explicitly marking MCP tools unavailable.
- Improved paginated thread resume to reuse prepared model context when its stored history revision remains current.
- Improved encrypted credential reads by sharing cached decryption results while continuing to check the credential file and keyring.
- Improved enterprise MCP sign-in errors with sanitized failure-stage and HTTP-status details.
- Improved external-agent memory import to respect the selected memory pipeline and synchronize both versions when needed.
- Improved trace reconstruction to distinguish accepted conversation history from unaccepted model output and preserve Responses item identities.
- Fixed unavailable-model errors triggering recoverable connection handling instead of terminating with the provider’s error.
- Fixed cancelled or timed-out MCP tool calls leaving remote work running by sending cancellation notifications.
- Fixed MCP byte transports allowing cancellation messages to overtake their corresponding requests.
- Fixed memory import and consolidation racing over the same workspace by retaining exclusive ownership through completion.
- Fixed terminal writes and cleanup acting on a replacement process after a terminal session ID was reused.
- Fixed Windows sandbox helper startup losing `SystemRoot`.
- Fixed marketplace host-policy checks accepting ambiguous HTTP URL user information containing backslashes.
- Fixed credential masking collisions involving configured providers and embedded credential values.
- Fixed explicit final-answer messages allowing pending agent mail to continue the same turn when the answer had no visible text.

## Notes

Session lookup is now directory-scoped by default, including latest-session lookup. Use `Repo` in the picker to include linked worktrees, or `--all` where appropriate for a broader search.

To keep the previous memory pipeline on a fresh profile, select it explicitly:

```toml
[memories]
version = "v1"
```

Trace consumers should recognize schema version 2 and the revised meaning of `conversation_item_ids`: it represents accepted model-visible conversation history. Unaccepted output remains accessible through its inference call. Conversation items can also contain `responses_item_id`, and payload references can contain `content_sha256`.

App-server clients with exhaustive account or error handling should add `gcp` and `modelNotFound`. Clients using attached forks must delete attached threads before deleting their source.


Generated by `harness-investigations@1484912-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: raw diff
