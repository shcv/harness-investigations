# Changelog for version 0.159.0

## Release Status

> **Not yet released:** `rust-v0.159.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.158.0, this snapshot adds structured Guardian circuit-breaker errors, extends history pagination and MCP status queries, strengthens executor credential isolation, and improves terminal rendering and session recovery. It also introduces opt-in interruption and proxy-routing behavior, expands sandbox protections, and removes the bundled `plugin-creator` skill.

The source tag `rust-v0.159.0` exists, but no published GitHub Release was found when the sync ran. This changelog describes an intermediate development snapshot; it does not imply that official release notes, binaries, or other release assets were published.

## New Features


### Structured Guardian Circuit-Breaker Errors

What: A new `auto_review.circuit_break_action` setting lets clients receive a structured error when Guardian stops a turn after repeated denials.

Usage:

```toml
[auto_review]
circuit_break_action = "strict"
```

Details:

- `"strict"` preserves the existing warning and interruption, while attaching a structured `tooManyDenials` error.
- The app-server reports the turn as interrupted, with details in `turn.error`. Those details also survive history reconstruction.
- This does not change the denial threshold or introduce a separate error notification for the interruption.
- The default value, `"default"`, retains the previous warning-and-interruption behavior without structured error details.
- Older clients may not recognize the new error variant when reading shared history. Update those clients before enabling strict mode.

Code references:

- `AutoReviewToml.circuit_break_action` and `CircuitBreakAction` in `codex-rs/config/src/config_toml.rs`
- `ReviewHost::interrupt` in `codex-rs/core/src/guardian/review_request.rs`
- `CodexErrorInfo::TooManyDenials` in `codex-rs/app-server-protocol/src/protocol/v2/shared.rs`
- `TurnAbortedEvent.error` in `codex-rs/protocol/src/protocol.rs`
- Updated schema `codex-rs/app-server-protocol/schema/json/v2/TurnCompletedNotification.json`

## Improvements


### Start History Pagination From a Known Item

The existing `thread/items/list` method now accepts an item anchor as an alternative to an opaque string cursor. Clients can load history around an item they already know without first obtaining a pagination cursor.

Usage:

```json
{
  "method": "thread/items/list",
  "params": {
    "threadId": "<thread-id>",
    "turnId": "<turn-id>",
    "cursor": {
      "type": "item",
      "itemId": "<item-id>"
    },
    "sortDirection": "asc",
    "limit": 50
  }
}
```

Details:

- Anchors are exclusive: ascending pagination returns items after the anchor; descending pagination returns items before it.
- An item anchor requires a non-empty `turnId` and an item belonging to the requested visible turn.
- Invalid anchors produce an invalid-parameters error.
- Existing string cursors remain accepted. Continue subsequent requests using the string cursor returned in the response.

Code references:

- `ThreadItemsListParams`, `ThreadItemsListCursor`, and `ThreadItemsListAnchor` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- Anchor validation in `codex-rs/app-server/src/request_processors/thread_processor.rs`
- `page_item_rows` in `codex-rs/thread-store/src/local/thread_history/segment_paging.rs`
- Updated schema `codex-rs/app-server-protocol/schema/json/v2/ThreadItemsListParams.json`


### Query the Status of One MCP Server

The existing `mcpServerStatus/list` method gains an optional `serverName` filter, allowing clients to inspect one server without discovering every configured server.

Usage:

```json
{
  "method": "mcpServerStatus/list",
  "params": {
    "threadId": "<thread-id>",
    "serverName": "docs"
  }
}
```

Details:

- With `threadId`, the request reuses that thread’s MCP runtime and connection.
- Discovery waits for the selected server rather than unrelated servers.
- Without `threadId`, discovery is limited to the named server.
- An unknown name returns an empty result. Omitting `serverName` preserves the existing full-list behavior.

Code references:

- `ListMcpServerStatusParams.server_name` in `codex-rs/app-server-protocol/src/protocol/v2/mcp.rs`
- `list_mcp_server_status_response` in `codex-rs/app-server/src/request_processors/mcp_processor.rs`
- `server_status_snapshot` in `codex-rs/codex-mcp/src/runtime/status.rs`
- Updated schema `codex-rs/app-server-protocol/schema/json/v2/ListMcpServerStatusParams.json`


### Better Handling of Empty Sessions

Fresh persistent threads can now be archived before their first turn. Archival materializes the thread’s stored history first, and archived-thread listings include threads with empty previews.

Usage:

```json
{
  "method": "thread/archive",
  "params": {
    "threadId": "<fresh-thread-id>"
  }
}
```

In the terminal UI, blank sessions backed by a daemon or remote app-server remain available when navigating between sessions. Draft input and pending thread-setting updates are retained. This navigation behavior excludes embedded and ephemeral sessions.

Code references:

- `ThreadRequestProcessor` archival handling in `codex-rs/app-server/src/request_processors/thread_processor.rs`
- Archived-thread filtering in `codex-rs/state/src/runtime/threads.rs` and `codex-rs/rollout/src/list.rs`
- `start_fresh_session` in `codex-rs/tui/src/app/session_lifecycle.rs`
- Blank-session handling in `codex-rs/tui/src/app/agents_overview.rs`
- `ThreadInputState.pending_thread_settings` in `codex-rs/tui/src/chatwidget/user_messages.rs`


### More Mermaid Syntax Renders in the Terminal

The existing Mermaid renderer supports additional flowchart syntax and handles labels more faithfully.

Usage: Include the following inside a `mermaid` Markdown fence:

```text
flowchart LR
  A & B --> C
  C -. retry .-> A
```

Details:

- Flowcharts support undirected and bidirectional solid edges, plus directed, undirected, and bidirectional dashed edges.
- `&` groups support fan-in and fan-out.
- Spaced edge labels such as `-- label -->` and `-. label .->` are recognized.
- Omitting a flowchart direction now defaults to top-to-bottom.
- Quoted flowchart labels preserve delimiters such as brackets, pipes, and semicolons.
- Other diagram families accept more printable punctuation and literal ampersands. Repeated state descriptions are retained rather than replacing earlier text.
- Existing bounds still apply, including 16 nodes and 24 edges after group expansion. Unsupported diagrams retain their source instead of rendering a partial diagram.

Code references:

- Flowchart parsing in `codex-rs/mermaid/src/parse.rs`
- Statement and label parsing in `codex-rs/mermaid/src/syntax.rs`
- Relationship parsing in `codex-rs/mermaid/src/relations.rs`
- State descriptions in `codex-rs/mermaid/src/state.rs`
- Supported syntax and limits in `codex-rs/mermaid/README.md`


### Keep or Dismiss Reviewed Warnings

The existing warnings viewer now distinguishes warnings you have reviewed from those you still want to retain.

Usage: Open `/warnings` or press the default `F2` shortcut. Press `k` to keep the current warning and advance.

Details:

- Closing the viewer dismisses warnings that were actually displayed, except those explicitly kept.
- Unvisited warnings remain available.
- Pressing `k` on the final warning keeps it and closes the viewer.
- Dismissals are scoped to the current transcript. A warning whose details change can appear again.
- Viewer keystrokes are consumed rather than being inserted into the draft.

Code references:

- `WarningsView::close` and `WarningsView::handle_key` in `codex-rs/tui/src/bottom_pane/warnings_view.rs`
- Warning retention in `codex-rs/tui/src/chatwidget/warnings.rs`
- Viewer hints in `codex-rs/tui/src/bottom_pane/warnings_view_render.rs`


### Clearer Session Status and Command Output

Session headers and `/status` use a simpler borderless layout. Status values such as long paths and identifiers wrap rather than being prematurely truncated, and completed turns display their duration even when they took less than a minute.

Collapsed command output now indicates how many retained lines can actually be revealed and shows the configured expansion shortcut. Counts exclude output that is no longer available, making the disclosure more accurate.

Starting, clearing, or switching sessions also stops inserting the previous session’s usage summary and resume hint into the new transcript.

Code references:

- `SessionHeaderHistoryCell` in `codex-rs/tui/src/history_cell/session.rs`
- Status rendering in `codex-rs/tui/src/status/card.rs` and `codex-rs/tui/src/status/format.rs`
- Completion duration handling in `codex-rs/tui/src/chatwidget/completion.rs`
- `command_disclosure` in `codex-rs/tui/src/exec_cell/compact.rs`
- Disclosure layout in `codex-rs/tui/src/transcript_view/layout.rs`
- Session transitions in `codex-rs/tui/src/app/session_lifecycle.rs`


### Easier Transcript Navigation During Approvals

The terminal UI allows mouse-wheel scrolling over the visible transcript while a modal is open, so users can review context before responding to an approval request. The modal continues to own keyboard input and other interactions.

Supported Ghostty and Kitty sessions also show a hand pointer over links while Codex owns the transcript screen. Pointer-shape changes are disabled under terminal multiplexers and restored during terminal handoffs.

Code references:

- `handle_owned_transcript_event` in `codex-rs/tui/src/app/owned_transcript.rs`
- Link-hover handling in `codex-rs/tui/src/app/link_hover.rs`
- `Tui::set_link_pointer` and `LinkPointer::restore` in `codex-rs/tui/src/tui/link_pointer.rs`


### More Stable Skill and Tool Discovery

Skill-catalog budgeting is retained across reconnects, resume, and compaction. Temporary executor unavailability no longer causes the cloud catalog to expand into space previously reserved for filesystem skills.

When an unchanged executor skill catalog becomes available again, Codex can use a short availability notice if the original catalog remains in context. If compaction removed it, Codex supplies the full catalog again.

Tool namespace rendering also reserves space for names before distributing space among descriptions, reducing the chance that lengthy descriptions hide other available namespaces.

Code references:

- `CatalogBudgetAllocation` and `render_catalogs` in `codex-rs/ext/skills/src/world_state_catalogs.rs`
- Executor-catalog restoration in `codex-rs/ext/skills/src/world_state.rs`
- World-state retention in `codex-rs/core/src/session/mod.rs`
- `truncate_namespace_rows` in `codex-rs/core/src/context/world_state/tools_budget.rs`


### More Persistent Connection Recovery

The terminal UI now continues reconnecting throughout its existing two-minute recovery window, using eight-second delays after the initial backoff. Previously, the fixed attempt count could stop recovery well before that window expired.

Newly provisioned remote executors also receive additional time to become reachable: registry responses reporting `environment_offline` can be retried for up to five minutes after provisioning readiness. Other failures retain their existing retry limits.

Code references:

- `reconnect` in `codex-rs/tui/src/app/reconnect.rs`
- `PROVISIONED_ENVIRONMENT_CONNECT_TIMEOUT` and provisioning-aware retry handling in `codex-rs/exec-server/src/client_transport.rs`


### Explicit Environment Proxy Requirements

Execution-environment owners can now declare that managed proxy routing is required, even when direct network access is restricted.

Usage: Set `"requiresProxy": true` in the existing environment network-policy object.

This activates filtered networking through the managed proxy. It does not grant unrestricted direct access or override destination restrictions. Omitting the field, or setting it to `false`, leaves activation to the controller and command permissions.

Code references:

- `EnvironmentNetworkPolicy.requires_proxy` in `codex-rs/network-proxy/src/environment_policy.rs`
- Managed-network activation in `codex-rs/core/src/tools/orchestrator.rs`


### Linux Sandbox Capability Reporting

Executor capability responses gain two optional fields:

```json
{
  "linuxRootWritePreservesDevices": true,
  "linuxApprovedRootWritePreservesRestrictions": true
}
```

These let client authors identify executors with the corresponding Linux sandbox support. Both default to `false` when absent; the updated implementation advertises them on Linux.

These capability fields do not themselves grant filesystem permissions or enable a new approval workflow.

Code references:

- `EnvironmentCapabilities` and `EnvironmentInfo::local` in `codex-rs/exec-server-protocol/src/protocol.rs`

## Bug Fixes

- **Executor-discovered MCP servers no longer fall back to host environment credentials.** Credential policy follows where a server declaration originated and remains attached through caching and reconnection. Executor-owned declarations also cannot acquire host environment-header helpers through cached registration. Older executors that lack executor-side credential resolution now receive an explicit upgrade error. Host-configured servers retain their existing credential behavior. (`McpCredentialPolicy` in `codex-rs/codex-mcp/src/server.rs`; catalog construction in `codex-rs/codex-mcp/src/catalog.rs`; `resolve_bearer_token` in `codex-rs/codex-mcp/src/rmcp_client.rs`.)

- **`.aws` directories receive default write protection beneath writable roots.** AWS configuration and credential-related metadata join the existing protected metadata paths. Explicit filesystem-policy rules continue to determine intentional exceptions. (`PROTECTED_METADATA_PATH_NAMES` and `FileSystemSandboxPolicy` in `codex-rs/protocol/src/permissions.rs`.)

- **Linux sandboxes preserve standard devices when `/` is writable.** Root mounts no longer shadow the sandbox’s device setup. Related mount handling avoids redundant metadata binds that could reopen a denied symlink target. (`create_filesystem_args` in `codex-rs/linux-sandbox/src/bwrap.rs`; `get_writable_roots_with_cwd_inheriting_root_metadata` in `codex-rs/protocol/src/permissions.rs`.)

- **Permitted macOS HTTPS requests can reach system certificate-trust evaluation.** Network-enabled and applicable managed-proxy sandbox profiles allow the trust-evaluation service needed by system networking libraries. Offline, Unix-socket-only access does not receive the same expansion. (`dynamic_network_policy_for_network` in `codex-rs/sandboxing/src/seatbelt.rs`.)

- **MCP Apps no longer receive an invented inline display preference.** `mcpAppUi` is populated only for an explicit supported `inline` or `fullscreen` preference. The app resource URI is retained independently, allowing clients to apply resource defaults when no preference is supplied. (`mcp_tool_metadata` in `codex-rs/core/src/mcp_tool_call.rs`; behavior documented in `codex-rs/app-server/README.md`.)

- **Guardian retains confirmed messages sent through nested code-mode calls.** Successful User Messaging sends are recorded before later callbacks or cancellation can lose them, with ordering retained across compaction, resume, and rollback. Changes to this context invalidate stale review evidence. Assistant messages remain contextual evidence rather than user authorization. (`record_confirmed_code_mode_send` in `codex-rs/core/src/tools/user_messaging.rs`; retained-context handling in `codex-rs/core/src/session/retained_context.rs`; review validation in `codex-rs/core/src/guardian/review_request.rs`.)

- **Model-switch compaction preserves the previous access program.** Compaction of history produced by the previous model now uses that turn’s saved `cyber_access_program`, avoiding mismatches with the newly selected model’s settings. (`maybe_run_previous_model_inline_compact` in `codex-rs/core/src/session/turn.rs`; prompt construction in `codex-rs/core/src/compact.rs`; `PreviousTurnSettings` in `codex-rs/history/src/compaction_resume_metadata.rs`.)

- **Shared executors avoid process-ID collisions.** Execution requests always receive a unique suffix, including requests that previously bypassed the suffix because they did not require sandbox or snapshot handling. (`exec_server_params_for_request` in `codex-rs/core/src/unified_exec/process_manager.rs`.)

- **Code-mode termination drains output reliably.** Terminating a cell clears stale yield state and keeps observing it until its terminal result, preventing intervening lifecycle messages from ending the drain early. (`run_cell` in `codex-rs/code-mode-runtime/src/cell_actor/mod.rs`.)

- **Inter-agent delivery respects turn finalization.** Message-board delivery checks whether the active turn still accepts mailbox input, avoiding reopening a finalized answer. Remote board notifications also enforce frame-size bounds before SSE parsing and reject invalid UTF-8. (`deliver_mailbox_communication_to_current_turn` in `codex-rs/core/src/session/input_queue.rs`; `codex-rs/core/src/agent_message_board.rs`; `RemoteAgentMessageBoard::notifications` in `codex-rs/agent-message-board-client/src/client.rs`.)

- **Long Unix socket paths can connect through shorter canonical paths.** When an overlong path fails with `InvalidInput`, connection handling retries its canonicalized form. This helps daemon connections through long symlink-based `CODEX_HOME` paths. (`platform::connect_stream` in `codex-rs/uds/src/lib.rs`.)

- **Zsh aliases containing quotes replay correctly.** Source-based shell snapshots capture aliases with `NO_RC_QUOTES`, avoiding incompatible quoting during replay. (`capture_script` in `codex-rs/shell-command/src/shell_snapshot_capture.rs`.)

- **Windows sandbox provisioning fails faster when the service is unavailable.** Connection handling checks service state, bounds startup waiting, and avoids sending requests after the deadline. Registered-runtime failures also include more useful stage context. (`codex-rs/windows-sandbox-rs/src/provisioning_client.rs`; `codex-rs/windows-sandbox-service/src/registered_runtime.rs`.)

- **External-editor handoffs preserve the screen and restore terminal input modes.** The editor can open without unnecessarily clearing Codex’s visible frame, while keyboard and mouse modes are released and restored around the handoff. Windows SGR mouse reporting is handled explicitly. (`Tui::with_restored` in `codex-rs/tui/src/tui.rs`; `codex-rs/tui/src/tui/alternate_screen.rs`.)

- **Additional Markdown and math cases render correctly.** Inline `$0$` is recognized as math; `\bigwedge`, `\bigl`, and `\bigr` are supported; display-mode conjunction operators support stacked limits. Empty list items retain their markers, while streaming avoids prematurely committing incomplete list syntax. (`MathMarkdown` in `codex-rs/tui/src/markdown_render/math.rs`; `MathParser` in `codex-rs/tui/src/markdown_render/math/render.rs`; list handling in `codex-rs/tui/src/markdown_render.rs` and `codex-rs/tui/src/streaming/controller.rs`.)

## In Development


### Faster Steering Interruptions [Experimental]

What: The new `instant_interrupt` feature lets incoming user input preempt selected ongoing work so steering can be handled sooner.

Usage:

```toml
[features]
instant_interrupt = true
```

Status: Runtime-gated, marked `UnderDevelopment`, and disabled by default.

Details:

- User input can preempt sampling waits and retry delays, and cause code-mode execution or waiting to yield.
- For models using Responses Lite over WebSocket, Codex can send `response.interrupt` and drain the terminal response before reusing the connection.
- Other WebSocket paths finish draining the response before following up. HTTP streaming has a separate cancellation path.
- This is not a promise of immediate cancellation for every model, provider, or running tool. Partial-item reconciliation remains unfinished in one streaming path.

Code references:

- `Feature::InstantInterrupt` in `codex-rs/features/src/lib.rs`
- User-input watching in `codex-rs/core/src/session/input_queue.rs`
- Preemption handling in `codex-rs/core/src/session/turn.rs`
- `run_websocket_response_stream` in `codex-rs/codex-api/src/endpoint/responses_websocket.rs`
- Code-mode integration in `codex-rs/core/src/tools/code_mode/mod.rs`


### Private-IP Routing Through an Upstream Proxy [Experimental]

What: The experimental exec-server gains an option allowing permitted private-IP destinations to use an inherited upstream proxy.

Usage:

```bash
codex exec-server --proxy-private-ips-via-upstream
```

Alternatively:

```bash
CODEX_EXEC_SERVER_PROXY_PRIVATE_IPS_VIA_UPSTREAM=true codex exec-server
```

Status: Opt-in behavior on the existing experimental `exec-server` command.

Details:

- Applicable private destinations can use the configured `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`.
- Supported address classes include private IPv4, carrier-grade NAT space, and IPv6 unique-local addresses.
- Loopback remains local.
- Existing destination restrictions and upstream-proxy permissions still apply.
- If no valid upstream proxy applies, the request connects directly. This flag therefore does not enforce mandatory proxy routing.
- A connection failure after selecting a proxy is not silently retried as a direct connection.

Code references:

- `ExecServerCommand.proxy_private_ips_via_upstream` in `codex-rs/cli/src/exec_server_command.rs`
- `ProxyConfig::proxy_for_target` in `codex-rs/network-proxy/src/upstream.rs`
- `is_private_network_ip` in `codex-rs/network-proxy/src/policy.rs`
- Managed-proxy setup in `codex-rs/exec-server/src/process_sandbox.rs`


### Guardian History Independent of Parent Compaction [Experimental]

What: An alternate Guardian history mode retains a separate review transcript instead of depending on the parent agent’s compacted transcript.

Usage:

```toml
[features]
guardian_reuse_parent_compaction = false
```

Status: Non-default behavior selected by disabling an existing feature whose default remains `true`. The configuration switch itself is not new.

Details:

- The alternate path now selects `GuardianContextMode::Independent`.
- Review history retains original transcript envelopes separately from parent compaction and persists the information needed for recovery.
- Users retaining the default `guardian_reuse_parent_compaction = true` continue using parent-context review.

Code references:

- `GuardianContextMode::Independent` in `codex-rs/core/src/context/guardian_context_mode.rs`
- `HistoryManager::for_session` in `codex-rs/core/src/context_manager/history.rs`
- Guardian-history persistence in `codex-rs/history/src/guardian_history.rs`
- Parent-compaction handling in `codex-rs/ext/guardian-v2/src/async_scorer/parent_compaction.rs`

## Notes


### Bundled Plugin-Creator Skill Removed

The embedded `plugin-creator` skill and its associated scaffolding, validation, and update scripts are removed from the system-skill bundle.

The existing installer refreshes `CODEX_HOME/skills/.system` when embedded contents change. Workflows that directly reference `.system/plugin-creator` or its scripts should move to a separately maintained skill installation or tooling location. The diff does not establish a replacement bundled skill.

Code references:

- Removed directory `codex-rs/skills/src/assets/samples/plugin-creator/`
- `SYSTEM_SKILLS_DIR`, `embedded_system_skills_fingerprint`, and `install_system_skills` in `codex-rs/skills/src/lib.rs`


### Client Compatibility

Existing JSON string cursors remain valid for `thread/items/list`. Rust callers rebuilding against the updated protocol types must wrap those strings in `ThreadItemsListCursor::Opaque`.

Clients should also tolerate structured errors on interrupted turns before strict Guardian circuit-breaker reporting is enabled. Executor integrations that previously relied on host credential fallback for executor-discovered MCP declarations need executor-side credential resolution.

Code references:

- `ThreadItemsListCursor` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- `Turn.error` in `codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs`
- `resolve_bearer_token` in `codex-rs/codex-mcp/src/rmcp_client.rs`


Generated with:
- tool: `harness-investigations@ed91713-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.159.0.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
