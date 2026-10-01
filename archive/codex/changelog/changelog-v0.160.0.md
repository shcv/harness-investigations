# Changelog for version 0.160.0

## Release Status

> **Not yet released:** `rust-v0.160.0` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

This changelog covers the changes from **0.159.3 to 0.160.0**. The snapshot improves task browsing, reconnect recovery, permission preservation, custom model catalogs, and terminal copying, and adds experimental Guardian history controls. The source tag `rust-v0.160.0` exists, but no published GitHub Release was found when synchronization ran; this is an unpublished development snapshot, with no claim that binaries or release assets were published.

## New Features


### X11 selection and middle-click paste

What: Local Linux X11 sessions can publish selected transcript text to the PRIMARY selection and paste it into the composer with the middle mouse button.

Usage: Select text in Codex’s transcript, then middle-click in the composer to paste it.

Details:

- PRIMARY selection works even when automatic copying to the regular clipboard is disabled.
- PRIMARY contains plain text; regular clipboard copying retains its existing formatting behavior.
- Selection publication and paste are coordinated so a paste can wait for the current selection to become available.
- Delayed paste results are discarded when their target is no longer valid, such as after changing drafts or conversations.
- This integration requires a local X11 session. It is disabled for Wayland, SSH, tmux, WSL, and detected VS Code terminals.

Code references:

- `available`, `copy`, and `read` in `codex-rs/tui/src/clipboard_copy/primary.rs`
- `ClipboardWorker::select` and `ClipboardWorker::read_text` in `codex-rs/tui/src/clipboard_copy/worker.rs`
- `TranscriptView::publish_primary` in `codex-rs/tui/src/transcript_view/selection.rs`

## Improvements


### Browse older tasks from Agent Command Center

The existing Agent Command Center now offers **Show more** to load additional historical tasks beyond its initial recent-task window.

Usage: Run `/agents`, select **Show more**, and press Enter.

Each activation adds up to ten tasks, combining interactive and non-interactive task history by recency. Subagent and ephemeral threads are excluded from these historical root-task results. Failed refreshes retain existing entries, and removing or archiving tasks can refill the current window.

Search still filters loaded entries; **Show more** remains available when additional history may contain a match.

Code references: `AgentsOverviewDiscovery::next_batch` in `codex-rs/tui/src/app/agents_overview_discovery.rs`; `AgentsOverviewView::activate` in `codex-rs/tui/src/app/agents_overview_view.rs`.


### Easier startup outside a project

Fresh local tasks in positively identified projectless folders can now start without a folder-trust prompt and use the built-in workspace permission profile.

Usage: Start `codex` in an ordinary local folder without project markers or a saved trust decision.

The implicit approval policy permits explicit permission requests and MCP elicitations while disabling sandbox-escalation, rule, and skill approval prompts. This does not save a trust decision.

These defaults apply only when discovery and server configuration agree. Explicit permission settings, managed requirements, existing trust decisions, remote execution, and additional workspace roots preserve their own behavior. On Windows, missing sandbox setup triggers the setup flow before workspace-write permissions are enabled.

Code references:

- `apply_defaults` and `has_only_local_environments` in `codex-rs/tui/src/projectless.rs`
- `read_remote_project_trust` in `codex-rs/tui/src/config_update.rs`
- `ChatWidget::maybe_prompt_windows_sandbox_enable` in `codex-rs/tui/src/chatwidget/windows_sandbox_prompts.rs`


### Trust a destination folder during `/cd`

Changing directories can now present the folder-trust decision inside the current session, instead of rejecting an undecided destination and requiring Codex to be launched there separately.

Usage:

```text
/cd /path/to/project
```

Choose **Trust and continue**, or **Keep current directory** to cancel the transition. Codex rechecks running tasks and background terminals after consent and configuration loading, preventing a directory switch when another client starts work during that interval.

Code references: directory-transition handling in `codex-rs/tui/src/app/working_directory.rs`; `check_directory_trust` in `codex-rs/tui/src/onboarding/directory_trust.rs`; `TrustCancelAction::CurrentTask` in `codex-rs/tui/src/onboarding/trust_directory.rs`.


### Custom model catalogs are authoritative

Providers using the existing `model_catalog_url` setting now use that catalog without silently substituting bundled OpenAI models.

Details:

- Catalog entries must have unique, nonblank model slugs.
- Failed refreshes clear stale catalog results and invalidate the cached catalog.
- Model metadata is selected by an exact slug match.
- An explicitly selected model remains usable with fallback metadata when it is absent from the catalog.
- An empty catalog without an explicitly selected model produces an actionable configuration error.

Usage: If discovery is unavailable, select a model supported by your configured provider:

```bash
codex -m provider-model-id
```

The existing authentication and API-key discovery gates still apply; configuring a catalog does not bypass them.

Code references:

- `OpenAiModelsEndpoint::list_models` in `codex-rs/model-provider/src/models_endpoint.rs`
- `CatalogSource::ExplicitProvider` and `OpenAiModelsManager::with_provider_catalog` in `codex-rs/models-manager/src/manager.rs`
- `AppServerSession::bootstrap` in `codex-rs/tui/src/app_server_session.rs`


### Guided recovery after content-filter interruptions

When a sampling response stops with `content_filter`, Codex now adds developer guidance before proceeding through its existing retry policy. The default guidance tells the model to explain the limitation, offer a permitted alternative, avoid attempts to reproduce the blocked content, and continue unrelated authorized work.

Catalog authors can customize this through a new optional field inside a model’s existing `model_messages` object:

```json
{
  "model_messages": {
    "content_filter_guidance": "Explain the limitation and offer a permitted alternative."
  }
}
```

Missing, null, blank, or longer-than-512-byte UTF-8 values use the bundled guidance. The public error category and error text remain compatible; this change does not introduce a new app-server error category.

Code references:

- `ModelMessages::content_filter_guidance` in `codex-rs/protocol/src/openai_models.rs`
- `ResolvedModelMessages::content_filter_guidance` in `codex-rs/prompts/src/model_messages.rs`
- `handle_response_stream_error` in `codex-rs/core/src/responses_retry.rs`


### Cleaner copying of code and quotations

Transcript selections now produce more useful clipboard text for common copy-and-paste tasks.

Usage: Select an inline command, path, or quoted passage and copy it using the existing transcript controls.

- Selecting only inline code copies its contents without adding Markdown backticks.
- Selections containing only blockquoted content omit the quote markers.
- Quoted tables and task lists retain the structure needed to preserve cell contents and checkbox states.
- Inline-code selections inside table cells also copy as plain text, including after line wrapping.

Code references: `selection` and `CopyLine::is_inline_code` in `codex-rs/tui/src/markdown_copy.rs`; `render` in `codex-rs/tui/src/markdown_copy/table.rs`.


### Readable follow-up suggestions

The terminal now renders recognized `codex-followup` directives as their visible labels instead of exposing the directive syntax and embedded prompt.

For example, an assistant response containing:

```text
:codex-followup[Inspect **test failures**]{prompt="Inspect the failing tests"}
```

displays the formatted label “Inspect test failures.” Whole-response copying also substitutes the label. Streaming previews withhold unfinished directives, while literal examples inside code and malformed completed directives retain their source representation.

This change adds label rendering, not an interactive follow-up button.

Code references:

- `parse_assistant_directive_with_budget` in `codex-rs/tui/src/assistant_directives.rs`
- `InlineDirectives` and `followup_labels` in `codex-rs/tui/src/markdown_render/inline_directives.rs`
- `ProsePreview` in `codex-rs/tui/src/streaming/prose_preview.rs`
- `TranscriptState::record_agent_markdown` in `codex-rs/tui/src/chatwidget/transcript.rs`


### Less duplication in skill catalogs

When the same qualified plugin skill is available through both the cloud catalog and an executor catalog, the model-facing listing now prefers the cloud entry.

Deduplication happens before the listing’s token budget is allocated, leaving more room for distinct skills. Executor skill packages remain accessible through skill tools, executor aliases stay stable, and disabling the cloud entry allows the executor listing to reappear. No configuration change is required.

Code references: `PreparedSkillCatalog::prefer_cloud_skills` in `codex-rs/ext/skills/src/render_dedup.rs`; catalog preparation in `codex-rs/ext/skills/src/world_state_catalogs.rs`.


### Reduced repeated work during plugin discovery

Plugin listing and discovery reuse parsed manifests and overlays when their contents are unchanged. Changes to those files still invalidate the cached result.

Remote plugin operations also reuse a lazily initialized HTTP client across configuration clones, reducing repeated connection setup while retaining current routing and authentication configuration. These optimizations require no new setting.

Code references: `ManifestCache` in `codex-rs/core-plugins/src/manifest/manifest_cache.rs`; `PluginsConfigInput::remote_plugin_service_config` in `codex-rs/core-plugins/src/manager.rs`.


### Automatic reclamation of unused log-database space

Codex now runs background reclamation for eligible log databases, returning unused SQLite pages to the filesystem after substantial free space accumulates.

The worker uses bounded batches and backs off under contention. Only the log database is opted in in this snapshot; existing databases with incompatible vacuum modes are preserved rather than automatically converted. No user configuration is needed.

Code references: `SqliteReclamationWorker` in `codex-rs/state/src/runtime/reclamation.rs`; `LOGS_DB` and `RuntimeDbSpec::background_reclamation` in `codex-rs/state/src/sqlite.rs`.


### Clearer terminal status and hints

- The idle fullscreen Plan-mode indicator shows **Shift+Tab to cycle** when space permits.
- Symbolic modifier hints use compact forms such as `⌥→`, without changing the underlying bindings.
- `/status` labels the existing Pro plan variants as **Pro 100**, **Pro 200**, and **Pro 500**. This is a display-label change.
- Status views connected to an app-server omit reasoning-summary settings that the client cannot reliably represent.

Code references: `ChatComposer::render_status_surface` in `codex-rs/tui/src/bottom_pane/chat_composer/status_surface.rs`; `KeyBinding` in `codex-rs/tui/src/key_hint.rs`; `SubscriptionDisplay::label` in `codex-rs/tui/src/subscription.rs`; `StatusHistoryCell` in `codex-rs/tui/src/status/card.rs`.

## Bug Fixes

- **Reconnect recovery distinguishes unsent messages from uncertain submissions.** Confirmed client message IDs remove already accepted submissions from recovered queues, allowing genuinely unsent follow-ups to continue. Messages whose delivery cannot be confirmed remain paused and are not automatically resent. (`ChatWidget::restore_reconnected_input` and `reconcile_recovered_messages` in `codex-rs/tui/src/chatwidget/reconnect.rs`)

- **Resuming tasks preserves saved permissions more faithfully.** Ordinary configuration defaults no longer overwrite saved approval policies, reviewers, permission profiles, or workspace roots. Direct launch overrides are tracked separately, and display-only sandbox projections are not sent back as execution overrides on ordinary turns. (`ResumePermissions::from_overrides` in `codex-rs/tui/src/resume_permissions.rs`; `thread_resume_params_from_config` in `codex-rs/tui/src/app_server_session.rs`; turn routing in `codex-rs/tui/src/app/thread_routing.rs`)

- **Permission choices remain correctly scoped when switching tasks.** Restored settings do not become unintended defaults for new tasks, and carrying an explicit reviewer into a destination that forbids it fails visibly. (`apply_runtime_policy_overrides` and task lifecycle handling under `codex-rs/tui/src/app/`)

- **Provider selection follows server defaults unless explicitly overridden.** New tasks, history lookup, and resume/fork pickers no longer use an incidental client-side provider default in place of the server’s effective provider. Forking the active session preserves its provider. (`explicit_provider` and `AppServerSession::history_model_provider` in `codex-rs/tui/src/app_server_session/provider_selection.rs`)

- **Reasoning-summary and verbosity defaults no longer overwrite server-owned settings.** These values are forwarded as overrides only when their winning configuration comes from an explicit launch choice or selected profile. (`config_request_overrides_from_config` in `codex-rs/tui/src/app_server_session.rs`)

- **Voice-catalog failures are reported instead of silently using a built-in fallback list.** Voice selection and conversation startup surface the failure; saving a preference distinguishes successful persistence from failure to confirm the effective voice. (`App::realtime_voices` and realtime settings handling in `codex-rs/tui/src/app/realtime_settings.rs`)

- **Usage-limit failures during compaction stop automatic work.** Manual and post-turn compaction notify lifecycle consumers of usage-limit failures; post-turn failures preserve the completed answer. (`CompactTask` in `codex-rs/core/src/tasks/compact.rs`; `run_turn` in `codex-rs/core/src/session/turn.rs`)

- **Guardian reviews retain encrypted agent-message evidence.** Review transcripts preserve native encrypted agent messages instead of losing them during plaintext conversion. Budget handling omits whole encrypted items when necessary rather than truncating their payloads. (`TranscriptContent::AgentMessage` in `codex-rs/guardian-context/src/entry.rs`; `collect_transcript` in `codex-rs/guardian-context/src/transcript.rs`)

- **Guardian reviews avoid unnecessary remote Git discovery.** Review startup no longer waits on remote repository discovery merely to determine displayed diff paths. (`run_turn` in `codex-rs/core/src/session/turn.rs`)

- **SQLite connection initialization avoids unnecessary writer-lock contention.** Opening existing databases preserves their vacuum mode, and initialization failures retain the underlying error instead of becoming a generic pool timeout. (`SqliteConfig::open_read_write_pool` in `codex-rs/state/src/sqlite.rs`)

- **App-server stderr logging reduces database-stall risk.** Removing per-poll span enter/exit records reduces the chance that a blocked stderr pipe stalls database work while a transaction holds a write lock. (`stderr_span_events` in `codex-rs/app-server/src/lib.rs`)

- **Windows sandbox ACL repair supports long paths.** Reading and updating access-control entries now handles paths beyond the legacy Windows path limit while preserving read/execute-only grants. (`fetch_dacl_handle` and `ensure_allow_mask_aces_with_inheritance_impl` in `codex-rs/windows-sandbox-rs/src/acl.rs`)

- **MXC sandbox execution gains the PowerShell fallback previously used for elevated sandboxing.** When necessary, Windows Store PowerShell is replaced with a discovered unpackaged shell on the executor host. (`fallback_powershell_shell_for_windows_sandbox` in `codex-rs/shell-command/src/shell_detect.rs`; `prepare_exec_request_with_telemetry` in `codex-rs/exec-server/src/process_sandbox.rs`)

- **Windows provisioning diagnostics avoid persisting sensitive configuration text.** Administrator-policy rejection events record controlled stage names and typed error codes instead of parser messages that can contain credentials. (`policy_rejection_diagnostic` in `codex-rs/windows-sandbox-service/src/ipc.rs`)

- **Sandbox debugging works with older macOS policy compilers.** The generated terminal-injection restriction uses the numeric `TIOCSTI` value instead of requiring the compiler to recognize its symbolic name. (`run_command_under_sandbox` in `codex-rs/cli/src/debug_sandbox.rs`)

## In Development


### Guardian conversation-history retrieval [Experimental]

What: Guardian V2 can use narrowly scoped history tools to check prior user instructions, permissions, and revocations during automatic approval review.

Status: Off by default, controlled by `guardian_conversation_history_tools`; the implemented tool integration requires Guardian V2 and Apps.

Usage:

```toml
approvals_reviewer = "auto_review"

[features]
guardianv2 = true
apps = true
guardian_conversation_history_tools = true

[auto_review]
conversation_history_max_output_tokens = 4000
```

Details:

- Exposes only `user_message.search_messages` and `user_message.read_messages` from the parent’s hosted Apps connection.
- Rechecks the parent’s current connection, authentication, and tool policy on each call.
- Does not create a separate Apps connection or grant access to unrelated Apps tools.
- History calls requiring interactive approval are unavailable during review.
- The response budget defaults to 4,000 estimated tokens; stricter parent and caller limits still apply.
- The optional `[auto_review] experimental_conversation_history_prompt` replaces the retrieval instructions. Omitted or blank values use the built-in prompt.
- Enabling the flags does not provision history tools if the parent’s hosted connection does not provide them.

Code references:

- `AutoReviewToml` in `codex-rs/config/src/config_toml.rs`
- `conversation_history_tools` in `codex-rs/core/src/mcp_tool_call/conversation_history.rs`
- `ConversationHistoryTools` in `codex-rs/ext/guardian-v2/src/sync_reviewer/conversation_history.rs`
- `Feature::GuardianConversationHistoryTools` in `codex-rs/features/src/lib.rs`


### Guardian context focused on worker handoffs [Experimental]

What: Worker approval reviews can use selected root-conversation context around relevant delegation messages.

Status: Off by default, controlled by `guardian_root_handoff_context`.

Usage with automatic approval review:

```toml
approvals_reviewer = "auto_review"

[features]
guardian_root_handoff_context = true
```

Details:

- Recognizes root `spawn_agent`, `send_message`, and `followup_task` calls directed to the worker or an ancestor.
- Selects preceding root-message windows and recent root context.
- Preserves verified user-input evidence and unordered legacy evidence.
- Falls back to the existing context when suitable handoff evidence is unavailable, including relevant compaction and heartbeat cases.

Code references: `selected_message_indices` in `codex-rs/core/src/agent/control/root_handoff.rs`; root authorization collection in `codex-rs/core/src/agent/control/user_authorization.rs`; `Feature::GuardianRootHandoffContext` in `codex-rs/features/src/lib.rs`.


### Pending environment inheritance for subagents [Experimental]

What: The existing deferred-executor path now lets subagents inherit environments that are still starting.

Status: The deferred-executor feature remains off by default.

Usage:

```toml
[features]
deferred_executor = true
```

Details:

- Spawned agents retain pending environment attachments rather than receiving only already-ready selections.
- Descendants follow the pending configuration’s completion.
- Later parent changes do not overwrite a child’s already accepted environment configuration.

This is a correction to experimental environment handling, not a new executor provider.

Code references: `TurnEnvironmentSnapshot` in `codex-rs/core/src/environment_selection.rs`; `follow_inherited_environment_configurations` in `codex-rs/core/src/session/environment.rs`; spawn handlers under `codex-rs/core/src/tools/handlers/multi_agents/` and `multi_agents_v2/`.

## Notes

- **Custom catalogs:** If an existing `model_catalog_url` configuration depended on bundled-model fallback, repair the catalog or explicitly select a provider-supported model. Catalog slugs must be unique and nonblank.
- **Resumed permissions:** Saved task permissions now take precedence over ordinary launch configuration defaults. Use direct launch overrides when intentionally changing a resumed task’s permissions; merely selecting a profile does not make all of its permission defaults explicit resume overrides.
- **Release status:** These entries describe the tagged source comparison, not official release notes or verified availability of published binaries.


Generated with:
- tool: `harness-investigations@e031414-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.160.0.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
