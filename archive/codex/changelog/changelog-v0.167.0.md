# Changelog for version 0.167.0

## Release Status

> **Not yet released:** `rust-v0.167.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

This development snapshot makes the agent command center available without a shared daemon, adds image previews to drafts, and improves recovery when a conversation’s model provider changes. It also introduces experimental human approval checkpoints and direct Guardian reviews for app-server clients; managed policies must account for `network` becoming a reserved permission name. The tag `rust-v0.167.0` exists, but no published GitHub Release was found when this snapshot was synced.

## New Features


### Agent command center without a daemon

Browse and switch sessions using an embedded app server. `codex agents --no-daemon` is now supported, and embedded sessions can open the command center without first starting a background server.

```bash
codex agents --no-daemon
```

The command center also shows unread-result indicators and orders tasks by recent activity within their groups. Archiving or deleting the current session returns you to the command center. When quitting would stop other sessions running in the embedded server, Codex asks for confirmation.


### Image previews while composing

Local image attachments now appear as thumbnails above your draft on terminals supporting Kitty graphics or Sixel. Previews follow the order of image references in the draft, with a count for attachments that do not fit.

```bash
codex --image screenshot.png
```

Previews require a local workspace and local execution environments. Viewed local images also gain clickable file links in the conversation history on supported terminals.


### Recovery when a conversation’s provider changes

Conversations remain readable when their provider is missing, differs from the current provider, or conflicts with organization policy. Codex displays a specific explanation and preserves drafts and rejected input.

Where saved history is available, press `c` to prepare a new chat with a draft asking Codex to read the saved conversation and continue. Press `n` to start fresh or `Esc` to browse other chats.


### Plugin-scoped app settings

Configure app availability and tool approval settings beneath a plugin’s configuration. These settings apply connector-wide while that plugin is enabled.

```toml
[plugins."sample@marketplace".apps.calendar.tools.list]
approval_mode = "prompt"
```

Explicit top-level `[apps.<connector>]` fields take precedence. Settings contributed by disabled plugins are ignored.


### Canonical command-rule matching

Execution-policy authors can opt into Unicode canonical caseless matching. This covers every token in the prefix, including alternatives, so rules can recognize case differences and canonically equivalent Unicode spellings.

```python
prefix_rule(
    pattern = ["git", "push"],
    canonical_matching = True,
    decision = "prompt",
)
```

Matching remains case-sensitive by default. Managed `requirements.toml` prefix rules also accept `canonical_matching = true`.


### Google Cloud setup wizard [Experimental]

An opt-in onboarding flow configures Google Cloud Vertex AI. Choose “Sign in another way,” then “Use Google Cloud Vertex AI,” and enter your project ID, location, and optional credential-file path.

```bash
codex --enable gcp_setup_wizard
```

The location defaults to `global`. Leaving the credential path empty uses Application Default Credentials; an explicit path must be absolute on the host running Codex. Setup validates credentials and waits for configuration to be saved before reporting success.


### System proxy settings [Experimental]

The existing system-proxy support is now exposed through `/experimental` as “System proxy.” It lets Codex use macOS or Windows system proxy settings.

```bash
codex features enable respect_system_proxy
```

Restart Codex after changing the setting. On macOS, `codex doctor` also explains how to enable it when a configured system proxy is not being used.


### Managed human approval checkpoints [Experimental]

Administrators can require a fresh human decision for selected commands, even when the conversation normally uses automatic review.

In `requirements.toml`:

```toml
[[rules.prefix_rules]]
pattern = [{ token = "git" }, { token = "push" }]
decision = "prompt-user"
```

App-server clients must advertise both capabilities during `initialize`:

```json
{
  "experimentalApi": true,
  "requiredHumanApproval": true
}
```

The server sends `item/commandExecution/requestApproval` with `kind: "humanCommand"` and a unique `approvalId`.

- Only `accept`, `decline`, and `cancel` are valid decisions.
- Hook approvals, session approvals, and persistent approvals cannot satisfy the checkpoint.
- Pending requests can be replayed when a compatible client reconnects.
- Commands are rejected when no compatible client is available or policy prevents human review.


### Review a recorded command without executing it [Experimental]

App-server clients can request a Guardian assessment of an idle thread’s final injected `exec_command` call.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "thread/guardianReview",
  "params": {
    "threadId": "THREAD_ID"
  }
}
```

Enable `experimentalApi` during initialization. The response contains `callId` and an assessment with outcome, risk level, user authorization, and rationale. `assessment` is `null` when execution policy skips approval.

The method supports ordinary plaintext command calls; it rejects commands requiring a managed human checkpoint and commands intercepted as patches. It subscribes the connection to the thread until `thread/unsubscribe` or disconnection.

## In Development


### Uploaded audio references

The protocol adds `{ "type": "audio", "fileId": "…" }` alongside existing URL-based audio input, with history support for preserving mixed audio-reference order.

Uploaded audio is explicitly rejected by turn handling in this build with “Uploaded audio file inputs are not enabled in this build.” Raw history injection also rejects uploaded audio references. The schema addition does not yet make uploaded-audio prompts usable.


### Switching conversations across backends

Work behind `features.tui_multi_backend` adds switching to saved conversations through their owning backend. It prepares the destination before changing the displayed session and restores drafts and backend-specific configuration.

This remains an off-by-default development path. Switching backends requires the current turn to finish.


### Code Mode output limits and cancellation

`features.code_mode_host_output_truncation` adds bounded output retention in the process-owned Code Mode host, including text, image, and audio budgets and omission reporting. The feature remains off by default.

Separately, `features.interrupt_on_cancel` can interrupt upstream inference when a turn is cancelled. Its implementation requires Responses Lite and an interrupt-capable stream; experimental `thread/sample` requests can override it with `interruptOnCancel`.


### Extension-rendered status line

`features.tui_extensions_statusline` renders the configured status line through the TUI Extensions renderer, including pull-request links and live configuration previews. It remains off by default and currently uses plain text without the native renderer’s theme-color option.


### Earlier app discovery

`features.apps_early_resource_discovery` allows app catalog reads to overlap the initial tool inventory. This startup optimization is implemented behind an off-by-default development flag.


### Message-board access over MCP

A new MCP adapter exposes existing message-board tools with their validation, permissions, and output limits. It requires a host to supply an authorized board connection, caller identity, authentication, and transport; this snapshot does not wire it into a standalone server or new CLI command.

## Other Changes

- Changed managed policy so `permissions.network` defines shared network constraints and cannot name a permission profile.
- Changed executable basename fallback to honor applicable `host_executable()` restrictions for both the command name and matching rule name.
- Changed `features.deferred_tool_world_state` to be enabled by default.
- Added gateway OAuth `credentials_store = "file"` for plaintext storage in `$CODEX_HOME/secrets/gateway_oauth.json`; the default remains `keyring`.
- Added `thread/section/changed` notifications after section moves and reordering, carrying `threadId` and nullable `sectionId`.
- Added `[otel] log_sse_deltas = false` to suppress successful streaming delta logs while retaining errors, completion events, and metrics.
- Added provider capability `cyber_access_programs` so custom providers can explicitly accept Cyber program selections without changing authentication or granting access.
- Added `features.suppress_model_change_announcements` to omit model-ID announcements from incremental model context after switching models.
- Improved the agent picker to label and prioritize agents awaiting approval while retaining the selected agent during refreshes.
- Improved patch approval inspection so visible transcript details can be expanded while the approval dialog remains open.
- Improved Bedrock onboarding fields with cursor editing and paste support, and made cloud setup wait for configuration persistence.
- Improved inline visualizations with variant-carousel controls, accessible tabs, and responsive form styling.
- Added Rex terminal detection and Kitty graphics support.
- Fixed deleting text before a leading `!` unexpectedly switching a normal draft into shell mode.
- Fixed clipboard copying through GNU Screen by forwarding OSC 52 sequences in bounded chunks.
- Fixed terminal images remaining visible after terminal handoffs and improved image restoration around dialogs.
- Fixed hyperlink alignment around tabs, wide characters, and reasoning-effort status-line transitions.
- Fixed `Ctrl+L` clearing to preserve complete detailed history while establishing a new visible scrollback boundary.
- Fixed concurrent network approval requests to coordinate prompts and resolve them correctly across cancellation and turn changes.
- Fixed standalone web search to use the current turn’s search mode and workspace routing.
- Fixed context-token estimates after failed responses or responses without usable usage counts.
- Fixed remote execution authentication recovery to reload and refresh ChatGPT credentials.
- Fixed transient authentication-file read failures discarding cached credentials.
- Fixed remote filesystem compatibility for unrestricted reads against older executors and added explicit rejection of unsupported remote MXC selection.
- Fixed Windows MXC read-only volume grants to recurse and prepared missing parent directories for deny paths.
- Fixed paginated thread resume to restore completed assistant text and respect ascending page boundaries.
- Fixed plugin refreshes to apply explicit session plugin overrides while preserving unrelated settings.
- Fixed plugin download errors exposing signed download URLs.
- Changed package-manager update commands to run from `/`, avoiding project-local package-manager configuration and hooks.

## Notes

For managed `requirements.toml`, rename any permission profile named `network`, then update `default_permissions`, `allowed_permission_profiles`, `extends`, and saved-session references. Profiles named `network` remain valid in user `config.toml`.

Shared network constraints can now use:

```toml
[permissions.network]
enabled = true
```

Do not combine this table with `[network_proxy]` or `[experimental_network]`, including across requirements layers. An empty `[permissions.network]` is rejected; omit it when no constraints are needed. Policy publishers should retain `[experimental_network]` until every consuming client and validation layer supports the replacement spelling.

App-server clients supporting human checkpoints must handle `humanCommand` as a distinct approval kind and return only a one-time decision. Rust users constructing `InProcessClientStartArgs` or `RemoteAppServerConnectArgs` must also supply the new `required_human_approval` field.

Existing URL-based audio JSON remains supported. Generated Rust and TypeScript audio types now represent inline and file references; regenerate bindings as needed, while treating uploaded-file input as unavailable in this snapshot.


Generated by `harness-investigations@f77910e-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: raw diff
