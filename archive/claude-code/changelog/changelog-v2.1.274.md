# Changelog for version 2.1.274

## Summary

Version 2.1.274 improves marketplace refreshes, Chrome browser selection, MCP authentication diagnostics, and worktree cleanup. It adds configurable MCP startup waiting and terminal labels, changes marketplace Git LFS handling, and ships gated implementations of Claude Test, AGENTS.md instruction loading, and pasted-content separation.

## New Features


### Custom Terminal Footer Label

What: Set a short label in the terminal footer through `CLAUDE_CODE_FOOTER_INDICATOR`.

Usage:

```bash
CLAUDE_CODE_FOOTER_INDICATOR="Development" claude
```

Details:

- A nonempty environment value takes precedence over the server-configured footer indicator.
- The displayed text is sanitized and length-limited.
- The footer indicator itself existed previously; configuring it through this environment variable is new.

Evidence: Footer configuration resolution and rendering — search for `"CLAUDE_CODE_FOOTER_INDICATOR"` and `"footer-indicator"`.


### Structured Startup Failures for CLI Automation

What: Opt into machine-readable results for recognized startup failures in `stream-json` runs.

Usage:

```bash
CLAUDE_CODE_STARTUP_FAILURE_RESULTS=1 \
  claude -p --verbose --output-format stream-json "Explain this repository"
```

Details:

- Recognized failures can emit an `error_during_execution` result with zero turns and a `startup_failure_reason`.
- Reasons distinguish problems such as an unavailable working directory, invalid managed settings, an organization-login mismatch, or a session already held by background work.
- The result includes the error text so launchers can present a useful remedy.
- This does not make every possible startup failure produce a structured result.

Evidence: Startup-result construction and opt-in checks — search for `"CLAUDE_CODE_STARTUP_FAILURE_RESULTS"` and `"startup_failure_reason"`.


### Runtime Agent Registration for Function-Hook Plugins

What: Plugins using the function-hook API can register agent definitions during a session.

Usage:

```javascript
await $.agent.register({
  name: "reviewer",
  description: "Review changes for correctness",
  prompt: "Inspect the requested changes and report concrete defects."
});
```

Details:

- Registered agents use the plugin’s namespace.
- Registering an identical definition is a no-op; a changed definition replaces the previous registration.
- Definitions exist only in the current process.
- Pane-based teammates cannot run these runtime-only agent types; use an in-process execution path.
- Requires the existing function-hook plugin system to be available.

Evidence: Registration validation, agent-list refresh, and teammate restrictions — search for `"$.agent.register"` and `"pane teammate cannot run a run-time registered agent type"`.

## Improvements


### Configurable MCP Startup Waiting

Headless runs can now control how long startup waits for pending MCP connections using `CLAUDE_CODE_MCP_STARTUP_WAIT_MS`.

```bash
CLAUDE_CODE_MCP_STARTUP_WAIT_MS=10000 \
  claude -p "Use the configured tools to inspect this project"
```

A positive value enables waiting for deferrable servers within the applicable startup scope. Setting it to `0` skips that general wait. A configured permission-prompt server retains its separate readiness handling.

Evidence: Headless MCP prewait configuration — search for `"CLAUDE_CODE_MCP_STARTUP_WAIT_MS"`.


### Safer Marketplace Refreshes

Marketplace refreshes now compare the cached checkout with the requested remote revision before replacing it.

- Unchanged revisions can keep the existing checkout.
- Changed revisions or sparse-checkout paths trigger a fresh clone in a staging directory.
- The old checkout is moved aside only after cloning succeeds.
- If installing the replacement fails, the code attempts to restore the previous checkout.
- When the directory is busy, the error explicitly says the existing copy was kept.

Evidence: Revision probing and staged replacement — search for `"Marketplace checkout probe:"`, `"Replacing the existing marketplace clone…"`, and `"the existing copy was kept"`.


### Explicit Git LFS Handling in Marketplaces

Claude Code’s marketplace Git operations now leave LFS-tracked files as pointer files. The existing `skipLfs` setting remains accepted but no longer changes this behavior.

Add and update operations report detected pointer files and explain how to fetch their contents manually:

```bash
git -C ~/.claude/plugins/marketplaces/<marketplace> lfs pull
```

Evidence: Updated setting description and pointer-file reporting — search for `"Has no effect; accepted so existing settings keep working"` and `"Git LFS pointer files"`.


### Better Chrome Selection Across Computers

The existing Chrome integration makes better use of a previous browser choice and verified local-browser information.

- A still-connected selected browser remains preferred.
- With several connected browsers, a single browser verified live on this computer can be selected automatically.
- Otherwise, Claude is instructed to ask, listing browsers on this computer first.
- Remote-hosted sessions can receive browser-selection hints from their host.
- Timeout messages now distinguish a possibly sleeping remote computer from an unresponsive local page.

Evidence: Browser selection and discovery output — search for `"onThisComputer"`, `"preferredDeviceId"`, and `"Browsers on this computer:"`.


### More Specific MCP Authentication Errors

MCP tool calls now distinguish an expired or rejected credential from a server requesting additional OAuth scopes. Missing-scope errors identify the requested scope and direct users to `/mcp` to reauthenticate.

Concurrent calls can also join an authentication recovery already in progress, with account-change checks preventing recovery under a different login.

Evidence: Authentication classification and recovery — search for `"needs additional permissions (scope:"`, `"collateral_rejoin"`, and `"account changed during re-authentication"`.


### More Precise Worktree Cleanup Checks

Worktree cleanup now inspects configured submodules and distinguishes:

- Tracked changes inside a submodule.
- Untracked files.
- Submodules whose state cannot be verified.
- Separate nested repositories that are not configured submodules.

This replaces blanket treatment of submodule checkouts with more specific checks and recovery messages. Forced cleanup still refuses relevant uncommitted or unverifiable submodule work.

Evidence: Submodule inspection and removal decisions — search for `"submodule inspection deadline"`, `"submodule work unverified or uncommitted"`, and `"commit or stash them, inside the submodule too"`.


### Clearer Shared-Memory Sync Failures

Shared-memory synchronization now recognizes an oversized `MEMORY.md` index separately from an oversized individual memory file. It also distinguishes content rejected by the server’s safety check.

Messages explain which files remain local, that other files can continue syncing, and what to change before retrying. Temporary synchronization failures explicitly warn that recent writes have not reached shared memory.

Evidence: Rejection classification and recovery text — search for `"index_too_large"`, `"content_screened"`, and `"Recent memory writes are saved locally"`.


### Project File Delivery Through SendUserFile

For supported project-thread sessions, `SendUserFile` can place output in the project’s shared folder, visible in its Library.

The implementation checks read permissions and file identity, requires approval before project-folder writes in plan mode, and reports partial delivery when only the project folder or chat viewers received a file.

Evidence: Project-folder delivery and permission checks — search for `"placed in the project's shared folder (visible in its Library)"`, `"SendUserFile reads file contents"`, and `"tengu_bridge_child_file_upload"`.


### Clearer Artifact Reads and Document Creation

Existing Artifact workflows gain more explicit handling of ownership, external content, and document-backed artifacts.

- Public artifacts outside the organization require a user-approved read; a hook’s approval alone does not satisfy that requirement.
- External public artifacts can be read but cannot be watched from the current organization.
- Document-backed artifacts explain when creation already provisioned an empty Claude Docs document, helping avoid duplicate documents.
- Instructions distinguish filling a document through its connector from publishing page files.

Evidence: Artifact consent and document routing — search for `"Reading someone else's artifact requires confirmation"`, `"a PermissionRequest hook answered"`, and `"a new, empty Claude Docs document"`.


### Quieter Local Artifact Watching

Local live-watch messages now describe background version tracking accurately: a republish does not start a turn or send a notification. Certain Artifact results instead flag that a newer version exists and instruct Claude to reread and merge before publishing.

Comments explicitly sent to Claude remain a separate notification path where enabled.

Evidence: Local watch behavior and stale-version guidance — search for `"a new version starts no turn and sends no notification"` and `"fetch the artifact's URL again and merge your edits"`.


### Critical-Memory Warning

The terminal can now display a critical-memory warning with recovery guidance: restart and resume using `claude --continue`, or use `/compact` when available.

Evidence: Mounted terminal warning component — search for `"Critical memory usage ("`.


### Enterprise Gateway Reliability and Diagnostics

The bundled gateway gains several operational improvements:

- Graceful shutdown waits for active requests, with a default drain window of 25 seconds.
- `CLAUDE_GATEWAY_DRAIN_TIMEOUT_MS` customizes that window.
- A second termination signal forces shutdown.
- Recognized PostgreSQL connection failures receive up to three startup attempts, two seconds apart.
- Diagnostics explain upstream concurrency saturation and sign-in rate limits caused by missing trusted-proxy configuration.

Evidence: Gateway shutdown, startup retry, and diagnostic paths — search for `"CLAUDE_GATEWAY_DRAIN_TIMEOUT_MS"`, `"could not connect to Postgres at boot, attempt"`, `"BUN_CONFIG_MAX_HTTP_REQUESTS"`, and `"listen.trusted_proxies is not set"`.


### Opt-In Managed-Settings Logging

Administrators can enable `OTEL_LOG_MANAGED_SETTINGS` to include a filtered representation of resolved managed settings in OpenTelemetry events.

```bash
OTEL_LOG_MANAGED_SETTINGS=1 claude
```

This supplements the existing telemetry setup. The implementation bounds the payload, marks truncation, and includes settings/helper hashes when this logging is enabled.

Evidence: Configurable managed-settings export — search for `"OTEL_LOG_MANAGED_SETTINGS"`, `"managed_settings.settings"`, and `"managed_settings.settings_truncated"`.

## Bug Fixes

- **Reject invalid host-only MCP configuration.** Configuration files and plugins can no longer declare transports reserved for runtime host registration, including `sdk` and IDE transports. Errors explain where these servers must be registered. Search for `"Cannot add MCP server: host-only transport type"` and `"servers cannot be declared by a plugin"`.

- **Recover selected Git reads in partial clones.** Failed operations can retry with a constrained lazy fetch when repository and credential checks permit it. If an unscoped authentication header was withheld, the error explains how to scope it to a trusted host. Search for `"is a partial clone: retrying with a constrained lazy fetch"` and `"The lazy fetch did not send your unscoped http.extraHeader"`.

- **Avoid executing unverified repository-local Git configuration.** Additional checks reject unsafe or unverifiable configuration in affected built-in Git operations, including settings that name programs Git or Git LFS would execute. Search for `"the repository's own git config has a conditional include"` and `"which names a program git-lfs would run"`.

- **Preserve a usable shell snapshot during plugin refresh.** Refreshing plugins retains the existing shell snapshot when plugin `bin/` paths are unchanged; changed paths or unusable snapshots cause a rebuild on the next Bash execution. Search for `"Shell snapshot kept across plugin refresh"`.

- **Explain orphaned tool results.** Conversation-history errors involving a result without its corresponding tool call now receive a specific error and `/rewind` recovery guidance in interactive sessions. Search for `"API Error: 400 orphaned tool_result in conversation history."`.

- **Reject conversation-fork boundaries that split a tool call.** A fork request is refused when its selected boundary would separate a tool call from its associated history. Search for `"target splits a tool call"`.

- **Restore context announcements after compaction.** When compaction preserves recent messages, missing context attachments can be restored without duplicating attachment types already retained. This path defaults on. Search for `"tengu_calm_noodle"` and `"compact_kept_tail_announcements"`.

- **Refresh runner inference credentials after authentication failures.** A child turn ending with HTTP 401 or 403 can trigger an immediate inference-token refresh, with duplicate refreshes suppressed. Search for `"requesting a fresh inference_token from CCR now"`.

- **Remind agents about unread session-inbox messages.** A delivered inbox notification whose referenced message was not read can be announced once more after the turn. The new gate defaults on. Search for `"was not read by its turn; re-notifying once"` and `"tengu_bridge_inbox_pointer_boundary"`.

- **Protect raw API-body log destinations.** Raw-body logging rejects symbolic links, multiply linked files, and destinations whose identity changes while opening them. Search for `"OTEL raw body target is not a regular single-link file"` and `"OTEL raw body target changed identity around the open"`.

## In Development

These implementations are present in the bundle, but their new availability gates default to off. Source presence does not establish general availability.


### Claude Test [In Development]

What: Run plain-language browser tests against a local web application and receive PASS/FAIL results with screenshots.

Status: Feature-flagged by `tengu_mellow_hollerith`, default off.

Usage when enabled:

```text
/claude-test
/claude-test fix
/claude-test onboard
```

Details:

- Specs live under `.claude-test/specs/`.
- A first run proposes starter specs for the user to approve.
- Separate background agents draft specs and execute tests in a fenced headless browser.
- The browser helper requires an interactive terminal session and Node.
- Availability also requires the function-hook plugin system and excludes HIPAA/ZDR modes.
- The skill instructs Claude to offer testing after relevant changes rather than start it unasked.

Evidence: Built-in plugin registration, command definitions, and availability checks — search for `"claude-test"`, `"tengu_mellow_hollerith"`, and `"Claude Test needs an interactive Claude Code session"`.


### AGENTS.md Project Instructions [In Development]

What: A built-in `agents-md` plugin adds configurable loading of AGENTS.md instructions.

Status: Feature-flagged by `tengu_agents_md_mod`, default off; also requires function-hook plugins.

Details:

- The `projectInstructions` option accepts `claude`, `agents-fallback`, `both`, and `none`.
- `claude` preserves ordinary CLAUDE.md loading.
- `agents-fallback` adds fallback AGENTS.md loading when the applicable CLAUDE.md checks find none.
- `both` supports loading AGENTS.md alongside CLAUDE.md.
- `none` removes the engine’s CLAUDE.md context block, including managed and personal CLAUDE.md content.
- The plugin searches for both `AGENTS.md` and `.claude/AGENTS.md`, with handling for directory changes and nested reads.

When the plugin is active in its default `claude` mode, it can show a nudge explaining that AGENTS.md is not being loaded. That is configuration guidance, not evidence that fallback loading is already active.

Evidence: Plugin configuration and context hooks — search for `"tengu_agents_md_mod"`, `"projectInstructions"`, and `"This project has AGENTS.md but no CLAUDE.md"`.


### Pasted-Content Separation [In Development]

What: Distinguish pasted reference material from the user’s own instructions.

Status: Feature-flagged by `tengu_virtual_pancake`, default off.

Details:

- Pasted blocks can be wrapped in `pasted_content` markers with matching session-specific identifiers.
- Added model guidance explains that instructions inside those blocks establish user intent only when the surrounding user message directs Claude to follow them.
- History restoration can reconstruct the corresponding paste blocks.

Evidence: Paste serialization, restoration, and prompt guidance — search for `"pasted_content"`, `"tengu_virtual_pancake"`, and `"was pasted into the message by the user from somewhere else"`.


### Artifact Starter Files [In Development]

What: Make eligible Artifact type instructions, reference files, and design-system files available locally during quickstart workflows.

Status: Feature-flagged by `tengu_concurrent_candle`, default off, with a `CLAUDE_CODE_ARTIFACT_START_KIT` override.

Details:

- Eligible files are saved into the session scratchpad and listed for Claude to use.
- The implementation checks permissions and whether the type is listed as first-party.
- When files cannot be fetched or saved, the result explains the limitation and directs Claude to the appropriate read path.

Evidence: Starter-file collection and availability checks — search for `"tengu_concurrent_candle"`, `"CLAUDE_CODE_ARTIFACT_START_KIT"`, and `"quickstartStartKit"`.


### Automatic Protocol Negotiation for Stdio MCP Servers [Gradual Rollout]

What: Extend automatic MCP protocol probing to local stdio servers.

Status: Feature-flagged by `tengu_mcp_protocol_negotiation_stdio`, default off; the existing environment override can explicitly request automatic negotiation.

Usage:

```bash
MCP_PROTOCOL_NEGOTIATION=auto claude
```

Details:

- Stdio connections receive their own bounded probe timeout.
- If a slow-starting server exits during initialization after the probe times out, Claude Code can restart it once without the probe.
- Legacy negotiation remains available through `MCP_PROTOCOL_NEGOTIATION=legacy`.

Evidence: Transport-specific negotiation and fallback — search for `"tengu_mcp_protocol_negotiation_stdio"` and `"restarting it once without the probe"`.

## Notes

- Compared version **2.1.273 → 2.1.274**, checking both analysis snapshots and original split-module sources for substantive additions.
- Marketplace users who need LFS content must fetch it manually; `skipLfs: false` no longer enables automatic downloads.
- MCP configurations containing host-only transport types must move those registrations into the host application or use an appropriate external transport.
- Existing “Claude Code on the web” labels now generally say “cloud sessions” or “Open in browser”; this wording change does not introduce a new cloud workflow.


Generated with:
- tool: `harness-investigations@9a69160-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.274.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.274.txt`
- source modules: `archive/claude-code/original/cli-v2.1.274.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
