# Changelog for version 2.1.295

## Summary

Version 2.1.295 adds opt-in restrictions on personal configuration, structured web-search citations, and controls for self-hosted runners. Compared with 2.1.294, it also improves plugin management, gateway behavior, and recovery from interrupted connections. Several automatic recovery features ship behind disabled-by-default gates.


## New Features


### Restricted Personal Configuration

What: A new environment variable limits how personal skills, agents, plugins, and hooks can influence permissions and tool execution.

Usage:
```bash
CLAUDE_CODE_RESTRICT_PERSONAL_CONFIG=1 claude
```

Details:

- Personal skills and commands cannot use `allowed-tools` to pre-approve calls.
- Personal agents cannot widen their permission mode or define new MCP server configurations.
- Personal hooks may block or request approval, but cannot perform certain input, answer, or output rewrites.
- Invalid personal permission rules or required hooks can stop prompts and tool calls instead of silently dropping those protections.
- Restrictions depend on customization provenance; trusted host-provided and attested components have separate handling.

Evidence: Personal-customization checks and diagnostics (search for `"CLAUDE_CODE_RESTRICT_PERSONAL_CONFIG"`, `"your own agents can't define their own MCP servers"`, and `"your own skills and commands pre-approve tools"`).


### Structured Web-Search Citations

What: An opt-in citation path supplies web-search snippets as structured, citable search results.

Usage:
```bash
CLAUDE_CODE_WEBSEARCH_CITATIONS=1 claude -p \
  --verbose --output-format stream-json --allowedTools WebSearch \
  "Search the web for recent developments in TypeScript."
```

Details:

- Search results can carry their source URL, title, and snippet with citations enabled.
- Non-interactive responses join adjacent text blocks while retaining citation positions.
- The existing plain-text search-result and Markdown-source path remains available when this option is off.
- Structured results require snippets from the search backend.

Evidence: Structured search-result construction and response handling (search for `"CLAUDE_CODE_WEBSEARCH_CITATIONS"`, `"search_result"`, and `"text_runs_joined"`).


### Server Auto-Mode Lists for Self-Hosted Runners

What: Runner operators can choose which server-provided auto-mode classifier lists reach sessions.

Usage:
```bash
claude self-hosted-runner --server-auto-mode-lists no-allow
```

Details:

- `no-allow`, the default, applies `environment` and `soft_deny` while withholding `allow` exceptions.
- `all` applies all three lists.
- `none` applies none of them.
- The equivalent environment variable is `SELF_HOSTED_RUNNER_SERVER_AUTO_MODE_LISTS`.
- Invalid values stop runner startup.
- Malformed restrictions cause related grants to be withheld, preventing a partially loaded configuration from allowing more than intended.
- An `environment` entry can influence the classifier toward allowing or blocking an action; `no-allow` does not make that list restriction-only.

Evidence: Runner argument parsing, help, and launcher-settings validation (search for `"--server-auto-mode-lists"`, `"SELF_HOSTED_RUNNER_SERVER_AUTO_MODE_LISTS"`, and `"entries could allow more than the server meant"`).


### Capacity-Retry Wait Budget

What: A new environment variable bounds the accumulated wait in the persistent API capacity-retry path.

Usage:
```bash
CLAUDE_CODE_RETRY_WATCHDOG_MAX_WAIT_MS=120000 claude
```

Details:

- The value is a positive integer in milliseconds.
- Retry delays are limited to the remaining budget.
- When the budget is exhausted, the request surfaces its failure.
- This controls the capacity-retry path, rather than imposing a timeout on every tool or API operation.

Evidence: Remaining-budget calculation and retry termination (search for `"CLAUDE_CODE_RETRY_WATCHDOG_MAX_WAIT_MS"` and `"api_request_capacity_wait_exhausted"`).


### HTTP MCP Serving for Remote Tool Runtimes

What: Eligible remote tool runtimes can serve Claude Code’s MCP interface over authenticated localhost HTTP.

Usage:
```bash
# Inside an eligible remote tool runtime:
claude mcp serve --transport http --port 28471 --result-format rendered
```

Details:

- These options are registered only when `CLAUDE_CODE_REMOTE` is enabled and `CLAUDE_CODE_ENVIRONMENT_KIND` is empty.
- The server binds to `127.0.0.1`; port `0` requests a kernel-assigned port.
- `--result-format` accepts `raw` or `rendered`, defaulting to `raw`.
- `--session-tunnel` connects the server to a session relay and requires port `28471` plus a validated JSON envelope on standard input.
- The interface includes remote file operations, project-context inspection, command execution, and hook forwarding with permission checks.
- HTTP serving deliberately does not run settings/plugin hooks or send HTTP hooks.
- Ordinary local `claude mcp serve` continues to use its existing stdio interface.

Evidence: Conditional CLI registration, HTTP startup, and remote tool catalog (search for `"Transport for MCP JSON-RPC"`, `"--result-format <format>"`, `"--session-tunnel"`, and `"claude mcp serve --transport http never runs them"`).


### Opt-In Compaction Before Hosted Sessions Go Idle

What: Eligible hosted remote sessions can schedule compaction near prompt-cache expiry, before a long conversation becomes expensive to resume.

Usage:
```bash
# Set in the eligible hosted session's launch environment:
export CLAUDE_CODE_SLEEP_COMPACT=1
```

Details:

- The scheduler normally targets 90% of the cache lifetime.
- A configured exit delay can move compaction earlier.
- It requires an idle session, a warm cache, enabled compaction, sufficient context, and available usage.
- It skips sessions that are stopping, awaiting permission, or handling a newer request.
- This is hosted-session scheduling infrastructure; setting the variable in an ordinary local session does not activate this path.

Evidence: Hosted-session eligibility and cache-aware scheduling (search for `"CLAUDE_CODE_SLEEP_COMPACT"`, `"compact_sleep"`, and `"permission_pending"`).

## Improvements


### More Selective Marketplace Submodule Downloads

Marketplace cloning now examines plugin paths and supporting files before deciding which Git submodules to initialize. This can avoid fetching unrelated submodules in large marketplace repositories.

If the manifest, links, or referenced paths cannot be inspected confidently, cloning falls back to fetching all submodules.

Evidence: Manifest-based submodule selection and fallback diagnostics (search for `"Marketplace clone:"`, `"submodule.active=."`, and `"fetching every submodule"`).


### Clearer Marketplace Removal and Settings Cleanup

Marketplace removal now provides more detailed cleanup and confirmation behavior across user, project, and local settings.

- Confirmation explains which installed plugins will be uninstalled and which registration or enablement entries will be removed.
- Built-in and claude.ai-hosted marketplaces explain when `--scope` is inappropriate.
- Read-only seeded marketplaces explain why they would reappear and direct users toward disabling their plugins.
- Reserved-name collisions receive special handling so unrelated built-in plugins are preserved.

Usage:
```bash
claude plugin marketplace remove <marketplace>
```

Evidence: Removal planning and confirmation text (search for `"extraKnownMarketplaces and enabledPlugins entries"` and `"Nothing installed from"`).


### Earlier Rejection of Unusable Marketplace Names

Adding a marketplace now rejects a new name that cannot form a valid `plugin@marketplace` identifier. The error explains the allowed characters and identifies the marketplace manifest field its maintainer must change.

Evidence: Marketplace-name validation (search for `"marketplace add refused: the name cannot form a plugin id"` and `"Each part of a plugin id"`).


### More Resilient MCP Reconnection

MCP connections that repeatedly close shortly after connecting now receive reconnect backoff. Recovery also accounts for a transport that has already closed by the time its listeners are attached and avoids competing with an existing reconnect.

Evidence: Connection-close recovery and hold-off logic (search for `"transport closed again soon after it connected"` and `"Connection closed again while reconnecting"`).


### Browser Approval Prompts Identify the Site

Claude-in-Chrome approval handling can use connector-provided site metadata to name the affected site and apply site-deny rules.

When site restrictions exist but the connector’s target site is unreadable, the call is refused. Session-level site grants are offered only when the connector supports them and the action meets the grant conditions.

Evidence: Site metadata validation and permission decisions (search for `"claudecode/chromeSite"`, `"Claude in Chrome action on"`, and `"Claude in Chrome: unreadable site"`).


### Broad macOS Searches Avoid Other Applications’ Data

Recursive searches covering macOS Library locations now exclude `Containers`, `Group Containers`, and `Mobile Documents` when those directories fall beneath the search root. This reduces incidental traversal of application-private data during broad searches.

Evidence: macOS-specific ripgrep exclusions (search for `"ripgrep: leaving other apps' data out of the walk of"` and `"Group Containers"`).


### Gateway Login Can Use a Personal URL Preference

On a machine without the relevant administrator-controlled configuration, user settings can now pre-fill a gateway URL during login.

Example user settings:
```json
{
  "forceLoginMethod": "gateway",
  "forceLoginGatewayUrl": "https://gateway.example.com"
}
```

The preference remains subject to provider policy. Project, local, flag, and remote-delivered settings do not supply this fallback, and it does not automatically connect the user.

Evidence: Gateway preference selection and schema documentation (search for `"forceLoginGatewayUrl"` and `"on a machine with none of those"`).


### Native Bedrock Token Counting Through the Gateway

The bundled gateway can now answer token-count requests through AWS CountTokens where the Bedrock upstream supports it, instead of always rejecting that endpoint.

Failures produce diagnostics about AWS permissions and proxy routing. Token-counting failure does not disable model requests; fallback counting paths remain available.

Evidence: Bedrock token-count routing and recovery diagnostics (search for `"AWS CountTokens works again"`, `"bedrock:CountTokens"`, and `"count_tokens is not available on this Bedrock upstream"`).


### Gateway Timeouts Cover More Providers

An explicitly configured `timeouts.upstream_ttfb_ms` now also applies to streaming and token-count requests on non-Anthropic upstreams. Previously, that setting applied to Anthropic upstreams only.

Gateway startup logs explain the expanded scope. Operators who configured a short timeout should review it for providers with slower first responses.

Evidence: Provider request options and startup diagnostics (search for `"timeouts.upstream_ttfb_ms:"` and `"older gateways applied it to provider: anthropic upstreams only"`).


### Configurable Git Fetch Progress Deadline

Self-hosted checkout preparation adds a configurable deadline for server-side Git progress before pack data arrives.

Usage:
```bash
CLAUDE_RUNNER_FETCH_SERVER_PROGRESS_CAP_MS=900000 \
  claude self-hosted-runner
```

Details:

- The default is ten minutes.
- Positive values are clamped between two and thirty minutes.
- `0` or `off` disables this cap.
- Diagnostics distinguish missing client-side progress from server progress that has stopped advancing.

Evidence: Fetch-progress deadline parsing and reporting (search for `"CLAUDE_RUNNER_FETCH_SERVER_PROGRESS_CAP_MS"` and `"no pack data received; server-side progress last advanced"`).


### Plugin Updates Respect Host-Level Pins

When a host manages Claude Code’s update pin, plugin auto-update now checks the applicable settings and update-disable conditions before proceeding. Diagnostics explain when plugin updates are held under that pin.

Evidence: Host-aware plugin update eligibility (search for `"CLAUDE_CODE_AUTOUPDATER_DISABLED_BY_HOST"` and `"Plugin autoupdate: off under the host's pin"`).


### Better Recovery Guidance When an Attached Computer Sleeps

Remote-tool failures now distinguish an attached computer announcing sleep from a generic connection failure.

The session can explain that a command may be paused or partly executed, avoid replaying it, and receive a later correction about its outcome. Reachability notifications let pending work continue when the computer returns.

Evidence: Sleep-state and command-outcome guidance (search for `"The command was not cancelled: it is paused with the machine"` and `"This session now knows what became of a command"`).


### More Useful Artifact Conflict Responses

When publishing against a newer live artifact version, the conflict response can now compare the submitted page with the live page and provide a line diff for merging.

If their author content is identical, the response explains that publishing would lose none of it and permits a subsequent publish. The comparison explicitly excludes supporting files, removals, and the title.

Evidence: Conflict comparison and merge instructions (search for `"Against the content you just sent"`, `"Compared with the content you just sent"`, and `"supporting files, removals and the title were not compared"`).


### More Explicit Hook Failure Behavior

The existing `onFailure: "block"` option receives broader failure handling and clearer documentation. Failures include startup errors, timeouts, unsuccessful exit codes, and invalid JSON answers.

Async hooks and the completion events `Stop`, `SubagentStop`, `TaskCompleted`, and `TeammateIdle` remain excluded from this blocking behavior.

Evidence: Hook-failure conversion and documented exceptions (search for `"What a failure of this hook does"` and `"onFailure: \"block\" is ignored on"`).

## Bug Fixes

- Windows project/local plugin installations can be recognized when the same directory or checkout is opened under another spelling of its path. This avoids treating the plugin as absent solely because the stored path differs. Evidence: search for `"the same folder or the same checkout, under another spelling of its path"`.
- A rejected long-context beta can be retried once without that beta. After a successful retry, the session sizes the model without 1M context until a reset such as clearing, compaction, resume, or provider change. Evidence: search for `"retry:context-1m-beta"` and `"long context beta"`.
- Remote MCP approvals missing their stored arguments are refused instead of being treated as reusable approval. Evidence: search for `"the user's approval was stored without this call's arguments"`.
- Served shell calls recheck their working directory before execution. A directory that was moved, deleted, replaced by a link, or made unreadable invalidates the call’s earlier permission check. Evidence: search for `"Could not confirm that working directory"` and `"WORKING_DIRECTORY_MOVED_UNDONE"`.
- A `/loop` wakeup whose deadline passed while the process was stopped now produces an explicit stopped notification. The user can reply to continue scheduling it. Evidence: search for `"after its next /loop wakeup was due"`.
- Deliberately closed session connections no longer initiate another connect or reconnect. Evidence: search for `"[SessionsV2Client] Ignoring reconnect() — deliberately closed"`.
- Background attachment and daemon startup now stand down when the process is exiting. Where relevant, the terminal explains that unattended background sessions may stop and suggests `claude agents` to keep them. Evidence: search for `"Background sessions still running will stop in about a minute"` and `"daemon: not started, because this process is exiting"`.
- MCP WebSocket messages exceeding the transport cap are rejected before parsing, with an explicit error and connection closure. Evidence: search for `"MCP server sent a WebSocket message over"`.
- A blocking hook’s exit-code-2 decision is preserved when its output stream is cut before completion. Evidence: search for `"hook stdio was cut before end-of-stream"`.

## In Development

These paths have new infrastructure but default to disabled or remain unreachable. Server-controlled gates may enable some of them for selected sessions.


### Automatic Recovery After a Prompt-Too-Long Refusal [In Development]

What: Attempt compaction after the backend rejects a prompt as too long, then continue with the compacted conversation.

Status: Feature-flagged; `tengu_modular_seal` defaults to false.

Details:

- The recovery path checks conversation length, previous refusals, compaction state, and whether compaction could actually create enough room.
- It avoids repeated or futile attempts.
- This extends existing auto-compaction rather than introducing compaction itself.

Evidence: Refusal-triggered recovery (search for `"tengu_modular_seal"` and `"compactAfterRefusal: the compaction threw"`).


### MCP Retry at the Start of a Later Turn [In Development]

What: Retry eligible transient MCP connection failures when another conversation turn begins.

Status: Feature-flagged; `tengu_snug_reef` defaults to zero retry turns.

Details:

- Tracks attempts and backoff separately for each server.
- Avoids duplicating connections already being attempted.
- Applies limits to retry concurrency and how long a turn waits.
- Authentication and other non-transient failures are handled separately.

Evidence: Turn-start redial scheduling (search for `"tengu_snug_reef"` and `"[MCP] Retrying"`).


### Pending Launcher Approvals Reconsidered After Settings Changes [In Development]

What: Allow certain pending launcher-mediated permission requests to resolve when changed permission settings now permit the call.

Status: Feature-flagged; `tengu_drifting_dream` defaults to false.

Details:

- Rechecks the current permission context while the request is still waiting.
- Excludes forced approvals, person-only requests, hook-imposed approval floors, and remote-execution requests.
- Requires an explicit qualifying allow decision.

Evidence: Permission-change subscription and re-evaluation (search for `"tengu_drifting_dream"` and `"permissionRecheckSignal: hasPermissionsToUseTool failed for a waiting can_use_tool ask"`).


### Usage Warning When Returning to an Idle Conversation [In Development]

What: Extend the existing cold-resume usage warning to an already-open conversation whose cached context has become cold.

Status: Feature-flagged; the new idle path uses `tengu_drifting_nova`, defaulting to false.

Details:

- Estimates the share of the five-hour allowance required to resend the conversation.
- Offers resuming or starting a new conversation.
- Preserves unsent input and handles pasted text while the warning is open.
- Includes input protections against accidentally choosing a new conversation.

Evidence: Idle-triggered warning and input preservation (search for `"tengu_drifting_nova"` and `"Your unsent message will still be there after you answer"`).


### Configuration-Based Subagent Usage Warning [In Development]

What: Warn when personal configuration encourages subagents that may increase token use.

Status: Feature-flagged; `tengu_luminous_locket` defaults to `{ off: true }`. An explicit `CLAUDE_CODE_SUBAGENT_CONFIG_WARNING` override also exists.

Details:

- Examines CLAUDE.md content, skill descriptions, and custom agent descriptions.
- Uses a classifier to identify configuration encouraging subagents.
- Limits how often the warning appears.
- The warning suggests editing those instructions; it does not automatically change them.

Evidence: Configuration analysis and notification text (search for `"tengu_luminous_locket"`, `"subagent-config-warning"`, and `"may save tokens on"`).


### Cloud Environment Selection by Name or Hosted ID [In Development]

What: Recognize environment names and `env_...` IDs in addition to self-hosted pool IDs.

Status: Stubbed and blocked by the active argument-validation path.

Details:

- A parser distinguishes pool IDs, hosted environment IDs, and names.
- The resolver always returns `ok: false` with `environment_unresolved`.
- The active CLI validation still requires a `ccpool_...` self-hosted environment ID.
- Names and hosted IDs therefore cannot be used through this new path yet.

Evidence: Parser, hardcoded rejection, and resolver stub (search for `"environment_unresolved"` and `"--environment expects a self-hosted environment id (ccpool_...)"`).


### Missing File-Transfer Notifications [In Development]

What: Notify a receiving session when staged files were not placed successfully and may be missing or outdated.

Status: Feature-flagged; `tengu_ochre_dunlin` defaults to false.

Details:

- Creates a passive notification identifying affected paths.
- Explains that files may not have arrived or may still contain an older copy.
- Does not automatically replay the transfer.

Evidence: Staged-file notification construction (search for `"tengu_ochre_dunlin"` and `"may be missing or hold an older copy"`).

## Notes

Restricted personal configuration is opt-in. When enabled, customizations that previously granted permissions or rewrote tool input may require changes; affected diagnostics identify the source.

Self-hosted runner operators should review the new auto-mode list policy and Git progress deadline. Gateway operators should review explicitly configured first-byte timeouts because they now cover additional providers.

This comparison covers CLI implementation changes between 2.1.294 and 2.1.295, with substantive claims checked against the original split-module sources. Rebundling changes, identifier renames, and separate VSCode or SDK package features are excluded.


Generated with:
- tool: `harness-investigations@523aa00-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.295.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.295.txt`
- source modules: `archive/claude-code/original/cli-v2.1.295.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
