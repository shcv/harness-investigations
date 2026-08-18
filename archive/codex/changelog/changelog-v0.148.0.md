# Changelog for version 0.148.0

## Summary

Codex 0.148.0 adds conversation export, session forking and archive management, startup drafting, thread-cost visibility, Amazon Bedrock Runtime support, and more capable hooks. It also hardens session recovery, provider/MCP reconnection, terminal input handling, rendering, and sandbox path enforcement.

## Official Release Highlights

The published release notes focus on new session-management and TUI workflows, Bedrock support, and hook extensibility. They also call out important reliability and security fixes around resumed sessions, connectivity, rendering, startup input, and sandboxing.

## Additional Changes Beyond Official Notes

This changelog additionally covers new configuration and app-server protocol capabilities that were present in the diff but not highlighted in the published notes.

## New Features

### Export TUI conversations as Markdown

What: Export the complete interactive conversation to the clipboard or a Markdown file.

Usage:

```text
/export
```

Details:

- The TUI offers `/export` as “export the conversation as markdown.”
- Select a clipboard or file destination when prompted.

Code references:

- `TranscriptExportDestination` in `codex-rs/tui/src/app_event.rs`
- `transcript_export` in `codex-rs/tui/src/app/transcript_export.rs`
- `SlashCommand::Export` in `codex-rs/tui/src/slash_command.rs`


### Fork a session from `codex exec`

What: Create a new session from an existing session ID or thread name, optionally immediately supplying a prompt and images.

Usage:

```bash
codex exec fork SESSION_ID "Continue by testing the fix"
```

Details:

- `--image` / `-i` accepts one or more image files to attach to the post-fork prompt.
- The forked session is separate from the source conversation.

Code references:

- `ForkArgs` and `Command::Fork` in `codex-rs/exec/src/cli.rs`


### Archive and restore sessions from the TUI

What: Manage saved sessions from the resume picker without deleting them.

Usage:

```text
Open the TUI resume picker, archive a session, or restore it from the archived-session view.
```

Details:

- Archived sessions are kept separately and can be restored.
- Resumed sessions also preserve their stored working directory and approval policy.

Code references:

- `thread/archive` and `thread/unarchive` in `codex-rs/app-server/src/request_processors/thread_processor.rs`
- `run_session_archive_command` in `codex-rs/tui/src/session_archive_commands.rs`


### Draft while Codex starts

What: Type and edit a prompt while the TUI is still initializing.

Usage:

```text
Start Codex and begin typing immediately.
```

Details:

- Startup preserves the draft through initialization and terminal handoff.
- Startup UI now reports resume and fork progress instead of forcing users to wait before composing.

Code references:

- `StartupDraft` in `codex-rs/tui/src/startup_draft.rs`
- `startup_orchestration` in `codex-rs/tui/src/startup_orchestration.rs`


### View estimated thread cost and credits

What: View available estimated thread credits or cost in `/status`, status lines, and terminal titles for supported workspaces.

Usage:

```text
/status
```

Details:

- Availability depends on the active account and workspace returning thread-usage data.
- The TUI refreshes and renders `ThreadUsage` estimates when available.

Code references:

- `ThreadUsage` in `codex-rs/app-server-protocol/src/protocol/v2/thread_usage.rs`
- `ThreadUsageState` in `codex-rs/tui/src/chatwidget/thread_usage.rs`
- `StatusThreadUsage` in `codex-rs/tui/src/status/thread_usage.rs`


### Use Amazon Bedrock Runtime as a built-in provider

What: Use Amazon Bedrock Runtime for supported GPT-5.6 routing with AWS credentials, profile, and region configuration.

Usage:

```toml
[model_providers.amazon_bedrock]
# Configure the AWS credentials/profile and region appropriate to your environment.
```

Details:

- Codex includes an `AmazonBedrockModelProvider` implementation rather than requiring an external compatibility proxy.
- Provider authentication and Runtime endpoint handling are integrated into model-provider routing.

Code references:

- `AmazonBedrockModelProvider` in `codex-rs/model-provider/src/amazon_bedrock/mod.rs`
- provider registration in `codex-rs/model-provider/src/provider.rs`


### Run asynchronous command hooks and invoke MCP tools from hooks

What: Hooks can now run command handlers asynchronously and use configured MCP tools as hook handlers.

Usage:

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "scripts/notify.sh",
      "async": true
    }
  ]
}
```

Details:

- Asynchronous mode applies to command handlers; MCP-tool handlers execute synchronously.
- MCP hook handlers carry a server, tool, and JSON input payload.

Code references:

- `ConfiguredHandlerKind::Command` and `ConfiguredHandlerKind::McpTool` in `codex-rs/hooks/src/engine/mod.rs`
- `HookMcpCall` in `codex-rs/hooks/src/mcp.rs`


### [Additional] Workload-identity authentication

What: Support host-managed ChatGPT authentication through a file-backed workload-identity assertion.

Usage:

```bash
export OPENAI_FEDERATION_RULE_ID="your-federation-rule"
export OPENAI_IDENTITY_TOKEN_FILE="/absolute/path/to/assertion"
codex
```

Details:

- An optional `OPENAI_WORKLOAD_IDENTITY_CONTEXT` value is passed with the token exchange.
- Partial configuration fails closed rather than falling back to another credential source.
- The assertion file must be an absolute path; this is intended for managed environments.

Code references:

- `WorkloadIdentityConfig` in `codex-rs/workload-identity/src/lib.rs`
- `is_workload_identity_selected` and `resolve_config` in `codex-rs/login/src/auth/workload_identity.rs`
- environment-variable constants in `codex-rs/protocol/src/shell_environment.rs`


### [Additional] Configure default and maximum goal token budgets

What: Set the default goal budget and cap goal budgets created through Codex’s stable goals feature.

Usage:

```toml
[goals]
max_goal_token_budget = 25000
```

Details:

- The configured value becomes the default for new goals and the maximum accepted goal budget.
- The goals feature is stable and enabled by default.

Code references:

- `GoalsToml::max_goal_token_budget` in `codex-rs/config/src/config_toml.rs`
- budget validation in `codex-rs/app-server/src/request_processors/thread_goal_processor.rs`
- `Feature::Goals` in `codex-rs/features/src/lib.rs`


### [Additional] Add bounded metadata to Responses API requests

What: Add a small map of custom metadata to every Responses API request made by Codex.

Usage:

```toml
responses_api_metadata = { deployment = "staging", team = "platform" }
```

Details:

- Codex validates the map: at most 16 entries, short ASCII identifier keys, and values of at most 128 bytes.
- Reserved metadata keys are rejected.

Code references:

- `responses_api_metadata` in `codex-rs/config/src/config_toml.rs`
- `validate_extra_metadata` in `codex-rs/core/src/responses_metadata.rs`
- request attachment in `codex-rs/core/src/turn_metadata.rs`

## Improvements

### Preserve visual metadata on app-server thread sections

App-server clients can now attach an optional icon and color to persisted thread sections, and can later replace or clear that appearance.

Usage:

```json
{
  "method": "threadSection/create",
  "params": {
    "name": "Release work",
    "appearance": { "icon": "rocket", "color": "blue" }
  }
}
```

Code references:

- `ThreadSectionAppearance` in `codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs`
- `ThreadSectionCreateParams` and `ThreadSectionUpdateParams` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- schema `codex-rs/app-server-protocol/schema/json/v2/ThreadSectionCreateParams.json`


### Improve bundled skill-creator guidance

The bundled skill-creator material is more focused, and validation rejects unfinished TODO placeholders.

Code references: skill validation updates in `codex-rs/core-plugins/` and bundled skill content in `codex-rs/core/`.


## Bug Fixes

- Model changes and settings updates no longer leave stale instructions in place or alter an active turn midstream. (`turn` configuration handling in `codex-rs/core/src/session/`)
- Resuming a session restores its persisted working directory and approval policy, and transcript previews better reflect saved content. (`latest_persisted_approval_policy` in `codex-rs/app-server/src/request_processors/thread_processor.rs`)
- Turns reconnect through temporary provider failures, and MCP servers recover after OAuth reauthentication without requiring a Codex restart. (`mcp_refresh` in `codex-rs/app-server/src/mcp_refresh.rs`)
- TUI startup drains buffered terminal input before protected prompts and shows onboarding when authentication is absent. (`discard_pending_input_before_interactive_screen` in `codex-rs/tui/src/tui.rs`)
- Composer and transcript rendering now preserve CRLF and wrapped whitespace correctly and handle long URLs more reliably. (`thread_transcript` in `codex-rs/tui/src/thread_transcript.rs`)
- Linux and Windows sandbox path restrictions now fail closed when denied or unreadable paths cannot be safely resolved. (`resolve_windows_deny_read_paths` in `codex-rs/windows-sandbox-rs/src/deny_read_resolver.rs`)


## In Development

### Queued thread submissions [Experimental]

What: The app-server now has endpoints for clients to add, list, edit, delete, reorder, and start queued user submissions for a thread.

Usage:

```json
{
  "method": "thread/queue/add",
  "params": {
    "threadId": "thr_example",
    "clientUserMessageId": "msg_001",
    "input": [{ "type": "text", "text": "Run the tests after the current turn." }]
  }
}
```

Status: Runtime-gated behind the app-server experimental API capability and marked experimental for each `thread/queue/*` method.

Details:

- Queue changes are reported with the experimental `thread/queue/changed` notification.
- Clients should treat the protocol as experimental and handle future changes.

Code references:

- `ThreadQueueAddParams` and `QueuedSubmission` in `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`
- experimental `thread/queue/*` registrations in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `thread_queue_processor` in `codex-rs/app-server/src/request_processors/thread_queue_processor.rs`


Generated with:
- tool: `harness-investigations@97d5ba5-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.148.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.148.0.md`
